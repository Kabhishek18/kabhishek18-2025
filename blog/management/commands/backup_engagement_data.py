from django.core.management.base import BaseCommand
from django.core import serializers
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from blog.models import (
    Post, Tag, Category, NewsletterSubscriber, Comment, 
    SocialShare, AuthorProfile, MediaItem
)
import json
import os
import gzip
import shutil
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backup and restore utilities for blog engagement data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            choices=['backup', 'restore', 'list-backups', 'cleanup-backups'],
            required=True,
            help='Action to perform',
        )
        parser.add_argument(
            '--backup-file',
            type=str,
            help='Specific backup file to restore from or create',
        )
        parser.add_argument(
            '--backup-dir',
            type=str,
            default='backups/engagement',
            help='Directory to store backups (default: backups/engagement)',
        )
        parser.add_argument(
            '--data-types',
            nargs='+',
            choices=['posts', 'tags', 'categories', 'subscribers', 'comments', 'social', 'authors', 'media', 'all'],
            default=['all'],
            help='Types of data to backup/restore (default: all)',
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            help='Compress backup files with gzip',
        )
        parser.add_argument(
            '--include-content',
            action='store_true',
            help='Include full post content in backup (warning: large files)',
        )
        parser.add_argument(
            '--date-range',
            type=str,
            help='Date range for backup in format YYYY-MM-DD:YYYY-MM-DD',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be backed up/restored without doing it',
        )
        parser.add_argument(
            '--keep-days',
            type=int,
            default=30,
            help='Number of days to keep old backups (default: 30)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force restore even if data exists (will overwrite)',
        )

    def handle(self, *args, **options):
        action = options['action']
        
        # Ensure backup directory exists
        backup_dir = options['backup_dir']
        os.makedirs(backup_dir, exist_ok=True)
        
        if action == 'backup':
            self._perform_backup(options)
        elif action == 'restore':
            self._perform_restore(options)
        elif action == 'list-backups':
            self._list_backups(options)
        elif action == 'cleanup-backups':
            self._cleanup_old_backups(options)

    def _perform_backup(self, options):
        """Perform backup of engagement data"""
        backup_dir = options['backup_dir']
        data_types = options['data_types']
        dry_run = options['dry_run']
        compress = options['compress']
        
        # Generate backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = options['backup_file'] or f"engagement_backup_{timestamp}.json"
        
        if compress and not backup_file.endswith('.gz'):
            backup_file += '.gz'
        
        backup_path = os.path.join(backup_dir, backup_file)
        
        self.stdout.write(f"Creating backup: {backup_path}")
        
        try:
            # Collect data
            backup_data = self._collect_backup_data(options)
            
            if dry_run:
                self._show_backup_summary(backup_data, backup_path)
                return
            
            # Write backup file
            if compress:
                with gzip.open(backup_path, 'wt', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, default=str)
            else:
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, default=str)
            
            # Get file size
            file_size = os.path.getsize(backup_path)
            size_mb = file_size / (1024 * 1024)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Backup completed successfully: {backup_path} ({size_mb:.2f} MB)"
                )
            )
            
            # Log backup creation
            logger.info(f"Engagement data backup created: {backup_path}")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Backup failed: {str(e)}")
            )
            logger.error(f"Backup failed: {str(e)}")

    def _collect_backup_data(self, options):
        """Collect data for backup"""
        data_types = options['data_types']
        include_content = options['include_content']
        date_range = self._parse_date_range(options.get('date_range'))
        
        backup_data = {
            'metadata': {
                'created_at': timezone.now().isoformat(),
                'version': '1.0',
                'data_types': data_types,
                'include_content': include_content,
                'date_range': date_range,
            },
            'data': {}
        }
        
        if 'all' in data_types or 'posts' in data_types:
            backup_data['data']['posts'] = self._backup_posts(date_range, include_content)
        
        if 'all' in data_types or 'tags' in data_types:
            backup_data['data']['tags'] = self._backup_tags()
        
        if 'all' in data_types or 'categories' in data_types:
            backup_data['data']['categories'] = self._backup_categories()
        
        if 'all' in data_types or 'subscribers' in data_types:
            backup_data['data']['subscribers'] = self._backup_subscribers(date_range)
        
        if 'all' in data_types or 'comments' in data_types:
            backup_data['data']['comments'] = self._backup_comments(date_range)
        
        if 'all' in data_types or 'social' in data_types:
            backup_data['data']['social_shares'] = self._backup_social_shares()
        
        if 'all' in data_types or 'authors' in data_types:
            backup_data['data']['author_profiles'] = self._backup_author_profiles()
        
        if 'all' in data_types or 'media' in data_types:
            backup_data['data']['media_items'] = self._backup_media_items(date_range)
        
        return backup_data

    def _backup_posts(self, date_range, include_content):
        """Backup post data"""
        posts_query = Post.objects.all()
        
        if date_range:
            posts_query = posts_query.filter(
                created_at__range=date_range
            )
        
        posts_data = []
        for post in posts_query.select_related('author').prefetch_related('tags', 'categories'):
            post_data = {
                'id': post.id,
                'title': post.title,
                'slug': post.slug,
                'author_username': post.author.username,
                'status': post.status,
                'created_at': post.created_at.isoformat(),
                'updated_at': post.updated_at.isoformat(),
                'is_featured': post.is_featured,
                'view_count': post.view_count,
                'allow_comments': post.allow_comments,
                'table_of_contents': post.table_of_contents,
                'tags': [tag.name for tag in post.tags.all()],
                'categories': [cat.name for cat in post.categories.all()],
            }
            
            if include_content:
                post_data['content'] = post.content
                post_data['excerpt'] = post.excerpt
            
            posts_data.append(post_data)
        
        return posts_data

    def _backup_tags(self):
        """Backup tag data"""
        return [
            {
                'name': tag.name,
                'slug': tag.slug,
                'color': tag.color,
                'description': tag.description,
                'created_at': tag.created_at.isoformat(),
            }
            for tag in Tag.objects.all()
        ]

    def _backup_categories(self):
        """Backup category data"""
        return [
            {
                'name': category.name,
                'slug': category.slug,
                'parent_name': category.parent.name if category.parent else None,
            }
            for category in Category.objects.all()
        ]

    def _backup_subscribers(self, date_range):
        """Backup newsletter subscriber data"""
        subscribers_query = NewsletterSubscriber.objects.all()
        
        if date_range:
            subscribers_query = subscribers_query.filter(
                subscribed_at__range=date_range
            )
        
        return [
            {
                'email': subscriber.email,
                'is_confirmed': subscriber.is_confirmed,
                'subscribed_at': subscriber.subscribed_at.isoformat(),
                'confirmed_at': subscriber.confirmed_at.isoformat() if subscriber.confirmed_at else None,
                'preferences': subscriber.preferences,
            }
            for subscriber in subscribers_query
        ]

    def _backup_comments(self, date_range):
        """Backup comment data"""
        comments_query = Comment.objects.all()
        
        if date_range:
            comments_query = comments_query.filter(
                created_at__range=date_range
            )
        
        return [
            {
                'post_slug': comment.post.slug,
                'parent_id': comment.parent.id if comment.parent else None,
                'author_name': comment.author_name,
                'author_email': comment.author_email,
                'author_website': comment.author_website,
                'content': comment.content,
                'is_approved': comment.is_approved,
                'created_at': comment.created_at.isoformat(),
                'ip_address': str(comment.ip_address),
            }
            for comment in comments_query.select_related('post', 'parent')
        ]

    def _backup_social_shares(self):
        """Backup social share data"""
        return [
            {
                'post_slug': share.post.slug,
                'platform': share.platform,
                'share_count': share.share_count,
                'last_shared': share.last_shared.isoformat(),
                'created_at': share.created_at.isoformat(),
            }
            for share in SocialShare.objects.select_related('post')
        ]

    def _backup_author_profiles(self):
        """Backup author profile data"""
        return [
            {
                'username': profile.user.username,
                'bio': profile.bio,
                'website': profile.website,
                'twitter': profile.twitter,
                'linkedin': profile.linkedin,
                'github': profile.github,
                'instagram': profile.instagram,
                'is_guest_author': profile.is_guest_author,
                'guest_author_email': profile.guest_author_email,
                'guest_author_company': profile.guest_author_company,
                'is_active': profile.is_active,
                'created_at': profile.created_at.isoformat(),
                'updated_at': profile.updated_at.isoformat(),
            }
            for profile in AuthorProfile.objects.select_related('user')
        ]

    def _backup_media_items(self, date_range):
        """Backup media item data"""
        media_query = MediaItem.objects.all()
        
        if date_range:
            media_query = media_query.filter(
                created_at__range=date_range
            )
        
        return [
            {
                'post_slug': item.post.slug,
                'media_type': item.media_type,
                'title': item.title,
                'description': item.description,
                'alt_text': item.alt_text,
                'order': item.order,
                'is_featured': item.is_featured,
                'video_url': item.video_url,
                'video_platform': item.video_platform,
                'video_id': item.video_id,
                'gallery_images': item.gallery_images,
                'file_size': item.file_size,
                'width': item.width,
                'height': item.height,
                'created_at': item.created_at.isoformat(),
                'updated_at': item.updated_at.isoformat(),
            }
            for item in media_query.select_related('post')
        ]

    def _parse_date_range(self, date_range_str):
        """Parse date range string"""
        if not date_range_str:
            return None
        
        try:
            start_str, end_str = date_range_str.split(':')
            start_date = datetime.strptime(start_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_str, '%Y-%m-%d')
            return (start_date, end_date)
        except ValueError:
            self.stdout.write(
                self.style.ERROR("Invalid date range format. Use YYYY-MM-DD:YYYY-MM-DD")
            )
            return None

    def _show_backup_summary(self, backup_data, backup_path):
        """Show summary of what would be backed up"""
        self.stdout.write(
            self.style.WARNING(f"DRY RUN: Would create backup at {backup_path}")
        )
        
        data = backup_data['data']
        
        for data_type, items in data.items():
            if items:
                self.stdout.write(f"  {data_type}: {len(items)} items")

    def _perform_restore(self, options):
        """Perform restore from backup"""
        backup_file = options['backup_file']
        backup_dir = options['backup_dir']
        dry_run = options['dry_run']
        force = options['force']
        
        if not backup_file:
            self.stdout.write(
                self.style.ERROR("--backup-file is required for restore action")
            )
            return
        
        backup_path = os.path.join(backup_dir, backup_file)
        
        if not os.path.exists(backup_path):
            self.stdout.write(
                self.style.ERROR(f"Backup file not found: {backup_path}")
            )
            return
        
        try:
            # Load backup data
            if backup_path.endswith('.gz'):
                with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                    backup_data = json.load(f)
            else:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
            
            if dry_run:
                self._show_restore_summary(backup_data, backup_path)
                return
            
            # Perform restore
            with transaction.atomic():
                self._restore_data(backup_data, force)
            
            self.stdout.write(
                self.style.SUCCESS(f"Restore completed successfully from {backup_path}")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Restore failed: {str(e)}")
            )
            logger.error(f"Restore failed: {str(e)}")

    def _restore_data(self, backup_data, force):
        """Restore data from backup"""
        data = backup_data['data']
        
        # Restore in dependency order
        if 'categories' in data:
            self._restore_categories(data['categories'], force)
        
        if 'tags' in data:
            self._restore_tags(data['tags'], force)
        
        if 'author_profiles' in data:
            self._restore_author_profiles(data['author_profiles'], force)
        
        if 'subscribers' in data:
            self._restore_subscribers(data['subscribers'], force)
        
        # Note: Posts, comments, social shares, and media would require more complex
        # restoration logic to handle foreign key relationships properly
        # This is a simplified implementation

    def _restore_categories(self, categories_data, force):
        """Restore category data"""
        for cat_data in categories_data:
            Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'slug': cat_data['slug']}
            )

    def _restore_tags(self, tags_data, force):
        """Restore tag data"""
        for tag_data in tags_data:
            Tag.objects.get_or_create(
                name=tag_data['name'],
                defaults={
                    'slug': tag_data['slug'],
                    'color': tag_data['color'],
                    'description': tag_data['description'],
                }
            )

    def _restore_author_profiles(self, profiles_data, force):
        """Restore author profile data"""
        from django.contrib.auth.models import User
        
        for profile_data in profiles_data:
            try:
                user = User.objects.get(username=profile_data['username'])
                AuthorProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'bio': profile_data['bio'],
                        'website': profile_data['website'],
                        'twitter': profile_data['twitter'],
                        'linkedin': profile_data['linkedin'],
                        'github': profile_data['github'],
                        'is_guest_author': profile_data['is_guest_author'],
                        'is_active': profile_data['is_active'],
                    }
                )
            except User.DoesNotExist:
                logger.warning(f"User {profile_data['username']} not found, skipping profile")

    def _restore_subscribers(self, subscribers_data, force):
        """Restore newsletter subscriber data"""
        for sub_data in subscribers_data:
            NewsletterSubscriber.objects.get_or_create(
                email=sub_data['email'],
                defaults={
                    'is_confirmed': sub_data['is_confirmed'],
                    'preferences': sub_data.get('preferences', {}),
                }
            )

    def _show_restore_summary(self, backup_data, backup_path):
        """Show summary of what would be restored"""
        self.stdout.write(
            self.style.WARNING(f"DRY RUN: Would restore from {backup_path}")
        )
        
        metadata = backup_data.get('metadata', {})
        data = backup_data['data']
        
        self.stdout.write(f"Backup created: {metadata.get('created_at', 'Unknown')}")
        self.stdout.write(f"Backup version: {metadata.get('version', 'Unknown')}")
        
        for data_type, items in data.items():
            if items:
                self.stdout.write(f"  {data_type}: {len(items)} items")

    def _list_backups(self, options):
        """List available backups"""
        backup_dir = options['backup_dir']
        
        if not os.path.exists(backup_dir):
            self.stdout.write(
                self.style.WARNING(f"Backup directory does not exist: {backup_dir}")
            )
            return
        
        backup_files = [
            f for f in os.listdir(backup_dir)
            if f.endswith('.json') or f.endswith('.json.gz')
        ]
        
        if not backup_files:
            self.stdout.write(
                self.style.WARNING("No backup files found")
            )
            return
        
        self.stdout.write(f"Available backups in {backup_dir}:")
        
        for backup_file in sorted(backup_files, reverse=True):
            backup_path = os.path.join(backup_dir, backup_file)
            file_size = os.path.getsize(backup_path)
            size_mb = file_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(os.path.getmtime(backup_path))
            
            self.stdout.write(
                f"  {backup_file} ({size_mb:.2f} MB, {mtime.strftime('%Y-%m-%d %H:%M:%S')})"
            )

    def _cleanup_old_backups(self, options):
        """Clean up old backup files"""
        backup_dir = options['backup_dir']
        keep_days = options['keep_days']
        dry_run = options['dry_run']
        
        if not os.path.exists(backup_dir):
            self.stdout.write(
                self.style.WARNING(f"Backup directory does not exist: {backup_dir}")
            )
            return
        
        cutoff_time = timezone.now() - timedelta(days=keep_days)
        
        backup_files = [
            f for f in os.listdir(backup_dir)
            if f.endswith('.json') or f.endswith('.json.gz')
        ]
        
        old_files = []
        
        for backup_file in backup_files:
            backup_path = os.path.join(backup_dir, backup_file)
            mtime = datetime.fromtimestamp(os.path.getmtime(backup_path))
            mtime = timezone.make_aware(mtime)
            
            if mtime < cutoff_time:
                old_files.append((backup_file, backup_path, mtime))
        
        if not old_files:
            self.stdout.write(
                self.style.SUCCESS(f"No backup files older than {keep_days} days found")
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would delete {len(old_files)} backup files older than {keep_days} days:"
                )
            )
            for backup_file, _, mtime in old_files:
                self.stdout.write(f"  - {backup_file} ({mtime.strftime('%Y-%m-%d %H:%M:%S')})")
        else:
            deleted_count = 0
            for backup_file, backup_path, mtime in old_files:
                try:
                    os.remove(backup_path)
                    deleted_count += 1
                    self.stdout.write(f"Deleted: {backup_file}")
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error deleting {backup_file}: {str(e)}")
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f"Deleted {deleted_count} old backup files")
            )