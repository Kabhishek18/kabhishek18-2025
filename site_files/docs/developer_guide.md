# Site Files Updater - Developer Guide

## Overview

The Site Files Updater is a Django application that automatically generates and updates important site metadata files:
- Sitemap.xml
- robots.txt
- security.txt
- LLMs.txt (for Large Language Model guidance)

This document provides technical details for developers who need to maintain, extend, or integrate with the Site Files Updater.

## Architecture

The Site Files Updater follows a service-oriented architecture within the Django framework, with clear separation of concerns:

1. **URL Discovery Service**: Discovers all available URLs in the Django project
2. **File Generator Services**: Separate services for each file type
3. **Management Command**: For manual execution
4. **Celery Task**: For scheduled execution
5. **Configuration System**: For controlling behavior

### Architecture Diagram

```
┌─────────────────┐     ┌─────────────────┐
│ Django Command  │     │ Celery Task     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────────────────────────────┐
│           URL Discovery Service         │
└─────────┬─────────┬─────────┬──────────┘
          │         │         │
          ▼         ▼         ▼          ▼
┌──────────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ Sitemap      │ │ Robots  │ │Security │ │ LLMs    │
│ Generator    │ │ Updater │ │ Updater │ │ Creator │
└──────┬───────┘ └────┬────┘ └────┬────┘ └────┬────┘
       │              │           │           │
       ▼              ▼           ▼           ▼
┌─────────────────────────────────────────────────┐
│                  File System                     │
└─────────────────────────────────────────────────┘
```

## Components

### 1. URL Discovery Service

The URL Discovery Service (`url_discovery.py`) is responsible for collecting all available URLs from the Django project.

#### Key Classes and Methods:

- `URLInfo`: Data class that stores URL metadata (path, lastmod, changefreq, priority)
- `get_all_public_urls()`: Discovers all public-facing URLs
- `get_dynamic_content_urls()`: Queries the database for dynamic content URLs

#### Example Usage:

```python
from site_files.services.url_discovery import get_all_public_urls, get_dynamic_content_urls

# Get all public URLs
urls = get_all_public_urls()

# Get only dynamic content URLs (e.g., blog posts)
dynamic_urls = get_dynamic_content_urls()

# Access URL metadata
for url_info in urls:
    print(f"URL: {url_info.url}")
    print(f"Last Modified: {url_info.lastmod}")
    print(f"Change Frequency: {url_info.changefreq}")
    print(f"Priority: {url_info.priority}")
```

### 2. Sitemap Generator

The Sitemap Generator (`sitemap_generator.py`) creates an XML sitemap based on the discovered URLs.

#### Key Classes and Methods:

- `SitemapGenerator`: Main class for generating sitemaps
- `generate_sitemap()`: Creates the XML content
- `write_sitemap_file()`: Writes the sitemap to the file system

#### Example Usage:

```python
from site_files.services.sitemap_generator import SitemapGenerator
from site_files.services.url_discovery import get_all_public_urls

# Create a sitemap generator
generator = SitemapGenerator()

# Generate sitemap content
urls = get_all_public_urls()
sitemap_content = generator.generate_sitemap(urls)

# Write to file
success = generator.write_sitemap_file('static/Sitemap.xml', sitemap_content)
```

### 3. Robots.txt Updater

The Robots.txt Updater (`robots_txt_updater.py`) updates the robots.txt file with the current sitemap URL.

#### Key Classes and Methods:

- `RobotsTxtUpdater`: Main class for updating robots.txt
- `update_robots_txt()`: Updates the file while preserving existing rules

#### Example Usage:

```python
from site_files.services.robots_txt_updater import RobotsTxtUpdater

# Create a robots.txt updater
updater = RobotsTxtUpdater(site_url='https://example.com')

# Update robots.txt
success = updater.update_robots_txt(
    path='static/robots.txt',
    sitemap_path='/Sitemap.xml'
)
```

### 4. Security.txt Updater

The Security.txt Updater (`security_txt_updater.py`) updates the security.txt file with the current canonical URL.

#### Key Classes and Methods:

- `SecurityTxtUpdater`: Main class for updating security.txt
- `update_security_txt()`: Updates the file while preserving existing content

#### Example Usage:

```python
from site_files.services.security_txt_updater import SecurityTxtUpdater

# Create a security.txt updater
updater = SecurityTxtUpdater(site_url='https://example.com')

# Update security.txt
success = updater.update_security_txt(path='static/security.txt')
```

### 5. LLMs.txt Creator

The LLMs.txt Creator (`llms_txt_creator.py`) creates or updates the LLMs.txt file with guidance for large language models.

#### Key Classes and Methods:

- `LLMsTxtCreator`: Main class for creating LLMs.txt
- `create_llms_txt()`: Creates or updates the file

#### Example Usage:

```python
from site_files.services.llms_txt_creator import LLMsTxtCreator
from site_files.services.url_discovery import get_all_public_urls

# Create an LLMs.txt creator
creator = LLMsTxtCreator(
    site_name='My Site',
    site_url='https://example.com',
    site_description='A description of my site'
)

# Create LLMs.txt
urls = get_all_public_urls()
success = creator.create_llms_txt(path='static/humans.txt', urls=urls)
```

### 6. Management Command

The management command (`update_site_files.py`) allows manual execution of the file updates.

