# api/blog_views.py - Blog API Views with Authentication

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q
from blog.models import Post, Category
from .serializers import PostSerializer, CategorySerializer
from .authentication import CombinedAPIAuthentication, APIClientUser, get_authenticated_client
from .utils import APIKeyValidator, log_api_usage
import time
import logging

logger = logging.getLogger(__name__)


class APIClientPermission(permissions.BasePermission):
    """
    Custom permission class for API clients
    """
    
    def has_permission(self, request, view):
        # Allow GET requests for clients with read permission
        if request.method in permissions.SAFE_METHODS:
            if isinstance(request.user, APIClientUser):
                return request.user.client.can_read_posts
            return True  # Allow anonymous read access
        
        # For write operations, require authenticated API client
        if not isinstance(request.user, APIClientUser):
            return False
        
        client = request.user.client
        
        # Check specific permissions based on action
        if request.method == 'POST':
            return client.can_write_posts
        elif request.method in ['PUT', 'PATCH']:
            return client.can_write_posts
        elif request.method == 'DELETE':
            return client.can_delete_posts
        
        return False
    
    def has_object_permission(self, request, view, obj):
        # Allow read access for clients with read permission
        if request.method in permissions.SAFE_METHODS:
            if isinstance(request.user, APIClientUser):
                return request.user.client.can_read_posts
            return True
        
        # For write operations, check permissions
        if isinstance(request.user, APIClientUser):
            client = request.user.client
            
            if request.method in ['PUT', 'PATCH']:
                return client.can_write_posts
            elif request.method == 'DELETE':
                return client.can_delete_posts
        
        return False


class CategoryPermission(permissions.BasePermission):
    """
    Custom permission class for category management
    """
    
    def has_permission(self, request, view):
        # Allow GET requests for clients with read permission
        if request.method in permissions.SAFE_METHODS:
            if isinstance(request.user, APIClientUser):
                return request.user.client.can_read_posts
            return True
        
        # For write operations, require category management permission
        if isinstance(request.user, APIClientUser):
            return request.user.client.can_manage_categories
        
        return False


class PostViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows blog posts to be viewed or edited.
    Requires API authentication for write operations.
    """
    serializer_class = PostSerializer
    authentication_classes = [CombinedAPIAuthentication]
    permission_classes = [APIClientPermission]
    lookup_field = 'slug'
    
    def get_queryset(self):
        """
        Filter posts based on client permissions and status
        """
        queryset = Post.objects.all()
        
        # If user is an API client, apply filtering based on permissions
        if isinstance(self.request.user, APIClientUser):
            client = self.request.user.client
            if client.can_read_posts:
                # API clients can see published posts by default
                # Add draft access if they have write permissions
                if client.can_write_posts:
                    queryset = queryset.filter(Q(status='published') | Q(status='draft'))
                else:
                    queryset = queryset.filter(status='published')
            else:
                queryset = queryset.none()
        else:
            # Anonymous users only see published posts
            queryset = queryset.filter(status='published')
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        """
        Set the author when creating a post via API
        """
        # For API clients, we need to set a default author
        # You might want to create a system user for API-created posts
        # or associate posts with the client somehow
        if isinstance(self.request.user, APIClientUser):
            # Try to get the client's creator as author, or use a default
            author = self.request.user.client.created_by
            serializer.save(author=author)
        else:
            serializer.save(author=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Override create to add logging"""
        start_time = time.time()
        response = super().create(request, *args, **kwargs)
        
        # Log API usage
        if isinstance(request.user, APIClientUser):
            log_api_usage(
                client=request.user.client,
                endpoint=request.path,
                method=request.method,
                status_code=response.status_code,
                response_time=time.time() - start_time,
                request=request,
                api_key=request.user.api_key
            )
        
        return response
    
    def update(self, request, *args, **kwargs):
        """Override update to add logging"""
        start_time = time.time()
        response = super().update(request, *args, **kwargs)
        
        # Log API usage
        if isinstance(request.user, APIClientUser):
            log_api_usage(
                client=request.user.client,
                endpoint=request.path,
                method=request.method,
                status_code=response.status_code,
                response_time=time.time() - start_time,
                request=request,
                api_key=request.user.api_key
            )
        
        return response
    
    def destroy(self, request, *args, **kwargs):
        """Override destroy to add logging"""
        start_time = time.time()
        response = super().destroy(request, *args, **kwargs)
        
        # Log API usage
        if isinstance(request.user, APIClientUser):
            log_api_usage(
                client=request.user.client,
                endpoint=request.path,
                method=request.method,
                status_code=response.status_code,
                response_time=time.time() - start_time,
                request=request,
                api_key=request.user.api_key
            )
        
        return response
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured posts"""
        featured_posts = self.get_queryset().filter(is_featured=True)[:5]
        serializer = self.get_serializer(featured_posts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get posts by category slug"""
        category_slug = request.query_params.get('category')
        if not category_slug:
            return Response(
                {'error': 'Category parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        posts = self.get_queryset().filter(categories__slug=category_slug)
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows categories to be viewed or edited.
    Requires API authentication and category management permission for write operations.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    authentication_classes = [CombinedAPIAuthentication]
    permission_classes = [CategoryPermission]
    lookup_field = 'slug'
    
    def create(self, request, *args, **kwargs):
        """Override create to add logging"""
        start_time = time.time()
        response = super().create(request, *args, **kwargs)
        
        # Log API usage
        if isinstance(request.user, APIClientUser):
            log_api_usage(
                client=request.user.client,
                endpoint=request.path,
                method=request.method,
                status_code=response.status_code,
                response_time=time.time() - start_time,
                request=request,
                api_key=request.user.api_key
            )
        
        return response
    
    def update(self, request, *args, **kwargs):
        """Override update to add logging"""
        start_time = time.time()
        response = super().update(request, *args, **kwargs)
        
        # Log API usage
        if isinstance(request.user, APIClientUser):
            log_api_usage(
                client=request.user.client,
                endpoint=request.path,
                method=request.method,
                status_code=response.status_code,
                response_time=time.time() - start_time,
                request=request,
                api_key=request.user.api_key
            )
        
        return response
    
    def destroy(self, request, *args, **kwargs):
        """Override destroy to add logging"""
        start_time = time.time()
        response = super().destroy(request, *args, **kwargs)
        
        # Log API usage
        if isinstance(request.user, APIClientUser):
            log_api_usage(
                client=request.user.client,
                endpoint=request.path,
                method=request.method,
                status_code=response.status_code,
                response_time=time.time() - start_time,
                request=request,
                api_key=request.user.api_key
            )
        
        return response
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get categories in tree structure"""
        # Get root categories (no parent)
        root_categories = Category.objects.filter(parent=None)
        
        def build_tree(categories):
            tree = []
            for category in categories:
                category_data = CategorySerializer(category).data
                # Get subcategories
                subcategories = Category.objects.filter(parent=category)
                if subcategories.exists():
                    category_data['subcategories'] = build_tree(subcategories)
                tree.append(category_data)
            return tree
        
        tree = build_tree(root_categories)
        return Response(tree)