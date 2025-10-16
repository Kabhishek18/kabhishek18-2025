"""
Tests for roadmap app utilities
"""
import io
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from ..utils.validators import FileValidator, validate_pdf_file, validate_file_size, validate_complete_file
from ..utils.exceptions import (
    ResumeParsingError, InvalidFileFormatError, FileSizeExceededError,
    PDFExtractionError, AIProcessingError, FileValidationError, ConfigurationError
)


class FileValidatorTests(TestCase):
    """
    Tests for FileValidator utility class
    """
    
    def setUp(self):
        self.validator = FileValidator()
        
        # Create test file contents (make sure it's large enough)
        self.valid_pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n' + b'A' * 100
        self.invalid_content = b'This is not a PDF file'
        self.empty_content = b''
    
    def test_validate_file_type_valid_pdf(self):
        """Test file type validation with valid PDF"""
        pdf_file = SimpleUploadedFile(
            "test.pdf", 
            self.valid_pdf_content, 
            content_type="application/pdf"
        )
        
        result = self.validator.validate_file_type(pdf_file)
        self.assertTrue(result)
    
    def test_validate_file_type_invalid_extension(self):
        """Test file type validation with invalid extension"""
        doc_file = SimpleUploadedFile(
            "test.doc", 
            self.invalid_content, 
            content_type="application/msword"
        )
        
        with self.assertRaises(InvalidFileFormatError) as context:
            self.validator.validate_file_type(doc_file)
        
        self.assertIn("extension", str(context.exception))
        self.assertIn(".doc", str(context.exception))
    
    def test_validate_file_type_invalid_mime_type(self):
        """Test file type validation with invalid MIME type"""
        pdf_file = SimpleUploadedFile(
            "test.pdf", 
            self.valid_pdf_content, 
            content_type="application/msword"  # Wrong MIME type
        )
        
        with self.assertRaises(InvalidFileFormatError) as context:
            self.validator.validate_file_type(pdf_file)
        
        self.assertIn("MIME type", str(context.exception))
    
    def test_validate_file_type_invalid_magic_numbers(self):
        """Test file type validation with invalid magic numbers"""
        pdf_file = SimpleUploadedFile(
            "test.pdf", 
            self.invalid_content,  # Wrong content
            content_type="application/pdf"
        )
        
        with self.assertRaises(InvalidFileFormatError) as context:
            self.validator.validate_file_type(pdf_file)
        
        self.assertIn("content does not match", str(context.exception))
    
    def test_validate_file_size_valid(self):
        """Test file size validation with valid size"""
        content = b'A' * 1000  # 1KB file
        pdf_file = SimpleUploadedFile("test.pdf", content)
        
        result = self.validator.validate_file_size(pdf_file, max_size_mb=1)
        self.assertTrue(result)
    
    def test_validate_file_size_too_large(self):
        """Test file size validation with file too large"""
        content = b'A' * (2 * 1024 * 1024)  # 2MB file
        pdf_file = SimpleUploadedFile("test.pdf", content)
        
        with self.assertRaises(FileSizeExceededError) as context:
            self.validator.validate_file_size(pdf_file, max_size_mb=1)
        
        self.assertIn("exceeds maximum", str(context.exception))
        self.assertIn("2.0MB", str(context.exception))
    
    def test_validate_file_size_too_small(self):
        """Test file size validation with file too small"""
        content = b'A' * 50  # 50 bytes (below minimum)
        pdf_file = SimpleUploadedFile("test.pdf", content)
        
        with self.assertRaises(FileSizeExceededError) as context:
            self.validator.validate_file_size(pdf_file)
        
        self.assertIn("too small", str(context.exception))
    
    def test_validate_file_size_with_bytesio(self):
        """Test file size validation with BytesIO object"""
        content = b'A' * 1000
        file_obj = io.BytesIO(content)
        
        result = self.validator.validate_file_size(file_obj, max_size_mb=1)
        self.assertTrue(result)
    
    def test_validate_file_content_valid_pdf(self):
        """Test file content validation with valid PDF"""
        pdf_file = SimpleUploadedFile("test.pdf", self.valid_pdf_content)
        
        result = self.validator.validate_file_content(pdf_file)
        self.assertTrue(result)
    
    def test_validate_file_content_empty_file(self):
        """Test file content validation with empty file"""
        pdf_file = SimpleUploadedFile("test.pdf", self.empty_content)
        
        with self.assertRaises(FileValidationError) as context:
            self.validator.validate_file_content(pdf_file)
        
        self.assertIn("empty", str(context.exception))
    
    def test_validate_file_content_invalid_header(self):
        """Test file content validation with invalid PDF header"""
        pdf_file = SimpleUploadedFile("test.pdf", self.invalid_content)
        
        with self.assertRaises(FileValidationError) as context:
            self.validator.validate_file_content(pdf_file)
        
        self.assertIn("valid PDF header", str(context.exception))
    
    def test_validate_complete_success(self):
        """Test complete file validation success"""
        pdf_file = SimpleUploadedFile(
            "test.pdf", 
            self.valid_pdf_content, 
            content_type="application/pdf"
        )
        
        result = self.validator.validate_complete(pdf_file)
        self.assertTrue(result)
    
    def test_get_file_extension(self):
        """Test file extension extraction"""
        self.assertEqual(self.validator._get_file_extension("test.pdf"), ".pdf")
        self.assertEqual(self.validator._get_file_extension("test.PDF"), ".pdf")
        self.assertEqual(self.validator._get_file_extension("test"), "")
        self.assertEqual(self.validator._get_file_extension(""), "")
    
    def test_validate_magic_numbers(self):
        """Test magic number validation"""
        pdf_file = io.BytesIO(self.valid_pdf_content)
        result = self.validator._validate_magic_numbers(pdf_file)
        self.assertTrue(result)
        
        invalid_file = io.BytesIO(self.invalid_content)
        result = self.validator._validate_magic_numbers(invalid_file)
        self.assertFalse(result)
    
    @patch('roadmap.utils.validators.MAGIC_AVAILABLE', True)
    @patch('roadmap.utils.validators.magic')
    def test_detect_file_type_with_magic(self, mock_magic):
        """Test file type detection with python-magic"""
        mock_magic.from_buffer.return_value = "application/pdf"
        
        pdf_file = io.BytesIO(self.valid_pdf_content)
        result = self.validator._detect_file_type(pdf_file)
        
        self.assertEqual(result, "application/pdf")
        mock_magic.from_buffer.assert_called_once()
    
    @patch('roadmap.utils.validators.MAGIC_AVAILABLE', False)
    def test_detect_file_type_without_magic(self):
        """Test file type detection without python-magic"""
        pdf_file = io.BytesIO(self.valid_pdf_content)
        result = self.validator._detect_file_type(pdf_file)
        
        self.assertEqual(result, "unknown")
    
    def test_get_max_file_size_config_default(self):
        """Test getting max file size configuration with default"""
        result = self.validator._get_max_file_size_config()
        self.assertEqual(result, self.validator.DEFAULT_MAX_FILE_SIZE_MB)


