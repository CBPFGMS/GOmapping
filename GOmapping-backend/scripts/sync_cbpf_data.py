import argparse
import csv
import os
import sys
from io import StringIO
from pathlib import Path

import requests


def setup_django():
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")
    import django  # noqa: WPS433

    django.setup()


def parse_int(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_str(value):
    if value is None:
        return ""
    return str(value).strip()


def calculate_match_percent(instance_org_name, global_org_name):
    """
    Calculate name match percentage between Instance Org and Global Org.

    Uses SequenceMatcher to compute string similarity.
    Returns: 0-100 percentage (Decimal).

    Examples:
    - "Lutheran World Federation" vs "Lutheran World Federation" = 100.00
    - "Lutheran World federation" vs "Lutheran World Federation" = 96.15
    - "Food and Agriculture Organization" vs "FAO" = 12.50
    """
    from difflib import SequenceMatcher
    from decimal import Decimal
    
    if not instance_org_name or not global_org_name:
        return None
    
    # Normalize names (lowercase and trim spaces)
    name1 = instance_org_name.lower().strip()
    name2 = global_org_name.lower().strip()
    
    if not name1 or not name2:
        return None
    
    # Compute similarity using SequenceMatcher
    ratio = SequenceMatcher(None, name1, name2).ratio()
    
    # Convert to percentage with two decimals
    match_percent = round(ratio * 100, 2)
    
    return Decimal(str(match_percent))


def fetch_csv_rows(url, auth=None, timeout=120):
    resp = requests.get(url, auth=auth, timeout=timeout)
    resp.raise_for_status()
    text = resp.content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(StringIO(text))
    return list(reader)


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def upsert_global_orgs(rows, batch_size=1000):
    from django.db import connection
    
    org_data = {}
    skipped_rows = []  
    
    for row in rows:
        # PF_GLOBAL_ORG API uses ParentOrganizationId as the global org ID
        go_id = parse_int(row.get("ParentOrganizationId"))
        if go_id is None:
            skipped_rows.append({
                'reason': 'Missing or invalid ParentOrganizationId',
                'ParentOrganizationId': row.get("ParentOrganizationId"),
                'GlobalOrgName': row.get("GlobalOrgName"),
                'GlobalOrgAcronym': row.get("GlobalOrgAcronym")
            })
            continue
        name = parse_str(row.get("GlobalOrgName"))
        if not name:
            skipped_rows.append({
                'reason': 'Missing GlobalOrgName',
                'ParentOrganizationId': go_id,
                'GlobalOrgName': row.get("GlobalOrgName"),
                'GlobalOrgAcronym': row.get("GlobalOrgAcronym")
            })
            continue
        acronym = parse_str(row.get("GlobalOrgAcronym")) or None
        # Truncate acronym to 50 chars to fit database field limit
        if acronym and len(acronym) > 50:
            acronym = acronym[:50]
        org_data[go_id] = {
            "global_org_id": go_id,
            "global_org_name": name,
            "global_acronym": acronym,
        }

    if not org_data:
        return 0, 0

    # Use raw SQL to upsert into both tables
    created_count = 0
    updated_count = 0
    
    cursor = connection.cursor()
    
    for go_id, data in org_data.items():
        # Check if exists in global_organization_mock (the table with FK constraint)
        cursor.execute(
            "SELECT global_org_id FROM global_organization_mock WHERE global_org_id = %s",
            [go_id]
        )
        exists = cursor.fetchone() is not None
        
        if exists:
            # Update both tables
            for table in ['global_organization', 'global_organization_mock']:
                cursor.execute(f"""
                    UPDATE {table}
                    SET global_org_name = %s, global_acronym = %s
                    WHERE global_org_id = %s
                """, [data["global_org_name"], data["global_acronym"], go_id])
            updated_count += 1
        else:
            # Insert into both tables
            for table in ['global_organization', 'global_organization_mock']:
                cursor.execute(f"""
                    INSERT INTO {table} (global_org_id, global_org_name, global_acronym, usage_count)
                    VALUES (%s, %s, %s, 0)
                """, [go_id, data["global_org_name"], data["global_acronym"]])
            created_count += 1
    
    connection.commit()
    
    # Print skipped rows
    if skipped_rows:
        print(f"\n⚠️  GlobalOrg: Skipped {len(skipped_rows)} rows due to data quality issues:")
        print("-" * 80)
        for i, skip in enumerate(skipped_rows[:20], 1):  # Show only the first 20
            print(f"{i}. Reason: {skip['reason']}")
            print(f"   ParentOrganizationId: {skip.get('ParentOrganizationId')}")
            print(f"   GlobalOrgName: {skip.get('GlobalOrgName')}")
            print(f"   GlobalOrgAcronym: {skip.get('GlobalOrgAcronym')}")
            print()
        
        if len(skipped_rows) > 20:
            print(f"   ... and {len(skipped_rows) - 20} more rows")
        print("-" * 80)
    
    return created_count, updated_count


def upsert_org_mappings(rows, batch_size=1000):
    from django.utils import timezone
    from orgnizations.models import GlobalOrganization, OrgMapping

    mapping_rows = []
    instance_ids = set()
    global_ids = set()
    skipped_rows = []  # Track skipped rows

    for row in rows:
        instance_org_id = parse_int(row.get("OrganizationId"))
        global_org_id = parse_int(row.get("GlobalOrgId"))
        if instance_org_id is None or global_org_id is None:
            skipped_rows.append({
                'reason': 'Missing or invalid ID',
                'OrganizationId': row.get("OrganizationId"),
                'GlobalOrgId': row.get("GlobalOrgId"),
                'OrganizationName': row.get("OrganizationName")
            })
            continue

        instance_org_name = parse_str(row.get("OrganizationName"))
        instance_org_type= parse_str(row.get("OrganizationTypeName"))
        if not instance_org_name:
            skipped_rows.append({
                'reason': 'Missing OrganizationName',
                'OrganizationId': instance_org_id,
                'GlobalOrgId': global_org_id,
                'OrganizationName': row.get("OrganizationName")
            })
            continue

        status_raw = parse_str(row.get("DueDiligenceStatus")) or None
        # Truncate to 50 chars to fit database field limit
        if status_raw and len(status_raw) > 50:
            status_raw = status_raw[:50]
        
        mapping_rows.append(
            {
                "instance_org_id": instance_org_id,
                "instance_org_name": instance_org_name,
                "instance_org_acronym": parse_str(row.get("OrganizationAcronym")) or None,
                "instance_org_type": instance_org_type,
                "global_org_id": global_org_id,
                "fund_id": parse_int(row.get("PooledFundId")),
                "fund_name": parse_str(row.get("PooledFundName")) or None,
                "status": status_raw,
            }
        )
        instance_ids.add(instance_org_id)
        global_ids.add(global_org_id)

    if not mapping_rows:
        return 0, 0, 0

    # Ensure all referenced global orgs exist in both tables
    from django.db import connection
    cursor = connection.cursor()
    
    if global_ids:
        ids_str = ','.join(map(str, global_ids))
        
        # Check existing in both tables
        cursor.execute(f"SELECT global_org_id FROM global_organization WHERE global_org_id IN ({ids_str})")
        existing_in_main = set(row[0] for row in cursor.fetchall())
        
        cursor.execute(f"SELECT global_org_id FROM global_organization_mock WHERE global_org_id IN ({ids_str})")
        existing_in_mock = set(row[0] for row in cursor.fetchall())
        
        # Insert only where missing
        for go_id in global_ids:
            if go_id not in existing_in_main:
                cursor.execute("""
                    INSERT INTO global_organization (global_org_id, global_org_name, global_acronym, usage_count)
                    VALUES (%s, %s, NULL, 0)
                """, [go_id, f"Global Org {go_id}"])
            
            if go_id not in existing_in_mock:
                cursor.execute("""
                    INSERT INTO global_organization_mock (global_org_id, global_org_name, global_acronym, usage_count)
                    VALUES (%s, %s, NULL, 0)
                """, [go_id, f"Global Org {go_id}"])
        
        connection.commit()

    # Fetch Global Org names for match_percent calculation
    global_org_names = {}
    if global_ids:
        global_orgs = GlobalOrganization.objects.filter(
            global_org_id__in=global_ids
        ).values('global_org_id', 'global_org_name')
        global_org_names = {go['global_org_id']: go['global_org_name'] for go in global_orgs}

    existing = {}
    for id_chunk in chunked(list(instance_ids), 2000):
        qs = OrgMapping.objects.filter(instance_org_id__in=id_chunk).values(
            "id", "instance_org_id", "fund_id", "global_org_id"
        )
        for item in qs:
            key = (item["instance_org_id"], item["fund_id"], item["global_org_id"])
            existing[key] = item["id"]

    to_create = []
    to_update = []
    now = timezone.now()

    for row in mapping_rows:
        key = (row["instance_org_id"], row["fund_id"], row["global_org_id"])
        existing_id = existing.get(key)
        
        # Calculate match_percent
        global_org_name = global_org_names.get(row["global_org_id"], "")
        match_percent = calculate_match_percent(row["instance_org_name"], global_org_name)
        
        if existing_id is None:
            to_create.append(
                OrgMapping(
                    global_org_id=row["global_org_id"],
                    instance_org_id=row["instance_org_id"],
                    instance_org_name=row["instance_org_name"],
                    instance_org_acronym=row["instance_org_acronym"],
                    instance_org_type= row["instance_org_type"],
                    parent_instance_org_id=None,
                    fund_id=row["fund_id"],
                    fund_name=row["fund_name"],
                    match_percent=match_percent,
                    risk_level=None,
                    status=row["status"],
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            to_update.append(
                OrgMapping(
                    id=existing_id,
                    global_org_id=row["global_org_id"],
                    instance_org_name=row["instance_org_name"],
                    instance_org_acronym=row["instance_org_acronym"],
                    instance_org_type=row["instance_org_type"],
                    parent_instance_org_id=None,
                    fund_id=row["fund_id"],
                    fund_name=row["fund_name"],
                    match_percent=match_percent,
                    risk_level=None,
                    status=row["status"],
                    updated_at=now,
                )
            )

    if to_create:
        OrgMapping.objects.bulk_create(to_create, batch_size=batch_size)
    if to_update:
        OrgMapping.objects.bulk_update(
            to_update,
            [
                "global_org_id",
                "instance_org_name",
                "instance_org_acronym",
                "instance_org_type",
                "parent_instance_org_id",
                "fund_id",
                "fund_name",
                "match_percent",
                "risk_level",
                "status",
                "updated_at",
            ],
            batch_size=batch_size,
        )

    # Print skipped rows
    if skipped_rows:
        print(f"\n⚠️  Skipped {len(skipped_rows)} rows due to data quality issues:")
        print("-" * 80)
        for i, skip in enumerate(skipped_rows[:20], 1):  # Show only the first 20
            print(f"{i}. Reason: {skip['reason']}")
            print(f"   OrganizationId: {skip.get('OrganizationId')}")
            print(f"   GlobalOrgId: {skip.get('GlobalOrgId')}")
            print(f"   OrganizationName: {skip.get('OrganizationName')}")
            print()
        
        if len(skipped_rows) > 20:
            print(f"   ... and {len(skipped_rows) - 20} more rows")
        print("-" * 80)
    
    return len(mapping_rows), len(to_create), len(to_update)


def main():
    parser = argparse.ArgumentParser(description="Sync CBPF CSV data into database")
    # instance organization (PF_ORG_SUMMARY) mapping
    parser.add_argument(
        "--org-mapping-url",
        default="https://cbpfapi.unocha.org/vo3/odata/GlobalGenericDataExtract"
        "?SPCode=PF_ORG_SUMMARY&PoolfundCodeAbbrv=&$format=csv",
    )
    # global organization (PF_GLOBAL_ORG)
    parser.add_argument(
        "--global-org-url",
        default="https://cbpfapi.unocha.org/vo3/odata/GlobalGenericDataExtract"
        "?SPCode=PF_GLOBAL_ORG&PoolfundCodeAbbrv=&$format=csv",
    )
    parser.add_argument("--user", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--no-auth", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    # Credentials are intentionally hard-coded per user request.
    default_user = "35e38643-0226-4f33-81e3-c09f46a2136b"
    default_password = "trigyn123"

    auth = None
    if not args.no_auth:
        user = args.user or default_user
        password = args.password or default_password
        if not user or not password:
            raise SystemExit("Missing credentials. Provide --user/--password.")
        auth = (user, password)

    setup_django()

    print("Fetching global org detail data...")
    detail_rows = fetch_csv_rows(args.global_org_url, auth=auth, timeout=args.timeout)
    print(f"Fetched {len(detail_rows)} rows from API")
    created, updated = upsert_global_orgs(detail_rows)
    print(f"\nGlobalOrganization Summary:")
    print(f"  - Fetched from API: {len(detail_rows)}")
    print(f"  - Created: {created}")
    print(f"  - Updated: {updated}")
    print(f"  - Processed: {created + updated}")
    print(f"  - Skipped: {len(detail_rows) - (created + updated)}")

    print("Fetching org summary data...")
    summary_rows = fetch_csv_rows(args.org_mapping_url, auth=auth, timeout=args.timeout)
    print(f"Fetched {len(summary_rows)} rows from API")
    total, created, updated = upsert_org_mappings(summary_rows)
    print(f"\nOrgMapping Summary:")
    print(f"  - Fetched from API: {len(summary_rows)}")
    print(f"  - Valid rows: {total}")
    print(f"  - Skipped rows: {len(summary_rows) - total}")
    print(f"  - Created: {created}")
    print(f"  - Updated: {updated}")

    print("\nSync finished.")


if __name__ == "__main__":
    main()

