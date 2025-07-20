"""
Extended tests for the URL Discovery Service.
"""
from unittest import mock
from django.test import TestCase, override_settings
from django.urls import path, include, re_path
from django.http import HttpResponse
from site_files.services.url_discovery import URLDiscoveryService, URLInfo


# Mock views for testing
def mock_view(request):
    return HttpResponse("Mock View")


# Test URL patterns for testing
test_urlpatterns = [
    path('', mock_view, name='home'),
    path('about/', mock_view, name='about'),
    path('contact/', mock_view, name='contact'),
    path('blog/', include([
        path('', mock_view, name='blog_list'),
        path('<slug:slug>/', mock_view, name='blog_detail'),
        path('category/<slug:category>/', mock_view, name='blog_category'),
    ])),
    path('api/', include([
        path('docs/', mock_view, name='api_docs'),
        path('auth/', include([
            path('login/', mock_view, name='api_login'),
            path('logout/', mock_view, name='api_logout'),
        ])),
    ])),
    re_path(r'^legacy/(?P<page_id>\d+)/$', mock_view, name='legacy_page'),
    path('admin/', include([
        path('', mock_view, name='admin_index'),
        path('users/', mock_view, name='admin_users'),
    ])),
]


class URLDiscoveryExtendedTestCase(TestCase):
    """Extended test case for the URLDiscoveryService."""
    
    def setUp(self):
        """Set up test data."""
        self.service = URLDiscoveryService(site_url='https://example.com')
    
    @mock.patch('django.urls.get_resolver')
    def test_extract_patterns_with_complex_urls(self, mock_get_resolver):
        """Test extraction of URL patterns with complex patterns."""
        # Create a mock resolver with our test patterns
        mock_resolver = mock.MagicMock()
        mock_resolver.url_patterns = test_urlpatterns
        mock_get_resolver.return_value = mock_resolver
        
        # Mock the _extract_patterns_from_resolver method to use our test patterns
        with mock.patch.object(
            URLDiscoveryService, 
            '_extract_patterns_from_resolver', 
            return_value=[
                '',
                'about/',
                'contact/',
                'blog/',
                'blog/<slug:slug>/',
                'blog/category/<slug:category>/',
                'api/docs/',
                'api/auth/login/',
                'api/auth/logout/',
                'legacy/(?P<page_id>\\d+)/',
                'admin/',
                'admin/users/',
            ]
        ):
            # Call the method
            urls = self.service._extract_url_patterns()
            
            # Get the URLs as a list of strings for easier testing
            url_strings = [url.url for url in urls]
            
            # Check that the correct URLs were extracted and filtered
            self.assertIn('', url_strings)
            self.assertIn('about/', url_strings)
            self.assertIn('contact/', url_strings)
            self.assertIn('blog/', url_strings)
            self.assertIn('api/docs/', url_strings)
            
            # Check that URLs with parameters were filtered out
            self.assertNotIn('blog/<slug:slug>/', url_strings)
            self.assertNotIn('blog/category/<slug:category>/', url_strings)
            self.assertNotIn('legacy/(?P<page_id>\\d+)/', url_strings)
            
            # Check that excluded URLs were filtered out
            self.assertNotIn('admin/', url_strings)
            self.assertNotIn('admin/users/', url_strings)
            self.assertNotIn('api/auth/login/', url_strings)
            self.assertNotIn('api/auth/logout/', url_strings)
    
    @mock.patch('site_files.services.url_discovery.logger')
    def test_error_handling_in_url_extraction(self, mock_logger):
        """Test error handling during URL pattern extraction."""
        # Mock the get_resolver function to raise an exception
        with mock.patch('django.urls.get_resolver', side_effect=Exception('Test error')):
            # Call the method
            urls = self.service._extract_url_patterns()
            
            # Check that an empty list was returned
            self.assertEqual(urls, [])
            
            # Check that the error was logged
            mock_logger.error.assert_called_once()
            self.assertIn('Error extracting URL patterns', mock_logger.error.call_args[0][0])
    
    @mock.patch('site_files.services.url_discovery.logger')
    def test_error_handling_in_blog_post_urls(self, mock_logger):
        """Test error handling during blog post URL discovery."""
        # Mock the Post.objects.filter method to raise an exception
        with mock.patch('blog.models.Post.objects.filter', side_effect=Exception('Test error')):
            # Call the method
            urls = self.service._get_blog_post_urls()
            
            # Check that an empty list was returned
            self.assertEqual(urls, [])
            
            # Check that the error was logged
            mock_logger.error.assert_called_once()
            self.assertIn('Error discovering blog post URLs', mock_logger.error.call_args[0][0])
    
    @mock.patch('site_files.services.url_discovery.logger')
    def test_error_handling_in_blog_category_urls(self, mock_logger):
        """Test error handling during blog category URL discovery."""
        # Mock the Category.objects.all method to raise an exception
        with mock.patch('blog.models.Category.objects.all', side_effect=Exception('Test error')):
            # Call the method
            urls = self.service._get_blog_category_urls()
            
            # Check that an empty list was returned
            self.assertEqual(urls, [])
            
            # Check that the error was logged
            mock_logger.error.assert_called_once()
            self.assertIn('Error discovering blog category URLs', mock_logger.error.call_args[0][0])
    
    @mock.patch('site_files.services.url_discovery.logger')
    def test_error_handling_in_page_urls(self, mock_logger):
        """Test error handling during page URL discovery."""
        # Mock the Page.objects.filter method to raise an exception
        with mock.patch('core.models.Page.objects.filter', side_effect=Exception('Test error')):
            # Call the method
            urls = self.service._get_page_urls()
            
            # Check that an empty list was returned
            self.assertEqual(urls, [])
            
            # Check that the error was logged
            mock_logger.error.assert_called_once()
            self.assertIn('Error discovering page URLs', mock_logger.error.call_args[0][0])
    
    @override_settings(SITEMAP_EXCLUDE_PATTERNS=['blog/', 'contact/'])
    def test_exclude_patterns_from_settings(self):
        """Test that exclude patterns from settings are used."""
        # Create a new service instance to pick up the settings
        service = URLDiscoveryService(site_url='https://example.com')
        
        # Check that the exclude patterns from settings were added
        self.assertIn('blog/', service.exclude_patterns)
        self.assertIn('contact/', service.exclude_patterns)
        
        # Test filtering with these patterns
        test_urls = [
            'home',
            'about',
            'blog/',
            'contact/',
        ]
        
        public_urls = service._filter_public_urls(test_urls)
        
        # Check that the correct URLs were filtered
        self.assertEqual(len(public_urls), 2)
        self.assertIn(URLInfo(url='home'), public_urls)
        self.assertIn(URLInfo(url='about'), public_urls)
        self.assertNotIn(URLInfo(url='blog/'), public_urls)
        self.assertNotIn(URLInfo(url='contact/'), public_urls)
    
    @override_settings(SITE_URL='https://custom-example.com')
    def test_site_url_from_settings(self):
        """Test that site URL from settings is used."""
        # Create a new service instance to pick up the settings
        service = URLDiscoveryService()
        
        # Check that the site URL from settings was used
        self.assertEqual(service.site_url, 'https://custom-example.com')
    
    def test_integration_with_real_url_patterns(self):
        """Test integration with real URL patterns from the project."""
        # This test uses the actual URL configuration from the project
        service = URLDiscoveryService(site_url='https://example.com')
        
        # Call the method to extract URL patterns
        urls = service._extract_url_patterns()
        
        # Check that we got some URLs
        self.assertGreater(len(urls), 0)
        
        # Check that all URLs are URLInfo objects
        for url in urls:
            self.assertIsInstance(url, URLInfo)
            
        # Check that all URLs have the expected attributes
        for url in urls:
            self.assertTrue(hasattr(url, 'url'))
            self.assertTrue(hasattr(url, 'changefreq'))
            self.assertTrue(hasattr(url, 'priority'))
            self.assertTrue(hasattr(url, 'type'))


if __name__ == '__main__':
    from django.test import runner
    runner.main()
</text>
</invoke>