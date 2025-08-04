"""
Content Discovery Service for Blog Posts

This service provides functionality for content discovery features including
featured posts, related posts, popular posts, and view tracking.
"""

from django.db.models import F, Q, Count
from django.utils import timezone
from datetime import timedelta
from typing import List, Optional
from ..models import Post, Tag


class ContentDiscoveryService:
    """Service class for content discovery and recommendation features"""
    
    @classmethod
    def get_featured_posts(cls, limit: int = 3) -> List[Post]:
        """
        Get featured posts for homepage display.
        
        Args:
            limit: Maximum number of featured posts to return
            
        Returns:
            List of featured Post objects
        """
        return Post.objects.filter(
            status='published',
            is_featured=True
        ).select_related('author').prefetch_related('categories', 'tags').order_by('-created_at')[:limit]
    
    @classmethod
    def get_related_posts(cls, post: Post, limit: int = 3) -> List[Post]:
        """
        Get related posts based on tags, categories, and content similarity.
        
        Args:
            post: The current post to find related posts for
            limit: Maximum number of related posts to return
            
        Returns:
            List of related Post objects
        """
        # Get posts with similar tags and categories
        related_posts = Post.objects.filter(
            status='published'
        ).exclude(
            id=post.id
        ).select_related('author').prefetch_related('categories', 'tags')
        
        # Filter by same categories or tags
        category_ids = list(post.categories.values_list('id', flat=True))
        tag_ids = list(post.tags.values_list('id', flat=True))
        
        if category_ids or tag_ids:
            related_posts = related_posts.filter(
                Q(categories__id__in=category_ids) | Q(tags__id__in=tag_ids)
            ).distinct()
        
        # Order by relevance (posts with more matching tags/categories first)
        related_posts = related_posts.annotate(
            relevance_score=Count('categories', filter=Q(categories__id__in=category_ids)) +
                          Count('tags', filter=Q(tags__id__in=tag_ids))
        ).order_by('-relevance_score', '-created_at')
        
        return list(related_posts[:limit])
    
    @classmethod
    def get_popular_posts(cls, timeframe: str = 'week', limit: int = 5) -> List[Post]:
        """
        Get popular posts based on view count within a timeframe.
        
        Args:
            timeframe: Time period ('week', 'month', 'year', 'all')
            limit: Maximum number of popular posts to return
            
        Returns:
            List of popular Post objects
        """
        posts = Post.objects.filter(status='published').select_related('author')
        
        # Filter by timeframe
        if timeframe != 'all':
            now = timezone.now()
            if timeframe == 'week':
                start_date = now - timedelta(days=7)
            elif timeframe == 'month':
                start_date = now - timedelta(days=30)
            elif timeframe == 'year':
                start_date = now - timedelta(days=365)
            else:
                start_date = now - timedelta(days=7)  # Default to week
            
            posts = posts.filter(created_at__gte=start_date)
        
        return list(posts.order_by('-view_count', '-created_at')[:limit])
    
    @classmethod
    def get_trending_tags(cls, limit: int = 10) -> List[Tag]:
        """
        Get trending tags based on recent post activity.
        
        Args:
            limit: Maximum number of trending tags to return
            
        Returns:
            List of trending Tag objects
        """
        # Get tags from posts created in the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        return list(Tag.objects.annotate(
            recent_post_count=Count(
                'posts',
                filter=Q(posts__status='published', posts__created_at__gte=thirty_days_ago)
            )
        ).filter(recent_post_count__gt=0).order_by('-recent_post_count', 'name')[:limit])
    
    @classmethod
    def update_view_count(cls, post: Post) -> None:
        """
        Increment the view count for a post.
        
        Args:
            post: Post object to update view count for
        """
        Post.objects.filter(id=post.id).update(view_count=F('view_count') + 1)