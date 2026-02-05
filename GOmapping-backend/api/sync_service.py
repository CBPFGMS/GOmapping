"""
智能数据同步服务
提供数据同步、变化检测、状态管理等功能
"""

import hashlib
import requests
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction

from orgnizations.models import DataSyncLog


class SmartDataSyncService:
    """智能数据同步服务"""
    
    # API 配置
    ORG_SUMMARY_URL = (
        "https://cbpfapi.unocha.org/vo3/odata/GlobalGenericDataExtract"
        "?SPCode=PF_ORG_SUMMARY&PoolfundCodeAbbrv=&$format=csv"
    )
    GLOBAL_ORG_URL = (
        "https://cbpfapi.unocha.org/vo3/odata/GlobalGenericDataExtract"
        "?SPCode=PF_GLOBAL_ORG&PoolfundCodeAbbrv=&$format=csv"
    )
    
    # 认证信息
    DEFAULT_USER = "35e38643-0226-4f33-81e3-c09f46a2136b"
    DEFAULT_PASSWORD = "trigyn123"
    
    # 同步间隔（分钟）
    MIN_SYNC_INTERVAL = 30
    
    def __init__(self, auth=None):
        """初始化服务"""
        if auth is None:
            auth = (self.DEFAULT_USER, self.DEFAULT_PASSWORD)
        self.auth = auth
    
    def should_sync(self, sync_type='org_mapping', force=False):
        """
        判断是否需要同步
        
        Args:
            sync_type: 同步类型 ('org_mapping' / 'global_org' / 'full')
            force: 是否强制同步（忽略时间和指纹检查）
        
        Returns:
            (should_sync: bool, reason: str, last_sync: DataSyncLog or None)
        """
        if force:
            return True, "force_sync", None
        
        # Level 1: 检查时间间隔
        last_sync = DataSyncLog.objects.filter(
            sync_type=sync_type,
            status__in=['success', 'no_changes']
        ).first()
        
        if last_sync and last_sync.completed_at:
            time_since_sync = timezone.now() - last_sync.completed_at
            if time_since_sync < timedelta(minutes=self.MIN_SYNC_INTERVAL):
                minutes_ago = time_since_sync.total_seconds() / 60
                return False, f"too_soon ({minutes_ago:.1f} minutes ago)", last_sync
        
        # Level 2: 检查数据指纹
        try:
            current_checksum = self.get_data_checksum(sync_type)
            last_checksum = last_sync.data_checksum if last_sync else None
            
            if current_checksum and current_checksum == last_checksum:
                return False, "no_changes", last_sync
        except Exception as e:
            # 如果检查失败，继续同步（保守策略）
            print(f"Warning: Unable to check data checksum: {e}")
        
        # Level 3: 需要同步
        return True, "should_sync", last_sync
    
    def get_data_checksum(self, sync_type, sample_size=10240):
        """
        获取数据的快速指纹（只读取前 sample_size 字节）
        
        Args:
            sync_type: 同步类型
            sample_size: 采样大小（字节）
        
        Returns:
            str: MD5 checksum
        """
        url = self.ORG_SUMMARY_URL if sync_type == 'org_mapping' else self.GLOBAL_ORG_URL
        
        try:
            response = requests.get(url, auth=self.auth, stream=True, timeout=30)
            response.raise_for_status()
            
            # 只读取前 sample_size 字节
            sample_data = response.raw.read(sample_size)
            checksum = hashlib.md5(sample_data).hexdigest()
            
            return checksum
        except Exception as e:
            print(f"Error getting checksum: {e}")
            return None
    
    def sync_all(self, triggered_by='manual', force=False):
        """
        执行完整同步（Global Org + Org Mapping）
        
        Args:
            triggered_by: 触发方式 ('manual' / 'auto' / 'api')
            force: 是否强制同步
        
        Returns:
            dict: 同步结果
        """
        results = {
            'global_org': None,
            'org_mapping': None,
            'overall_status': 'success',
            'message': ''
        }
        
        # 1. 同步 Global Organizations
        try:
            results['global_org'] = self.sync_global_orgs(triggered_by, force)
        except Exception as e:
            results['global_org'] = {'error': str(e)}
            results['overall_status'] = 'partial_failed'
        
        # 2. 同步 Org Mappings
        try:
            results['org_mapping'] = self.sync_org_mappings(triggered_by, force)
        except Exception as e:
            results['org_mapping'] = {'error': str(e)}
            results['overall_status'] = 'failed'
        
        # 3. 如果有数据变化，清除缓存
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
        """同步 Global Organizations"""
        return self._sync_data(
            sync_type='global_org',
            url=self.GLOBAL_ORG_URL,
            upsert_function='upsert_global_orgs',
            triggered_by=triggered_by,
            force=force
        )
    
    def sync_org_mappings(self, triggered_by='manual', force=False):
        """同步 Organization Mappings"""
        return self._sync_data(
            sync_type='org_mapping',
            url=self.ORG_SUMMARY_URL,
            upsert_function='upsert_org_mappings',
            triggered_by=triggered_by,
            force=force
        )
    
    def _sync_data(self, sync_type, url, upsert_function, triggered_by='manual', force=False):
        """
        通用同步逻辑
        
        Args:
            sync_type: 同步类型
            url: API URL
            upsert_function: 数据导入函数名
            triggered_by: 触发方式
            force: 是否强制同步
        
        Returns:
            dict: 同步结果
        """
        # 检查是否需要同步
        should_sync, reason, last_sync = self.should_sync(sync_type, force)
        
        if not should_sync:
            return {
                'synced': False,
                'reason': reason,
                'last_sync_time': last_sync.completed_at if last_sync else None,
                'message': f'Skipped: {reason}'
            }
        
        # 创建同步日志
        log = DataSyncLog.objects.create(
            sync_type=sync_type,
            status='running',
            triggered_by=triggered_by
        )
        
        try:
            # 导入同步脚本
            from scripts.sync_cbpf_data import fetch_csv_rows, upsert_global_orgs, upsert_org_mappings
            
            # 获取数据
            rows = fetch_csv_rows(url, auth=self.auth, timeout=120)
            log.records_fetched = len(rows)
            
            # 执行 upsert
            if upsert_function == 'upsert_global_orgs':
                created, updated = upsert_global_orgs(rows)
                total = len(rows)
            else:
                total, created, updated = upsert_org_mappings(rows)
            
            # 获取数据指纹
            checksum = self.get_data_checksum(sync_type)
            
            # 更新日志
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
            # 记录错误
            log.status = 'failed'
            log.error_message = str(e)
            log.completed_at = timezone.now()
            log.save()
            
            raise Exception(f"Sync failed: {str(e)}")
    
    def get_sync_status(self, sync_type=None):
        """
        获取同步状态
        
        Args:
            sync_type: 可选，指定同步类型
        
        Returns:
            dict: 同步状态信息
        """
        query = DataSyncLog.objects.all()
        if sync_type:
            query = query.filter(sync_type=sync_type)
        
        last_sync = query.filter(status__in=['success', 'no_changes']).first()
        last_attempt = query.first()
        running_sync = query.filter(status='running').first()
        
        # 统计最近24小时的同步
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
        获取同步历史记录
        
        Args:
            limit: 返回记录数
            sync_type: 可选，过滤同步类型
        
        Returns:
            list: 同步记录列表
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
