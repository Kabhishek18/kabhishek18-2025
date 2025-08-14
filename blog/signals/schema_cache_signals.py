"""
Django signals for schema cache invalidation.

This module provides signal handlers to automatically invalidate
schema markup cache when blog posts or related data is updated.
"""

import logging
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.cache import caches

from blog.models import Post, Category, Tag, AuthorProfile
from blog.services.schema_service import SchemaService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Post)
def invalidate_post_schema_cache(sender, instance, created, **kwargs):
    """
    Invalidate schema cache when a post is saved.
    
    Args:
        sender: The model class (Post)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    try:
        # Invalidate the specific post's schema cache
        SchemaService.invalidate_post_schema_cache(instance.id)
        
        # Also invalidate template cache for this post
        template_cache = caches['template_cache']
        cache_pattern = f"schema_template:article:{instance.id}:*"
        
        if hasattr(template_cache, 'delete_pattern'):
            template_cache.delete_pattern(cache_pattern)
            logger.info(f"Invalidated template cache for post {instance.id}")
        
        # Invalidate Django's template fragment cache
        try:
            from django.core.cache.utils import make_template_fragment_key
            fragment_key = make_template_fragment_key('schema_markup', [instance.id, instance.updated_at])
            caches['default'].delete(fragment_key)
        except ImportError:
            # Fallback for different Django versions
            cache_key = f"template.cache.schema_markup.{instance.id}.{instance.updated_at}"
            caches['default'].delete(cache_key)
        
        logger.info(f"Schema cache invalidated for post {instance.id} ({'created' if created else 'updated'})")
        
    except Exception as e:
        logger.error(f"Error invalidating schema cache for post {instance.id}: {str(e)}")


@receiver(post_delete, sender=Post)
def cleanup_post_schema_cache(sender, instance, **kwargs):
    """
    Clean up schema cache when a post is deleted.
    
    Args:
        sender: The model class (Post)
        instance: The actual instance being deleted
        **kwargs: Additional keyword arguments
    """
    try:
        # Clean up the specific post's schema cache
        SchemaService.invalidate_post_schema_cache(instance.id)
        
        # Clean up template cache
        template_cache = caches['template_cache']
        cache_pattern = f"schema_template:article:{instance.id}:*"
        
        if hasattr(template_cache, 'delete_pattern'):
            template_cache.delete_pattern(cache_pattern)
        
        logger.info(f"Schema cache cleaned up for deleted post {instance.id}")
        
    except Exception as e:
        logger.error(f"Error cleaning up schema cache for deleted post {instance.id}: {str(e)}")


@receiver(post_save, sender=AuthorProfile)
def invalidate_author_schema_cache(sender, instance, created, **kwargs):
    """
    Invalidate schema cache when an author profile is updated.
    
    Args:
        sender: The model class (AuthorProfile)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    try:
        # Find all posts by this author and invalidate their cache
        user = instance.user
        posts = Post.objects.filter(author=user)
        
        for post in posts:
            SchemaService.invalidate_post_schema_cache(post.id)
        
        logger.info(f"Schema cache invalidated for {posts.count()} posts by author {user.username}")
        
    except Exception as e:
        logger.error(f"Error invalidating author schema cache: {str(e)}")


@receiver(m2m_changed, sender=Post.categories.through)
def invalidate_post_categories_cache(sender, instance, action, pk_set, **kwargs):
    """
    Invalidate schema cache when post categories are changed.
    
    Args:
        sender: The through model for the many-to-many relationship
        instance: The Post instance
        action: The action being performed ('post_add', 'post_remove', etc.)
        pk_set: Set of primary keys of the related objects
        **kwargs: Additional keyword arguments
    """
    if action in ['post_add', 'post_remove', 'post_clear']:
        try:
            SchemaService.invalidate_post_schema_cache(instance.id)
            logger.info(f"Schema cache invalidated for post {instance.id} due to category changes")
        except Exception as e:
            logger.error(f"Error invalidating schema cache for post categories: {str(e)}")


@receiver(m2m_changed, sender=Post.tags.through)
def invalidate_post_tags_cache(sender, instance, action, pk_set, **kwargs):
    """
    Invalidate schema cache when post tags are changed.
    
    Args:
        sender: The through model for the many-to-many relationship
        instance: The Post instance
        action: The action being performed ('post_add', 'post_remove', etc.)
        pk_set: Set of primary keys of the related objects
        **kwargs: Additional keyword arguments
    """
    if action in ['post_add', 'post_remove', 'post_clear']:
        try:
            SchemaService.invalidate_post_schema_cache(instance.id)
            logger.info(f"Schema cache invalidated for post {instance.id} due to tag changes")
        except Exception as e:
            logger.error(f"Error invalidating schema cache for post tags: {str(e)}")


@receiver(post_save, sender=Category)
def invalidate_category_posts_cache(sender, instance, created, **kwargs):
    """
    Invalidate schema cache for posts when a category is updated.
    
    Args:
        sender: The model class (Category)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    if not created:  # Only for updates, not new categories
        try:
            # Find all posts in this category and invalidate their cache
            posts = Post.objects.filter(categories=instance)
            
            for post in posts:
                SchemaService.invalidate_post_schema_cache(post.id)
            
            logger.info(f"Schema cache invalidated for {posts.count()} posts in category '{instance.name}'")
            
        except Exception as e:
            logger.error(f"Error invalidating category posts cache: {str(e)}")


@receiver(post_save, sender=Tag)
def invalidate_tag_posts_cache(sender, instance, created, **kwargs):
    """
    Invalidate schema cache for posts when a tag is updated.
    
    Args:
        sender: The model class (Tag)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    if not created:  # Only for updates, not new tags
        try:
            # Find all posts with this tag and invalidate their cache
            posts = Post.objects.filter(tags=instance)
            
            for post in posts:
                SchemaService.invalidate_post_schema_cache(post.id)
            
            logger.info(f"Schema cache invalidated for {posts.count()} posts with tag '{instance.name}'")
            
        except Exception as e:
            logger.error(f"Error invalidating tag posts cache: {str(e)}")


def bulk_invalidate_schema_cache():
    """
    Utility function to bulk invalidate all schema cache.
    Useful for maintenance or when making global changes.
    """
    try:
        SchemaService.clear_all_schema_cache()
        
        # Also clear template cache
        template_cache = caches['template_cache']
        template_cache.clear()
        
        # Clear template fragment cache
        caches['default'].clear()
        
        logger.info("Bulk invalidation of all schema cache completed")
        
    except Exception as e:
        logger.error(f"Error during bulk cache invalidation: {str(e)}")


def warm_up_schema_cache(post_queryset=None):
    """
    Utility function to warm up schema cache for posts.
    
    Args:
        post_queryset: Optional queryset of posts to warm up. 
                      If None, warms up cache for all published posts.
    """
    try:
        if post_queryset is None:
            post_queryset = Post.objects.select_related(
                'author',
                'author__profile'
            ).prefetch_related(
                'categories',
                'tags',
                'media_items'
            ).filter(status='published')
        
        warmed_count = 0
        for post in post_queryset:
            try:
                # Generate schema to warm up cache
                SchemaService.generate_article_schema(post)
                warmed_count += 1
            except Exception as e:
                logger.warning(f"Failed to warm cache for post {post.id}: {str(e)}")
        
        logger.info(f"Schema cache warmed up for {warmed_count} posts")
        
    except Exception as e:
        logger.error(f"Error during cache warm-up: {str(e)}")