"""
Schema Service for generating JSON-LD structured data for blog posts.

This service provides methods to generate Schema.org compliant structured data
for articles, authors, and publishers to improve SEO and enable rich results
in search engines.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

from django.conf import settings
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.contrib.sites.models import Site
from django.core.cache import caches
from blog.utils.performance_monitor import performance_monitor, monitor_schema_performance

logger = logging.getLogger(__name__)


class SchemaService:
    """Service for generating Schema.org structured data markup."""
    
    # Schema.org context
    SCHEMA_CONTEXT = "https://schema.org"
    
    # Cache configuration
    SCHEMA_CACHE_TIMEOUT = 3600  # 1 hour
    SCHEMA_CACHE_KEY_PREFIX = 'schema'
    
    # Default publisher information
    DEFAULT_PUBLISHER = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Digital Codex",
        "url": "https://kabhishek18.com",
        "logo": {
            "@type": "ImageObject",
            "url": "https://kabhishek18.com/static/web-app-manifest-512x512.png",
            "width": 512,
            "height": 512
        },
        "sameAs": [
            "https://twitter.com/kabhishek18",
            "https://linkedin.com/in/kabhishek18"
        ]
    }

    @staticmethod
    @monitor_schema_performance
    def generate_article_schema(post, request=None) -> Dict[str, Any]:
        """
        Generate Article schema markup for a blog post.
        
        Args:
            post: Post model instance (should be prefetched with related data)
            request: Django request object for absolute URL generation
            
        Returns:
            Dict containing Article schema markup
        """
        # Try to get from cache first
        cache_key = f"{SchemaService.SCHEMA_CACHE_KEY_PREFIX}:article:{post.id}:{post.updated_at.timestamp()}"
        
        try:
            # Try schema_cache first, fallback to default cache
            try:
                schema_cache = caches['schema_cache']
            except:
                schema_cache = caches['default']
            
            cached_schema = schema_cache.get(cache_key)
            if cached_schema:
                logger.debug(f"Schema cache hit for post {post.id}")
                performance_monitor.record_cache_hit('schema_article')
                return cached_schema
            else:
                performance_monitor.record_cache_miss('schema_article')
        except Exception as e:
            logger.warning(f"Schema cache error for post {post.id}: {str(e)}")
            performance_monitor.record_cache_miss('schema_article')
        
        try:
            # Build absolute URL
            if request:
                absolute_url = request.build_absolute_uri(post.get_absolute_url())
            else:
                # Fallback to constructing URL manually
                domain = getattr(settings, 'SITE_DOMAIN', 'kabhishek18.com')
                absolute_url = f"https://{domain}{post.get_absolute_url()}"
            
            # Handle date formatting safely
            try:
                date_published = post.created_at.isoformat() if hasattr(post.created_at, 'isoformat') else str(post.created_at)
                date_modified = post.updated_at.isoformat() if hasattr(post.updated_at, 'isoformat') else str(post.updated_at)
            except:
                date_published = "2024-01-01T00:00:00Z"
                date_modified = "2024-01-01T00:00:00Z"
            
            # Generate base article schema
            schema = {
                "@context": SchemaService.SCHEMA_CONTEXT,
                "@type": "Article",
                "headline": SchemaService._truncate_headline(post.title),
                "url": absolute_url,
                "datePublished": date_published,
                "dateModified": date_modified,
                "author": SchemaService.generate_author_schema(post.author, request),
                "publisher": SchemaService.generate_publisher_schema(),
            }
            
            # Add description/excerpt
            if post.excerpt:
                schema["description"] = SchemaService._clean_text(post.excerpt)
            elif post.content:
                # Generate excerpt from content
                clean_content = strip_tags(post.content)
                schema["description"] = Truncator(clean_content).words(30)
            
            # Add word count and reading time
            if post.content:
                word_count = len(strip_tags(post.content).split())
                schema["wordCount"] = word_count
                
                # Convert reading time to ISO 8601 duration format
                reading_minutes = post.get_reading_time()
                schema["timeRequired"] = f"PT{reading_minutes}M"
            
            # Add images (optimized to avoid N+1 queries)
            images = SchemaService._get_post_images(post, request)
            if images:
                schema["image"] = images
            
            # Use prefetched categories and tags to avoid additional queries
            try:
                # Try to use prefetched data first
                if hasattr(post, '_prefetched_objects_cache') and 'categories' in post._prefetched_objects_cache:
                    categories = [cat.name for cat in post.categories.all()]
                else:
                    categories = list(post.categories.values_list('name', flat=True))
                
                if categories:
                    schema["articleSection"] = categories
            except Exception as e:
                logger.warning(f"Error getting categories for post {post.id}: {str(e)}")
            
            try:
                # Try to use prefetched data first
                if hasattr(post, '_prefetched_objects_cache') and 'tags' in post._prefetched_objects_cache:
                    tags = [tag.name for tag in post.tags.all()]
                else:
                    tags = list(post.tags.values_list('name', flat=True))
                
                if tags:
                    schema["keywords"] = tags
            except Exception as e:
                logger.warning(f"Error getting tags for post {post.id}: {str(e)}")
            
            # Add main entity of page
            schema["mainEntityOfPage"] = {
                "@type": "WebPage",
                "@id": absolute_url
            }
            
            # Cache the generated schema
            try:
                try:
                    schema_cache = caches['schema_cache']
                except:
                    schema_cache = caches['default']
                schema_cache.set(cache_key, schema, SchemaService.SCHEMA_CACHE_TIMEOUT)
                logger.debug(f"Schema cached for post {post.id}")
            except Exception as e:
                logger.warning(f"Failed to cache schema for post {post.id}: {str(e)}")
            
            return schema
            
        except Exception as e:
            logger.error(f"Error generating article schema for post {post.id}: {str(e)}")
            # Return minimal schema on error
            return SchemaService._get_minimal_article_schema(post, request)

    @staticmethod
    def generate_author_schema(author, request=None) -> Dict[str, Any]:
        """
        Generate Person schema markup for an author.
        
        Args:
            author: User model instance or AuthorProfile instance
            request: Django request object for absolute URL generation
            
        Returns:
            Dict containing Person schema markup
        """
        try:
            # Handle both User and AuthorProfile instances
            if hasattr(author, 'author_profile'):
                profile = author.author_profile
                user = author
            elif hasattr(author, 'user'):
                profile = author
                user = author.user
            else:
                # Direct User instance without profile
                profile = None
                user = author
            
            # Generate display name
            if user.first_name and user.last_name:
                name = f"{user.first_name} {user.last_name}"
            elif user.first_name:
                name = user.first_name
            else:
                name = user.username
            
            schema = {
                "@type": "Person",
                "name": name,
            }
            
            # Add profile information if available
            if profile:
                # Add bio as description
                if profile.bio:
                    schema["description"] = SchemaService._clean_text(profile.bio)
                
                # Add social media profiles
                same_as = []
                if profile.website:
                    same_as.append(profile.website)
                if profile.twitter:
                    username = profile.twitter.lstrip('@')
                    same_as.append(f"https://twitter.com/{username}")
                if profile.linkedin:
                    same_as.append(profile.linkedin)
                if profile.github:
                    same_as.append(f"https://github.com/{profile.github}")
                if profile.instagram:
                    username = profile.instagram.lstrip('@')
                    same_as.append(f"https://instagram.com/{username}")
                
                if same_as:
                    schema["sameAs"] = same_as
                
                # Add profile image
                if profile.profile_picture and request:
                    schema["image"] = request.build_absolute_uri(profile.profile_picture.url)
                
                # Add author URL if we can generate it
                if request:
                    try:
                        author_url = reverse('blog:author_detail', kwargs={'username': user.username})
                        schema["url"] = request.build_absolute_uri(author_url)
                    except:
                        pass  # Author detail URL might not exist
            
            return schema
            
        except Exception as e:
            logger.error(f"Error generating author schema for user {author}: {str(e)}")
            # Return minimal author schema
            return {
                "@type": "Person",
                "name": getattr(author, 'username', 'Unknown Author')
            }

    @staticmethod
    def generate_standalone_author_schema(author, request=None) -> Dict[str, Any]:
        """
        Generate standalone Person schema markup for an author with @context.
        
        Args:
            author: User model instance or AuthorProfile instance
            request: Django request object for absolute URL generation
            
        Returns:
            Dict containing standalone Person schema markup
        """
        schema = SchemaService.generate_author_schema(author, request)
        schema["@context"] = SchemaService.SCHEMA_CONTEXT
        return schema

    @staticmethod
    def generate_publisher_schema() -> Dict[str, Any]:
        """
        Generate Organization schema markup for the publisher.
        
        Returns:
            Dict containing Organization schema markup
        """
        # Try to get from cache first (publisher info rarely changes)
        cache_key = f"{SchemaService.SCHEMA_CACHE_KEY_PREFIX}:publisher"
        
        try:
            try:
                schema_cache = caches['schema_cache']
            except:
                schema_cache = caches['default']
            
            cached_schema = schema_cache.get(cache_key)
            if cached_schema:
                logger.debug("Publisher schema cache hit")
                performance_monitor.record_cache_hit('schema_publisher')
                return cached_schema
            else:
                performance_monitor.record_cache_miss('schema_publisher')
        except Exception as e:
            logger.warning(f"Publisher schema cache error: {str(e)}")
            performance_monitor.record_cache_miss('schema_publisher')
        
        try:
            # Try to get publisher info from settings
            publisher_name = getattr(settings, 'SITE_NAME', SchemaService.DEFAULT_PUBLISHER['name'])
            publisher_url = getattr(settings, 'SITE_URL', SchemaService.DEFAULT_PUBLISHER['url'])
            
            schema = {
                "@context": SchemaService.SCHEMA_CONTEXT,
                "@type": "Organization",
                "name": publisher_name,
                "url": publisher_url,
            }
            
            # Add logo
            logo_url = getattr(settings, 'SITE_LOGO_URL', SchemaService.DEFAULT_PUBLISHER['logo']['url'])
            schema["logo"] = {
                "@type": "ImageObject",
                "url": logo_url,
                "width": 512,
                "height": 512
            }
            
            # Add social media profiles
            social_profiles = getattr(settings, 'SOCIAL_PROFILES', SchemaService.DEFAULT_PUBLISHER['sameAs'])
            if social_profiles:
                schema["sameAs"] = social_profiles
            
            # Cache the publisher schema (long timeout since it rarely changes)
            try:
                try:
                    schema_cache = caches['schema_cache']
                except:
                    schema_cache = caches['default']
                schema_cache.set(cache_key, schema, 86400)  # 24 hours
                logger.debug("Publisher schema cached")
            except Exception as e:
                logger.warning(f"Failed to cache publisher schema: {str(e)}")
            
            return schema
            
        except Exception as e:
            logger.error(f"Error generating publisher schema: {str(e)}")
            return SchemaService.DEFAULT_PUBLISHER.copy()

    @staticmethod
    def generate_breadcrumb_schema(post, request=None) -> Dict[str, Any]:
        """
        Generate BreadcrumbList schema markup for a blog post.
        
        Args:
            post: Post model instance
            request: Django request object for absolute URL generation
            
        Returns:
            Dict containing BreadcrumbList schema markup
        """
        try:
            if not request:
                return {}
            
            breadcrumbs = []
            
            # Home page
            breadcrumbs.append({
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": request.build_absolute_uri('/')
            })
            
            # Blog page
            try:
                blog_url = reverse('blog:list')
                breadcrumbs.append({
                    "@type": "ListItem",
                    "position": 2,
                    "name": "Blog",
                    "item": request.build_absolute_uri(blog_url)
                })
            except:
                pass
            
            # Current post
            breadcrumbs.append({
                "@type": "ListItem",
                "position": len(breadcrumbs) + 1,
                "name": post.title,
                "item": request.build_absolute_uri(post.get_absolute_url())
            })
            
            return {
                "@context": SchemaService.SCHEMA_CONTEXT,
                "@type": "BreadcrumbList",
                "itemListElement": breadcrumbs
            }
            
        except Exception as e:
            logger.error(f"Error generating breadcrumb schema for post {post.id}: {str(e)}")
            return {}

    @staticmethod
    def validate_schema(schema_data: Dict[str, Any], is_embedded: bool = False) -> bool:
        """
        Validate schema markup for basic compliance.
        
        Args:
            schema_data: Schema markup dictionary
            is_embedded: Whether this is an embedded schema (doesn't need @context)
            
        Returns:
            bool: True if schema appears valid, False otherwise
        """
        try:
            if not isinstance(schema_data, dict):
                return False
            
            # Check for required context (only for top-level schemas)
            if not is_embedded and schema_data.get("@context") != SchemaService.SCHEMA_CONTEXT:
                return False
            
            # Check for required type
            if not schema_data.get("@type"):
                return False
            
            # Validate Article schema
            if schema_data.get("@type") == "Article":
                required_fields = ["headline", "author", "publisher", "datePublished"]
                for field in required_fields:
                    if not schema_data.get(field):
                        logger.warning(f"Missing required Article field: {field}")
                        return False
            
            # Validate Person schema
            elif schema_data.get("@type") == "Person":
                if not schema_data.get("name"):
                    logger.warning("Missing required Person field: name")
                    return False
            
            # Validate Organization schema
            elif schema_data.get("@type") == "Organization":
                required_fields = ["name"]
                for field in required_fields:
                    if not schema_data.get(field):
                        logger.warning(f"Missing required Organization field: {field}")
                        return False
            
            # Try to serialize to JSON to check for serialization issues
            json.dumps(schema_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Schema validation error: {str(e)}")
            return False

    @staticmethod
    def _truncate_headline(title: str, max_length: int = 110) -> str:
        """
        Truncate headline to optimal length for SEO.
        
        Args:
            title: Original title
            max_length: Maximum length for headline
            
        Returns:
            Truncated title
        """
        if len(title) <= max_length:
            return title
        return Truncator(title).chars(max_length, truncate='...')

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Clean text content for schema markup.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Strip HTML tags and normalize whitespace
        clean_text = strip_tags(text)
        clean_text = ' '.join(clean_text.split())
        
        return clean_text

    @staticmethod
    def _get_post_images(post, request=None) -> List[str]:
        """
        Get all relevant images for a post.
        
        Args:
            post: Post model instance (should be prefetched with media_items)
            request: Django request object for absolute URL generation
            
        Returns:
            List of absolute image URLs
        """
        images = []
        
        try:
            # Add featured image
            if post.featured_image:
                if request:
                    images.append(request.build_absolute_uri(post.featured_image.url))
                else:
                    domain = getattr(settings, 'SITE_DOMAIN', 'kabhishek18.com')
                    images.append(f"https://{domain}{post.featured_image.url}")
            
            # Add social image if different from featured
            if post.social_image and post.social_image != post.featured_image:
                if request:
                    images.append(request.build_absolute_uri(post.social_image.url))
                else:
                    domain = getattr(settings, 'SITE_DOMAIN', 'kabhishek18.com')
                    images.append(f"https://{domain}{post.social_image.url}")
            
            # Add media item images (use prefetched data if available)
            try:
                if hasattr(post, '_prefetched_objects_cache') and 'media_items' in post._prefetched_objects_cache:
                    media_items = [item for item in post.media_items.all() if item.media_type == 'image']
                else:
                    media_items = post.media_items.filter(media_type='image')
                
                for media_item in media_items:
                    if media_item.original_image:
                        if request:
                            images.append(request.build_absolute_uri(media_item.original_image.url))
                        else:
                            domain = getattr(settings, 'SITE_DOMAIN', 'kabhishek18.com')
                            images.append(f"https://{domain}{media_item.original_image.url}")
            except Exception as e:
                logger.warning(f"Error getting media items for post {post.id}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error getting post images: {str(e)}")
        
        return images

    @staticmethod
    def _get_minimal_article_schema(post, request=None) -> Dict[str, Any]:
        """
        Generate minimal article schema as fallback.
        
        Args:
            post: Post model instance
            request: Django request object
            
        Returns:
            Minimal article schema
        """
        try:
            if request:
                absolute_url = request.build_absolute_uri(post.get_absolute_url())
            else:
                domain = getattr(settings, 'SITE_DOMAIN', 'kabhishek18.com')
                absolute_url = f"https://{domain}{post.get_absolute_url()}"
            
            # Handle date formatting safely
            try:
                date_published = post.created_at.isoformat() if hasattr(post.created_at, 'isoformat') else str(post.created_at)
            except:
                date_published = "2024-01-01T00:00:00Z"
            
            return {
                "@context": SchemaService.SCHEMA_CONTEXT,
                "@type": "Article",
                "headline": post.title,
                "url": absolute_url,
                "datePublished": date_published,
                "author": {"@type": "Person", "name": getattr(post.author, 'username', 'Unknown')},
                "publisher": SchemaService.DEFAULT_PUBLISHER.copy()
            }
        except Exception as e:
            logger.error(f"Error generating minimal article schema: {str(e)}")
            return {}

    @staticmethod
    def invalidate_post_schema_cache(post_id: int):
        """
        Invalidate cached schema data for a specific post.
        
        Args:
            post_id: ID of the post to invalidate cache for
        """
        try:
            try:
                schema_cache = caches['schema_cache']
            except:
                schema_cache = caches['default']
            
            # We need to invalidate all possible cache keys for this post
            # Since we include timestamp in the key, we'll use pattern matching
            cache_pattern = f"{SchemaService.SCHEMA_CACHE_KEY_PREFIX}:article:{post_id}:*"
            
            # For Redis backend, we can use delete_pattern
            if hasattr(schema_cache, 'delete_pattern'):
                schema_cache.delete_pattern(cache_pattern)
                logger.info(f"Invalidated schema cache pattern for post {post_id}")
            else:
                # Fallback: just log that we can't pattern delete
                logger.warning(f"Cannot pattern delete cache for post {post_id}, cache backend doesn't support it")
                
        except Exception as e:
            logger.error(f"Error invalidating schema cache for post {post_id}: {str(e)}")

    @staticmethod
    def invalidate_publisher_schema_cache():
        """
        Invalidate cached publisher schema data.
        """
        try:
            schema_cache = caches['schema_cache']
            cache_key = f"{SchemaService.SCHEMA_CACHE_KEY_PREFIX}:publisher"
            schema_cache.delete(cache_key)
            logger.info("Invalidated publisher schema cache")
        except Exception as e:
            logger.error(f"Error invalidating publisher schema cache: {str(e)}")

    @staticmethod
    def clear_all_schema_cache():
        """
        Clear all schema-related cache data.
        """
        try:
            schema_cache = caches['schema_cache']
            schema_cache.clear()
            logger.info("Cleared all schema cache data")
        except Exception as e:
            logger.error(f"Error clearing schema cache: {str(e)}")