class ValidatorFunctionTests(TestCase):
    """
    Tests for validator functions used in Django forms/serializers
    """
    
    def setUp(self):
        self.valid_pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n' + b'A' * 100
        self.invalid_content = b'This is not a PDF file'
    
    @patch('roadmap.utils.validators.SecurityValidator')
    def test_validate_pdf_file_success(self, mock_security_validator):
        """Test PDF file validation function success"""
        # Mock security validator to return valid
        mock_validator_instance = MagicMock()
        mock_validator_instance.validate_file_upload.return_value = {
            'is_valid': True,
            'errors': []
        }
        mock_security_validator.return_value = mock_validator_instance
        
        pdf_file = SimpleUploadedFile(
            "test.pdf", 
            self.valid_pdf_content, 
            content_type="application/pdf"
        )
        
        # Also mock the FileValidator to avoid magic import issues
        with patch('roadmap.utils.validators.FileValidator') as mock_file_validator:
            mock_file_validator_instance = MagicMock()
            mock_file_validator_instance.validate_file_type.return_value = True
            mock_file_validator.return_value = mock_file_validator_instance
            
            result = validate_pdf_file(pdf_file)
            self.assertEqual(result, pdf_file)
    
    @patch('roadmap.utils.validators.SecurityValidator')
    def test_validate_pdf_file_security_failure(self, mock_security_validator):
        """Test PDF file validation function with security failure"""
        # Mock security validator to return invalid
        mock_validator_instance = MagicMock()
        mock_validator_instance.validate_file_upload.return_value = {
            'is_valid': False,
            'errors': ['File contains malicious content']
        }
        mock_security_validator.return_value = mock_validator_instance
        
        pdf_file = SimpleUploadedFile("test.pdf", self.invalid_content)
        
        with self.assertRaises(ValidationError) as context:
            validate_pdf_file(pdf_file)
        
        self.assertIn("malicious content", str(context.exception))
    
    def test_validate_file_size_success(self):
        """Test file size validation function success"""
        content = b'A' * 1000  # 1KB file
        pdf_file = SimpleUploadedFile("test.pdf", content)
        
        result = validate_file_size(pdf_file)
        self.assertEqual(result, pdf_file)
    
    def test_validate_file_size_failure(self):
        """Test file size validation function failure"""
        content = b'A' * (20 * 1024 * 1024)  # 20MB file (exceeds default limit)
        pdf_file = SimpleUploadedFile("test.pdf", content)
        
        with self.assertRaises(ValidationError):
            validate_file_size(pdf_file)
    
    @patch('roadmap.utils.validators.SecurityValidator')
    def test_validate_complete_file_success(self, mock_security_validator):
        """Test complete file validation function success"""
        # Mock security validator to return valid
        mock_validator_instance = MagicMock()
        mock_validator_instance.validate_file_upload.return_value = {
            'is_valid': True,
            'errors': []
        }
        mock_security_validator.return_value = mock_validator_instance
        
        pdf_file = SimpleUploadedFile(
            "test.pdf", 
            self.valid_pdf_content, 
            content_type="application/pdf"
        )
        
        # Also mock the FileValidator to avoid magic import issues
        with patch('roadmap.utils.validators.FileValidator') as mock_file_validator:
            mock_file_validator_instance = MagicMock()
            mock_file_validator_instance.validate_complete.return_value = True
            mock_file_validator.return_value = mock_file_validator_instance
            
            result = validate_complete_file(pdf_file)
            self.assertEqual(result, pdf_file)


