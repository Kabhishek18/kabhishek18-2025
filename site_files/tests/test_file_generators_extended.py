"""
Extended tests for the file generator services.
"""
import os
import tempfile
import shutil
from unittest import mock
from datetime import datetime
from django.test import TestCase, override_settings
from django.conf import settings

from site_files.services.url_discovery import URLInfo
from site_files.services.sitemap_generator import SitemapGenerator
from site_files.services.robots_txt_updater import RobotsTxtUpdater
from site_files.services.security_txt_updater import SecurityTxtUpdater
from site_files.services.llms_txt_creator import LLMsTxtCreator


class ExtendedSitemapGeneratorTests(TestCase):
    """Extended tests for the SitemapGenerator class."""
    
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
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.temp_dir)
    
    def test_generate_xml_content_with_malformed_urls(self):
        """Test generating XML content with URLs that could cause malformed XML."""
        # Create URLs with characters that need to be escaped in XML
        urls = [
            URLInfo(url='search?q=test&category=blog', title='Search Results'),
            URLInfo(url='product/<product_id>', title='Product Details'),
            URLInfo(url='blog/post-with-"quotes"', title='Post with Quotes'),
            URLInfo(url='page-with-<html>-tags', title='HTML Tags'),
        ]
        
        # Generate the XML content
        xml_content = self.generator._generate_xml_content(urls)
        
        # Check that the XML is well-formed
        self.assertTrue(xml_content.startswith('<?xml'))
        self.assertIn('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">', xml_content)
        self.assertIn('</urlset>', xml_content)
        
        # Check that special characters are properly escaped
        self.assertIn('search?q=test&amp;category=blog', xml_content)
        self.assertIn('product/&lt;product_id&gt;', xml_content)
        self.assertIn('blog/post-with-&quot;quotes&quot;', xml_content)
        self.assertIn('page-with-&lt;html&gt;-tags', xml_content)
    
    @mock.patch('xml.dom.minidom.parseString')
    def test_generate_xml_content_with_pretty_print_error(self, mock_parse_string):
        """Test error handling when pretty-printing XML fails."""
        # Configure the mock to raise an exception
        mock_parse_string.side_effect = Exception("XML parsing error")
        
        # Create some test URLs
        urls = [
            URLInfo(url='about/', title='About Us'),
            URLInfo(url='contact/', title='Contact Us'),
        ]
        
        # Generate the XML content
        xml_content = self.generator._generate_xml_content(urls)
        
        # Check that the raw XML is returned
        self.assertTrue(xml_content.startswith('<?xml'))
        self.assertIn('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">', xml_content)
        self.assertIn('<loc>https://example.com/about/</loc>', xml_content)
        self.assertIn('<loc>https://example.com/contact/</loc>', xml_content)
        self.assertIn('</urlset>', xml_content)
    
    @override_settings(SITEMAP_PATH='custom/path/Sitemap.xml')
    def test_default_sitemap_path_from_settings(self):
        """Test that the default sitemap path is taken from settings."""
        # Create a new generator to pick up the settings
        generator = SitemapGenerator(site_url=self.site_url)
        
        # Check that the default path is from settings
        self.assertEqual(generator.default_sitemap_path, 'custom/path/Sitemap.xml')
    
    @override_settings(SITEMAP_BACKUP_DIR='custom/backups')
    def test_backup_dir_from_settings(self):
        """Test that the backup directory is taken from settings."""
        # Create a new generator to pick up the settings
        generator = SitemapGenerator(site_url=self.site_url)
        
        # Check that the backup directory is from settings
        self.assertEqual(generator.backup_dir, 'custom/backups')


