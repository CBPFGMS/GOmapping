# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class GlobalOrganization(models.Model):
    global_org_id = models.IntegerField(primary_key=True)
    global_org_name = models.CharField(max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS')
    global_acronym = models.CharField(max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    usage_count = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'global_organization'


class GoSimilarity(models.Model):
    pk = models.CompositePrimaryKey('source_global_org_id', 'target_global_org_id')
    source_global_org = models.ForeignKey(GlobalOrganization, models.DO_NOTHING)
    target_global_org = models.ForeignKey(GlobalOrganization, models.DO_NOTHING, related_name='gosimilarity_target_global_org_set')
    similarity_percent = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'go_similarity'


class OrgMapping(models.Model):
    id = models.BigAutoField(primary_key=True)
    global_org = models.ForeignKey(GlobalOrganization, models.DO_NOTHING)
    instance_org_id = models.IntegerField(blank=True, null=True)
    instance_org_name = models.CharField(max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS')
    instance_org_acronym = models.CharField(max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    parent_instance_org_id = models.IntegerField(blank=True, null=True)
    fund_name = models.CharField(max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    fund_id = models.IntegerField(blank=True, null=True)
    match_percent = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    risk_level = models.CharField(max_length=10, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    status = models.CharField(max_length=20, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'org_mapping'


class DataSyncLog(models.Model):
    """
    记录每次数据同步的情况
    用于追踪外部数据更新和同步状态
    """
    SYNC_TYPES = [
        ('global_org', 'Global Organization'),
        ('org_mapping', 'Organization Mapping'),
        ('full', 'Full Sync'),
    ]
    
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('no_changes', 'No Changes'),
    ]
    
    sync_id = models.AutoField(primary_key=True)
    sync_type = models.CharField(max_length=50, choices=SYNC_TYPES)
    
    # 时间记录
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # 数据变化统计
    records_fetched = models.IntegerField(default=0)
    records_created = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)
    records_deleted = models.IntegerField(default=0)
    
    # 数据指纹（用于检测变化）
    data_checksum = models.CharField(max_length=64, null=True, blank=True)
    
    # 状态和错误信息
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    error_message = models.TextField(blank=True)
    
    # 触发方式
    triggered_by = models.CharField(max_length=50, default='auto')  # 'auto' / 'manual' / 'api'
    
    class Meta:
        db_table = 'data_sync_log'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['-started_at']),
            models.Index(fields=['sync_type', '-started_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Sync {self.sync_id}: {self.sync_type} - {self.status}"
    
    @property
    def duration_seconds(self):
        """计算同步耗时（秒）"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
