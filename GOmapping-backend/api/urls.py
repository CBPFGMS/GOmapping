from django.urls import path
from . import views

urlpatterns = [
    path('go-summary/', views.go_summary),
    path('go-detail/<int:go_id>/', views.go_detail),
    path('org-mappings/<int:go_id>/', views.org_mapping),
]