class ExtendedRobotsTxtUpdaterTests(TestCase):
    """Extended tests for the RobotsTxtUpdater class."""
    
    def setUp(self):
        """Set up test environment."""
        self.site_url = "https://example.com"
        self.updater = RobotsTxtUpdater(self.site_url)
        
        # Create a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove the temporary file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_update_sitemap_url_with_absolute_url(self):
        """Test updating the sitemap URL with an absolute URL."""
        content_lines = [
            "# robots.txt\n",
            "User-agent: *\n",
            "Allow: /\n",
        ]
        
        # Update with an absolute URL
        updated_lines = self.updater.update_sitemap_url(content_lines, "https://other-domain.com/Sitemap.xml")
        
        # Check that the absolute URL is preserved
        self.assertTrue(any("Sitemap: https://other-domain.com/Sitemap.xml" in line for line in updated_lines))
    
    def test_update_sitemap_url_with_no_trailing_newline(self):
        """Test updating the sitemap URL when the content doesn't end with a newline."""
        content_lines = [
            "# robots.txt\n",
            "User-agent: *\n",
            "Allow: /"  # No trailing newline
        ]
        
        updated_lines = self.updater.update_sitemap_url(content_lines, "/Sitemap.xml")
        
        # Check that a newline was added before the sitemap URL
        self.assertEqual(updated_lines[-2], "Allow: /\n")
        self.assertEqual(updated_lines[-1], "Sitemap: https://example.com/Sitemap.xml\n")
    
    def test_parse_robots_txt_with_multiple_sitemaps(self):
        """Test parsing a robots.txt file with multiple sitemap directives."""
        # Create a robots.txt file with multiple sitemaps
        with open(self.temp_file.name, 'w') as f:
            f.write("""
# robots.txt
User-agent: *
Allow: /

Sitemap: https://example.com/sitemap1.xml
Sitemap: https://example.com/sitemap2.xml
""")
        
        content_lines, sitemap_url = self.updater.parse_robots_txt(self.temp_file.name)
        
        # Check that the last sitemap URL was extracted
        self.assertEqual(sitemap_url, "https://example.com/sitemap2.xml")
        
        # Check that no sitemap lines are in the content
        self.assertFalse(any("Sitemap:" in line for line in content_lines))
    
    def test_parse_robots_txt_with_case_insensitive_sitemap(self):
        """Test parsing a robots.txt file with case-insensitive sitemap directive."""
        # Create a robots.txt file with a case-insensitive sitemap directive
        with open(self.temp_file.name, 'w') as f:
            f.write("""
# robots.txt
User-agent: *
Allow: /

sitemap: https://example.com/Sitemap.xml
""")
        
        content_lines, sitemap_url = self.updater.parse_robots_txt(self.temp_file.name)
        
        # Check that the sitemap URL was extracted despite the case
        self.assertEqual(sitemap_url, "https://example.com/Sitemap.xml")
        
        # Check that no sitemap lines are in the content
        self.assertFalse(any("sitemap:" in line for line in content_lines))


class ExtendedSecurityTxtUpdaterTests(TestCase):
    """Extended tests for the SecurityTxtUpdater class."""
    
    def setUp(self):
        """Set up test environment."""
        self.site_url = "https://example.com"
        self.updater = SecurityTxtUpdater(self.site_url)
    
    def test_parse_security_txt_with_malformed_content(self):
        """Test parsing malformed security.txt content."""
        malformed_content = """
# This is a malformed security.txt file
Contact: mailto:security@example.com
This line has no directive
Canonical: https://example.com/.well-known/security.txt
"""
        
        directives = self.updater.parse_security_txt(malformed_content)
        
        # Check that valid directives were parsed
        self.assertEqual(len(directives), 2)
        self.assertEqual(directives[0][0], "Contact")
        self.assertEqual(directives[0][1], "mailto:security@example.com")
        self.assertEqual(directives[1][0], "Canonical")
        self.assertEqual(directives[1][1], "https://example.com/.well-known/security.txt")
    
    def test_format_security_txt_with_empty_directives(self):
        """Test formatting security.txt with empty directives."""
        formatted_content = self.updater.format_security_txt([])
        
        # Check that a header was added
        self.assertIn("security.txt for example.com", formatted_content)
        self.assertIn("https://securitytxt.org/", formatted_content)
    
    def test_update_security_txt_with_empty_file(self):
        """Test updating an empty security.txt file."""
        # Mock the necessary methods
        with mock.patch.object(self.updater, 'read_security_txt', return_value=""), \
             mock.patch.object(self.updater, 'write_security_txt', return_value=True), \
             mock.patch('os.path.exists', return_value=True):
            result = self.updater.update_security_txt("/mock/path")
            self.assertTrue(result)
    
    def test_update_canonical_url_case_insensitive(self):
        """Test updating the canonical URL with case-insensitive matching."""
        # Create directives with a lowercase canonical directive
        directives = [
            ("Contact", "mailto:security@example.com", "# Contact info"),
            ("canonical", "https://old-domain.com/.well-known/security.txt", "# Canonical URL"),
        ]
        
        updated_directives = self.updater.update_canonical_url(directives)
        
        # Check that the canonical URL was updated despite the case
        self.assertEqual(updated_directives[1][0], "canonical")  # Case preserved
        self.assertEqual(updated_directives[1][1], "https://example.com/.well-known/security.txt")


