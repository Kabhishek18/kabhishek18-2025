"""
Custom exceptions for roadmap app resume parsing functionality
"""


class ResumeParsingError(Exception):
    """
    Base exception for resume parsing errors
    
    Attributes:
        message: Error message
        error_code: Optional error code for API responses
        details: Optional additional error details
    """
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses"""
        return {
            'error': {
                'code': self.error_code,
                'message': self.message,
                'details': self.details
            }
        }


class InvalidFileFormatError(ResumeParsingError):
    """
    Exception for invalid file format errors
    
    Raised when uploaded file is not a supported format (e.g., not PDF)
    """
    
    def __init__(self, message: str = "Invalid file format", 
                 detected_type: str = None, supported_types: list = None):
        details = {}
        if detected_type:
            details['detected_type'] = detected_type
        if supported_types:
            details['supported_types'] = supported_types
        
        super().__init__(
            message=message,
            error_code='INVALID_FILE_FORMAT',
            details=details
        )


class FileSizeExceededError(ResumeParsingError):
    """
    Exception for file size limit exceeded
    
    Raised when uploaded file exceeds configured size limits
    """
    
    def __init__(self, message: str = "File size exceeds limit", 
                 file_size: int = None, max_size: int = None):
        details = {}
        if file_size is not None:
            details['file_size_bytes'] = file_size
            details['file_size_mb'] = round(file_size / (1024 * 1024), 2)
        if max_size is not None:
            details['max_size_bytes'] = max_size
            details['max_size_mb'] = round(max_size / (1024 * 1024), 2)
        
        super().__init__(
            message=message,
            error_code='FILE_SIZE_EXCEEDED',
            details=details
        )


class PDFExtractionError(ResumeParsingError):
    """
    Exception for PDF text extraction failures
    
    Raised when PDF processing or text extraction fails
    """
    
    def __init__(self, message: str = "PDF text extraction failed", 
                 pdf_info: dict = None):
        details = {}
        if pdf_info:
            details['pdf_info'] = pdf_info
        
        super().__init__(
            message=message,
            error_code='PDF_EXTRACTION_ERROR',
            details=details
        )


class AIProcessingError(ResumeParsingError):
    """
    Exception for AI processing failures
    
    Raised when AI/NLP processing of resume text fails
    """
    
    def __init__(self, message: str = "AI processing failed", 
                 backend: str = None, retry_available: bool = False):
        details = {}
        if backend:
            details['backend'] = backend
        if retry_available:
            details['retry_available'] = retry_available
        
        super().__init__(
            message=message,
            error_code='AI_PROCESSING_ERROR',
            details=details
        )


class FileValidationError(ResumeParsingError):
    """
    Exception for general file validation errors
    
    Raised when file validation fails for reasons other than format or size
    """
    
    def __init__(self, message: str = "File validation failed", 
                 validation_type: str = None):
        details = {}
        if validation_type:
            details['validation_type'] = validation_type
        
        super().__init__(
            message=message,
            error_code='FILE_VALIDATION_ERROR',
            details=details
        )


class ConfigurationError(ResumeParsingError):
    """
    Exception for configuration-related errors
    
    Raised when system configuration is invalid or missing
    """
    
    def __init__(self, message: str = "Configuration error", 
                 config_key: str = None):
        details = {}
        if config_key:
            details['config_key'] = config_key
        
        super().__init__(
            message=message,
            error_code='CONFIGURATION_ERROR',
            details=details
        )