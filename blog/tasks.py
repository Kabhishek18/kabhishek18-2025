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
from django.core.management import call_command
from django.utils import timezone

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




@shared_task(name="blog.tasks.generate_ai_blog_post")
def generate_ai_blog_post(publish=True, count=1):
    """
    A Celery task that calls the aicontent management command.
    
    This task can be configured from the Django Admin in Celery Beat
    by passing arguments in the 'Arguments' field, e.g., [false, 5]
    to create 5 draft posts.
    """
    print(f"[{timezone.now()}] Running AI blog post generation task...")
    
    try:
        # This is the corrected way to call the command with a boolean flag.
        call_command('aicontent', 'create_post', publish=publish, count=count)
        
        result_message = f"AI content generation command executed successfully. Created {count} post(s) with publish={publish}."
        print(result_message)
        return result_message
    except Exception as e:
        # It's good practice to log errors in scheduled tasks.
        error_message = f"An error occurred during AI content generation: {e}"
        print(error_message)
        return error_message


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def post_to_linkedin(self, post_id):
    """
    Celery task for posting blog content to LinkedIn asynchronously.
    
    This task handles:
    - Authentication with LinkedIn API
    - Content formatting and posting
    - Error handling with exponential backoff
    - Status tracking and monitoring
    
    Args:
        post_id (int): ID of the blog post to share on LinkedIn
        
    Returns:
        dict: Result information including success status and details
        
    Raises:
        Retry: If the task should be retried due to temporary failures
    """
    from .models import Post
    from .linkedin_models import LinkedInPost, LinkedInConfig
    from .services.linkedin_service import LinkedInAPIService, LinkedInAPIError
    from .services.linkedin_task_monitor import LinkedInTaskMonitor
    from django.utils import timezone
    from datetime import timedelta
    import time
    
    task_start_time = timezone.now()
    monitor = LinkedInTaskMonitor()
    
    logger.info(f"Starting LinkedIn posting task for post ID {post_id} (attempt {self.request.retries + 1})")
    
    try:
        # Get the blog post
        try:
            blog_post = Post.objects.get(id=post_id, status='published')
        except Post.DoesNotExist:
            error_msg = f"Blog post with ID {post_id} not found or not published"
            logger.error(error_msg)
            result = {
                'success': False,
                'error': error_msg,
                'post_id': post_id,
                'task_duration': (timezone.now() - task_start_time).total_seconds()
            }
            monitor.log_task_completion(result)
            return result
        
        # Check if LinkedIn integration is configured
        linkedin_config = LinkedInConfig.get_active_config()
        if not linkedin_config or not linkedin_config.is_active:
            error_msg = "LinkedIn integration is not configured or inactive"
            logger.warning(error_msg)
            result = {
                'success': False,
                'error': error_msg,
                'post_id': post_id,
                'skipped': True,
                'task_duration': (timezone.now() - task_start_time).total_seconds()
            }
            monitor.log_task_completion(result)
            return result
        
        # Get or create LinkedIn post tracking record
        linkedin_post, created = LinkedInPost.objects.get_or_create(
            post=blog_post,
            defaults={'status': 'pending'}
        )
        
        # Check if already successfully posted
        if linkedin_post.is_successful():
            logger.info(f"Blog post '{blog_post.title}' already successfully posted to LinkedIn")
            result = {
                'success': True,
                'already_posted': True,
                'post_id': post_id,
                'linkedin_post_id': linkedin_post.linkedin_post_id,
                'linkedin_post_url': linkedin_post.linkedin_post_url,
                'task_duration': (timezone.now() - task_start_time).total_seconds()
            }
            monitor.log_task_completion(result)
            return result
        
        # Update status to indicate posting is in progress
        linkedin_post.status = 'pending'
        linkedin_post.save(update_fields=['status'])
        
        # Initialize LinkedIn API service
        linkedin_service = LinkedInAPIService(config=linkedin_config)
        
        try:
            # Attempt to post to LinkedIn with current attempt count
            result_linkedin_post = linkedin_service.post_blog_article(blog_post, attempt_count=self.request.retries + 1)
            
            # Task completed successfully
            task_duration = (timezone.now() - task_start_time).total_seconds()
            success_result = {
                'success': True,
                'post_id': post_id,
                'blog_title': blog_post.title,
                'linkedin_post_id': result_linkedin_post.linkedin_post_id,
                'linkedin_post_url': result_linkedin_post.linkedin_post_url,
                'attempt_count': result_linkedin_post.attempt_count,
                'task_duration': task_duration,
                'used_fallback': 'fallback' in (result_linkedin_post.error_message or '')
            }
            
            logger.info(f"Successfully posted blog post '{blog_post.title}' to LinkedIn in {task_duration:.2f}s")
            monitor.log_task_completion(success_result)
            return success_result
            
        except (LinkedInAPIError, LinkedInAuthenticationError, LinkedInRateLimitError, LinkedInContentError) as e:
            # Handle LinkedIn API specific errors with enhanced error handling
            error_context = {
                'error_type': type(e).__name__,
                'error_message': e.message,
                'error_code': getattr(e, 'error_code', None),
                'status_code': getattr(e, 'status_code', None),
                'is_retryable': getattr(e, 'is_retryable', False),
                'retry_after': getattr(e, 'retry_after', None)
            }
            
            logger.error(f"LinkedIn API error for post '{blog_post.title}': {error_context}")
            
            # Enhanced retry logic based on error type
            should_retry = _should_retry_enhanced(e, self.request.retries)
            
            if should_retry and self.request.retries < self.max_retries:
                # Calculate retry delay based on error type
                retry_delay = _calculate_enhanced_retry_delay(e, self.request.retries)
                
                logger.info(f"Retrying LinkedIn post for '{blog_post.title}' in {retry_delay} seconds (attempt {self.request.retries + 2})")
                
                # Update LinkedIn post status for retry
                linkedin_post.status = 'retrying'
                linkedin_post.next_retry_at = timezone.now() + timedelta(seconds=retry_delay)
                linkedin_post.error_message = f"{e.message} (will retry in {retry_delay}s)"
                linkedin_post.save(update_fields=['status', 'next_retry_at', 'error_message'])
                
                # Retry the task with calculated delay
                raise self.retry(countdown=retry_delay, exc=e)
            else:
                # Mark as permanently failed with detailed error information
                linkedin_post.mark_as_failed(
                    error_message=f"{e.message} (Error Type: {type(e).__name__})",
                    error_code=getattr(e, 'error_code', None),
                    can_retry=False
                )
                
                task_duration = (timezone.now() - task_start_time).total_seconds()
                failure_result = {
                    'success': False,
                    'error': e.message,
                    'error_code': getattr(e, 'error_code', None),
                    'error_type': type(e).__name__,
                    'post_id': post_id,
                    'blog_title': blog_post.title,
                    'final_failure': True,
                    'attempt_count': self.request.retries + 1,
                    'task_duration': task_duration,
                    'error_context': error_context
                }
                monitor.log_task_completion(failure_result)
                return failure_result
        
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error posting to LinkedIn for '{blog_post.title}': {str(e)}")
            
            if self.request.retries < self.max_retries:
                # Retry for unexpected errors
                retry_delay = _calculate_retry_delay(self.request.retries)
                
                logger.info(f"Retrying LinkedIn post for '{blog_post.title}' due to unexpected error in {retry_delay} seconds")
                
                # Update LinkedIn post status
                linkedin_post.status = 'retrying'
                linkedin_post.next_retry_at = timezone.now() + timedelta(seconds=retry_delay)
                linkedin_post.save(update_fields=['status', 'next_retry_at'])
                
                raise self.retry(countdown=retry_delay, exc=e)
            else:
                # Mark as permanently failed
                linkedin_post.mark_as_failed(
                    error_message=str(e),
                    can_retry=False
                )
                
                task_duration = (timezone.now() - task_start_time).total_seconds()
                failure_result = {
                    'success': False,
                    'error': str(e),
                    'post_id': post_id,
                    'blog_title': blog_post.title,
                    'final_failure': True,
                    'attempt_count': self.request.retries + 1,
                    'task_duration': task_duration
                }
                monitor.log_task_completion(failure_result)
                return failure_result
    
    except Exception as e:
        # Handle task-level errors (database issues, etc.)
        logger.error(f"Task-level error in LinkedIn posting for post ID {post_id}: {str(e)}")
        
        task_duration = (timezone.now() - task_start_time).total_seconds()
        error_result = {
            'success': False,
            'error': f"Task error: {str(e)}",
            'post_id': post_id,
            'task_level_error': True,
            'task_duration': task_duration
        }
        monitor.log_task_completion(error_result)
        return error_result


