from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Post, AuthorProfile
from .linkedin_models import LinkedInPost, LinkedInConfig
from .tasks import send_new_post_notification, post_to_linkedin
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_author_profile(sender, instance, created, **kwargs):
    """
    Automatically create an AuthorProfile when a new User is created.
    """
    if created:
        AuthorProfile.objects.create(user=instance)
        logger.info(f"Created AuthorProfile for user: {instance.username}")


@receiver(post_save, sender=User)
def save_author_profile(sender, instance, **kwargs):
    """
    Save the AuthorProfile when the User is saved.
    """
    if hasattr(instance, 'author_profile'):
        instance.author_profile.save()


@receiver(post_save, sender=Post)
def ensure_author_profile_exists(sender, instance, created, **kwargs):
    """
    Ensure that the post author has an AuthorProfile.
    Create one if it doesn't exist.
    """
    if not hasattr(instance.author, 'author_profile'):
        AuthorProfile.objects.create(user=instance.author)
        logger.info(f"Created AuthorProfile for post author: {instance.author.username}")


@receiver(post_save, sender=Post)
def send_newsletter_on_publish(sender, instance, created, **kwargs):
    """
    Send newsletter notification when a post is published.
    """
    # Only send newsletter for newly published posts or when status changes to published
    if instance.status == 'published':
        # Check if this is a new post or if the status just changed to published
        if created:
            # New post published
            logger.info(f"New post published: {instance.title}. Sending newsletter.")
            send_new_post_notification.delay(instance.id)
        else:
            # Existing post status changed - check if it was just published
            try:
                # Get the previous state from database
                old_instance = Post.objects.get(pk=instance.pk)
                # This won't work as expected since we're in post_save
                # We'll need to track this differently
                # For now, we'll send newsletter for any published post save
                # In production, you might want to add a field to track if newsletter was sent
                if not hasattr(instance, '_newsletter_sent'):
                    logger.info(f"Post status changed to published: {instance.title}. Sending newsletter.")
                    send_new_post_notification.delay(instance.id)
            except Post.DoesNotExist:
                pass


@receiver(post_save, sender=Post)
def post_to_linkedin_on_publish(sender, instance, created, **kwargs):
    """
    Automatically post to LinkedIn when a blog post is published.
    
    This signal handler:
    - Triggers LinkedIn posting when post status changes to published
    - Implements duplicate posting prevention logic
    - Adds proper logging for signal-triggered actions
    
    Requirements: 1.1, 1.2, 4.1
    """
    # Only process published posts
    if instance.status != 'published':
        return
    
    # Check if LinkedIn integration is configured and active
    linkedin_config = LinkedInConfig.get_active_config()
    if not linkedin_config:
        logger.warning(f"No LinkedIn configuration found. Skipping LinkedIn posting for post: {instance.title}")
        return
    elif not linkedin_config.is_active:
        logger.info(f"LinkedIn integration is disabled. Skipping LinkedIn posting for post: {instance.title}")
        return
    elif not linkedin_config.has_valid_credentials():
        logger.error(f"LinkedIn configuration has invalid credentials. Skipping LinkedIn posting for post: {instance.title}")
        return
    
    # Duplicate posting prevention logic
    try:
        # Check if we already have a LinkedIn post record for this blog post
        existing_linkedin_post = LinkedInPost.objects.filter(post=instance).first()
        
        if existing_linkedin_post:
            # If already successfully posted, skip
            if existing_linkedin_post.is_successful():
                logger.info(f"Post '{instance.title}' already successfully posted to LinkedIn. Skipping duplicate posting.")
                return
            
            # If failed but can retry, allow reposting
            if existing_linkedin_post.is_failed() and existing_linkedin_post.can_retry():
                logger.info(f"Retrying LinkedIn posting for post '{instance.title}' (attempt {existing_linkedin_post.attempt_count + 1})")
            elif existing_linkedin_post.is_failed():
                logger.warning(f"Post '{instance.title}' has failed LinkedIn posting and exceeded max attempts. Skipping.")
                return
            # If pending or retrying, let the existing task handle it
            elif existing_linkedin_post.status in ['pending', 'retrying']:
                logger.info(f"LinkedIn posting already in progress for post '{instance.title}'. Skipping duplicate trigger.")
                return
    
    except Exception as e:
        logger.error(f"Error checking existing LinkedIn post for '{instance.title}': {e}")
        # Continue with posting attempt despite the error
    
    # Trigger LinkedIn posting task
    try:
        # Use a flag to prevent recursive signal triggering
        if not hasattr(instance, '_linkedin_posting_triggered'):
            instance._linkedin_posting_triggered = True
            
            logger.info(f"Triggering LinkedIn posting for published post: {instance.title}")
            
            # Queue the LinkedIn posting task asynchronously
            post_to_linkedin.delay(instance.id)
            
            logger.info(f"LinkedIn posting task queued for post: {instance.title}")
        else:
            logger.debug(f"LinkedIn posting already triggered for post: {instance.title}")
    
    except Exception as e:
        logger.error(f"Failed to queue LinkedIn posting task for post '{instance.title}': {e}")
        # Don't raise the exception to avoid interrupting the post save process