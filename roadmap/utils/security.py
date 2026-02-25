"""
Security utilities for the resume parser.
Provides file upload security checks, input sanitization, and audit logging.
"""

import os
import re
import hashlib
import logging
from typing import Optional, Dict, Any, List
from django.core.files.uploadedfile import UploadedFile
from django.conf import settings
from django.utils.html import strip_tags
from django.utils.text import slugify

# Try to import python-magic, but make it optional
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None

logger = logging.getLogger(__name__)


class SecurityValidator:
    """
    Security validation service for file uploads and data sanitization.
    """
    
    # Allowed MIME types for PDF files
    ALLOWED_PDF_MIME_TYPES = [
        'application/pdf',
        'application/x-pdf',
    ]
    
    # PDF magic number signatures
    PDF_MAGIC_SIGNATURES = [
        b'%PDF-',  # Standard PDF signature
    ]
    
    # Maximum file size (configurable via settings)
    MAX_FILE_SIZE = getattr(settings, 'RESUME_PARSER_MAX_FILE_SIZE_MB', 10) * 1024 * 1024
    
    # Dangerous file extensions to block
    BLOCKED_EXTENSIONS = [
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
        '.jar', '.app', '.deb', '.pkg', '.dmg', '.iso', '.zip', '.rar'
    ]
    
    def __init__(self):
        self.audit_logger = logging.getLogger('resume_parser.audit')
    
    def validate_file_upload(self, uploaded_file: UploadedFile) -> Dict[str, Any]:
        """
        Comprehensive security validation for uploaded files.
        
        Args:
            uploaded_file: Django UploadedFile instance
            
        Returns:
            dict: Validation result with success status and details
        """
        validation_result = {
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'file_info': {}
        }
        
        try:
            # Basic file information
            file_info = {
                'name': uploaded_file.name,
                'size': uploaded_file.size,
                'content_type': uploaded_file.content_type,
            }
            validation_result['file_info'] = file_info
            
            # 1. File size validation
            if not self._validate_file_size(uploaded_file.size):
                validation_result['errors'].append(
                    f"File size ({uploaded_file.size} bytes) exceeds maximum allowed size ({self.MAX_FILE_SIZE} bytes)"
                )
            
            # 2. File extension validation
            if not self._validate_file_extension(uploaded_file.name):
                validation_result['errors'].append(
                    f"File extension not allowed. Only PDF files are permitted."
                )
            
            # 3. MIME type validation
            if not self._validate_mime_type(uploaded_file.content_type):
                validation_result['errors'].append(
                    f"Invalid MIME type: {uploaded_file.content_type}. Only PDF files are allowed."
                )
            
            # 4. Magic number validation (file signature)
            magic_validation = self._validate_file_signature(uploaded_file)
            if not magic_validation['is_valid']:
                validation_result['errors'].append(magic_validation['error'])
            
            # 5. File name security validation
            name_validation = self._validate_filename_security(uploaded_file.name)
            if not name_validation['is_valid']:
                validation_result['errors'].append(name_validation['error'])
            elif name_validation.get('warnings'):
                validation_result['warnings'].extend(name_validation['warnings'])
            
            # Set overall validation status
            validation_result['is_valid'] = len(validation_result['errors']) == 0
            
            # Audit log the validation attempt
            self._audit_log_file_validation(uploaded_file, validation_result)
            
        except Exception as e:
            logger.error(f"SecurityValidator: Unexpected error during file validation: {e}")
            validation_result['errors'].append("Internal validation error occurred")
        
        return validation_result
    
    def _validate_file_size(self, file_size: int) -> bool:
        """Validate file size against maximum allowed size."""
        return file_size <= self.MAX_FILE_SIZE
    
    def _validate_file_extension(self, filename: str) -> bool:
        """Validate file extension is PDF and not in blocked list."""
        if not filename:
            return False
            
        filename_lower = filename.lower()
        
        # Check for blocked extensions
        for blocked_ext in self.BLOCKED_EXTENSIONS:
            if filename_lower.endswith(blocked_ext):
                return False
        
        # Must be PDF extension
        return filename_lower.endswith('.pdf')
    
    def _validate_mime_type(self, content_type: str) -> bool:
        """Validate MIME type is an allowed PDF type."""
        return content_type in self.ALLOWED_PDF_MIME_TYPES
    
    def _validate_file_signature(self, uploaded_file: UploadedFile) -> Dict[str, Any]:
        """Validate file signature using magic numbers."""
        try:
            # Read first few bytes to check magic number
            uploaded_file.seek(0)
            file_header = uploaded_file.read(1024)
            uploaded_file.seek(0)  # Reset file pointer
            
            # Check PDF magic signatures
            for signature in self.PDF_MAGIC_SIGNATURES:
                if file_header.startswith(signature):
                    return {'is_valid': True}
            
            # Try using python-magic if available
            if MAGIC_AVAILABLE:
                try:
                    file_type = magic.from_buffer(file_header, mime=True)
                    if file_type in self.ALLOWED_PDF_MIME_TYPES:
                        return {'is_valid': True}
                except Exception as e:
                    logger.warning(f"SecurityValidator: Magic library check failed: {e}")
            else:
                logger.debug("SecurityValidator: python-magic not available, skipping MIME type detection")
            
            return {
                'is_valid': False,
                'error': "File signature does not match PDF format"
            }
            
        except Exception as e:
            logger.error(f"SecurityValidator: Error validating file signature: {e}")
            return {
                'is_valid': False,
                'error': "Unable to validate file signature"
            }
    
    def _validate_filename_security(self, filename: str) -> Dict[str, Any]:
        """Validate filename for security issues."""
        result = {'is_valid': True, 'warnings': []}
        
        if not filename:
            return {'is_valid': False, 'error': "Filename is empty"}
        
        # Check for path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            return {'is_valid': False, 'error': "Filename contains path traversal characters"}
        
        # Check for null bytes
        if '\x00' in filename:
            return {'is_valid': False, 'error': "Filename contains null bytes"}
        
        # Check for excessively long filename
        if len(filename) > 255:
            return {'is_valid': False, 'error': "Filename is too long (max 255 characters)"}
        
        # Check for suspicious characters
        suspicious_chars = ['<', '>', ':', '"', '|', '?', '*']
        if any(char in filename for char in suspicious_chars):
            result['warnings'].append("Filename contains potentially problematic characters")
        
        return result
    
    def sanitize_extracted_text(self, text: str) -> str:
        """
        Sanitize extracted text data to remove potentially harmful content.
        
        Args:
            text: Raw extracted text from resume
            
        Returns:
            str: Sanitized text safe for processing and storage
        """
        if not text:
            return ""
        
        try:
            # Remove HTML tags if any
            sanitized = strip_tags(text)
            
            # Remove null bytes and control characters
            sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
            
            # Normalize whitespace
            sanitized = re.sub(r'\s+', ' ', sanitized).strip()
            
            # Limit length to prevent memory issues
            max_length = getattr(settings, 'RESUME_PARSER_MAX_TEXT_LENGTH', 50000)
            if len(sanitized) > max_length:
                sanitized = sanitized[:max_length]
                logger.warning(f"SecurityValidator: Text truncated to {max_length} characters")
            
            return sanitized
            
        except Exception as e:
            logger.error(f"SecurityValidator: Error sanitizing text: {e}")
            return ""
    
    def sanitize_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize extracted resume data structure.
        
        Args:
            data: Dictionary containing extracted resume data
            
        Returns:
            dict: Sanitized data structure
        """
        if not isinstance(data, dict):
            return {}
        
        sanitized_data = {}
        
        try:
            # Sanitize string fields
            string_fields = ['name', 'email', 'phone']
            for field in string_fields:
                if field in data and isinstance(data[field], str):
                    sanitized_data[field] = self._sanitize_string_field(data[field])
                else:
                    sanitized_data[field] = None
            
            # Sanitize list fields
            list_fields = ['skills', 'experience', 'education']
            for field in list_fields:
                if field in data and isinstance(data[field], list):
                    sanitized_data[field] = self._sanitize_list_field(data[field])
                else:
                    sanitized_data[field] = []
            
            # Preserve safe metadata
            if 'processing_backend_used' in data:
                sanitized_data['processing_backend_used'] = str(data['processing_backend_used'])
            
            if 'confidence_score' in data and isinstance(data['confidence_score'], (int, float)):
                sanitized_data['confidence_score'] = max(0.0, min(1.0, float(data['confidence_score'])))
            
        except Exception as e:
            logger.error(f"SecurityValidator: Error sanitizing extracted data: {e}")
            return {}
        
        return sanitized_data
    
    def _sanitize_string_field(self, value: str) -> Optional[str]:
        """Sanitize individual string field."""
        if not value or not isinstance(value, str):
            return None
        
        # Remove HTML tags
        sanitized = strip_tags(value)
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Limit length
        if len(sanitized) > 500:
            sanitized = sanitized[:500]
        
        return sanitized if sanitized else None
    
    def _sanitize_list_field(self, value: List[Any]) -> List[str]:
        """Sanitize list field containing strings."""
        if not isinstance(value, list):
            return []
        
        sanitized_list = []
        for item in value[:50]:  # Limit list size
            if isinstance(item, str):
                sanitized_item = self._sanitize_string_field(item)
                if sanitized_item:
                    sanitized_list.append(sanitized_item)
            elif isinstance(item, dict):
                # Handle nested dictionaries (e.g., experience, education)
                sanitized_dict = {}
                for key, val in item.items():
                    if isinstance(val, str):
                        sanitized_dict[str(key)] = self._sanitize_string_field(val)
                if sanitized_dict:
                    sanitized_list.append(sanitized_dict)
        
        return sanitized_list
    
    def _audit_log_file_validation(self, uploaded_file: UploadedFile, validation_result: Dict[str, Any]) -> None:
        """
        Create audit log entry for file validation without exposing sensitive data.
        
        Args:
            uploaded_file: The uploaded file
            validation_result: Result of validation
        """
        try:
            # Create file hash for tracking without storing content
            uploaded_file.seek(0)
            file_hash = hashlib.sha256(uploaded_file.read(1024)).hexdigest()[:16]
            uploaded_file.seek(0)
            
            audit_data = {
                'event': 'file_validation',
                'file_hash': file_hash,
                'file_size': uploaded_file.size,
                'content_type': uploaded_file.content_type,
                'validation_success': validation_result['is_valid'],
                'error_count': len(validation_result['errors']),
                'warning_count': len(validation_result['warnings'])
            }
            
            # Log without sensitive filename or content
            self.audit_logger.info(f"File validation: {audit_data}")
            
        except Exception as e:
            logger.error(f"SecurityValidator: Error creating audit log: {e}")
    
    def generate_secure_filename(self, original_filename: str) -> str:
        """
        Generate a secure filename for temporary storage.
        
        Args:
            original_filename: Original uploaded filename
            
        Returns:
            str: Secure filename for temporary use
        """
        try:
            # Extract extension
            name, ext = os.path.splitext(original_filename)
            
            # Create secure base name
            secure_name = slugify(name)[:50]  # Limit length
            
            # Add timestamp and random component
            import time
            import random
            timestamp = int(time.time())
            random_suffix = random.randint(1000, 9999)
            
            return f"resume_{secure_name}_{timestamp}_{random_suffix}{ext}"
            
        except Exception as e:
            logger.error(f"SecurityValidator: Error generating secure filename: {e}")
            # Fallback to timestamp-based name
            import time
            return f"resume_{int(time.time())}.pdf"