@shared_task
def retry_failed_linkedin_posts():
    """
    Celery task to retry LinkedIn posts that are ready for retry.
    
    This task should be run periodically (e.g., every 15 minutes) to check
    for posts that are ready to be retried based on their retry schedule.
    
    Returns:
        dict: Summary of retry attempts
    """
    from .linkedin_models import LinkedInPost
    from django.utils import timezone
    
    logger.info("Starting retry of failed LinkedIn posts")
    
    # Get posts ready for retry
    posts_to_retry = LinkedInPost.get_posts_ready_for_retry()
    
    if not posts_to_retry.exists():
        logger.info("No LinkedIn posts ready for retry")
        return {
            'posts_checked': 0,
            'posts_retried': 0,
            'message': 'No posts ready for retry'
        }
    
    retry_count = 0
    for linkedin_post in posts_to_retry:
        try:
            # Trigger the main posting task for retry
            post_to_linkedin.delay(linkedin_post.post.id)
            retry_count += 1
            
            logger.info(f"Queued retry for LinkedIn post: {linkedin_post.post.title}")
            
        except Exception as e:
            logger.error(f"Failed to queue retry for LinkedIn post {linkedin_post.id}: {str(e)}")
    
    result = {
        'posts_checked': posts_to_retry.count(),
        'posts_retried': retry_count,
        'message': f'Queued {retry_count} posts for retry'
    }
    
    logger.info(f"LinkedIn retry task completed: {result['message']}")
    return result


