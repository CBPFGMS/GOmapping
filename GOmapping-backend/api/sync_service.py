"""
Smart data synchronization service.
Provides data sync, change detection, and sync status management.
"""

import hashlib
import requests
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction

from orgnizations.models import DataSyncLog


class SmartDataSyncService:
    """Smart data synchronization service."""
    
    # API configuration
    ORG_SUMMARY_URL = (
        "https://cbpfapi.unocha.org/vo3/odata/GlobalGenericDataExtract"
        "?SPCode=PF_ORG_SUMMARY&PoolfundCodeAbbrv=&$format=csv"
    )
    GLOBAL_ORG_URL = (
        "https://cbpfapi.unocha.org/vo3/odata/GlobalGenericDataExtract"
        "?SPCode=PF_GLOBAL_ORG&PoolfundCodeAbbrv=&$format=csv"
    )
    
    # Authentication settings
    DEFAULT_USER = "35e38643-0226-4f33-81e3-c09f46a2136b"
    DEFAULT_PASSWORD = "trigyn123"
    
    # Minimum sync interval (minutes)
    MIN_SYNC_INTERVAL = 30
    
    def __init__(self, auth=None):
        """Initialize the service."""
        if auth is None:
            auth = (self.DEFAULT_USER, self.DEFAULT_PASSWORD)
        self.auth = auth
    
    def should_sync(self, sync_type='org_mapping', force=False):
        """
        Determine whether synchronization is needed.
        
        Args:
            sync_type: Sync type ('org_mapping' / 'global_org' / 'full')
            force: Force sync (skip time and checksum checks)
        
        Returns:
            (should_sync: bool, reason: str, last_sync: DataSyncLog or None)
        """
        if force:
            return True, "force_sync", None
        
        # Level 1: Check minimum time interval
        last_sync = DataSyncLog.objects.filter(
            sync_type=sync_type,
            status__in=['success', 'no_changes']
        ).first()
        
        if last_sync and last_sync.completed_at:
            time_since_sync = timezone.now() - last_sync.completed_at
            if time_since_sync < timedelta(minutes=self.MIN_SYNC_INTERVAL):
                minutes_ago = time_since_sync.total_seconds() / 60
                return False, f"too_soon ({minutes_ago:.1f} minutes ago)", last_sync
        
        # Level 2: Check data checksum
        try:
            current_checksum = self.get_data_checksum(sync_type)
            last_checksum = last_sync.data_checksum if last_sync else None
            
            if current_checksum and current_checksum == last_checksum:
                return False, "no_changes", last_sync
        except Exception as e:
            # If checksum check fails, continue syncing (conservative strategy)
            print(f"Warning: Unable to check data checksum: {e}")
        
        # Level 3: Sync is required
        return True, "should_sync", last_sync
    
    def get_data_checksum(self, sync_type, sample_size=10240):
        """
        Get a quick data checksum (read only the first sample_size bytes).
        
        Args:
            sync_type: Sync type
            sample_size: Sample size in bytes
        
        Returns:
            str: MD5 checksum
        """
        url = self.ORG_SUMMARY_URL if sync_type == 'org_mapping' else self.GLOBAL_ORG_URL
        
        try:
            response = requests.get(url, auth=self.auth, stream=True, timeout=30)
            response.raise_for_status()
            
            # Read only the first sample_size bytes
            sample_data = response.raw.read(sample_size)
            checksum = hashlib.md5(sample_data).hexdigest()
            
            return checksum
        except Exception as e:
            print(f"Error getting checksum: {e}")
            return None
    
    def sync_all(self, triggered_by='manual', force=False):
        """
        Run a full synchronization (Global Org + Org Mapping).
        
        Args:
            triggered_by: Trigger source ('manual' / 'auto' / 'api')
            force: Whether to force sync
        
        Returns:
            dict: Sync results
        """
        results = {
            'global_org': None,
            'org_mapping': None,
            'overall_status': 'success',
            'message': ''
        }
        
        # 1. Sync Global Organizations
        try:
            results['global_org'] = self.sync_global_orgs(triggered_by, force)
        except Exception as e:
            results['global_org'] = {'error': str(e)}
            results['overall_status'] = 'partial_failed'
        
        # 2. Sync Org Mappings
        try:
            results['org_mapping'] = self.sync_org_mappings(triggered_by, force)
        except Exception as e:
            results['org_mapping'] = {'error': str(e)}
            results['overall_status'] = 'failed'
        
        # 3. Clear cache if any data changed
        total_changes = 0
        for sync_result in [results['global_org'], results['org_mapping']]:
            if sync_result and not sync_result.get('error'):
                total_changes += sync_result.get('created', 0) + sync_result.get('updated', 0)
        
        if total_changes > 0:
            cache.delete('go_summary_data')
            results['message'] = f'Synced successfully. {total_changes} records changed. Cache cleared.'
        else:
            results['message'] = 'Sync completed. No changes detected.'
        
        return results
    
    def sync_global_orgs(self, triggered_by='manual', force=False):
        """Sync Global Organizations."""
        return self._sync_data(
            sync_type='global_org',
            url=self.GLOBAL_ORG_URL,
            upsert_function='upsert_global_orgs',
            triggered_by=triggered_by,
            force=force
        )
    
    def sync_org_mappings(self, triggered_by='manual', force=False):
        """Sync Organization Mappings."""
        return self._sync_data(
            sync_type='org_mapping',
            url=self.ORG_SUMMARY_URL,
            upsert_function='upsert_org_mappings',
            triggered_by=triggered_by,
            force=force
        )
    
    def _sync_data(self, sync_type, url, upsert_function, triggered_by='manual', force=False):
        """
        Generic synchronization workflow.
        
        Args:
            sync_type: Sync type
            url: API URL
            upsert_function: Upsert function name
            triggered_by: Trigger source
            force: Whether to force sync
        
        Returns:
            dict: Sync results
        """
        # Check if sync is needed
        should_sync, reason, last_sync = self.should_sync(sync_type, force)
        
        if not should_sync:
            return {
                'synced': False,
                'reason': reason,
                'last_sync_time': last_sync.completed_at if last_sync else None,
                'message': f'Skipped: {reason}'
            }
        
        # Create sync log
        log = DataSyncLog.objects.create(
            sync_type=sync_type,
            status='running',
            triggered_by=triggered_by
        )
        
        try:
            # Import sync helpers
            from scripts.sync_cbpf_data import fetch_csv_rows, upsert_global_orgs, upsert_org_mappings
            
            # Fetch data
            rows = fetch_csv_rows(url, auth=self.auth, timeout=120)
            log.records_fetched = len(rows)
            
            # Execute upsert
            if upsert_function == 'upsert_global_orgs':
                created, updated = upsert_global_orgs(rows)
                total = len(rows)
            else:
                total, created, updated = upsert_org_mappings(rows)
            
            # Calculate data checksum
            checksum = self.get_data_checksum(sync_type)
            
            # Update sync log
            log.records_created = created
            log.records_updated = updated
            log.data_checksum = checksum
            log.status = 'success' if (created > 0 or updated > 0) else 'no_changes'
            log.completed_at = timezone.now()
            log.save()
            
            return {
                'synced': True,
                'sync_id': log.sync_id,
                'fetched': total,
                'created': created,
                'updated': updated,
                'duration': log.duration_seconds,
                'message': f'Successfully synced {total} records: {created} created, {updated} updated'
            }
            
        except Exception as e:
            # Record error
            log.status = 'failed'
            log.error_message = str(e)
            log.completed_at = timezone.now()
            log.save()
            
            raise Exception(f"Sync failed: {str(e)}")
    
    def get_sync_status(self, sync_type=None):
        """
        Get synchronization status.
        
        Args:
            sync_type: Optional sync type filter
        
        Returns:
            dict: Sync status information
        """
        query = DataSyncLog.objects.all()
        if sync_type:
            query = query.filter(sync_type=sync_type)
        
        last_sync = query.filter(status__in=['success', 'no_changes']).first()
        last_attempt = query.first()
        running_sync = query.filter(status='running').first()
        
        # Aggregate sync stats from the last 24 hours
        one_day_ago = timezone.now() - timedelta(days=1)
        recent_syncs = query.filter(started_at__gte=one_day_ago)
        
        return {
            'is_syncing': running_sync is not None,
            'last_sync': {
                'time': last_sync.completed_at if last_sync else None,
                'status': last_sync.status if last_sync else None,
                'created': last_sync.records_created if last_sync else 0,
                'updated': last_sync.records_updated if last_sync else 0,
                'duration': last_sync.duration_seconds if last_sync else None,
            } if last_sync else None,
            'last_attempt': {
                'time': last_attempt.started_at if last_attempt else None,
                'status': last_attempt.status if last_attempt else None,
                'error': last_attempt.error_message if last_attempt and last_attempt.status == 'failed' else None,
            } if last_attempt else None,
            'recent_24h': {
                'total_syncs': recent_syncs.count(),
                'successful': recent_syncs.filter(status__in=['success', 'no_changes']).count(),
                'failed': recent_syncs.filter(status='failed').count(),
            }
        }
    
    def get_sync_history(self, limit=20, sync_type=None):
        """
        Get synchronization history.
        
        Args:
            limit: Number of records to return
            sync_type: Optional sync type filter
        
        Returns:
            list: Sync history records
        """
        query = DataSyncLog.objects.all()
        if sync_type:
            query = query.filter(sync_type=sync_type)
        
        logs = query[:limit]
        
        return [
            {
                'sync_id': log.sync_id,
                'sync_type': log.sync_type,
                'started_at': log.started_at,
                'completed_at': log.completed_at,
                'status': log.status,
                'records_fetched': log.records_fetched,
                'records_created': log.records_created,
                'records_updated': log.records_updated,
                'duration_seconds': log.duration_seconds,
                'triggered_by': log.triggered_by,
                'error_message': log.error_message if log.status == 'failed' else None,
            }
            for log in logs
        ]
