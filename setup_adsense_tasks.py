#!/usr/bin/env python
"""
Quick setup script for AdSense periodic tasks
Run: python setup_adsense_tasks.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kabhishek18.settings')
django.setup()

from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule


def create_audit_report_task():
    """Create daily audit report task (safe, no changes)"""
    
    # Create or get daily schedule (2 AM)
    schedule, created = CrontabSchedule.objects.get_or_create(
        minute='0',
        hour='2',
        day_of_week='*',
        day_of_month='*',
        month_of_year='*',
    )
    
    # Create periodic task
    task, created = PeriodicTask.objects.get_or_create(
        name='AdSense Audit Report (Daily)',
        defaults={
            'crontab': schedule,
            'task': 'blog.tasks.adsense_audit_report_task',
            'enabled': True,
        }
    )
    
    if created:
        print("✅ Created: AdSense Audit Report (Daily at 2 AM)")
    else:
        print("ℹ️  Already exists: AdSense Audit Report")
    
    return task


def create_autofix_task():
    """Create weekly auto-fix task (caution: makes changes)"""
    
    # Create or get weekly schedule (Sunday 3 AM)
    schedule, created = CrontabSchedule.objects.get_or_create(
        minute='0',
        hour='3',
        day_of_week='0',  # Sunday
        day_of_month='*',
        month_of_year='*',
    )
    
    # Create periodic task (disabled by default for safety)
    task, created = PeriodicTask.objects.get_or_create(
        name='AdSense Auto-Fix (Weekly)',
        defaults={
            'crontab': schedule,
            'task': 'blog.tasks.adsense_audit_autofix_task',
            'enabled': False,  # Disabled by default for safety
        }
    )
    
    if created:
        print("⚠️  Created: AdSense Auto-Fix (Weekly, DISABLED by default)")
        print("   Enable in admin after testing: /admin/django_celery_beat/periodictask/")
    else:
        print("ℹ️  Already exists: AdSense Auto-Fix")
    
    return task


def main():
    print("\n" + "="*60)
    print("AdSense Periodic Tasks Setup")
    print("="*60 + "\n")
    
    try:
        # Check if django-celery-beat is installed
        import django_celery_beat
    except ImportError:
        print("❌ Error: django-celery-beat not installed")
        print("\nInstall it with:")
        print("  pip install django-celery-beat")
        print("\nThen add to INSTALLED_APPS in settings.py:")
        print("  'django_celery_beat',")
        print("\nAnd run migrations:")
        print("  python manage.py migrate django_celery_beat")
        sys.exit(1)
    
    # Create tasks
    print("Creating periodic tasks...\n")
    
    audit_task = create_audit_report_task()
    autofix_task = create_autofix_task()
    
    print("\n" + "="*60)
    print("Setup Complete!")
    print("="*60 + "\n")
    
    print("📋 Tasks Created:")
    print(f"  1. {audit_task.name}")
    print(f"     Status: {'✅ Enabled' if audit_task.enabled else '❌ Disabled'}")
    print(f"     Schedule: Daily at 2 AM")
    print(f"     Action: Reports issues (safe, no changes)")
    
    print(f"\n  2. {autofix_task.name}")
    print(f"     Status: {'✅ Enabled' if autofix_task.enabled else '⚠️  Disabled (for safety)'}")
    print(f"     Schedule: Weekly on Sunday at 3 AM")
    print(f"     Action: Unpublishes low-quality posts")
    
    print("\n" + "="*60)
    print("Next Steps:")
    print("="*60 + "\n")
    
    print("1. Start Celery services:")
    print("   celery -A kabhishek18 worker --loglevel=info &")
    print("   celery -A kabhishek18 beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler &")
    
    print("\n2. View tasks in admin:")
    print("   http://localhost:8000/admin/django_celery_beat/periodictask/")
    
    print("\n3. Test manually:")
    print("   python manage.py shell")
    print("   >>> from blog.tasks import adsense_audit_report_task")
    print("   >>> result = adsense_audit_report_task.delay()")
    print("   >>> print(result.get(timeout=60))")
    
    print("\n4. Enable auto-fix (optional, use with caution):")
    print("   - Go to admin")
    print("   - Find 'AdSense Auto-Fix (Weekly)'")
    print("   - Check 'Enabled'")
    print("   - Save")
    
    print("\n" + "="*60)
    print("Documentation: ADSENSE_PERIODIC_TASKS_SETUP.md")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
