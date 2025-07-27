from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from blog.models import Post, NewsletterSubscriber
from blog.tasks import send_new_post_notification
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Enhanced newsletter sending automation with scheduling and batch processing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--post-id',
            type=int,
            help='ID of the specific post to send newsletter for',
        )
        parser.add_argument(
            '--post-slug',
            type=str,
            help='Slug of the specific post to send newsletter for',
        )
        parser.add_argument(
            '--latest',
            action='store_true',
            help='Send newsletter for the latest published post',
        )
        parser.add_argument(
            '--auto',
            action='store_true',
            help='Automatically send newsletters for posts published in the last 24 hours',
        )
        parser.add_argument(
            '--featured-only',
            action='store_true',
            help='Only send newsletters for featured posts',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of subscribers to process in each batch (default: 100)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force send even if newsletter was already sent for this post',
        )
        parser.add_argument(
            '--schedule',
            type=str,
            help='Schedule newsletter for later (format: YYYY-MM-DD HH:MM)',
        )

    def handle(self, *args, **options):
        if options['auto']:
            self._handle_auto_newsletter(options)
        elif options['schedule']:
            self._handle_scheduled_newsletter(options)
        else:
            self._handle_manual_newsletter(options)

    def _handle_manual_newsletter(self, options):
        """Handle manual newsletter sending for specific posts"""
        post = None
        
        if options['post_id']:
            try:
                post = Post.objects.get(id=options['post_id'], status='published')
                self.stdout.write(f"Found post by ID: {post.title}")
            except Post.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"No published post found with ID {options['post_id']}")
                )
                return
                
        elif options['post_slug']:
            try:
                post = Post.objects.get(slug=options['post_slug'], status='published')
                self.stdout.write(f"Found post by slug: {post.title}")
            except Post.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"No published post found with slug '{options['post_slug']}'")
                )
                return
                
        elif options['latest']:
            try:
                query = Post.objects.filter(status='published')
                if options['featured_only']:
                    query = query.filter(is_featured=True)
                post = query.latest('created_at')
                self.stdout.write(f"Found latest post: {post.title}")
            except Post.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR("No published posts found")
                )
                return
        else:
            self.stdout.write(
                self.style.ERROR("Please specify --post-id, --post-slug, --latest, or --auto")
            )
            return

        self._send_newsletter_for_post(post, options)

    def _handle_auto_newsletter(self, options):
        """Handle automatic newsletter sending for recent posts"""
        # Find posts published in the last 24 hours
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        query = Post.objects.filter(
            status='published',
            created_at__gte=cutoff_time
        )
        
        if options['featured_only']:
            query = query.filter(is_featured=True)
        
        recent_posts = query.order_by('-created_at')
        
        if not recent_posts.exists():
            self.stdout.write(
                self.style.WARNING("No posts published in the last 24 hours")
            )
            return
        
        self.stdout.write(f"Found {recent_posts.count()} recent posts to process")
        
        for post in recent_posts:
            # Check if newsletter was already sent (simple check - could be enhanced)
            if not options['force']:
                # This is a simplified check - in production, you might want to track
                # newsletter sending status in the database
                self.stdout.write(f"Processing post: {post.title}")
            
            self._send_newsletter_for_post(post, options)

    def _handle_scheduled_newsletter(self, options):
        """Handle scheduled newsletter sending"""
        from datetime import datetime
        from celery import current_app
        
        try:
            # Parse the schedule time
            schedule_time = datetime.strptime(options['schedule'], '%Y-%m-%d %H:%M')
            schedule_time = timezone.make_aware(schedule_time)
            
            if schedule_time <= timezone.now():
                self.stdout.write(
                    self.style.ERROR("Scheduled time must be in the future")
                )
                return
            
            # Get the post to schedule
            post = self._get_post_from_options(options)
            if not post:
                return
            
            # Schedule the task
            task = send_new_post_notification.apply_async(
                args=[post.id],
                eta=schedule_time
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Newsletter for '{post.title}' scheduled for {schedule_time} "
                    f"(Task ID: {task.id})"
                )
            )
            
        except ValueError:
            self.stdout.write(
                self.style.ERROR("Invalid schedule format. Use: YYYY-MM-DD HH:MM")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error scheduling newsletter: {str(e)}")
            )

    def _get_post_from_options(self, options):
        """Get post based on command options"""
        if options['post_id']:
            try:
                return Post.objects.get(id=options['post_id'], status='published')
            except Post.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"No published post found with ID {options['post_id']}")
                )
                return None
        elif options['post_slug']:
            try:
                return Post.objects.get(slug=options['post_slug'], status='published')
            except Post.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"No published post found with slug '{options['post_slug']}'")
                )
                return None
        elif options['latest']:
            try:
                query = Post.objects.filter(status='published')
                if options['featured_only']:
                    query = query.filter(is_featured=True)
                return query.latest('created_at')
            except Post.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR("No published posts found")
                )
                return None
        return None

    def _send_newsletter_for_post(self, post, options):
        """Send newsletter for a specific post with enhanced options"""
        # Get subscriber count for reporting
        subscriber_count = NewsletterSubscriber.objects.filter(is_confirmed=True).count()
        
        if subscriber_count == 0:
            self.stdout.write(
                self.style.WARNING("No confirmed subscribers found")
            )
            return
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would send newsletter for '{post.title}' "
                    f"to {subscriber_count} subscribers"
                )
            )
            return
        
        # Send newsletter
        self.stdout.write(f"Sending newsletter for: {post.title}")
        self.stdout.write(f"Subscribers: {subscriber_count}")
        
        try:
            task = send_new_post_notification.delay(post.id)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Newsletter task queued with ID: {task.id}"
                )
            )
            
            # Log the newsletter sending
            logger.info(
                f"Newsletter queued for post '{post.title}' (ID: {post.id}) "
                f"to {subscriber_count} subscribers. Task ID: {task.id}"
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error queuing newsletter task: {str(e)}")
            )
            logger.error(f"Error queuing newsletter for post {post.id}: {str(e)}")

    def _get_newsletter_stats(self):
        """Get newsletter statistics for reporting"""
        total_subscribers = NewsletterSubscriber.objects.count()
        confirmed_subscribers = NewsletterSubscriber.objects.filter(is_confirmed=True).count()
        unconfirmed_subscribers = total_subscribers - confirmed_subscribers
        
        return {
            'total': total_subscribers,
            'confirmed': confirmed_subscribers,
            'unconfirmed': unconfirmed_subscribers
        }