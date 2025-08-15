"""
Management command to demonstrate LinkedIn image error handling and monitoring system.

This command showcases the comprehensive error handling, logging, and monitoring
capabilities of the LinkedIn image integration system.
"""

import time
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from blog.services.linkedin_error_handler import LinkedInImageErrorHandler, ImageProcessingError, ImageUploadError
from blog.services.linkedin_image_monitor import LinkedInImageMonitor
from blog.services.linkedin_task_monitor import LinkedInTaskMonitor
from blog.services.linkedin_error_logger import LinkedInErrorLogger


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Demonstrate LinkedIn image error handling and monitoring system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--demo-type',
            type=str,
            choices=['error-handling', 'monitoring', 'task-tracking', 'all'],
            default='all',
            help='Type of demonstration to run'
        )
        
        parser.add_argument(
            '--simulate-errors',
            action='store_true',
            help='Simulate various error scenarios'
        )
        
        parser.add_argument(
            '--show-dashboard',
            action='store_true',
            help='Display monitoring dashboard data'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('LinkedIn Image Error Handling & Monitoring Demo')
        )
        self.stdout.write('=' * 60)
        
        demo_type = options['demo_type']
        
        if demo_type in ['error-handling', 'all']:
            self.demonstrate_error_handling(options['simulate_errors'])
        
        if demo_type in ['monitoring', 'all']:
            self.demonstrate_monitoring(options['show_dashboard'])
        
        if demo_type in ['task-tracking', 'all']:
            self.demonstrate_task_tracking()
        
        self.stdout.write(
            self.style.SUCCESS('\nDemo completed successfully!')
        )
    
    def demonstrate_error_handling(self, simulate_errors=False):
        """Demonstrate comprehensive error handling capabilities."""
        self.stdout.write('\n' + self.style.WARNING('=== Error Handling Demo ==='))
        
        error_handler = LinkedInImageErrorHandler()
        
        # Demonstrate error categorization
        self.stdout.write('\n1. Error Categorization:')
        
        # Simulate different types of errors
        test_errors = [
            {
                'error': ConnectionError("Network connection failed"),
                'image_url': 'https://example.com/test-image.jpg',
                'step': 'image_download',
                'expected_code': 'NETWORK_ERROR'
            },
            {
                'error': TimeoutError("Request timed out"),
                'image_url': 'https://example.com/large-image.jpg',
                'step': 'image_processing',
                'expected_code': 'TIMEOUT_ERROR'
            },
            {
                'error': ValueError("Image file too large: 25MB"),
                'image_url': 'https://example.com/huge-image.jpg',
                'step': 'image_validation',
                'expected_code': 'IMAGE_TOO_LARGE'
            },
            {
                'error': Exception("Unsupported image format: WEBP"),
                'image_url': 'https://example.com/image.webp',
                'step': 'image_processing',
                'expected_code': 'UNSUPPORTED_FORMAT'
            }
        ]
        
        for i, test_case in enumerate(test_errors, 1):
            self.stdout.write(f'  {i}. Testing {test_case["expected_code"]}...')
            
            result = error_handler.handle_image_processing_error(
                test_case['error'],
                test_case['image_url'],
                test_case['step'],
                {'test_case': True}
            )
            
            self.stdout.write(f'     ✓ Error handled: {result["error_code"]}')
            self.stdout.write(f'     ✓ Retryable: {result["is_retryable"]}')
            self.stdout.write(f'     ✓ Recovery strategy: {result["recovery_strategy"]["strategy_type"]}')
        
        # Demonstrate retry logic
        self.stdout.write('\n2. Retry Logic with Exponential Backoff:')
        
        def failing_function():
            """Function that fails a few times then succeeds."""
            if not hasattr(failing_function, 'attempts'):
                failing_function.attempts = 0
            
            failing_function.attempts += 1
            
            if failing_function.attempts < 3:
                raise ConnectionError(f"Attempt {failing_function.attempts} failed")
            
            return f"Success after {failing_function.attempts} attempts"
        
        try:
            result, retry_info = error_handler.retry_with_backoff(
                failing_function,
                error_code='NETWORK_ERROR',
                max_retries=3,
                base_delay=0.1  # Short delay for demo
            )
            
            self.stdout.write(f'     ✓ Function succeeded: {result}')
            self.stdout.write(f'     ✓ Total attempts: {retry_info["attempts"]}')
            self.stdout.write(f'     ✓ Total delay: {retry_info["total_delay"]:.2f}s')
            
        except Exception as e:
            self.stdout.write(f'     ✗ Function failed: {e}')
        
        # Show error metrics
        self.stdout.write('\n3. Error Metrics Summary:')
        metrics = error_handler.get_error_metrics_summary()
        
        if metrics['processing_metrics']:
            self.stdout.write('     Processing Metrics:')
            for step, data in metrics['processing_metrics'].items():
                self.stdout.write(f'       - {step}: {data.get("total_errors", 0)} errors')
        
        if metrics['upload_metrics']:
            self.stdout.write('     Upload Metrics:')
            for stage, data in metrics['upload_metrics'].items():
                self.stdout.write(f'       - {stage}: {data.get("total_errors", 0)} errors')
        
        performance = metrics.get('performance_analysis', {})
        self.stdout.write(f'     Overall Health: {performance.get("overall_health", "unknown")}')
        
        if performance.get('issues_detected'):
            self.stdout.write('     Issues Detected:')
            for issue in performance['issues_detected']:
                self.stdout.write(f'       - {issue}')
    
    def demonstrate_monitoring(self, show_dashboard=False):
        """Demonstrate monitoring and dashboard capabilities."""
        self.stdout.write('\n' + self.style.WARNING('=== Monitoring Demo ==='))
        
        monitor = LinkedInImageMonitor()
        
        # Simulate some processing activities
        self.stdout.write('\n1. Simulating Image Processing Activities:')
        
        # Simulate successful processing
        for i in range(5):
            post_id = 100 + i
            image_url = f'https://example.com/image-{i}.jpg'
            
            monitor.record_image_processing_attempt(post_id, image_url, 'image_download')
            time.sleep(0.1)  # Simulate processing time
            monitor.record_image_processing_success(
                post_id, image_url, 'image_download', 
                processing_time=0.5 + (i * 0.1),
                result_data={'file_size': 1024 * (i + 1)}
            )
            
            monitor.record_image_processing_attempt(post_id, image_url, 'image_validation')
            time.sleep(0.05)
            monitor.record_image_processing_success(
                post_id, image_url, 'image_validation',
                processing_time=0.2,
                result_data={'is_valid': True}
            )
        
        # Simulate some failures
        for i in range(2):
            post_id = 200 + i
            image_url = f'https://example.com/bad-image-{i}.jpg'
            
            monitor.record_image_processing_attempt(post_id, image_url, 'image_download')
            time.sleep(0.1)
            monitor.record_image_processing_failure(
                post_id, image_url, 'image_download',
                error=ConnectionError("Network timeout"),
                processing_time=2.0
            )
        
        self.stdout.write('     ✓ Simulated 5 successful and 2 failed processing attempts')
        
        # Simulate upload activities
        self.stdout.write('\n2. Simulating Upload Activities:')
        
        for i in range(3):
            post_id = 300 + i
            image_url = f'https://example.com/upload-image-{i}.jpg'
            
            monitor.record_image_upload_attempt(post_id, image_url, 'media_registration')
            time.sleep(0.1)
            monitor.record_image_upload_success(
                post_id, image_url, 'media_registration',
                upload_time=1.0 + (i * 0.2),
                media_id=f'media-{i}',
                result_data={'upload_url': f'https://linkedin.com/media/{i}'}
            )
        
        self.stdout.write('     ✓ Simulated 3 successful upload attempts')
        
        # Show success rates
        self.stdout.write('\n3. Current Success Rates:')
        success_rates = monitor.get_success_rates()
        
        for operation, rate in success_rates.items():
            percentage = rate * 100
            status = '✓' if rate >= 0.8 else '⚠' if rate >= 0.5 else '✗'
            self.stdout.write(f'     {status} {operation}: {percentage:.1f}%')
        
        # Show dashboard data if requested
        if show_dashboard:
            self.stdout.write('\n4. Dashboard Data:')
            dashboard = monitor.get_dashboard_data()
            
            overview = dashboard['overview']
            self.stdout.write(f'     Overall Success Rate: {overview["overall_success_rate"]:.2%}')
            self.stdout.write(f'     Total Operations: {overview["total_operations"]}')
            self.stdout.write(f'     System Health: {overview["system_health"]}')
            self.stdout.write(f'     Active Alerts: {overview["active_alerts"]}')
            
            if dashboard['recommendations']:
                self.stdout.write('     Recommendations:')
                for rec in dashboard['recommendations']:
                    self.stdout.write(f'       - {rec}')
    
    def demonstrate_task_tracking(self):
        """Demonstrate task-specific monitoring capabilities."""
        self.stdout.write('\n' + self.style.WARNING('=== Task Tracking Demo ==='))
        
        task_monitor = LinkedInTaskMonitor()
        
        # Create and execute a sample task
        self.stdout.write('\n1. Creating and Executing Sample Task:')
        
        task_id = task_monitor.create_task(
            'image_processing',
            post_id=123,
            context={'post_title': 'Sample Blog Post', 'author': 'Demo User'}
        )
        
        self.stdout.write(f'     ✓ Created task: {task_id}')
        
        # Start the task
        task_monitor.start_task(task_id)
        self.stdout.write('     ✓ Started task')
        
        # Add and complete steps
        steps = [
            ('image_selection', 0.5, None),
            ('image_download', 1.2, None),
            ('image_validation', 0.3, None),
            ('image_processing', 2.1, None),
            ('image_upload', 3.0, ConnectionError("Upload failed"))  # Simulate failure
        ]
        
        for step_name, duration, error in steps:
            task_monitor.add_task_step(
                task_id, 
                step_name, 
                {'image_url': 'https://example.com/test.jpg'}
            )
            
            time.sleep(0.1)  # Simulate processing time
            
            if error:
                task_monitor.complete_task_step(task_id, step_name, error=error)
                self.stdout.write(f'     ✗ Step {step_name} failed: {error}')
                break
            else:
                task_monitor.complete_task_step(
                    task_id, 
                    step_name, 
                    {'duration': duration, 'status': 'success'}
                )
                self.stdout.write(f'     ✓ Step {step_name} completed ({duration}s)')
        
        # Complete the task with failure
        task_monitor.complete_task(task_id, error=ConnectionError("Upload failed"))
        self.stdout.write('     ✗ Task completed with failure')
        
        # Show task summary
        self.stdout.write('\n2. Task Summary:')
        summary = task_monitor.get_task_summary(task_id)
        
        if summary:
            self.stdout.write(f'     Task ID: {summary["task_id"]}')
            self.stdout.write(f'     Status: {summary["status"]}')
            self.stdout.write(f'     Duration: {summary.get("duration", "N/A")}s')
            self.stdout.write(f'     Steps: {summary["step_count"]}')
            self.stdout.write(f'     Errors: {summary["error_count"]}')
            self.stdout.write(f'     Retry Count: {summary["retry_count"]}')
            
            if 'step_success_rate' in summary:
                self.stdout.write(f'     Step Success Rate: {summary["step_success_rate"]:.2%}')
        
        # Show queue metrics
        self.stdout.write('\n3. Queue Metrics:')
        queue_metrics = task_monitor.get_queue_metrics()
        
        for task_type, metrics in queue_metrics.items():
            self.stdout.write(f'     {task_type}:')
            self.stdout.write(f'       Created: {metrics.get("created", 0)}')
            self.stdout.write(f'       Started: {metrics.get("started", 0)}')
            self.stdout.write(f'       Completed: {metrics.get("completed", 0)}')
            self.stdout.write(f'       Failed: {metrics.get("failed", 0)}')
        
        # Show health report
        self.stdout.write('\n4. Task Health Report:')
        health_report = task_monitor.get_task_health_report()
        
        queue_health = health_report['queue_health']
        self.stdout.write(f'     Queue Health: {queue_health["status"]}')
        
        if queue_health['issues']:
            self.stdout.write('     Issues:')
            for issue in queue_health['issues']:
                self.stdout.write(f'       - {issue}')
        
        if health_report['recommendations']:
            self.stdout.write('     Recommendations:')
            for rec in health_report['recommendations']:
                self.stdout.write(f'       - {rec}')
    
    def show_comprehensive_status(self):
        """Show comprehensive status of all monitoring systems."""
        self.stdout.write('\n' + self.style.SUCCESS('=== Comprehensive System Status ==='))
        
        # Error logger summary
        error_logger = LinkedInErrorLogger()
        error_summary = error_logger.get_error_summary()
        
        self.stdout.write('\n1. Error Summary (Last 24 Hours):')
        self.stdout.write(f'     Total Errors: {error_summary["total_errors"]}')
        self.stdout.write(f'     Critical Errors: {error_summary["critical_errors"]}')
        
        if error_summary['categories']:
            self.stdout.write('     By Category:')
            for category, data in error_summary['categories'].items():
                count = data.get('count', 0)
                if count > 0:
                    self.stdout.write(f'       - {category}: {count}')
        
        # Image monitor dashboard
        monitor = LinkedInImageMonitor()
        dashboard = monitor.get_dashboard_data()
        
        self.stdout.write('\n2. Image Processing Status:')
        overview = dashboard['overview']
        self.stdout.write(f'     System Health: {overview["system_health"]}')
        self.stdout.write(f'     Overall Success Rate: {overview["overall_success_rate"]:.2%}')
        self.stdout.write(f'     Total Operations: {overview["total_operations"]}')
        
        if dashboard['alerts']:
            self.stdout.write('     Active Alerts:')
            for alert in dashboard['alerts']:
                self.stdout.write(f'       - {alert["type"].upper()}: {alert["message"]}')
        
        # Task monitor status
        task_monitor = LinkedInTaskMonitor()
        health_report = task_monitor.get_task_health_report()
        
        self.stdout.write('\n3. Task System Status:')
        self.stdout.write(f'     Queue Health: {health_report["queue_health"]["status"]}')
        self.stdout.write(f'     Performance Health: {health_report["performance_health"]["status"]}')
        
        self.stdout.write('\n' + '=' * 60)