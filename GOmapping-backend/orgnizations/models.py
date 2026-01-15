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