#### Usage:

```bash
# Update all files
python manage.py update_site_files

# Update only specific files
python manage.py update_site_files --sitemap --robots
```

### 7. Celery Task

The Celery task (`tasks.py`) runs the file updates on a schedule.

#### Key Functions:

- `update_site_files()`: Updates all site metadata files
- `register_scheduled_tasks()`: Registers the task with Celery Beat

## Configuration

### SiteFilesConfig Model

The `SiteFilesConfig` model stores configuration settings for the Site Files Updater.

#### Fields:

- `site_name`: Name of the site
- `site_url`: URL of the site
- `sitemap_path`: Path to the sitemap file
- `robots_path`: Path to the robots.txt file
- `security_path`: Path to the security.txt file
- `llms_path`: Path to the LLMs.txt file
- `update_frequency`: Frequency of updates (daily, weekly, monthly)
- `update_sitemap`: Whether to update the sitemap
- `update_robots`: Whether to update robots.txt
- `update_security`: Whether to update security.txt
- `update_llms`: Whether to update LLMs.txt
- `last_update`: Timestamp of the last update

#### Example Usage:

```python
from site_files.models import SiteFilesConfig

# Get the configuration
config = SiteFilesConfig.objects.first()

# Use configuration values
site_url = config.site_url
sitemap_path = config.sitemap_path
```

## Extending the System

### Adding a New File Generator

To add a new file generator:

1. Create a new service class in `site_files/services/`
2. Add the necessary fields to the `SiteFilesConfig` model
3. Update the management command and Celery task to use the new service
4. Add tests for the new service

### Example: Adding a humans.txt Generator

```python
# site_files/services/humans_txt_generator.py
class HumansTxtGenerator:
    def __init__(self, site_name, team_info):
        self.site_name = site_name
        self.team_info = team_info
    
    def generate_humans_txt(self):
        content = f"""/* TEAM */
Site Name: {self.site_name}
"""
        for person in self.team_info:
            content += f"{person['role']}: {person['name']}\n"
        
        return content
    
    def write_humans_txt(self, path, content=None):
        if content is None:
            content = self.generate_humans_txt()
        
        try:
            with open(path, 'w') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Error writing humans.txt: {e}")
            return False
```

## Testing

The Site Files Updater includes comprehensive tests:

- Unit tests for each service
- Integration tests for the complete flow
- File validation tests

### Running Tests:

```bash
# Run all tests
python manage.py test site_files

# Run specific test modules
python manage.py test site_files.tests.test_url_discovery
python manage.py test site_files.tests.test_sitemap_generator
```

## Troubleshooting

### Common Issues

1. **File Permission Errors**:
   - Ensure the Django process has write permissions to the static files directory
   - Check file ownership and permissions

2. **URL Discovery Issues**:
   - Check that URLs are properly registered in Django's URL configuration
   - Verify that database models have the necessary methods for URL generation

3. **Scheduled Task Not Running**:
   - Verify that Celery and Celery Beat are properly configured
   - Check the Celery logs for errors

### Logging

The Site Files Updater uses Django's logging system. To enable detailed logging, add the following to your settings:

```python
LOGGING = {
    # ... existing logging configuration ...
    'loggers': {
        'site_files': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

## API Reference

### URL Discovery Service

```python
def get_all_public_urls() -> List[URLInfo]:
    """
    Discovers all public-facing URLs in the Django project.
    Returns a list of URLInfo objects.
    """

def get_dynamic_content_urls() -> List[URLInfo]:
    """
    Queries the database for dynamic content URLs.
    Returns a list of URLInfo objects.
    """

@dataclass
class URLInfo:
    """Data class for URL information."""
    url: str
    lastmod: datetime = None
    changefreq: str = 'monthly'
    priority: float = 0.5
    title: str = None
    type: str = 'page'
```

### Sitemap Generator

```python
class SitemapGenerator:
    def generate_sitemap(self, urls: List[URLInfo]) -> str:
        """
        Generates an XML sitemap based on the provided URLs.
        Returns the XML content as a string.
        """
    
    def write_sitemap_file(self, path: str, content: str = None) -> bool:
        """
        Writes the generated sitemap to the specified file path.
        Returns True if successful, False otherwise.
        """
```

### Robots.txt Updater

```python
class RobotsTxtUpdater:
    def __init__(self, site_url: str):
        """
        Initialize with the site URL.
        """
    
    def update_robots_txt(self, path: str, sitemap_path: str) -> bool:
        """
        Updates the robots.txt file at the specified path.
        Returns True if successful, False otherwise.
        """
```

### Security.txt Updater

```python
class SecurityTxtUpdater:
    def __init__(self, site_url: str):
        """
        Initialize with the site URL.
        """
    
    def update_security_txt(self, path: str) -> bool:
        """
        Updates the security.txt file at the specified path.
        Returns True if successful, False otherwise.
        """
```

### LLMs.txt Creator

```python
class LLMsTxtCreator:
    def __init__(self, site_name: str, site_url: str, site_description: str = None):
        """
        Initialize with site information.
        """
    
    def create_llms_txt(self, path: str, urls: List[URLInfo] = None) -> bool:
        """
        Creates or updates the LLMs.txt file at the specified path.
        Returns True if successful, False otherwise.
        """
```