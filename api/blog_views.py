# api/views.py

from rest_framework import viewsets, permissions
from blog.models import Post, Category
from .serializers import PostSerializer, CategorySerializer

class PostViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows blog posts to be viewed or edited.
    """
    queryset = Post.objects.filter(status='published')  # Only show published posts
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Allow read-only for anonymous users
    lookup_field = 'slug' # Use the post's slug in the URL instead of its ID

class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows categories to be viewed or edited.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug' # Use the category's slug in the URL