"""
Tests for the URL Discovery Service.
"""
from unittest import mock
from django.test import TestCase
from django.urls import path, include
from django.conf import settings
from site_files.services.url_discovery import URLDiscoveryService, URLInfo


class MockURLPattern:
    """Mock URL pattern for testing."""
    
    def __init__(self, pattern_str, name=None):
        self.pattern_str = pattern_str
        self.name = name
        
    @property
    def pattern(self):
        return self
    
    def describe(self):
        return self.pattern_str


class MockURLResolver:
    """Mock URL resolver for testing."""
    
    def __init__(self, url_patterns, pattern_str=None):
        self.url_patterns = url_patterns
        self.pattern_str = pattern_str
        
    @property
    def pattern(self):
        return MockURLPattern(self.pattern_str) if self.pattern_str else None


class URLDiscoveryServiceTestCase(TestCase):
    """Test case for the URLDiscoveryService."""
    
    def setUp(self):
        """Set up test data."""
        self.service = URLDiscoveryService(site_url='https://example.com')
        
        # Mock exclude patterns
        self.service.exclude_patterns = [
            r'^admin/',
            r'^api/auth/',
            r'^swagger',
        ]
    
    def test_filter_public_urls(self):
        """Test filtering of public URLs."""
        test_urls = [
            'home',
            'blog',
            'admin/dashboard',
            'api/auth/login',
            'swagger/docs',
            'about',
            'contact',
        ]
        
        public_urls = self.service._filter_public_urls(test_urls)
        
        # Check that the correct URLs were filtered
        self.assertEqual(len(public_urls), 4)
        self.assertIn(URLInfo(url='home'), public_urls)
        self.assertIn(URLInfo(url='blog'), public_urls)
        self.assertIn(URLInfo(url='about'), public_urls)
        self.assertIn(URLInfo(url='contact'), public_urls)
        
        # Check that excluded URLs were filtered out
        self.assertNotIn(URLInfo(url='admin/dashboard'), public_urls)
        self.assertNotIn(URLInfo(url='api/auth/login'), public_urls)
        self.assertNotIn(URLInfo(url='swagger/docs'), public_urls)
    
    def test_get_pattern_regex_string(self):
        """Test extraction of pattern regex string."""
        # Test with Django 2.0+ pattern
        pattern = MockURLPattern('^home/$')
        result = self.service._get_pattern_regex_string(pattern)
        self.assertEqual(result, 'home/')
        
        # Test with pattern containing special characters
        pattern = MockURLPattern('^blog/(?P<slug>[-\\w]+)/$')
        result = self.service._get_pattern_regex_string(pattern)
        self.assertEqual(result, 'blog/(?P<slug>[-\\w]+)/')
    
    @mock.patch('django.urls.get_resolver')
    def test_extract_url_patterns(self, mock_get_resolver):
        """Test extraction of URL patterns."""
        # Create mock URL patterns
        mock_patterns = [
            MockURLPattern('^$', name='home'),
            MockURLPattern('^about/$', name='about'),
            MockURLPattern('^contact/$', name='contact'),
            MockURLPattern('^admin/$', name='admin'),
            MockURLResolver([
                MockURLPattern('^$', name='blog_list'),
                MockURLPattern('^(?P<slug>[-\\w]+)/$', name='blog_detail'),
            ], '^blog/'),
            MockURLResolver([
                MockURLPattern('^login/$', name='login'),
                MockURLPattern('^logout/$', name='logout'),
            ], '^api/auth/'),
        ]
        
        # Set up the mock resolver
        mock_resolver = MockURLResolver(mock_patterns)
        mock_get_resolver.return_value = mock_resolver
        
        # Call the method
        urls = self.service._extract_url_patterns()
        
        # Get the URLs as a list of strings for easier testing
        url_strings = [url.url for url in urls]
        
        # Check that the correct URLs were extracted
        self.assertEqual(len(urls), 3)
        self.assertIn('about/', url_strings)
        self.assertIn('contact/', url_strings)
        self.assertIn('blog/', url_strings)
        
        # Check that excluded URLs were filtered out
        self.assertNotIn('admin/', url_strings)
        self.assertNotIn('api/auth/login/', url_strings)
        
        # Check that URLs with parameters were filtered out
        self.assertNotIn('blog/(?P<slug>[-\\w]+)/', url_strings)
    
    @mock.patch.object(URLDiscoveryService, '_extract_url_patterns')
    @mock.patch.object(URLDiscoveryService, 'get_dynamic_content_urls')
    def test_get_all_public_urls(self, mock_get_dynamic, mock_extract_patterns):
        """Test getting all public URLs."""
        # Set up mock return values
        mock_extract_patterns.return_value = [
            URLInfo(url=''),
            URLInfo(url='about/'),
            URLInfo(url='contact/'),
        ]
        mock_get_dynamic.return_value = [
            URLInfo(url='blog/post-1', type='blog'),
            URLInfo(url='blog/post-2', type='blog'),
            # Add a duplicate to test deduplication
            URLInfo(url='about/', type='page'),
        ]
        
        # Call the method
        urls = self.service.get_all_public_urls()
        
        # Check that the correct URLs were returned and deduplicated
        self.assertEqual(len(urls), 5)
        self.assertIn(URLInfo(url=''), urls)
        self.assertIn(URLInfo(url='about/'), urls)
        self.assertIn(URLInfo(url='contact/'), urls)
        self.assertIn(URLInfo(url='blog/post-1'), urls)
        self.assertIn(URLInfo(url='blog/post-2'), urls)


if __name__ == '__main__':
    from django.test import runner
    runner.main()