@shared_task
def cleanup_old_linkedin_posts():
    """
    Celery task to clean up old LinkedIn post tracking records.
    
    This task removes successful LinkedIn post records older than 90 days
    and failed records older than 30 days to prevent database bloat.
    
    Returns:
        dict: Summary of cleanup operations
    """
    from .linkedin_models import LinkedInPost
    from django.utils import timezone
    from datetime import timedelta
    
    logger.info("Starting cleanup of old LinkedIn post records")
    
    now = timezone.now()
    
    # Clean up successful posts older than 90 days
    successful_cutoff = now - timedelta(days=90)
    successful_deleted = LinkedInPost.objects.filter(
        status='success',
        posted_at__lt=successful_cutoff
    ).delete()[0]
    
    # Clean up failed posts older than 30 days
    failed_cutoff = now - timedelta(days=30)
    failed_deleted = LinkedInPost.objects.filter(
        status='failed',
        created_at__lt=failed_cutoff
    ).delete()[0]
    
    result = {
        'successful_posts_deleted': successful_deleted,
        'failed_posts_deleted': failed_deleted,
        'total_deleted': successful_deleted + failed_deleted
    }
    
    logger.info(f"LinkedIn cleanup completed: deleted {result['total_deleted']} records")
    return result


def _should_retry_linkedin_error(error: 'LinkedInAPIError') -> bool:
    """
    Determine if a LinkedIn API error should trigger a retry.
    
    Args:
        error: LinkedInAPIError instance
        
    Returns:
        bool: True if the error is retryable
    """
    # Don't retry client errors (4xx status codes)
    if error.status_code and 400 <= error.status_code < 500:
        # Exception: retry rate limiting (429)
        if error.status_code == 429:
            return True
        # Exception: retry authentication errors that might be token expiration
        if error.status_code == 401:
            return True
        return False
    
    # Retry server errors (5xx) and network errors
    if error.status_code and error.status_code >= 500:
        return True
    
    # Retry specific error codes that are known to be temporary
    retryable_codes = [
        'RATE_LIMIT_EXCEEDED',
        'INTERNAL_SERVER_ERROR',
        'SERVICE_UNAVAILABLE',
        'TIMEOUT'
    ]
    
    if error.error_code in retryable_codes:
        return True
    
    # Default to not retrying unknown errors
    return False


# Enhanced retry logic methods for the Celery task
def _should_retry_enhanced(error, current_retries):
    """
    Enhanced retry logic that considers error type and attempt count.
    
    Args:
        error: LinkedIn API error instance
        current_retries: Current number of retries
        
    Returns:
        bool: True if should retry
    """
    from .services.linkedin_service import (
        LinkedInAPIError, LinkedInAuthenticationError, 
        LinkedInRateLimitError, LinkedInContentError
    )
    
    # Content errors are generally not retryable
    if isinstance(error, LinkedInContentError):
        return False
    
    # Rate limit errors are retryable but with longer delays
    if isinstance(error, LinkedInRateLimitError):
        return current_retries < 2  # Limit rate limit retries
    
    # Authentication errors - retry once to attempt token refresh
    if isinstance(error, LinkedInAuthenticationError):
        if hasattr(error, 'needs_reauth') and error.needs_reauth:
            return False  # Don't retry if re-authentication is needed
        return current_retries < 1  # Only retry once for auth errors
    
    # Use the error's is_retryable property if available
    if hasattr(error, 'is_retryable'):
        return error.is_retryable and current_retries < 3
    
    # Fallback to original logic
    return _should_retry_linkedin_error(error)


