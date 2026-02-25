#!/usr/bin/env python3
"""
Django Beat Quality Score Setup

This script helps you set up Django Beat (Celery Beat) to automatically
update quality scores daily and generate weekly reports.

Features:
- Configures Celery Beat for quality monitoring
- Sets up daily quality score updates
- Configures weekly comprehensive reports
- Provides monitoring and management commands
"""

import os
import sys
import json
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kabhishek18.settings')
django.setup()

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"🚀 {title}")
    print("=" * 60)

def print_step(step_num, title):
    """Print a formatted step"""
    print(f"\n📋 Step {step_num}: {title}")
    print("-" * 40)

def check_celery_setup():
    """Check if Celery and Django Beat are properly configured"""
    print_step(1, "Checking Celery and Django Beat Setup")
    
    requirements_met = True
    
    # Check if Celery is installed
    try:
        import celery
        print(f"✅ Celery installed: {celery.__version__}")
    except ImportError:
        print("❌ Celery not installed. Run: pip install celery")
        requirements_met = False
    
    # Check if django-celery-beat is installed
    try:
        import django_celery_beat
        print(f"✅ Django Celery Beat installed: {django_celery_beat.__version__}")
    except ImportError:
        print("❌ Django Celery Beat not installed. Run: pip install django-celery-beat")
        requirements_met = False
    
    # Check if Redis/RabbitMQ is configured
    from django.conf import settings
    
    if hasattr(settings, 'CELERY_BROKER_URL'):
        print(f"✅ Celery broker configured: {settings.CELERY_BROKER_URL}")
    else:
        print("⚠️ Celery broker not configured in settings")
        print("   Add CELERY_BROKER_URL to your settings (e.g., Redis or RabbitMQ)")
    
    # Check if django_celery_beat is in INSTALLED_APPS
    if 'django_celery_beat' in settings.INSTALLED_APPS:
        print("✅ django_celery_beat in INSTALLED_APPS")
    else:
        print("❌ Add 'django_celery_beat' to INSTALLED_APPS in settings.py")
        requirements_met = False
    
    return requirements_met

def setup_beat_configuration():
    """Set up Beat configuration"""
    print_step(2, "Setting Up Beat Configuration")
    
    # Read the celery beat config
    try:
        with open('celery_beat_config.py', 'r') as f:
            config_content = f.read()
        
        print("✅ Celery Beat configuration file found")
        
        # Check if configuration is already in settings
        from django.conf import settings
        
        if hasattr(settings, 'CELERY_BEAT_SCHEDULE'):
            print("✅ CELERY_BEAT_SCHEDULE already configured in settings")
        else:
            print("⚠️ CELERY_BEAT_SCHEDULE not found in settings")
            print("\n📋 Add this to your settings.py:")
            print("-" * 40)
            print("# Import the beat configuration")
            print("from celery_beat_config import CELERY_BEAT_SCHEDULE, CELERY_TIMEZONE")
            print("")
            print("# Celery Beat Settings")
            print("CELERY_BEAT_SCHEDULE = CELERY_BEAT_SCHEDULE")
            print("CELERY_TIMEZONE = CELERY_TIMEZONE")
            print("CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'")
        
        return True
        
    except FileNotFoundError:
        print("❌ celery_beat_config.py not found")
        return False

