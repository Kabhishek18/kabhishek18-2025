"""
Management command to set up periodic tasks for LinkedIn image monitoring.

This command creates or updates Celery Beat periodic tasks for:
- Metrics cleanup
- Health monitoring
- Daily reporting
- Automatic retry of failed uploads
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json


class Command(BaseCommand):
    help = 'Set up periodic tasks for LinkedIn image monitoring'

    def add_arguments(self, parser):
        parser.add_argument(
            '--enable-all',
            action='store_true',
            help='Enable all monitoring tasks'
        )
        
        parser.add_argument(
            '--disable-all',
            action='store_true',
            help='Disable all monitoring tasks'
        )
        
        parser.add_argument(
            '--cleanup-only',
            action='store_true',
            help='Only set up metrics cleanup task'
        )
        
        parser.add_argument(
            '--health-only',
            action='store_true',
            help='Only set up health monitoring task'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating tasks'
        )

    def handle(self, *args, **options):
        if options['disable_all']:
            self.disable_all_tasks()
            return
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No tasks will be created'))
        
        # Check if LinkedIn image settings are enabled
        linkedin_settings = getattr(settings, 'LINKEDIN_IMAGE_SETTINGS', {})
        if not linkedin_settings.get('ENABLE_IMAGE_UPLOAD', False):
            self.stdout.write(
                self.style.WARNING(
                    'LinkedIn image upload is disabled in settings. '
                    'Monitoring tasks may not be necessary.'
                )
            )
        
        tasks_to_create = []
        
        if options['enable_all'] or options['cleanup_only']:
            tasks_to_create.append('cleanup')
        
        if options['enable_all'] or options['health_only']:
            tasks_to_create.append('health')
        
        if options['enable_all']:
            tasks_to_create.extend(['daily_report', 'retry_failed'])
        
        if not tasks_to_create and not (options['cleanup_only'] or options['health_only']):
            # Default: create cleanup and health monitoring
            tasks_to_create = ['cleanup', 'health']
        
        for task_type in tasks_to_create:
            if task_type == 'cleanup':
                self.create_cleanup_task(options['dry_run'])
            elif task_type == 'health':
                self.create_health_monitoring_task(options['dry_run'])
            elif task_type == 'daily_report':
                self.create_daily_report_task(options['dry_run'])
            elif task_type == 'retry_failed':
                self.create_retry_failed_task(options['dry_run'])
        
        if not options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully set up {len(tasks_to_create)} LinkedIn image monitoring tasks'
                )
            )

    def create_cleanup_task(self, dry_run=False):
        """Create or update the metrics cleanup task"""
        task_name = 'LinkedIn Image Metrics Cleanup'
        
        # Create daily schedule (run at 2 AM)
        schedule, created = CrontabSchedule.objects.get_or_create(
            minute=0,
            hour=2,
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        if dry_run:
            self.stdout.write(f'Would create/update task: {task_name}')
            self.stdout.write(f'  Schedule: Daily at 2:00 AM')
            self.stdout.write(f'  Task: blog.tasks.linkedin_image_monitoring.cleanup_linkedin_image_metrics')
            return
        
        task, created = PeriodicTask.objects.get_or_create(
            name=task_name,
            defaults={
                'crontab': schedule,
                'task': 'blog.tasks.linkedin_image_monitoring.cleanup_linkedin_image_metrics',
                'enabled': True,
            }
        )
        
        if not created:
            task.crontab = schedule
            task.task = 'blog.tasks.linkedin_image_monitoring.cleanup_linkedin_image_metrics'
            task.enabled = True
            task.save()
        
        action = 'Created' if created else 'Updated'
        self.stdout.write(f'{action} task: {task_name}')

    def create_health_monitoring_task(self, dry_run=False):
        """Create or update the health monitoring task"""
        task_name = 'LinkedIn Image Health Monitoring'
        
        # Create hourly schedule
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.HOURS,
        )
        
        if dry_run:
            self.stdout.write(f'Would create/update task: {task_name}')
            self.stdout.write(f'  Schedule: Every hour')
            self.stdout.write(f'  Task: blog.tasks.linkedin_image_monitoring.monitor_linkedin_image_health')
            return
        
        task, created = PeriodicTask.objects.get_or_create(
            name=task_name,
            defaults={
                'interval': schedule,
                'task': 'blog.tasks.linkedin_image_monitoring.monitor_linkedin_image_health',
                'enabled': True,
            }
        )
        
        if not created:
            task.interval = schedule
            task.task = 'blog.tasks.linkedin_image_monitoring.monitor_linkedin_image_health'
            task.enabled = True
            task.save()
        
        action = 'Created' if created else 'Updated'
        self.stdout.write(f'{action} task: {task_name}')

    def create_daily_report_task(self, dry_run=False):
        """Create or update the daily report task"""
        task_name = 'LinkedIn Image Daily Report'
        
        # Create daily schedule (run at 8 AM)
        schedule, created = CrontabSchedule.objects.get_or_create(
            minute=0,
            hour=8,
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        if dry_run:
            self.stdout.write(f'Would create/update task: {task_name}')
            self.stdout.write(f'  Schedule: Daily at 8:00 AM')
            self.stdout.write(f'  Task: blog.tasks.linkedin_image_monitoring.generate_daily_linkedin_report')
            return
        
        task, created = PeriodicTask.objects.get_or_create(
            name=task_name,
            defaults={
                'crontab': schedule,
                'task': 'blog.tasks.linkedin_image_monitoring.generate_daily_linkedin_report',
                'enabled': True,
            }
        )
        
        if not created:
            task.crontab = schedule
            task.task = 'blog.tasks.linkedin_image_monitoring.generate_daily_linkedin_report'
            task.enabled = True
            task.save()
        
        action = 'Created' if created else 'Updated'
        self.stdout.write(f'{action} task: {task_name}')

    def create_retry_failed_task(self, dry_run=False):
        """Create or update the retry failed uploads task"""
        task_name = 'LinkedIn Image Retry Failed Uploads'
        
        # Create schedule to run every 4 hours
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=4,
            period=IntervalSchedule.HOURS,
        )
        
        if dry_run:
            self.stdout.write(f'Would create/update task: {task_name}')
            self.stdout.write(f'  Schedule: Every 4 hours')
            self.stdout.write(f'  Task: blog.tasks.linkedin_image_monitoring.retry_failed_image_uploads')
            return
        
        task, created = PeriodicTask.objects.get_or_create(
            name=task_name,
            defaults={
                'interval': schedule,
                'task': 'blog.tasks.linkedin_image_monitoring.retry_failed_image_uploads',
                'enabled': True,
            }
        )
        
        if not created:
            task.interval = schedule
            task.task = 'blog.tasks.linkedin_image_monitoring.retry_failed_image_uploads'
            task.enabled = True
            task.save()
        
        action = 'Created' if created else 'Updated'
        self.stdout.write(f'{action} task: {task_name}')

    def disable_all_tasks(self):
        """Disable all LinkedIn image monitoring tasks"""
        task_names = [
            'LinkedIn Image Metrics Cleanup',
            'LinkedIn Image Health Monitoring',
            'LinkedIn Image Daily Report',
            'LinkedIn Image Retry Failed Uploads'
        ]
        
        disabled_count = 0
        for task_name in task_names:
            try:
                task = PeriodicTask.objects.get(name=task_name)
                task.enabled = False
                task.save()
                disabled_count += 1
                self.stdout.write(f'Disabled task: {task_name}')
            except PeriodicTask.DoesNotExist:
                self.stdout.write(f'Task not found: {task_name}')
        
        if disabled_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Disabled {disabled_count} LinkedIn image monitoring tasks')
            )
        else:
            self.stdout.write(
                self.style.WARNING('No LinkedIn image monitoring tasks found to disable')
            )