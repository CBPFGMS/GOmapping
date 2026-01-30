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
    
    # Merge Decision API
    path('merge-decisions/', views.list_merge_decisions, name='list_merge_decisions'),
    path('merge-decisions/create/', views.create_merge_decision, name='create_merge_decision'),
    path('merge-decisions/<int:decision_id>/', views.delete_merge_decision, name='delete_merge_decision'),
    path('merge-decisions/<int:decision_id>/status/', views.update_merge_decision_status, name='update_merge_decision_status'),
]