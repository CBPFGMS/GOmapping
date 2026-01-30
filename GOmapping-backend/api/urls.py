from django.urls import path
from . import views

urlpatterns = [
    path('go-summary/', views.go_summary),
    path('go-detail/<int:go_id>/', views.go_detail),
    path('org-mappings/<int:go_id>/', views.org_mapping),
    path('mapping-dashboard/', views.mapping_dashboard),
    path('ai-recommendation/', views.ai_recommendation),
    
    # Data Sync API
    path('sync-status/', views.sync_status, name='sync_status'),
    path('sync-history/', views.sync_history, name='sync_history'),
    path('trigger-sync/', views.trigger_sync, name='trigger_sync'),
    path('check-for-updates/', views.check_for_updates, name='check_for_updates'),
]