class ExceptionTests(TestCase):
    """
    Tests for custom exception classes
    """
    
    def test_resume_parsing_error_basic(self):
        """Test basic ResumeParsingError functionality"""
        error = ResumeParsingError("Test error message")
        
        self.assertEqual(str(error), "Test error message")
        self.assertEqual(error.message, "Test error message")
        self.assertEqual(error.error_code, "RESUMEPARSINGERROR")
        self.assertEqual(error.details, {})
    
    def test_resume_parsing_error_with_details(self):
        """Test ResumeParsingError with custom details"""
        details = {"file_name": "test.pdf", "line_number": 42}
        error = ResumeParsingError(
            "Test error", 
            error_code="CUSTOM_ERROR", 
            details=details
        )
        
        self.assertEqual(error.error_code, "CUSTOM_ERROR")
        self.assertEqual(error.details, details)
    
    def test_resume_parsing_error_to_dict(self):
        """Test ResumeParsingError to_dict method"""
        error = ResumeParsingError(
            "Test error", 
            error_code="TEST_ERROR", 
            details={"key": "value"}
        )
        
        expected = {
            'error': {
                'code': 'TEST_ERROR',
                'message': 'Test error',
                'details': {'key': 'value'}
            }
        }
        
        self.assertEqual(error.to_dict(), expected)
    
    def test_invalid_file_format_error(self):
        """Test InvalidFileFormatError specific functionality"""
        error = InvalidFileFormatError(
            "Invalid format", 
            detected_type="application/msword",
            supported_types=["application/pdf"]
        )
        
        self.assertEqual(error.error_code, "INVALID_FILE_FORMAT")
        self.assertEqual(error.details['detected_type'], "application/msword")
        self.assertEqual(error.details['supported_types'], ["application/pdf"])
    
    def test_file_size_exceeded_error(self):
        """Test FileSizeExceededError specific functionality"""
        error = FileSizeExceededError(
            "File too large",
            file_size=2048000,  # 2MB in bytes
            max_size=1048576    # 1MB in bytes
        )
        
        self.assertEqual(error.error_code, "FILE_SIZE_EXCEEDED")
        self.assertEqual(error.details['file_size_bytes'], 2048000)
        self.assertEqual(error.details['file_size_mb'], 1.95)  # Rounded
        self.assertEqual(error.details['max_size_bytes'], 1048576)
        self.assertEqual(error.details['max_size_mb'], 1.0)
    
    def test_pdf_extraction_error(self):
        """Test PDFExtractionError specific functionality"""
        pdf_info = {"pages": 0, "corrupted": True}
        error = PDFExtractionError(
            "Cannot extract text",
            pdf_info=pdf_info
        )
        
        self.assertEqual(error.error_code, "PDF_EXTRACTION_ERROR")
        self.assertEqual(error.details['pdf_info'], pdf_info)
    
    def test_ai_processing_error(self):
        """Test AIProcessingError specific functionality"""
        error = AIProcessingError(
            "AI processing failed",
            backend="gemini",
            retry_available=True
        )
        
        self.assertEqual(error.error_code, "AI_PROCESSING_ERROR")
        self.assertEqual(error.details['backend'], "gemini")
        self.assertTrue(error.details['retry_available'])
    
    def test_file_validation_error(self):
        """Test FileValidationError specific functionality"""
        error = FileValidationError(
            "Validation failed",
            validation_type="content_check"
        )
        
        self.assertEqual(error.error_code, "FILE_VALIDATION_ERROR")
        self.assertEqual(error.details['validation_type'], "content_check")
    
    def test_configuration_error(self):
        """Test ConfigurationError specific functionality"""
        error = ConfigurationError(
            "Missing configuration",
            config_key="GEMINI_API_KEY"
        )
        
        self.assertEqual(error.error_code, "CONFIGURATION_ERROR")
        self.assertEqual(error.details['config_key'], "GEMINI_API_KEY")
    
    def test_exception_inheritance(self):
        """Test that custom exceptions inherit properly"""
        error = InvalidFileFormatError("Test")
        
        # Should be instance of both custom and base exception classes
        self.assertIsInstance(error, InvalidFileFormatError)
        self.assertIsInstance(error, ResumeParsingError)
        self.assertIsInstance(error, Exception)
    
    def test_exception_default_messages(self):
        """Test exception default messages"""
        self.assertEqual(
            InvalidFileFormatError().message, 
            "Invalid file format"
        )
        self.assertEqual(
            FileSizeExceededError().message, 
            "File size exceeds limit"
        )
        self.assertEqual(
            PDFExtractionError().message, 
            "PDF text extraction failed"
        )
        self.assertEqual(
            AIProcessingError().message, 
            "AI processing failed"
        )
        self.assertEqual(
            FileValidationError().message, 
            "File validation failed"
        )
        self.assertEqual(
            ConfigurationError().message, 
            "Configuration error"
        )