def migrate_beat_database():
    """Run migrations for django-celery-beat"""
    print_step(3, "Setting Up Beat Database")
    
    try:
        import subprocess
        
        print("🔄 Running django-celery-beat migrations...")
        result = subprocess.run([
            sys.executable, 'manage.py', 'migrate', 'django_celery_beat'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Django Celery Beat migrations completed")
            return True
        else:
            print(f"❌ Migration failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running migrations: {str(e)}")
        return False

def create_beat_schedule():
    """Create the beat schedule in database"""
    print_step(4, "Creating Beat Schedule in Database")
    
    try:
        from django_celery_beat.models import PeriodicTask, CrontabSchedule
        
        # Create crontab schedules
        schedules = {
            'daily_2am': CrontabSchedule.objects.get_or_create(
                minute=0, hour=2, day_of_week='*', day_of_month='*', month_of_year='*'
            )[0],
            'weekly_monday_6am': CrontabSchedule.objects.get_or_create(
                minute=0, hour=6, day_of_week=1, day_of_month='*', month_of_year='*'
            )[0],
        }
        
        # Create periodic tasks
        tasks_created = 0
        
        # Daily quality update
        task, created = PeriodicTask.objects.get_or_create(
            name='Daily Quality Score Update',
            defaults={
                'task': 'blog.tasks.daily_quality_update',
                'crontab': schedules['daily_2am'],
                'enabled': True,
                'description': 'Update quality scores for all blog posts daily at 2 AM'
            }
        )
        if created:
            tasks_created += 1
            print("✅ Created: Daily Quality Score Update (2:00 AM daily)")
        else:
            print("ℹ️ Exists: Daily Quality Score Update")
        
        # Weekly quality report
        task, created = PeriodicTask.objects.get_or_create(
            name='Weekly Quality Report',
            defaults={
                'task': 'blog.tasks.weekly_quality_report',
                'crontab': schedules['weekly_monday_6am'],
                'enabled': True,
                'description': 'Generate comprehensive weekly quality report on Mondays at 6 AM'
            }
        )
        if created:
            tasks_created += 1
            print("✅ Created: Weekly Quality Report (Monday 6:00 AM)")
        else:
            print("ℹ️ Exists: Weekly Quality Report")
        
        print(f"\n📊 Summary: {tasks_created} new tasks created")
        return True
        
    except Exception as e:
        print(f"❌ Error creating beat schedule: {str(e)}")
        return False

def test_quality_task():
    """Test the quality update task"""
    print_step(5, "Testing Quality Update Task")
    
    try:
        from blog.tasks import daily_quality_update
        
        print("🧪 Running test quality update (this may take a moment)...")
        
        # Run the task synchronously for testing
        result = daily_quality_update.apply()
        
        if result.successful():
            task_result = result.result
            print("✅ Quality update task completed successfully")
            print(f"   Processed: {task_result.get('processed_posts', 0)} posts")
            print(f"   Average Score: {task_result.get('average_score', 0):.1f}")
        else:
            print(f"❌ Quality update task failed: {result.result}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing quality task: {str(e)}")
        return False

def provide_management_instructions():
    """Provide instructions for managing the Beat schedule"""
    print_step(6, "Management Instructions")
    
    print("🎯 STARTING CELERY SERVICES:")
    print("-" * 40)
    print("1. Start Celery Worker (in one terminal):")
    print("   celery -A kabhishek18 worker --loglevel=info")
    print("")
    print("2. Start Celery Beat (in another terminal):")
    print("   celery -A kabhishek18 beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler")
    print("")
    print("3. Or start both together:")
    print("   celery -A kabhishek18 worker --beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler")
    print("")
    
    print("📊 MONITORING COMMANDS:")
    print("-" * 40)
    print("• View scheduled tasks:")
    print("  python manage.py shell")
    print("  >>> from django_celery_beat.models import PeriodicTask")
    print("  >>> PeriodicTask.objects.all()")
    print("")
    print("• Run quality update manually:")
    print("  python manage.py update_quality_scores")
    print("")
    print("• Check task results:")
    print("  python manage.py shell")
    print("  >>> from blog.tasks import daily_quality_update")
    print("  >>> result = daily_quality_update.delay()")
    print("  >>> result.get()")
    print("")
    
    print("🔧 DJANGO ADMIN MANAGEMENT:")
    print("-" * 40)
    print("• Access Django Admin → Periodic Tasks")
    print("• Enable/disable tasks")
    print("• Modify schedules")
    print("• View task history")
    print("")
    
    print("📈 QUALITY MONITORING:")
    print("-" * 40)
    print("• Daily updates run automatically at 2:00 AM")
    print("• Weekly reports generated on Mondays at 6:00 AM")
    print("• Check logs for task execution status")
    print("• Monitor quality trends in Django admin")

def main():
    """Main setup process"""
    print_header("Django Beat Quality Score Setup")
    
    print("This script will set up Django Beat to automatically update")
    print("quality scores daily and generate comprehensive weekly reports.")
    
    # Step 1: Check Celery setup
    if not check_celery_setup():
        print("\n❌ Please fix the requirements above before continuing.")
        return False
    
    # Step 2: Setup Beat configuration
    if not setup_beat_configuration():
        print("\n❌ Beat configuration setup failed.")
        return False
    
    # Step 3: Migrate database
    if not migrate_beat_database():
        print("\n❌ Database migration failed.")
        return False
    
    # Step 4: Create beat schedule
    if not create_beat_schedule():
        print("\n❌ Beat schedule creation failed.")
        return False
    
    # Step 5: Test quality task
    print("\nDo you want to test the quality update task now? (y/n): ", end="")
    test_choice = input().lower()
    
    if test_choice in ['y', 'yes']:
        if not test_quality_task():
            print("\n⚠️ Task test failed, but setup is complete.")
    
    # Step 6: Provide management instructions
    provide_management_instructions()
    
    print_header("Setup Complete!")
    print("✅ Django Beat is now configured for automatic quality updates.")
    print("🚀 Start Celery worker and beat to begin automatic monitoring.")
    print("📊 Quality scores will be updated daily at 2:00 AM.")
    print("📈 Weekly reports will be generated on Mondays at 6:00 AM.")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)