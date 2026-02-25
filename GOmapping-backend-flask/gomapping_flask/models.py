from datetime import datetime

from sqlalchemy import DECIMAL, Index

from .extensions import db


class GlobalOrganization(db.Model):
    __tablename__ = "global_organization"

    global_org_id = db.Column(db.Integer, primary_key=True)
    global_org_name = db.Column(db.String(255), nullable=False)
    global_acronym = db.Column(db.String(50))
    usage_count = db.Column(db.Integer, default=0)


class GoSimilarity(db.Model):
    __tablename__ = "go_similarity"

    source_global_org_id = db.Column(db.Integer, primary_key=True)
    target_global_org_id = db.Column(db.Integer, primary_key=True)
    similarity_percent = db.Column(DECIMAL(5, 2), nullable=False)


class OrgMapping(db.Model):
    __tablename__ = "org_mapping"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    global_org_id = db.Column(db.Integer, nullable=False)
    instance_org_id = db.Column(db.Integer)
    instance_org_name = db.Column(db.String(255), nullable=False)
    instance_org_acronym = db.Column(db.String(50))
    instance_org_type = db.Column(db.String(255), nullable=False)
    parent_instance_org_id = db.Column(db.Integer)
    fund_name = db.Column(db.String(255))
    fund_id = db.Column(db.Integer)
    match_percent = db.Column(DECIMAL(5, 2))
    risk_level = db.Column(db.String(10))
    status = db.Column(db.String(20))
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)


class DataSyncLog(db.Model):
    __tablename__ = "data_sync_log"
    __table_args__ = (
        Index("ix_data_sync_log_started_at_desc", "started_at"),
        Index("ix_data_sync_log_sync_type_started_at", "sync_type", "started_at"),
        Index("ix_data_sync_log_status", "status"),
    )

    sync_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sync_type = db.Column(db.String(50), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime)
    records_fetched = db.Column(db.Integer, default=0)
    records_created = db.Column(db.Integer, default=0)
    records_updated = db.Column(db.Integer, default=0)
    records_deleted = db.Column(db.Integer, default=0)
    data_checksum = db.Column(db.String(64))
    status = db.Column(db.String(20), default="running", nullable=False)
    error_message = db.Column(db.Text, default="")
    triggered_by = db.Column(db.String(50), default="auto")

    @property
    def duration_seconds(self):
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class MergeDecision(db.Model):
    __tablename__ = "merge_decisions"
    __table_args__ = (
        Index("ix_merge_decisions_instance_org_id", "instance_org_id"),
        Index("ix_merge_decisions_original_global_org_id", "original_global_org_id"),
        Index("ix_merge_decisions_target_global_org_id", "target_global_org_id"),
        Index("ix_merge_decisions_execution_status", "execution_status"),
        Index("ix_merge_decisions_decided_at_desc", "decided_at"),
    )

    decision_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    instance_org_id = db.Column(db.Integer, nullable=False)
    instance_org_name = db.Column(db.String(255), nullable=False)
    original_global_org_id = db.Column(db.Integer, nullable=False)
    original_global_org_name = db.Column(db.String(255), nullable=False)
    target_global_org_id = db.Column(db.Integer, nullable=False)
    target_global_org_name = db.Column(db.String(255), nullable=False)
    decision_type = db.Column(db.String(50), default="remap", nullable=False)
    confidence = db.Column(db.String(20))
    similarity_score = db.Column(DECIMAL(5, 2))
    notes = db.Column(db.Text, default="")
    decided_by = db.Column(db.String(100), default="admin")
    decided_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    execution_status = db.Column(db.String(50), default="pending", nullable=False)
    executed_at = db.Column(db.DateTime)
    executed_by = db.Column(db.String(100))
    execution_notes = db.Column(db.Text, default="")
