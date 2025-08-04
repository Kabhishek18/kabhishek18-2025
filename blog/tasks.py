from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
from .models import NewsletterSubscriber, Post, Comment
from .performance import ViewCountOptimizer, CacheInvalidator
from .security_clean import SecurityAuditLogger
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_confirmation_email(subscriber_id):
    """
    Send confirmation email to a newsletter subscriber.
    """
    try:
        subscriber = NewsletterSubscriber.objects.get(id=subscriber_id)
        
        # Build confirmation URL
        confirmation_url = f"{settings.SITE_URL or 'http://localhost:8000'}{reverse('blog:confirm_subscription', kwargs={'token': subscriber.confirmation_token})}"
        
        # Render email templates
        html_message = render_to_string('blog/emails/confirmation_email.html', {
            'subscriber': subscriber,
            'confirmation_url': confirmation_url,
            'site_name': getattr(settings, 'SITE_NAME', 'Digital Codex'),
        })
        
        plain_message = render_to_string('blog/emails/confirmation_email.txt', {
            'subscriber': subscriber,
            'confirmation_url': confirmation_url,
            'site_name': getattr(settings, 'SITE_NAME', 'Digital Codex'),
        })
        
        # Send email
        send_mail(
            subject='Confirm your newsletter subscription',
            message=plain_message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
            recipient_list=[subscriber.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Confirmation email sent to {subscriber.email}")
        return f"Confirmation email sent to {subscriber.email}"
        
    except NewsletterSubscriber.DoesNotExist:
        logger.error(f"Newsletter subscriber with id {subscriber_id} not found")
        return f"Subscriber with id {subscriber_id} not found"
    except Exception as e:
        logger.error(f"Failed to send confirmation email to subscriber {subscriber_id}: {str(e)}")
        raise


@shared_task
def send_new_post_notification(post_id):
    """
    Send newsletter notification to all confirmed subscribers when a new post is published.
    """
    try:
        post = Post.objects.get(id=post_id, status='published')
        confirmed_subscribers = NewsletterSubscriber.objects.filter(is_confirmed=True)
        
        if not confirmed_subscribers.exists():
            logger.info("No confirmed subscribers found for newsletter notification")
            return "No confirmed subscribers found"
        
        # Build post URL
        post_url = f"{settings.SITE_URL or 'http://localhost:8000'}{reverse('blog:detail', kwargs={'slug': post.slug})}"
        
        sent_count = 0
        failed_count = 0
        
        for subscriber in confirmed_subscribers:
            try:
                # Build unsubscribe URL
                unsubscribe_url = f"{settings.SITE_URL or 'http://localhost:8000'}{reverse('blog:unsubscribe', kwargs={'token': subscriber.unsubscribe_token})}"
                
                # Render email templates
                html_message = render_to_string('blog/emails/new_post_notification.html', {
                    'post': post,
                    'subscriber': subscriber,
                    'post_url': post_url,
                    'unsubscribe_url': unsubscribe_url,
                    'site_name': getattr(settings, 'SITE_NAME', 'Digital Codex'),
                })
                
                plain_message = render_to_string('blog/emails/new_post_notification.txt', {
                    'post': post,
                    'subscriber': subscriber,
                    'post_url': post_url,
                    'unsubscribe_url': unsubscribe_url,
                    'site_name': getattr(settings, 'SITE_NAME', 'Digital Codex'),
                })
                
                # Send email
                send_mail(
                    subject=f'New post: {post.title}',
                    message=plain_message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                    recipient_list=[subscriber.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send newsletter to {subscriber.email}: {str(e)}")
                failed_count += 1
        
        logger.info(f"Newsletter sent for post '{post.title}': {sent_count} sent, {failed_count} failed")
        return f"Newsletter sent: {sent_count} sent, {failed_count} failed"
        
    except Post.DoesNotExist:
        logger.error(f"Post with id {post_id} not found or not published")
        return f"Post with id {post_id} not found or not published"
    except Exception as e:
        logger.error(f"Failed to send newsletter for post {post_id}: {str(e)}")
        raise


@shared_task
def cleanup_unconfirmed_subscriptions():
    """
    Clean up unconfirmed subscriptions older than 7 days.
    """
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        cutoff_date = timezone.now() - timedelta(days=7)
        deleted_count = NewsletterSubscriber.objects.filter(
            is_confirmed=False,
            subscribed_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} unconfirmed subscriptions")
        return f"Cleaned up {deleted_count} unconfirmed subscriptions"
        
    except Exception as e:
        logger.error(f"Failed to cleanup unconfirmed subscriptions: {str(e)}")
        raise


@shared_task
def send_comment_notification(comment_id):
    """
    Send email notification to post author when a new comment is submitted.
    """
    try:
        comment = Comment.objects.get(id=comment_id)
        post = comment.post
        post_author = post.author
        
        # Don't send notification if author doesn't have an email
        if not post_author.email:
            logger.info(f"Post author {post_author.username} has no email address")
            return "Post author has no email address"
        
        # Build post URL
        post_url = f"{settings.SITE_URL or 'http://localhost:8000'}{reverse('blog:detail', kwargs={'slug': post.slug})}"
        
        # Determine if this is a reply or a new comment
        is_reply = comment.parent is not None
        subject_prefix = "New reply" if is_reply else "New comment"
        
        # Render email content
        context = {
            'comment': comment,
            'post': post,
            'post_author': post_author,
            'post_url': post_url,
            'is_reply': is_reply,
            'site_name': getattr(settings, 'SITE_NAME', 'Digital Codex'),
        }
        
        # For now, create a simple text email (HTML template can be added later)
        message = f"""
Hello {post_author.get_full_name() or post_author.username},

{subject_prefix} has been posted on your blog post "{post.title}".

Comment by: {comment.author_name}
Email: {comment.author_email}
{'Website: ' + comment.author_website if comment.author_website else ''}

Comment:
{comment.content}

{'This is a reply to an existing comment.' if is_reply else ''}

View the full post and moderate comments here:
{post_url}

Best regards,
{getattr(settings, 'SITE_NAME', 'Digital Codex')} Team
        """.strip()
        
        # Send email
        send_mail(
            subject=f'{subject_prefix} on "{post.title}"',
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
            recipient_list=[post_author.email],
            fail_silently=False,
        )
        
        logger.info(f"Comment notification sent to {post_author.email} for comment {comment_id}")
        return f"Comment notification sent to {post_author.email}"
        
    except Comment.DoesNotExist:
        logger.error(f"Comment with id {comment_id} not found")
        return f"Comment with id {comment_id} not found"
    except Exception as e:
        logger.error(f"Failed to send comment notification for comment {comment_id}: {str(e)}")
        raise


@shared_task
def flush_view_counts():
    """
    Periodically flush buffered view counts to the database.
    This task should be run every 5-10 minutes to optimize database writes.
    """
    try:
        ViewCountOptimizer.flush_all_view_counts()
        logger.info("View counts flushed successfully")
        return "View counts flushed successfully"
    except Exception as e:
        logger.error(f"Failed to flush view counts: {str(e)}")
        raise


@shared_task
def invalidate_expired_caches():
    """
    Clean up expired cache entries and invalidate stale data.
    This task should be run periodically to maintain cache hygiene.
    """
    try:
        from django.core.cache import cache
        
        # Clear expired rate limit entries
        # Note: This is a simplified version - actual implementation would depend on cache backend
        cache.delete_pattern('rate_limit:*')
        
        # Invalidate old search results
        CacheInvalidator.invalidate_pattern('search_results')
        
        logger.info("Expired caches invalidated successfully")
        return "Expired caches invalidated successfully"
    except Exception as e:
        logger.error(f"Failed to invalidate expired caches: {str(e)}")
        raise


@shared_task
def security_audit_task():
    """
    Perform periodic security audits and cleanup.
    This task should be run daily to maintain security hygiene.
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # Clean up old unconfirmed subscriptions (older than 30 days)
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count = NewsletterSubscriber.objects.filter(
            is_confirmed=False,
            subscribed_at__lt=cutoff_date
        ).delete()[0]
        
        # Log security audit completion
        logger.info(f"Security audit completed: {deleted_count} old subscriptions cleaned up")
        
        return f"Security audit completed: {deleted_count} old subscriptions cleaned up"
    except Exception as e:
        logger.error(f"Security audit failed: {str(e)}")
        raise


@shared_task
def performance_monitoring_task():
    """
    Monitor performance metrics and log slow operations.
    This task should be run periodically to track system performance.
    """
    try:
        from django.db import connection
        from django.core.cache import cache
        
        # Get database query count (simplified monitoring)
        query_count = len(connection.queries) if hasattr(connection, 'queries') else 0
        
        # Check cache hit ratio (if supported by cache backend)
        cache_info = getattr(cache, 'get_stats', lambda: {})()
        
        # Log performance metrics
        logger.info(f"Performance monitoring: {query_count} queries, cache stats: {cache_info}")
        
        return f"Performance monitoring completed: {query_count} queries tracked"
    except Exception as e:
        logger.error(f"Performance monitoring failed: {str(e)}")
        raise


@shared_task
def cleanup_spam_attempts():
    """
    Clean up logged spam attempts and security violations.
    This task should be run weekly to prevent log bloat.
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # This is a placeholder for cleaning up spam attempt logs
        # Actual implementation would depend on how security logs are stored
        
        cutoff_date = timezone.now() - timedelta(days=7)
        
        # Clean up old rate limit violations from cache
        # Note: Actual implementation would depend on cache backend capabilities
        
        logger.info("Spam attempt cleanup completed")
        return "Spam attempt cleanup completed"
    except Exception as e:
        logger.error(f"Spam attempt cleanup failed: {str(e)}")
        raise