from django.core.management.base import BaseCommand
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
# from django.contrib.sites.models import Site  # Not available in this project
from blog.models import Post, Category, Tag, AuthorProfile
from site_files.services.sitemap_generator import SitemapGenerator
from site_files.services.url_discovery import URLInfo
import os
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate enhanced sitemap with new blog engagement content types'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-file',
            type=str,
            help='Output file path for the sitemap (default: static/Sitemap.xml)',
        )
        parser.add_argument(
            '--include-drafts',
            action='store_true',
            help='Include draft posts in sitemap (for staging environments)',
        )
        parser.add_argument(
            '--include-tags',
            action='store_true',
            default=True,
            help='Include tag pages in sitemap (default: True)',
        )
        parser.add_argument(
            '--include-categories',
            action='store_true',
            default=True,
            help='Include category pages in sitemap (default: True)',
        )
        parser.add_argument(
            '--include-authors',
            action='store_true',
            default=True,
            help='Include author profile pages in sitemap (default: True)',
        )
        parser.add_argument(
            '--priority-featured',
            type=float,
            default=0.9,
            help='Priority for featured posts (default: 0.9)',
        )
        parser.add_argument(
            '--priority-posts',
            type=float,
            default=0.8,
            help='Priority for regular posts (default: 0.8)',
        )
        parser.add_argument(
            '--priority-categories',
            type=float,
            default=0.7,
            help='Priority for category pages (default: 0.7)',
        )
        parser.add_argument(
            '--priority-tags',
            type=float,
            default=0.6,
            help='Priority for tag pages (default: 0.6)',
        )
        parser.add_argument(
            '--priority-authors',
            type=float,
            default=0.5,
            help='Priority for author pages (default: 0.5)',
        )
        parser.add_argument(
            '--changefreq-posts',
            choices=['always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never'],
            default='weekly',
            help='Change frequency for posts (default: weekly)',
        )
        parser.add_argument(
            '--changefreq-categories',
            choices=['always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never'],
            default='daily',
            help='Change frequency for categories (default: daily)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be included without generating the file',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about sitemap generation',
        )

    def handle(self, *args, **options):
        try:
            # Get site URL
            site_url = self._get_site_url()
            
            # Generate URL list
            urls = self._generate_url_list(options, site_url)
            
            if options['dry_run']:
                self._show_dry_run_results(urls, options)
                return
            
            # Generate sitemap XML
            xml_content = self._generate_sitemap_xml(urls)
            
            # Write to file
            output_file = options['output_file'] or getattr(settings, 'SITEMAP_PATH', 'static/Sitemap.xml')
            success = self._write_sitemap(xml_content, output_file)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully generated sitemap with {len(urls)} URLs at {output_file}"
                    )
                )
                
                if options['verbose']:
                    self._show_sitemap_stats(urls)
            else:
                self.stdout.write(
                    self.style.ERROR("Failed to write sitemap file")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error generating sitemap: {str(e)}")
            )
            logger.error(f"Sitemap generation error: {str(e)}")

    def _get_site_url(self):
        """Get the site URL from settings"""
        site_url = getattr(settings, 'SITE_URL', None)
        
        if not site_url:
            site_url = "https://example.com"
            self.stdout.write(
                self.style.WARNING(
                    f"Could not determine site URL, using default: {site_url}"
                )
            )
        
        return site_url.rstrip('/')

    def _generate_url_list(self, options, site_url):
        """Generate list of URLs to include in sitemap"""
        urls = []
        
        # Add homepage
        urls.append(URLInfo(
            url='/',
            priority=1.0,
            changefreq='daily',
            lastmod=timezone.now()
        ))
        
        # Add blog posts
        urls.extend(self._get_post_urls(options))
        
        # Add categories
        if options['include_categories']:
            urls.extend(self._get_category_urls(options))
        
        # Add tags
        if options['include_tags']:
            urls.extend(self._get_tag_urls(options))
        
        # Add author profiles
        if options['include_authors']:
            urls.extend(self._get_author_urls(options))
        
        # Add blog list page
        try:
            blog_url = reverse('blog:list')
            urls.append(URLInfo(
                url=blog_url,
                priority=0.9,
                changefreq='daily',
                lastmod=timezone.now()
            ))
        except:
            pass
        
        return urls

    def _get_post_urls(self, options):
        """Get URLs for blog posts"""
        urls = []
        
        # Filter posts based on options
        posts_query = Post.objects.all()
        
        if not options['include_drafts']:
            posts_query = posts_query.filter(status='published')
        
        posts = posts_query.select_related('author').prefetch_related('tags', 'categories')
        
        for post in posts:
            try:
                # Determine priority based on featured status
                priority = options['priority_featured'] if post.is_featured else options['priority_posts']
                
                # Use post's updated_at as lastmod
                lastmod = post.updated_at or post.created_at
                
                url_info = URLInfo(
                    url=reverse('blog:detail', kwargs={'slug': post.slug}),
                    priority=priority,
                    changefreq=options['changefreq_posts'],
                    lastmod=lastmod
                )
                
                urls.append(url_info)
                
            except Exception as e:
                logger.warning(f"Could not generate URL for post {post.slug}: {str(e)}")
        
        return urls

    def _get_category_urls(self, options):
        """Get URLs for category pages"""
        urls = []
        
        categories = Category.objects.all()
        
        for category in categories:
            try:
                # Check if category has published posts
                post_count = category.posts.filter(status='published').count()
                
                if post_count > 0:
                    url_info = URLInfo(
                        url=reverse('blog:category', kwargs={'slug': category.slug}),
                        priority=options['priority_categories'],
                        changefreq=options['changefreq_categories'],
                        lastmod=timezone.now()
                    )
                    
                    urls.append(url_info)
                    
            except Exception as e:
                logger.warning(f"Could not generate URL for category {category.slug}: {str(e)}")
        
        return urls

    def _get_tag_urls(self, options):
        """Get URLs for tag pages"""
        urls = []
        
        tags = Tag.objects.all()
        
        for tag in tags:
            try:
                # Check if tag has published posts
                post_count = tag.posts.filter(status='published').count()
                
                if post_count > 0:
                    url_info = URLInfo(
                        url=reverse('blog:tag', kwargs={'slug': tag.slug}),
                        priority=options['priority_tags'],
                        changefreq='weekly',
                        lastmod=timezone.now()
                    )
                    
                    urls.append(url_info)
                    
            except Exception as e:
                logger.warning(f"Could not generate URL for tag {tag.slug}: {str(e)}")
        
        return urls

    def _get_author_urls(self, options):
        """Get URLs for author profile pages"""
        urls = []
        
        # Only include active authors with published posts
        authors = AuthorProfile.objects.filter(
            is_active=True,
            user__blog_posts__status='published'
        ).distinct().select_related('user')
        
        for author in authors:
            try:
                url_info = URLInfo(
                    url=reverse('blog:author_detail', kwargs={'username': author.user.username}),
                    priority=options['priority_authors'],
                    changefreq='monthly',
                    lastmod=author.updated_at
                )
                
                urls.append(url_info)
                
            except Exception as e:
                logger.warning(f"Could not generate URL for author {author.user.username}: {str(e)}")
        
        return urls

    def _generate_sitemap_xml(self, urls):
        """Generate XML content for sitemap"""
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        ]
        
        site_url = self._get_site_url()
        
        for url_info in urls:
            xml_parts.append(url_info.to_sitemap_element(site_url))
        
        xml_parts.append('</urlset>')
        
        return '\n'.join(xml_parts)

    def _write_sitemap(self, xml_content, output_file):
        """Write sitemap to file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Create backup if file exists
            if os.path.exists(output_file):
                backup_file = f"{output_file}.backup"
                os.rename(output_file, backup_file)
                self.stdout.write(f"Created backup: {backup_file}")
            
            # Write new sitemap
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            return True
            
        except Exception as e:
            logger.error(f"Error writing sitemap to {output_file}: {str(e)}")
            return False

    def _show_dry_run_results(self, urls, options):
        """Show what would be included in dry run mode"""
        self.stdout.write(
            self.style.WARNING(f"DRY RUN: Would generate sitemap with {len(urls)} URLs:")
        )
        
        # Group URLs by type
        url_types = {
            'posts': [],
            'categories': [],
            'tags': [],
            'authors': [],
            'other': []
        }
        
        for url in urls:
            if '/blog/' in url.url and url.url.count('/') == 3:
                url_types['posts'].append(url)
            elif '/category/' in url.url:
                url_types['categories'].append(url)
            elif '/tag/' in url.url:
                url_types['tags'].append(url)
            elif '/author/' in url.url:
                url_types['authors'].append(url)
            else:
                url_types['other'].append(url)
        
        for url_type, type_urls in url_types.items():
            if type_urls:
                self.stdout.write(f"\n{url_type.title()}: {len(type_urls)} URLs")
                if options['verbose']:
                    for url in type_urls[:5]:  # Show first 5
                        self.stdout.write(f"  - {url.url} (priority: {url.priority})")
                    if len(type_urls) > 5:
                        self.stdout.write(f"  ... and {len(type_urls) - 5} more")

    def _show_sitemap_stats(self, urls):
        """Show statistics about generated sitemap"""
        self.stdout.write("\nSitemap Statistics:")
        
        # Count by priority
        priority_counts = {}
        changefreq_counts = {}
        
        for url in urls:
            priority = str(url.priority)
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            changefreq = url.changefreq
            changefreq_counts[changefreq] = changefreq_counts.get(changefreq, 0) + 1
        
        self.stdout.write("By Priority:")
        for priority, count in sorted(priority_counts.items(), reverse=True):
            self.stdout.write(f"  {priority}: {count} URLs")
        
        self.stdout.write("By Change Frequency:")
        for changefreq, count in changefreq_counts.items():
            self.stdout.write(f"  {changefreq}: {count} URLs")
        
        # File size estimate
        total_chars = sum(len(url.url) for url in urls) * 4  # Rough estimate
        self.stdout.write(f"Estimated file size: ~{total_chars // 1024}KB")