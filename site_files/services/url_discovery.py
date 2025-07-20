"""
URL Discovery Service for the Site Files Updater.

This module provides functionality to discover all available URLs in the Django project,
including static URLs from URL patterns and dynamic URLs from database content.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from django.urls import URLPattern, URLResolver
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@dataclass
class URLInfo:
    """
    Data class to store information about a URL.
    """
    url: str  # The relative or absolute URL
    lastmod: Optional[datetime] = None  # Last modification date
    changefreq: str = 'monthly'  # Change frequency (daily, weekly, monthly, etc.)
    priority: float = 0.5  # Priority (0.0 to 1.0)
    title: Optional[str] = None  # Page title if available
    type: str = 'page'  # Type of content (page, blog, api, etc.)

    def get_absolute_url(self, site_url: str) -> str:
        """
        Get the absolute URL by combining the site URL with the relative URL.
        
        Args:
            site_url: The base URL of the site (e.g., https://example.com)
            
        Returns:
            The absolute URL
        """
        if self.url.startswith(('http://', 'https://')):
            return self.url
        
        # Ensure site_url doesn't end with a slash and url doesn't start with a slash
        site_url = site_url.rstrip('/')
        url = self.url.lstrip('/')
        
        return f"{site_url}/{url}"
    
    def to_dict(self) -> dict:
        """
        Convert the URLInfo object to a dictionary.
        
        Returns:
            A dictionary representation of the URLInfo object
        """
        result = {
            'url': self.url,
            'changefreq': self.changefreq,
            'priority': self.priority,
            'type': self.type
        }
        
        if self.lastmod:
            result['lastmod'] = self.lastmod.isoformat()
        
        if self.title:
            result['title'] = self.title
            
        return result
    
    def to_sitemap_element(self, site_url: str) -> str:
        """
        Convert the URLInfo object to a sitemap XML element.
        
        Args:
            site_url: The base URL of the site (e.g., https://example.com)
            
        Returns:
            A string containing the sitemap XML element
        """
        absolute_url = self.get_absolute_url(site_url)
        
        # XML escape special characters
        absolute_url = absolute_url.replace('&', '&amp;').replace("'", '&apos;').replace('"', '&quot;')
        absolute_url = absolute_url.replace('<', '&lt;').replace('>', '&gt;')
        
        xml = [f'  <url>\n    <loc>{absolute_url}</loc>']
        
        if self.lastmod:
            xml.append(f'    <lastmod>{self.lastmod.strftime("%Y-%m-%d")}</lastmod>')
            
        xml.append(f'    <changefreq>{self.changefreq}</changefreq>')
        xml.append(f'    <priority>{self.priority}</priority>')
        xml.append('  </url>')
        
        return '\n'.join(xml)
    
    def __eq__(self, other) -> bool:
        """
        Compare two URLInfo objects for equality.
        
        Args:
            other: Another URLInfo object to compare with
            
        Returns:
            True if the URLs are equal, False otherwise
        """
        if not isinstance(other, URLInfo):
            return False
        return self.url == other.url
    
    def __hash__(self) -> int:
        """
        Generate a hash value for the URLInfo object.
        
        Returns:
            A hash value based on the URL
        """
        return hash(self.url)


class URLDiscoveryService:
    """
    Service for discovering all available URLs in the Django project.
    """
    
    def __init__(self, site_url: str = None):
        """
        Initialize the URL discovery service.
        
        Args:
            site_url: The base URL of the site (e.g., https://example.com)
        """
        self.site_url = site_url or getattr(settings, 'SITE_URL', 'https://example.com')
        # Patterns to exclude from the sitemap
        self.exclude_patterns = [
            r'^admin/',
            r'^open/admin/',
            r'^api/auth/',
            r'^swagger',
            r'^redoc',
            r'^__debug__/',
            r'^media/',
            r'^static/',
        ]
        # Additional exclude patterns from settings
        self.exclude_patterns.extend(getattr(settings, 'SITEMAP_EXCLUDE_PATTERNS', []))
    
    def get_all_public_urls(self) -> List[URLInfo]:
        """
        Discovers all public-facing URLs in the Django project.
        
        Returns:
            A list of URLInfo objects representing all public URLs
        """
        logger.info("Discovering all public URLs")
        
        # Get URLs from URL patterns
        static_urls = self._extract_url_patterns()
        
        # Get dynamic content URLs (will be implemented in the next task)
        dynamic_urls = self.get_dynamic_content_urls()
        
        # Combine and deduplicate URLs
        all_urls = list({url.url: url for url in static_urls + dynamic_urls}.values())
        
        logger.info(f"Discovered {len(all_urls)} public URLs")
        return all_urls
    
    def _extract_url_patterns(self) -> List[URLInfo]:
        """
        Extract URL patterns from Django's URL configuration.
        
        Returns:
            A list of URLInfo objects representing static URL patterns
        """
        from django.urls import get_resolver
        
        logger.info("Extracting URL patterns")
        urls = []
        
        try:
            # Get the URL resolver
            resolver = get_resolver()
            
            # Extract URL patterns
            extracted_patterns = self._extract_patterns_from_resolver(resolver)
            
            # Filter out non-public URLs
            urls = self._filter_public_urls(extracted_patterns)
            
            logger.info(f"Extracted {len(urls)} URL patterns")
        except Exception as e:
            logger.error(f"Error extracting URL patterns: {e}")
        
        return urls
    
    def _extract_patterns_from_resolver(self, resolver, prefix='') -> List[str]:
        """
        Recursively extract URL patterns from a URL resolver.
        
        Args:
            resolver: The URL resolver
            prefix: The URL prefix for nested patterns
            
        Returns:
            A list of URL strings
        """
        patterns = []
        
        # Process URL patterns
        for pattern in resolver.url_patterns:
            if hasattr(pattern, 'pattern'):
                # This is a URLPattern
                if hasattr(pattern, 'name') and pattern.name:
                    # Try to reverse the URL
                    try:
                        from django.urls import reverse
                        url = prefix + self._get_pattern_regex_string(pattern)
                        
                        # Skip if the pattern has unnamed URL parameters
                        if '<' in url and '>' in url:
                            continue
                        
                        patterns.append(url)
                    except Exception as e:
                        logger.debug(f"Could not reverse URL pattern {pattern.name}: {e}")
                else:
                    # Pattern without a name
                    url = prefix + self._get_pattern_regex_string(pattern)
                    
                    # Skip if the pattern has unnamed URL parameters
                    if '<' in url and '>' in url:
                        continue
                    
                    patterns.append(url)
            
            elif hasattr(pattern, 'url_patterns'):
                # This is a URLResolver (includes)
                new_prefix = prefix
                if hasattr(pattern, 'pattern'):
                    new_prefix = prefix + self._get_pattern_regex_string(pattern)
                
                # Recursively process nested patterns
                patterns.extend(self._extract_patterns_from_resolver(pattern, new_prefix))
        
        return patterns
    
    def _get_pattern_regex_string(self, pattern) -> str:
        """
        Get the string representation of a URL pattern.
        
        Args:
            pattern: The URL pattern
            
        Returns:
            The string representation of the pattern
        """
        if hasattr(pattern, 'pattern'):
            # Django 2.0+
            return pattern.pattern.describe().replace('^', '').replace('$', '')
        else:
            # Older Django versions
            return pattern.regex.pattern.replace('^', '').replace('$', '')
    
    def _filter_public_urls(self, urls: List[str]) -> List[URLInfo]:
        """
        Filter out non-public URLs.
        
        Args:
            urls: A list of URL strings
            
        Returns:
            A list of URLInfo objects representing public URLs
        """
        import re
        
        public_urls = []
        
        for url in urls:
            # Skip empty URLs
            if not url:
                continue
            
            # Check if the URL matches any exclude pattern
            exclude = False
            for pattern in self.exclude_patterns:
                if re.match(pattern, url):
                    exclude = True
                    break
            
            if not exclude:
                # Create a URLInfo object for the URL
                url_info = URLInfo(
                    url=url,
                    # Default values for static URLs
                    changefreq='monthly',
                    priority=0.5,
                    type='page'
                )
                public_urls.append(url_info)
        
        return public_urls
    
    def get_dynamic_content_urls(self) -> List[URLInfo]:
        """
        Queries the database for dynamic content URLs.
        
        Returns:
            A list of URLInfo objects representing dynamic content URLs
        """
        logger.info("Discovering dynamic content URLs")
        
        urls = []
        
        # Get blog post URLs
        blog_urls = self._get_blog_post_urls()
        urls.extend(blog_urls)
        
        # Get page URLs
        page_urls = self._get_page_urls()
        urls.extend(page_urls)
        
        # Get blog category URLs
        category_urls = self._get_blog_category_urls()
        urls.extend(category_urls)
        
        logger.info(f"Discovered {len(urls)} dynamic content URLs")
        return urls
    
    def _get_blog_post_urls(self) -> List[URLInfo]:
        """
        Get URLs for all published blog posts.
        
        Returns:
            A list of URLInfo objects for blog posts
        """
        try:
            # Import here to avoid circular imports
            from blog.models import Post
            
            logger.info("Discovering blog post URLs")
            urls = []
            
            # Get all published blog posts
            posts = Post.objects.filter(status='published')
            
            for post in posts:
                url_info = URLInfo(
                    url=f"blog/{post.slug}/",
                    lastmod=post.updated_at,
                    changefreq='weekly',
                    priority=0.7,
                    title=post.title,
                    type='blog'
                )
                urls.append(url_info)
            
            logger.info(f"Discovered {len(urls)} blog post URLs")
            return urls
        except Exception as e:
            logger.error(f"Error discovering blog post URLs: {e}")
            return []
    
    def _get_blog_category_urls(self) -> List[URLInfo]:
        """
        Get URLs for all blog categories.
        
        Returns:
            A list of URLInfo objects for blog categories
        """
        try:
            # Import here to avoid circular imports
            from blog.models import Category
            
            logger.info("Discovering blog category URLs")
            urls = []
            
            # Get all categories
            categories = Category.objects.all()
            
            for category in categories:
                url_info = URLInfo(
                    url=f"blog/category/{category.slug}/",
                    changefreq='monthly',
                    priority=0.6,
                    title=category.name,
                    type='blog_category'
                )
                urls.append(url_info)
            
            logger.info(f"Discovered {len(urls)} blog category URLs")
            return urls
        except Exception as e:
            logger.error(f"Error discovering blog category URLs: {e}")
            return []
    
    def _get_page_urls(self) -> List[URLInfo]:
        """
        Get URLs for all published pages.
        
        Returns:
            A list of URLInfo objects for pages
        """
        try:
            # Import here to avoid circular imports
            from core.models import Page
            
            logger.info("Discovering page URLs")
            urls = []
            
            # Get all published pages
            pages = Page.objects.filter(is_published=True)
            
            for page in pages:
                # Skip the homepage as it's already covered by the root URL
                if page.is_homepage:
                    continue
                
                url_info = URLInfo(
                    url=f"{page.slug}/",
                    lastmod=page.updated_at,
                    changefreq='monthly',
                    priority=0.8,
                    title=page.title,
                    type='page'
                )
                urls.append(url_info)
            
            logger.info(f"Discovered {len(urls)} page URLs")
            return urls
        except Exception as e:
            logger.error(f"Error discovering page URLs: {e}")
            return []