"""
LinkedIn Image Service for handling image selection and processing for LinkedIn posts.

This service provides image handling logic for LinkedIn integration, including:
- Image selection from blog posts
- Image validation for LinkedIn compatibility
- Image metadata extraction and processing
- Fallback logic for when primary images are unavailable
- Comprehensive error handling and monitoring
"""

import os
import logging
import time
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urljoin, urlparse
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.files.storage import default_storage
from ..utils.image_processor import ImageProcessor, ImageProcessingError
from ..models import Post, MediaItem
from .linkedin_error_handler import LinkedInImageErrorHandler, ImageProcessingError as LinkedInImageProcessingError
from .linkedin_image_monitor import LinkedInImageMonitor
from .linkedin_task_monitor import LinkedInTaskMonitor


logger = logging.getLogger(__name__)


class LinkedInImageService:
    """
    Service class for handling image selection and processing for LinkedIn posts.
    
    Provides methods for:
    - Selecting the best image from a blog post
    - Validating images for LinkedIn compatibility
    - Processing images for LinkedIn requirements
    - Extracting image metadata
    - Implementing fallback logic
    """
    
    def __init__(self, base_url: str = None):
        """
        Initialize the LinkedIn image service.
        
        Args:
            base_url: Base URL for the website (used for absolute image URLs)
        """
        self.base_url = base_url or self._get_base_url()
        self.image_processor = ImageProcessor()
        self.error_handler = LinkedInImageErrorHandler()
        self.image_monitor = LinkedInImageMonitor()
        self.task_monitor = LinkedInTaskMonitor()
    
    def _get_base_url(self) -> str:
        """Get the base URL from Django settings or sites framework."""
        try:
            current_site = Site.objects.get_current()
            return f"https://{current_site.domain}"
        except ImportError:
            # Fallback if sites framework is not installed
            domain = getattr(settings, 'ALLOWED_HOSTS', ['localhost'])[0]
            if domain == '*':
                domain = 'localhost'
            return f"https://{domain}"
        except Exception:
            return "https://localhost"
    
    @staticmethod
    def get_post_image(blog_post: Post, task_id: str = None) -> Optional[str]:
        """
        Select the best image from a blog post for LinkedIn posting.
        
        Priority order:
        1. social_image (if available)
        2. featured_image (if available)
        3. First image from media_items
        4. None (no suitable image found)
        
        Args:
            blog_post: Blog Post model instance
            task_id: Optional task ID for monitoring
            
        Returns:
            Absolute URL to the best available image, or None if no image found
        """
        service = LinkedInImageService()
        start_time = time.time()
        
        # Add task step if task_id provided
        if task_id:
            service.task_monitor.add_task_step(
                task_id, 
                'image_selection', 
                {'post_id': blog_post.id, 'post_title': blog_post.title}
            )
        
        try:
            # Priority 1: Social image (specifically for social media sharing)
            if hasattr(blog_post, 'social_image') and blog_post.social_image:
                try:
                    image_url = urljoin(service.base_url, blog_post.social_image.url)
                    logger.debug(f"Found social_image for post {blog_post.id}: {image_url}")
                    
                    # Complete task step if successful
                    if task_id:
                        processing_time = time.time() - start_time
                        service.task_monitor.complete_task_step(
                            task_id, 
                            'image_selection', 
                            {'selected_image': image_url, 'image_source': 'social_image'}
                        )
                    
                    return image_url
                except Exception as e:
                    logger.warning(f"Could not get social_image URL for post {blog_post.id}: {e}")
            
            # Priority 2: Featured image
            if hasattr(blog_post, 'featured_image') and blog_post.featured_image:
                try:
                    image_url = urljoin(service.base_url, blog_post.featured_image.url)
                    logger.debug(f"Found featured_image for post {blog_post.id}: {image_url}")
                    
                    # Complete task step if successful
                    if task_id:
                        processing_time = time.time() - start_time
                        service.task_monitor.complete_task_step(
                            task_id, 
                            'image_selection', 
                            {'selected_image': image_url, 'image_source': 'featured_image'}
                        )
                    
                    return image_url
                except Exception as e:
                    logger.warning(f"Could not get featured_image URL for post {blog_post.id}: {e}")
            
            # Priority 3: First image from media items
            if hasattr(blog_post, 'media_items'):
                try:
                    # Look for featured media item first
                    featured_media = blog_post.media_items.filter(
                        media_type='image',
                        is_featured=True,
                        original_image__isnull=False
                    ).first()
                    
                    if featured_media and featured_media.original_image:
                        image_url = urljoin(service.base_url, featured_media.original_image.url)
                        logger.debug(f"Found featured media image for post {blog_post.id}: {image_url}")
                        
                        # Complete task step if successful
                        if task_id:
                            processing_time = time.time() - start_time
                            service.task_monitor.complete_task_step(
                                task_id, 
                                'image_selection', 
                                {'selected_image': image_url, 'image_source': 'featured_media'}
                            )
                        
                        return image_url
                    
                    # If no featured media, get first available image
                    first_media = blog_post.media_items.filter(
                        media_type='image',
                        original_image__isnull=False
                    ).order_by('order', 'created_at').first()
                    
                    if first_media and first_media.original_image:
                        image_url = urljoin(service.base_url, first_media.original_image.url)
                        logger.debug(f"Found first media image for post {blog_post.id}: {image_url}")
                        
                        # Complete task step if successful
                        if task_id:
                            processing_time = time.time() - start_time
                            service.task_monitor.complete_task_step(
                                task_id, 
                                'image_selection', 
                                {'selected_image': image_url, 'image_source': 'first_media'}
                            )
                        
                        return image_url
                        
                except Exception as e:
                    logger.warning(f"Could not get media image URL for post {blog_post.id}: {e}")
            
            logger.info(f"No suitable image found for post {blog_post.id}")
            
            # Complete task step with no image found
            if task_id:
                processing_time = time.time() - start_time
                service.task_monitor.complete_task_step(
                    task_id, 
                    'image_selection', 
                    {'selected_image': None, 'reason': 'no_images_available'}
                )
            
            return None
            
        except Exception as e:
            error = LinkedInImageProcessingError(
                f"Error selecting image for post {blog_post.id}: {e}",
                error_code='IMAGE_SELECTION_FAILED',
                is_retryable=False,
                context={'post_id': blog_post.id, 'post_title': blog_post.title}
            )
            
            # Handle error with comprehensive logging
            service.error_handler.handle_image_processing_error(
                error, '', 'image_selection', 
                {'post_id': blog_post.id, 'post_title': blog_post.title}
            )
            
            # Complete task step with error
            if task_id:
                service.task_monitor.complete_task_step(task_id, 'image_selection', error=error)
            
            return None
    
    @staticmethod
    def validate_image_for_linkedin(image_url: str, task_id: str = None) -> Tuple[bool, List[str]]:
        """
        Validate an image URL for LinkedIn compatibility.
        
        This method downloads the image temporarily and validates it against
        LinkedIn's requirements for dimensions, file size, and format.
        
        Args:
            image_url: URL of the image to validate
            task_id: Optional task ID for monitoring
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        service = LinkedInImageService()
        issues = []
        temp_file = None
        start_time = time.time()
        
        # Add task step if task_id provided
        if task_id:
            service.task_monitor.add_task_step(
                task_id, 
                'image_validation', 
                {'image_url': image_url}
            )
        
        try:
            # Check if URL is accessible
            if not image_url or not image_url.startswith(('http://', 'https://')):
                issues.append("Invalid image URL format")
                error = LinkedInImageProcessingError(
                    "Invalid image URL format",
                    image_url=image_url,
                    processing_step='image_validation',
                    error_code='INVALID_URL_FORMAT',
                    is_retryable=False
                )
                
                service.error_handler.handle_image_processing_error(
                    error, image_url, 'image_validation'
                )
                
                if task_id:
                    service.task_monitor.complete_task_step(task_id, 'image_validation', error=error)
                
                return False, issues
            
            # Download image temporarily for validation
            try:
                temp_file = ImageProcessor.download_and_process_image(
                    image_url, 
                    output_dir=getattr(settings, 'MEDIA_ROOT', '/tmp')
                )
            except ImageProcessingError as e:
                issues.append(f"Failed to download/process image: {str(e)}")
                error = LinkedInImageProcessingError(
                    f"Failed to download/process image: {str(e)}",
                    image_url=image_url,
                    processing_step='image_validation',
                    error_code='IMAGE_DOWNLOAD_FAILED',
                    is_retryable=True
                )
                
                service.error_handler.handle_image_processing_error(
                    error, image_url, 'image_validation'
                )
                
                if task_id:
                    service.task_monitor.complete_task_step(task_id, 'image_validation', error=error)
                
                return False, issues
            
            # Validate LinkedIn compatibility
            is_compatible, compatibility_issues = ImageProcessor.is_linkedin_compatible(temp_file)
            issues.extend(compatibility_issues)
            
            logger.debug(f"Image validation for {image_url}: {'valid' if is_compatible else 'invalid'}")
            if issues:
                logger.debug(f"Validation issues: {issues}")
            
            # Complete task step
            if task_id:
                processing_time = time.time() - start_time
                if is_compatible:
                    service.task_monitor.complete_task_step(
                        task_id, 
                        'image_validation', 
                        {'is_valid': True, 'issues': issues, 'validation_time': processing_time}
                    )
                else:
                    error = LinkedInImageProcessingError(
                        f"Image validation failed: {', '.join(issues)}",
                        image_url=image_url,
                        processing_step='image_validation',
                        error_code='IMAGE_VALIDATION_FAILED',
                        is_retryable=False
                    )
                    service.task_monitor.complete_task_step(task_id, 'image_validation', error=error)
            
            return is_compatible, issues
            
        except Exception as e:
            logger.error(f"Error validating image {image_url}: {e}")
            issues.append(f"Validation error: {str(e)}")
            
            error = LinkedInImageProcessingError(
                f"Validation error: {str(e)}",
                image_url=image_url,
                processing_step='image_validation',
                error_code='VALIDATION_ERROR',
                is_retryable=True
            )
            
            service.error_handler.handle_image_processing_error(
                error, image_url, 'image_validation'
            )
            
            if task_id:
                service.task_monitor.complete_task_step(task_id, 'image_validation', error=error)
            
            return False, issues
            
        finally:
            # Cleanup temporary file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logger.warning(f"Could not remove temp file {temp_file}: {e}")
    
    @staticmethod
    def get_image_metadata(image_url: str) -> Dict[str, Any]:
        """
        Extract metadata from an image URL.
        
        Downloads the image temporarily and extracts comprehensive metadata
        including dimensions, format, file size, and other properties.
        
        Args:
            image_url: URL of the image to analyze
            
        Returns:
            Dictionary containing image metadata
        """
        metadata = {
            'url': image_url,
            'accessible': False,
            'linkedin_compatible': False,
            'error': None
        }
        
        temp_file = None
        
        try:
            # Validate URL format
            if not image_url or not image_url.startswith(('http://', 'https://')):
                metadata['error'] = "Invalid image URL format"
                return metadata
            
            # Download image temporarily
            try:
                temp_file = ImageProcessor.download_and_process_image(
                    image_url,
                    output_dir=getattr(settings, 'MEDIA_ROOT', '/tmp')
                )
                metadata['accessible'] = True
            except ImageProcessingError as e:
                metadata['error'] = f"Failed to download image: {str(e)}"
                return metadata
            
            # Extract basic metadata
            image_metadata = ImageProcessor.get_image_metadata(temp_file)
            metadata.update(image_metadata)
            
            # Check LinkedIn compatibility
            is_compatible, issues = ImageProcessor.is_linkedin_compatible(temp_file)
            metadata['linkedin_compatible'] = is_compatible
            metadata['compatibility_issues'] = issues
            
            # Add LinkedIn-specific analysis
            metadata['linkedin_analysis'] = {
                'meets_min_dimensions': (
                    metadata.get('width', 0) >= ImageProcessor.MIN_DIMENSIONS[0] and
                    metadata.get('height', 0) >= ImageProcessor.MIN_DIMENSIONS[1]
                ),
                'within_max_dimensions': (
                    metadata.get('width', 0) <= ImageProcessor.MAX_DIMENSIONS[0] and
                    metadata.get('height', 0) <= ImageProcessor.MAX_DIMENSIONS[1]
                ),
                'within_file_size_limit': metadata.get('file_size', 0) <= ImageProcessor.MAX_FILE_SIZE,
                'supported_format': metadata.get('format') in ImageProcessor.SUPPORTED_FORMATS,
                'aspect_ratio_acceptable': (
                    ImageProcessor.MIN_ASPECT_RATIO <= 
                    metadata.get('aspect_ratio', 0) <= 
                    ImageProcessor.MAX_ASPECT_RATIO
                ) if metadata.get('aspect_ratio') else False
            }
            
            logger.debug(f"Extracted metadata for {image_url}: {metadata['format']} "
                        f"{metadata.get('width')}x{metadata.get('height')} "
                        f"({metadata.get('file_size')} bytes)")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {image_url}: {e}")
            metadata['error'] = str(e)
            return metadata
            
        finally:
            # Cleanup temporary file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logger.warning(f"Could not remove temp file {temp_file}: {e}")
    
    @staticmethod
    def get_fallback_images(blog_post: Post) -> List[str]:
        """
        Get a list of fallback images for a blog post.
        
        Returns all available images from the post in priority order,
        useful when the primary image fails validation or processing.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            List of absolute URLs to available images
        """
        service = LinkedInImageService()
        fallback_images = []
        
        try:
            # Collect all possible images
            image_sources = []
            
            # Add social_image
            if hasattr(blog_post, 'social_image') and blog_post.social_image:
                try:
                    image_sources.append({
                        'url': urljoin(service.base_url, blog_post.social_image.url),
                        'type': 'social_image',
                        'priority': 1
                    })
                except Exception as e:
                    logger.warning(f"Could not get social_image URL for post {blog_post.id}: {e}")
            
            # Add featured_image
            if hasattr(blog_post, 'featured_image') and blog_post.featured_image:
                try:
                    image_sources.append({
                        'url': urljoin(service.base_url, blog_post.featured_image.url),
                        'type': 'featured_image',
                        'priority': 2
                    })
                except Exception as e:
                    logger.warning(f"Could not get featured_image URL for post {blog_post.id}: {e}")
            
            # Add media items
            if hasattr(blog_post, 'media_items'):
                try:
                    media_items = blog_post.media_items.filter(
                        media_type='image',
                        original_image__isnull=False
                    ).order_by('order', 'created_at')
                    
                    for i, media_item in enumerate(media_items):
                        if media_item.original_image:
                            try:
                                image_sources.append({
                                    'url': urljoin(service.base_url, media_item.original_image.url),
                                    'type': 'media_item',
                                    'priority': 3 + i,
                                    'media_id': media_item.id
                                })
                            except Exception as e:
                                logger.warning(f"Could not get media image URL for item {media_item.id}: {e}")
                                
                except Exception as e:
                    logger.warning(f"Could not get media items for post {blog_post.id}: {e}")
            
            # Sort by priority and extract URLs
            image_sources.sort(key=lambda x: x['priority'])
            fallback_images = [source['url'] for source in image_sources]
            
            # Remove duplicates while preserving order
            seen = set()
            unique_images = []
            for img_url in fallback_images:
                if img_url not in seen:
                    seen.add(img_url)
                    unique_images.append(img_url)
            
            logger.debug(f"Found {len(unique_images)} fallback images for post {blog_post.id}")
            return unique_images
            
        except Exception as e:
            logger.error(f"Error getting fallback images for post {blog_post.id}: {e}")
            return []
    
    @staticmethod
    def select_best_compatible_image(blog_post: Post) -> Optional[str]:
        """
        Select the best LinkedIn-compatible image from a blog post.
        
        This method tries each available image in priority order and returns
        the first one that passes LinkedIn validation.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            URL of the best compatible image, or None if no compatible image found
        """
        try:
            # Get all available images in priority order
            candidate_images = LinkedInImageService.get_fallback_images(blog_post)
            
            if not candidate_images:
                logger.info(f"No images available for post {blog_post.id}")
                return None
            
            logger.debug(f"Testing {len(candidate_images)} candidate images for post {blog_post.id}")
            
            # Test each image for LinkedIn compatibility
            for i, image_url in enumerate(candidate_images):
                logger.debug(f"Testing image {i+1}/{len(candidate_images)}: {image_url}")
                
                is_valid, issues = LinkedInImageService.validate_image_for_linkedin(image_url)
                
                if is_valid:
                    logger.info(f"Found compatible image for post {blog_post.id}: {image_url}")
                    return image_url
                else:
                    logger.debug(f"Image {image_url} not compatible: {issues}")
            
            logger.warning(f"No LinkedIn-compatible images found for post {blog_post.id}")
            return None
            
        except Exception as e:
            logger.error(f"Error selecting compatible image for post {blog_post.id}: {e}")
            return None
    
    @staticmethod
    def process_image_for_linkedin(image_url: str, output_filename: str = None) -> Optional[str]:
        """
        Process an image to make it LinkedIn-compatible.
        
        Downloads the image, processes it according to LinkedIn requirements,
        and returns the path to the processed image.
        
        Args:
            image_url: URL of the image to process
            output_filename: Optional filename for the processed image
            
        Returns:
            Path to the processed image file, or None if processing failed
        """
        try:
            # Validate input
            if not image_url or not image_url.startswith(('http://', 'https://')):
                logger.error(f"Invalid image URL: {image_url}")
                return None
            
            # Set up output path
            if output_filename is None:
                parsed_url = urlparse(image_url)
                base_name = os.path.splitext(os.path.basename(parsed_url.path))[0]
                if not base_name:
                    base_name = 'linkedin_image'
                output_filename = f"{base_name}_linkedin.jpg"
            
            output_dir = os.path.join(getattr(settings, 'MEDIA_ROOT', '/tmp'), 'linkedin_images')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)
            
            # Download and process image
            try:
                processed_path = ImageProcessor.download_and_process_image(
                    image_url, 
                    output_dir=output_dir
                )
                
                # Further process for LinkedIn if needed
                final_path = ImageProcessor.process_for_linkedin(processed_path, output_path)
                
                # Clean up intermediate file if different
                if processed_path != final_path and os.path.exists(processed_path):
                    os.remove(processed_path)
                
                logger.info(f"Successfully processed image for LinkedIn: {image_url} -> {final_path}")
                return final_path
                
            except ImageProcessingError as e:
                logger.error(f"Failed to process image {image_url}: {e}")
                return None
            
        except Exception as e:
            logger.error(f"Error processing image for LinkedIn {image_url}: {e}")
            return None
    
    @staticmethod
    def get_image_for_linkedin_post(blog_post: Post, validate: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get the best image for a LinkedIn post with comprehensive information.
        
        This is the main method that combines image selection, validation,
        and metadata extraction to provide complete image information for LinkedIn posting.
        
        Args:
            blog_post: Blog Post model instance
            validate: Whether to validate the image for LinkedIn compatibility
            
        Returns:
            Dictionary with image information, or None if no suitable image found
        """
        try:
            # Select the best image
            if validate:
                image_url = LinkedInImageService.select_best_compatible_image(blog_post)
            else:
                image_url = LinkedInImageService.get_post_image(blog_post)
            
            if not image_url:
                logger.info(f"No suitable image found for LinkedIn post {blog_post.id}")
                return None
            
            # Get image metadata
            metadata = LinkedInImageService.get_image_metadata(image_url)
            
            # Prepare result
            result = {
                'url': image_url,
                'metadata': metadata,
                'linkedin_compatible': metadata.get('linkedin_compatible', False),
                'compatibility_issues': metadata.get('compatibility_issues', []),
                'post_id': blog_post.id,
                'post_title': blog_post.title,
                'selected_at': None  # Will be set when actually used
            }
            
            # Add fallback information
            fallback_images = LinkedInImageService.get_fallback_images(blog_post)
            result['fallback_images_available'] = len(fallback_images) - 1  # Exclude the selected one
            result['total_images_available'] = len(fallback_images)
            
            logger.info(f"Selected image for LinkedIn post {blog_post.id}: {image_url} "
                       f"(compatible: {result['linkedin_compatible']})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting image for LinkedIn post {blog_post.id}: {e}")
            return None