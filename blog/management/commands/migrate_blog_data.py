from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from django.contrib.auth.models import User
from blog.models import Post, Tag, Category, NewsletterSubscriber, AuthorProfile
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Data migration utilities for existing blog data to support new engagement features'

    def add_arguments(self, parser):
        parser.add_argument(
            '--migration-type',
            choices=['tags', 'author-profiles', 'newsletter', 'categories', 'all'],
            default='all',
            help='Type of migration to perform (default: all)',
        )
        parser.add_argument(
            '--source-file',
            type=str,
            help='JSON file containing data to import',
        )
        parser.add_argument(
            '--export-file',
            type=str,
            help='JSON file to export current data to',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually migrating',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of records to process in each batch (default: 100)',
        )
        parser.add_argument(
            '--create-defaults',
            action='store_true',
            help='Create default tags and categories if none exist',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing records instead of skipping them',
        )

    def handle(self, *args, **options):
        migration_type = options['migration_type']
        
        if options['export_file']:
            self._export_data(options)
            return
        
        if migration_type in ['tags', 'all']:
            self._migrate_tags(options)
        
        if migration_type in ['author-profiles', 'all']:
            self._migrate_author_profiles(options)
        
        if migration_type in ['newsletter', 'all']:
            self._migrate_newsletter_data(options)
        
        if migration_type in ['categories', 'all']:
            self._migrate_categories(options)
        
        if options['create_defaults']:
            self._create_default_data(options)

    def _migrate_tags(self, options):
        """Migrate and create tags from post content or import from file"""
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        update_existing = options['update_existing']
        
        self.stdout.write("Migrating tags...")
        
        if options['source_file']:
            self._import_tags_from_file(options)
        else:
            self._extract_tags_from_posts(options)

    def _extract_tags_from_posts(self, options):
        """Extract potential tags from existing post content"""
        dry_run = options['dry_run']
        
        # Common programming and tech tags that might be found in content
        common_tags = [
            'python', 'django', 'javascript', 'react', 'vue', 'angular',
            'html', 'css', 'bootstrap', 'tailwind', 'api', 'rest',
            'database', 'sql', 'postgresql', 'mysql', 'mongodb',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp',
            'git', 'github', 'gitlab', 'ci/cd', 'devops',
            'machine-learning', 'ai', 'data-science', 'analytics',
            'web-development', 'mobile', 'ios', 'android',
            'security', 'performance', 'optimization', 'testing',
            'tutorial', 'guide', 'tips', 'best-practices'
        ]
        
        created_count = 0
        
        for tag_name in common_tags:
            # Check if posts contain this tag term
            posts_with_tag = Post.objects.filter(
                content__icontains=tag_name
            ).count()
            
            if posts_with_tag > 0:
                if not dry_run:
                    tag, created = Tag.objects.get_or_create(
                        name=tag_name.title(),
                        defaults={
                            'slug': slugify(tag_name),
                            'color': self._get_tag_color(tag_name),
                            'description': f'Posts related to {tag_name}'
                        }
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(f"Created tag: {tag.name}")
                else:
                    self.stdout.write(f"Would create tag: {tag_name.title()}")
                    created_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: Would create {created_count} tags")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Created {created_count} tags")
            )

    def _get_tag_color(self, tag_name):
        """Get a color for a tag based on its category"""
        color_map = {
            'python': '#3776ab',
            'django': '#092e20',
            'javascript': '#f7df1e',
            'react': '#61dafb',
            'vue': '#4fc08d',
            'html': '#e34f26',
            'css': '#1572b6',
            'database': '#336791',
            'docker': '#2496ed',
            'aws': '#ff9900',
            'git': '#f05032',
            'security': '#dc3545',
            'performance': '#28a745',
            'tutorial': '#6f42c1',
        }
        return color_map.get(tag_name.lower(), '#007acc')

    def _migrate_author_profiles(self, options):
        """Create author profiles for existing users"""
        dry_run = options['dry_run']
        update_existing = options['update_existing']
        
        self.stdout.write("Migrating author profiles...")
        
        # Get all users who have written posts
        authors = User.objects.filter(blog_posts__isnull=False).distinct()
        created_count = 0
        updated_count = 0
        
        for author in authors:
            try:
                profile, created = AuthorProfile.objects.get_or_create(
                    user=author,
                    defaults={
                        'bio': f'Author of {author.blog_posts.count()} blog posts.',
                        'is_active': True,
                    }
                )
                
                if created:
                    created_count += 1
                    if not dry_run:
                        self.stdout.write(f"Created profile for: {author.username}")
                elif update_existing and not profile.bio:
                    if not dry_run:
                        profile.bio = f'Author of {author.blog_posts.count()} blog posts.'
                        profile.save()
                        updated_count += 1
                        self.stdout.write(f"Updated profile for: {author.username}")
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error creating profile for {author.username}: {str(e)}")
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would create {created_count} author profiles"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created {created_count} author profiles, updated {updated_count}"
                )
            )

    def _migrate_newsletter_data(self, options):
        """Migrate existing newsletter subscriber data"""
        dry_run = options['dry_run']
        
        self.stdout.write("Migrating newsletter data...")
        
        # Check for any newsletter subscribers that might need token generation
        subscribers_without_tokens = NewsletterSubscriber.objects.filter(
            confirmation_token=''
        )
        
        updated_count = 0
        
        for subscriber in subscribers_without_tokens:
            if not dry_run:
                # Regenerate tokens
                subscriber.confirmation_token = subscriber._generate_token()
                if not subscriber.unsubscribe_token:
                    subscriber.unsubscribe_token = subscriber._generate_token()
                subscriber.save()
                updated_count += 1
            else:
                updated_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would update {updated_count} newsletter subscribers"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Updated {updated_count} newsletter subscribers with tokens"
                )
            )

    def _migrate_categories(self, options):
        """Ensure all categories have proper slugs and hierarchy"""
        dry_run = options['dry_run']
        
        self.stdout.write("Migrating categories...")
        
        categories_without_slugs = Category.objects.filter(slug='')
        updated_count = 0
        
        for category in categories_without_slugs:
            if not dry_run:
                category.slug = slugify(category.name)
                category.save()
                updated_count += 1
                self.stdout.write(f"Updated slug for category: {category.name}")
            else:
                updated_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would update {updated_count} categories"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Updated {updated_count} categories")
            )

    def _create_default_data(self, options):
        """Create default tags and categories if none exist"""
        dry_run = options['dry_run']
        
        self.stdout.write("Creating default data...")
        
        # Default categories
        default_categories = [
            {'name': 'Technology', 'slug': 'technology'},
            {'name': 'Programming', 'slug': 'programming'},
            {'name': 'Web Development', 'slug': 'web-development'},
            {'name': 'Tutorials', 'slug': 'tutorials'},
            {'name': 'News', 'slug': 'news'},
        ]
        
        # Default tags
        default_tags = [
            {'name': 'Python', 'color': '#3776ab'},
            {'name': 'Django', 'color': '#092e20'},
            {'name': 'JavaScript', 'color': '#f7df1e'},
            {'name': 'Tutorial', 'color': '#6f42c1'},
            {'name': 'Guide', 'color': '#17a2b8'},
        ]
        
        created_categories = 0
        created_tags = 0
        
        # Create categories
        for cat_data in default_categories:
            if not dry_run:
                category, created = Category.objects.get_or_create(
                    name=cat_data['name'],
                    defaults={'slug': cat_data['slug']}
                )
                if created:
                    created_categories += 1
            else:
                created_categories += 1
        
        # Create tags
        for tag_data in default_tags:
            if not dry_run:
                tag, created = Tag.objects.get_or_create(
                    name=tag_data['name'],
                    defaults={
                        'slug': slugify(tag_data['name']),
                        'color': tag_data['color']
                    }
                )
                if created:
                    created_tags += 1
            else:
                created_tags += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would create {created_categories} categories "
                    f"and {created_tags} tags"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created {created_categories} categories and {created_tags} tags"
                )
            )

    def _export_data(self, options):
        """Export current blog data to JSON file"""
        export_file = options['export_file']
        
        self.stdout.write(f"Exporting data to {export_file}...")
        
        data = {
            'posts': [],
            'categories': [],
            'tags': [],
            'newsletter_subscribers': [],
            'author_profiles': [],
            'export_date': datetime.now().isoformat(),
        }
        
        # Export posts
        for post in Post.objects.all():
            data['posts'].append({
                'id': post.id,
                'title': post.title,
                'slug': post.slug,
                'author': post.author.username,
                'status': post.status,
                'created_at': post.created_at.isoformat(),
                'categories': [cat.name for cat in post.categories.all()],
                'tags': [tag.name for tag in post.tags.all()],
                'is_featured': post.is_featured,
                'view_count': post.view_count,
            })
        
        # Export categories
        for category in Category.objects.all():
            data['categories'].append({
                'name': category.name,
                'slug': category.slug,
                'parent': category.parent.name if category.parent else None,
            })
        
        # Export tags
        for tag in Tag.objects.all():
            data['tags'].append({
                'name': tag.name,
                'slug': tag.slug,
                'color': tag.color,
                'description': tag.description,
            })
        
        # Export newsletter subscribers (without sensitive tokens)
        for subscriber in NewsletterSubscriber.objects.all():
            data['newsletter_subscribers'].append({
                'email': subscriber.email,
                'is_confirmed': subscriber.is_confirmed,
                'subscribed_at': subscriber.subscribed_at.isoformat(),
                'confirmed_at': subscriber.confirmed_at.isoformat() if subscriber.confirmed_at else None,
            })
        
        # Export author profiles
        for profile in AuthorProfile.objects.all():
            data['author_profiles'].append({
                'username': profile.user.username,
                'bio': profile.bio,
                'website': profile.website,
                'twitter': profile.twitter,
                'linkedin': profile.linkedin,
                'github': profile.github,
                'is_guest_author': profile.is_guest_author,
                'is_active': profile.is_active,
            })
        
        try:
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(
                self.style.SUCCESS(f"Successfully exported data to {export_file}")
            )
            
            # Print summary
            self.stdout.write(f"Exported:")
            self.stdout.write(f"  - {len(data['posts'])} posts")
            self.stdout.write(f"  - {len(data['categories'])} categories")
            self.stdout.write(f"  - {len(data['tags'])} tags")
            self.stdout.write(f"  - {len(data['newsletter_subscribers'])} subscribers")
            self.stdout.write(f"  - {len(data['author_profiles'])} author profiles")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error exporting data: {str(e)}")
            )

    def _import_tags_from_file(self, options):
        """Import tags from a JSON file"""
        source_file = options['source_file']
        dry_run = options['dry_run']
        
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'tags' not in data:
                self.stdout.write(
                    self.style.ERROR("No 'tags' key found in source file")
                )
                return
            
            created_count = 0
            
            for tag_data in data['tags']:
                if not dry_run:
                    tag, created = Tag.objects.get_or_create(
                        name=tag_data['name'],
                        defaults={
                            'slug': tag_data.get('slug', slugify(tag_data['name'])),
                            'color': tag_data.get('color', '#007acc'),
                            'description': tag_data.get('description', ''),
                        }
                    )
                    if created:
                        created_count += 1
                else:
                    created_count += 1
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"DRY RUN: Would import {created_count} tags")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"Imported {created_count} tags")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error importing tags: {str(e)}")
            )