def _calculate_enhanced_retry_delay(error, retry_count):
    """
    Calculate retry delay based on error type and attempt count.
    
    Args:
        error: LinkedIn API error instance
        retry_count: Current retry attempt (0-based)
        
    Returns:
        int: Delay in seconds
    """
    from .services.linkedin_service import (
        LinkedInRateLimitError, LinkedInAuthenticationError
    )
    import random
    
    # Rate limit errors - use the retry_after if provided
    if isinstance(error, LinkedInRateLimitError):
        if hasattr(error, 'retry_after') and error.retry_after:
            # Add some jitter to avoid thundering herd
            jitter = random.uniform(0.8, 1.2)
            return int(error.retry_after * jitter)
        else:
            # Default rate limit delay
            return 3600 + random.randint(0, 600)  # 1 hour + up to 10 minutes jitter
    
    # Authentication errors - shorter delay for token refresh
    if isinstance(error, LinkedInAuthenticationError):
        return 300 + random.randint(0, 120)  # 5 minutes + up to 2 minutes jitter
    
    # Default exponential backoff with jitter
    base_delay = 60  # 1 minute base
    exponential_delay = base_delay * (2 ** retry_count)
    jitter = random.uniform(-0.25, 0.25) * exponential_delay
    
    # Ensure minimum delay of 30 seconds and maximum of 1800 seconds (30 minutes)
    final_delay = max(30, min(1800, int(exponential_delay + jitter)))
    
    return final_delay


@shared_task
def monitor_linkedin_health():
    """
    Celery task to monitor LinkedIn integration health and generate alerts.
    
    This task should be run periodically (e.g., every 30 minutes) to:
    - Check overall system health
    - Monitor failure rates
    - Generate alerts for critical issues
    - Log health metrics
    
    Returns:
        dict: Health monitoring results
    """
    from .services.linkedin_task_monitor import LinkedInTaskMonitor
    
    logger.info("Starting LinkedIn health monitoring task")
    
    monitor = LinkedInTaskMonitor()
    
    try:
        # Get overall health status
        health_status = monitor.get_health_status()
        
        # Check for high failure rates
        failure_alert = monitor.alert_on_failures(threshold_percentage=50.0, time_window_hours=1)
        
        # Get retry queue status
        retry_status = monitor.get_retry_queue_status()
        
        # Log health metrics with comprehensive details
        logger.info(f"LinkedIn health check: {health_status['overall_health']} (score: {health_status['health_score']})")
        
        # Log configuration issues
        config_status = health_status.get('configuration_status', {})
        if config_status.get('issues'):
            for issue in config_status['issues']:
                logger.warning(f"LinkedIn configuration issue: {issue}")
        
        # Log performance metrics
        recent_performance = health_status.get('recent_performance', {})
        if recent_performance.get('total_posts', 0) > 0:
            success_rate = recent_performance.get('success_rate', 0)
            logger.info(f"LinkedIn recent performance: {success_rate}% success rate over {recent_performance.get('total_posts')} posts")
            
            # Log error breakdown
            error_breakdown = recent_performance.get('error_breakdown', {})
            if error_breakdown.get('by_category'):
                logger.info(f"LinkedIn error categories: {error_breakdown['by_category']}")
        
        # Generate alerts for critical issues
        if health_status['overall_health'] == 'critical':
            logger.critical(f"LinkedIn integration in critical state: {config_status.get('issues', [])}")
        elif health_status['overall_health'] == 'warning':
            logger.warning(f"LinkedIn integration has warnings: {config_status.get('issues', [])}")
        
        if failure_alert:
            logger.critical(
                f"LinkedIn high failure rate alert: {failure_alert['failure_rate']}% failures "
                f"in last {failure_alert['time_window_hours']} hours "
                f"({failure_alert['failed_posts']}/{failure_alert['total_posts']} posts failed)"
            )
        
        # Log retry queue status
        if retry_status['ready_for_retry'] > 0:
            logger.info(f"LinkedIn retry queue: {retry_status['ready_for_retry']} posts ready for retry")
        
        if retry_status['total_retrying'] > retry_status['ready_for_retry']:
            pending_retries = retry_status['total_retrying'] - retry_status['ready_for_retry']
            logger.info(f"LinkedIn retry queue: {pending_retries} posts scheduled for future retry")
        
        return {
            'health_status': health_status,
            'failure_alert': failure_alert,
            'retry_status': retry_status,
            'monitoring_completed_at': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"LinkedIn health monitoring task failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'monitoring_completed_at': timezone.now().isoformat()
        }


