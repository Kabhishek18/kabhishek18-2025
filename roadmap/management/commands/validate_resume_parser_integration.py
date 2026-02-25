"""
Management command to validate Resume Parser integration with the project
"""
import os
import tempfile
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIClient
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Validate Resume Parser integration with the existing project structure'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--test-auth',
            action='store_true',
            help='Test authentication integration',
        )
        parser.add_argument(
            '--test-backends',
            action='store_true',
            help='Test AI backend availability',
        )
        parser.add_argument(
            '--test-config',
            action='store_true',
            help='Test configuration integration',
        )
        parser.add_argument(
            '--test-all',
            action='store_true',
            help='Run all integration tests',
        )
    
    def handle(self, *args, **options):
        """Run integration validation tests"""
        self.stdout.write(
            self.style.SUCCESS('Starting Resume Parser Integration Validation...\n')
        )
        
        test_all = options['test_all']
        
        # Run tests based on options
        if test_all or options['test_config']:
            self.test_configuration_integration()
        
        if test_all or options['test_backends']:
            self.test_backend_integration()
        
        if test_all or options['test_auth']:
            self.test_authentication_integration()
        
        # Always run basic integration tests
        self.test_url_integration()
        self.test_middleware_integration()
        self.test_admin_integration()
        
        self.stdout.write(
            self.style.SUCCESS('\n✓ Resume Parser Integration Validation Complete!')
        )
    
    def test_configuration_integration(self):
        """Test configuration model integration"""
        self.stdout.write('Testing Configuration Integration...')
        
        try:
            from roadmap.models import ResumeParserConfig
            
            # Test configuration model
            config = ResumeParserConfig.get_config()
            self.stdout.write(f'  ✓ Configuration model accessible: {config}')
            
            # Test settings integration
            resume_settings = getattr(settings, 'RESUME_PARSER_SETTINGS', {})
            if resume_settings:
                self.stdout.write(f'  ✓ Settings integration working: {len(resume_settings)} settings found')
            else:
                self.stdout.write(
                    self.style.WARNING('  ⚠ RESUME_PARSER_SETTINGS not found in Django settings')
                )
            
            # Test environment variables
            env_vars = [
                'GEMINI_API_KEY',
                'RESUME_PARSER_MAX_FILE_SIZE',
                'RESUME_PARSER_DEFAULT_BACKEND'
            ]
            
            for var in env_vars:
                value = os.getenv(var)
                if value:
                    self.stdout.write(f'  ✓ Environment variable {var} is set')
                else:
                    self.stdout.write(f'  - Environment variable {var} not set (optional)')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ✗ Configuration integration error: {e}')
            )
    
    def test_backend_integration(self):
        """Test AI backend integration"""
        self.stdout.write('Testing AI Backend Integration...')
        
        try:
            from roadmap.services.ai_processor import AIProcessor
            
            processor = AIProcessor()
            
            # Test backend status
            status = processor.get_backend_status()
            self.stdout.write(f'  ✓ Backend status check working: {len(status)} backends found')
            
            for backend_name, backend_status in status.items():
                if backend_status['available']:
                    self.stdout.write(f'    ✓ {backend_status["backend_name"]}: Available')
                else:
                    error = backend_status.get('error', 'Unknown error')
                    self.stdout.write(f'    ✗ {backend_status["backend_name"]}: {error}')
            
            # Test available backends
            available = processor.get_available_backends()
            if available:
                self.stdout.write(f'  ✓ Available backends: {", ".join(available)}')
            else:
                self.stdout.write(
                    self.style.WARNING('  ⚠ No backends available - check configuration')
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ✗ Backend integration error: {e}')
            )
    
    def test_authentication_integration(self):
        """Test authentication system integration"""
        self.stdout.write('Testing Authentication Integration...')
        
        try:
            from api.authentication import CombinedAPIAuthentication, get_authenticated_client
            from django.test import RequestFactory
            
            # Test authentication classes
            auth = CombinedAPIAuthentication()
            self.stdout.write('  ✓ CombinedAPIAuthentication class accessible')
            
            # Test helper functions
            factory = RequestFactory()
            request = factory.get('/api/roadmap/health/')
            request.user = AnonymousUser()
            
            client = get_authenticated_client(request)
            if client is None:
                self.stdout.write('  ✓ get_authenticated_client works for anonymous users')
            
            # Test REST framework integration
            rest_auth_classes = getattr(settings, 'REST_FRAMEWORK', {}).get('DEFAULT_AUTHENTICATION_CLASSES', [])
            if 'api.authentication.CombinedAPIAuthentication' in rest_auth_classes:
                self.stdout.write('  ✓ CombinedAPIAuthentication in REST_FRAMEWORK settings')
            else:
                self.stdout.write(
                    self.style.WARNING('  ⚠ CombinedAPIAuthentication not in REST_FRAMEWORK settings')
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ✗ Authentication integration error: {e}')
            )
    
    def test_url_integration(self):
        """Test URL configuration integration"""
        self.stdout.write('Testing URL Integration...')
        
        try:
            from django.urls import reverse, NoReverseMatch
            
            # Test URL patterns
            urls_to_test = [
                ('roadmap:v1:parse-resume', 'parse-resume'),
                ('roadmap:v1:health-check', 'health-check'),
            ]
            
            for url_name, description in urls_to_test:
                try:
                    url = reverse(url_name)
                    self.stdout.write(f'  ✓ URL {description}: {url}')
                except NoReverseMatch:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ URL {description} not found: {url_name}')
                    )
            
            # Test main project URL integration
            from django.conf import settings
            if 'roadmap' in settings.INSTALLED_APPS:
                self.stdout.write('  ✓ roadmap app in INSTALLED_APPS')
            else:
                self.stdout.write(
                    self.style.ERROR('  ✗ roadmap app not in INSTALLED_APPS')
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ✗ URL integration error: {e}')
            )
    
    def test_middleware_integration(self):
        """Test middleware integration"""
        self.stdout.write('Testing Middleware Integration...')
        
        try:
            # Check if Resume Parser middleware is available
            from roadmap.middleware import (
                ResumeParserRateLimitMiddleware,
                ResumeParserLoggingMiddleware,
                ResumeParserSecurityMiddleware
            )
            
            self.stdout.write('  ✓ Resume Parser middleware classes accessible')
            
            # Test middleware instantiation
            from django.http import HttpRequest
            
            def dummy_get_response(request):
                from django.http import HttpResponse
                return HttpResponse()
            
            # Test each middleware
            middlewares = [
                ('Rate Limiting', ResumeParserRateLimitMiddleware),
                ('Logging', ResumeParserLoggingMiddleware),
                ('Security', ResumeParserSecurityMiddleware),
            ]
            
            for name, middleware_class in middlewares:
                try:
                    middleware = middleware_class(dummy_get_response)
                    self.stdout.write(f'  ✓ {name} middleware instantiated successfully')
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ {name} middleware error: {e}')
                    )
            
        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(f'  ✗ Middleware import error: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ✗ Middleware integration error: {e}')
            )
    
    def test_admin_integration(self):
        """Test admin interface integration"""
        self.stdout.write('Testing Admin Integration...')
        
        try:
            from django.contrib import admin
            from roadmap.models import ResumeParserConfig
            
            # Check if model is registered
            if ResumeParserConfig in admin.site._registry:
                self.stdout.write('  ✓ ResumeParserConfig registered in admin')
                
                # Test admin class
                admin_class = admin.site._registry[ResumeParserConfig]
                self.stdout.write(f'  ✓ Admin class: {admin_class.__class__.__name__}')
                
                # Test admin actions
                actions = admin_class.get_actions(None)
                if actions:
                    action_names = list(actions.keys())
                    self.stdout.write(f'  ✓ Admin actions available: {", ".join(action_names)}')
                
            else:
                self.stdout.write(
                    self.style.ERROR('  ✗ ResumeParserConfig not registered in admin')
                )
            
            # Check admin navigation integration
            unfold_config = getattr(settings, 'UNFOLD', {})
            sidebar = unfold_config.get('SIDEBAR', {})
            navigation = sidebar.get('navigation', [])
            
            resume_parser_section = None
            for section in navigation:
                if section.get('title') == 'Resume Parser':
                    resume_parser_section = section
                    break
            
            if resume_parser_section:
                self.stdout.write('  ✓ Resume Parser section in admin navigation')
            else:
                self.stdout.write(
                    self.style.WARNING('  ⚠ Resume Parser section not found in admin navigation')
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ✗ Admin integration error: {e}')
            )
    
    def test_api_endpoints(self):
        """Test API endpoints functionality"""
        self.stdout.write('Testing API Endpoints...')
        
        try:
            from django.test import Client
            
            client = Client()
            
            # Test health endpoint
            response = client.get('/api/roadmap/health/')
            if response.status_code in [200, 503]:  # 503 is acceptable if backends are down
                self.stdout.write(f'  ✓ Health endpoint accessible: HTTP {response.status_code}')
            else:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Health endpoint error: HTTP {response.status_code}')
                )
            
            # Test parse-resume endpoint (should require POST with file)
            response = client.get('/api/roadmap/parse-resume/')
            if response.status_code == 405:  # Method not allowed is expected for GET
                self.stdout.write('  ✓ Parse-resume endpoint accessible (POST required)')
            else:
                self.stdout.write(f'  - Parse-resume endpoint: HTTP {response.status_code}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ✗ API endpoint test error: {e}')
            )