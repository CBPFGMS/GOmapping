import csv
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
from difflib import SequenceMatcher
from io import StringIO

import requests
from flask import current_app

from ..cache import cache
from ..extensions import db
from ..models import DataSyncLog, GlobalOrganization, OrgMapping


def _parse_int(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _parse_str(value):
    return str(value).strip() if value is not None else ""


def _calculate_match_percent(instance_name, global_name):
    if not instance_name or not global_name:
        return None
    ratio = SequenceMatcher(None, instance_name.lower().strip(), global_name.lower().strip()).ratio()
    return Decimal(str(round(ratio * 100, 2)))


class SmartDataSyncService:
    ORG_SUMMARY_URL = (
        "https://cbpfapi.unocha.org/vo3/odata/GlobalGenericDataExtract"
        "?SPCode=PF_ORG_SUMMARY&PoolfundCodeAbbrv=&$format=csv"
    )
    GLOBAL_ORG_URL = (
        "https://cbpfapi.unocha.org/vo3/odata/GlobalGenericDataExtract"
        "?SPCode=PF_GLOBAL_ORG&PoolfundCodeAbbrv=&$format=csv"
    )
    DEFAULT_USER = "35e38643-0226-4f33-81e3-c09f46a2136b"
    DEFAULT_PASSWORD = "trigyn123"
    MIN_SYNC_INTERVAL = 30

    def __init__(self, auth=None):
        self.auth = auth or (self.DEFAULT_USER, self.DEFAULT_PASSWORD)

    def fetch_csv_rows(self, url, timeout=120):
        resp = requests.get(url, auth=self.auth, timeout=timeout)
        resp.raise_for_status()
        text = resp.content.decode("utf-8-sig", errors="replace")
        return list(csv.DictReader(StringIO(text)))

    def get_data_checksum(self, sync_type, sample_size=10240):
        url = self.ORG_SUMMARY_URL if sync_type == "org_mapping" else self.GLOBAL_ORG_URL
        try:
            response = requests.get(url, auth=self.auth, stream=True, timeout=30)
            response.raise_for_status()
            sample_data = response.raw.read(sample_size)
            return hashlib.md5(sample_data).hexdigest()
        except Exception:
            return None

    def should_sync(self, sync_type="org_mapping", force=False):
        if force:
            return True, "force_sync", None

        last_sync = (
            DataSyncLog.query.filter(
                DataSyncLog.sync_type == sync_type,
                DataSyncLog.status.in_(["success", "no_changes"]),
            )
            .order_by(DataSyncLog.started_at.desc())
            .first()
        )

        if last_sync and last_sync.completed_at:
            time_since_sync = datetime.utcnow() - last_sync.completed_at
            if time_since_sync < timedelta(minutes=self.MIN_SYNC_INTERVAL):
                mins = time_since_sync.total_seconds() / 60
                return False, f"too_soon ({mins:.1f} minutes ago)", last_sync

        try:
            current_checksum = self.get_data_checksum(sync_type)
            if current_checksum and last_sync and current_checksum == last_sync.data_checksum:
                return False, "no_changes", last_sync
        except Exception:
            pass

        return True, "should_sync", last_sync

    def upsert_global_orgs(self, rows):
        created = 0
        updated = 0
        for row in rows:
            go_id = _parse_int(row.get("ParentOrganizationId"))
            if go_id is None:
                continue
            name = _parse_str(row.get("GlobalOrgName"))
            if not name:
                continue
            acronym = _parse_str(row.get("GlobalOrgAcronym")) or None
            if acronym and len(acronym) > 50:
                acronym = acronym[:50]

            item = GlobalOrganization.query.filter_by(global_org_id=go_id).first()
            if item:
                item.global_org_name = name
                item.global_acronym = acronym
                updated += 1
            else:
                db.session.add(
                    GlobalOrganization(
                        global_org_id=go_id,
                        global_org_name=name,
                        global_acronym=acronym,
                        usage_count=0,
                    )
                )
                created += 1
        db.session.commit()
        return created, updated

    def upsert_org_mappings(self, rows):
        created = 0
        updated = 0
        valid_rows = 0

        global_names = {g.global_org_id: g.global_org_name for g in GlobalOrganization.query.all()}

        for row in rows:
            instance_org_id = _parse_int(row.get("OrganizationId"))
            global_org_id = _parse_int(row.get("GlobalOrgId"))
            if instance_org_id is None or global_org_id is None:
                continue
            valid_rows += 1

            instance_org_name = _parse_str(row.get("OrganizationName"))
            instance_org_type = _parse_str(row.get("OrganizationTypeName"))
            if not instance_org_name:
                continue

            fund_id = _parse_int(row.get("PooledFundId"))
            match_percent = _calculate_match_percent(instance_org_name, global_names.get(global_org_id, ""))
            status_val = _parse_str(row.get("DueDiligenceStatus")) or None
            if status_val and len(status_val) > 50:
                status_val = status_val[:50]

            item = OrgMapping.query.filter_by(
                instance_org_id=instance_org_id,
                fund_id=fund_id,
                global_org_id=global_org_id,
            ).first()

            if item:
                item.instance_org_name = instance_org_name
                item.instance_org_type = instance_org_type
                item.instance_org_acronym = _parse_str(row.get("OrganizationAcronym")) or None
                item.fund_name = _parse_str(row.get("PooledFundName")) or None
                item.match_percent = match_percent
                item.status = status_val
                item.updated_at = datetime.utcnow()
                updated += 1
            else:
                db.session.add(
                    OrgMapping(
                        global_org_id=global_org_id,
                        instance_org_id=instance_org_id,
                        instance_org_name=instance_org_name,
                        instance_org_acronym=_parse_str(row.get("OrganizationAcronym")) or None,
                        instance_org_type=instance_org_type,
                        parent_instance_org_id=None,
                        fund_id=fund_id,
                        fund_name=_parse_str(row.get("PooledFundName")) or None,
                        match_percent=match_percent,
                        risk_level=None,
                        status=status_val,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )
                created += 1

        db.session.commit()
        return valid_rows, created, updated

    def _sync_data(self, sync_type, url, upsert_function, triggered_by="manual", force=False):
        should_sync, reason, last_sync = self.should_sync(sync_type, force)
        if not should_sync:
            return {
                "synced": False,
                "reason": reason,
                "last_sync_time": last_sync.completed_at.isoformat() if last_sync and last_sync.completed_at else None,
                "message": f"Skipped: {reason}",
            }

        log = DataSyncLog(sync_type=sync_type, status="running", triggered_by=triggered_by)
        db.session.add(log)
        db.session.commit()

        try:
            rows = self.fetch_csv_rows(url, timeout=120)
            log.records_fetched = len(rows)

            if upsert_function == "upsert_global_orgs":
                created, updated = self.upsert_global_orgs(rows)
                fetched = len(rows)
            else:
                fetched, created, updated = self.upsert_org_mappings(rows)

            log.records_created = created
            log.records_updated = updated
            log.data_checksum = self.get_data_checksum(sync_type)
            log.status = "success" if (created > 0 or updated > 0) else "no_changes"
            log.completed_at = datetime.utcnow()
            db.session.commit()

            if created > 0 or updated > 0:
                cache.delete("go_summary_data")
                cache.delete("mapping_dashboard_data")

            return {
                "synced": True,
                "sync_id": log.sync_id,
                "fetched": fetched,
                "created": created,
                "updated": updated,
                "duration": log.duration_seconds,
                "message": f"Successfully synced {fetched} records: {created} created, {updated} updated",
            }
        except Exception as exc:
            log.status = "failed"
            log.error_message = str(exc)
            log.completed_at = datetime.utcnow()
            db.session.commit()
            raise

    def sync_global_orgs(self, triggered_by="manual", force=False):
        return self._sync_data("global_org", self.GLOBAL_ORG_URL, "upsert_global_orgs", triggered_by, force)

    def sync_org_mappings(self, triggered_by="manual", force=False):
        return self._sync_data("org_mapping", self.ORG_SUMMARY_URL, "upsert_org_mappings", triggered_by, force)

    def sync_all(self, triggered_by="manual", force=False):
        results = {"global_org": None, "org_mapping": None, "overall_status": "success", "message": ""}
        try:
            results["global_org"] = self.sync_global_orgs(triggered_by, force)
        except Exception as exc:
            results["global_org"] = {"error": str(exc)}
            results["overall_status"] = "partial_failed"

        try:
            results["org_mapping"] = self.sync_org_mappings(triggered_by, force)
        except Exception as exc:
            results["org_mapping"] = {"error": str(exc)}
            results["overall_status"] = "failed"

        changes = 0
        for part in [results["global_org"], results["org_mapping"]]:
            if part and not part.get("error"):
                changes += part.get("created", 0) + part.get("updated", 0)

        if changes:
            results["message"] = f"Synced successfully. {changes} records changed. Cache cleared."
        else:
            results["message"] = "Sync completed. No changes detected."
        return results

    def get_sync_status(self, sync_type=None):
        query = DataSyncLog.query
        if sync_type:
            query = query.filter_by(sync_type=sync_type)

        last_sync = query.filter(DataSyncLog.status.in_(["success", "no_changes"])).order_by(DataSyncLog.started_at.desc()).first()
        last_attempt = query.order_by(DataSyncLog.started_at.desc()).first()
        running_sync = query.filter_by(status="running").order_by(DataSyncLog.started_at.desc()).first()

        one_day_ago = datetime.utcnow() - timedelta(days=1)
        recent = query.filter(DataSyncLog.started_at >= one_day_ago)

        return {
            "is_syncing": running_sync is not None,
            "last_sync": {
                "time": last_sync.completed_at.isoformat() if last_sync and last_sync.completed_at else None,
                "status": last_sync.status if last_sync else None,
                "created": last_sync.records_created if last_sync else 0,
                "updated": last_sync.records_updated if last_sync else 0,
                "duration": last_sync.duration_seconds if last_sync else None,
            }
            if last_sync
            else None,
            "last_attempt": {
                "time": last_attempt.started_at.isoformat() if last_attempt and last_attempt.started_at else None,
                "status": last_attempt.status if last_attempt else None,
                "error": last_attempt.error_message if last_attempt and last_attempt.status == "failed" else None,
            }
            if last_attempt
            else None,
            "recent_24h": {
                "total_syncs": recent.count(),
                "successful": recent.filter(DataSyncLog.status.in_(["success", "no_changes"])).count(),
                "failed": recent.filter_by(status="failed").count(),
            },
        }

    def get_sync_history(self, limit=20, sync_type=None):
        query = DataSyncLog.query
        if sync_type:
            query = query.filter_by(sync_type=sync_type)
        logs = query.order_by(DataSyncLog.started_at.desc()).limit(limit).all()
        return [
            {
                "sync_id": log.sync_id,
                "sync_type": log.sync_type,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "status": log.status,
                "records_fetched": log.records_fetched,
                "records_created": log.records_created,
                "records_updated": log.records_updated,
                "duration_seconds": log.duration_seconds,
                "triggered_by": log.triggered_by,
                "error_message": log.error_message if log.status == "failed" else None,
            }
            for log in logs
        ]


def get_sync_service():
    return SmartDataSyncService()
