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
            '--sitemap-index',
            action='store_true',
            help='Generate separate sitemap files and index (for large sites)',
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
        
        # Update config with correct paths and site URL from environment
        from django.conf import settings
        import os
        
        # Use site URL from environment variable
        site_url = os.getenv('SITE_URL', 'https://kabhishek18.com')
        if config.site_url != site_url:
            config.site_url = site_url
            config.save()
        
        # Update paths to point to templates directory
        template_paths = {
            'sitemap_path': 'templates/sitemap.xml',
            'robots_path': 'templates/robots.txt',
            'security_path': 'templates/security.txt',
            'llms_path': 'templates/humans.txt'
        }
        
        updated = False
        for field, path in template_paths.items():
            if getattr(config, field) != path:
                setattr(config, field, path)
                updated = True
        
        if updated:
            config.save()
            if verbose:
                self.stdout.write('Updated configuration paths to use templates directory')
        
        # Determine which files to update
        update_all = options.get('all', False)
        update_sitemap = options.get('sitemap', False) or update_all or config.update_sitemap
        update_sitemap_index = options.get('sitemap_index', False)
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
        
        if update_sitemap_index:
            try:
                self._update_sitemap_index(config, verbose)
                updated_files.append('sitemap_index.xml')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error updating sitemap index: {e}')
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
        
        # Import blog models
        from blog.models import Post, Category, Tag
        
        # Start building sitemap content
        sitemap_urls = []
        
        # Homepage
        sitemap_urls.append(f'''    <url>
        <loc>{config.site_url}</loc>
        <lastmod>{timezone.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>''')
        
        # Blog homepage
        sitemap_urls.append(f'''    <url>
        <loc>{config.site_url}/blog/</loc>
        <lastmod>{timezone.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>''')
        
        # Categories
        categories = Category.objects.all()
        for category in categories:
            sitemap_urls.append(f'''    <url>
        <loc>{config.site_url}/blog/category/{category.slug}/</loc>
        <lastmod>{timezone.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.7</priority>
    </url>''')
        
        # Tags (only include tags that have published posts)
        tags = Tag.objects.filter(posts__status='published').distinct()
        for tag in tags:
            sitemap_urls.append(f'''    <url>
        <loc>{config.site_url}/blog/tag/{tag.slug}/</loc>
        <lastmod>{timezone.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.6</priority>
    </url>''')
        
        # Published blog posts
        posts = Post.objects.filter(status='published').order_by('-updated_at')
        for post in posts:
            # Calculate priority based on post age and features
            priority = 0.8 if post.is_featured else 0.6
            
            # Determine change frequency based on post age
            days_old = (timezone.now().date() - post.created_at.date()).days
            if days_old < 7:
                changefreq = 'daily'
            elif days_old < 30:
                changefreq = 'weekly'
            else:
                changefreq = 'monthly'
            
            sitemap_urls.append(f'''    <url>
        <loc>{config.site_url}/blog/{post.slug}/</loc>
        <lastmod>{post.updated_at.strftime('%Y-%m-%d')}</lastmod>
        <changefreq>{changefreq}</changefreq>
        <priority>{priority}</priority>
    </url>''')
        
        # Combine all URLs into complete sitemap
        sitemap_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(sitemap_urls)}
