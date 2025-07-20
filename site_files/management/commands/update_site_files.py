"""
Management command to update site metadata files.

This command updates the site's metadata files (Sitemap.xml, robots.txt, security.txt, LLMs.txt)
with the latest available URLs from the website.

Usage:
    python manage.py update_site_files [options]

Options:
    --sitemap       Update only the sitemap
    --robots        Update only the robots.txt
    --security      Update only the security.txt
    --llms          Update only the LLMs.txt
    --all           Update all files (default)
    --verbose       Increase output verbosity

Examples:
    # Update all files
    python manage.py update_site_files

    # Update only the sitemap
    python manage.py update_site_files --sitemap

    # Update robots.txt and security.txt
    python manage.py update_site_files --robots --security

    # Update all files with verbose output
    python manage.py update_site_files --all --verbose

Notes:
    - If no specific file options are provided, all files will be updated
    - The command respects the configuration settings in the admin interface
    - Each file update creates a backup of the existing file before modification
    - Results are logged and displayed in the console output
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from site_files.models import SiteFilesConfig
from site_files.services.sitemap_generator import SitemapGenerator
from site_files.services.robots_txt_updater import RobotsTxtUpdater
from site_files.services.security_txt_updater import SecurityTxtUpdater
from site_files.services.llms_txt_creator import LLMsTxtCreator
from django.utils import timezone

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates site metadata files (Sitemap.xml, robots.txt, security.txt, LLMs.txt)'
    
    def add_arguments(self, parser):
        parser.add_argument('--sitemap', action='store_true', help='Update only the sitemap')
        parser.add_argument('--robots', action='store_true', help='Update only the robots.txt')
        parser.add_argument('--security', action='store_true', help='Update only the security.txt')
        parser.add_argument('--llms', action='store_true', help='Update only the LLMs.txt')
        parser.add_argument('--all', action='store_true', help='Update all files (default)')
        parser.add_argument('--verbose', action='store_true', help='Increase output verbosity')
    
    def handle(self, *args, **options):
        # Set up logging based on verbosity
        verbosity = 2 if options['verbose'] else 1
        
        # Get configuration
        try:
            config = SiteFilesConfig.objects.first()
            if not config:
                config = SiteFilesConfig.objects.create()
                self.stdout.write(self.style.WARNING('No configuration found. Created default configuration.'))
        except Exception as e:
            raise CommandError(f"Error getting configuration: {e}")
        
        # Determine which files to update
        update_all = options['all'] or not any([
            options['sitemap'], options['robots'], options['security'], options['llms']
        ])
        
        update_sitemap = options['sitemap'] or update_all
        update_robots = options['robots'] or update_all
        update_security = options['security'] or update_all
        update_llms = options['llms'] or update_all
        
        # Apply configuration settings
        if not update_all:
            # If specific files are requested, respect those choices
            pass
        else:
            # If updating all files, respect configuration settings
            update_sitemap = update_sitemap and config.update_sitemap
            update_robots = update_robots and config.update_robots
            update_security = update_security and config.update_security
            update_llms = update_llms and config.update_llms
        
        # Track results
        results = {
            'sitemap': None,
            'robots': None,
            'security': None,
            'llms': None
        }
        
        # Update sitemap
        if update_sitemap:
            self.stdout.write('Updating sitemap...')
            try:
                sitemap_generator = SitemapGenerator(site_url=config.site_url)
                success = sitemap_generator.update_sitemap(config.sitemap_path)
                results['sitemap'] = success
                
                if success:
                    self.stdout.write(self.style.SUCCESS(f'Sitemap updated successfully at {config.sitemap_path}'))
                else:
                    self.stdout.write(self.style.ERROR('Failed to update sitemap'))
            except Exception as e:
                logger.error(f"Error updating sitemap: {e}")
                self.stdout.write(self.style.ERROR(f'Error updating sitemap: {e}'))
                results['sitemap'] = False
        
        # Update robots.txt
        if update_robots:
            self.stdout.write('Updating robots.txt...')
            try:
                robots_updater = RobotsTxtUpdater(site_url=config.site_url)
                success = robots_updater.write_robots_txt(config.robots_path, config.sitemap_path)
                results['robots'] = success
                
                if success:
                    self.stdout.write(self.style.SUCCESS(f'robots.txt updated successfully at {config.robots_path}'))
                else:
                    self.stdout.write(self.style.ERROR('Failed to update robots.txt'))
            except Exception as e:
                logger.error(f"Error updating robots.txt: {e}")
                self.stdout.write(self.style.ERROR(f'Error updating robots.txt: {e}'))
                results['robots'] = False
        
        # Update security.txt
        if update_security:
            self.stdout.write('Updating security.txt...')
            try:
                security_updater = SecurityTxtUpdater(site_url=config.site_url)
                success = security_updater.update_security_txt(config.security_path)
                results['security'] = success
                
                if success:
                    self.stdout.write(self.style.SUCCESS(f'security.txt updated successfully at {config.security_path}'))
                else:
                    self.stdout.write(self.style.ERROR('Failed to update security.txt'))
            except Exception as e:
                logger.error(f"Error updating security.txt: {e}")
                self.stdout.write(self.style.ERROR(f'Error updating security.txt: {e}'))
                results['security'] = False
        
        # Update LLMs.txt
        if update_llms:
            self.stdout.write('Updating LLMs.txt...')
            try:
                llms_creator = LLMsTxtCreator(site_url=config.site_url, site_name=config.site_name)
                success = llms_creator.write_llms_txt(config.llms_path)
                results['llms'] = success
                
                if success:
                    self.stdout.write(self.style.SUCCESS(f'LLMs.txt updated successfully at {config.llms_path}'))
                else:
                    self.stdout.write(self.style.ERROR('Failed to update LLMs.txt'))
            except Exception as e:
                logger.error(f"Error updating LLMs.txt: {e}")
                self.stdout.write(self.style.ERROR(f'Error updating LLMs.txt: {e}'))
                results['llms'] = False
        
        # Update last_update timestamp in configuration
        try:
            config.last_update = timezone.now()
            config.save()
        except Exception as e:
            logger.error(f"Error updating last_update timestamp: {e}")
            self.stdout.write(self.style.WARNING(f'Error updating last_update timestamp: {e}'))
        
        # Print summary
        self.stdout.write('\nSummary:')
        for file_type, success in results.items():
            if success is None:
                status = 'Skipped'
                style = self.style.WARNING
            elif success:
                status = 'Success'
                style = self.style.SUCCESS
            else:
                status = 'Failed'
                style = self.style.ERROR
            
            self.stdout.write(f'  {file_type}: {style(status)}')