# Site Files Updater - User Guide

## Introduction

The Site Files Updater is a tool that automatically generates and updates important site metadata files:
- **Sitemap.xml**: Helps search engines discover and index your site's pages
- **robots.txt**: Provides instructions to search engine crawlers
- **security.txt**: Provides security contact information for security researchers
- **LLMs.txt**: Provides guidance for Large Language Models interacting with your site

This guide explains how to configure and use the Site Files Updater.

## Getting Started

The Site Files Updater is pre-configured with sensible defaults, so it should work out of the box. However, you may want to customize its behavior to suit your specific needs.

## Configuration

### Accessing the Configuration

1. Log in to the Django admin interface
2. Navigate to "Site Files" > "Site Files Configuration"
3. Click on the existing configuration or create a new one if none exists

### Configuration Options

#### Site Information

- **Site Name**: The name of your website
- **Site URL**: The base URL of your website (e.g., https://example.com)

#### File Paths

- **Sitemap Path**: Path where the sitemap will be saved (default: static/Sitemap.xml)
- **Robots Path**: Path where robots.txt will be saved (default: static/robots.txt)
- **Security Path**: Path where security.txt will be saved (default: static/security.txt)
- **LLMs Path**: Path where LLMs.txt will be saved (default: static/humans.txt)

#### Schedule Settings

- **Update Frequency**: How often the files should be updated (daily, weekly, monthly)

#### Feature Flags

- **Update Sitemap**: Whether to update the sitemap
- **Update Robots**: Whether to update robots.txt
- **Update Security**: Whether to update security.txt
- **Update LLMs**: Whether to update LLMs.txt

### Saving Configuration

After making changes to the configuration, click the "Save" button to apply your changes.

## Manual Execution

While the Site Files Updater runs automatically on a schedule, you may want to trigger it manually after making changes to your site.

### Using the Management Command

You can use the Django management command to manually update the site files:

```bash
# Update all files
python manage.py update_site_files

# Update only specific files
python manage.py update_site_files --sitemap --robots
```

### Command Options

- `--sitemap`: Update only the sitemap
- `--robots`: Update only the robots.txt
- `--security`: Update only the security.txt
- `--llms`: Update only the LLMs.txt

If no options are specified, all files will be updated.

### Example Usage

```bash
# Update only the sitemap and robots.txt
python manage.py update_site_files --sitemap --robots

# Update only the security.txt
python manage.py update_site_files --security
```

## Monitoring

### Last Update Time

The configuration page in the admin interface shows the last time the files were updated.

### Checking Generated Files

You can view the generated files in your browser:

- Sitemap: https://your-site.com/Sitemap.xml
- Robots: https://your-site.com/robots.txt
- Security: https://your-site.com/security.txt
- LLMs: https://your-site.com/humans.txt

## Troubleshooting

### Files Not Updating

If the files are not updating as expected:

1. Check that the Site Files Updater is enabled in the configuration
2. Verify that the file paths are correct
3. Ensure that the Django process has write permissions to the specified paths
4. Try running the management command manually to see if there are any errors

### Incorrect URLs in Files

If the URLs in the generated files are incorrect:

1. Check the "Site URL" setting in the configuration
2. Verify that your Django site domain is correctly configured
3. Check that your URLs are properly registered in Django's URL configuration

### Scheduled Updates Not Running

If the scheduled updates are not running:

1. Verify that Celery and Celery Beat are properly configured and running
2. Check the Celery logs for errors
3. Ensure that the update frequency is set correctly in the configuration

## Best Practices

### Sitemap

- Keep your sitemap up to date to ensure search engines can find all your pages
- Include only public-facing pages in your sitemap
- Set appropriate change frequencies and priorities for different types of content

### robots.txt

- Use robots.txt to guide search engines, not to hide content
- Don't block CSS and JavaScript files that are needed for rendering
- Use the sitemap directive to point search engines to your sitemap

### security.txt

- Keep your security contact information up to date
- Include a canonical URL to prevent spoofing
- Consider adding an encryption key for secure communication

### LLMs.txt

- Provide clear guidance on how LLMs should interact with your site
- Include information about your site's structure and content
- Specify any restrictions on AI-generated content or interactions

## Getting Help

If you encounter any issues with the Site Files Updater, please contact your site administrator or developer for assistance.