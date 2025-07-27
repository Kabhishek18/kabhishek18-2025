"""
Performance optimization utilities for blog engagement features.

This module provides caching strategies, database optimization,
and performance monitoring for the blog system.
"""

from django.core.cache import cache
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from typing import Dict, List, Optional, Any, Union
import hashlib
import json
import time
from functools import wraps


class CacheManager:
    """Centralized cache management for blog features"""
    
    # Cache key prefixes
    CACHE_PREFIXES = {
        'popular_posts': 'blog:popular_posts',
        'featured_posts': 'blog:featured_posts',
        'tag_cloud': 'blog:tag_cloud',
        'category_hierarchy': 'blog:category_hierarchy',
        'search_results': 'blog:search',
        'post_views': 'blog:post_views',
        'related_posts': 'blog:related_posts',
        'author_stats': 'blog:author_stats',
        'social_shares': 'blog:social_shares',
    }
    
    # Default cache timeouts (in seconds)
    CACHE_TIMEOUTS = {
        'popular_posts': 3600,      # 1 hour
        'featured_posts': 1800,     # 30 minutes
        'tag_cloud': 7200,          # 2 hours
        'category_hierarchy': 14400, # 4 hours
        'search_results': 900,      # 15 minutes
        'post_views': 300,          # 5 minutes
        'related_posts': 3600,      # 1 hour
        'author_stats': 1800,       # 30 minutes
        'social_shares': 600,       # 10 minutes
    }
    
    @classmethod
    def get_cache_key(cls, prefix: str, *args, **kwargs) -> str:
        """
        Generate a cache key with consistent formatting.
        
        Args:
            prefix: Cache key prefix
            *args: Additional arguments for the key
            **kwargs: Additional keyword arguments for the key
            
        Returns:
            Formatted cache key
        """
        base_key = cls.CACHE_PREFIXES.get(prefix, prefix)
        
        # Add arguments to key
        if args:
            key_parts = [str(arg) for arg in args]
            base_key += ':' + ':'.join(key_parts)
        
        # Add keyword arguments (sorted for consistency)
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            kwargs_str = ':'.join(f"{k}={v}" for k, v in sorted_kwargs)
            base_key += ':' + kwargs_str
        
        # Hash long keys to avoid cache key length limits
        if len(base_key) > 200:
            base_key = f"{prefix}:{hashlib.md5(base_key.encode()).hexdigest()}"
        
        return base_key
    
    @classmethod
    def get(cls, prefix: str, *args, default=None, **kwargs) -> Any:
        """Get value from cache"""
        cache_key = cls.get_cache_key(prefix, *args, **kwargs)
        return cache.get(cache_key, default)
    
    @classmethod
    def set(cls, prefix: str, value: Any, timeout: Optional[int] = None, 
            *args, **kwargs) -> None:
        """Set value in cache"""
        cache_key = cls.get_cache_key(prefix, *args, **kwargs)
        if timeout is None:
            timeout = cls.CACHE_TIMEOUTS.get(prefix, 3600)
        cache.set(cache_key, value, timeout)
    
    @classmethod
    def delete(cls, prefix: str, *args, **kwargs) -> None:
        """Delete value from cache"""
        cache_key = cls.get_cache_key(prefix, *args, **kwargs)
        cache.delete(cache_key)
    
    @classmethod
    def invalidate_pattern(cls, pattern: str) -> None:
        """Invalidate all cache keys matching a pattern"""
        # Note: This requires Redis or a cache backend that supports pattern deletion
        try:
            from django.core.cache.backends.redis import RedisCache
            if isinstance(cache, RedisCache):
                cache.delete_pattern(f"*{pattern}*")
        except ImportError:
            # Fallback: clear entire cache (not ideal but safe)
            cache.clear()


