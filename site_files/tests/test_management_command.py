"""
Tests for the update_site_files management command.
"""
import os
from io import StringIO
from unittest import mock
from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from site_files.models import SiteFilesConfig


class UpdateSiteFilesCommandTests(TestCase):
    """Test cases for the update_site_files management command."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a test configuration
        self.config = SiteFilesConfig.objects.create(
            site_name="Test Site",
            site_url="https://example.com",
            sitemap_path="static/test/Sitemap.xml",
            robots_path="static/test/robots.txt",
            security_path="static/test/security.txt",
            llms_path="static/test/LLMs.txt",
            update_frequency="daily",
            update_sitemap=True,
            update_robots=True,
            update_security=True,
            update_llms=True
        )
    
    def call_command(self, *args, **kwargs):
        """Call the management command and capture output."""
        out = StringIO()
        err = StringIO()
        call_command(
            'update_site_files',
            *args,
            stdout=out,
            stderr=err,
            **kwargs
        )
        return out.getvalue(), err.getvalue()
    
    @mock.patch('site_files.management.commands.update_site_files.SitemapGenerator')
    @mock.patch('site_files.management.commands.update_site_files.RobotsTxtUpdater')
    @mock.patch('site_files.management.commands.update_site_files.SecurityTxtUpdater')
    @mock.patch('site_files.management.commands.update_site_files.LLMsTxtCreator')
    def test_update_all_files(self, mock_llms, mock_security, mock_robots, mock_sitemap):
        """Test updating all files."""
        # Configure mocks to return success
        mock_sitemap.return_value.update_sitemap.return_value = True
        mock_robots.return_value.write_robots_txt.return_value = True
        mock_security.return_value.update_security_txt.return_value = True
        mock_llms.return_value.write_llms_txt.return_value = True
        
        # Call the command
        out, err = self.call_command()
        
        # Check that all services were called
        mock_sitemap.return_value.update_sitemap.assert_called_once_with(self.config.sitemap_path)
        mock_robots.return_value.write_robots_txt.assert_called_once_with(
            self.config.robots_path, self.config.sitemap_path
        )
        mock_security.return_value.update_security_txt.assert_called_once_with(self.config.security_path)
        mock_llms.return_value.write_llms_txt.assert_called_once_with(self.config.llms_path)
        
        # Check output
        self.assertIn('Sitemap updated successfully', out)
        self.assertIn('robots.txt updated successfully', out)
        self.assertIn('security.txt updated successfully', out)
        self.assertIn('LLMs.txt updated successfully', out)
        
        # Check that last_update was updated
        self.config.refresh_from_db()
        self.assertIsNotNone(self.config.last_update)
    
    @mock.patch('site_files.management.commands.update_site_files.SitemapGenerator')
    @mock.patch('site_files.management.commands.update_site_files.RobotsTxtUpdater')
    @mock.patch('site_files.management.commands.update_site_files.SecurityTxtUpdater')
    @mock.patch('site_files.management.commands.update_site_files.LLMsTxtCreator')
    def test_update_specific_files(self, mock_llms, mock_security, mock_robots, mock_sitemap):
        """Test updating specific files."""
        # Configure mocks to return success
        mock_sitemap.return_value.update_sitemap.return_value = True
        mock_robots.return_value.write_robots_txt.return_value = True
        
        # Call the command with specific files
        out, err = self.call_command('--sitemap', '--robots')
        
        # Check that only specified services were called
        mock_sitemap.return_value.update_sitemap.assert_called_once()
        mock_robots.return_value.write_robots_txt.assert_called_once()
        mock_security.return_value.update_security_txt.assert_not_called()
        mock_llms.return_value.write_llms_txt.assert_not_called()
        
        # Check output
        self.assertIn('Sitemap updated successfully', out)
        self.assertIn('robots.txt updated successfully', out)
        self.assertNotIn('security.txt updated successfully', out)
        self.assertNotIn('LLMs.txt updated successfully', out)
    
    @mock.patch('site_files.management.commands.update_site_files.SitemapGenerator')
    @mock.patch('site_files.management.commands.update_site_files.RobotsTxtUpdater')
    @mock.patch('site_files.management.commands.update_site_files.SecurityTxtUpdater')
    @mock.patch('site_files.management.commands.update_site_files.LLMsTxtCreator')
    def test_respect_config_settings(self, mock_llms, mock_security, mock_robots, mock_sitemap):
        """Test that configuration settings are respected."""
        # Update configuration to disable some updates
        self.config.update_robots = False
        self.config.update_security = False
        self.config.save()
        
        # Call the command with --all flag
        out, err = self.call_command('--all')
        
        # Check that only enabled services were called
        mock_sitemap.return_value.update_sitemap.assert_called_once()
        mock_llms.return_value.write_llms_txt.assert_called_once()
        mock_robots.return_value.write_robots_txt.assert_not_called()
        mock_security.return_value.update_security_txt.assert_not_called()
    
    @mock.patch('site_files.management.commands.update_site_files.SitemapGenerator')
    def test_error_handling(self, mock_sitemap):
        """Test error handling in the command."""
        # Configure mock to raise an exception
        mock_sitemap.return_value.update_sitemap.side_effect = Exception("Test error")
        
        # Call the command with only sitemap update
        out, err = self.call_command('--sitemap')
        
        # Check that the error was reported
        self.assertIn('Error updating sitemap', out)
        self.assertIn('Failed', out)
    
    @mock.patch('site_files.models.SiteFilesConfig.objects.first')
    def test_no_configuration(self, mock_first):
        """Test behavior when no configuration exists."""
        # Delete the test configuration
        self.config.delete()
        
        # Configure mock to return None first, then the newly created config
        mock_first.side_effect = [None, SiteFilesConfig()]
        
        # Call the command
        out, err = self.call_command()
        
        # Check that a warning was issued and a default config was created
        self.assertIn('No configuration found', out)
    
    @mock.patch('site_files.models.SiteFilesConfig.objects.first')
    def test_configuration_error(self, mock_first):
        """Test error handling when getting configuration fails."""
        # Configure mock to raise an exception
        mock_first.side_effect = Exception("Database error")
        
        # Call the command and check for error
        with self.assertRaises(CommandError):
            self.call_command()
    
    @mock.patch('site_files.management.commands.update_site_files.SitemapGenerator')
    @mock.patch('site_files.management.commands.update_site_files.RobotsTxtUpdater')
    @mock.patch('site_files.management.commands.update_site_files.SecurityTxtUpdater')
    @mock.patch('site_files.management.commands.update_site_files.LLMsTxtCreator')
    def test_verbose_output(self, mock_llms, mock_security, mock_robots, mock_sitemap):
        """Test verbose output option."""
        # Configure mocks to return success
        mock_sitemap.return_value.update_sitemap.return_value = True
        
        # Call the command with verbose flag
        out, err = self.call_command('--sitemap', '--verbose')
        
        # Check that verbose output was enabled (this is hard to test directly,
        # but we can check that the command ran successfully)
        self.assertIn('Sitemap updated successfully', out)
    
    @mock.patch('site_files.management.commands.update_site_files.timezone.now')
    @mock.patch('site_files.management.commands.update_site_files.SitemapGenerator')
    def test_last_update_timestamp(self, mock_sitemap, mock_now):
        """Test that the last_update timestamp is updated."""
        # Set a fixed timestamp for testing
        test_time = timezone.now()
        mock_now.return_value = test_time
        
        # Configure mock to return success
        mock_sitemap.return_value.update_sitemap.return_value = True
        
        # Call the command
        self.call_command('--sitemap')
        
        # Check that last_update was updated
        self.config.refresh_from_db()
        self.assertEqual(self.config.last_update, test_time)
    
    @mock.patch('site_files.models.SiteFilesConfig.save')
    @mock.patch('site_files.management.commands.update_site_files.SitemapGenerator')
    def test_last_update_error(self, mock_sitemap, mock_save):
        """Test error handling when updating last_update fails."""
        # Configure mocks
        mock_sitemap.return_value.update_sitemap.return_value = True
        mock_save.side_effect = Exception("Database error")
        
        # Call the command
        out, err = self.call_command('--sitemap')
        
        # Check that a warning was issued
        self.assertIn('Error updating last_update timestamp', out)


if __name__ == '__main__':
    from django.test import runner
    runner.main()
</text>
</invoke>