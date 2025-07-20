"""
Robots.txt Updater Service

This module provides functionality to update the robots.txt file with the current sitemap URL
while preserving existing user-agent rules and disallow directives.
"""
import os
import re
import logging
import shutil
from typing import List, Tuple, Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class RobotsTxtUpdater:
    """
    A class to update the robots.txt file with the current sitemap URL
    while preserving other directives.
    """
    
    def __init__(self, site_url: str):
        """
        Initialize the RobotsTxtUpdater with the site URL.
        
        Args:
            site_url (str): The base URL of the site (e.g., https://example.com)
        """
        self.site_url = site_url.rstrip('/')
        
    def parse_robots_txt(self, file_path: str) -> Tuple[List[str], Optional[str]]:
        """
        Parse the existing robots.txt file and extract its content.
        
        Args:
            file_path (str): Path to the robots.txt file
            
        Returns:
            Tuple[List[str], Optional[str]]: A tuple containing:
                - List of lines from the robots.txt file (excluding sitemap)
                - The current sitemap URL if found, None otherwise
        """
        if not os.path.exists(file_path):
            logger.warning(f"robots.txt file not found at {file_path}")
            return [], None
            
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                
            # Extract content and find sitemap
            content_lines = []
            sitemap_url = None
            sitemap_pattern = re.compile(r'^Sitemap:\s*(.*?)$', re.IGNORECASE)
            
            for line in lines:
                match = sitemap_pattern.match(line.strip())
                if match:
                    sitemap_url = match.group(1).strip()
                else:
                    content_lines.append(line)
                    
            return content_lines, sitemap_url
            
        except Exception as e:
            logger.error(f"Error parsing robots.txt: {str(e)}")
            return [], None
            
    def update_sitemap_url(self, content_lines: List[str], sitemap_path: str) -> List[str]:
        """
        Update the content lines with the current sitemap URL.
        
        Args:
            content_lines (List[str]): The content lines from the robots.txt file
            sitemap_path (str): The path to the sitemap file (e.g., /Sitemap.xml)
            
        Returns:
            List[str]: The updated content lines with the sitemap URL
        """
        # Ensure sitemap_path starts with a slash if it's a relative path
        if not sitemap_path.startswith('/') and not sitemap_path.startswith('http'):
            sitemap_path = f"/{sitemap_path}"
            
        # If sitemap_path is a relative path, prepend the site URL
        if not sitemap_path.startswith('http'):
            sitemap_url = f"{self.site_url}{sitemap_path}"
        else:
            sitemap_url = sitemap_path
            
        # Create a new list with the updated content
        updated_lines = content_lines.copy()
        
        # Ensure there's a newline at the end of the content
        if updated_lines and not updated_lines[-1].endswith('\n'):
            updated_lines[-1] += '\n'
            
        # Add an empty line if the file doesn't end with one
        if updated_lines and updated_lines[-1].strip():
            updated_lines.append('\n')
            
        # Add the sitemap directive
        updated_lines.append(f"Sitemap: {sitemap_url}\n")
        
        return updated_lines
        
    def generate_robots_txt(self, file_path: str, sitemap_path: str) -> str:
        """
        Generate the updated robots.txt content.
        
        Args:
            file_path (str): Path to the existing robots.txt file
            sitemap_path (str): Path to the sitemap file
            
        Returns:
            str: The updated robots.txt content
        """
        content_lines, _ = self.parse_robots_txt(file_path)
        
        # If no existing content, create a default robots.txt
        if not content_lines:
            content_lines = [
                "# robots.txt\n",
                "# This file tells search engine crawlers which pages they can access on your site\n",
                "\n",
                "User-agent: *\n",
                "Allow: /\n",
                "\n"
            ]
            
        updated_lines = self.update_sitemap_url(content_lines, sitemap_path)
        return ''.join(updated_lines)
        
    def create_backup(self, file_path: str) -> bool:
        """
        Create a backup of the existing robots.txt file.
        
        Args:
            file_path (str): Path to the robots.txt file
            
        Returns:
            bool: True if backup was created successfully, False otherwise
        """
        if not os.path.exists(file_path):
            logger.warning(f"Cannot create backup: {file_path} does not exist")
            return False
            
        try:
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backup_path = f"{file_path}.{timestamp}.bak"
            
            # Copy the file
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup of robots.txt at {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create backup of robots.txt: {str(e)}")
            return False
            
    def write_robots_txt(self, file_path: str, sitemap_path: str) -> bool:
        """
        Update the robots.txt file with the current sitemap URL.
        
        Args:
            file_path (str): Path to the robots.txt file
            sitemap_path (str): Path to the sitemap file
            
        Returns:
            bool: True if the file was updated successfully, False otherwise
        """
        try:
            # Create backup if file exists
            if os.path.exists(file_path):
                self.create_backup(file_path)
                
            # Generate the updated content
            content = self.generate_robots_txt(file_path, sitemap_path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            # Write the updated content
            with open(file_path, 'w') as f:
                f.write(content)
                
            logger.info(f"Successfully updated robots.txt at {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to update robots.txt: {str(e)}")
            return False