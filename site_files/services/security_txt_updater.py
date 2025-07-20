"""
Security.txt Updater Service

This module provides functionality to update the security.txt file with the current canonical URL
while preserving other directives.
"""
import os
import re
import logging
import shutil
from datetime import datetime
from typing import List, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class SecurityTxtUpdater:
    """
    A class to update the security.txt file with the current canonical URL
    while preserving other directives.
    """

    def __init__(self, site_url: str):
        """
        Initialize the SecurityTxtUpdater with the site URL.

        Args:
            site_url (str): The base URL of the site (e.g., https://example.com)
        """
        self.site_url = site_url.rstrip('/')
        
    def parse_security_txt(self, content: str) -> List[Tuple[str, str, str]]:
        """
        Parse the security.txt file content into directives.

        Args:
            content (str): The content of the security.txt file

        Returns:
            List[Tuple[str, str, str]]: A list of tuples containing (directive, value, comments)
                where comments are any lines preceding the directive
        """
        lines = content.split('\n')
        directives = []
        
        current_comments = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
                
            # Collect comments
            if line.startswith('#'):
                current_comments.append(lines[i])
                i += 1
                continue
                
            # Parse directive
            match = re.match(r'^([A-Za-z-]+):\s*(.*)$', line)
            if match:
                directive = match.group(1)
                value = match.group(2)
                directives.append((directive, value, '\n'.join(current_comments)))
                current_comments = []
            
            i += 1
            
        return directives
    
    def update_canonical_url(self, directives: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
        """
        Update the canonical URL directive in the list of directives.

        Args:
            directives (List[Tuple[str, str, str]]): The list of directives

        Returns:
            List[Tuple[str, str, str]]: The updated list of directives
        """
        canonical_url = f"{self.site_url}/.well-known/security.txt"
        
        # Check if Canonical directive exists
        for i, (directive, value, comments) in enumerate(directives):
            if directive.lower() == 'canonical':
                directives[i] = (directive, canonical_url, comments)
                return directives
        
        # If no Canonical directive exists, add one
        canonical_comments = "# The canonical URL of this security.txt file."
        directives.append(('Canonical', canonical_url, canonical_comments))
        
        return directives
    
    def format_security_txt(self, directives: List[Tuple[str, str, str]]) -> str:
        """
        Format the directives back into security.txt content.

        Args:
            directives (List[Tuple[str, str, str]]): The list of directives

        Returns:
            str: The formatted security.txt content
        """
        content = []
        
        # Add header if not present in comments
        if not any('security.txt' in d[2].lower() for d in directives if d[2]):
            header = (
                "# ===================================================================\n"
                f"# security.txt for {self.site_url.replace('https://', '').replace('http://', '')}\n"
                "# -------------------------------------------------------------------\n"
                "# This file provides a point of contact for security researchers\n"
                "# to report vulnerabilities in a responsible manner.\n"
                "# For more information, see https://securitytxt.org/\n"
                "# ===================================================================\n"
            )
            content.append(header)
        
        # Add directives with their comments
        for directive, value, comments in directives:
            if comments:
                content.append(comments)
            content.append(f"{directive}: {value}\n")
        
        return '\n'.join(content)
    
    def read_security_txt(self, file_path: str) -> Optional[str]:
        """
        Read the security.txt file.

        Args:
            file_path (str): Path to the security.txt file

        Returns:
            Optional[str]: The content of the file or None if the file doesn't exist
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            logger.warning(f"Security.txt file not found at {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error reading security.txt file: {str(e)}")
            return None
    
    def create_backup(self, file_path: str) -> bool:
        """
        Create a backup of the security.txt file.

        Args:
            file_path (str): Path to the security.txt file

        Returns:
            bool: True if backup was created successfully, False otherwise
        """
        try:
            if os.path.exists(file_path):
                backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                shutil.copy2(file_path, backup_path)
                logger.info(f"Created backup of security.txt at {backup_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error creating backup of security.txt: {str(e)}")
            return False
    
    def write_security_txt(self, file_path: str, content: str) -> bool:
        """
        Write content to the security.txt file.

        Args:
            file_path (str): Path to the security.txt file
            content (str): Content to write

        Returns:
            bool: True if the write was successful, False otherwise
        """
        try:
            # Ensure directory exists
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                
            # Write to a temporary file first
            temp_file = f"{file_path}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as file:
                file.write(content)
                
            # Replace the original file with the temporary file
            if os.path.exists(file_path):
                os.replace(temp_file, file_path)
            else:
                os.rename(temp_file, file_path)
                
            logger.info(f"Successfully updated security.txt at {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing security.txt file: {str(e)}")
            if os.path.exists(f"{file_path}.tmp"):
                try:
                    os.remove(f"{file_path}.tmp")
                except:
                    pass
            return False
    
    def update_security_txt(self, file_path: str) -> bool:
        """
        Update the security.txt file with the current canonical URL.

        Args:
            file_path (str): Path to the security.txt file

        Returns:
            bool: True if the update was successful, False otherwise
        """
        try:
            # Read the existing file
            content = self.read_security_txt(file_path)
            
            # If file doesn't exist, create a default one
            if content is None:
                content = (
                    "# ===================================================================\n"
                    f"# security.txt for {self.site_url.replace('https://', '').replace('http://', '')}\n"
                    "# -------------------------------------------------------------------\n"
                    "# This file provides a point of contact for security researchers\n"
                    "# to report vulnerabilities in a responsible manner.\n"
                    "# For more information, see https://securitytxt.org/\n"
                    "# ===================================================================\n\n"
                    "# The primary contact for any security-related issues.\n"
                    "Contact: mailto:security@example.com\n\n"
                    "# The canonical URL of this security.txt file.\n"
                    f"Canonical: {self.site_url}/.well-known/security.txt\n\n"
                    "# Preferred language for security reports.\n"
                    "Preferred-Languages: en\n"
                )
            
            # Parse the content
            directives = self.parse_security_txt(content)
            
            # Update the canonical URL
            updated_directives = self.update_canonical_url(directives)
            
            # Format the updated content
            updated_content = self.format_security_txt(updated_directives)
            
            # Create a backup of the existing file
            if os.path.exists(file_path):
                self.create_backup(file_path)
            
            # Write the updated content to the file
            return self.write_security_txt(file_path, updated_content)
        except Exception as e:
            logger.error(f"Error updating security.txt: {str(e)}")
            return False