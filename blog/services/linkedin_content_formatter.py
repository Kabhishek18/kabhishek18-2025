"""
LinkedIn Content Formatting Utilities

This module provides utilities for formatting blog post content for LinkedIn posting.
Handles character limits, hashtag generation, and media URL extraction.
"""

import re
import logging
from typing import List, Optional, Dict, Tuple, Any
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.conf import settings
from urllib.parse import urljoin
from .linkedin_image_service import LinkedInImageService


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
    
    def format_post_content(self, blog_post, include_excerpt: bool = True, optimize_for_images: bool = True) -> str:
        """
        Format a blog post for LinkedIn posting with image considerations.
        
        Args:
            blog_post: Blog Post model instance
            include_excerpt: Whether to include the excerpt in the post
            optimize_for_images: Whether to optimize content length for image posts
            
        Returns:
            Formatted LinkedIn post content
        """
        # Get the blog post URL
        post_url = self._get_post_url(blog_post)
        
        # Format title with length limit
        title = self._format_title(blog_post.title)
        
        # Check if we have images available for this post
        has_images = False
        if optimize_for_images:
            try:
                available_images = self.get_post_images(blog_post)
                has_images = len(available_images) > 0
                logger.debug(f"Post {blog_post.id} has {len(available_images)} images available")
            except Exception as e:
                logger.warning(f"Could not check images for post {blog_post.id}: {e}")
        
        # Format content/excerpt with image considerations
        content = ""
        if include_excerpt and blog_post.excerpt:
            content = self._format_excerpt(blog_post.excerpt)
        elif include_excerpt and not blog_post.excerpt:
            # Extract excerpt from content if no explicit excerpt
            content = self._extract_excerpt_from_content(blog_post.content)
        
        # If we have images, we might want to shorten text content slightly
        # to leave more visual focus on the image
        if has_images and content and optimize_for_images:
            # Reduce excerpt length slightly for image posts to balance visual elements
            image_optimized_length = int(self.MAX_EXCERPT_LENGTH * 0.85)  # 15% shorter
            if len(content) > image_optimized_length:
                truncator = Truncator(content)
                content = truncator.chars(image_optimized_length - 3, truncate='...')
                logger.debug(f"Shortened excerpt for image post {blog_post.id}")
        
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
        final_content = self._apply_character_limit(formatted_post, post_url, hashtag_string)
        
        # Log formatting result
        if has_images:
            logger.debug(f"Formatted post {blog_post.id} for LinkedIn with image optimization: "
                        f"{len(final_content)} characters")
        
        return final_content
    
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
    
    def get_post_images(self, blog_post) -> List[str]:
        """
        Extract multiple images from blog posts for LinkedIn posting.
        
        Returns all available images from the blog post in priority order,
        including featured image, social image, and media items.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            List of absolute URLs to available images
        """
        try:
            # Use the LinkedIn image service to get all fallback images
            return LinkedInImageService.get_fallback_images(blog_post)
        except Exception as e:
            logger.error(f"Error getting post images for {blog_post.id}: {e}")
            return []
    
    def select_best_image_for_linkedin(self, blog_post) -> Optional[str]:
        """
        Select the optimal image for LinkedIn posting from available images.
        
        This method uses the LinkedIn image service to find the best image
        that meets LinkedIn's requirements for dimensions, format, and file size.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            URL of the best LinkedIn-compatible image, or None if no suitable image found
        """
        try:
            # Use the LinkedIn image service to select the best compatible image
            return LinkedInImageService.select_best_compatible_image(blog_post)
        except Exception as e:
            logger.error(f"Error selecting best image for LinkedIn for post {blog_post.id}: {e}")
            return None
    
    def validate_image_compatibility(self, image_url: str) -> bool:
        """
        Validate if an image meets LinkedIn's requirements.
        
        Checks the image against LinkedIn's specifications for:
        - Supported formats (JPEG, PNG, GIF)
        - Dimension requirements (200x200 to 7680x4320 pixels)
        - File size limits (max 20MB)
        - Aspect ratio constraints
        
        Args:
            image_url: URL of the image to validate
            
        Returns:
            True if image is compatible with LinkedIn, False otherwise
        """
        try:
            is_valid, issues = LinkedInImageService.validate_image_for_linkedin(image_url)
            if not is_valid and issues:
                logger.debug(f"Image {image_url} validation issues: {issues}")
            return is_valid
        except Exception as e:
            logger.error(f"Error validating image compatibility for {image_url}: {e}")
            return False

    def get_featured_image_url(self, blog_post) -> Optional[str]:
        """
        Extract featured image URL for LinkedIn media.
        
        This method is maintained for backward compatibility but now uses
        the LinkedIn image service for consistent image selection logic.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            Full URL to featured image or None
        """
        try:
            # Use the LinkedIn image service for consistent image selection
            return LinkedInImageService.get_post_image(blog_post)
        except Exception as e:
            logger.error(f"Error getting featured image URL for post {blog_post.id}: {e}")
            return None
    
    def get_image_info_for_linkedin(self, blog_post) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive image information for LinkedIn posting.
        
        This method provides all the image information needed for LinkedIn posting,
        including the best image, metadata, and compatibility information.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            Dictionary with comprehensive image information, or None if no suitable image
        """
        try:
            # Get comprehensive image information from the LinkedIn image service
            return LinkedInImageService.get_image_for_linkedin_post(blog_post, validate=True)
        except Exception as e:
            logger.error(f"Error getting image info for LinkedIn post {blog_post.id}: {e}")
            return None
    
    def format_post_with_image_info(self, blog_post, include_excerpt: bool = True) -> Dict[str, Any]:
        """
        Format a blog post for LinkedIn with comprehensive image information.
        
        This method combines content formatting with image analysis to provide
        everything needed for LinkedIn posting with images.
        
        Args:
            blog_post: Blog Post model instance
            include_excerpt: Whether to include excerpt in the post
            
        Returns:
            Dictionary with formatted content and image information
        """
        try:
            # Format the text content
            formatted_content = self.format_post_content(blog_post, include_excerpt, optimize_for_images=True)
            
            # Get image information
            image_info = self.get_image_info_for_linkedin(blog_post)
            
            # Validate content with image considerations
            validation_result = self.validate_content(formatted_content, blog_post, include_image_validation=True)
            
            # Prepare comprehensive result
            result = {
                # Content information
                'content': formatted_content,
                'character_count': len(formatted_content),
                'is_valid': validation_result[0],
                'validation_errors': validation_result[1],
                
                # Post metadata
                'post_id': blog_post.id,
                'post_title': blog_post.title,
                'post_url': self._get_post_url(blog_post),
                
                # Image information
                'has_image': image_info is not None,
                'image_info': image_info,
                
                # Posting strategy
                'posting_strategy': 'image_post' if image_info else 'text_only_post',
                'ready_for_posting': validation_result[0] and (image_info is not None or True)  # Text-only is also valid
            }
            
            # Add image-specific details if available
            if image_info:
                result.update({
                    'image_url': image_info.get('url'),
                    'image_compatible': image_info.get('linkedin_compatible', False),
                    'image_issues': image_info.get('compatibility_issues', []),
                    'fallback_images_count': image_info.get('fallback_images_available', 0)
                })
            
            logger.debug(f"Formatted post {blog_post.id} with image info: "
                        f"strategy={result['posting_strategy']}, "
                        f"has_image={result['has_image']}, "
                        f"ready={result['ready_for_posting']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error formatting post with image info for {blog_post.id}: {e}")
            # Return basic fallback result
            return {
                'content': self.format_post_content(blog_post, include_excerpt),
                'has_image': False,
                'image_info': None,
                'posting_strategy': 'text_only_post',
                'ready_for_posting': False,
                'error': str(e)
            }
    
    def validate_content(self, content: str, blog_post=None, include_image_validation: bool = True) -> Tuple[bool, List[str]]:
        """
        Validate formatted content for LinkedIn posting, including image considerations.
        
        Args:
            content: Formatted LinkedIn post content
            blog_post: Optional blog post instance for image validation
            include_image_validation: Whether to validate associated images
            
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
        
        # Image validation if blog post is provided
        if blog_post and include_image_validation:
            try:
                # Check if there are images available
                available_images = self.get_post_images(blog_post)
                if available_images:
                    # Check if at least one image is LinkedIn compatible
                    compatible_image = self.select_best_image_for_linkedin(blog_post)
                    if not compatible_image:
                        # This is a warning, not an error - post can still be text-only
                        logger.warning(f"No LinkedIn-compatible images found for post {blog_post.id}")
                        # Could add this as a warning rather than error:
                        # errors.append("No LinkedIn-compatible images available (post will be text-only)")
                else:
                    logger.debug(f"No images available for post {blog_post.id}")
            except Exception as e:
                logger.error(f"Error during image validation for post {blog_post.id if blog_post else 'unknown'}: {e}")
                # Don't fail validation due to image validation errors
        
        return len(errors) == 0, errors
    
    def format_for_preview(self, blog_post, include_excerpt: bool = True, include_image_analysis: bool = True) -> Dict[str, str]:
        """
        Format content for preview purposes (admin interface, etc.) with enhanced image information.
        
        Args:
            blog_post: Blog Post model instance
            include_excerpt: Whether to include excerpt
            include_image_analysis: Whether to include detailed image analysis
            
        Returns:
            Dictionary with formatted content components and image information
        """
        formatted_content = self.format_post_content(blog_post, include_excerpt)
        validation_result = self.validate_content(formatted_content, blog_post, include_image_validation=True)
        
        result = {
            'full_content': formatted_content,
            'title': self._format_title(blog_post.title),
            'excerpt': self._format_excerpt(blog_post.excerpt) if blog_post.excerpt else self._extract_excerpt_from_content(blog_post.content),
            'url': self._get_post_url(blog_post),
            'hashtags': self._generate_hashtags(blog_post),
            'featured_image_url': self.get_featured_image_url(blog_post),
            'character_count': len(formatted_content),
            'is_valid': validation_result[0],
            'validation_errors': validation_result[1]
        }
        
        # Add enhanced image information if requested
        if include_image_analysis:
            try:
                # Get all available images
                available_images = self.get_post_images(blog_post)
                result['available_images'] = available_images
                result['total_images_count'] = len(available_images)
                
                # Get the best LinkedIn-compatible image
                best_image = self.select_best_image_for_linkedin(blog_post)
                result['best_linkedin_image'] = best_image
                result['has_linkedin_compatible_image'] = best_image is not None
                
                # Image compatibility analysis
                if available_images:
                    compatible_count = 0
                    image_analysis = []
                    
                    for img_url in available_images[:5]:  # Limit analysis to first 5 images
                        is_compatible = self.validate_image_compatibility(img_url)
                        if is_compatible:
                            compatible_count += 1
                        
                        image_analysis.append({
                            'url': img_url,
                            'linkedin_compatible': is_compatible
                        })
                    
                    result['image_analysis'] = image_analysis
                    result['compatible_images_count'] = compatible_count
                    result['image_compatibility_rate'] = (
                        compatible_count / len(available_images) * 100 
                        if available_images else 0
                    )
                else:
                    result['image_analysis'] = []
                    result['compatible_images_count'] = 0
                    result['image_compatibility_rate'] = 0
                
            except Exception as e:
                logger.error(f"Error during image analysis for preview of post {blog_post.id}: {e}")
                # Set default values on error
                result.update({
                    'available_images': [],
                    'total_images_count': 0,
                    'best_linkedin_image': None,
                    'has_linkedin_compatible_image': False,
                    'image_analysis': [],
                    'compatible_images_count': 0,
                    'image_compatibility_rate': 0
                })
        
        return result


