"""
Celery Beat Configuration for Quality Score Updates

This file contains the Celery Beat schedule configuration for automatic
quality score updates and content monitoring tasks.

Add this configuration to your Django settings or Celery configuration.
"""

from celery.schedules import crontab

# Celery Beat Schedule Configuration
CELERY_BEAT_SCHEDULE = {
    # Daily quality score update at 2:00 AM
    'daily-quality-update': {
        'task': 'blog.tasks.daily_quality_update',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2:00 AM
        'options': {
            'expires': 3600,  # Task expires after 1 hour if not executed
        }
    },
    
    # Weekly comprehensive quality report on Mondays at 6:00 AM
    'weekly-quality-report': {
        'task': 'blog.tasks.weekly_quality_report',
        'schedule': crontab(hour=6, minute=0, day_of_week=1),  # Monday at 6:00 AM
        'options': {
            'expires': 7200,  # Task expires after 2 hours if not executed
        }
    },
    
    # Existing tasks (keep your current schedule)
    'generate-ai-blog-post': {
        'task': 'blog.tasks.generate_ai_blog_post',
        'schedule': crontab(hour=9, minute=0, day_of_week='1,3,5'),  # Mon, Wed, Fri at 9 AM
        'kwargs': {'publish': True, 'count': 1}
    },
    
    # Auto-publish premium posts (using CRAG) - 3 times per week
    'auto-publish-premium-crag': {
        'task': 'blog.tasks.auto_publish_premium_post',
        'schedule': crontab(hour=10, minute=0, day_of_week='2,4,6'),  # Tue, Thu, Sat at 10 AM
        'options': {
            'expires': 3600,
        }
    },
    
    # LinkedIn posting retry - every 30 minutes
    'retry-failed-linkedin-posts': {
        'task': 'blog.tasks.retry_failed_linkedin_posts',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    
    # Cleanup tasks - daily at midnight
    'cleanup-old-linkedin-posts': {
        'task': 'blog.tasks.cleanup_old_linkedin_posts',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
    
    # Newsletter cleanup - weekly on Sundays at 1 AM
    'cleanup-unconfirmed-subscriptions': {
        'task': 'blog.tasks.cleanup_unconfirmed_subscriptions',
        'schedule': crontab(hour=1, minute=0, day_of_week=0),  # Sunday at 1 AM
    },
    
    # Performance monitoring - every 6 hours
    'performance-monitoring': {
        'task': 'blog.tasks.performance_monitoring_task',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    },
    
    # Security audit - daily at 3 AM
    'security-audit': {
        'task': 'blog.tasks.security_audit_task',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    
    # AdSense audit - weekly on Wednesdays at 4 AM
    'adsense-audit': {
        'task': 'blog.tasks.adsense_audit_report_task',
        'schedule': crontab(hour=4, minute=0, day_of_week=3),  # Wednesday at 4 AM
    },
}

# Timezone for all scheduled tasks
CELERY_TIMEZONE = 'UTC'  # Change to your timezone, e.g., 'America/New_York'

# Additional Celery Beat settings
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Task routing (optional - for multiple queues)
CELERY_TASK_ROUTES = {
    'blog.tasks.daily_quality_update': {'queue': 'quality'},
    'blog.tasks.weekly_quality_report': {'queue': 'reports'},
    'blog.tasks.generate_ai_blog_post': {'queue': 'content'},
    'blog.tasks.auto_publish_premium_post': {'queue': 'content'},
    'blog.tasks.post_to_linkedin': {'queue': 'social'},
}

# Default queue
CELERY_TASK_DEFAULT_QUEUE = 'default'

# Quality-specific task settings
CELERY_TASK_ANNOTATIONS = {
    'blog.tasks.daily_quality_update': {
        'rate_limit': '1/h',  # Max 1 per hour
        'time_limit': 1800,   # 30 minutes timeout
        'soft_time_limit': 1500,  # 25 minutes soft timeout
    },
    'blog.tasks.weekly_quality_report': {
        'rate_limit': '1/d',  # Max 1 per day
        'time_limit': 3600,   # 1 hour timeout
        'soft_time_limit': 3300,  # 55 minutes soft timeout
    },
}