"""
Trigger Quality Task Management Command

This command allows you to manually trigger the Celery quality update task
for testing and immediate execution.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.tasks import daily_quality_update, weekly_quality_report


class Command(BaseCommand):
    help = 'Manually trigger quality update Celery tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            choices=['daily', 'weekly', 'both'],
            default='daily',
            help='Which task to trigger (default: daily)'
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run task asynchronously (requires Celery worker)'
        )
        parser.add_argument(
            '--wait',
            action='store_true',
            help='Wait for async task to complete'
        )

    def handle(self, *args, **options):
        task_type = options['task']
        run_async = options['async']
        wait_for_result = options['wait']
        
        self.stdout.write(self.style.SUCCESS("🚀 Triggering Quality Update Tasks"))
        self.stdout.write("=" * 50)
        
        if task_type in ['daily', 'both']:
            self._trigger_daily_task(run_async, wait_for_result)
        
        if task_type in ['weekly', 'both']:
            self._trigger_weekly_task(run_async, wait_for_result)
        
        self.stdout.write(self.style.SUCCESS("\n✅ Task triggering completed!"))

    def _trigger_daily_task(self, run_async, wait_for_result):
        """Trigger the daily quality update task"""
        self.stdout.write("\n📊 Triggering Daily Quality Update Task")
        self.stdout.write("-" * 40)
        
        try:
            if run_async:
                self.stdout.write("🔄 Running task asynchronously...")
                result = daily_quality_update.delay()
                
                self.stdout.write(f"✅ Task queued with ID: {result.id}")
                
                if wait_for_result:
                    self.stdout.write("⏳ Waiting for task to complete...")
                    task_result = result.get(timeout=1800)  # 30 minute timeout
                    
                    if task_result['success']:
                        self.stdout.write("✅ Daily task completed successfully")
                        self.stdout.write(f"   Processed: {task_result['processed_posts']} posts")
                        self.stdout.write(f"   Average Score: {task_result['average_score']:.1f}")
                    else:
                        self.stdout.write(f"❌ Daily task failed: {task_result['error']}")
                else:
                    self.stdout.write("ℹ️ Task is running in background")
                    self.stdout.write("   Check Celery logs for progress")
            else:
                self.stdout.write("🔄 Running task synchronously...")
                result = daily_quality_update.apply()
                
                if result.successful():
                    task_result = result.result
                    self.stdout.write("✅ Daily task completed successfully")
                    self.stdout.write(f"   Processed: {task_result['processed_posts']} posts")
                    self.stdout.write(f"   Average Score: {task_result['average_score']:.1f}")
                else:
                    self.stdout.write(f"❌ Daily task failed: {result.result}")
                    
        except Exception as e:
            self.stdout.write(f"❌ Error triggering daily task: {str(e)}")

    def _trigger_weekly_task(self, run_async, wait_for_result):
        """Trigger the weekly quality report task"""
        self.stdout.write("\n📈 Triggering Weekly Quality Report Task")
        self.stdout.write("-" * 40)
        
        try:
            if run_async:
                self.stdout.write("🔄 Running task asynchronously...")
                result = weekly_quality_report.delay()
                
                self.stdout.write(f"✅ Task queued with ID: {result.id}")
                
                if wait_for_result:
                    self.stdout.write("⏳ Waiting for task to complete...")
                    task_result = result.get(timeout=3600)  # 1 hour timeout
                    
                    if task_result['success']:
                        self.stdout.write("✅ Weekly task completed successfully")
                        summary = task_result.get('quality_summary', {})
                        if summary:
                            self.stdout.write(f"   Total Posts: {summary.get('total_posts', 0)}")
                            self.stdout.write(f"   Average Score: {summary.get('average_score', 0):.1f}")
                            self.stdout.write(f"   Quality Status: {summary.get('quality_status', 'unknown')}")
                    else:
                        self.stdout.write(f"❌ Weekly task failed: {task_result['error']}")
                else:
                    self.stdout.write("ℹ️ Task is running in background")
                    self.stdout.write("   Check Celery logs for progress")
            else:
                self.stdout.write("🔄 Running task synchronously...")
                result = weekly_quality_report.apply()
                
                if result.successful():
                    task_result = result.result
                    self.stdout.write("✅ Weekly task completed successfully")
                    summary = task_result.get('quality_summary', {})
                    if summary:
                        self.stdout.write(f"   Total Posts: {summary.get('total_posts', 0)}")
                        self.stdout.write(f"   Average Score: {summary.get('average_score', 0):.1f}")
                        self.stdout.write(f"   Quality Status: {summary.get('quality_status', 'unknown')}")
                else:
                    self.stdout.write(f"❌ Weekly task failed: {result.result}")
                    
        except Exception as e:
            self.stdout.write(f"❌ Error triggering weekly task: {str(e)}")

    def _show_task_status(self):
        """Show current task status"""
        self.stdout.write("\n📋 Current Task Status")
        self.stdout.write("-" * 40)
        
        try:
            from django_celery_beat.models import PeriodicTask
            
            # Check if tasks are configured
            daily_task = PeriodicTask.objects.filter(
                task='blog.tasks.daily_quality_update'
            ).first()
            
            weekly_task = PeriodicTask.objects.filter(
                task='blog.tasks.weekly_quality_report'
            ).first()
            
            if daily_task:
                status = "Enabled" if daily_task.enabled else "Disabled"
                self.stdout.write(f"Daily Task: {status}")
                self.stdout.write(f"  Schedule: {daily_task.crontab}")
                self.stdout.write(f"  Last Run: {daily_task.last_run_at or 'Never'}")
            else:
                self.stdout.write("Daily Task: Not configured")
            
            if weekly_task:
                status = "Enabled" if weekly_task.enabled else "Disabled"
                self.stdout.write(f"Weekly Task: {status}")
                self.stdout.write(f"  Schedule: {weekly_task.crontab}")
                self.stdout.write(f"  Last Run: {weekly_task.last_run_at or 'Never'}")
            else:
                self.stdout.write("Weekly Task: Not configured")
                
        except ImportError:
            self.stdout.write("django-celery-beat not installed")
        except Exception as e:
            self.stdout.write(f"Error checking task status: {str(e)}")