class QueryOptimizer:
    """Database query optimization utilities"""
    
    @staticmethod
    def optimize_post_queryset(queryset):
        """
        Optimize post queryset with proper select_related and prefetch_related.
        
        Args:
            queryset: Post queryset to optimize
            
        Returns:
            Optimized queryset
        """
        return queryset.select_related(
            'author',
            'author__author_profile'
        ).prefetch_related(
            'categories',
            'tags',
            'comments',
            'social_shares',
            'media_items'
        )
    
    @staticmethod
    def optimize_comment_queryset(queryset):
        """Optimize comment queryset"""
        return queryset.select_related('post').prefetch_related('replies')
    
    @staticmethod
    def get_popular_posts_optimized(timeframe: str = 'week', limit: int = 5):
        """Get popular posts with optimized query"""
        from .models import Post
        
        cache_key = f"popular_posts:{timeframe}:{limit}"
        cached_result = CacheManager.get('popular_posts', timeframe, limit=limit)
        
        if cached_result is not None:
            return cached_result
        
        # Calculate date filter
        now = timezone.now()
        if timeframe == 'week':
            start_date = now - timedelta(days=7)
        elif timeframe == 'month':
            start_date = now - timedelta(days=30)
        elif timeframe == 'year':
            start_date = now - timedelta(days=365)
        else:
            start_date = None
        
        # Build optimized query
        queryset = Post.objects.filter(status='published')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        
        posts = list(QueryOptimizer.optimize_post_queryset(queryset).order_by(
            '-view_count', '-created_at'
        )[:limit])
        
        # Cache the result
        CacheManager.set('popular_posts', posts, args=[timeframe], limit=limit)
        
        return posts
    
    @staticmethod
    def get_related_posts_optimized(post, limit: int = 3):
        """Get related posts with optimized query and caching"""
        from .models import Post
        from django.db.models import Q, Count
        
        cached_result = CacheManager.get('related_posts', post.id, limit=limit)
        if cached_result is not None:
            return cached_result
        
        # Get category and tag IDs
        category_ids = list(post.categories.values_list('id', flat=True))
        tag_ids = list(post.tags.values_list('id', flat=True))
        
        if not category_ids and not tag_ids:
            # Fallback to recent posts
            related_posts = list(QueryOptimizer.optimize_post_queryset(
                Post.objects.filter(status='published').exclude(id=post.id)
            ).order_by('-created_at')[:limit])
        else:
            # Find posts with matching categories or tags
            related_posts = list(QueryOptimizer.optimize_post_queryset(
                Post.objects.filter(
                    status='published'
                ).exclude(
                    id=post.id
                ).filter(
                    Q(categories__id__in=category_ids) | Q(tags__id__in=tag_ids)
                ).distinct().annotate(
                    relevance_score=Count('categories', filter=Q(categories__id__in=category_ids)) +
                                  Count('tags', filter=Q(tags__id__in=tag_ids))
                ).order_by('-relevance_score', '-created_at')
            )[:limit])
        
        # Cache the result
        CacheManager.set('related_posts', related_posts, args=[post.id], limit=limit)
        
        return related_posts


class PerformanceMonitor:
    """Monitor and track performance metrics"""
    
    @staticmethod
    def time_function(func):
        """Decorator to time function execution"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            # Log slow queries (> 1 second)
            if execution_time > 1.0:
                import logging
                logger = logging.getLogger('blog.performance')
                logger.warning(
                    f"Slow function execution: {func.__name__} took {execution_time:.2f}s"
                )
            
            return result
        return wrapper
    
    @staticmethod
    def track_query_count(func):
        """Decorator to track database query count"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            from django.db import connection
            
            initial_queries = len(connection.queries)
            result = func(*args, **kwargs)
            final_queries = len(connection.queries)
            
            query_count = final_queries - initial_queries
            
            # Log excessive queries (> 10)
            if query_count > 10:
                import logging
                logger = logging.getLogger('blog.performance')
                logger.warning(
                    f"High query count: {func.__name__} executed {query_count} queries"
                )
            
            return result
        return wrapper


class ViewCountOptimizer:
    """Optimize view count tracking to reduce database writes"""
    
    @staticmethod
    def increment_view_count(post_id: int) -> None:
        """
        Increment view count with batching to reduce database load.
        
        Args:
            post_id: ID of the post to increment view count for
        """
        cache_key = f"view_count_buffer:{post_id}"
        
        # Increment counter in cache
        current_count = cache.get(cache_key, 0)
        cache.set(cache_key, current_count + 1, 300)  # 5 minutes
        
        # Batch update every 10 views or 5 minutes
        if current_count + 1 >= 10:
            ViewCountOptimizer._flush_view_count(post_id)
    
    @staticmethod
    def _flush_view_count(post_id: int) -> None:
        """Flush buffered view count to database"""
        from .models import Post
        
        cache_key = f"view_count_buffer:{post_id}"
        buffered_count = cache.get(cache_key, 0)
        
        if buffered_count > 0:
            # Update database
            Post.objects.filter(id=post_id).update(
                view_count=models.F('view_count') + buffered_count
            )
            
            # Clear cache
            cache.delete(cache_key)
    
    @staticmethod
    def flush_all_view_counts() -> None:
        """Flush all buffered view counts (for periodic cleanup)"""
        # This would typically be called by a management command or Celery task
        # Implementation depends on cache backend capabilities
        pass


