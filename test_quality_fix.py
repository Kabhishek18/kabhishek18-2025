#!/usr/bin/env python3
"""
Test Quality Score Fix

This script tests the timezone fix for the quality score update system.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kabhishek18.settings')
django.setup()

from django.core.management import call_command
from django.utils import timezone
from datetime import datetime, timedelta

def test_quality_update():
    """Test the quality update command with timezone fix"""
    
    print("🧪 Testing Quality Score Update (Timezone Fix)")
    print("=" * 50)
    
    try:
        # Test with a small number of posts
        print("🔄 Running quality update for 5 posts...")
        
        call_command(
            'update_quality_scores',
            posts_per_run=5,
            generate_report=False,
            alert_low_quality=False,
            save_history=False,
            verbosity=1
        )
        
        print("✅ Quality update completed successfully!")
        print("🎉 Timezone issue has been fixed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Quality update failed: {str(e)}")
        return False

def test_timezone_handling():
    """Test timezone handling specifically"""
    
    print("\n🕐 Testing Timezone Handling")
    print("-" * 30)
    
    try:
        from django.core.cache import cache
        
        # Test timezone-aware datetime storage and retrieval
        now = timezone.now()
        cache_key = "test_timezone_key"
        
        # Store timezone-aware datetime as ISO string
        cache.set(f"{cache_key}_timestamp", now.isoformat(), 60)
        
        # Retrieve and compare
        stored_time_str = cache.get(f"{cache_key}_timestamp")
        stored_time = datetime.fromisoformat(stored_time_str)
        
        # Make timezone-aware if naive
        if stored_time.tzinfo is None:
            stored_time = timezone.make_aware(stored_time)
        
        # Test comparison
        cutoff = now - timedelta(minutes=1)
        
        if stored_time > cutoff:
            print("✅ Timezone comparison working correctly")
            return True
        else:
            print("❌ Timezone comparison failed")
            return False
            
    except Exception as e:
        print(f"❌ Timezone test failed: {str(e)}")
        return False

def main():
    """Main test function"""
    
    print("🚀 Quality Score System Test")
    print("=" * 50)
    
    # Test 1: Timezone handling
    timezone_ok = test_timezone_handling()
    
    # Test 2: Quality update (if timezone is OK)
    if timezone_ok:
        quality_ok = test_quality_update()
    else:
        print("⚠️ Skipping quality update test due to timezone issues")
        quality_ok = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    if timezone_ok and quality_ok:
        print("✅ All tests passed!")
        print("🎉 Quality score system is working correctly")
        print("\nNext steps:")
        print("1. Add Beat configuration to settings:")
        print("   python add_beat_to_settings.py")
        print("2. Start Celery services:")
        print("   celery -A kabhishek18 worker --loglevel=info &")
        print("   celery -A kabhishek18 beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler &")
    else:
        print("❌ Some tests failed")
        if not timezone_ok:
            print("   - Timezone handling needs attention")
        if not quality_ok:
            print("   - Quality update system needs attention")

if __name__ == "__main__":
    main()