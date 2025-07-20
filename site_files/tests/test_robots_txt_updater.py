"""
Tests for the RobotsTxtUpdater class.
"""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from site_files.services.robots_txt_updater import RobotsTxtUpdater


class TestRobotsTxtUpdater(unittest.TestCase):
    """Test cases for the RobotsTxtUpdater class."""

    def setUp(self):
        """Set up test environment."""
        self.site_url = "https://example.com"
        self.updater = RobotsTxtUpdater(self.site_url)
        
        # Create a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()
        
        # Sample robots.txt content
        self.sample_content = """
# robots.txt
User-agent: *
Allow: /

Disallow: /admin/
Disallow: /private/

Sitemap: https://old-domain.com/Sitemap.xml
"""
        
        # Write sample content to the temp file
        with open(self.temp_file.name, 'w') as f:
            f.write(self.sample_content)
            
    def tearDown(self):
        """Clean up after tests."""
        # Remove the temporary file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
            
        # Remove any backup files
        for filename in os.listdir(os.path.dirname(self.temp_file.name)):
            if filename.startswith(os.path.basename(self.temp_file.name)) and filename.endswith('.bak'):
                os.unlink(os.path.join(os.path.dirname(self.temp_file.name), filename))
                
    def test_parse_robots_txt(self):
        """Test parsing of robots.txt file."""
        content_lines, sitemap_url = self.updater.parse_robots_txt(self.temp_file.name)
        
        # Check that sitemap URL was extracted correctly
        self.assertEqual(sitemap_url, "https://old-domain.com/Sitemap.xml")
        
        # Check that content lines don't include the sitemap line
        self.assertFalse(any("Sitemap:" in line for line in content_lines))
        
        # Check that other content was preserved
        self.assertTrue(any("User-agent: *" in line for line in content_lines))
        self.assertTrue(any("Disallow: /admin/" in line for line in content_lines))
        
    def test_update_sitemap_url(self):
        """Test updating the sitemap URL."""
        content_lines = [
            "# robots.txt\n",
            "User-agent: *\n",
            "Allow: /\n",
            "\n",
            "Disallow: /admin/\n",
        ]
        
        updated_lines = self.updater.update_sitemap_url(content_lines, "/Sitemap.xml")
        
        # Check that sitemap URL was added
        self.assertTrue(any("Sitemap: https://example.com/Sitemap.xml" in line for line in updated_lines))
        
        # Check that other content was preserved
        self.assertTrue(any("User-agent: *" in line for line in updated_lines))
        self.assertTrue(any("Disallow: /admin/" in line for line in updated_lines))
        
    def test_generate_robots_txt(self):
        """Test generating the robots.txt content."""
        content = self.updater.generate_robots_txt(self.temp_file.name, "/Sitemap.xml")
        
        # Check that the new sitemap URL is in the content
        self.assertIn("Sitemap: https://example.com/Sitemap.xml", content)
        
        # Check that the old sitemap URL is not in the content
        self.assertNotIn("Sitemap: https://old-domain.com/Sitemap.xml", content)
        
        # Check that other content was preserved
        self.assertIn("User-agent: *", content)
        self.assertIn("Disallow: /admin/", content)
        
    def test_create_backup(self):
        """Test creating a backup of the robots.txt file."""
        with patch('site_files.services.robots_txt_updater.shutil.copy2') as mock_copy:
            result = self.updater.create_backup(self.temp_file.name)
            
            # Check that the backup was created
            self.assertTrue(result)
            mock_copy.assert_called_once()
            
    def test_write_robots_txt(self):
        """Test writing the updated robots.txt file."""
        with patch('site_files.services.robots_txt_updater.RobotsTxtUpdater.create_backup') as mock_backup:
            result = self.updater.write_robots_txt(self.temp_file.name, "/Sitemap.xml")
            
            # Check that the file was updated
            self.assertTrue(result)
            mock_backup.assert_called_once()
            
            # Read the updated file
            with open(self.temp_file.name, 'r') as f:
                content = f.read()
                
            # Check that the new sitemap URL is in the content
            self.assertIn("Sitemap: https://example.com/Sitemap.xml", content)
            
            # Check that the old sitemap URL is not in the content
            self.assertNotIn("Sitemap: https://old-domain.com/Sitemap.xml", content)
            
    def test_write_robots_txt_nonexistent_file(self):
        """Test writing to a nonexistent robots.txt file."""
        nonexistent_file = os.path.join(tempfile.gettempdir(), "nonexistent_robots.txt")
        
        # Make sure the file doesn't exist
        if os.path.exists(nonexistent_file):
            os.unlink(nonexistent_file)
            
        result = self.updater.write_robots_txt(nonexistent_file, "/Sitemap.xml")
        
        # Check that the file was created
        self.assertTrue(result)
        self.assertTrue(os.path.exists(nonexistent_file))
        
        # Read the created file
        with open(nonexistent_file, 'r') as f:
            content = f.read()
            
        # Check that the default content and sitemap URL are in the file
        self.assertIn("User-agent: *", content)
        self.assertIn("Sitemap: https://example.com/Sitemap.xml", content)
        
        # Clean up
        os.unlink(nonexistent_file)
        
    def test_write_robots_txt_error_handling(self):
        """Test error handling when writing the robots.txt file."""
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            result = self.updater.write_robots_txt(self.temp_file.name, "/Sitemap.xml")
            
            # Check that the method returned False due to the error
            self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()