# api/serializers.py

from rest_framework import serializers
from blog.models import Post, Category

class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for the Category model.
    """
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent']

class PostSerializer(serializers.ModelSerializer):
    """
    Serializer for the Post model, including nested category details.
    """
    # Use CategorySerializer to display full category details instead of just IDs
    categories = CategorySerializer(many=True, read_only=True)
    # Display the author's username for better context
    author = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'author', 'content', 'excerpt', 
            'featured_image', 'categories', 'read_time', 'view_count', 
            'is_featured', 'status', 'created_at', 'updated_at'
        ]
        # Make certain fields read-only as they are auto-generated
        read_only_fields = ['read_time', 'view_count', 'author']