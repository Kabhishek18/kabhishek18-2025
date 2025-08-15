"""
Management command for troubleshooting LinkedIn image processing issues.

This command provides various troubleshooting utilities for diagnosing and
resolving LinkedIn image integration problems.
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import json
import sys

from blog.services.linkedin_image_monitor import LinkedInImageMetrics, LinkedInImageTroubleshooter
from blog.linkedin_models import LinkedInPost, LinkedInConfig


class Command(BaseCommand):
    help = 'Troubleshoot LinkedIn image processing issues'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=[
                'health-check', 'config-check', 'metrics', 'failures', 
                'cleanup', 'test-config', 'reset-failed'
            ],
            help='Action to perform'
        )
        
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Number of hours to analyze (default: 24)'
        )
        
        parser.add_argument(
            '--post-id',
            type=int,
            help='Specific post ID to analyze'
        )
        
        parser.add_argument(
            '--format',
            choices=['text', 'json'],
            default='text',
            help='Output format (default: text)'
        )
        
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to fix issues automatically'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        try:
            if action == 'health-check':
                self.health_check(options)
            elif action == 'config-check':
                self.config_check(options)
            elif action == 'metrics':
                self.show_metrics(options)
            elif action == 'failures':
                self.analyze_failures(options)
            elif action == 'cleanup':
                self.cleanup_metrics(options)
            elif action == 'test-config':
                self.test_configuration(options)
            elif action == 'reset-failed':
                self.reset_failed_posts(options)
        except Exception as e:
            raise CommandError(f'Error executing {action}: {str(e)}')

    def health_check(self, options):
        """Perform comprehensive health check"""
        self.stdout.write(self.style.SUCCESS('LinkedIn Image Processing Health Check'))
        self.stdout.write('=' * 50)
        
        try:
            health_report = LinkedInImageTroubleshooter.generate_health_report()
            
            if options['format'] == 'json':
                self.stdout.write(json.dumps(health_report, indent=2, default=str))
                return
            
            # Overall health
            score = health_report['overall_health_score']
            if score >= 90:
                status_color = self.style.SUCCESS
                status_text = 'HEALTHY'
            elif score >= 70:
                status_color = self.style.WARNING
                status_text = 'NEEDS ATTENTION'
            else:
                status_color = self.style.ERROR
                status_text = 'CRITICAL'
            
            self.stdout.write(f'Overall Health Score: {status_color(f"{score}% - {status_text}")}')
            self.stdout.write('')
            
            # Current status
            current = health_report['current_status']
            self.stdout.write('Current Status:')
            self.stdout.write(f'  Health: {current["health_status"]}')
            self.stdout.write(f'  Image Upload: {"Enabled" if current["image_upload_enabled"] else "Disabled"}')
            self.stdout.write(f'  Image Processing: {"Enabled" if current["image_processing_enabled"] else "Disabled"}')
            self.stdout.write(f'  Active Sessions: {current["active_processing_sessions"]}')
            self.stdout.write(f'  Recent Success Rate: {current["recent_success_rate"]}%')
            self.stdout.write('')
            
            # Configuration issues
            config_check = health_report['configuration_check']
            if config_check['issues']:
                self.stdout.write(self.style.ERROR('Critical Issues:'))
                for issue in config_check['issues']:
                    self.stdout.write(f'  ✗ {issue}')
                self.stdout.write('')
            
            if config_check['warnings']:
                self.stdout.write(self.style.WARNING('Warnings:'))
                for warning in config_check['warnings']:
                    self.stdout.write(f'  ⚠ {warning}')
                self.stdout.write('')
            
            # Recent failures
            failures = health_report['recent_failures']
            if failures['total_failures'] > 0:
                self.stdout.write(self.style.WARNING(f'Recent Failures: {failures["total_failures"]}'))
                if failures['error_breakdown']:
                    for error_type, count in failures['error_breakdown'].items():
                        self.stdout.write(f'  {error_type}: {count}')
                self.stdout.write('')
            
            # Recommendations
            if config_check['recommendations']:
                self.stdout.write('Recommendations:')
                for rec in config_check['recommendations']:
                    self.stdout.write(f'  • {rec}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error generating health report: {str(e)}'))

    def config_check(self, options):
        """Check configuration for issues"""
        self.stdout.write(self.style.SUCCESS('LinkedIn Image Configuration Check'))
        self.stdout.write('=' * 50)
        
        try:
            config_check = LinkedInImageTroubleshooter.check_configuration()
            
            if options['format'] == 'json':
                self.stdout.write(json.dumps(config_check, indent=2, default=str))
                return
            
            # Status
            status = config_check['status']
            if status == 'ok':
                self.stdout.write(self.style.SUCCESS('Configuration Status: OK'))
            elif status == 'warning':
                self.stdout.write(self.style.WARNING('Configuration Status: WARNING'))
            else:
                self.stdout.write(self.style.ERROR('Configuration Status: ERROR'))
            
            self.stdout.write('')
            
            # Issues
            if config_check['issues']:
                self.stdout.write(self.style.ERROR('Critical Issues:'))
                for issue in config_check['issues']:
                    self.stdout.write(f'  ✗ {issue}')
                    if options['fix']:
                        self.stdout.write(f'    Attempting to fix...')
                        # Add auto-fix logic here if needed
                self.stdout.write('')
            
            # Warnings
            if config_check['warnings']:
                self.stdout.write(self.style.WARNING('Warnings:'))
                for warning in config_check['warnings']:
                    self.stdout.write(f'  ⚠ {warning}')
                self.stdout.write('')
            
            # Configuration details
            self.stdout.write('Current Configuration:')
            for key, value in config_check['configuration'].items():
                self.stdout.write(f'  {key}: {value}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error checking configuration: {str(e)}'))

    def show_metrics(self, options):
        """Show processing metrics"""
        hours = options['hours']
        self.stdout.write(self.style.SUCCESS(f'LinkedIn Image Processing Metrics (Last {hours} hours)'))
        self.stdout.write('=' * 60)
        
        try:
            metrics = LinkedInImageMetrics.get_processing_metrics(hours=hours)
            
            if options['format'] == 'json':
                self.stdout.write(json.dumps(metrics, indent=2, default=str))
                return
            
            # Summary
            self.stdout.write('Summary:')
            self.stdout.write(f'  Total Attempts: {metrics["total_attempts"]}')
            self.stdout.write(f'  Successful: {metrics["successful_uploads"]}')
            self.stdout.write(f'  Failed: {metrics["failed_uploads"]}')
            self.stdout.write(f'  Success Rate: {metrics["success_rate_percent"]}%')
            self.stdout.write('')
            
            # Processing times
            times = metrics['processing_times']
            self.stdout.write('Processing Times:')
            self.stdout.write(f'  Average: {times["average_seconds"]}s')
            self.stdout.write(f'  Minimum: {times["minimum_seconds"]}s')
            self.stdout.write(f'  Maximum: {times["maximum_seconds"]}s')
            self.stdout.write(f'  Samples: {times["total_samples"]}')
            self.stdout.write('')
            
            # Error breakdown
            if metrics['error_breakdown']:
                self.stdout.write('Error Breakdown:')
                for error_type, count in metrics['error_breakdown'].items():
                    self.stdout.write(f'  {error_type}: {count}')
                self.stdout.write('')
            
            # Daily stats
            if metrics['daily_statistics']:
                self.stdout.write('Daily Statistics:')
                for date, stats in metrics['daily_statistics'].items():
                    success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
                    self.stdout.write(f'  {date}: {stats["total"]} total, {stats["success"]} success ({success_rate:.1f}%)')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error retrieving metrics: {str(e)}'))

    def analyze_failures(self, options):
        """Analyze recent failures"""
        hours = options['hours']
        self.stdout.write(self.style.SUCCESS(f'LinkedIn Image Failure Analysis (Last {hours} hours)'))
        self.stdout.write('=' * 60)
        
        try:
            failures = LinkedInImageTroubleshooter.diagnose_recent_failures(hours=hours)
            
            if options['format'] == 'json':
                self.stdout.write(json.dumps(failures, indent=2, default=str))
                return
            
            # Status
            status = failures['status']
            if status == 'healthy':
                self.stdout.write(self.style.SUCCESS('Status: Healthy - No recent failures'))
                return
            elif status == 'minor_issues':
                self.stdout.write(self.style.WARNING('Status: Minor Issues'))
            elif status == 'warning':
                self.stdout.write(self.style.WARNING('Status: Warning'))
            else:
                self.stdout.write(self.style.ERROR('Status: Critical'))
            
            self.stdout.write(f'Total Failures: {failures["total_failures"]}')
            self.stdout.write('')
            
            # Error breakdown
            if failures['error_breakdown']:
                self.stdout.write('Error Types:')
                for error_type, count in failures['error_breakdown'].items():
                    self.stdout.write(f'  {error_type}: {count}')
                self.stdout.write('')
            
            # Recommendations
            if failures['recommendations']:
                self.stdout.write('Recommendations:')
                for rec in failures['recommendations']:
                    self.stdout.write(f'  • {rec}')
            
            # Show specific failed posts if requested
            if options['post_id']:
                self.analyze_specific_post(options['post_id'])
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error analyzing failures: {str(e)}'))

    def analyze_specific_post(self, post_id):
        """Analyze a specific post's LinkedIn integration"""
        self.stdout.write('')
        self.stdout.write(f'Analyzing Post ID: {post_id}')
        self.stdout.write('-' * 30)
        
        try:
            linkedin_posts = LinkedInPost.objects.filter(post_id=post_id)
            
            if not linkedin_posts.exists():
                self.stdout.write(self.style.WARNING('No LinkedIn posts found for this blog post'))
                return
            
            for linkedin_post in linkedin_posts:
                self.stdout.write(f'LinkedIn Post Status: {linkedin_post.get_status_display()}')
                self.stdout.write(f'Image Status: {linkedin_post.get_image_upload_status_display()}')
                self.stdout.write(f'Attempts: {linkedin_post.attempt_count}')
                
                if linkedin_post.media_ids:
                    self.stdout.write(f'Media IDs: {linkedin_post.media_ids}')
                
                if linkedin_post.image_urls:
                    self.stdout.write(f'Image URLs: {linkedin_post.image_urls}')
                
                if linkedin_post.error_message:
                    self.stdout.write(self.style.ERROR(f'Error: {linkedin_post.error_message}'))
                
                if linkedin_post.image_error_message:
                    self.stdout.write(self.style.ERROR(f'Image Error: {linkedin_post.image_error_message}'))
                
                if linkedin_post.can_retry():
                    self.stdout.write(self.style.WARNING('Can be retried'))
                else:
                    self.stdout.write('Cannot be retried (max attempts reached)')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error analyzing post: {str(e)}'))

    def cleanup_metrics(self, options):
        """Clean up old metrics data"""
        self.stdout.write(self.style.SUCCESS('Cleaning up old LinkedIn image metrics'))
        
        try:
            LinkedInImageMetrics.cleanup_old_metrics()
            self.stdout.write(self.style.SUCCESS('Metrics cleanup completed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during cleanup: {str(e)}'))

    def test_configuration(self, options):
        """Test LinkedIn configuration"""
        self.stdout.write(self.style.SUCCESS('Testing LinkedIn Configuration'))
        self.stdout.write('=' * 40)
        
        try:
            # Check Django settings
            linkedin_settings = getattr(settings, 'LINKEDIN_IMAGE_SETTINGS', {})
            self.stdout.write(f'Image upload enabled: {linkedin_settings.get("ENABLE_IMAGE_UPLOAD", False)}')
            self.stdout.write(f'Image processing enabled: {linkedin_settings.get("ENABLE_IMAGE_PROCESSING", False)}')
            
            # Check LinkedIn config
            config = LinkedInConfig.get_active_config()
            if config:
                self.stdout.write(f'Active LinkedIn config: {config.name}')
                self.stdout.write(f'Has client ID: {"Yes" if config.client_id else "No"}')
                self.stdout.write(f'Has client secret: {"Yes" if config.client_secret else "No"}')
                self.stdout.write(f'Has access token: {"Yes" if config.access_token else "No"}')
            else:
                self.stdout.write(self.style.ERROR('No active LinkedIn configuration found'))
            
            # Test image processing capabilities
            try:
                from PIL import Image
                self.stdout.write('PIL (Pillow) available: Yes')
            except ImportError:
                self.stdout.write(self.style.ERROR('PIL (Pillow) available: No'))
            
            # Test cache
            from django.core.cache import cache
            test_key = 'linkedin_image_test'
            cache.set(test_key, 'test_value', 60)
            if cache.get(test_key) == 'test_value':
                self.stdout.write('Cache working: Yes')
                cache.delete(test_key)
            else:
                self.stdout.write(self.style.WARNING('Cache working: No'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error testing configuration: {str(e)}'))

    def reset_failed_posts(self, options):
        """Reset failed posts for retry"""
        self.stdout.write(self.style.SUCCESS('Resetting failed LinkedIn posts'))
        
        try:
            failed_posts = LinkedInPost.objects.filter(
                status__in=['failed', 'retrying'],
                image_upload_status='failed'
            )
            
            count = failed_posts.count()
            if count == 0:
                self.stdout.write('No failed posts found to reset')
                return
            
            if options['fix']:
                # Reset image processing status
                failed_posts.update(
                    image_upload_status='pending',
                    image_error_message='',
                    media_ids=[],
                    image_urls=[]
                )
                self.stdout.write(self.style.SUCCESS(f'Reset {count} failed posts'))
            else:
                self.stdout.write(f'Found {count} failed posts that can be reset')
                self.stdout.write('Use --fix to actually reset them')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error resetting failed posts: {str(e)}'))