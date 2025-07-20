"""
Tests for the LLMs.txt Creator service.
"""
import os
import tempfile
from unittest import mock
from django.test import TestCase
from django.conf import settings

from site_files.services.llms_txt_creator import LLMsTxtCreator
from site_files.services.url_discovery import URLInfo


class LLMsTxtCreatorTests(TestCase):
    """
    Test cases for the LLMsTxtCreator class.
    """
    
    def setUp(self):
        """
        Set up the test environment.
        """
        self.site_url = "https://example.com"
        self.site_name = "Test Site"
        self.creator = LLMsTxtCreator(site_url=self.site_url, site_name=self.site_name)
        
        # Create a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()
        
    def tearDown(self):
        """
        Clean up the test environment.
        """
        # Remove the temporary file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    @mock.patch('site_files.services.url_discovery.URLDiscoveryService.get_all_public_urls')
    def test_generate_llms_txt_content(self, mock_get_all_public_urls):
        """
        Test generating the LLMs.txt content.
        """
        # Mock the URL discovery service
        mock_get_all_public_urls.return_value = [
            URLInfo(url="about/", title="About Us", type="page"),
            URLInfo(url="contact/", title="Contact", type="page"),
            URLInfo(url="blog/post-1/", title="First Post", type="blog"),
            URLInfo(url="blog/category/news/", title="News", type="blog_category"),
            URLInfo(url="api/v1/users/", title="Users API", type="api"),
        ]
        
        # Generate the content
        content = self.creator.generate_llms_txt_content()
        
        # Check that the content contains the expected sections
        self.assertIn("# LLMs.txt for Test Site", content)
        self.assertIn("## Site Structure", content)
        self.assertIn("## Acceptable AI Interactions", content)
        self.assertIn("## API Endpoints", content)
        self.assertIn("## Content Licensing and Usage Policies", content)
        
        # Check that the content contains the URLs
        self.assertIn("https://example.com/about/", content)
        self.assertIn("https://example.com/blog/", content)
        self.assertIn("Users API", content)
    
    @mock.patch('site_files.services.llms_txt_creator.LLMsTxtCreator.generate_llms_txt_content')
    def test_write_llms_txt(self, mock_generate_content):
        """
        Test writing the LLMs.txt file.
        """
        # Mock the content generation
        mock_generate_content.return_value = "# Test LLMs.txt Content"
        
        # Write the file
        result = self.creator.write_llms_txt(self.temp_file.name)
        
        # Check that the file was written successfully
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.temp_file.name))
        
        # Check the file content
        with open(self.temp_file.name, 'r') as f:
            content = f.read()
        self.assertEqual(content, "# Test LLMs.txt Content")
    
    @mock.patch('site_files.services.llms_txt_creator.LLMsTxtCreator.generate_llms_txt_content')
    def test_write_llms_txt_with_error(self, mock_generate_content):
        """
        Test writing the LLMs.txt file with an error.
        """
        # Mock the content generation to raise an exception
        mock_generate_content.side_effect = Exception("Test error")
        
        # Write the file
        result = self.creator.write_llms_txt(self.temp_file.name)
        
        # Check that the operation failed
        self.assertFalse(result)
    
    @mock.patch('os.path.exists')
    @mock.patch('shutil.copy2')
    def test_create_backup(self, mock_copy2, mock_exists):
        """
        Test creating a backup of the LLMs.txt file.
        """
        # Mock the file existence check
        mock_exists.return_value = True
        
        # Create a backup
        result = self.creator.create_backup(self.temp_file.name)
        
        # Check that the backup was created
        self.assertTrue(result)
        mock_copy2.assert_called_once()
    
    @mock.patch('os.path.exists')
    def test_create_backup_nonexistent_file(self, mock_exists):
        """
        Test creating a backup of a nonexistent file.
        """
        # Mock the file existence check
        mock_exists.return_value = False
        
        # Create a backup
        result = self.creator.create_backup(self.temp_file.name)
        
        # Check that the operation failed
        self.assertFalse(result)
    
    def test_group_urls_by_type(self):
        """
        Test grouping URLs by type.
        """
        # Create test URLs
        urls = [
            URLInfo(url="about/", type="page"),
            URLInfo(url="contact/", type="page"),
            URLInfo(url="blog/post-1/", type="blog"),
            URLInfo(url="blog/post-2/", type="blog"),
            URLInfo(url="api/v1/users/", type="api"),
        ]
        
        # Group the URLs
        groups = self.creator._group_urls_by_type(urls)
        
        # Check the groups
        self.assertEqual(len(groups), 3)
        self.assertEqual(len(groups["page"]), 2)
        self.assertEqual(len(groups["blog"]), 2)
        self.assertEqual(len(groups["api"]), 1)