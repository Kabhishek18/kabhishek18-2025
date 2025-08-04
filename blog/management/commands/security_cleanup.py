"""
Management command for security cleanup and maintenance.

This command performs various security-related cleanup tasks including
removing expired tokens, cleaning up old rate limit data, and performing
security audits.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from blog.models import NewsletterSubscriber
from blog.security import SecurityAuditLogger
import logging


class Command(BaseCommand):
    help = 'Perform security cleanup and maintenance tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup-tokens',
            action='store_true',
            help='Clean up expired confirmation tokens',
        )
        parser.add_argument(
            '--cleanup-cache',
            action='store_true',
            help='Clean up expired rate limit cache entries',
        )
        parser.add_argument(
            '--audit-subscribers',
            action='store_true',
            help='Audit newsletter subscribers for suspicious patterns',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days for cleanup operations (default: 30)',
        )

    def handle(self, *args, **options):
        if options['cleanup_tokens']:
            self.cleanup_expired_tokens(options['days'])
        
        if options['cleanup_cache']:
            self.cleanup_rate_limit_cache()
        
        if options['audit_subscribers']:
            self.audit_newsletter_subscribers()
        
        if not any([options['cleanup_tokens'], options['cleanup_cache'], options['audit_subscribers']]):
            # Run all cleanup tasks by default
            self.cleanup_expired_tokens(options['days'])
            self.cleanup_rate_limit_cache()
            self.audit_newsletter_subscribers()

    def cleanup_expired_tokens(self, days):
        """Clean up expired confirmation tokens"""
        self.stdout.write(
            self.style.SUCCESS(f'Cleaning up tokens older than {days} days...')
        )
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find unconfirmed subscribers with old tokens
        expired_subscribers = NewsletterSubscriber.objects.filter(
            is_confirmed=False,
            subscribed_at__lt=cutoff_date
        )
        
        count = expired_subscribers.count()
        
        if count > 0:
            # Log the cleanup action
            logger = logging.getLogger('blog.security')
            logger.info(f'Cleaning up {count} expired newsletter subscriptions')
            
            # Delete expired unconfirmed subscriptions
            expired_subscribers.delete()
            
            self.stdout.write(
                self.style.SUCCESS(f'Cleaned up {count} expired subscriptions.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('No expired subscriptions found.')
            )

    def cleanup_rate_limit_cache(self):
        """Clean up expired rate limit cache entries"""
        self.stdout.write(
            self.style.SUCCESS('Cleaning up rate limit cache...')
        )
        
        # This is a simplified cleanup - actual implementation would depend
        # on the cache backend and its capabilities
        try:
            # Clear rate limit related cache entries
            cache.delete_pattern('rate_limit:*')
            cache.delete_pattern('view_count_buffer:*')
            
            self.stdout.write(
                self.style.SUCCESS('Rate limit cache cleanup complete.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Cache cleanup failed: {e}')
            )

    def audit_newsletter_subscribers(self):
        """Audit newsletter subscribers for suspicious patterns"""
        self.stdout.write(
            self.style.SUCCESS('Auditing newsletter subscribers...')
        )
        
        # Check for suspicious email patterns
        suspicious_patterns = [
            '@tempmail.',
            '@10minutemail.',
            '@guerrillamail.',
            '@mailinator.',
            '@throwaway.',
        ]
        
        suspicious_count = 0
        
        for pattern in suspicious_patterns:
            suspicious_subscribers = NewsletterSubscriber.objects.filter(
                email__icontains=pattern
            )
            
            count = suspicious_subscribers.count()
            if count > 0:
                suspicious_count += count
                self.stdout.write(
                    self.style.WARNING(
                        f'Found {count} subscribers with pattern "{pattern}"'
                    )
                )
                
                # Log suspicious subscribers
                logger = logging.getLogger('blog.security')
                for subscriber in suspicious_subscribers:
                    logger.warning(
                        f'Suspicious email pattern detected: {subscriber.email}'
                    )
        
        # Check for rapid subscriptions from same IP (would need IP tracking)
        # This is a placeholder for more advanced auditing
        
        if suspicious_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No suspicious subscribers found.')
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'Found {suspicious_count} potentially suspicious subscribers.'
                )
            )