"""
LinkedIn Content Formatting Utilities

This module provides utilities for formatting blog post content for LinkedIn posting.
Handles character limits, hashtag generation, and media URL extraction.
"""

import re
import logging
from typing import List, Optional, Dict, Tuple
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.conf import settings
from urllib.parse import urljoin


logger = logging.getLogger(__name__)


class LinkedInContentFormatter:
    """
    Utility class for formatting blog post content for LinkedIn.
    
    Handles:
    - Character limit enforcement with intelligent truncation
    - Hashtag generation from blog post tags
    - Featured image URL extraction
    - Content formatting for LinkedIn posts
    """
    
    # LinkedIn content limits
    MAX_POST_LENGTH = 3000
    MAX_TITLE_LENGTH = 200
    MAX_EXCERPT_LENGTH = 300
    MAX_HASHTAGS = 5
    
    # Content formatting templates
    POST_TEMPLATE = "{title}\n\n{content}\n\n{url}{hashtags}"
    SIMPLE_TEMPLATE = "{title}\n\n{url}{hashtags}"
    
    def __init__(self, base_url: str = None):
        """
        Initialize the content formatter.
        
        Args:
            base_url: Base URL for the website (used for image URLs)
        """
        self.base_url = base_url or self._get_base_url()
    
    def _get_base_url(self) -> str:
        """Get the base URL from Django settings or sites framework."""
        try:
            from django.contrib.sites.models import Site
            current_site = Site.objects.get_current()
            return f"https://{current_site.domain}"
        except ImportError:
            # Fallback if sites framework is not installed
            from django.conf import settings
            domain = getattr(settings, 'ALLOWED_HOSTS', ['localhost'])[0]
            if domain == '*':
                domain = 'localhost'
            return f"https://{domain}"
        except Exception:
            return "https://localhost"
    
    def format_post_content(self, blog_post, include_excerpt: bool = True) -> str:
        """
        Format a blog post for LinkedIn posting.
        
        Args:
            blog_post: Blog Post model instance
            include_excerpt: Whether to include the excerpt in the post
            
        Returns:
            Formatted LinkedIn post content
        """
        # Get the blog post URL
        post_url = self._get_post_url(blog_post)
        
        # Format title with length limit
        title = self._format_title(blog_post.title)
        
        # Format content/excerpt
        content = ""
        if include_excerpt and blog_post.excerpt:
            content = self._format_excerpt(blog_post.excerpt)
        elif include_excerpt and not blog_post.excerpt:
            # Extract excerpt from content if no explicit excerpt
            content = self._extract_excerpt_from_content(blog_post.content)
        
        # Generate hashtags
        hashtags = self._generate_hashtags(blog_post)
        hashtag_string = f"\n\n{hashtags}" if hashtags else ""
        
        # Choose template based on content availability
        if content:
            formatted_post = self.POST_TEMPLATE.format(
                title=title,
                content=content,
                url=post_url,
                hashtags=hashtag_string
            )
        else:
            formatted_post = self.SIMPLE_TEMPLATE.format(
                title=title,
                url=post_url,
                hashtags=hashtag_string
            )
        
        # Apply character limit with intelligent truncation
        return self._apply_character_limit(formatted_post, post_url, hashtag_string)
    
    def _format_title(self, title: str) -> str:
        """
        Format and truncate title for LinkedIn.
        
        Args:
            title: Original blog post title
            
        Returns:
            Formatted title
        """
        if not title:
            return ""
        
        # Clean up title
        clean_title = title.strip()
        
        # Apply length limit with intelligent truncation
        if len(clean_title) > self.MAX_TITLE_LENGTH:
            truncator = Truncator(clean_title)
            clean_title = truncator.chars(self.MAX_TITLE_LENGTH - 3, truncate='...')
        
        return clean_title
    
    def _format_excerpt(self, excerpt: str) -> str:
        """
        Format and truncate excerpt for LinkedIn.
        
        Args:
            excerpt: Blog post excerpt
            
        Returns:
            Formatted excerpt
        """
        if not excerpt:
            return ""
        
        # Strip HTML tags and clean up
        clean_excerpt = strip_tags(excerpt).strip()
        
        # Remove extra whitespace
        clean_excerpt = re.sub(r'\s+', ' ', clean_excerpt)
        
        # Apply length limit
        if len(clean_excerpt) > self.MAX_EXCERPT_LENGTH:
            truncator = Truncator(clean_excerpt)
            clean_excerpt = truncator.chars(self.MAX_EXCERPT_LENGTH - 3, truncate='...')
        
        return clean_excerpt
    
    def _extract_excerpt_from_content(self, content: str) -> str:
        """
        Extract an excerpt from blog post content.
        
        Args:
            content: Full blog post content
            
        Returns:
            Extracted excerpt
        """
        if not content:
            return ""
        
        # Strip HTML tags
        clean_content = strip_tags(content).strip()
        
        # Remove extra whitespace
        clean_content = re.sub(r'\s+', ' ', clean_content)
        
        # Extract first paragraph or sentence
        paragraphs = clean_content.split('\n\n')
        first_paragraph = paragraphs[0] if paragraphs else clean_content
        
        # If first paragraph is too long, try to get first few sentences
        if len(first_paragraph) > self.MAX_EXCERPT_LENGTH:
            sentences = re.split(r'[.!?]+', first_paragraph)
            excerpt = ""
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Check if adding this sentence would exceed limit
                test_excerpt = f"{excerpt} {sentence}".strip() if excerpt else sentence
                if len(test_excerpt) > self.MAX_EXCERPT_LENGTH - 3:
                    break
                
                excerpt = test_excerpt
            
            if not excerpt:  # Fallback if no complete sentences fit
                truncator = Truncator(first_paragraph)
                excerpt = truncator.chars(self.MAX_EXCERPT_LENGTH - 3, truncate='...')
        else:
            excerpt = first_paragraph
        
        return excerpt
    
    def _generate_hashtags(self, blog_post) -> str:
        """
        Generate hashtags from blog post tags.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            Formatted hashtags string
        """
        if not hasattr(blog_post, 'tags') or not blog_post.tags.exists():
            return ""
        
        # Get tag names and format as hashtags
        tag_names = list(blog_post.tags.values_list('name', flat=True)[:self.MAX_HASHTAGS])
        
        hashtags = []
        for tag_name in tag_names:
            # Clean tag name for hashtag format
            hashtag = self._format_hashtag(tag_name)
            if hashtag:
                hashtags.append(hashtag)
        
        return " ".join(hashtags) if hashtags else ""
    
    def _format_hashtag(self, tag_name: str) -> str:
        """
        Format a tag name as a LinkedIn hashtag.
        
        Args:
            tag_name: Original tag name
            
        Returns:
            Formatted hashtag or empty string if invalid
        """
        if not tag_name:
            return ""
        
        # Remove special characters and spaces, keep alphanumeric
        clean_tag = re.sub(r'[^a-zA-Z0-9\s]', '', tag_name)
        
        # Convert to camelCase for multi-word tags
        words = clean_tag.split()
        if not words:
            return ""
        
        # First word lowercase, subsequent words capitalized
        formatted_words = [words[0].lower()]
        for word in words[1:]:
            if word:
                formatted_words.append(word.capitalize())
        
        hashtag = ''.join(formatted_words)
        
        # Ensure hashtag is valid (at least 1 character, not just numbers)
        if len(hashtag) > 0 and not hashtag.isdigit():
            return f"#{hashtag}"
        
        return ""
    
    def _get_post_url(self, blog_post) -> str:
        """
        Get the full URL for a blog post.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            Full URL to the blog post
        """
        try:
            # Try to get absolute URL from the model
            relative_url = blog_post.get_absolute_url()
            return urljoin(self.base_url, relative_url)
        except Exception as e:
            logger.warning(f"Could not get absolute URL for post {blog_post.id}: {e}")
            # Fallback URL construction
            return f"{self.base_url}/blog/{blog_post.slug}/"
    
    def _apply_character_limit(self, content: str, post_url: str, hashtags: str) -> str:
        """
        Apply LinkedIn character limit with intelligent truncation.
        
        Args:
            content: Full formatted content
            post_url: Blog post URL (must be preserved)
            hashtags: Hashtags string (lower priority)
            
        Returns:
            Truncated content that fits LinkedIn limits
        """
        if len(content) <= self.MAX_POST_LENGTH:
            return content
        
        # Calculate space needed for URL and hashtags
        hashtag_space = len(hashtags)
        
        # If even without hashtags we're over limit, remove hashtags
        if len(content) - hashtag_space > self.MAX_POST_LENGTH:
            content_without_hashtags = content.replace(hashtags, "").rstrip()
            
            # If still over limit, truncate content intelligently
            if len(content_without_hashtags) > self.MAX_POST_LENGTH:
                # Split content to preserve structure
                parts = content_without_hashtags.split('\n\n')
                if len(parts) >= 3:  # title, content, url
                    title = parts[0]
                    excerpt = parts[1]
                    url_part = parts[2]
                    
                    # Calculate space for title and URL (must be preserved)
                    title_and_url_space = len(title) + len(url_part) + 4  # + newlines
                    
                    if title_and_url_space < self.MAX_POST_LENGTH:
                        # Calculate remaining space for excerpt
                        excerpt_space = self.MAX_POST_LENGTH - title_and_url_space
                        
                        if excerpt_space > 10:  # Minimum meaningful excerpt length
                            truncator = Truncator(excerpt)
                            truncated_excerpt = truncator.chars(excerpt_space - 3, truncate='...')
                            final_content = f"{title}\n\n{truncated_excerpt}\n\n{url_part}"
                        else:
                            # Just title and URL
                            final_content = f"{title}\n\n{url_part}"
                    else:
                        # Even title and URL are too long, truncate everything
                        truncator = Truncator(content_without_hashtags)
                        final_content = truncator.chars(self.MAX_POST_LENGTH - 3, truncate='...')
                else:
                    # Fallback: truncate entire content
                    truncator = Truncator(content_without_hashtags)
                    final_content = truncator.chars(self.MAX_POST_LENGTH - 3, truncate='...')
                
                return final_content
            else:
                return content_without_hashtags
        else:
            # Remove some hashtags to fit
            truncator = Truncator(content)
            return truncator.chars(self.MAX_POST_LENGTH - 3, truncate='...')
    
    def get_featured_image_url(self, blog_post) -> Optional[str]:
        """
        Extract featured image URL for LinkedIn media.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            Full URL to featured image or None
        """
        # Try featured_image field first
        if hasattr(blog_post, 'featured_image') and blog_post.featured_image:
            try:
                return urljoin(self.base_url, blog_post.featured_image.url)
            except Exception as e:
                logger.warning(f"Could not get featured image URL for post {blog_post.id}: {e}")
        
        # Try social_image field
        if hasattr(blog_post, 'social_image') and blog_post.social_image:
            try:
                return urljoin(self.base_url, blog_post.social_image.url)
            except Exception as e:
                logger.warning(f"Could not get social image URL for post {blog_post.id}: {e}")
        
        # Try to find first image in media items
        if hasattr(blog_post, 'media_items'):
            try:
                first_image = blog_post.media_items.filter(
                    media_type='image',
                    original_image__isnull=False
                ).first()
                
                if first_image and first_image.original_image:
                    return urljoin(self.base_url, first_image.original_image.url)
            except Exception as e:
                logger.warning(f"Could not get media image URL for post {blog_post.id}: {e}")
        
        return None
    
    def validate_content(self, content: str) -> Tuple[bool, List[str]]:
        """
        Validate formatted content for LinkedIn posting.
        
        Args:
            content: Formatted LinkedIn post content
            
        Returns:
            Tuple of (is_valid: bool, errors: List[str])
        """
        errors = []
        
        # Check length
        if len(content) > self.MAX_POST_LENGTH:
            errors.append(f"Content exceeds LinkedIn limit of {self.MAX_POST_LENGTH} characters")
        
        # Check if content is empty
        if not content.strip():
            errors.append("Content cannot be empty")
        
        # Check for required URL
        if "http" not in content:
            errors.append("Content should include a URL to the blog post")
        
        # Check for excessive hashtags
        hashtag_count = len(re.findall(r'#\w+', content))
        if hashtag_count > self.MAX_HASHTAGS:
            errors.append(f"Too many hashtags ({hashtag_count}). Maximum is {self.MAX_HASHTAGS}")
        
        return len(errors) == 0, errors
    
    def format_for_preview(self, blog_post, include_excerpt: bool = True) -> Dict[str, str]:
        """
        Format content for preview purposes (admin interface, etc.).
        
        Args:
            blog_post: Blog Post model instance
            include_excerpt: Whether to include excerpt
            
        Returns:
            Dictionary with formatted content components
        """
        formatted_content = self.format_post_content(blog_post, include_excerpt)
        
        return {
            'full_content': formatted_content,
            'title': self._format_title(blog_post.title),
            'excerpt': self._format_excerpt(blog_post.excerpt) if blog_post.excerpt else self._extract_excerpt_from_content(blog_post.content),
            'url': self._get_post_url(blog_post),
            'hashtags': self._generate_hashtags(blog_post),
            'featured_image_url': self.get_featured_image_url(blog_post),
            'character_count': len(formatted_content),
            'is_valid': self.validate_content(formatted_content)[0],
            'validation_errors': self.validate_content(formatted_content)[1]
        }


