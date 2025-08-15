"""
Image processing utility for LinkedIn image handling.

This module provides image validation, resizing, format conversion, and optimization
functionality specifically tailored for LinkedIn's image requirements.
"""

import os
import logging
from typing import Tuple, Dict, Any, Optional, List
from PIL import Image, ImageOps
from io import BytesIO
import requests
from urllib.parse import urlparse
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


class ImageProcessingError(Exception):
    """Custom exception for image processing errors."""
    pass


class ImageProcessor:
    """
    Utility class for processing images for LinkedIn posting.
    
    Handles image validation, resizing, format conversion, and optimization
    according to LinkedIn's image requirements.
    """
    
    # LinkedIn image requirements
    SUPPORTED_FORMATS = ['JPEG', 'PNG', 'GIF']
    MIN_DIMENSIONS = (200, 200)  # width, height
    MAX_DIMENSIONS = (7680, 4320)  # width, height
    RECOMMENDED_DIMENSIONS = (1200, 627)  # width, height
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB in bytes
    MIN_ASPECT_RATIO = 1.0 / 1.91  # 1:1.91 (portrait)
    MAX_ASPECT_RATIO = 1.91  # 1.91:1 (landscape)
    DEFAULT_QUALITY = 85
    
    @staticmethod
    def validate_image_dimensions(image_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate image dimensions against LinkedIn requirements.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (is_valid, validation_info)
        """
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                aspect_ratio = width / height
                
                validation_info = {
                    'width': width,
                    'height': height,
                    'aspect_ratio': aspect_ratio,
                    'format': img.format,
                    'mode': img.mode,
                    'errors': [],
                    'warnings': []
                }
                
                # Check minimum dimensions
                if width < ImageProcessor.MIN_DIMENSIONS[0] or height < ImageProcessor.MIN_DIMENSIONS[1]:
                    validation_info['errors'].append(
                        f"Image dimensions {width}x{height} are below minimum {ImageProcessor.MIN_DIMENSIONS}"
                    )
                
                # Check maximum dimensions
                if width > ImageProcessor.MAX_DIMENSIONS[0] or height > ImageProcessor.MAX_DIMENSIONS[1]:
                    validation_info['warnings'].append(
                        f"Image dimensions {width}x{height} exceed maximum {ImageProcessor.MAX_DIMENSIONS}"
                    )
                
                # Check aspect ratio
                if aspect_ratio < ImageProcessor.MIN_ASPECT_RATIO or aspect_ratio > ImageProcessor.MAX_ASPECT_RATIO:
                    validation_info['warnings'].append(
                        f"Aspect ratio {aspect_ratio:.2f} is outside recommended range "
                        f"{ImageProcessor.MIN_ASPECT_RATIO:.2f}-{ImageProcessor.MAX_ASPECT_RATIO:.2f}"
                    )
                
                # Check format
                if img.format not in ImageProcessor.SUPPORTED_FORMATS:
                    validation_info['errors'].append(
                        f"Image format {img.format} is not supported. Supported formats: {ImageProcessor.SUPPORTED_FORMATS}"
                    )
                
                is_valid = len(validation_info['errors']) == 0
                return is_valid, validation_info
                
        except Exception as e:
            logger.error(f"Error validating image dimensions for {image_path}: {str(e)}")
            return False, {
                'errors': [f"Failed to validate image: {str(e)}"],
                'warnings': []
            }
    
    @staticmethod
    def validate_image_file_size(image_path: str) -> Tuple[bool, int]:
        """
        Validate image file size against LinkedIn requirements.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (is_valid, file_size_bytes)
        """
        try:
            file_size = os.path.getsize(image_path)
            is_valid = file_size <= ImageProcessor.MAX_FILE_SIZE
            
            if not is_valid:
                logger.warning(
                    f"Image file size {file_size} bytes exceeds maximum {ImageProcessor.MAX_FILE_SIZE} bytes"
                )
            
            return is_valid, file_size
            
        except Exception as e:
            logger.error(f"Error checking file size for {image_path}: {str(e)}")
            return False, 0
    
    @staticmethod
    def resize_image_for_linkedin(image_path: str, output_path: str, 
                                target_dimensions: Optional[Tuple[int, int]] = None) -> str:
        """
        Resize image to meet LinkedIn requirements.
        
        Args:
            image_path: Path to the source image
            output_path: Path where resized image will be saved
            target_dimensions: Optional target dimensions (width, height)
            
        Returns:
            Path to the resized image
        """
        try:
            if target_dimensions is None:
                target_dimensions = ImageProcessor.RECOMMENDED_DIMENSIONS
            
            with Image.open(image_path) as img:
                # Convert to RGB if necessary (for JPEG output)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparent images
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Calculate resize dimensions maintaining aspect ratio
                original_width, original_height = img.size
                target_width, target_height = target_dimensions
                
                # Calculate scaling factor
                width_ratio = target_width / original_width
                height_ratio = target_height / original_height
                scale_factor = min(width_ratio, height_ratio)
                
                # Calculate new dimensions
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                
                # Resize image with high-quality resampling
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Save resized image
                resized_img.save(output_path, 'JPEG', quality=ImageProcessor.DEFAULT_QUALITY, optimize=True)
                
                logger.info(f"Resized image from {original_width}x{original_height} to {new_width}x{new_height}")
                return output_path
                
        except Exception as e:
            logger.error(f"Error resizing image {image_path}: {str(e)}")
            raise ImageProcessingError(f"Failed to resize image: {str(e)}")
    
    @staticmethod
    def convert_image_format(image_path: str, target_format: str, output_path: str) -> str:
        """
        Convert image to specified format.
        
        Args:
            image_path: Path to the source image
            target_format: Target format ('JPEG', 'PNG', 'GIF')
            output_path: Path where converted image will be saved
            
        Returns:
            Path to the converted image
        """
        try:
            if target_format not in ImageProcessor.SUPPORTED_FORMATS:
                raise ImageProcessingError(f"Unsupported target format: {target_format}")
            
            with Image.open(image_path) as img:
                # Handle format-specific conversions
                if target_format == 'JPEG':
                    # Convert to RGB for JPEG (no transparency support)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    img.save(output_path, 'JPEG', quality=ImageProcessor.DEFAULT_QUALITY, optimize=True)
                    
                elif target_format == 'PNG':
                    # Ensure RGBA mode for PNG with transparency support
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    
                    img.save(output_path, 'PNG', optimize=True)
                    
                elif target_format == 'GIF':
                    # Convert to P mode for GIF
                    if img.mode != 'P':
                        img = img.convert('P', palette=Image.ADAPTIVE)
                    
                    img.save(output_path, 'GIF', optimize=True)
                
                logger.info(f"Converted image from {img.format} to {target_format}")
                return output_path
                
        except Exception as e:
            logger.error(f"Error converting image format {image_path}: {str(e)}")
            raise ImageProcessingError(f"Failed to convert image format: {str(e)}")    

    @staticmethod
    def optimize_image_for_web(image_path: str, output_path: str = None, 
                             quality: int = None) -> str:
        """
        Optimize image for web usage while maintaining LinkedIn compatibility.
        
        Args:
            image_path: Path to the source image
            output_path: Optional output path (defaults to overwriting source)
            quality: JPEG quality (1-100, defaults to DEFAULT_QUALITY)
            
        Returns:
            Path to the optimized image
        """
        try:
            if output_path is None:
                output_path = image_path
            
            if quality is None:
                quality = ImageProcessor.DEFAULT_QUALITY
            
            with Image.open(image_path) as img:
                # Apply optimization based on format
                if img.format == 'JPEG' or output_path.lower().endswith('.jpg'):
                    # Optimize JPEG
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Apply progressive JPEG for better loading
                    img.save(output_path, 'JPEG', quality=quality, optimize=True, progressive=True)
                    
                elif img.format == 'PNG' or output_path.lower().endswith('.png'):
                    # Optimize PNG
                    img.save(output_path, 'PNG', optimize=True)
                    
                elif img.format == 'GIF' or output_path.lower().endswith('.gif'):
                    # Optimize GIF
                    img.save(output_path, 'GIF', optimize=True)
                
                else:
                    # Default to JPEG for unknown formats
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    img.save(output_path, 'JPEG', quality=quality, optimize=True, progressive=True)
                
                logger.info(f"Optimized image: {image_path} -> {output_path}")
                return output_path
                
        except Exception as e:
            logger.error(f"Error optimizing image {image_path}: {str(e)}")
            raise ImageProcessingError(f"Failed to optimize image: {str(e)}")
    
    @staticmethod
    def download_and_process_image(image_url: str, output_dir: str = None) -> str:
        """
        Download image from URL and process it for LinkedIn compatibility.
        
        Args:
            image_url: URL of the image to download
            output_dir: Directory to save processed image (defaults to temp)
            
        Returns:
            Path to the processed image file
        """
        try:
            # Parse URL to get filename
            parsed_url = urlparse(image_url)
            filename = os.path.basename(parsed_url.path)
            if not filename or '.' not in filename:
                filename = 'image.jpg'
            
            # Set output directory
            if output_dir is None:
                output_dir = getattr(settings, 'MEDIA_ROOT', '/tmp')
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Download image
            response = requests.get(image_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                raise ImageProcessingError(f"URL does not point to an image: {content_type}")
            
            # Save downloaded image
            temp_path = os.path.join(output_dir, f"temp_{filename}")
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Validate file size
            is_valid_size, file_size = ImageProcessor.validate_image_file_size(temp_path)
            if not is_valid_size:
                # Try to optimize if too large
                optimized_path = os.path.join(output_dir, f"optimized_{filename}")
                ImageProcessor.optimize_image_for_web(temp_path, optimized_path, quality=70)
                
                # Check size again
                is_valid_size, file_size = ImageProcessor.validate_image_file_size(optimized_path)
                if not is_valid_size:
                    os.remove(temp_path)
                    if os.path.exists(optimized_path):
                        os.remove(optimized_path)
                    raise ImageProcessingError(f"Image file size {file_size} bytes exceeds maximum after optimization")
                
                os.remove(temp_path)
                temp_path = optimized_path
            
            # Validate dimensions
            is_valid_dims, validation_info = ImageProcessor.validate_image_dimensions(temp_path)
            
            if not is_valid_dims:
                os.remove(temp_path)
                raise ImageProcessingError(f"Image validation failed: {validation_info['errors']}")
            
            # Resize if dimensions are too large
            if validation_info['width'] > ImageProcessor.MAX_DIMENSIONS[0] or \
               validation_info['height'] > ImageProcessor.MAX_DIMENSIONS[1]:
                
                resized_path = os.path.join(output_dir, f"resized_{filename}")
                ImageProcessor.resize_image_for_linkedin(temp_path, resized_path)
                os.remove(temp_path)
                temp_path = resized_path
            
            # Final optimization
            final_path = os.path.join(output_dir, f"linkedin_{filename}")
            ImageProcessor.optimize_image_for_web(temp_path, final_path)
            
            if temp_path != final_path:
                os.remove(temp_path)
            
            logger.info(f"Successfully processed image from {image_url} -> {final_path}")
            return final_path
            
        except requests.RequestException as e:
            logger.error(f"Error downloading image from {image_url}: {str(e)}")
            raise ImageProcessingError(f"Failed to download image: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing image from {image_url}: {str(e)}")
            raise ImageProcessingError(f"Failed to process image: {str(e)}")
    
    @staticmethod
    def get_image_metadata(image_path: str) -> Dict[str, Any]:
        """
        Extract metadata from image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing image metadata
        """
        try:
            with Image.open(image_path) as img:
                metadata = {
                    'width': img.size[0],
                    'height': img.size[1],
                    'format': img.format,
                    'mode': img.mode,
                    'aspect_ratio': img.size[0] / img.size[1],
                    'file_size': os.path.getsize(image_path),
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info,
                }
                
                # Add EXIF data if available
                if hasattr(img, '_getexif') and img._getexif():
                    metadata['exif'] = dict(img._getexif())
                
                # Add format-specific info
                if img.format == 'JPEG':
                    metadata['progressive'] = 'progressive' in img.info
                elif img.format == 'PNG':
                    metadata['interlace'] = img.info.get('interlace', 0)
                elif img.format == 'GIF':
                    metadata['animated'] = getattr(img, 'is_animated', False)
                    if metadata['animated']:
                        metadata['frames'] = getattr(img, 'n_frames', 1)
                
                return metadata
                
        except Exception as e:
            logger.error(f"Error extracting metadata from {image_path}: {str(e)}")
            return {
                'error': str(e),
                'file_size': os.path.getsize(image_path) if os.path.exists(image_path) else 0
            }
    
    @staticmethod
    def is_linkedin_compatible(image_path: str) -> Tuple[bool, List[str]]:
        """
        Check if image is fully compatible with LinkedIn requirements.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (is_compatible, list_of_issues)
        """
        issues = []
        
        try:
            # Check file size
            is_valid_size, file_size = ImageProcessor.validate_image_file_size(image_path)
            if not is_valid_size:
                issues.append(f"File size {file_size} bytes exceeds maximum {ImageProcessor.MAX_FILE_SIZE} bytes")
            
            # Check dimensions and format
            is_valid_dims, validation_info = ImageProcessor.validate_image_dimensions(image_path)
            issues.extend(validation_info.get('errors', []))
            
            # Only include critical warnings that would prevent LinkedIn posting
            warnings = validation_info.get('warnings', [])
            for warning in warnings:
                if 'exceed maximum' in warning:
                    issues.append(warning)
                # Aspect ratio warnings are not critical for LinkedIn compatibility
                # LinkedIn will accept images with various aspect ratios
            
            is_compatible = len(issues) == 0
            return is_compatible, issues
            
        except Exception as e:
            logger.error(f"Error checking LinkedIn compatibility for {image_path}: {str(e)}")
            return False, [f"Failed to validate image: {str(e)}"]
    
    @staticmethod
    def process_for_linkedin(image_path: str, output_path: str = None) -> str:
        """
        Process image to ensure LinkedIn compatibility.
        
        This is the main method that combines validation, resizing, format conversion,
        and optimization to prepare an image for LinkedIn posting.
        
        Args:
            image_path: Path to the source image
            output_path: Optional output path for processed image
            
        Returns:
            Path to the LinkedIn-compatible processed image
        """
        try:
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_dir = os.path.dirname(image_path)
                output_path = os.path.join(output_dir, f"{base_name}_linkedin.jpg")
            
            # Check if already compatible
            is_compatible, issues = ImageProcessor.is_linkedin_compatible(image_path)
            
            if is_compatible:
                # Just optimize if already compatible
                return ImageProcessor.optimize_image_for_web(image_path, output_path)
            
            logger.info(f"Processing image for LinkedIn compatibility. Issues found: {issues}")
            
            # Start processing pipeline
            current_path = image_path
            temp_files = []
            
            try:
                # Step 1: Convert format if needed
                with Image.open(current_path) as img:
                    if img.format not in ImageProcessor.SUPPORTED_FORMATS:
                        temp_converted = os.path.join(
                            os.path.dirname(output_path), 
                            f"temp_converted_{os.path.basename(output_path)}"
                        )
                        current_path = ImageProcessor.convert_image_format(
                            current_path, 'JPEG', temp_converted
                        )
                        temp_files.append(temp_converted)
                
                # Step 2: Resize if needed
                is_valid_dims, validation_info = ImageProcessor.validate_image_dimensions(current_path)
                if (validation_info['width'] > ImageProcessor.MAX_DIMENSIONS[0] or 
                    validation_info['height'] > ImageProcessor.MAX_DIMENSIONS[1]):
                    
                    temp_resized = os.path.join(
                        os.path.dirname(output_path),
                        f"temp_resized_{os.path.basename(output_path)}"
                    )
                    current_path = ImageProcessor.resize_image_for_linkedin(
                        current_path, temp_resized
                    )
                    temp_files.append(temp_resized)
                
                # Step 3: Final optimization
                final_path = ImageProcessor.optimize_image_for_web(current_path, output_path)
                
                # Cleanup temp files
                for temp_file in temp_files:
                    if os.path.exists(temp_file) and temp_file != final_path:
                        os.remove(temp_file)
                
                # Final validation
                is_final_compatible, final_issues = ImageProcessor.is_linkedin_compatible(final_path)
                if not is_final_compatible:
                    logger.warning(f"Processed image still has issues: {final_issues}")
                
                logger.info(f"Successfully processed image for LinkedIn: {image_path} -> {final_path}")
                return final_path
                
            except Exception as e:
                # Cleanup temp files on error
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                raise e
                
        except Exception as e:
            logger.error(f"Error processing image for LinkedIn {image_path}: {str(e)}")
            raise ImageProcessingError(f"Failed to process image for LinkedIn: {str(e)}")