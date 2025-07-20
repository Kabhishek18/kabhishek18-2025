"""
File validation tests for the Site Files Updater.

These tests validate the generated files against their respective formats:
- Sitemap.xml against XML schema
- robots.txt format
- security.txt format
"""
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from unittest import mock
from django.test import TestCase
from django.utils import timezone
from site_files.models import SiteFilesConfig
from site_files.services.sitemap_generator import SitemapGenerator
from site_files.services.robots_txt_updater import RobotsTxtUpdater
from site_files.services.security_txt_updater import SecurityTxtUpdater
from site_files.services.url_discovery import URLInfo


class FileValidationTestCase(TestCase):
    """Test case for validating the format of generated files."""
    
    def setUp(self):
        """Set up test data."""
        # Create a temporary directory for testing file operations
        self.temp_dir = tempfile.mkdtemp()
        
        # Define file paths
        self.sitemap_path = os.path.join(self.temp_dir, 'Sitemap.xml')
        self.robots_path = os.path.join(self.temp_dir, 'robots.txt')
        self.security_path = os.path.join(self.temp_dir, 'security.txt')
        
        # Site URL for testing
        self.site_url = 'https://example.com'
        
        # Get or create configuration
        self.config, created = SiteFilesConfig.objects.get_or_create(
            defaults={
                'site_name': 'Test Site',
                'site_url': self.site_url,
                'update_frequency': 'daily',
                'last_update': timezone.now()
            }
        )
        
        # Update the paths for this test
        self.config.sitemap_path = self.sitemap_path
        self.config.robots_path = self.robots_path
        self.config.security_path = self.security_path
        self.config.save()
        
        # Sample URLs for testing
        self.test_urls = [
            URLInfo(
                url='',
                lastmod=timezone.now(),
                changefreq='monthly',
                priority=1.0,
                title='Home',
                type='page'
            ),
            URLInfo(
                url='about/',
                lastmod=timezone.now(),
                changefreq='monthly',
                priority=0.8,
                title='About Us',
                type='page'
            ),
            URLInfo(
                url='blog/post-1/',
                lastmod=timezone.now(),
                changefreq='weekly',
                priority=0.7,
                title='Test Post 1',
                type='blog'
            ),
        ]
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.temp_dir)
    
    def test_sitemap_xml_schema_validation(self):
        """Test that the generated sitemap conforms to the XML schema."""
        # Create a mock URL discovery service
        url_discovery_service = mock.Mock()
        url_discovery_service.get_all_public_urls.return_value = self.test_urls
        
        # Create the sitemap generator
        generator = SitemapGenerator(
            url_discovery_service=url_discovery_service,
            site_url=self.site_url
        )
        
        # Generate and write the sitemap
        sitemap_xml = generator.generate_sitemap()
        generator.write_sitemap(sitemap_xml, self.sitemap_path)
        
        # Validate the XML structure
        try:
            # Parse the XML
            tree = ET.parse(self.sitemap_path)
            root = tree.getroot()
            
            # Check the root element
            self.assertEqual(root.tag, '{http://www.sitemaps.org/schemas/sitemap/0.9}urlset')
            
            # Check that there are URL elements
            urls = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url')
            self.assertEqual(len(urls), len(self.test_urls))
            
            # Check each URL element
            for url_element in urls:
                # Check that it has the required elements
                loc = url_element.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                self.assertIsNotNone(loc)
                self.assertTrue(loc.text.startswith(self.site_url))
                
                # Check optional elements
                lastmod = url_element.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
                if lastmod is not None:
                    # Validate the date format (YYYY-MM-DD)
                    self.assertRegex(lastmod.text, r'^\d{4}-\d{2}-\d{2}$')
                
                changefreq = url_element.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}changefreq')
                if changefreq is not None:
                    # Validate the changefreq value
                    self.assertIn(changefreq.text, ['always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never'])
                
                priority = url_element.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}priority')
                if priority is not None:
                    # Validate the priority value (0.0 to 1.0)
                    priority_value = float(priority.text)
                    self.assertGreaterEqual(priority_value, 0.0)
                    self.assertLessEqual(priority_value, 1.0)
            
        except ET.ParseError as e:
            self.fail(f"Sitemap XML is not well-formed: {e}")
    
    def test_robots_txt_format_validation(self):
        """Test that the generated robots.txt conforms to the expected format."""
        # Create initial robots.txt
        with open(self.robots_path, 'w', encoding='utf-8') as f:
            f.write("User-agent: *\nDisallow: /admin/\n")
        
        # Create the robots.txt updater
        updater = RobotsTxtUpdater(site_url=self.site_url)
        
        # Update the robots.txt
        updater.write_robots_txt(self.robots_path, self.sitemap_path)
        
        # Read the updated robots.txt
        with open(self.robots_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into lines for validation
        lines = content.strip().split('\n')
        
        # Validate the format
        user_agent_found = False
        disallow_found = False
        sitemap_found = False
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Check User-agent directive
            if line.startswith('User-agent:'):
                user_agent_found = True
                # Validate the format
                parts = line.split(':', 1)
                self.assertEqual(len(parts), 2)
                self.assertTrue(parts[1].strip())  # Value should not be empty
            
            # Check Disallow directive
            elif line.startswith('Disallow:'):
                disallow_found = True
                # Validate the format
                parts = line.split(':', 1)
                self.assertEqual(len(parts), 2)
                # Value can be empty (allow all) or a path
            
            # Check Sitemap directive
            elif line.startswith('Sitemap:'):
                sitemap_found = True
                # Validate the format
                parts = line.split(':', 1)
                self.assertEqual(len(parts), 2)
                sitemap_url = parts[1].strip()
                self.assertTrue(sitemap_url)  # Value should not be empty
                self.assertTrue(sitemap_url.startswith('http'))  # Should be an absolute URL
                self.assertTrue(sitemap_url.endswith('.xml'))  # Should end with .xml
            
            # Unknown directive
            else:
                # Check if it's a valid directive
                valid_directives = ['Allow:', 'Crawl-delay:', 'Host:', 'Clean-param:']
                is_valid = any(line.startswith(directive) for directive in valid_directives)
                self.assertTrue(is_valid, f"Unknown directive in robots.txt: {line}")
        
        # Check that required directives are present
        self.assertTrue(user_agent_found, "User-agent directive not found in robots.txt")
        self.assertTrue(sitemap_found, "Sitemap directive not found in robots.txt")
    
    def test_security_txt_format_validation(self):
        """Test that the generated security.txt conforms to the expected format."""
        # Create initial security.txt
        with open(self.security_path, 'w', encoding='utf-8') as f:
            f.write("Contact: security@example.com\nExpires: 2023-12-31T23:59:59Z\n")
        
        # Create the security.txt updater
        updater = SecurityTxtUpdater(site_url=self.site_url)
        
        # Update the security.txt
        updater.update_security_txt(self.security_path)
        
        # Read the updated security.txt
        with open(self.security_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into lines for validation
        lines = content.strip().split('\n')
        
        # Validate the format
        contact_found = False
        expires_found = False
        canonical_found = False
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Check Contact directive
            if line.startswith('Contact:'):
                contact_found = True
                # Validate the format
                parts = line.split(':', 1)
                self.assertEqual(len(parts), 2)
                contact_value = parts[1].strip()
                self.assertTrue(contact_value)  # Value should not be empty
                # Should be an email or URL
                self.assertTrue('@' in contact_value or contact_value.startswith('http'))
            
            # Check Expires directive
            elif line.startswith('Expires:'):
                expires_found = True
                # Validate the format
                parts = line.split(':', 1)
                self.assertEqual(len(parts), 2)
                expires_value = parts[1].strip()
                self.assertTrue(expires_value)  # Value should not be empty
                # Should be in ISO 8601 format
                self.assertRegex(expires_value, r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
            
            # Check Canonical directive
            elif line.startswith('Canonical:'):
                canonical_found = True
                # Validate the format
                parts = line.split(':', 1)
                self.assertEqual(len(parts), 2)
                canonical_value = parts[1].strip()
                self.assertTrue(canonical_value)  # Value should not be empty
                self.assertTrue(canonical_value.startswith('http'))  # Should be an absolute URL
                self.assertTrue('/.well-known/security.txt' in canonical_value)  # Should point to the well-known location
            
            # Other valid directives
            elif any(line.startswith(directive) for directive in ['Acknowledgments:', 'Encryption:', 'Hiring:', 'Policy:', 'Preferred-Languages:']):
                # These are valid directives, no additional validation needed
                pass
            
            # Unknown directive
            else:
                self.fail(f"Unknown directive in security.txt: {line}")
        
        # Check that required directives are present
        self.assertTrue(contact_found, "Contact directive not found in security.txt")
        self.assertTrue(canonical_found, "Canonical directive not found in security.txt")
        # Expires is recommended but not required by the spec


if __name__ == '__main__':
    from django.test import runner
    runner.main()