"""
Validation utilities for roadmap app resume parsing functionality
"""
import io
import logging
from typing import Union, List, Optional
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.conf import settings

from .exceptions import (
    InvalidFileFormatError, 
    FileSizeExceededError, 
    FileValidationError,
    ConfigurationError
)
from .security import SecurityValidator

# Try to import python-magic, but make it optional
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None

logger = logging.getLogger(__name__)


class FileValidator:
    """
    Comprehensive file validation utilities for resume parsing
    """
    
    # Supported file types
    SUPPORTED_MIME_TYPES = [
        'application/pdf',
    ]
    
    SUPPORTED_EXTENSIONS = [
        '.pdf',
    ]
    
    # PDF magic number signatures
    PDF_MAGIC_NUMBERS = [
        b'%PDF-',  # Standard PDF signature
    ]
    
    # Default configuration values
    DEFAULT_MAX_FILE_SIZE_MB = 10
    DEFAULT_MIN_FILE_SIZE_BYTES = 100  # Minimum 100 bytes
    
    def __init__(self):
        """Initialize the file validator"""
        self.logger = logger
    
    def validate_file_type(self, file: Union[UploadedFile, io.BytesIO], 
                          filename: str = None) -> bool:
        """
        Validate file type using multiple methods:
        1. File extension check
        2. MIME type check
        3. Magic number validation
        
        Args:
            file: File to validate
            filename: Optional filename for extension checking
            
        Returns:
            bool: True if valid file type
            
        Raises:
            InvalidFileFormatError: If file type is not supported
        """
        try:
            # Get filename from file object if not provided
            if filename is None and hasattr(file, 'name'):
                filename = file.name
            
            detected_type = None
            
            # 1. File extension validation
            if filename:
                file_ext = self._get_file_extension(filename)
                if file_ext not in self.SUPPORTED_EXTENSIONS:
                    raise InvalidFileFormatError(
                        f"File extension '{file_ext}' is not supported",
                        detected_type=file_ext,
                        supported_types=self.SUPPORTED_EXTENSIONS
                    )
            
            # 2. MIME type validation
            if isinstance(file, UploadedFile) and hasattr(file, 'content_type'):
                if file.content_type not in self.SUPPORTED_MIME_TYPES:
                    detected_type = file.content_type
                    raise InvalidFileFormatError(
                        f"MIME type '{file.content_type}' is not supported",
                        detected_type=detected_type,
                        supported_types=self.SUPPORTED_MIME_TYPES
                    )
            
            # 3. Magic number validation
            if not self._validate_magic_numbers(file):
                # Try to detect actual file type using python-magic
                try:
                    detected_type = self._detect_file_type(file)
                except Exception as e:
                    self.logger.warning(f"Could not detect file type: {str(e)}")
                
                raise InvalidFileFormatError(
                    "File content does not match expected PDF format",
                    detected_type=detected_type,
                    supported_types=['application/pdf']
                )
            
            self.logger.debug("File type validation passed")
            return True
            
        except InvalidFileFormatError:
            raise
        except Exception as e:
            raise FileValidationError(f"Error validating file type: {str(e)}")
    
    def validate_file_size(self, file: Union[UploadedFile, io.BytesIO], 
                          max_size_mb: Optional[int] = None) -> bool:
        """
        Validate file size against configured limits
        
        Args:
            file: File to validate
            max_size_mb: Optional override for max file size
            
        Returns:
            bool: True if file size is valid
            
        Raises:
            FileSizeExceededError: If file size exceeds limits
        """
        try:
            # Get file size
            if isinstance(file, UploadedFile):
                file_size = file.size
            elif isinstance(file, io.BytesIO):
                current_pos = file.tell()
                file.seek(0, 2)  # Seek to end
                file_size = file.tell()
                file.seek(current_pos)  # Restore position
            else:
                raise FileValidationError("Cannot determine file size for this file type")
            
            # Check minimum file size
            if file_size < self.DEFAULT_MIN_FILE_SIZE_BYTES:
                raise FileSizeExceededError(
                    f"File is too small ({file_size} bytes). Minimum size is {self.DEFAULT_MIN_FILE_SIZE_BYTES} bytes",
                    file_size=file_size,
                    max_size=self.DEFAULT_MIN_FILE_SIZE_BYTES
                )
            
            # Get maximum file size
            if max_size_mb is None:
                max_size_mb = self._get_max_file_size_config()
            
            max_size_bytes = max_size_mb * 1024 * 1024
            
            # Check maximum file size
            if file_size > max_size_bytes:
                raise FileSizeExceededError(
                    f"File size ({file_size / (1024 * 1024):.1f}MB) exceeds maximum allowed size ({max_size_mb}MB)",
                    file_size=file_size,
                    max_size=max_size_bytes
                )
            
            self.logger.debug(f"File size validation passed: {file_size / (1024 * 1024):.1f}MB")
            return True
            
        except FileSizeExceededError:
            raise
        except Exception as e:
            raise FileValidationError(f"Error validating file size: {str(e)}")
    
    def validate_file_content(self, file: Union[UploadedFile, io.BytesIO]) -> bool:
        """
        Validate file content for security and integrity
        
        Args:
            file: File to validate
            
        Returns:
            bool: True if file content is valid
            
        Raises:
            FileValidationError: If file content validation fails
        """
        try:
            # Check if file is empty
            if isinstance(file, UploadedFile):
                if file.size == 0:
                    raise FileValidationError("File is empty")
                file.seek(0)
                content = file.read(1024)  # Read first 1KB
                file.seek(0)
            elif isinstance(file, io.BytesIO):
                current_pos = file.tell()
                file.seek(0)
                content = file.read(1024)
                file.seek(current_pos)
            else:
                raise FileValidationError("Unsupported file type for content validation")
            
            # Check for null bytes (potential security issue)
            if b'\x00' in content[:100]:  # Check first 100 bytes
                self.logger.warning("File contains null bytes in header")
            
            # Basic PDF structure validation
            if not content.startswith(b'%PDF-'):
                raise FileValidationError("File does not have valid PDF header")
            
            # Check for PDF version
            try:
                pdf_version_line = content.split(b'\n')[0].decode('ascii', errors='ignore')
                if not pdf_version_line.startswith('%PDF-'):
                    raise FileValidationError("Invalid PDF version header")
                
                version = pdf_version_line[5:8]  # Extract version like "1.4"
                self.logger.debug(f"PDF version detected: {version}")
                
            except Exception as e:
                self.logger.warning(f"Could not parse PDF version: {str(e)}")
            
            self.logger.debug("File content validation passed")
            return True
            
        except FileValidationError:
            raise
        except Exception as e:
            raise FileValidationError(f"Error validating file content: {str(e)}")
    
    def validate_complete(self, file: Union[UploadedFile, io.BytesIO], 
                         filename: str = None, max_size_mb: Optional[int] = None) -> bool:
        """
        Perform complete file validation (type, size, content)
        
        Args:
            file: File to validate
            filename: Optional filename
            max_size_mb: Optional max file size override
            
        Returns:
            bool: True if all validations pass
            
        Raises:
            Various validation exceptions if validation fails
        """
        try:
            # Validate file type
            self.validate_file_type(file, filename)
            
            # Validate file size
            self.validate_file_size(file, max_size_mb)
            
            # Validate file content
            self.validate_file_content(file)
            
            self.logger.info("Complete file validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"File validation failed: {str(e)}")
            raise
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename"""
        if not filename:
            return ""
        return '.' + filename.lower().split('.')[-1] if '.' in filename else ""
    
    def _validate_magic_numbers(self, file: Union[UploadedFile, io.BytesIO]) -> bool:
        """Validate file using magic numbers"""
        try:
            # Read file header
            if isinstance(file, UploadedFile):
                file.seek(0)
                header = file.read(10)
                file.seek(0)
            elif isinstance(file, io.BytesIO):
                current_pos = file.tell()
                file.seek(0)
                header = file.read(10)
                file.seek(current_pos)
            else:
                return False
            
            # Check PDF magic numbers
            for magic_number in self.PDF_MAGIC_NUMBERS:
                if header.startswith(magic_number):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Magic number validation failed: {str(e)}")
            return False
    
    def _detect_file_type(self, file: Union[UploadedFile, io.BytesIO]) -> str:
        """Detect file type using python-magic"""
        if not MAGIC_AVAILABLE:
            self.logger.warning("python-magic not available for file type detection")
            return "unknown"
            
        try:
            if isinstance(file, UploadedFile):
                file.seek(0)
                content = file.read()
                file.seek(0)
            elif isinstance(file, io.BytesIO):
                current_pos = file.tell()
                file.seek(0)
                content = file.read()
                file.seek(current_pos)
            else:
                return "unknown"
            
            return magic.from_buffer(content, mime=True)
            
        except Exception as e:
            self.logger.warning(f"File type detection failed: {str(e)}")
            return "unknown"
    
    def _get_max_file_size_config(self) -> int:
        """Get maximum file size from configuration"""
        try:
            # Try to get from Django settings first
            if hasattr(settings, 'RESUME_PARSER_SETTINGS'):
                return settings.RESUME_PARSER_SETTINGS.get('MAX_FILE_SIZE_MB', self.DEFAULT_MAX_FILE_SIZE_MB)
            
            # Try to get from ResumeParserConfig model
            try:
                from ..models import ResumeParserConfig
                config = ResumeParserConfig.get_config()
                return config.max_file_size_mb
            except Exception:
                pass
            
            # Fallback to default
            return self.DEFAULT_MAX_FILE_SIZE_MB
            
        except Exception as e:
            self.logger.warning(f"Could not get max file size config: {str(e)}")
            return self.DEFAULT_MAX_FILE_SIZE_MB


# Convenience functions for Django form/serializer validation
def validate_pdf_file(file):
    """
    Django validator function for PDF file validation with security checks
    
    Args:
        file: Uploaded file to validate
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        # Use security validator for comprehensive validation
        security_validator = SecurityValidator()
        validation_result = security_validator.validate_file_upload(file)
        
        if not validation_result['is_valid']:
            error_messages = validation_result['errors']
            raise ValidationError('; '.join(error_messages))
        
        # Also run original file type validation
        validator = FileValidator()
        validator.validate_file_type(file)
        return file
    except ValidationError:
        raise
    except (InvalidFileFormatError, FileValidationError) as e:
        raise ValidationError(e.message)


def validate_file_size(file):
    """
    Django validator function for file size validation
    
    Args:
        file: Uploaded file to validate
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        validator = FileValidator()
        validator.validate_file_size(file)
        return file
    except (FileSizeExceededError, FileValidationError) as e:
        raise ValidationError(e.message)


def validate_complete_file(file):
    """
    Django validator function for complete file validation with security checks
    
    Args:
        file: Uploaded file to validate
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        # Use security validator for comprehensive validation
        security_validator = SecurityValidator()
        validation_result = security_validator.validate_file_upload(file)
        
        if not validation_result['is_valid']:
            error_messages = validation_result['errors']
            raise ValidationError('; '.join(error_messages))
        
        # Also run original complete validation
        validator = FileValidator()
        validator.validate_complete(file)
        return file
    except ValidationError:
        raise
    except Exception as e:
        if hasattr(e, 'message'):
            raise ValidationError(e.message)
        else:
            raise ValidationError(str(e))