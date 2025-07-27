"""
Multimedia service for handling image processing, video embeds, and media optimization.
"""
import os
import re
import uuid
from io import BytesIO
from urllib.parse import urlparse, parse_qs
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils.text import slugify
import logging

logger = logging.getLogger(__name__)


class MultimediaService:
    """Service for handling multimedia content processing and optimization."""
    
    # Image size configurations
    IMAGE_SIZES = {
        'thumbnail': (300, 200),
        'medium': (800, 600),
        'large': (1200, 800),
        'social': (1200, 630),  # For social media sharing
    }
    
    # Supported image formats
    SUPPORTED_IMAGE_FORMATS = ['JPEG', 'PNG', 'WebP', 'GIF']
    
    # Video platform patterns
    VIDEO_PATTERNS = {
        'youtube': [
            r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        ],
        'vimeo': [
            r'(?:https?://)?(?:www\.)?vimeo\.com/(\d+)',
            r'(?:https?://)?player\.vimeo\.com/video/(\d+)',
        ]
    }

    def process_image_upload(self, image_file, sizes=None, optimize=True):
        """
        Process uploaded image and generate multiple sizes.
        
        Args:
            image_file: Django UploadedFile object
            sizes: List of size names to generate (default: all sizes)
            optimize: Whether to optimize images for web
            
        Returns:
            dict: Dictionary with paths to generated images
        """
        if sizes is None:
            sizes = list(self.IMAGE_SIZES.keys())
            
        try:
            # Open and process the original image
            with Image.open(image_file) as img:
                # Convert to RGB if necessary (for JPEG compatibility)
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Auto-rotate based on EXIF data
                img = ImageOps.exif_transpose(img)
                
                # Generate filename base
                original_name = os.path.splitext(image_file.name)[0]
                safe_name = slugify(original_name)
                
                results = {}
                
                # Generate different sizes
                for size_name in sizes:
                    if size_name not in self.IMAGE_SIZES:
                        continue
                        
                    target_size = self.IMAGE_SIZES[size_name]
                    processed_img = self._resize_image(img, target_size)
                    
                    # Save processed image
                    filename = f"{safe_name}_{size_name}_{uuid.uuid4().hex[:8]}.jpg"
                    file_path = f"blog_images/processed/{filename}"
                    
                    # Convert to bytes
                    img_io = BytesIO()
                    quality = 85 if optimize else 95
                    processed_img.save(img_io, format='JPEG', quality=quality, optimize=optimize)
                    img_io.seek(0)
                    
                    # Save to storage
                    saved_path = default_storage.save(file_path, ContentFile(img_io.getvalue()))
                    results[size_name] = saved_path
                    
                return results
                
        except Exception as e:
            logger.error(f"Error processing image {image_file.name}: {str(e)}")
            raise
    
    def _resize_image(self, img, target_size):
        """
        Resize image while maintaining aspect ratio.
        
        Args:
            img: PIL Image object
            target_size: Tuple of (width, height)
            
        Returns:
            PIL Image object
        """
        # Calculate aspect ratios
        img_ratio = img.width / img.height
        target_ratio = target_size[0] / target_size[1]
        
        if img_ratio > target_ratio:
            # Image is wider than target ratio
            new_width = target_size[0]
            new_height = int(target_size[0] / img_ratio)
        else:
            # Image is taller than target ratio
            new_height = target_size[1]
            new_width = int(target_size[1] * img_ratio)
        
        # Resize image
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # If the resized image is smaller than target, pad it
        if new_width < target_size[0] or new_height < target_size[1]:
            # Create a new image with target size and paste the resized image
            padded_img = Image.new('RGB', target_size, (255, 255, 255))
            paste_x = (target_size[0] - new_width) // 2
            paste_y = (target_size[1] - new_height) // 2
            padded_img.paste(resized_img, (paste_x, paste_y))
            return padded_img
        
        return resized_img
    
    def generate_responsive_images(self, image_path):
        """
        Generate responsive image sizes from an existing image.
        
        Args:
            image_path: Path to the original image
            
        Returns:
            dict: Dictionary with responsive image information
        """
        try:
            if not default_storage.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            with default_storage.open(image_path, 'rb') as f:
                with Image.open(f) as img:
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    
                    # Auto-rotate based on EXIF data
                    img = ImageOps.exif_transpose(img)
                    
                    # Generate filename base
                    base_name = os.path.splitext(os.path.basename(image_path))[0]
                    dir_name = os.path.dirname(image_path)
                    
                    results = {
                        'original': {
                            'url': default_storage.url(image_path),
                            'width': img.width,
                            'height': img.height,
                        }
                    }
                    
                    # Generate different sizes
                    for size_name, target_size in self.IMAGE_SIZES.items():
                        # Skip if original is smaller than target
                        if img.width < target_size[0] and img.height < target_size[1]:
                            continue
                            
                        processed_img = self._resize_image(img, target_size)
                        
                        # Save processed image
                        filename = f"{base_name}_{size_name}.jpg"
                        file_path = os.path.join(dir_name, 'responsive', filename)
                        
                        # Convert to bytes
                        img_io = BytesIO()
                        processed_img.save(img_io, format='JPEG', quality=85, optimize=True)
                        img_io.seek(0)
                        
                        # Save to storage
                        saved_path = default_storage.save(file_path, ContentFile(img_io.getvalue()))
                        
                        results[size_name] = {
                            'url': default_storage.url(saved_path),
                            'width': processed_img.width,
                            'height': processed_img.height,
                        }
                    
                    return results
                    
        except Exception as e:
            logger.error(f"Error generating responsive images for {image_path}: {str(e)}")
            raise
    
    def extract_video_embed(self, url):
        """
        Extract video embed information from URL.
        
        Args:
            url: Video URL
            
        Returns:
            dict: Video embed information or None if not supported
        """
        if not url:
            return None
            
        # Clean up the URL
        url = url.strip()
        
        # Check YouTube patterns
        for pattern in self.VIDEO_PATTERNS['youtube']:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                return {
                    'platform': 'youtube',
                    'video_id': video_id,
                    'embed_url': f'https://www.youtube.com/embed/{video_id}',
                    'thumbnail_url': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
                    'watch_url': f'https://www.youtube.com/watch?v={video_id}',
                }
        
        # Check Vimeo patterns
        for pattern in self.VIDEO_PATTERNS['vimeo']:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                return {
                    'platform': 'vimeo',
                    'video_id': video_id,
                    'embed_url': f'https://player.vimeo.com/video/{video_id}',
                    'thumbnail_url': f'https://vumbnail.com/{video_id}.jpg',
                    'watch_url': f'https://vimeo.com/{video_id}',
                }
        
        return None
    
    def create_image_gallery(self, images):
        """
        Create image gallery data structure.
        
        Args:
            images: List of image paths or image objects
            
        Returns:
            list: Gallery data with responsive images
        """
        gallery = []
        
        for i, image in enumerate(images):
            try:
                if hasattr(image, 'url'):
                    # Django ImageField
                    image_path = image.name
                    image_url = image.url
                else:
                    # String path
                    image_path = image
                    image_url = default_storage.url(image_path)
                
                # Generate responsive images
                responsive_data = self.generate_responsive_images(image_path)
                
                gallery_item = {
                    'id': i,
                    'original': responsive_data.get('original', {'url': image_url}),
                    'responsive': responsive_data,
                    'alt': f'Gallery image {i + 1}',
                }
                
                gallery.append(gallery_item)
                
            except Exception as e:
                logger.error(f"Error processing gallery image {image}: {str(e)}")
                continue
        
        return gallery
    
    def optimize_image_for_web(self, image_path, quality=85):
        """
        Optimize an existing image for web delivery.
        
        Args:
            image_path: Path to the image
            quality: JPEG quality (1-100)
            
        Returns:
            str: Path to optimized image
        """
        try:
            if not default_storage.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            with default_storage.open(image_path, 'rb') as f:
                with Image.open(f) as img:
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    
                    # Auto-rotate based on EXIF data
                    img = ImageOps.exif_transpose(img)
                    
                    # Generate optimized filename
                    base_name = os.path.splitext(os.path.basename(image_path))[0]
                    dir_name = os.path.dirname(image_path)
                    filename = f"{base_name}_optimized.jpg"
                    file_path = os.path.join(dir_name, filename)
                    
                    # Convert to bytes with optimization
                    img_io = BytesIO()
                    img.save(img_io, format='JPEG', quality=quality, optimize=True)
                    img_io.seek(0)
                    
                    # Save optimized image
                    saved_path = default_storage.save(file_path, ContentFile(img_io.getvalue()))
                    return saved_path
                    
        except Exception as e:
            logger.error(f"Error optimizing image {image_path}: {str(e)}")
            raise
    
    def get_image_info(self, image_path):
        """
        Get information about an image.
        
        Args:
            image_path: Path to the image
            
        Returns:
            dict: Image information
        """
        try:
            if not default_storage.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            with default_storage.open(image_path, 'rb') as f:
                with Image.open(f) as img:
                    return {
                        'width': img.width,
                        'height': img.height,
                        'format': img.format,
                        'mode': img.mode,
                        'size_bytes': default_storage.size(image_path),
                        'url': default_storage.url(image_path),
                    }
                    
        except Exception as e:
            logger.error(f"Error getting image info for {image_path}: {str(e)}")
            return None
    
    def validate_image_upload(self, image_file, max_size_mb=10):
        """
        Validate uploaded image file.
        
        Args:
            image_file: Django UploadedFile object
            max_size_mb: Maximum file size in MB
            
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            # Check file size
            if image_file.size > max_size_mb * 1024 * 1024:
                return False, f"File size exceeds {max_size_mb}MB limit"
            
            # Check if it's a valid image
            with Image.open(image_file) as img:
                # Check format
                if img.format not in self.SUPPORTED_IMAGE_FORMATS:
                    return False, f"Unsupported format. Supported: {', '.join(self.SUPPORTED_IMAGE_FORMATS)}"
                
                # Check dimensions (reasonable limits)
                if img.width > 5000 or img.height > 5000:
                    return False, "Image dimensions too large (max 5000x5000)"
                
                if img.width < 50 or img.height < 50:
                    return False, "Image dimensions too small (min 50x50)"
            
            return True, None
            
        except Exception as e:
            return False, f"Invalid image file: {str(e)}"


# Global instance
multimedia_service = MultimediaService()