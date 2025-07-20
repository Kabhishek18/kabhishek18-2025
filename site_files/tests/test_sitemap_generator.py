"""
Tests for the Sitemap Generator Service.
"""
import os
import shutil
import tempfile
from datetime import datetime
from unittest import mock
from django.test import TestCase
from site_files.services.url_discovery import URLInfo
from site_files.services.sitemap_generator import SitemapGenerator


class SitemapGeneratorTestCase(TestCase):
    """Test case for the SitemapGenerator."""
    
    def setUp(self):
        """Set up test data."""
        self.site_url = 'https://example.com'
        
        # Create a mock URL discovery service
        self.url_discovery_service = mock.Mock()
        
        # Create a temporary directory for testing file operations
        self.temp_dir = tempfile.mkdtemp()
        self.sitemap_path = os.path.join(self.temp_dir, 'Sitemap.xml')
        self.backup_dir = os.path.join(self.temp_dir, 'backups')
        
        # Create the sitemap generator with the mock service
        self.generator = SitemapGenerator(
            url_discovery_service=self.url_discovery_service,
            site_url=self.site_url
        )
        
        # Override the default paths for testing
        self.generator.default_sitemap_path = self.sitemap_path
        self.generator.backup_dir = self.backup_dir
        
        # Sample URLs for testing
        self.test_urls = [
            URLInfo(
                url='',
                lastmod=datetime(2023, 1, 1),
                changefreq='monthly',
                priority=1.0,
                title='Home',
                type='page'
            ),
            URLInfo(
                url='about/',
                lastmod=datetime(2023, 1, 2),
                changefreq='monthly',
                priority=0.8,
                title='About Us',
                type='page'
            ),
            URLInfo(
                url='blog/post-1/',
                lastmod=datetime(2023, 1, 3),
                changefreq='weekly',
                priority=0.7,
                title='Test Post 1',
                type='blog'
            ),
            URLInfo(
                url='blog/post-2/',
                lastmod=datetime(2023, 1, 4),
                changefreq='weekly',
                priority=0.7,
                title='Test Post 2',
                type='blog'
            ),
            URLInfo(
                url='contact/',
                lastmod=datetime(2023, 1, 5),
                changefreq='monthly',
                priority=0.8,
                title='Contact Us',
                type='page'
            ),
        ]
    
    def test_generate_sitemap(self):
        """Test generating a sitemap."""
        # Configure the mock to return our test URLs
        self.url_discovery_service.get_all_public_urls.return_value = self.test_urls
        
        # Generate the sitemap
        sitemap_xml = self.generator.generate_sitemap()
        
        # Check that the XML is well-formed
        self.assertTrue(sitemap_xml.startswith('<?xml'))
        self.assertIn('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">', sitemap_xml)
        self.assertIn('</urlset>', sitemap_xml)
        
        # Check that all URLs are included
        for url_info in self.test_urls:
            absolute_url = url_info.get_absolute_url(self.site_url)
            self.assertIn(f'<loc>{absolute_url}</loc>', sitemap_xml)
            
            # Check that lastmod is included
            if url_info.lastmod:
                self.assertIn(f'<lastmod>{url_info.lastmod.strftime("%Y-%m-%d")}</lastmod>', sitemap_xml)
            
            # Check that changefreq is included
            self.assertIn(f'<changefreq>{url_info.changefreq}</changefreq>', sitemap_xml)
            
            # Check that priority is included
            self.assertIn(f'<priority>{url_info.priority}</priority>', sitemap_xml)
        
        # Verify that the URL discovery service was called
        self.url_discovery_service.get_all_public_urls.assert_called_once()
    
    def test_generate_sitemap_with_special_characters(self):
        """Test generating a sitemap with URLs containing special characters."""
        # Create a URL with special characters
        url_with_special_chars = URLInfo(
            url='search?q=test&category=blog',
            lastmod=datetime(2023, 1, 6),
            changefreq='daily',
            priority=0.6,
            title='Search Results',
            type='search'
        )
        
        # Configure the mock to return our test URL
        self.url_discovery_service.get_all_public_urls.return_value = [url_with_special_chars]
        
        # Generate the sitemap
        sitemap_xml = self.generator.generate_sitemap()
        
        # Check that special characters are properly escaped
        self.assertIn('<loc>https://example.com/search?q=test&amp;category=blog</loc>', sitemap_xml)
    
    def test_generate_sitemap_error_handling(self):
        """Test error handling during sitemap generation."""
        # Configure the mock to raise an exception
        self.url_discovery_service.get_all_public_urls.side_effect = Exception("Test error")
        
        # Check that the exception is propagated
        with self.assertRaises(Exception):
            self.generator.generate_sitemap()
    
    def test_generate_xml_content(self):
        """Test the internal _generate_xml_content method."""
        # Call the method directly
        xml_content = self.generator._generate_xml_content(self.test_urls)
        
        # Check that the XML is well-formed
        self.assertTrue(xml_content.startswith('<?xml'))
        self.assertIn('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">', xml_content)
        self.assertIn('</urlset>', xml_content)
        
        # Check that all URLs are included
        for url_info in self.test_urls:
            absolute_url = url_info.get_absolute_url(self.site_url)
            self.assertIn(f'<loc>{absolute_url}</loc>', xml_content)
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.temp_dir)
    
    def test_write_sitemap(self):
        """Test writing the sitemap to a file."""
        # Generate some XML content
        self.url_discovery_service.get_all_public_urls.return_value = self.test_urls
        sitemap_xml = self.generator.generate_sitemap()
        
        # Write the sitemap to a file
        result = self.generator.write_sitemap(sitemap_xml)
        
        # Check that the operation was successful
        self.assertTrue(result)
        
        # Check that the file was created
        self.assertTrue(os.path.exists(self.sitemap_path))
        
        # Check the content of the file
        with open(self.sitemap_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, sitemap_xml)
    
    def test_write_sitemap_with_custom_path(self):
        """Test writing the sitemap to a custom path."""
        # Generate some XML content
        self.url_discovery_service.get_all_public_urls.return_value = self.test_urls
        sitemap_xml = self.generator.generate_sitemap()
        
        # Define a custom path
        custom_path = os.path.join(self.temp_dir, 'custom', 'Sitemap.xml')
        
        # Write the sitemap to the custom path
        result = self.generator.write_sitemap(sitemap_xml, custom_path)
        
        # Check that the operation was successful
        self.assertTrue(result)
        
        # Check that the file was created
        self.assertTrue(os.path.exists(custom_path))
        
        # Check that the directory was created
        self.assertTrue(os.path.exists(os.path.dirname(custom_path)))
        
        # Check the content of the file
        with open(custom_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, sitemap_xml)
    
    def test_create_backup(self):
        """Test creating a backup of an existing sitemap file."""
        # Create a sitemap file
        os.makedirs(os.path.dirname(self.sitemap_path), exist_ok=True)
        with open(self.sitemap_path, 'w', encoding='utf-8') as f:
            f.write('<test>content</test>')
        
        # Create a backup
        backup_path = self.generator._create_backup(self.sitemap_path)
        
        # Check that the backup was created
        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))
        
        # Check that the backup directory was created
        self.assertTrue(os.path.exists(self.backup_dir))
        
        # Check the content of the backup file
        with open(backup_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, '<test>content</test>')
    
    def test_restore_backup(self):
        """Test restoring a backup of a sitemap file."""
        # Create a sitemap file
        os.makedirs(os.path.dirname(self.sitemap_path), exist_ok=True)
        with open(self.sitemap_path, 'w', encoding='utf-8') as f:
            f.write('<test>original</test>')
        
        # Create a backup
        backup_path = self.generator._create_backup(self.sitemap_path)
        
        # Modify the original file
        with open(self.sitemap_path, 'w', encoding='utf-8') as f:
            f.write('<test>modified</test>')
        
        # Restore the backup
        result = self.generator._restore_backup(self.sitemap_path)
        
        # Check that the operation was successful
        self.assertTrue(result)
        
        # Check the content of the restored file
        with open(self.sitemap_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, '<test>original</test>')
    
    def test_restore_backup_no_backup(self):
        """Test restoring a backup when no backup exists."""
        # Create a sitemap file
        os.makedirs(os.path.dirname(self.sitemap_path), exist_ok=True)
        with open(self.sitemap_path, 'w', encoding='utf-8') as f:
            f.write('<test>content</test>')
        
        # Try to restore a backup (none exists)
        result = self.generator._restore_backup(self.sitemap_path)
        
        # Check that the operation failed
        self.assertFalse(result)
        
        # Check that the original file is unchanged
        with open(self.sitemap_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, '<test>content</test>')
    
    def test_write_sitemap_error_handling(self):
        """Test error handling when writing the sitemap."""
        # Generate some XML content
        self.url_discovery_service.get_all_public_urls.return_value = self.test_urls
        sitemap_xml = self.generator.generate_sitemap()
        
        # Mock open to raise an exception
        with mock.patch('builtins.open', side_effect=PermissionError("Permission denied")):
            # Try to write the sitemap
            result = self.generator.write_sitemap(sitemap_xml)
            
            # Check that the operation failed
            self.assertFalse(result)
    
    def test_update_sitemap(self):
        """Test the update_sitemap method."""
        # Configure the mock to return our test URLs
        self.url_discovery_service.get_all_public_urls.return_value = self.test_urls
        
        # Update the sitemap
        result = self.generator.update_sitemap()
        
        # Check that the operation was successful
        self.assertTrue(result)
        
        # Check that the file was created
        self.assertTrue(os.path.exists(self.sitemap_path))
        
        # Check that the file contains the expected content
        with open(self.sitemap_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertTrue(content.startswith('<?xml'))
            self.assertIn('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">', content)
            
            # Check that all URLs are included
            for url_info in self.test_urls:
                absolute_url = url_info.get_absolute_url(self.site_url)
                self.assertIn(f'<loc>{absolute_url}</loc>', content)
    
    def test_update_sitemap_error_handling(self):
        """Test error handling in the update_sitemap method."""
        # Configure the mock to raise an exception
        self.url_discovery_service.get_all_public_urls.side_effect = Exception("Test error")
        
        # Try to update the sitemap
        result = self.generator.update_sitemap()
        
        # Check that the operation failed
        self.assertFalse(result)


if __name__ == '__main__':
    from django.test import runner
    runner.main()