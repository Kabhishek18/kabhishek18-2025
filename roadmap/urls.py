"""
URL configuration for roadmap app
"""
from django.urls import path, include
from . import views

app_name = 'roadmap'

# API v1 patterns
v1_patterns = [
    # Resume parsing endpoint
    path('parse-resume/', views.ResumeParseView.as_view(), name='parse-resume'),
    
    # Health check endpoint
    path('health/', views.HealthCheckView.as_view(), name='health-check'),
    
    # Web form for resume parsing
    path('upload/', views.ResumeUploadFormView.as_view(), name='upload-form'),
]

urlpatterns = [
    # Current version (v1) - default endpoints without version prefix
    path('', include((v1_patterns, 'roadmap'), namespace='v1')),
    
    # Explicit versioned endpoints
    path('v1/', include((v1_patterns, 'roadmap'), namespace='v1-explicit')),
]