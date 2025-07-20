# Site Files Updater Management Command

This document provides detailed information about the `update_site_files` management command, which is used to update the site's metadata files (Sitemap.xml, robots.txt, security.txt, LLMs.txt) with the latest available URLs from the website.

## Overview

The `update_site_files` command is designed to keep your site's metadata files up-to-date, ensuring that search engines and other automated systems have the most current information about your site. It can update all files at once or selectively update specific files based on command-line arguments.

## Usage

```bash
python manage.py update_site_files [options]
```

## Options

| Option | Description |
|--------|-------------|
| `--sitemap` | Update only the sitemap |
| `--robots` | Update only the robots.txt |
| `--security` | Update only the security.txt |
| `--llms` | Update only the LLMs.txt |
| `--all` | Update all files (default) |
| `--verbose` | Increase output verbosity |

## Examples

### Update all files
```bash
python manage.py update_site_files
```

### Update only the sitemap
```bash
python manage.py update_site_files --sitemap
```

### Update robots.txt and security.txt
```bash
python manage.py update_site_files --robots --security
```

### Update all files with verbose output
```bash
python manage.py update_site_files --all --verbose
```

## Configuration

The command uses the `SiteFilesConfig` model to determine file paths and other settings. You can configure these settings through the Django admin interface.

### Default Configuration

If no configuration exists, the command will create a default configuration with the following settings:

- **Site Name**: "My Site"
- **Site URL**: "https://example.com"
- **Sitemap Path**: "static/Sitemap.xml"
- **Robots Path**: "static/robots.txt"
- **Security Path**: "static/security.txt"
- **LLMs Path**: "static/humans.txt"
- **Update Frequency**: "daily"
- **Update Sitemap**: True
- **Update Robots**: True
- **Update Security**: True
- **Update LLMs**: True

## File Backups

Before updating any file, the command creates a backup of the existing file. Backups are stored with a timestamp in the filename, allowing you to restore previous versions if needed.

## Logging

The command logs all operations and errors using Django's logging system. You can configure the logging level and output in your Django settings.

## Integration with Celery

This command can be scheduled to run automatically using Celery Beat. See the Celery task documentation for more information.

## Error Handling

The command includes robust error handling to ensure that failures in one file update do not affect others. If an error occurs during an update, the command will:

1. Log the error
2. Display an error message in the console
3. Continue with the remaining updates
4. Provide a summary of all operations at the end

## Return Codes

The command returns the following exit codes:

- **0**: All requested operations completed successfully
- **1**: One or more operations failed
- **2**: An error occurred before any operations could be performed

## See Also

- [Django Management Commands Documentation](https://docs.djangoproject.com/en/stable/howto/custom-management-commands/)
- [Site Files Updater Design Document](/.kiro/specs/site-files-updater/design.md)