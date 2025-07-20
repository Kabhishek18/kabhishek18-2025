"""
Tests for the dynamic content URL discovery functionality.
"""
from datetime import datetime
from unittest import mock
from django.test import TestCase
from site_files.services.url_discovery import URLDiscoveryService, URLInfo


class DynamicURLDiscoveryTestCase(TestCase):
    """Test case for the dynamic content URL discovery functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.service = URLDiscoveryService(site_url='https://example.com')
    
    @mock.patch('site_files.services.url_discovery.URLDiscoveryService._get_blog_post_urls')
    @mock.patch('site_files.services.url_discovery.URLDiscoveryService._get_blog_category_urls')
    @mock.patch('site_files.services.url_discovery.URLDiscoveryService._get_page_urls')
    def test_get_dynamic_content_urls(self, mock_get_page_urls, mock_get_category_urls, mock_get_post_urls):
        """Test getting all dynamic content URLs."""
        # Set up mock return values
        mock_get_post_urls.return_value = [
            URLInfo(url='blog/post-1/', type='blog'),
            URLInfo(url='blog/post-2/', type='blog'),
        ]
        mock_get_category_urls.return_value = [
            URLInfo(url='blog/category/tech/', type='blog_category'),
            URLInfo(url='blog/category/news/', type='blog_category'),
        ]
        mock_get_page_urls.return_value = [
            URLInfo(url='about/', type='page'),
            URLInfo(url='contact/', type='page'),
        ]
        
        # Call the method
        urls = self.service.get_dynamic_content_urls()
        
        # Check that all URLs were returned
        self.assertEqual(len(urls), 6)
        self.assertIn(URLInfo(url='blog/post-1/'), urls)
        self.assertIn(URLInfo(url='blog/post-2/'), urls)
        self.assertIn(URLInfo(url='blog/category/tech/'), urls)
        self.assertIn(URLInfo(url='blog/category/news/'), urls)
        self.assertIn(URLInfo(url='about/'), urls)
        self.assertIn(URLInfo(url='contact/'), urls)
        
        # Check that the methods were called
        mock_get_post_urls.assert_called_once()
        mock_get_category_urls.assert_called_once()
        mock_get_page_urls.assert_called_once()
    
    @mock.patch('blog.models.Post.objects.filter')
    def test_get_blog_post_urls(self, mock_filter):
        """Test getting blog post URLs."""
        # Create mock posts
        mock_post1 = mock.MagicMock()
        mock_post1.slug = 'post-1'
        mock_post1.updated_at = datetime(2023, 1, 1)
        mock_post1.title = 'Post 1'
        
        mock_post2 = mock.MagicMock()
        mock_post2.slug = 'post-2'
        mock_post2.updated_at = datetime(2023, 1, 2)
        mock_post2.title = 'Post 2'
        
        # Set up mock return value
        mock_filter.return_value = [mock_post1, mock_post2]
        
        # Call the method
        urls = self.service._get_blog_post_urls()
        
        # Check that the correct URLs were returned
        self.assertEqual(len(urls), 2)
        self.assertEqual(urls[0].url, 'blog/post-1/')
        self.assertEqual(urls[0].lastmod, datetime(2023, 1, 1))
        self.assertEqual(urls[0].title, 'Post 1')
        self.assertEqual(urls[0].type, 'blog')
        self.assertEqual(urls[0].changefreq, 'weekly')
        self.assertEqual(urls[0].priority, 0.7)
        
        self.assertEqual(urls[1].url, 'blog/post-2/')
        self.assertEqual(urls[1].lastmod, datetime(2023, 1, 2))
        self.assertEqual(urls[1].title, 'Post 2')
        
        # Check that the filter was called with the correct arguments
        mock_filter.assert_called_once_with(status='published')
    
    @mock.patch('blog.models.Category.objects.all')
    def test_get_blog_category_urls(self, mock_all):
        """Test getting blog category URLs."""
        # Create mock categories
        mock_category1 = mock.MagicMock()
        mock_category1.slug = 'tech'
        mock_category1.name = 'Technology'
        
        mock_category2 = mock.MagicMock()
        mock_category2.slug = 'news'
        mock_category2.name = 'News'
        
        # Set up mock return value
        mock_all.return_value = [mock_category1, mock_category2]
        
        # Call the method
        urls = self.service._get_blog_category_urls()
        
        # Check that the correct URLs were returned
        self.assertEqual(len(urls), 2)
        self.assertEqual(urls[0].url, 'blog/category/tech/')
        self.assertEqual(urls[0].title, 'Technology')
        self.assertEqual(urls[0].type, 'blog_category')
        self.assertEqual(urls[0].changefreq, 'monthly')
        self.assertEqual(urls[0].priority, 0.6)
        
        self.assertEqual(urls[1].url, 'blog/category/news/')
        self.assertEqual(urls[1].title, 'News')
        
        # Check that the all method was called
        mock_all.assert_called_once()
    
    @mock.patch('core.models.Page.objects.filter')
    def test_get_page_urls(self, mock_filter):
        """Test getting page URLs."""
        # Create mock pages
        mock_page1 = mock.MagicMock()
        mock_page1.slug = 'about'
        mock_page1.updated_at = datetime(2023, 1, 1)
        mock_page1.title = 'About Us'
        mock_page1.is_homepage = False
        
        mock_page2 = mock.MagicMock()
        mock_page2.slug = 'contact'
        mock_page2.updated_at = datetime(2023, 1, 2)
        mock_page2.title = 'Contact Us'
        mock_page2.is_homepage = False
        
        mock_homepage = mock.MagicMock()
        mock_homepage.slug = 'home'
        mock_homepage.updated_at = datetime(2023, 1, 3)
        mock_homepage.title = 'Home'
        mock_homepage.is_homepage = True
        
        # Set up mock return value
        mock_filter.return_value = [mock_page1, mock_page2, mock_homepage]
        
        # Call the method
        urls = self.service._get_page_urls()
        
        # Check that the correct URLs were returned
        self.assertEqual(len(urls), 2)
        self.assertEqual(urls[0].url, 'about/')
        self.assertEqual(urls[0].lastmod, datetime(2023, 1, 1))
        self.assertEqual(urls[0].title, 'About Us')
        self.assertEqual(urls[0].type, 'page')
        self.assertEqual(urls[0].changefreq, 'monthly')
        self.assertEqual(urls[0].priority, 0.8)
        
        self.assertEqual(urls[1].url, 'contact/')
        self.assertEqual(urls[1].lastmod, datetime(2023, 1, 2))
        self.assertEqual(urls[1].title, 'Contact Us')
        
        # Check that the homepage was not included
        self.assertNotIn(URLInfo(url='home/'), urls)
        
        # Check that the filter was called with the correct arguments
        mock_filter.assert_called_once_with(is_published=True)


if __name__ == '__main__':
    from django.test import runner
    runner.main()