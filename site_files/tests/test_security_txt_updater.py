"""
Tests for the SecurityTxtUpdater class.
"""
import os
import tempfile
import unittest
from unittest.mock import patch, mock_open, MagicMock

from django.test import TestCase
from site_files.services.security_txt_updater import SecurityTxtUpdater


class SecurityTxtUpdaterTests(TestCase):
    """Test cases for the SecurityTxtUpdater class."""

    def setUp(self):
        """Set up test environment."""
        self.site_url = "https://example.com"
        self.updater = SecurityTxtUpdater(self.site_url)
        
        self.sample_security_txt = """# ===================================================================
# security.txt for example.com
# -------------------------------------------------------------------
# This file provides a point of contact for security researchers
# to report vulnerabilities in a responsible manner.
# For more information, see https://securitytxt.org/
# ===================================================================

# The primary contact for any security-related issues.
Contact: mailto:security@example.com

# The canonical URL of this security.txt file.
Canonical: https://old-domain.com/.well-known/security.txt

# Preferred language for security reports.
Preferred-Languages: en
"""

    def test_parse_security_txt(self):
        """Test parsing security.txt content."""
        directives = self.updater.parse_security_txt(self.sample_security_txt)
        
        # Check that we have the expected number of directives
        self.assertEqual(len(directives), 3)
        
        # Check that directives are correctly parsed
        self.assertEqual(directives[0][0], "Contact")
        self.assertEqual(directives[0][1], "mailto:security@example.com")
        self.assertTrue("primary contact" in directives[0][2])
        
        self.assertEqual(directives[1][0], "Canonical")
        self.assertEqual(directives[1][1], "https://old-domain.com/.well-known/security.txt")
        self.assertTrue("canonical URL" in directives[1][2])
        
        self.assertEqual(directives[2][0], "Preferred-Languages")
        self.assertEqual(directives[2][1], "en")
        self.assertTrue("Preferred language" in directives[2][2])

    def test_update_canonical_url(self):
        """Test updating the canonical URL in directives."""
        directives = self.updater.parse_security_txt(self.sample_security_txt)
        updated_directives = self.updater.update_canonical_url(directives)
        
        # Check that the canonical URL is updated
        for directive, value, _ in updated_directives:
            if directive == "Canonical":
                self.assertEqual(value, "https://example.com/.well-known/security.txt")
                break
        else:
            self.fail("Canonical directive not found")

    def test_update_canonical_url_missing(self):
        """Test adding a canonical URL when it's missing."""
        # Create a sample without a canonical URL
        sample_without_canonical = """# security.txt
Contact: mailto:security@example.com
Preferred-Languages: en
"""
        directives = self.updater.parse_security_txt(sample_without_canonical)
        updated_directives = self.updater.update_canonical_url(directives)
        
        # Check that a canonical URL is added
        canonical_found = False
        for directive, value, _ in updated_directives:
            if directive == "Canonical":
                self.assertEqual(value, "https://example.com/.well-known/security.txt")
                canonical_found = True
                break
        
        self.assertTrue(canonical_found, "Canonical directive should be added")

    def test_format_security_txt(self):
        """Test formatting directives back to security.txt content."""
        directives = self.updater.parse_security_txt(self.sample_security_txt)
        updated_directives = self.updater.update_canonical_url(directives)
        formatted_content = self.updater.format_security_txt(updated_directives)
        
        # Check that the formatted content contains the updated canonical URL
        self.assertIn("https://example.com/.well-known/security.txt", formatted_content)
        
        # Check that other directives are preserved
        self.assertIn("Contact: mailto:security@example.com", formatted_content)
        self.assertIn("Preferred-Languages: en", formatted_content)

    def test_read_security_txt_file_not_found(self):
        """Test reading a non-existent security.txt file."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            content = self.updater.read_security_txt("/nonexistent/path")
            self.assertIsNone(content)

    def test_read_security_txt_error(self):
        """Test handling errors when reading security.txt file."""
        with patch('builtins.open', side_effect=Exception("Test error")):
            content = self.updater.read_security_txt("/path/with/error")
            self.assertIsNone(content)

    def test_create_backup(self):
        """Test creating a backup of the security.txt file."""
        with patch('os.path.exists', return_value=True), \
             patch('shutil.copy2') as mock_copy:
            result = self.updater.create_backup("/mock/path")
            self.assertTrue(result)
            mock_copy.assert_called_once()
    
    def test_create_backup_file_not_exists(self):
        """Test creating a backup when the file doesn't exist."""
        with patch('os.path.exists', return_value=False), \
             patch('shutil.copy2') as mock_copy:
            result = self.updater.create_backup("/mock/path")
            self.assertFalse(result)
            mock_copy.assert_not_called()
    
    def test_create_backup_error(self):
        """Test handling errors when creating a backup."""
        with patch('os.path.exists', return_value=True), \
             patch('shutil.copy2', side_effect=Exception("Test error")):
            result = self.updater.create_backup("/mock/path")
            self.assertFalse(result)
    
    def test_write_security_txt(self):
        """Test writing content to the security.txt file."""
        mock_file = mock_open()
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_file), \
             patch('os.replace') as mock_replace:
            result = self.updater.write_security_txt("/mock/path", "Test content")
            self.assertTrue(result)
            mock_file.assert_called_once_with("/mock/path.tmp", 'w', encoding='utf-8')
            mock_replace.assert_called_once()
    
    def test_write_security_txt_new_file(self):
        """Test writing content when the file doesn't exist."""
        mock_file = mock_open()
        with patch('os.path.exists', return_value=False), \
             patch('os.path.dirname', return_value=""), \
             patch('builtins.open', mock_file), \
             patch('os.rename') as mock_rename:
            result = self.updater.write_security_txt("/mock/path", "Test content")
            self.assertTrue(result)
            mock_file.assert_called_once_with("/mock/path.tmp", 'w', encoding='utf-8')
            mock_rename.assert_called_once()
    
    def test_write_security_txt_create_directory(self):
        """Test creating directory when writing security.txt file."""
        mock_file = mock_open()
        with patch('os.path.exists', side_effect=[False, False]), \
             patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', mock_file), \
             patch('os.rename'):
            result = self.updater.write_security_txt("/mock/dir/path", "Test content")
            self.assertTrue(result)
            mock_makedirs.assert_called_once()
    
    def test_write_security_txt_error(self):
        """Test handling errors when writing security.txt file."""
        with patch('builtins.open', side_effect=Exception("Test error")):
            result = self.updater.write_security_txt("/mock/path", "Test content")
            self.assertFalse(result)
    
    def test_update_security_txt(self):
        """Test the update_security_txt method."""
        # Mock the necessary methods
        with patch.object(self.updater, 'read_security_txt', return_value=self.sample_security_txt), \
             patch.object(self.updater, 'create_backup', return_value=True), \
             patch.object(self.updater, 'write_security_txt', return_value=True), \
             patch('os.path.exists', return_value=True):
            result = self.updater.update_security_txt("/mock/path")
            self.assertTrue(result)
    
    def test_update_security_txt_new_file(self):
        """Test creating a new security.txt file when it doesn't exist."""
        # Mock the necessary methods
        with patch.object(self.updater, 'read_security_txt', return_value=None), \
             patch.object(self.updater, 'write_security_txt', return_value=True), \
             patch('os.path.exists', return_value=False):
            result = self.updater.update_security_txt("/mock/path")
            self.assertTrue(result)
    
    def test_update_security_txt_write_error(self):
        """Test handling write errors when updating security.txt."""
        # Mock the necessary methods
        with patch.object(self.updater, 'read_security_txt', return_value=self.sample_security_txt), \
             patch.object(self.updater, 'create_backup', return_value=True), \
             patch.object(self.updater, 'write_security_txt', return_value=False), \
             patch('os.path.exists', return_value=True):
            result = self.updater.update_security_txt("/mock/path")
            self.assertFalse(result)