# Convenience functions for easy usage
def format_blog_post_for_linkedin(blog_post, include_excerpt: bool = True, optimize_for_images: bool = True) -> str:
    """
    Convenience function to format a blog post for LinkedIn with image optimization.
    
    Args:
        blog_post: Blog Post model instance
        include_excerpt: Whether to include excerpt in the post
        optimize_for_images: Whether to optimize content for image posts
        
    Returns:
        Formatted LinkedIn post content
    """
    formatter = LinkedInContentFormatter()
    return formatter.format_post_content(blog_post, include_excerpt, optimize_for_images)


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


def get_blog_post_images(blog_post) -> List[str]:
    """
    Convenience function to get all available images from a blog post.
    
    Args:
        blog_post: Blog Post model instance
        
    Returns:
        List of absolute URLs to available images
    """
    formatter = LinkedInContentFormatter()
    return formatter.get_post_images(blog_post)


def get_best_linkedin_image(blog_post) -> Optional[str]:
    """
    Convenience function to get the best LinkedIn-compatible image for a blog post.
    
    Args:
        blog_post: Blog Post model instance
        
    Returns:
        URL of the best LinkedIn-compatible image, or None if no suitable image found
    """
    formatter = LinkedInContentFormatter()
    return formatter.select_best_image_for_linkedin(blog_post)