class SearchOptimizer:
    """Optimize search functionality with caching and indexing"""
    
    @staticmethod
    def search_posts_cached(query: str, filters: Dict = None, limit: int = 20):
        """
        Perform cached search with optimized queries.
        
        Args:
            query: Search query string
            filters: Additional filters (category, tag, date_range)
            limit: Maximum number of results
            
        Returns:
            List of matching posts
        """
        from .models import Post
        from django.db.models import Q
        
        # Create cache key from query and filters
        cache_key_data = {
            'query': query,
            'filters': filters or {},
            'limit': limit
        }
        
        cached_result = CacheManager.get(
            'search_results', 
            hashlib.md5(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()
        )
        
        if cached_result is not None:
            return cached_result
        
        # Build search query
        search_query = Q()
        if query:
            search_query = (
                Q(title__icontains=query) |
                Q(excerpt__icontains=query) |
                Q(content__icontains=query) |
                Q(tags__name__icontains=query) |
                Q(categories__name__icontains=query)
            )
        
        # Start with base queryset
        posts_queryset = Post.objects.filter(status='published')
        
        if query:
            posts_queryset = posts_queryset.filter(search_query).distinct()
        
        # Apply filters
        if filters:
            if filters.get('category'):
                posts_queryset = posts_queryset.filter(categories__slug=filters['category'])
            
            if filters.get('tag'):
                posts_queryset = posts_queryset.filter(tags__slug=filters['tag'])
            
            if filters.get('date_range'):
                now = timezone.now()
                if filters['date_range'] == 'week':
                    start_date = now - timedelta(days=7)
                    posts_queryset = posts_queryset.filter(created_at__gte=start_date)
                elif filters['date_range'] == 'month':
                    start_date = now - timedelta(days=30)
                    posts_queryset = posts_queryset.filter(created_at__gte=start_date)
                elif filters['date_range'] == 'year':
                    start_date = now - timedelta(days=365)
                    posts_queryset = posts_queryset.filter(created_at__gte=start_date)
        
        # Optimize and execute query
        posts = list(QueryOptimizer.optimize_post_queryset(
            posts_queryset
        ).order_by('-created_at')[:limit])
        
        # Cache results
        CacheManager.set(
            'search_results',
            posts,
            hashlib.md5(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()
        )
        
        return posts


class CacheInvalidator:
    """Handle cache invalidation when data changes"""
    
    @staticmethod
    def invalidate_post_caches(post_id: int) -> None:
        """Invalidate caches related to a specific post"""
        # Invalidate related posts cache
        CacheManager.delete('related_posts', post_id)
        
        # Invalidate popular posts (if this post might be popular)
        CacheManager.invalidate_pattern('popular_posts')
        
        # Invalidate search results
        CacheManager.invalidate_pattern('search_results')
    
    @staticmethod
    def invalidate_category_caches() -> None:
        """Invalidate category-related caches"""
        CacheManager.delete('category_hierarchy')
        CacheManager.invalidate_pattern('search_results')
    
    @staticmethod
    def invalidate_tag_caches() -> None:
        """Invalidate tag-related caches"""
        CacheManager.delete('tag_cloud')
        CacheManager.invalidate_pattern('search_results')
    
    @staticmethod
    def invalidate_featured_posts_cache() -> None:
        """Invalidate featured posts cache"""
        CacheManager.delete('featured_posts')


class DatabaseIndexOptimizer:
    """Utilities for database index optimization"""
    
    @staticmethod
    def get_recommended_indexes() -> List[Dict]:
        """
        Get recommended database indexes for optimal performance.
        
        Returns:
            List of recommended index configurations
        """
        return [
            {
                'model': 'Post',
                'fields': ['status', 'created_at'],
                'reason': 'Optimize published posts queries with date ordering'
            },
            {
                'model': 'Post',
                'fields': ['status', 'is_featured'],
                'reason': 'Optimize featured posts queries'
            },
            {
                'model': 'Post',
                'fields': ['status', 'view_count'],
                'reason': 'Optimize popular posts queries'
            },
            {
                'model': 'Comment',
                'fields': ['post', 'is_approved', 'created_at'],
                'reason': 'Optimize comment display queries'
            },
            {
                'model': 'Comment',
                'fields': ['parent', 'is_approved'],
                'reason': 'Optimize reply queries'
            },
            {
                'model': 'Tag',
                'fields': ['name'],
                'reason': 'Optimize tag search and filtering'
            },
            {
                'model': 'Category',
                'fields': ['parent', 'name'],
                'reason': 'Optimize category hierarchy queries'
            },
            {
                'model': 'SocialShare',
                'fields': ['post', 'platform'],
                'reason': 'Optimize social share tracking'
            },
            {
                'model': 'NewsletterSubscriber',
                'fields': ['is_confirmed', 'subscribed_at'],
                'reason': 'Optimize newsletter subscriber queries'
            }
        ]
    
    @staticmethod
    def analyze_query_performance() -> Dict:
        """
        Analyze query performance and provide recommendations.
        
        Returns:
            Dictionary with performance analysis
        """
        from django.db import connection
        
        # This would analyze slow query logs and provide recommendations
        # Implementation depends on database backend
        
        return {
            'slow_queries': [],
            'missing_indexes': [],
            'recommendations': []
        }


# Decorator for caching function results
def cached_result(cache_prefix: str, timeout: Optional[int] = None):
    """
    Decorator to cache function results.
    
    Args:
        cache_prefix: Prefix for cache key
        timeout: Cache timeout in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function arguments
            cache_key = CacheManager.get_cache_key(cache_prefix, *args, **kwargs)
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_timeout = timeout or CacheManager.CACHE_TIMEOUTS.get(cache_prefix, 3600)
            cache.set(cache_key, result, cache_timeout)
            
            return result
        return wrapper
    return decorator