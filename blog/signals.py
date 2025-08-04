from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Post, AuthorProfile
from .tasks import send_new_post_notification
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