# api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .blog_views import PostViewSet, CategoryViewSet
from .auth_views import (
    APIClientViewSet, APIKeyViewSet, register_client, generate_api_key,
    validate_authentication, get_api_endpoints, get_client_usage
)
from .user_views import UserViewSet
from .core_views import PageViewSet, ComponentViewSet, TemplateViewSet

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'users', UserViewSet, basename='user')
router.register(r'pages', PageViewSet, basename='page')
router.register(r'components', ComponentViewSet, basename='component')
router.register(r'templates', TemplateViewSet, basename='template')
router.register(r'clients', APIClientViewSet, basename='apiclient')
router.register(r'keys', APIKeyViewSet, basename='apikey')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    # Main API endpoints
    path('', include(router.urls)),
    
    # Authentication endpoints
    path('auth/client/register/', register_client, name='register-client'),
    path('auth/key/generate/<uuid:client_id>/', generate_api_key, name='generate-api-key'),
    path('auth/validate/', validate_authentication, name='validate-authentication'),
    
    # Discovery and usage endpoints
    path('endpoints/', get_api_endpoints, name='api-endpoints'),
    path('usage/<uuid:client_id>/', get_client_usage, name='client-usage'),
]