# Convenience functions for easy usage
def format_blog_post_for_linkedin(blog_post, include_excerpt: bool = True) -> str:
    """
    Convenience function to format a blog post for LinkedIn.
    
    Args:
        blog_post: Blog Post model instance
        include_excerpt: Whether to include excerpt in the post
        
    Returns:
        Formatted LinkedIn post content
    """
    formatter = LinkedInContentFormatter()
    return formatter.format_post_content(blog_post, include_excerpt)


def get_blog_post_hashtags(blog_post) -> str:
    """
    Convenience function to get hashtags for a blog post.
    
    Args:
        blog_post: Blog Post model instance
        
    Returns:
        Formatted hashtags string
    """
    formatter = LinkedInContentFormatter()
    return formatter._generate_hashtags(blog_post)


def get_blog_post_featured_image(blog_post) -> Optional[str]:
    """
    Convenience function to get featured image URL for a blog post.
    
    Args:
        blog_post: Blog Post model instance
        
    Returns:
        Full URL to featured image or None
    """
    formatter = LinkedInContentFormatter()
    return formatter.get_featured_image_url(blog_post)


def validate_linkedin_content(content: str) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate LinkedIn content.
    
    Args:
        content: Formatted LinkedIn post content
        
    Returns:
        Tuple of (is_valid: bool, errors: List[str])
    """
    formatter = LinkedInContentFormatter()
    return formatter.validate_content(content)