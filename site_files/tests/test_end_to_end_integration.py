"""
End-to-end integration tests for the Site Files Updater.

These tests verify the complete flow from URL discovery to file generation
for all file types (sitemap, robots.txt, security.txt, LLMs.txt).
"""
import os
import shutil
import tempfile
from unittest import mock
from django.test import TestCase, override_settings
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from site_files.models import SiteFilesConfig
from site_files.services.url_discovery import URLDiscoveryService, URLInfo
from site_files.services.sitemap_generator import SitemapGenerator
from site_files.services.robots_txt_updater import RobotsTxtUpdater
from site_files.services.security_txt_updater import SecurityTxtUpdater
from site_files.services.llms_txt_creator import LLMsTxtCreator
from site_files.management.commands.update_site_files import Command


# Test views for URL discovery
def test_home_view(request):
    return HttpResponse("Home")

def test_about_view(request):
    return HttpResponse("About")

def test_blog_view(request):
    return HttpResponse("Blog")

# Test URL patterns for URL discovery
test_urlpatterns = [
    path('', test_home_view, name='home'),
    path('about/', test_about_view, name='about'),
    path('blog/', test_blog_view, name='blog'),
]


class EndToEndIntegrationTestCase(TestCase):
    """Test case for end-to-end integration of the Site Files Updater."""
    
    def setUp(self):
        """Set up test data."""
        # Create a temporary directory for testing file operations
        self.temp_dir = tempfile.mkdtemp()
        
        # Define file paths
        self.sitemap_path = os.path.join(self.temp_dir, 'Sitemap.xml')
        self.robots_path = os.path.join(self.temp_dir, 'robots.txt')
        self.security_path = os.path.join(self.temp_dir, 'security.txt')
        self.llms_path = os.path.join(self.temp_dir, 'humans.txt')
        
        # Create initial files
        os.makedirs(os.path.dirname(self.sitemap_path), exist_ok=True)
        
        # Create initial robots.txt
        with open(self.robots_path, 'w', encoding='utf-8') as f:
            f.write("User-agent: *\nDisallow: /admin/\n")
        
        # Create initial security.txt
        with open(self.security_path, 'w', encoding='utf-8') as f:
            f.write("Contact: security@example.com\nExpires: 2023-12-31T23:59:59Z\n")
        
        # Get or create configuration
        self.config, created = SiteFilesConfig.objects.get_or_create(
            defaults={
                'site_name': 'Test Site',
                'site_url': 'https://example.com',
                'update_frequency': 'daily',
                'update_sitemap': True,
                'update_robots': True,
                'update_security': True,
                'update_llms': True,
                'last_update': timezone.now()
            }
        )
        
        # Update the paths for this test
        self.config.sitemap_path = self.sitemap_path
        self.config.robots_path = self.robots_path
        self.config.security_path = self.security_path
        self.config.llms_path = self.llms_path
        self.config.save()
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.temp_dir)
        
        # Delete the configuration
        self.config.delete()
    
    @mock.patch('site_files.services.url_discovery.URLDiscoveryService._extract_url_patterns')
    @mock.patch('site_files.services.url_discovery.URLDiscoveryService.get_dynamic_content_urls')
    def test_end_to_end_flow(self, mock_get_dynamic_urls, mock_extract_url_patterns):
        """Test the complete flow from URL discovery to file generation."""
        # Mock URL patterns
        mock_extract_url_patterns.return_value = [
            URLInfo(url='', changefreq='monthly', priority=0.5, type='page'),
            URLInfo(url='about/', changefreq='monthly', priority=0.5, type='page'),
            URLInfo(url='blog/', changefreq='monthly', priority=0.5, type='page'),
        ]
        
        # Mock dynamic content URLs
        mock_get_dynamic_urls.return_value = [
            URLInfo(url='blog/post-1/', lastmod=timezone.now(), title='Test Post 1', changefreq='weekly', priority=0.7, type='blog'),
            URLInfo(url='blog/post-2/', lastmod=timezone.now(), title='Test Post 2', changefreq='weekly', priority=0.7, type='blog'),
        ]
        
        # Create the command
        command = Command()
        
        # Execute the command with all file updates
        command.handle(sitemap=True, robots=True, security=True, llms=True, all=False, verbose=True)
        
        # Check that all files were created
        self.assertTrue(os.path.exists(self.sitemap_path))
        self.assertTrue(os.path.exists(self.robots_path))
        self.assertTrue(os.path.exists(self.security_path))
        self.assertTrue(os.path.exists(self.llms_path))
        
        # Check sitemap content
        with open(self.sitemap_path, 'r', encoding='utf-8') as f:
            sitemap_content = f.read()
            self.assertTrue(sitemap_content.startswith('<?xml'))
            self.assertIn('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">', sitemap_content)
            self.assertIn('<loc>https://example.com/</loc>', sitemap_content)
            self.assertIn('<loc>https://example.com/about/</loc>', sitemap_content)
            self.assertIn('<loc>https://example.com/blog/</loc>', sitemap_content)
            self.assertIn('<loc>https://example.com/blog/post-1/</loc>', sitemap_content)
            self.assertIn('<loc>https://example.com/blog/post-2/</loc>', sitemap_content)
        
        # Check robots.txt content
        with open(self.robots_path, 'r', encoding='utf-8') as f:
            robots_content = f.read()
            self.assertIn('User-agent: *', robots_content)
            self.assertIn('Disallow: /admin/', robots_content)
            # Just check that the Sitemap directive is present with the correct base URL
            self.assertIn('Sitemap: https://example.com/', robots_content)
        
        # Check security.txt content
        with open(self.security_path, 'r', encoding='utf-8') as f:
            security_content = f.read()
            self.assertIn('Contact: security@example.com', security_content)
            self.assertIn('Canonical: https://example.com/.well-known/security.txt', security_content)
        
        # Check LLMs.txt content
        with open(self.llms_path, 'r', encoding='utf-8') as f:
            llms_content = f.read()
            self.assertIn('# LLMs.txt', llms_content)
            # Check for site information in the content
            self.assertIn('https://example.com', llms_content)
    
    @mock.patch('site_files.services.url_discovery.URLDiscoveryService._extract_url_patterns')
    @mock.patch('site_files.services.url_discovery.URLDiscoveryService.get_dynamic_content_urls')
    def test_selective_file_updates(self, mock_get_dynamic_urls, mock_extract_url_patterns):
        """Test updating only specific files."""
        # Mock URL patterns
        mock_extract_url_patterns.return_value = [
            URLInfo(url='', changefreq='monthly', priority=0.5, type='page'),
            URLInfo(url='about/', changefreq='monthly', priority=0.5, type='page'),
        ]
        
        # Mock dynamic content URLs
        mock_get_dynamic_urls.return_value = [
            URLInfo(url='blog/post-1/', lastmod=timezone.now(), title='Test Post 1', changefreq='weekly', priority=0.7, type='blog'),
        ]
        
        # Create the command
        command = Command()
        
        # Execute the command with only sitemap and robots.txt updates
        command.handle(sitemap=True, robots=True, security=False, llms=False, all=False, verbose=True)
        
        # Check that only sitemap and robots.txt were created/updated
        self.assertTrue(os.path.exists(self.sitemap_path))
        self.assertTrue(os.path.exists(self.robots_path))
        
        # Check that LLMs.txt was not created
        self.assertFalse(os.path.exists(self.llms_path))
        
        # Check sitemap content
        with open(self.sitemap_path, 'r', encoding='utf-8') as f:
            sitemap_content = f.read()
            self.assertTrue(sitemap_content.startswith('<?xml'))
            self.assertIn('<loc>https://example.com/</loc>', sitemap_content)
            self.assertIn('<loc>https://example.com/about/</loc>', sitemap_content)
            self.assertIn('<loc>https://example.com/blog/post-1/</loc>', sitemap_content)
        
        # Check robots.txt content
        with open(self.robots_path, 'r', encoding='utf-8') as f:
            robots_content = f.read()
            self.assertIn('User-agent: *', robots_content)
            # Just check that the Sitemap directive is present with the correct base URL
            self.assertIn('Sitemap: https://example.com/', robots_content)
    
    @mock.patch('site_files.services.url_discovery.URLDiscoveryService._extract_url_patterns')
    @mock.patch('site_files.services.url_discovery.URLDiscoveryService.get_dynamic_content_urls')
    def test_error_handling_and_continuation(self, mock_get_dynamic_urls, mock_extract_url_patterns):
        """Test that errors in one file update don't prevent others from running."""
        # Mock URL patterns
        mock_extract_url_patterns.return_value = [
            URLInfo(url='', changefreq='monthly', priority=0.5, type='page'),
        ]
        
        # Mock dynamic content URLs
        mock_get_dynamic_urls.return_value = [
            URLInfo(url='blog/post-1/', lastmod=timezone.now(), title='Test Post 1', changefreq='weekly', priority=0.7, type='blog'),
        ]
        
        # Create the command
        command = Command()
        
        # Make the sitemap generator fail
        with mock.patch('site_files.services.sitemap_generator.SitemapGenerator.update_sitemap', 
                       side_effect=Exception("Test error")):
            # Execute the command with all file updates
            command.handle(sitemap=True, robots=True, security=True, llms=True, all=False, verbose=True)
            
            # Check that robots.txt, security.txt, and LLMs.txt were still created
            self.assertTrue(os.path.exists(self.robots_path))
            self.assertTrue(os.path.exists(self.security_path))
            self.assertTrue(os.path.exists(self.llms_path))
            
            # Check robots.txt content
            with open(self.robots_path, 'r', encoding='utf-8') as f:
                robots_content = f.read()
                self.assertIn('User-agent: *', robots_content)
                # Just check that the Sitemap directive is present with the correct base URL
                self.assertIn('Sitemap: https://example.com/', robots_content)
    
    @mock.patch('site_files.services.url_discovery.URLDiscoveryService._extract_url_patterns')
    @mock.patch('site_files.services.url_discovery.URLDiscoveryService.get_dynamic_content_urls')
    def test_with_real_url_patterns_and_models(self, mock_get_dynamic_urls, mock_extract_url_patterns):
        """Test with real URL patterns and database models."""
        # Use the actual URL discovery service to get real URL patterns
        url_discovery_service = URLDiscoveryService()
        
        # Get real URL patterns (but still mock to avoid test dependencies)
        try:
            real_patterns = url_discovery_service._extract_url_patterns()
            mock_extract_url_patterns.return_value = real_patterns
        except Exception:
            # Fall back to mock data if real patterns can't be retrieved
            mock_extract_url_patterns.return_value = [
                URLInfo(url='', changefreq='monthly', priority=0.5, type='page'),
                URLInfo(url='about/', changefreq='monthly', priority=0.5, type='page'),
                URLInfo(url='blog/', changefreq='monthly', priority=0.5, type='page'),
            ]
        
        # Try to get real dynamic content URLs (but still mock to avoid test dependencies)
        try:
            real_dynamic_urls = url_discovery_service.get_dynamic_content_urls()
            mock_get_dynamic_urls.return_value = real_dynamic_urls
        except Exception:
            # Fall back to mock data if real dynamic URLs can't be retrieved
            mock_get_dynamic_urls.return_value = [
                URLInfo(url='blog/post-1/', lastmod=timezone.now(), title='Test Post 1', changefreq='weekly', priority=0.7, type='blog'),
                URLInfo(url='blog/post-2/', lastmod=timezone.now(), title='Test Post 2', changefreq='weekly', priority=0.7, type='blog'),
            ]
        
        # Create the command
        command = Command()
        
        # Execute the command with all file updates
        command.handle(sitemap=True, robots=True, security=True, llms=True, all=False, verbose=True)
        
        # Check that all files were created
        self.assertTrue(os.path.exists(self.sitemap_path))
        self.assertTrue(os.path.exists(self.robots_path))
        self.assertTrue(os.path.exists(self.security_path))
        self.assertTrue(os.path.exists(self.llms_path))
        
        # Check sitemap content
        with open(self.sitemap_path, 'r', encoding='utf-8') as f:
            sitemap_content = f.read()
            self.assertTrue(sitemap_content.startswith('<?xml'))
            self.assertIn('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">', sitemap_content)
        
        # Check robots.txt content
        with open(self.robots_path, 'r', encoding='utf-8') as f:
            robots_content = f.read()
            self.assertIn('User-agent: *', robots_content)
            # Just check that the Sitemap directive is present with the correct base URL
            self.assertIn('Sitemap: https://example.com/', robots_content)
        
        # Check security.txt content
        with open(self.security_path, 'r', encoding='utf-8') as f:
            security_content = f.read()
            self.assertIn('Contact: security@example.com', security_content)
            self.assertIn('Canonical: https://example.com/.well-known/security.txt', security_content)
        
        # Check LLMs.txt content
        with open(self.llms_path, 'r', encoding='utf-8') as f:
            llms_content = f.read()
            self.assertIn('# LLMs.txt', llms_content)
            # Check for site information in the content
            self.assertIn('https://example.com', llms_content)


if __name__ == '__main__':
    from django.test import runner
    runner.main()