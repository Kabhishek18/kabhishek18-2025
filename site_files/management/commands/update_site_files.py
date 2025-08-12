"""
Management command to update site metadata files.

This command updates Sitemap.xml, robots.txt, security.txt, and LLMs.txt files
based on the current site configuration.
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from site_files.models import SiteFilesConfig


class Command(BaseCommand):
    help = 'Update site metadata files (Sitemap.xml, robots.txt, security.txt, LLMs.txt)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--sitemap',
            action='store_true',
            help='Update sitemap.xml file',
        )
        parser.add_argument(
            '--robots',
            action='store_true',
            help='Update robots.txt file',
        )
        parser.add_argument(
            '--security',
            action='store_true',
            help='Update security.txt file',
        )
        parser.add_argument(
            '--llms',
            action='store_true',
            help='Update LLMs.txt file',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Update all site files',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output',
        )
    
    def handle(self, *args, **options):
        """Execute the command."""
        verbose = options.get('verbose', False)
        
        # Get configuration
        config = SiteFilesConfig.objects.first()
        if not config:
            config = SiteFilesConfig.objects.create()
            if verbose:
                self.stdout.write(
                    self.style.WARNING('No configuration found. Created default configuration.')
                )
        
        # Determine which files to update
        update_all = options.get('all', False)
        update_sitemap = options.get('sitemap', False) or update_all or config.update_sitemap
        update_robots = options.get('robots', False) or update_all or config.update_robots
        update_security = options.get('security', False) or update_all or config.update_security
        update_llms = options.get('llms', False) or update_all or config.update_llms
        
        if verbose:
            self.stdout.write(f"Starting site files update at {timezone.now()}")
        
        # Update files
        updated_files = []
        
        if update_sitemap:
            try:
                self._update_sitemap(config, verbose)
                updated_files.append('sitemap.xml')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error updating sitemap.xml: {e}')
                )
        
        if update_robots:
            try:
                self._update_robots(config, verbose)
                updated_files.append('robots.txt')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error updating robots.txt: {e}')
                )
        
        if update_security:
            try:
                self._update_security(config, verbose)
                updated_files.append('security.txt')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error updating security.txt: {e}')
                )
        
        if update_llms:
            try:
                self._update_llms(config, verbose)
                updated_files.append('LLMs.txt')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error updating LLMs.txt: {e}')
                )
        
        if updated_files:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated: {", ".join(updated_files)}'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING('No files were updated.')
            )
    
    def _update_sitemap(self, config, verbose):
        """Update sitemap.xml file."""
        if verbose:
            self.stdout.write('Updating sitemap.xml...')
        
        # Basic sitemap content
        sitemap_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{config.site_url}</loc>
        <lastmod>{timezone.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
</urlset>'''
        
        file_path = os.path.join(settings.BASE_DIR, config.sitemap_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(sitemap_content)
    
    def _update_robots(self, config, verbose):
        """Update robots.txt file."""
        if verbose:
            self.stdout.write('Updating robots.txt...')
        
        robots_content = f'''User-agent: *
Allow: /

Sitemap: {config.site_url}/sitemap.xml
'''
        
        file_path = os.path.join(settings.BASE_DIR, config.robots_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(robots_content)
    
    def _update_security(self, config, verbose):
        """Update security.txt file."""
        if verbose:
            self.stdout.write('Updating security.txt...')
        
        security_content = f'''Contact: mailto:security@{config.site_url.replace("https://", "").replace("http://", "")}
Expires: {(timezone.now() + timezone.timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')}
Preferred-Languages: en
Canonical: {config.site_url}/.well-known/security.txt
'''
        
        file_path = os.path.join(settings.BASE_DIR, config.security_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(security_content)
    
    def _update_llms(self, config, verbose):
        """Update LLMs.txt file."""
        if verbose:
            self.stdout.write('Updating LLMs.txt...')
        
        llms_content = f'''# LLMs.txt - AI Training Data Usage Policy
# Generated on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Site: {config.site_name}
URL: {config.site_url}

# This site allows AI training on publicly available content
# with proper attribution and respect for copyright.

AI-Training: allowed
Attribution: required
Commercial-Use: allowed-with-attribution
'''
        
        file_path = os.path.join(settings.BASE_DIR, config.llms_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(llms_content)