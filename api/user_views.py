# api/user_views.py - User API Views

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.models import User
from users.models import Profile
from .serializers import UserSerializer, PublicUserSerializer
from .authentication import CombinedAPIAuthentication, APIClientUser
import logging

logger = logging.getLogger(__name__)


class UserPermission(permissions.BasePermission):
    """
    Custom permission class for user access
    """
    
    def has_permission(self, request, view):
        # Only allow GET requests
        if request.method not in permissions.SAFE_METHODS:
            return False
        
        # Check if user is an API client with user access permission
        if isinstance(request.user, APIClientUser):
            return request.user.client.can_access_users
        
        # Allow anonymous access to public user data
        return True
    
    def has_object_permission(self, request, view, obj):
        # Only allow GET requests
        if request.method not in permissions.SAFE_METHODS:
            return False
        
        # Check if user is an API client with user access permission
        if isinstance(request.user, APIClientUser):
            return request.user.client.can_access_users
        
        # Allow anonymous access to public user data
        return True


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for user information with privacy controls
    Read-only access only
    """
    queryset = User.objects.filter(is_active=True)
    authentication_classes = [CombinedAPIAuthentication]
    permission_classes = [UserPermission]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on client permissions"""
        if isinstance(self.request.user, APIClientUser) and self.request.user.client.can_access_users:
            return UserSerializer
        return PublicUserSerializer
    
    def get_queryset(self):
        """Filter users based on privacy settings and client permissions"""
        queryset = User.objects.filter(is_active=True)
        
        # If not an authenticated API client with user access, only show users with public profiles
        if not (isinstance(self.request.user, APIClientUser) and self.request.user.client.can_access_users):
            # Filter to only users with public profiles
            queryset = queryset.filter(profile__is_profile_public=True)
        
        return queryset.order_by('username')
    
    @action(detail=False, methods=['get'])
    def authors(self, request):
        """Get users who have authored blog posts"""
        from blog.models import Post
        
        # Get users who have published posts
        author_ids = Post.objects.filter(status='published').values_list('author_id', flat=True).distinct()
        authors = self.get_queryset().filter(id__in=author_ids)
        
        serializer = self.get_serializer(authors, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def posts(self, request, pk=None):
        """Get posts by a specific user"""
        from blog.models import Post
        from .serializers import PostSerializer
        
        user = self.get_object()
        
        # Get published posts by this user
        posts = Post.objects.filter(author=user, status='published').order_by('-created_at')
        
        # Paginate results
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = PostSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user statistics"""
        from blog.models import Post
        
        # Only allow for authenticated API clients
        if not (isinstance(request.user, APIClientUser) and request.user.client.can_access_users):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        stats = {
            'total_users': User.objects.filter(is_active=True).count(),
            'users_with_posts': User.objects.filter(
                blog_posts__status='published'
            ).distinct().count(),
            'users_with_public_profiles': User.objects.filter(
                profile__is_profile_public=True
            ).count(),
        }
        
        return Response(stats)