@shared_task
def comprehensive_error_audit():
    """
    Comprehensive error audit task for LinkedIn integration.
    
    This task performs detailed analysis of all error scenarios and generates
    comprehensive reports for troubleshooting and system improvement.
    
    Returns:
        dict: Comprehensive error audit results
    """
    from .linkedin_models import LinkedInPost, LinkedInConfig
    from .services.linkedin_task_monitor import LinkedInTaskMonitor
    from datetime import timedelta
    
    logger.info("Starting comprehensive LinkedIn error audit")
    
    try:
        audit_results = {
            'audit_timestamp': timezone.now().isoformat(),
            'configuration_audit': {},
            'error_pattern_analysis': {},
            'performance_analysis': {},
            'recommendations': []
        }
        
        # Configuration audit
        config = LinkedInConfig.get_active_config()
        if config:
            validation_results = config.validate_credentials()
            credential_status = config.get_credential_status()
            
            audit_results['configuration_audit'] = {
                'config_id': config.id,
                'is_active': config.is_active,
                'validation_results': validation_results,
                'credential_status': credential_status,
                'last_updated': config.updated_at.isoformat()
            }
            
            # Log configuration issues
            if validation_results['errors']:
                logger.error(f"LinkedIn configuration validation errors: {validation_results['errors']}")
                audit_results['recommendations'].append("Fix credential validation errors")
            
            if credential_status['token_expired']:
                logger.warning("LinkedIn access token has expired")
                audit_results['recommendations'].append("Refresh LinkedIn access token")
        else:
            logger.error("No active LinkedIn configuration found")
            audit_results['recommendations'].append("Configure LinkedIn integration")
        
        # Error pattern analysis
        monitor = LinkedInTaskMonitor()
        
        # Analyze last 7 days
        weekly_stats = monitor.get_task_statistics(hours=168)  # 7 days
        audit_results['error_pattern_analysis'] = weekly_stats
        
        # Analyze error trends
        if weekly_stats['total_posts'] > 0:
            failure_rate = 100 - weekly_stats['success_rate']
            
            if failure_rate > 20:
                logger.warning(f"High LinkedIn failure rate detected: {failure_rate}%")
                audit_results['recommendations'].append(f"Investigate high failure rate: {failure_rate}%")
            
            # Analyze specific error patterns
            error_breakdown = weekly_stats.get('error_breakdown', {})
            top_errors = error_breakdown.get('by_category', {})
            
            for error_type, count in top_errors.items():
                if count > 5:  # More than 5 occurrences
                    logger.warning(f"Frequent LinkedIn error type '{error_type}': {count} occurrences")
                    
                    if error_type == 'authentication':
                        audit_results['recommendations'].append("Check LinkedIn API credentials and permissions")
                    elif error_type == 'rate_limiting':
                        audit_results['recommendations'].append("Implement better rate limiting strategy")
                    elif error_type == 'network':
                        audit_results['recommendations'].append("Investigate network connectivity issues")
                    elif error_type == 'content_validation':
                        audit_results['recommendations'].append("Review content formatting and validation")
        
        # Performance analysis
        performance_metrics = weekly_stats.get('performance_metrics', {})
        audit_results['performance_analysis'] = performance_metrics
        
        if performance_metrics.get('first_attempt_success_rate', 0) < 80:
            logger.warning(f"Low first-attempt success rate: {performance_metrics.get('first_attempt_success_rate', 0)}%")
            audit_results['recommendations'].append("Improve first-attempt success rate")
        
        # Analyze retry patterns
        retry_status = monitor.get_retry_queue_status()
        if retry_status['total_retrying'] > 10:
            logger.warning(f"High number of posts in retry queue: {retry_status['total_retrying']}")
            audit_results['recommendations'].append("Investigate causes of frequent retries")
        
        # Log audit summary
        logger.info(f"LinkedIn error audit completed: {len(audit_results['recommendations'])} recommendations generated")
        
        if audit_results['recommendations']:
            logger.info(f"LinkedIn audit recommendations: {audit_results['recommendations']}")
        
        return audit_results
        
    except Exception as e:
        logger.error(f"Comprehensive LinkedIn error audit failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'audit_timestamp': timezone.now().isoformat()
        }


