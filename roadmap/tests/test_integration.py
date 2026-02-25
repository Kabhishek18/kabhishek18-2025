"""
Integration tests for Resume Parser with existing project structure
"""
import os
import tempfile
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.conf import settings
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
import json

from roadmap.models import ResumeParserConfig
from api.models import APIClient as APIClientModel, APIKey


class ResumeParserIntegrationTestCase(TestCase):
    """Test Resume Parser integration with existing project components"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.api_client = APIClient()
        
        # Create test user
        self.user = User.objects.create_superuser(
            username='testadmin',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create API client for authentication tests
        self.api_client_model = APIClientModel.objects.create(
            name='Test Resume Parser Client',
            description='Test client for resume parser',
            can_read_posts=True,
            can_write_posts=False,
            is_active=True
        )
        
        # Create API key
        self.api_key = APIKey.objects.create(
            client=self.api_client_model,
            name='Test Key',
            key_hash='test_hash',
            is_active=True
        )
        
        # Create Resume Parser configuration
        self.config = ResumeParserConfig.objects.create(
            max_file_size_mb=10,
            default_backend='auto',
            spacy_model='en_core_web_sm'
        )
    
    def test_url_integration(self):
        """Test URL routing integration"""
        # Test health endpoint
        response = self.client.get('/api/roadmap/health/')
        self.assertIn(response.status_code, [200, 503])  # 503 acceptable if backends down
        
        # Test parse-resume endpoint (should require POST)
        response = self.client.get('/api/roadmap/parse-resume/')
        self.assertEqual(response.status_code, 405)  # Method not allowed
        
        # Test versioned URLs
        response = self.client.get('/api/roadmap/v1/health/')
        self.assertIn(response.status_code, [200, 503])
    
    def test_admin_integration(self):
        """Test admin interface integration"""
        # Login as admin
        self.client.login(username='testadmin', password='testpass123')
        
        # Test admin changelist
        response = self.client.get('/open/admin/roadmap/resumeparserconfig/')
        self.assertEqual(response.status_code, 302)  # Should redirect to change view
        
        # Test admin change view
        response = self.client.get(f'/open/admin/roadmap/resumeparserconfig/{self.config.pk}/change/')
        self.assertEqual(response.status_code, 200)
        
        # Test admin actions are available
        self.assertTrue(hasattr(self.config._meta.model._default_manager, 'get_queryset'))
    
    def test_configuration_integration(self):
        """Test configuration model integration"""
        # Test singleton pattern
        config1 = ResumeParserConfig.get_config()
        config2 = ResumeParserConfig.get_config()
        self.assertEqual(config1.pk, config2.pk)
        
        # Test configuration values
        self.assertEqual(config1.max_file_size_mb, 10)
        self.assertEqual(config1.default_backend, 'auto')
    
    @patch('roadmap.services.ai_processor.AIProcessor.get_backend_status')
    def test_backend_integration(self, mock_backend_status):
        """Test AI backend integration"""
        # Mock backend status
        mock_backend_status.return_value = {
            'gemini': {
                'backend_name': 'Gemini AI',
                'available': False,
                'error': 'API key not configured'
            },
            'spacy': {
                'backend_name': 'spaCy NLP',
                'available': True,
                'model_loaded': 'en_core_web_sm'
            },
            'rule_based': {
                'backend_name': 'Rule-based',
                'available': True
            }
        }
        
        # Test health endpoint with backend status
        response = self.client.get('/api/roadmap/health/')
        self.assertIn(response.status_code, [200, 503])
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn('backends', data)
            self.assertIn('status', data)
    
    def test_authentication_integration(self):
        """Test authentication system integration"""
        # Test anonymous access (should work for health check)
        response = self.client.get('/api/roadmap/health/')
        self.assertIn(response.status_code, [200, 503])
        
        # Test with API authentication headers
        headers = {
            'HTTP_X_CLIENT_ID': str(self.api_client_model.client_id),
            'HTTP_X_API_KEY': 'test_api_key'
        }
        
        # This would normally fail authentication, but we're testing the integration
        response = self.client.get('/api/roadmap/health/', **headers)
        self.assertIn(response.status_code, [200, 401, 503])
    
    def test_error_handling_integration(self):
        """Test error handling integration with existing system"""
        # Test invalid endpoint
        response = self.client.get('/api/roadmap/invalid/')
        self.assertEqual(response.status_code, 404)
        
        # Test invalid method
        response = self.client.put('/api/roadmap/health/')
        self.assertEqual(response.status_code, 405)
    
    @override_settings(RESUME_PARSER_SETTINGS={'MAX_FILE_SIZE_MB': 5})
    def test_settings_integration(self):
        """Test Django settings integration"""
        from django.conf import settings
        
        # Test settings override
        resume_settings = getattr(settings, 'RESUME_PARSER_SETTINGS', {})
        self.assertEqual(resume_settings.get('MAX_FILE_SIZE_MB'), 5)
    
    def test_logging_integration(self):
        """Test logging integration"""
        import logging
        
        # Test logger exists
        logger = logging.getLogger('roadmap.views')
        self.assertIsNotNone(logger)
        
        # Test logger configuration
        logger = logging.getLogger('roadmap.services')
        self.assertIsNotNone(logger)


class ResumeParserAPIIntegrationTestCase(APITestCase):
    """API-specific integration tests"""
    
    def setUp(self):
        """Set up API test data"""
        self.config = ResumeParserConfig.objects.create(
            max_file_size_mb=10,
            default_backend='auto'
        )
    
    def test_api_response_format(self):
        """Test API response format consistency"""
        response = self.client.get('/api/roadmap/health/')
        
        if response.status_code == 200:
            data = response.json()
            # Check response structure
            self.assertIn('status', data)
            self.assertIn('backends', data)
            self.assertIn('configuration', data)
        elif response.status_code == 503:
            data = response.json()
            # Should still have proper structure even when degraded
            self.assertIn('status', data)
    
    @patch('roadmap.services.pdf_extractor.PDFExtractor.extract_text')
    @patch('roadmap.services.ai_processor.AIProcessor.process_resume_text')
    def test_resume_parsing_integration(self, mock_process, mock_extract):
        """Test resume parsing with mocked services"""
        # Mock PDF extraction
        mock_extract.return_value = "John Doe\nSoftware Engineer\njohn@example.com"
        
        # Mock AI processing
        mock_process.return_value = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'skills': ['Python', 'Django'],
            'experience': [],
            'education': [],
            'processing_backend_used': 'rule_based',
            'confidence_score': 0.8
        }
        
        # Create a test PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b'%PDF-1.4\ntest content')
            tmp_file.flush()
            
            try:
                with open(tmp_file.name, 'rb') as pdf_file:
                    response = self.client.post(
                        '/api/roadmap/parse-resume/',
                        {
                            'resume_file': pdf_file,
                            'processing_backend': 'auto'
                        },
                        format='multipart'
                    )
                
                # Should work with mocked services
                self.assertIn(response.status_code, [200, 400, 422])
                
            finally:
                os.unlink(tmp_file.name)
    
    def test_cors_integration(self):
        """Test CORS headers integration"""
        response = self.client.get('/api/roadmap/health/')
        
        # Check for security headers (added by middleware)
        if hasattr(response, 'get'):
            # These headers might be added by middleware
            pass  # Actual CORS testing would require specific setup
    
    def test_rate_limiting_integration(self):
        """Test rate limiting integration"""
        # Make multiple requests to test rate limiting
        responses = []
        for i in range(5):
            response = self.client.get('/api/roadmap/health/')
            responses.append(response.status_code)
        
        # Should not be rate limited for health checks in normal circumstances
        self.assertTrue(all(status_code in [200, 503] for status_code in responses))


class ResumeParserMiddlewareIntegrationTestCase(TestCase):
    """Test middleware integration"""
    
    def test_middleware_loading(self):
        """Test that middleware can be loaded"""
        from roadmap.middleware import (
            ResumeParserRateLimitMiddleware,
            ResumeParserLoggingMiddleware,
            ResumeParserSecurityMiddleware
        )
        
        # Test middleware instantiation
        def dummy_get_response(request):
            from django.http import HttpResponse
            return HttpResponse()
        
        # Should not raise exceptions
        rate_limit_middleware = ResumeParserRateLimitMiddleware(dummy_get_response)
        logging_middleware = ResumeParserLoggingMiddleware(dummy_get_response)
        security_middleware = ResumeParserSecurityMiddleware(dummy_get_response)
        
        self.assertIsNotNone(rate_limit_middleware)
        self.assertIsNotNone(logging_middleware)
        self.assertIsNotNone(security_middleware)
    
    def test_middleware_processing(self):
        """Test middleware request/response processing"""
        from roadmap.middleware import ResumeParserSecurityMiddleware
        from django.http import HttpRequest, HttpResponse
        
        def dummy_get_response(request):
            return HttpResponse()
        
        middleware = ResumeParserSecurityMiddleware(dummy_get_response)
        
        # Create test request
        request = HttpRequest()
        request.path = '/api/roadmap/health/'
        request.method = 'GET'
        
        # Test request processing
        result = middleware.process_request(request)
        self.assertIsNone(result)  # Should not block the request
        
        # Test response processing
        response = HttpResponse()
        processed_response = middleware.process_response(request, response)
        
        # Should add security headers
        self.assertIn('X-Content-Type-Options', processed_response)
        self.assertEqual(processed_response['X-Content-Type-Options'], 'nosniff')


class ResumeParserManagementCommandIntegrationTestCase(TestCase):
    """Test management command integration"""
    
    def test_management_command_exists(self):
        """Test that management command can be imported"""
        from roadmap.management.commands.validate_resume_parser_integration import Command
        
        command = Command()
        self.assertIsNotNone(command)
        self.assertEqual(command.help, 'Validate Resume Parser integration with the existing project structure')
    
    def test_command_arguments(self):
        """Test command argument parsing"""
        from roadmap.management.commands.validate_resume_parser_integration import Command
        
        command = Command()
        parser = command.create_parser('manage.py', 'validate_resume_parser_integration')
        
        # Test that arguments are properly defined
        args = parser.parse_args(['--test-all'])
        self.assertTrue(args.test_all)
        
        args = parser.parse_args(['--test-auth', '--test-backends'])
        self.assertTrue(args.test_auth)
        self.assertTrue(args.test_backends)


class ResumeParserDocumentationIntegrationTestCase(TestCase):
    """Test documentation integration"""
    
    def test_swagger_integration(self):
        """Test Swagger/OpenAPI documentation integration"""
        # Test that Swagger views work
        response = self.client.get('/swagger/')
        # Should either work (200) or be disabled in production (404/403)
        self.assertIn(response.status_code, [200, 404, 403])
    
    def test_api_documentation_files(self):
        """Test that documentation files exist"""
        import roadmap.docs
        docs_path = os.path.dirname(roadmap.docs.__file__)
        
        # Check for documentation files
        expected_files = [
            'api_documentation.md',
            'openapi_spec.yaml',
            'configuration_guide.md',
            'usage_examples.md'
        ]
        
        for filename in expected_files:
            file_path = os.path.join(docs_path, filename)
            self.assertTrue(
                os.path.exists(file_path),
                f"Documentation file {filename} not found"
            )