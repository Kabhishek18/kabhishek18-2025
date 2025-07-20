# core/urls.py

from django.urls import path
from .views import (
    PageRequest, custom_404, health_dashboard_view, 
    HealthDashboardAPIView, HealthMetricsAPIView, SystemAlertsAPIView
)

# Define the app namespace
app_name = 'core'

urlpatterns = [
    # Homepage - exact match for empty path
    path('', PageRequest.as_view(), name="home_page"),
    
    # Health Dashboard URLs
    path('dashboard/health/', health_dashboard_view, name='health_dashboard'),
    path('api/health/dashboard/', HealthDashboardAPIView.as_view(), name='health_dashboard_api'),
    path('api/health/metrics/', HealthMetricsAPIView.as_view(), name='health_metrics_api'),
    path('api/health/metrics/<str:metric_type>/', HealthMetricsAPIView.as_view(), name='health_metrics_type_api'),
    path('api/health/alerts/', SystemAlertsAPIView.as_view(), name='system_alerts_api'),
    
    # Generic catch-all for custom pages - MUST be last
    path('<slug:slug>/', PageRequest.as_view(), name="generic_page"),
]