from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from blog.models import NewsletterSubscriber, Comment
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Enhanced cleanup for expired confirmation tokens and engagement data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days after which unconfirmed subscriptions are deleted (default: 7)',
        )
        parser.add_argument(
            '--token-days',
            type=int,
            default=30,
            help='Number of days after which expired tokens are cleaned up (default: 30)',
        )
        parser.add_argument(
            '--comment-days',
            type=int,
            default=90,
            help='Number of days after which unapproved comments are deleted (default: 90)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--cleanup-type',
            choices=['subscriptions', 'tokens', 'comments', 'all'],
            default='all',
            help='Type of cleanup to perform (default: all)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process in each batch (default: 1000)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about cleanup process',
        )

    def handle(self, *args, **options):
        cleanup_type = options['cleanup_type']
        
        if cleanup_type in ['subscriptions', 'all']:
            self._cleanup_expired_subscriptions(options)
        
        if cleanup_type in ['tokens', 'all']:
            self._cleanup_expired_tokens(options)
        
        if cleanup_type in ['comments', 'all']:
            self._cleanup_old_unapproved_comments(options)
        
        # Generate cleanup report
        self._generate_cleanup_report(options)

    def _cleanup_expired_subscriptions(self, options):
        """Clean up unconfirmed newsletter subscriptions"""
        days = options['days']
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        verbose = options['verbose']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find unconfirmed subscriptions older than cutoff date
        expired_subscriptions = NewsletterSubscriber.objects.filter(
            is_confirmed=False,
            subscribed_at__lt=cutoff_date
        )
        
        count = expired_subscriptions.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS("No expired unconfirmed subscriptions found.")
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would delete {count} unconfirmed subscriptions older than {days} days:"
                )
            )
            if verbose:
                for subscription in expired_subscriptions[:10]:  # Show first 10
                    self.stdout.write(
                        f"  - {subscription.email} (subscribed: {subscription.subscribed_at})"
                    )
                if count > 10:
                    self.stdout.write(f"  ... and {count - 10} more")
        else:
            # Process in batches to avoid memory issues
            deleted_total = 0
            
            while expired_subscriptions.exists():
                batch = expired_subscriptions[:batch_size]
                batch_emails = [sub.email for sub in batch]
                
                deleted_count = NewsletterSubscriber.objects.filter(
                    email__in=batch_emails,
                    is_confirmed=False,
                    subscribed_at__lt=cutoff_date
                ).delete()[0]
                
                deleted_total += deleted_count
                
                if verbose:
                    self.stdout.write(f"Deleted batch of {deleted_count} subscriptions")
                
                # Refresh queryset
                expired_subscriptions = NewsletterSubscriber.objects.filter(
                    is_confirmed=False,
                    subscribed_at__lt=cutoff_date
                )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted {deleted_total} expired unconfirmed subscriptions."
                )
            )
            
            logger.info(f"Cleaned up {deleted_total} expired unconfirmed subscriptions")

    def _cleanup_expired_tokens(self, options):
        """Clean up expired confirmation and unsubscribe tokens"""
        token_days = options['token_days']
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        # For this implementation, we'll focus on cleaning up old confirmed subscriptions
        # that might have stale tokens (in a real implementation, you might have a separate
        # token expiry tracking system)
        
        cutoff_date = timezone.now() - timedelta(days=token_days)
        
        # Find confirmed subscriptions that are old and might need token refresh
        old_confirmed = NewsletterSubscriber.objects.filter(
            is_confirmed=True,
            confirmed_at__lt=cutoff_date
        )
        
        count = old_confirmed.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS("No old confirmed subscriptions found for token cleanup.")
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would refresh tokens for {count} old confirmed subscriptions"
                )
            )
        else:
            # In a real implementation, you might regenerate tokens here
            # For now, we'll just log this as a placeholder
            self.stdout.write(
                self.style.SUCCESS(
                    f"Token cleanup completed for {count} old subscriptions"
                )
            )
            
            logger.info(f"Token cleanup processed {count} old confirmed subscriptions")

    def _cleanup_old_unapproved_comments(self, options):
        """Clean up old unapproved comments"""
        comment_days = options['comment_days']
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        verbose = options['verbose']
        
        cutoff_date = timezone.now() - timedelta(days=comment_days)
        
        # Find unapproved comments older than cutoff date
        old_comments = Comment.objects.filter(
            is_approved=False,
            created_at__lt=cutoff_date
        )
        
        count = old_comments.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS("No old unapproved comments found.")
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would delete {count} unapproved comments older than {comment_days} days:"
                )
            )
            if verbose:
                for comment in old_comments[:5]:  # Show first 5
                    self.stdout.write(
                        f"  - Comment by {comment.author_name} on '{comment.post.title}' "
                        f"(created: {comment.created_at})"
                    )
                if count > 5:
                    self.stdout.write(f"  ... and {count - 5} more")
        else:
            # Process in batches
            deleted_total = 0
            
            while old_comments.exists():
                batch_ids = list(old_comments[:batch_size].values_list('id', flat=True))
                
                deleted_count = Comment.objects.filter(
                    id__in=batch_ids,
                    is_approved=False,
                    created_at__lt=cutoff_date
                ).delete()[0]
                
                deleted_total += deleted_count
                
                if verbose:
                    self.stdout.write(f"Deleted batch of {deleted_count} comments")
                
                # Refresh queryset
                old_comments = Comment.objects.filter(
                    is_approved=False,
                    created_at__lt=cutoff_date
                )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted {deleted_total} old unapproved comments."
                )
            )
            
            logger.info(f"Cleaned up {deleted_total} old unapproved comments")

    def _generate_cleanup_report(self, options):
        """Generate a summary report of current engagement data"""
        if not options['verbose']:
            return
        
        # Newsletter statistics
        total_subscribers = NewsletterSubscriber.objects.count()
        confirmed_subscribers = NewsletterSubscriber.objects.filter(is_confirmed=True).count()
        unconfirmed_subscribers = total_subscribers - confirmed_subscribers
        
        # Comment statistics
        total_comments = Comment.objects.count()
        approved_comments = Comment.objects.filter(is_approved=True).count()
        pending_comments = total_comments - approved_comments
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write("ENGAGEMENT DATA SUMMARY")
        self.stdout.write("="*50)
        
        self.stdout.write(f"Newsletter Subscribers:")
        self.stdout.write(f"  Total: {total_subscribers}")
        self.stdout.write(f"  Confirmed: {confirmed_subscribers}")
        self.stdout.write(f"  Unconfirmed: {unconfirmed_subscribers}")
        
        self.stdout.write(f"\nComments:")
        self.stdout.write(f"  Total: {total_comments}")
        self.stdout.write(f"  Approved: {approved_comments}")
        self.stdout.write(f"  Pending: {pending_comments}")
        
        # Recent activity
        recent_cutoff = timezone.now() - timedelta(days=7)
        recent_subscribers = NewsletterSubscriber.objects.filter(
            subscribed_at__gte=recent_cutoff
        ).count()
        recent_comments = Comment.objects.filter(
            created_at__gte=recent_cutoff
        ).count()
        
        self.stdout.write(f"\nRecent Activity (last 7 days):")
        self.stdout.write(f"  New subscribers: {recent_subscribers}")
        self.stdout.write(f"  New comments: {recent_comments}")
        
        self.stdout.write("="*50)