def _calculate_retry_delay(retry_count: int) -> int:
    """
    Calculate retry delay with exponential backoff and jitter.
    
    Args:
        retry_count: Current retry attempt (0-based)
        
    Returns:
        int: Delay in seconds
    """
    import random
    
    # Base delay: 60 seconds
    base_delay = 60
    
    # Exponential backoff: 60s, 120s, 240s
    exponential_delay = base_delay * (2 ** retry_count)
    
    # Add jitter (±25% of the delay)
    jitter = random.uniform(-0.25, 0.25) * exponential_delay
    
    # Ensure minimum delay of 30 seconds and maximum of 600 seconds (10 minutes)
    final_delay = max(30, min(600, int(exponential_delay + jitter)))
    
    return final_delay


# LinkedIn image monitoring tasks - moved inline to avoid import issues


@shared_task(bind=True, max_retries=3)
def cleanup_linkedin_image_metrics(self):
    """
    Periodic task to clean up old LinkedIn image processing metrics.
    
    This task should be run daily to prevent cache bloat and maintain
    system performance.
    """
    try:
        logger.info("Starting LinkedIn image metrics cleanup")
        # Basic cleanup logic - can be expanded later
        from blog.linkedin_models import LinkedInPost
        from django.utils import timezone
        from datetime import timedelta
        
        # Clean up old failed posts that can't be retried
        cutoff_date = timezone.now() - timedelta(days=30)
        old_failed_posts = LinkedInPost.objects.filter(
            status='failed',
            created_at__lt=cutoff_date,
            attempt_count__gte=3
        )
        
        deleted_count = old_failed_posts.count()
        old_failed_posts.delete()
        
        logger.info(f"LinkedIn image metrics cleanup completed - removed {deleted_count} old records")
        return f"Metrics cleanup completed - removed {deleted_count} records"
    except Exception as e:
        logger.error(f"Error during LinkedIn image metrics cleanup: {str(e)}")
        raise self.retry(exc=e, countdown=300)  # Retry after 5 minutes


@shared_task(bind=True, max_retries=2)
def monitor_linkedin_image_health(self):
    """
    Periodic task to monitor LinkedIn image processing health and send alerts.
    
    This task should be run every hour to monitor system health and
    send alerts when issues are detected.
    """
    try:
        logger.info("Starting LinkedIn image health monitoring")
        
        from blog.linkedin_models import LinkedInPost, LinkedInConfig
        from django.utils import timezone
        from datetime import timedelta
        
        # Check if LinkedIn integration is configured
        config = LinkedInConfig.get_active_config()
        if not config:
            logger.warning("No active LinkedIn configuration found")
            return "No LinkedIn configuration"
        
        # Get recent posts (last 24 hours)
        recent_cutoff = timezone.now() - timedelta(hours=24)
        recent_posts = LinkedInPost.objects.filter(created_at__gte=recent_cutoff)
        
        total_posts = recent_posts.count()
        if total_posts == 0:
            logger.info("No recent LinkedIn posts to monitor")
            return "No recent posts"
        
        # Calculate success/failure rates
        successful_posts = recent_posts.filter(status='success').count()
        failed_posts = recent_posts.filter(status='failed').count()
        success_rate = (successful_posts / total_posts) * 100 if total_posts > 0 else 0
        
        # Log health status
        logger.info(f"LinkedIn health check - Total: {total_posts}, Success: {successful_posts}, Failed: {failed_posts}, Success Rate: {success_rate:.1f}%")
        
        # Send alert if success rate is low
        if success_rate < 50 and total_posts >= 5:  # Only alert if we have enough data
            logger.warning(f"Low LinkedIn success rate detected: {success_rate:.1f}%")
            # Could send email alert here if configured
        
        return f"Health monitoring completed - Success rate: {success_rate:.1f}%"
        
    except Exception as e:
        logger.error(f"Error during LinkedIn image health monitoring: {str(e)}")
        raise self.retry(exc=e, countdown=600)  # Retry after 10 minutes


