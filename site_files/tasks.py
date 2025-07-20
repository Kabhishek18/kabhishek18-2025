"""
Celery tasks for the site_files app.

This module contains Celery tasks for updating site metadata files
(Sitemap.xml, robots.txt, security.txt, LLMs.txt).
"""
import logging
from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
from django.apps import apps
from django.db.models.signals import post_save
from django.dispatch import receiver
from site_files.models import SiteFilesConfig

logger = logging.getLogger(__name__)

@shared_task(name="site_files.tasks.update_site_files")
def update_site_files():
    """
    Celery task to update all site metadata files.
    
    This task runs the update_site_files management command to update
    Sitemap.xml, robots.txt, security.txt, and LLMs.txt files based on
    the current configuration.
    
    Returns:
        str: A message indicating the result of the task execution.
    """
    logger.info(f"[{timezone.now()}] Running site files update task...")
    
    try:
        # Get configuration to determine which files to update
        config = SiteFilesConfig.objects.first()
        if not config:
            config = SiteFilesConfig.objects.create()
            logger.warning("No configuration found. Created default configuration.")
        
        # Build command arguments based on configuration
        options = []
        if config.update_sitemap:
            options.append('--sitemap')
        if config.update_robots:
            options.append('--robots')
        if config.update_security:
            options.append('--security')
        if config.update_llms:
            options.append('--llms')
        
        # If no specific files are configured to update, update all
        if not options:
            options.append('--all')
        
        # Add verbose flag for better logging
        options.append('--verbose')
        
        # Call the management command
        call_command('update_site_files', *options)
        
        # Update last_update timestamp in configuration
        config.last_update = timezone.now()
        config.save()
        
        result_message = f"Site files update completed successfully at {timezone.now()}"
        logger.info(result_message)
        return result_message
    
    except Exception as e:
        error_message = f"An error occurred during site files update: {e}"
        logger.error(error_message)
        return error_message


def register_periodic_task():
    """
    Register the update_site_files task with Celery Beat.
    
    This function creates or updates a periodic task in the database
    based on the configuration in SiteFilesConfig.
    """
    try:
        # Import here to avoid circular imports
        from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
        
        # Get configuration
        config = SiteFilesConfig.objects.first()
        if not config:
            config = SiteFilesConfig.objects.create()
            logger.warning("No configuration found. Created default configuration.")
        
        # Delete existing task if it exists
        PeriodicTask.objects.filter(name="Update Site Files").delete()
        
        # Create schedule based on update_frequency
        if config.update_frequency == 'daily':
            # Run daily at midnight
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute='0',
                hour='0',
                day_of_week='*',
                day_of_month='*',
                month_of_year='*',
            )
        elif config.update_frequency == 'weekly':
            # Run weekly on Sunday at midnight
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute='0',
                hour='0',
                day_of_week='0',
                day_of_month='*',
                month_of_year='*',
            )
        elif config.update_frequency == 'monthly':
            # Run monthly on the 1st at midnight
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute='0',
                hour='0',
                day_of_week='*',
                day_of_month='1',
                month_of_year='*',
            )
        else:
            # Default to daily
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute='0',
                hour='0',
                day_of_week='*',
                day_of_month='*',
                month_of_year='*',
            )
        
        # Create the periodic task
        PeriodicTask.objects.create(
            name="Update Site Files",
            task="site_files.tasks.update_site_files",
            crontab=schedule,
            enabled=True,
            description="Automatically update site metadata files (Sitemap.xml, robots.txt, security.txt, LLMs.txt)"
        )
        
        logger.info(f"Registered periodic task for site files update with {config.update_frequency} frequency")
    except Exception as e:
        logger.error(f"Failed to register periodic task: {e}")


@receiver(post_save, sender=SiteFilesConfig)
def update_periodic_task(sender, instance, **kwargs):
    """
    Signal handler to update the periodic task when the configuration is saved.
    
    This ensures that the task schedule is updated whenever the configuration changes.
    """
    register_periodic_task()


# Register the periodic task when the app is ready
def ready():
    """
    Called when the app is ready.
    
    This function is called by Django when the app is ready.
    It registers the periodic task with Celery Beat.
    """
    # Check if we're in a management command
    import sys
    if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
        # Skip during migrations to avoid issues
        return
    
    # Register the periodic task
    register_periodic_task()