# core/urls.py

from django.urls import path
from .views import PageRequest, custom_404

# Define the app namespace
app_name = 'core'

urlpatterns = [
    # Homepage - exact match for empty path
    path('', PageRequest.as_view(), name="home_page"),
    
    # Generic catch-all for custom pages - MUST be last
    path('<slug:slug>/', PageRequest.as_view(), name="generic_page"),
]