</urlset>'''
        
        file_path = os.path.join(settings.BASE_DIR, config.sitemap_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(sitemap_content)
        
        if verbose:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Sitemap updated with {len(sitemap_urls)} URLs '
                    f'({len(categories)} categories, {len(tags)} tags, {len(posts)} blog posts)'
                )
            )
    
    def _update_sitemap_index(self, config, verbose):
        """Generate separate sitemap files and index for large sites."""
        if verbose:
            self.stdout.write('Generating sitemap index with separate files...')
        
        from blog.models import Post, Category, Tag
        
        # Create separate sitemap files
        sitemap_files = []
        
        # 1. Main pages sitemap
        main_sitemap = self._generate_main_sitemap(config)
        main_file_path = os.path.join(settings.BASE_DIR, 'sitemap_main.xml')
        with open(main_file_path, 'w', encoding='utf-8') as f:
            f.write(main_sitemap)
        sitemap_files.append('sitemap_main.xml')
        
        # 2. Categories sitemap
        categories = Category.objects.all()
        if categories.exists():
            categories_sitemap = self._generate_categories_sitemap(config, categories)
            categories_file_path = os.path.join(settings.BASE_DIR, 'sitemap_categories.xml')
            with open(categories_file_path, 'w', encoding='utf-8') as f:
                f.write(categories_sitemap)
            sitemap_files.append('sitemap_categories.xml')
        
        # 3. Tags sitemap
        tags = Tag.objects.filter(posts__status='published').distinct()
        if tags.exists():
            tags_sitemap = self._generate_tags_sitemap(config, tags)
            tags_file_path = os.path.join(settings.BASE_DIR, 'sitemap_tags.xml')
            with open(tags_file_path, 'w', encoding='utf-8') as f:
                f.write(tags_sitemap)
            sitemap_files.append('sitemap_tags.xml')
        
        # 4. Blog posts sitemap
        posts = Post.objects.filter(status='published')
        if posts.exists():
            posts_sitemap = self._generate_posts_sitemap(config, posts)
            posts_file_path = os.path.join(settings.BASE_DIR, 'sitemap_posts.xml')
            with open(posts_file_path, 'w', encoding='utf-8') as f:
                f.write(posts_sitemap)
            sitemap_files.append('sitemap_posts.xml')
        
        # Generate sitemap index
        index_content = self._generate_sitemap_index(config, sitemap_files)
        index_file_path = os.path.join(settings.BASE_DIR, 'sitemap_index.xml')
        with open(index_file_path, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        if verbose:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Sitemap index generated with {len(sitemap_files)} separate files'
                )
            )
    
    def _generate_main_sitemap(self, config):
        """Generate sitemap for main pages."""
        urls = [
            f'''    <url>
        <loc>{config.site_url}</loc>
        <lastmod>{timezone.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>''',
            f'''    <url>
        <loc>{config.site_url}/blog/</loc>
        <lastmod>{timezone.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>'''
        ]
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>'''
    
    def _generate_categories_sitemap(self, config, categories):
        """Generate sitemap for categories."""
        urls = []
        for category in categories:
            urls.append(f'''    <url>
        <loc>{config.site_url}/blog/category/{category.slug}/</loc>
        <lastmod>{timezone.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.7</priority>
    </url>''')
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>'''
    
    def _generate_tags_sitemap(self, config, tags):
        """Generate sitemap for tags."""
        urls = []
        for tag in tags:
            urls.append(f'''    <url>
        <loc>{config.site_url}/blog/tag/{tag.slug}/</loc>
        <lastmod>{timezone.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.6</priority>
    </url>''')
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>'''
    
    def _generate_posts_sitemap(self, config, posts):
        """Generate sitemap for blog posts."""
        urls = []
        for post in posts.order_by('-updated_at'):
            priority = 0.8 if post.is_featured else 0.6
            days_old = (timezone.now().date() - post.created_at.date()).days
            
            if days_old < 7:
                changefreq = 'daily'
            elif days_old < 30:
                changefreq = 'weekly'
            else:
                changefreq = 'monthly'
            
            urls.append(f'''    <url>
        <loc>{config.site_url}/blog/{post.slug}/</loc>
        <lastmod>{post.updated_at.strftime('%Y-%m-%d')}</lastmod>
        <changefreq>{changefreq}</changefreq>
        <priority>{priority}</priority>
    </url>''')
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>'''
    
    def _generate_sitemap_index(self, config, sitemap_files):
        """Generate sitemap index file."""
        sitemaps = []
        for sitemap_file in sitemap_files:
            sitemaps.append(f'''    <sitemap>
        <loc>{config.site_url}/{sitemap_file}</loc>
        <lastmod>{timezone.now().strftime('%Y-%m-%d')}</lastmod>
    </sitemap>''')
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(sitemaps)}
</sitemapindex>'''
    
    def _update_robots(self, config, verbose):
        """Update robots.txt file."""
        if verbose:
            self.stdout.write('Updating robots.txt...')
        
        # Check if sitemap index exists, otherwise use regular sitemap
        sitemap_index_path = os.path.join(settings.BASE_DIR, 'sitemap_index.xml')
        if os.path.exists(sitemap_index_path):
            sitemap_url = f'{config.site_url}/sitemap_index.xml'
        else:
            sitemap_url = f'{config.site_url}/sitemap.xml'
        
        robots_content = f'''User-agent: *
Allow: /

Sitemap: {sitemap_url}
'''
        
        file_path = os.path.join(settings.BASE_DIR, config.robots_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(robots_content)
    
    def _update_security(self, config, verbose):
        """Update security.txt file."""
        if verbose:
            self.stdout.write('Updating security.txt...')
        
        security_content = f'''Contact: mailto:developer@kabhishek18.com
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