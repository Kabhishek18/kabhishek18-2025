"""
Sitemap Generator Service for the Site Files Updater.

This module provides functionality to generate an XML sitemap based on the URLs
discovered by the URL Discovery Service.
"""
import logging
import os
import shutil
import xml.dom.minidom
from datetime import datetime
from typing import List, Optional, Tuple
from django.conf import settings
from .url_discovery import URLDiscoveryService, URLInfo

logger = logging.getLogger(__name__)

class SitemapGenerator:
    """
    Service for generating an XML sitemap based on discovered URLs.
    """
    
    def __init__(self, url_discovery_service: Optional[URLDiscoveryService] = None, site_url: str = None):
        """
        Initialize the sitemap generator.
        
        Args:
            url_discovery_service: The URL discovery service to use
            site_url: The base URL of the site (e.g., https://example.com)
        """
        self.site_url = site_url or getattr(settings, 'SITE_URL', 'https://example.com')
        self.url_discovery_service = url_discovery_service or URLDiscoveryService(site_url=self.site_url)
        self.default_sitemap_path = getattr(settings, 'SITEMAP_PATH', 'static/Sitemap.xml')
        self.backup_dir = getattr(settings, 'SITEMAP_BACKUP_DIR', 'static/backups')
        
    def generate_sitemap(self) -> str:
        """
        Generates an XML sitemap based on discovered URLs.
        
        Returns:
            The XML content as a string
        """
        logger.info("Generating sitemap")
        
        try:
            # Get all public URLs
            urls = self.url_discovery_service.get_all_public_urls()
            
            # Generate the XML content
            xml_content = self._generate_xml_content(urls)
            
            logger.info(f"Generated sitemap with {len(urls)} URLs")
            return xml_content
        except Exception as e:
            logger.error(f"Error generating sitemap: {e}")
            raise
    
    def _generate_xml_content(self, urls: List[URLInfo]) -> str:
        """
        Generate the XML content for the sitemap.
        
        Args:
            urls: A list of URLInfo objects
            
        Returns:
            The XML content as a string
        """
        # Start with the XML declaration and opening tags
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        ]
        
        # Add each URL as a sitemap element
        for url_info in urls:
            xml_parts.append(url_info.to_sitemap_element(self.site_url))
        
        # Add the closing tag
        xml_parts.append('</urlset>')
        
        # Join all parts with newlines
        xml_content = '\n'.join(xml_parts)
        
        # Pretty print the XML for better readability
        try:
            dom = xml.dom.minidom.parseString(xml_content)
            pretty_xml = dom.toprettyxml(indent="  ")
            
            # Remove empty lines that minidom sometimes adds
            pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
            
            return pretty_xml
        except Exception as e:
            logger.warning(f"Could not pretty-print XML: {e}. Returning raw XML.")
            return xml_content
            
    def write_sitemap(self, sitemap_content: str, file_path: Optional[str] = None) -> bool:
        """
        Write the sitemap content to the file system.
        
        Args:
            sitemap_content: The XML content to write
            file_path: The path to write the sitemap to (defaults to settings.SITEMAP_PATH)
            
        Returns:
            True if successful, False otherwise
        """
        file_path = file_path or self.default_sitemap_path
        logger.info(f"Writing sitemap to {file_path}")
        
        try:
            # Create backup of existing sitemap if it exists
            if os.path.exists(file_path):
                self._create_backup(file_path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write the new sitemap
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(sitemap_content)
            
            logger.info(f"Successfully wrote sitemap to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing sitemap to {file_path}: {e}")
            self._restore_backup(file_path)
            return False
    
    def _create_backup(self, file_path: str) -> Optional[str]:
        """
        Create a backup of the existing sitemap file.
        
        Args:
            file_path: The path to the sitemap file
            
        Returns:
            The path to the backup file, or None if backup failed
        """
        try:
            # Ensure backup directory exists
            os.makedirs(self.backup_dir, exist_ok=True)
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(file_path)
            backup_path = os.path.join(self.backup_dir, f"{filename}.{timestamp}.bak")
            
            # Copy the file
            shutil.copy2(file_path, backup_path)
            
            logger.info(f"Created backup of {file_path} at {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Error creating backup of {file_path}: {e}")
            return None
    
    def _restore_backup(self, file_path: str) -> bool:
        """
        Restore the most recent backup of the sitemap file.
        
        Args:
            file_path: The path to the sitemap file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find the most recent backup
            filename = os.path.basename(file_path)
            backup_files = [f for f in os.listdir(self.backup_dir) if f.startswith(filename) and f.endswith('.bak')]
            
            if not backup_files:
                logger.warning(f"No backup found for {file_path}")
                return False
            
            # Sort by timestamp (newest first)
            backup_files.sort(reverse=True)
            latest_backup = os.path.join(self.backup_dir, backup_files[0])
            
            # Restore the backup
            shutil.copy2(latest_backup, file_path)
            
            logger.info(f"Restored {file_path} from backup {latest_backup}")
            return True
        except Exception as e:
            logger.error(f"Error restoring backup for {file_path}: {e}")
            return False
    
    def update_sitemap(self, file_path: Optional[str] = None) -> bool:
        """
        Generate a new sitemap and write it to the file system.
        
        Args:
            file_path: The path to write the sitemap to (defaults to settings.SITEMAP_PATH)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate the sitemap content
            sitemap_content = self.generate_sitemap()
            
            # Write the sitemap to the file system
            success = self.write_sitemap(sitemap_content, file_path)
            
            return success
        except Exception as e:
            logger.error(f"Error updating sitemap: {e}")
            return False