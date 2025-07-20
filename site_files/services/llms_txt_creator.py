"""
LLMs.txt Creator Service

This module provides functionality to create or update the LLMs.txt file,
which provides guidance for large language models interacting with the site.
"""
import os
import logging
import shutil
from typing import Dict, List, Optional
from datetime import datetime

from .url_discovery import URLDiscoveryService, URLInfo

logger = logging.getLogger(__name__)

class LLMsTxtCreator:
    """
    A class to create or update the LLMs.txt file with guidance for large language models.
    """
    
    def __init__(self, site_url: str, site_name: str = None):
        """
        Initialize the LLMsTxtCreator with site information.
        
        Args:
            site_url (str): The base URL of the site (e.g., https://example.com)
            site_name (str, optional): The name of the site
        """
        self.site_url = site_url.rstrip('/')
        self.site_name = site_name or "Website"
        self.url_discovery_service = URLDiscoveryService(site_url=site_url)
        
    def generate_llms_txt_content(self) -> str:
        """
        Generate the content for the LLMs.txt file.
        
        Returns:
            str: The content for the LLMs.txt file
        """
        # Get all public URLs
        urls = self.url_discovery_service.get_all_public_urls()
        
        # Group URLs by type
        url_groups = self._group_urls_by_type(urls)
        
        # Generate the content
        content = self._generate_header()
        content += self._generate_site_structure_section(url_groups)
        content += self._generate_acceptable_interactions_section()
        content += self._generate_api_endpoints_section(url_groups.get('api', []))
        content += self._generate_content_licensing_section()
        
        return content
    
    def _group_urls_by_type(self, urls: List[URLInfo]) -> Dict[str, List[URLInfo]]:
        """
        Group URLs by their type.
        
        Args:
            urls (List[URLInfo]): A list of URLInfo objects
            
        Returns:
            Dict[str, List[URLInfo]]: A dictionary mapping URL types to lists of URLs
        """
        groups = {}
        
        for url in urls:
            if url.type not in groups:
                groups[url.type] = []
            groups[url.type].append(url)
            
        return groups
    
    def _generate_header(self) -> str:
        """
        Generate the header section of the LLMs.txt file.
        
        Returns:
            str: The header section
        """
        return f"""# LLMs.txt for {self.site_name}
# Version: 1.0
# Last Updated: {datetime.now().strftime('%Y-%m-%d')}
# This file provides guidance for large language models interacting with this site.

"""
    
    def _generate_site_structure_section(self, url_groups: Dict[str, List[URLInfo]]) -> str:
        """
        Generate the site structure section of the LLMs.txt file.
        
        Args:
            url_groups (Dict[str, List[URLInfo]]): A dictionary mapping URL types to lists of URLs
            
        Returns:
            str: The site structure section
        """
        section = """## Site Structure
This section describes the structure of the site, including main sections and content types.

"""
        
        # Add main sections
        section += "### Main Sections\n"
        for url_type, urls in url_groups.items():
            if url_type == 'page' and urls:
                section += "- Pages: Main static pages of the site\n"
            elif url_type == 'blog' and urls:
                section += "- Blog: Articles and posts\n"
            elif url_type == 'blog_category' and urls:
                section += "- Blog Categories: Categories for blog content\n"
            elif url_type == 'api' and urls:
                section += "- API: Application Programming Interface endpoints\n"
        
        section += "\n"
        
        # Add content types
        section += "### Content Types\n"
        if 'page' in url_groups:
            section += "- Pages: Static content pages\n"
        if 'blog' in url_groups:
            section += "- Blog Posts: Articles and news updates\n"
        if 'blog_category' in url_groups:
            section += "- Categories: Content organization by topic\n"
        
        section += "\n"
        
        # Add navigation
        section += "### Navigation\n"
        section += "The site has the following main navigation structure:\n"
        
        # Add homepage
        section += f"- Home: {self.site_url}/\n"
        
        # Add other main pages
        if 'page' in url_groups:
            for url in url_groups['page'][:5]:  # Limit to first 5 pages
                section += f"- {url.title or 'Page'}: {self.site_url}/{url.url}\n"
        
        # Add blog if available
        if 'blog' in url_groups:
            section += f"- Blog: {self.site_url}/blog/\n"
        
        section += "\n"
        
        return section
    
    def _generate_acceptable_interactions_section(self) -> str:
        """
        Generate the acceptable interactions section of the LLMs.txt file.
        
        Returns:
            str: The acceptable interactions section
        """
        return """## Acceptable AI Interactions
This section describes how AI systems should interact with this site.

### Permitted Uses
- Summarizing public content from the site
- Answering questions based on public information
- Providing links to relevant pages on the site
- Analyzing publicly available data

### Prohibited Uses
- Scraping content beyond rate limits
- Attempting to access non-public areas
- Generating false or misleading information about the site
- Impersonating the site or its owners
- Automated form submissions without explicit permission

### Interaction Guidelines
- Respect robots.txt directives
- Identify yourself as an AI system when interacting with site users
- Provide attribution when quoting or summarizing content
- Do not cache or store large amounts of content

"""
    
    def _generate_api_endpoints_section(self, api_urls: List[URLInfo]) -> str:
        """
        Generate the API endpoints section of the LLMs.txt file.
        
        Args:
            api_urls (List[URLInfo]): A list of API endpoint URLs
            
        Returns:
            str: The API endpoints section
        """
        section = """## API Endpoints
This section describes the API endpoints available on this site.

"""
        
        # Check if there are API endpoints
        if not api_urls:
            try:
                # Try to find API documentation
                from django.urls import reverse
                api_docs_url = f"{self.site_url}/api/docs/"
                section += f"API documentation is available at: {api_docs_url}\n\n"
            except:
                section += "No public API endpoints are currently available.\n\n"
            return section
        
        # Add API endpoints
        section += "### Available Endpoints\n"
        for url in api_urls:
            section += f"- {url.url}: {url.title or 'API Endpoint'}\n"
        
        section += "\n"
        
        # Add API usage information
        section += """### API Usage
- Authentication is required for most API endpoints
- Rate limits apply to all API requests
- See API documentation for detailed usage instructions

"""
        
        return section
    
    def _generate_content_licensing_section(self) -> str:
        """
        Generate the content licensing section of the LLMs.txt file.
        
        Returns:
            str: The content licensing section
        """
        return """## Content Licensing and Usage Policies
This section describes the licensing and usage policies for the site's content.

### Copyright
All content on this site is copyright protected unless otherwise stated.

### Usage Permissions
- Content may be quoted with proper attribution
- Summarization of content is generally permitted for informational purposes
- Republishing full articles or substantial portions requires permission

### Data Usage
- Public data may be used for analysis and research
- Personal data is protected and should not be collected or processed
- Usage of data must comply with the site's privacy policy

"""
    
    def create_backup(self, file_path: str) -> bool:
        """
        Create a backup of the existing LLMs.txt file.
        
        Args:
            file_path (str): Path to the LLMs.txt file
            
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
            logger.info(f"Created backup of LLMs.txt at {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create backup of LLMs.txt: {str(e)}")
            return False
    
    def write_llms_txt(self, file_path: str) -> bool:
        """
        Create or update the LLMs.txt file.
        
        Args:
            file_path (str): Path to the LLMs.txt file
            
        Returns:
            bool: True if the file was created or updated successfully, False otherwise
        """
        try:
            # Create backup if file exists
            if os.path.exists(file_path):
                self.create_backup(file_path)
                
            # Generate the content
            content = self.generate_llms_txt_content()
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            # Write the content
            with open(file_path, 'w') as f:
                f.write(content)
                
            logger.info(f"Successfully created/updated LLMs.txt at {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create/update LLMs.txt: {str(e)}")
            return False