class ExtendedLLMsTxtCreatorTests(TestCase):
    """Extended tests for the LLMsTxtCreator class."""
    
    def setUp(self):
        """Set up the test environment."""
        self.site_url = "https://example.com"
        self.site_name = "Test Site"
        self.creator = LLMsTxtCreator(site_url=self.site_url, site_name=self.site_name)
        
        # Create a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()
    
    def tearDown(self):
        """Clean up the test environment."""
        # Remove the temporary file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    @mock.patch('site_files.services.url_discovery.URLDiscoveryService.get_all_public_urls')
    def test_generate_llms_txt_content_with_no_urls(self, mock_get_all_public_urls):
        """Test generating LLMs.txt content with no URLs."""
        # Mock the URL discovery service to return no URLs
        mock_get_all_public_urls.return_value = []
        
        # Generate the content
        content = self.creator.generate_llms_txt_content()
        
        # Check that the content still contains the expected sections
        self.assertIn("# LLMs.txt for Test Site", content)
        self.assertIn("## Site Structure", content)
        self.assertIn("## Acceptable AI Interactions", content)
        self.assertIn("## API Endpoints", content)
        self.assertIn("## Content Licensing and Usage Policies", content)
    
    @mock.patch('site_files.services.url_discovery.URLDiscoveryService.get_all_public_urls')
    def test_generate_llms_txt_content_with_only_api_urls(self, mock_get_all_public_urls):
        """Test generating LLMs.txt content with only API URLs."""
        # Mock the URL discovery service to return only API URLs
        mock_get_all_public_urls.return_value = [
            URLInfo(url="api/v1/users/", title="Users API", type="api"),
            URLInfo(url="api/v1/posts/", title="Posts API", type="api"),
        ]
        
        # Generate the content
        content = self.creator.generate_llms_txt_content()
        
        # Check that the API endpoints section contains the URLs
        self.assertIn("## API Endpoints", content)
        self.assertIn("Users API", content)
        self.assertIn("Posts API", content)
    
    @mock.patch('site_files.services.url_discovery.URLDiscoveryService.get_all_public_urls')
    def test_generate_llms_txt_content_with_custom_site_name(self, mock_get_all_public_urls):
        """Test generating LLMs.txt content with a custom site name."""
        # Mock the URL discovery service
        mock_get_all_public_urls.return_value = [
            URLInfo(url="about/", title="About Us", type="page"),
        ]
        
        # Create a creator with a custom site name
        creator = LLMsTxtCreator(site_url=self.site_url, site_name="Custom Site Name")
        
        # Generate the content
        content = creator.generate_llms_txt_content()
        
        # Check that the content contains the custom site name
        self.assertIn("# LLMs.txt for Custom Site Name", content)
    
    @mock.patch('django.urls.reverse')
    @mock.patch('site_files.services.url_discovery.URLDiscoveryService.get_all_public_urls')
    def test_generate_api_endpoints_section_with_api_docs(self, mock_get_all_public_urls, mock_reverse):
        """Test generating the API endpoints section with API docs."""
        # Mock the URL discovery service to return no API URLs
        mock_get_all_public_urls.return_value = []
        
        # Mock the reverse function to not raise an exception
        mock_reverse.return_value = "/api/docs/"
        
        # Generate the content
        content = self.creator.generate_llms_txt_content()
        
        # Check that the API endpoints section mentions the API docs
        self.assertIn("API documentation is available at: https://example.com/api/docs/", content)
    
    @mock.patch('os.makedirs')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    def test_write_llms_txt_with_directory_creation(self, mock_open, mock_makedirs):
        """Test writing LLMs.txt with directory creation."""
        # Mock the content generation
        with mock.patch.object(self.creator, 'generate_llms_txt_content', return_value="Test content"):
            # Write to a path that requires directory creation
            result = self.creator.write_llms_txt("/nonexistent/dir/llms.txt")
            
            # Check that the directory was created
            mock_makedirs.assert_called_once_with(os.path.dirname("/nonexistent/dir/llms.txt"), exist_ok=True)
            
            # Check that the file was written
            mock_open.assert_called_once_with("/nonexistent/dir/llms.txt", 'w')
            mock_open().write.assert_called_once_with("Test content")
            
            # Check that the operation was successful
            self.assertTrue(result)
</text>
</invoke>