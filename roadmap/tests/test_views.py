"""
Integration tests for roadmap app API endpoints
Tests complete upload and processing workflow, error handling, and security measures
"""
import os
import json
import tempfile
from io import BytesIO
from unittest.mock import patch, MagicMock, mock_open
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status

from roadmap.models import ResumeParserConfig
from roadmap.services.ai_processor import AIProcessingError
from roadmap.services.cleanup_service import CleanupService
from roadmap.utils.exceptions import (
    PDFExtractionError, 
    InvalidFileFormatError,
    FileSizeExceededError
)


class ResumeParseViewIntegrationTests(APITestCase):
    """
    Integration tests for ResumeParseView API endpoint
    Tests complete upload and processing workflow
    """
    
    def setUp(self):
        """Set up test data and configuration"""
        self.url = reverse('roadmap:v1:parse-resume')
        
        # Create test configuration
        self.config = ResumeParserConfig.objects.create(
            max_file_size_mb=10,
            default_backend='auto',
            gemini_api_key='test-key',
            processing_timeout_seconds=300
        )
        
        # Create test PDF content
        self.valid_pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF'
        
        # Sample extracted text for mocking
        self.sample_extracted_text = """
        John Doe
        Software Engineer
        john.doe@email.com
        (555) 123-4567
        
        EXPERIENCE
        Senior Software Engineer at Tech Corp (2020-2023)
        - Developed web applications using Python and Django
        - Led team of 5 developers
        
        Software Engineer at StartupCo (2018-2020)
        - Built REST APIs and microservices
        - Worked with React and Node.js
        
        EDUCATION
        Bachelor of Science in Computer Science
        University of Technology (2014-2018)
        
        SKILLS
        Python, Django, JavaScript, React, Node.js, PostgreSQL, Docker
        """
        
        # Sample processed data for mocking
        self.sample_processed_data = {
            'name': 'John Doe',
            'email': 'john.doe@email.com',
            'phone': '(555) 123-4567',
            'skills': ['Python', 'Django', 'JavaScript', 'React', 'Node.js', 'PostgreSQL', 'Docker'],
            'experience': [
                {
                    'job_title': 'Senior Software Engineer',
                    'company': 'Tech Corp',
                    'start_date': '2020',
                    'end_date': '2023',
                    'description': 'Developed web applications using Python and Django'
                },
                {
                    'job_title': 'Software Engineer',
                    'company': 'StartupCo',
                    'start_date': '2018',
                    'end_date': '2020',
                    'description': 'Built REST APIs and microservices'
                }
            ],
            'education': [
                {
                    'degree': 'Bachelor of Science in Computer Science',
                    'institution': 'University of Technology',
                    'start_date': '2014',
                    'end_date': '2018'
                }
            ],
            'processing_backend_used': 'gemini',
            'confidence_score': 0.85
        }
    
    @patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text')
    @patch('roadmap.services.ai_processor.AIProcessor.process_resume_text')
    @patch('roadmap.services.cleanup_service.CleanupService.cleanup_temp_file')
    def test_successful_resume_processing_workflow(self, mock_cleanup, mock_ai_process, mock_pdf_extract):
        """
        Test complete successful upload and processing workflow
        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
        """
        # Mock successful processing
        mock_pdf_extract.return_value = self.sample_extracted_text
        mock_ai_process.return_value = self.sample_processed_data
        mock_cleanup.return_value = True
        
        # Create test file
        test_file = SimpleUploadedFile(
            "test_resume.pdf",
            self.valid_pdf_content,
            content_type="application/pdf"
        )
        
        # Make request
        response = self.client.post(self.url, {
            'resume_file': test_file,
            'processing_backend': 'gemini'
        }, format='multipart')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertEqual(response_data['name'], 'John Doe')
        self.assertEqual(response_data['email'], 'john.doe@email.com')
        self.assertEqual(response_data['processing_backend_used'], 'gemini')
        self.assertIn('processing_time_seconds', response_data)
        self.assertIsInstance(response_data['skills'], list)
        self.assertIsInstance(response_data['experience'], list)
        
        # Verify services were called
        mock_pdf_extract.assert_called_once()
        mock_ai_process.assert_called_once_with(self.sample_extracted_text, 'gemini')
        mock_cleanup.assert_called_once()
    
    @patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text')
    @patch('roadmap.services.cleanup_service.CleanupService.cleanup_on_error')
    def test_pdf_extraction_error_handling(self, mock_cleanup_error, mock_pdf_extract):
        """
        Test error handling when PDF extraction fails
        Requirements: 4.2, 4.3
        """
        # Mock PDF extraction failure
        mock_pdf_extract.side_effect = PDFExtractionError("Failed to extract text from corrupted PDF")
        
        test_file = SimpleUploadedFile(
            "corrupted_resume.pdf",
            self.valid_pdf_content,
            content_type="application/pdf"
        )
        
        response = self.client.post(self.url, {
            'resume_file': test_file
        }, format='multipart')
        
        # Verify error response
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        response_data = response.json()
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error']['code'], 'PDF_EXTRACTION_ERROR')
        self.assertIn('Failed to extract text from PDF', response_data['error']['message'])
        
        # Verify cleanup was called
        mock_cleanup_error.assert_called_once()
    
    @patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text')
    @patch('roadmap.services.ai_processor.AIProcessor.process_resume_text')
    @patch('roadmap.services.cleanup_service.CleanupService.cleanup_on_error')
    def test_ai_processing_error_handling(self, mock_cleanup_error, mock_ai_process, mock_pdf_extract):
        """
        Test error handling when AI processing fails
        Requirements: 4.2, 4.3
        """
        # Mock successful PDF extraction but AI processing failure
        mock_pdf_extract.return_value = self.sample_extracted_text
        mock_ai_process.side_effect = AIProcessingError("Gemini API unavailable", backend='gemini')
        
        test_file = SimpleUploadedFile(
            "test_resume.pdf",
            self.valid_pdf_content,
            content_type="application/pdf"
        )
        
        response = self.client.post(self.url, {
            'resume_file': test_file,
            'processing_backend': 'gemini'
        }, format='multipart')
        
        # Verify error response
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        response_data = response.json()
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error']['code'], 'AI_PROCESSING_ERROR')
        self.assertIn('Failed to process resume text', response_data['error']['message'])
        
        # Verify cleanup was called
        mock_cleanup_error.assert_called_once()
    
    def test_invalid_file_format_validation(self):
        """
        Test file format validation for non-PDF files
        Requirements: 4.1
        """
        # Create non-PDF file
        invalid_file = SimpleUploadedFile(
            "resume.txt",
            b"This is not a PDF file",
            content_type="text/plain"
        )
        
        response = self.client.post(self.url, {
            'resume_file': invalid_file
        }, format='multipart')
        
        # Verify validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error']['code'], 'VALIDATION_ERROR')
        self.assertIn('resume_file', response_data['error']['details'])
    
    @override_settings(RESUME_PARSER_MAX_FILE_SIZE_MB=1)
    def test_file_size_limit_validation(self):
        """
        Test file size limit validation
        Requirements: 4.4
        """
        # Create large file content (2MB)
        large_content = b'%PDF-1.4\n' + b'x' * (2 * 1024 * 1024)
        
        large_file = SimpleUploadedFile(
            "large_resume.pdf",
            large_content,
            content_type="application/pdf"
        )
        
        response = self.client.post(self.url, {
            'resume_file': large_file
        }, format='multipart')
        
        # Verify size validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error']['code'], 'VALIDATION_ERROR')
    
    def test_missing_file_validation(self):
        """
        Test validation when no file is provided
        Requirements: 4.1
        """
        response = self.client.post(self.url, {
            'processing_backend': 'auto'
        }, format='multipart')
        
        # Verify validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error']['code'], 'VALIDATION_ERROR')
        self.assertIn('resume_file', response_data['error']['details'])
    
    @patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text')
    @patch('roadmap.services.ai_processor.AIProcessor.process_resume_text')
    @patch('roadmap.services.cleanup_service.CleanupService.cleanup_temp_file')
    def test_backend_selection_parameter(self, mock_cleanup, mock_ai_process, mock_pdf_extract):
        """
        Test different backend selection options
        Requirements: 6.1, 6.2, 6.3
        """
        mock_pdf_extract.return_value = self.sample_extracted_text
        mock_cleanup.return_value = True
        
        backends_to_test = ['auto', 'gemini', 'spacy', 'rule_based']
        
        for backend in backends_to_test:
            with self.subTest(backend=backend):
                # Mock AI processor to return backend-specific data
                backend_data = self.sample_processed_data.copy()
                backend_data['processing_backend_used'] = backend
                mock_ai_process.return_value = backend_data
                
                test_file = SimpleUploadedFile(
                    f"test_resume_{backend}.pdf",
                    self.valid_pdf_content,
                    content_type="application/pdf"
                )
                
                response = self.client.post(self.url, {
                    'resume_file': test_file,
                    'processing_backend': backend
                }, format='multipart')
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                response_data = response.json()
                self.assertEqual(response_data['processing_backend_used'], backend)
    
    @patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text')
    @patch('roadmap.services.ai_processor.AIProcessor.process_resume_text')
    @patch('roadmap.services.cleanup_service.CleanupService.cleanup_temp_file')
    def test_include_raw_text_parameter(self, mock_cleanup, mock_ai_process, mock_pdf_extract):
        """
        Test include_raw_text parameter functionality
        Requirements: 1.4
        """
        mock_pdf_extract.return_value = self.sample_extracted_text
        mock_ai_process.return_value = self.sample_processed_data
        mock_cleanup.return_value = True
        
        test_file = SimpleUploadedFile(
            "test_resume.pdf",
            self.valid_pdf_content,
            content_type="application/pdf"
        )
        
        # Test with include_raw_text=True
        response = self.client.post(self.url, {
            'resume_file': test_file,
            'include_raw_text': True
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn('raw_text', response_data)
        self.assertEqual(response_data['raw_text'], self.sample_extracted_text)
        
        # Test with include_raw_text=False (default)
        test_file2 = SimpleUploadedFile(
            "test_resume2.pdf",
            self.valid_pdf_content,
            content_type="application/pdf"
        )
        
        response = self.client.post(self.url, {
            'resume_file': test_file2,
            'include_raw_text': False
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertNotIn('raw_text', response_data)
    
    @patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text')
    @patch('roadmap.services.ai_processor.AIProcessor.process_resume_text')
    @patch('roadmap.services.cleanup_service.CleanupService.cleanup_temp_file')
    def test_file_cleanup_verification(self, mock_cleanup, mock_ai_process, mock_pdf_extract):
        """
        Test that temporary files are properly cleaned up after processing
        Requirements: 5.1, 5.2, 5.3
        """
        mock_pdf_extract.return_value = self.sample_extracted_text
        mock_ai_process.return_value = self.sample_processed_data
        mock_cleanup.return_value = True
        
        test_file = SimpleUploadedFile(
            "test_resume.pdf",
            self.valid_pdf_content,
            content_type="application/pdf"
        )
        
        response = self.client.post(self.url, {
            'resume_file': test_file
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify cleanup was called exactly once
        mock_cleanup.assert_called_once()
        
        # Verify the cleanup was called with a file path
        cleanup_call_args = mock_cleanup.call_args[0]
        self.assertTrue(len(cleanup_call_args) > 0)
        self.assertIsInstance(cleanup_call_args[0], str)
    
    @patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text')
    @patch('roadmap.services.cleanup_service.CleanupService.cleanup_on_error')
    def test_cleanup_on_unexpected_error(self, mock_cleanup_error, mock_pdf_extract):
        """
        Test that cleanup happens even when unexpected errors occur
        Requirements: 5.3
        """
        # Mock an unexpected exception during PDF extraction
        mock_pdf_extract.side_effect = Exception("Unexpected error")
        
        test_file = SimpleUploadedFile(
            "test_resume.pdf",
            self.valid_pdf_content,
            content_type="application/pdf"
        )
        
        response = self.client.post(self.url, {
            'resume_file': test_file
        }, format='multipart')
        
        # Verify error response
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        response_data = response.json()
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error']['code'], 'INTERNAL_SERVER_ERROR')
        
        # Verify cleanup was called
        mock_cleanup_error.assert_called_once()
    
    def test_invalid_backend_parameter(self):
        """
        Test validation of invalid backend parameter
        Requirements: 4.1
        """
        test_file = SimpleUploadedFile(
            "test_resume.pdf",
            self.valid_pdf_content,
            content_type="application/pdf"
        )
        
        response = self.client.post(self.url, {
            'resume_file': test_file,
            'processing_backend': 'invalid_backend'
        }, format='multipart')
        
        # Verify validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        response_data = response.json()
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error']['code'], 'VALIDATION_ERROR')
        self.assertIn('processing_backend', response_data['error']['details'])


class HealthCheckViewIntegrationTests(APITestCase):
    """
    Integration tests for HealthCheckView API endpoint
    Tests system health monitoring and backend status
    """
    
    def setUp(self):
        """Set up test data and configuration"""
        self.url = reverse('roadmap:v1:health-check')
        
        # Create test configuration
        self.config = ResumeParserConfig.objects.create(
            max_file_size_mb=10,
            default_backend='auto',
            gemini_api_key='test-key'
        )
    
    @patch('roadmap.services.ai_processor.AIProcessor.get_backend_status')
    @patch('roadmap.services.ai_processor.AIProcessor.get_available_backends')
    @patch('roadmap.services.cleanup_service.CleanupService.get_temp_dir_stats')
    def test_healthy_system_status(self, mock_temp_stats, mock_available_backends, mock_backend_status):
        """
        Test health check when all systems are healthy
        Requirements: 6.1, 6.5
        """
        # Mock healthy system responses
        mock_backend_status.return_value = {
            'gemini': {'status': 'healthy', 'response_time_ms': 150},
            'spacy': {'status': 'healthy', 'model_loaded': True},
            'rule_based': {'status': 'healthy'}
        }
        mock_available_backends.return_value = ['gemini', 'spacy', 'rule_based']
        mock_temp_stats.return_value = {
            'file_count': 0,
            'total_size_bytes': 0,
            'oldest_file_age_minutes': 0,
            'temp_dir': '/tmp'
        }
        
        response = self.client.get(self.url)
        
        # Verify healthy response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertEqual(response_data['status'], 'healthy')
        self.assertIn('backends', response_data)
        self.assertIn('configuration', response_data)
        
        # Verify backend information
        self.assertEqual(len(response_data['backends']), 3)
        self.assertIn('gemini', response_data['backends'])
        self.assertIn('spacy', response_data['backends'])
        self.assertIn('rule_based', response_data['backends'])
        
        # Verify configuration information
        config = response_data['configuration']
        self.assertEqual(config['available_backends'], ['gemini', 'spacy', 'rule_based'])
        self.assertEqual(config['total_backends'], 3)
        self.assertEqual(config['temp_files_count'], 0)
    
    @patch('roadmap.services.ai_processor.AIProcessor.get_backend_status')
    @patch('roadmap.services.ai_processor.AIProcessor.get_available_backends')
    @patch('roadmap.services.cleanup_service.CleanupService.get_temp_dir_stats')
    def test_degraded_system_status(self, mock_temp_stats, mock_available_backends, mock_backend_status):
        """
        Test health check when some backends are unavailable
        Requirements: 6.1, 6.5
        """
        # Mock degraded system - some backends down
        mock_backend_status.return_value = {
            'gemini': {'status': 'unhealthy', 'error': 'API key invalid'},
            'spacy': {'status': 'healthy', 'model_loaded': True},
            'rule_based': {'status': 'healthy'}
        }
        mock_available_backends.return_value = ['spacy', 'rule_based']  # gemini unavailable
        mock_temp_stats.return_value = {
            'file_count': 2,
            'total_size_bytes': 1048576,  # 1MB
            'oldest_file_age_minutes': 5,
            'temp_dir': '/tmp'
        }
        
        response = self.client.get(self.url)
        
        # Verify degraded response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertEqual(response_data['status'], 'degraded')
        
        # Verify backend status shows issues
        self.assertEqual(response_data['backends']['gemini']['status'], 'unhealthy')
        self.assertEqual(response_data['backends']['spacy']['status'], 'healthy')
        
        # Verify configuration shows reduced availability
        config = response_data['configuration']
        self.assertEqual(config['available_backends'], ['spacy', 'rule_based'])
        self.assertEqual(config['total_backends'], 3)
        self.assertEqual(config['temp_files_count'], 2)
        self.assertEqual(config['temp_files_size_mb'], 1.0)
    
    @patch('roadmap.services.ai_processor.AIProcessor.get_backend_status')
    @patch('roadmap.services.ai_processor.AIProcessor.get_available_backends')
    @patch('roadmap.services.cleanup_service.CleanupService.get_temp_dir_stats')
    def test_service_unavailable_status(self, mock_temp_stats, mock_available_backends, mock_backend_status):
        """
        Test health check when no backends are available
        Requirements: 6.1, 6.5
        """
        # Mock system with no available backends
        mock_backend_status.return_value = {
            'gemini': {'status': 'unhealthy', 'error': 'API unavailable'},
            'spacy': {'status': 'unhealthy', 'error': 'Model not loaded'},
            'rule_based': {'status': 'unhealthy', 'error': 'Configuration error'}
        }
        mock_available_backends.return_value = []  # No backends available
        mock_temp_stats.return_value = {
            'file_count': 0,
            'total_size_bytes': 0,
            'oldest_file_age_minutes': 0,
            'temp_dir': '/tmp'
        }
        
        response = self.client.get(self.url)
        
        # Verify service unavailable response
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        
        response_data = response.json()
        self.assertEqual(response_data['status'], 'degraded')
        
        # Verify all backends show as unhealthy
        for backend_name, backend_info in response_data['backends'].items():
            self.assertEqual(backend_info['status'], 'unhealthy')
        
        # Verify no available backends
        config = response_data['configuration']
        self.assertEqual(config['available_backends'], [])
        self.assertEqual(config['total_backends'], 3)
    
    @patch('roadmap.services.ai_processor.AIProcessor.get_backend_status')
    def test_health_check_error_handling(self, mock_backend_status):
        """
        Test health check error handling when service calls fail
        Requirements: 4.1, 4.2, 4.3
        """
        # Mock service failure
        mock_backend_status.side_effect = Exception("Service unavailable")
        
        response = self.client.get(self.url)
        
        # Verify error response
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        response_data = response.json()
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error']['code'], 'HEALTH_CHECK_ERROR')
        self.assertIn('Health check failed', response_data['error']['message'])
    
    @patch('roadmap.services.ai_processor.AIProcessor.get_backend_status')
    @patch('roadmap.services.ai_processor.AIProcessor.get_available_backends')
    @patch('roadmap.services.cleanup_service.CleanupService.get_temp_dir_stats')
    def test_temp_file_monitoring(self, mock_temp_stats, mock_available_backends, mock_backend_status):
        """
        Test temporary file monitoring in health check
        Requirements: 5.1, 5.2, 5.3
        """
        # Mock system with temporary files
        mock_backend_status.return_value = {
            'gemini': {'status': 'healthy'},
            'spacy': {'status': 'healthy'},
            'rule_based': {'status': 'healthy'}
        }
        mock_available_backends.return_value = ['gemini', 'spacy', 'rule_based']
        mock_temp_stats.return_value = {
            'file_count': 5,
            'total_size_bytes': 52428800,  # 50MB
            'oldest_file_age_minutes': 15,
            'temp_dir': '/tmp/resume_parser'
        }
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        config = response_data['configuration']
        
        # Verify temp file statistics
        self.assertEqual(config['temp_files_count'], 5)
        self.assertEqual(config['temp_files_size_mb'], 50.0)
        self.assertEqual(config['oldest_temp_file_age_minutes'], 15)
        self.assertEqual(config['temp_directory'], '/tmp/resume_parser')


class SecurityIntegrationTests(APITestCase):
    """
    Integration tests for security measures and file handling
    Tests file isolation, cleanup, and security validation
    """
    
    def setUp(self):
        """Set up test data and configuration"""
        self.url = reverse('roadmap:v1:parse-resume')
        
        # Create test configuration
        self.config = ResumeParserConfig.objects.create(
            max_file_size_mb=10,
            default_backend='auto'
        )
    
    def test_malicious_file_rejection(self):
        """
        Test rejection of potentially malicious files
        Requirements: 5.5
        """
        # Test various malicious file types
        malicious_files = [
            ("malware.exe", b"MZ\x90\x00", "application/x-msdownload"),
            ("script.js", b"alert('xss')", "application/javascript"),
            ("shell.sh", b"#!/bin/bash\nrm -rf /", "application/x-sh"),
            ("fake.pdf", b"<script>alert('xss')</script>", "text/html"),
        ]
        
        for filename, content, content_type in malicious_files:
            with self.subTest(filename=filename):
                malicious_file = SimpleUploadedFile(
                    filename,
                    content,
                    content_type=content_type
                )
                
                response = self.client.post(self.url, {
                    'resume_file': malicious_file
                }, format='multipart')
                
                # Should be rejected due to file validation
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                
                response_data = response.json()
                self.assertIn('error', response_data)
                self.assertEqual(response_data['error']['code'], 'VALIDATION_ERROR')
    
    @patch('roadmap.services.cleanup_service.CleanupService.cleanup_temp_file')
    def test_file_isolation_and_cleanup(self, mock_cleanup):
        """
        Test that uploaded files are properly isolated and cleaned up
        Requirements: 5.1, 5.2, 5.4
        """
        mock_cleanup.return_value = True
        
        # Create test file with potentially sensitive content
        sensitive_content = b'%PDF-1.4\nSSN: 123-45-6789\nCredit Card: 4111-1111-1111-1111'
        
        test_file = SimpleUploadedFile(
            "sensitive_resume.pdf",
            sensitive_content,
            content_type="application/pdf"
        )
        
        with patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text') as mock_extract:
            mock_extract.side_effect = PDFExtractionError("Extraction failed")
            
            response = self.client.post(self.url, {
                'resume_file': test_file
            }, format='multipart')
            
            # Even on error, cleanup should be called
            self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
            mock_cleanup.assert_called_once()
    
    def test_concurrent_upload_handling(self):
        """
        Test handling of concurrent file uploads
        Requirements: 5.4
        """
        import threading
        import time
        
        results = []
        
        def upload_file(file_num):
            """Upload a file in a separate thread"""
            test_file = SimpleUploadedFile(
                f"concurrent_resume_{file_num}.pdf",
                b'%PDF-1.4\nTest content for file ' + str(file_num).encode(),
                content_type="application/pdf"
            )
            
            with patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text') as mock_extract:
                mock_extract.side_effect = PDFExtractionError("Simulated error")
                
                response = self.client.post(self.url, {
                    'resume_file': test_file
                }, format='multipart')
                
                results.append({
                    'file_num': file_num,
                    'status_code': response.status_code,
                    'thread_id': threading.current_thread().ident
                })
        
        # Create multiple threads to upload files concurrently
        threads = []
        for i in range(3):
            thread = threading.Thread(target=upload_file, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all uploads were handled properly
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertEqual(result['status_code'], status.HTTP_422_UNPROCESSABLE_ENTITY)
            self.assertIsNotNone(result['thread_id'])
    
    @patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text')
    @patch('roadmap.services.ai_processor.AIProcessor.process_resume_text')
    def test_sensitive_data_not_logged(self, mock_ai_process, mock_pdf_extract):
        """
        Test that sensitive data is not exposed in logs or responses
        Requirements: 5.5
        """
        # Mock extraction of sensitive data
        sensitive_text = """
        John Doe
        SSN: 123-45-6789
        Credit Card: 4111-1111-1111-1111
        Bank Account: 987654321
        """
        
        mock_pdf_extract.return_value = sensitive_text
        mock_ai_process.return_value = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'processing_backend_used': 'rule_based',
            'confidence_score': 0.7
        }
        
        test_file = SimpleUploadedFile(
            "sensitive_resume.pdf",
            b'%PDF-1.4\nSensitive content',
            content_type="application/pdf"
        )
        
        with patch('roadmap.services.cleanup_service.CleanupService.cleanup_temp_file'):
            response = self.client.post(self.url, {
                'resume_file': test_file,
                'include_raw_text': False  # Ensure raw text is not included
            }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        response_str = json.dumps(response_data)
        
        # Verify sensitive data is not in response
        self.assertNotIn('123-45-6789', response_str)
        self.assertNotIn('4111-1111-1111-1111', response_str)
        self.assertNotIn('987654321', response_str)
        self.assertNotIn('raw_text', response_data)  # Raw text should not be included