def validate_image_for_linkedin(image_url: str) -> bool:
    """
    Convenience function to validate if an image is LinkedIn-compatible.
    
    Args:
        image_url: URL of the image to validate
        
    Returns:
        True if image is compatible with LinkedIn, False otherwise
    """
    formatter = LinkedInContentFormatter()
    return formatter.validate_image_compatibility(image_url)


def get_linkedin_post_with_images(blog_post, include_excerpt: bool = True) -> Dict[str, Any]:
    """
    Convenience function to get comprehensive LinkedIn post information with images.
    
    Args:
        blog_post: Blog Post model instance
        include_excerpt: Whether to include excerpt in the post
        
    Returns:
        Dictionary with formatted content and image information
    """
    formatter = LinkedInContentFormatter()
    return formatter.format_post_with_image_info(blog_post, include_excerpt)


def validate_linkedin_content(content: str, blog_post=None, include_image_validation: bool = True) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate LinkedIn content with image considerations.
    
    Args:
        content: Formatted LinkedIn post content
        blog_post: Optional blog post instance for image validation
        include_image_validation: Whether to validate associated images
        
    Returns:
        Tuple of (is_valid: bool, errors: List[str])
    """
    formatter = LinkedInContentFormatter()
    return formatter.validate_content(content, blog_post, include_image_validation)