@shared_task(bind=True, max_retries=3)
def generate_daily_linkedin_report(self):
    """
    Generate and send daily LinkedIn image processing report.
    
    This task should be run once daily to provide a summary of
    LinkedIn image processing activities.
    """
    try:
        logger.info("Generating daily LinkedIn image processing report")
        
        from blog.linkedin_models import LinkedInPost
        from django.utils import timezone
        from datetime import timedelta
        
        # Get posts from last 24 hours
        yesterday = timezone.now() - timedelta(hours=24)
        recent_posts = LinkedInPost.objects.filter(created_at__gte=yesterday)
        
        # Calculate statistics
        total_posts = recent_posts.count()
        successful_posts = recent_posts.filter(status='success').count()
        failed_posts = recent_posts.filter(status='failed').count()
        pending_posts = recent_posts.filter(status='pending').count()
        
        # Image-specific statistics
        posts_with_images = recent_posts.filter(image_upload_status='success').count()
        image_failures = recent_posts.filter(image_upload_status='failed').count()
        
        success_rate = (successful_posts / total_posts * 100) if total_posts > 0 else 0
        image_success_rate = (posts_with_images / (posts_with_images + image_failures) * 100) if (posts_with_images + image_failures) > 0 else 0
        
        # Create report
        report_data = {
            'date': timezone.now().strftime('%Y-%m-%d'),
            'total_posts': total_posts,
            'successful_posts': successful_posts,
            'failed_posts': failed_posts,
            'pending_posts': pending_posts,
            'success_rate': success_rate,
            'posts_with_images': posts_with_images,
            'image_failures': image_failures,
            'image_success_rate': image_success_rate
        }
        
        logger.info(f"Daily LinkedIn report generated: {report_data}")
        return f"Daily report generated - Success rate: {success_rate:.1f}%"
        
    except Exception as e:
        logger.error(f"Error generating daily LinkedIn report: {str(e)}")
        raise self.retry(exc=e, countdown=1800)  # Retry after 30 minutes


@shared_task(bind=True, max_retries=2)
def retry_failed_image_uploads(self):
    """
    Periodic task to retry failed image uploads that can be retried.
    
    This task should be run every few hours to automatically retry
    failed uploads that may have been caused by temporary issues.
    """
    try:
        from blog.linkedin_models import LinkedInPost, LinkedInConfig
        from blog.services.linkedin_service import LinkedInAPIService
        
        logger.info("Starting automatic retry of failed LinkedIn image uploads")
        
        # Get LinkedIn configuration
        config = LinkedInConfig.get_active_config()
        if not config:
            logger.warning("No active LinkedIn configuration found")
            return "No LinkedIn configuration"
        
        # Find posts that can be retried
        failed_posts = LinkedInPost.objects.filter(
            status__in=['failed', 'retrying'],
            image_upload_status='failed'
        )
        
        # Filter posts that can actually be retried
        retryable_posts = [post for post in failed_posts if post.can_retry()]
        
        if not retryable_posts:
            logger.info("No failed posts available for retry")
            return "No posts to retry"
        
        # Limit the number of retries per run
        max_retries_per_run = 2
        posts_to_retry = retryable_posts[:max_retries_per_run]
        
        service = LinkedInAPIService(config)
        retry_count = 0
        success_count = 0
        
        for linkedin_post in posts_to_retry:
            try:
                logger.info(f"Retrying LinkedIn post for blog post: {linkedin_post.post.title}")
                
                # Reset status and retry
                linkedin_post.mark_as_pending()
                result = service.post_blog_article(linkedin_post.post)
                retry_count += 1
                
                if result.is_successful():
                    success_count += 1
                    logger.info(f"Successfully retried LinkedIn post for: {linkedin_post.post.title}")
                else:
                    logger.warning(f"Retry failed for LinkedIn post: {linkedin_post.post.title} - {result.error_message}")
                
            except Exception as e:
                logger.error(f"Error retrying LinkedIn post for {linkedin_post.post.title}: {str(e)}")
        
        logger.info(f"Automatic retry completed - Attempted: {retry_count}, Successful: {success_count}")
        return f"Retried {retry_count} posts, {success_count} successful"
        
    except Exception as e:
        logger.error(f"Error during automatic retry of failed uploads: {str(e)}")
        raise self.retry(exc=e, countdown=1800)  # Retry after 30 minutes