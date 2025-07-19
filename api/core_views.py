# api/core_views.py - Core Content API Views

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import models
from core.models import Page, Component, Template
from .serializers import PageSerializer, PublicPageSerializer, ComponentSerializer, TemplateSerializer
from .authentication import CombinedAPIAuthentication, APIClientUser
import logging

logger = logging.getLogger(__name__)


class CoreContentPermission(permissions.BasePermission):
    """
    Custom permission class for core content access
    """
    
    def has_permission(self, request, view):
        # Only allow GET requests for now
        if request.method not in permissions.SAFE_METHODS:
            return False
        
        # Check if user is an API client with page access permission
        if isinstance(request.user, APIClientUser):
            return request.user.client.can_access_pages
        
        # Allow anonymous access to published pages
        return True
    
    def has_object_permission(self, request, view, obj):
        # Only allow GET requests
        if request.method not in permissions.SAFE_METHODS:
            return False
        
        # Check if user is an API client with page access permission
        if isinstance(request.user, APIClientUser):
            return request.user.client.can_access_pages
        
        # Allow anonymous access to published pages
        return True


class PageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for page content
    Read-only access with authentication support
    """
    authentication_classes = [CombinedAPIAuthentication]
    permission_classes = [CoreContentPermission]
    lookup_field = 'slug'
    
    def get_serializer_class(self):
        """Return appropriate serializer based on client permissions"""
        if isinstance(self.request.user, APIClientUser) and self.request.user.client.can_access_pages:
            return PageSerializer
        return PublicPageSerializer
    
    def get_queryset(self):
        """Filter pages based on publication status and client permissions"""
        queryset = Page.objects.all()
        
        # If not an authenticated API client, only show published pages
        if not (isinstance(self.request.user, APIClientUser) and self.request.user.client.can_access_pages):
            queryset = queryset.filter(is_published=True)
        
        return queryset.order_by('title')
    
    @action(detail=False, methods=['get'])
    def homepage(self, request):
        """Get the homepage"""
        try:
            homepage = Page.objects.get(is_homepage=True, is_published=True)
            serializer = self.get_serializer(homepage)
            return Response(serializer.data)
        except Page.DoesNotExist:
            return Response(
                {'error': 'Homepage not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def published(self, request):
        """Get all published pages"""
        published_pages = Page.objects.filter(is_published=True).order_by('title')
        serializer = self.get_serializer(published_pages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def template_content(self, request, slug=None):
        """Get page with full template content rendered"""
        page = self.get_object()
        
        if not page.template:
            return Response(
                {'error': 'Page has no template'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get template with all components
        template_data = TemplateSerializer(page.template).data
        
        # Combine page data with template
        page_data = self.get_serializer(page).data
        page_data['template_content'] = template_data
        
        return Response(page_data)


class ComponentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for component data
    Read-only access with authentication support
    """
    queryset = Component.objects.all()
    serializer_class = ComponentSerializer
    authentication_classes = [CombinedAPIAuthentication]
    permission_classes = [CoreContentPermission]
    lookup_field = 'slug'
    
    def get_queryset(self):
        """Return all components ordered by name"""
        return Component.objects.all().order_by('name')
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search components by name or content"""
        query = request.query_params.get('q', '')
        if not query:
            return Response(
                {'error': 'Query parameter "q" is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        components = self.get_queryset().filter(
            models.Q(name__icontains=query) | 
            models.Q(content__icontains=query)
        )
        
        serializer = self.get_serializer(components, many=True)
        return Response(serializer.data)


class TemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for template information
    Read-only access with authentication support
    """
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    authentication_classes = [CombinedAPIAuthentication]
    permission_classes = [CoreContentPermission]
    
    def get_queryset(self):
        """Return all templates with prefetched components"""
        return Template.objects.prefetch_related('files').order_by('name')
    
    @action(detail=True, methods=['get'])
    def components(self, request, pk=None):
        """Get all components for a specific template"""
        template = self.get_object()
        components = template.files.all().order_by('name')
        
        serializer = ComponentSerializer(components, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get template usage statistics"""
        # Only allow for authenticated API clients
        if not (isinstance(request.user, APIClientUser) and request.user.client.can_access_pages):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        stats = {
            'total_templates': Template.objects.count(),
            'total_components': Component.objects.count(),
            'templates_in_use': Template.objects.filter(page__isnull=False).distinct().count(),
            'unused_templates': Template.objects.filter(page__isnull=True).count(),
        }
        
        return Response(stats)