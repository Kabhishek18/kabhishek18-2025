#!/usr/bin/env python3
"""
Add Beat Configuration to Django Settings

This script helps you add the Celery Beat configuration to your Django settings.py file.
"""

import os
import re

def add_beat_config_to_settings():
    """Add Beat configuration to settings.py"""
    
    settings_file = 'kabhishek18/settings.py'
    
    if not os.path.exists(settings_file):
        print(f"❌ Settings file not found: {settings_file}")
        return False
    
    # Read current settings
    with open(settings_file, 'r') as f:
        content = f.read()
    
    # Check if Beat config is already added
    if 'CELERY_BEAT_SCHEDULE' in content:
        print("✅ CELERY_BEAT_SCHEDULE already exists in settings.py")
        return True
    
    # Configuration to add
    beat_config = '''
# Celery Beat Configuration for Quality Monitoring
try:
    from celery_beat_config import (
        CELERY_BEAT_SCHEDULE, 
        CELERY_TIMEZONE,
        CELERY_BEAT_SCHEDULER
    )
    
    # Apply Beat configuration
    CELERY_BEAT_SCHEDULE = CELERY_BEAT_SCHEDULE
    CELERY_TIMEZONE = CELERY_TIMEZONE or 'UTC'
    CELERY_BEAT_SCHEDULER = CELERY_BEAT_SCHEDULER
    
    print("✅ Celery Beat configuration loaded successfully")
    
except ImportError:
    print("⚠️ celery_beat_config.py not found - Beat scheduling disabled")
    CELERY_BEAT_SCHEDULE = {}
    CELERY_TIMEZONE = 'UTC'
    CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
'''
    
    # Add the configuration at the end of the file
    updated_content = content + beat_config
    
    # Write back to file
    try:
        with open(settings_file, 'w') as f:
            f.write(updated_content)
        
        print("✅ Beat configuration added to settings.py")
        print("\n📋 Configuration added:")
        print("   - CELERY_BEAT_SCHEDULE")
        print("   - CELERY_TIMEZONE") 
        print("   - CELERY_BEAT_SCHEDULER")
        print("\n🔄 Restart your Django application to apply changes")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update settings.py: {str(e)}")
        return False

def main():
    print("🔧 Adding Celery Beat Configuration to Django Settings")
    print("=" * 60)
    
    success = add_beat_config_to_settings()
    
    if success:
        print("\n✅ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Restart your Django application")
        print("2. Start Celery worker and beat:")
        print("   celery -A kabhishek18 worker --loglevel=info &")
        print("   celery -A kabhishek18 beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler &")
        print("3. Test the quality update:")
        print("   python manage.py trigger_quality_task --task daily")
    else:
        print("\n❌ Setup failed. Please add the configuration manually.")

if __name__ == "__main__":
    main()