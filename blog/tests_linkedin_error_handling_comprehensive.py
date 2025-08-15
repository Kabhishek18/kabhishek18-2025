"""
Comprehensive tests for LinkedIn image error handling and monitoring system.

This test suite validates:
- Error handling and categorization
- Retry logic with exponential backoff
- Monitoring and metrics collection
- Task tracking and lifecycle management
- Alert generation and threshold monitoring
"""

import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from django.core.cache import cache
from blog.services.linkedin_error_handler import (
    LinkedInImageErrorHandler, 
    LinkedInImageError, 
    ImageProcessingError, 
    ImageUploadError
)
from blog.services.linkedin_image_monitor import LinkedInImageMonitor
from blog.services.linkedin_task_monitor import LinkedInTaskMonitor, LinkedInTaskStatus
from blog.services.linkedin_error_logger import LinkedInErrorLogger


class LinkedInErrorHandlerTests(TestCase):
    """Test cases for LinkedIn error handler."""
    
    def setUp(self):
        self.error_handler = LinkedInImageErrorHandler()
        cache.clear()  # Clear cache before each test
    
    def test_error_categorization(self):
        """Test that errors are properly categorized."""
        # Test network error
        network_error = ConnectionError("Network connection failed")
        result = self.error_handler.handle_image_processing_error(
            network_error, 
            'https://example.com/image.jpg', 
            'image_download'
        )
        
        self.assertEqual(result['error_code'], 'NETWORK_ERROR')
        self.assertTrue(result['is_retryable'])
        
        # Test timeout error
        timeout_error = TimeoutError("Request timed out")
        result = self.error_handler.handle_image_processing_error(
            timeout_error,
            'https://example.com/image.jpg',
            'image_processing'
        )
        
        self.assertEqual(result['error_code'], 'TIMEOUT_ERROR')
        self.assertTrue(result['is_retryable'])
        
        # Test file size error
        size_error = ValueError("Image file too large: 25MB")
        result = self.error_handler.handle_image_processing_error(
            size_error,
            'https://example.com/large.jpg',
            'image_validation'
        )
        
        self.assertEqual(result['error_code'], 'IMAGE_TOO_LARGE')
        self.assertTrue(result['is_retryable'])
    
    def test_retry_logic_success(self):
        """Test retry logic with eventual success."""
        attempts = 0
        
        def failing_then_succeeding_function():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionError(f"Attempt {attempts} failed")
            return f"Success after {attempts} attempts"
        
        result, retry_info = self.error_handler.retry_with_backoff(
            failing_then_succeeding_function,
            error_code='NETWORK_ERROR',
            max_retries=3,
            base_delay=0.01  # Very short delay for testing
        )
        
        self.assertEqual(result, "Success after 3 attempts")
        self.assertEqual(retry_info['attempts'], 3)
        self.assertTrue(retry_info['success'])
        self.assertEqual(len(retry_info['errors']), 2)  # 2 failures before success
    
    def test_retry_logic_failure(self):
        """Test retry logic with complete failure."""
        def always_failing_function():
            raise ConnectionError("Always fails")
        
        with self.assertRaises(ConnectionError):
            self.error_handler.retry_with_backoff(
                always_failing_function,
                error_code='NETWORK_ERROR',
                max_retries=2,
                base_delay=0.01
            )
    
    def test_recovery_strategy_determination(self):
        """Test recovery strategy determination for different error types."""
        # Test image download failure
        error_details = {
            'error_code': 'IMAGE_DOWNLOAD_FAILED',
            'is_retryable': True
        }
        
        strategy = self.error_handler._determine_recovery_strategy(
            error_details, 'image_download'
        )
        
        self.assertEqual(strategy['strategy_type'], 'retry_with_fallback')
        self.assertTrue(strategy['fallback_available'])
        self.assertEqual(strategy['fallback_type'], 'alternative_image')
        
        # Test quota exceeded
        error_details = {
            'error_code': 'QUOTA_EXCEEDED',
            'is_retryable': True,
            'retry_after': 3600
        }
        
        strategy = self.error_handler._determine_recovery_strategy(
            error_details, 'image_upload'
        )
        
        self.assertEqual(strategy['strategy_type'], 'delayed_retry')
        self.assertEqual(strategy['retry_after'], 3600)
    
    def test_error_metrics_collection(self):
        """Test that error metrics are properly collected."""
        # Simulate several errors
        for i in range(3):
            self.error_handler.handle_image_processing_error(
                ConnectionError("Network error"),
                f'https://example.com/image-{i}.jpg',
                'image_download'
            )
        
        for i in range(2):
            self.error_handler.handle_image_upload_error(
                TimeoutError("Upload timeout"),
                f'https://example.com/upload-{i}.jpg',
                'media_registration'
            )
        
        # Check metrics
        metrics = self.error_handler.get_error_metrics_summary()
        
        self.assertIn('processing_metrics', metrics)
        self.assertIn('upload_metrics', metrics)
        
        # Should have processing errors
        processing_metrics = metrics['processing_metrics']
        self.assertGreater(processing_metrics.get('total_errors', 0), 0)
        
        # Should have upload errors
        upload_metrics = metrics['upload_metrics']
        self.assertGreater(upload_metrics.get('total_errors', 0), 0)


class LinkedInImageMonitorTests(TestCase):
    """Test cases for LinkedIn image monitor."""
    
    def setUp(self):
        self.monitor = LinkedInImageMonitor()
        cache.clear()
    
    def test_processing_attempt_recording(self):
        """Test recording of processing attempts."""
        self.monitor.record_image_processing_attempt(
            post_id=123,
            image_url='https://example.com/test.jpg',
            processing_step='image_download',
            context={'test': True}
        )
        
        # Check that metrics were updated
        metrics = cache.get(f"{self.monitor.cache_prefix}_processing_metrics", {})
        self.assertIn('image_download', metrics)
        self.assertEqual(metrics['image_download']['attempts'], 1)
    
    def test_processing_success_recording(self):
        """Test recording of processing successes."""
        self.monitor.record_image_processing_success(
            post_id=123,
            image_url='https://example.com/test.jpg',
            processing_step='image_validation',
            processing_time=1.5,
            result_data={'is_valid': True}
        )
        
        # Check metrics
        metrics = cache.get(f"{self.monitor.cache_prefix}_processing_metrics", {})
        self.assertIn('image_validation', metrics)
        self.assertEqual(metrics['image_validation']['successes'], 1)
        
        # Check performance metrics
        perf_key = f"{self.monitor.cache_prefix}_performance_image_validation"
        perf_data = cache.get(perf_key, {})
        self.assertEqual(perf_data['count'], 1)
        self.assertEqual(perf_data['total_time'], 1.5)
    
    def test_processing_failure_recording(self):
        """Test recording of processing failures."""
        error = ConnectionError("Network failed")
        
        self.monitor.record_image_processing_failure(
            post_id=123,
            image_url='https://example.com/test.jpg',
            processing_step='image_download',
            error=error,
            processing_time=2.0
        )
        
        # Check metrics
        metrics = cache.get(f"{self.monitor.cache_prefix}_processing_metrics", {})
        self.assertIn('image_download', metrics)
        self.assertEqual(metrics['image_download']['failures'], 1)
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        # Record some successes and failures
        for i in range(7):  # 7 successes
            self.monitor.record_image_processing_attempt(i, f'url-{i}', 'test_step')
            self.monitor.record_image_processing_success(i, f'url-{i}', 'test_step', 1.0)
        
        for i in range(3):  # 3 failures
            self.monitor.record_image_processing_attempt(100+i, f'url-fail-{i}', 'test_step')
            self.monitor.record_image_processing_failure(100+i, f'url-fail-{i}', 'test_step', Exception("Failed"))
        
        success_rates = self.monitor.get_success_rates()
        
        # Should have 70% success rate (7 successes out of 10 attempts)
        self.assertAlmostEqual(success_rates['processing_test_step'], 0.7, places=2)
    
    def test_dashboard_data_generation(self):
        """Test dashboard data generation."""
        # Add some test data
        self.monitor.record_image_processing_attempt(1, 'url1', 'download')
        self.monitor.record_image_processing_success(1, 'url1', 'download', 1.0)
        
        dashboard = self.monitor.get_dashboard_data()
        
        self.assertIn('generated_at', dashboard)
        self.assertIn('overview', dashboard)
        self.assertIn('processing_metrics', dashboard)
        self.assertIn('performance_metrics', dashboard)
        self.assertIn('recommendations', dashboard)
        
        # Check overview
        overview = dashboard['overview']
        self.assertIn('overall_success_rate', overview)
        self.assertIn('system_health', overview)
    
    def test_alert_generation(self):
        """Test alert generation based on thresholds."""
        # Simulate high failure rate to trigger alerts
        for i in range(10):  # 10 failures
            self.monitor.record_image_processing_attempt(i, f'url-{i}', 'failing_step')
            self.monitor.record_image_processing_failure(i, f'url-{i}', 'failing_step', Exception("Failed"))
        
        dashboard = self.monitor.get_dashboard_data()
        alerts = dashboard['alerts']
        
        # Should have alerts due to 0% success rate
        self.assertGreater(len(alerts), 0)
        
        # Check for critical alert
        critical_alerts = [alert for alert in alerts if alert['type'] == 'critical']
        self.assertGreater(len(critical_alerts), 0)


class LinkedInTaskMonitorTests(TestCase):
    """Test cases for LinkedIn task monitor."""
    
    def setUp(self):
        self.task_monitor = LinkedInTaskMonitor()
        cache.clear()
    
    def test_task_creation(self):
        """Test task creation and initial state."""
        task_id = self.task_monitor.create_task(
            'image_processing',
            post_id=123,
            context={'test': True}
        )
        
        self.assertIsNotNone(task_id)
        
        # Check task data
        task_data = self.task_monitor.get_task_status(task_id)
        self.assertIsNotNone(task_data)
        self.assertEqual(task_data['task_type'], 'image_processing')
        self.assertEqual(task_data['post_id'], 123)
        self.assertEqual(task_data['status'], LinkedInTaskStatus.PENDING)
        self.assertEqual(task_data['retry_count'], 0)
    
    def test_task_lifecycle(self):
        """Test complete task lifecycle."""
        # Create task
        task_id = self.task_monitor.create_task('test_task', 456)
        
        # Start task
        success = self.task_monitor.start_task(task_id)
        self.assertTrue(success)
        
        task_data = self.task_monitor.get_task_status(task_id)
        self.assertEqual(task_data['status'], LinkedInTaskStatus.RUNNING)
        self.assertIsNotNone(task_data['started_at'])
        
        # Add steps
        self.task_monitor.add_task_step(task_id, 'step1', {'data': 'test'})
        self.task_monitor.complete_task_step(task_id, 'step1', {'result': 'success'})
        
        self.task_monitor.add_task_step(task_id, 'step2')
        self.task_monitor.complete_task_step(task_id, 'step2', error=Exception("Step failed"))
        
        # Complete task
        self.task_monitor.complete_task(task_id, error=Exception("Task failed"))
        
        # Check final state
        task_data = self.task_monitor.get_task_status(task_id)
        self.assertEqual(task_data['status'], LinkedInTaskStatus.FAILED)
        self.assertIsNotNone(task_data['completed_at'])
        self.assertEqual(len(task_data['steps']), 2)
        self.assertEqual(len(task_data['errors']), 1)
    
    def test_task_retry(self):
        """Test task retry functionality."""
        task_id = self.task_monitor.create_task('retry_test', 789)
        
        # Mark for retry
        success = self.task_monitor.retry_task(task_id, "Network error")
        self.assertTrue(success)
        
        task_data = self.task_monitor.get_task_status(task_id)
        self.assertEqual(task_data['status'], LinkedInTaskStatus.RETRYING)
        self.assertEqual(task_data['retry_count'], 1)
        self.assertEqual(task_data['retry_reason'], "Network error")
        
        # Test max retries
        for i in range(3):  # Should exceed max retries
            self.task_monitor.retry_task(task_id, f"Retry {i+2}")
        
        # Should not be able to retry anymore
        success = self.task_monitor.retry_task(task_id, "Final retry")
        self.assertFalse(success)
    
    def test_task_cancellation(self):
        """Test task cancellation."""
        task_id = self.task_monitor.create_task('cancel_test', 999)
        
        success = self.task_monitor.cancel_task(task_id, "User requested")
        self.assertTrue(success)
        
        task_data = self.task_monitor.get_task_status(task_id)
        self.assertEqual(task_data['status'], LinkedInTaskStatus.CANCELLED)
        self.assertEqual(task_data['cancellation_reason'], "User requested")
    
    def test_task_summary(self):
        """Test task summary generation."""
        task_id = self.task_monitor.create_task('summary_test', 111)
        self.task_monitor.start_task(task_id)
        
        # Add some steps
        self.task_monitor.add_task_step(task_id, 'step1')
        self.task_monitor.complete_task_step(task_id, 'step1', {'result': 'ok'})
        
        self.task_monitor.add_task_step(task_id, 'step2')
        self.task_monitor.complete_task_step(task_id, 'step2', error=Exception("Failed"))
        
        self.task_monitor.complete_task(task_id)
        
        # Get summary
        summary = self.task_monitor.get_task_summary(task_id)
        
        self.assertIsNotNone(summary)
        self.assertEqual(summary['task_id'], task_id)
        self.assertEqual(summary['post_id'], 111)
        self.assertEqual(summary['step_count'], 2)
        self.assertEqual(summary['successful_steps'], 1)
        self.assertEqual(summary['failed_steps'], 1)
        self.assertEqual(summary['step_success_rate'], 0.5)
    
    def test_queue_metrics(self):
        """Test queue metrics collection."""
        # Create several tasks
        for i in range(3):
            task_id = self.task_monitor.create_task('metric_test', 200 + i)
            self.task_monitor.start_task(task_id)
            
            if i < 2:  # Complete 2 successfully
                self.task_monitor.complete_task(task_id, {'result': 'success'})
            else:  # Fail 1
                self.task_monitor.complete_task(task_id, error=Exception("Failed"))
        
        metrics = self.task_monitor.get_queue_metrics()
        
        self.assertIn('metric_test', metrics)
        task_metrics = metrics['metric_test']
        
        self.assertEqual(task_metrics['created'], 3)
        self.assertEqual(task_metrics['started'], 3)
        self.assertEqual(task_metrics['completed'], 2)
        self.assertEqual(task_metrics['failed'], 1)
    
    def test_health_report(self):
        """Test health report generation."""
        # Create tasks with mixed results
        for i in range(5):
            task_id = self.task_monitor.create_task('health_test', 300 + i)
            self.task_monitor.start_task(task_id)
            
            if i < 4:  # 80% success rate
                self.task_monitor.complete_task(task_id, {'result': 'success'})
            else:
                self.task_monitor.complete_task(task_id, error=Exception("Failed"))
        
        health_report = self.task_monitor.get_task_health_report()
        
        self.assertIn('queue_health', health_report)
        self.assertIn('performance_health', health_report)
        self.assertIn('recommendations', health_report)
        
        # Should be healthy with 80% success rate
        queue_health = health_report['queue_health']
        self.assertIn(queue_health['status'], ['healthy', 'degraded'])  # Might be degraded due to 20% failure


class LinkedInErrorLoggerTests(TestCase):
    """Test cases for LinkedIn error logger."""
    
    def setUp(self):
        self.error_logger = LinkedInErrorLogger()
        cache.clear()
    
    def test_authentication_error_logging(self):
        """Test authentication error logging."""
        error_details = {
            'message': 'Token expired',
            'error_code': 'TOKEN_EXPIRED',
            'status_code': 401
        }
        
        self.error_logger.log_authentication_error(error_details)
        
        # Check that metrics were updated
        cache_key = f"{self.error_logger.cache_prefix}_authentication"
        metrics = cache.get(cache_key, {})
        
        self.assertEqual(metrics['count'], 1)
        self.assertIn('warning', metrics['severity_counts'])
    
    def test_rate_limit_error_logging(self):
        """Test rate limit error logging."""
        error_details = {
            'message': 'Rate limit exceeded',
            'retry_after': 300,
            'quota_type': 'hourly',
            'status_code': 429
        }
        
        self.error_logger.log_rate_limit_error(error_details)
        
        # Check metrics
        cache_key = f"{self.error_logger.cache_prefix}_rate_limiting"
        metrics = cache.get(cache_key, {})
        
        self.assertEqual(metrics['count'], 1)
    
    def test_media_upload_error_logging(self):
        """Test media upload error logging."""
        error_details = {
            'message': 'Image too large',
            'image_url': 'https://example.com/large.jpg',
            'status_code': 400
        }
        
        context = {
            'fallback_to_text': True,
            'image_format': 'jpg'
        }
        
        self.error_logger.log_media_upload_error(error_details, context)
        
        # Check metrics
        cache_key = f"{self.error_logger.cache_prefix}_media_upload"
        metrics = cache.get(cache_key, {})
        
        self.assertEqual(metrics['count'], 1)
    
    def test_error_summary_generation(self):
        """Test error summary generation."""
        # Log various types of errors
        self.error_logger.log_authentication_error({
            'message': 'Auth failed',
            'error_code': 'AUTH_FAILED'
        })
        
        self.error_logger.log_rate_limit_error({
            'message': 'Rate limited',
            'retry_after': 300
        })
        
        self.error_logger.log_media_upload_error({
            'message': 'Upload failed',
            'image_url': 'test.jpg'
        })
        
        # Get summary
        summary = self.error_logger.get_error_summary()
        
        self.assertGreater(summary['total_errors'], 0)
        self.assertIn('categories', summary)
        
        categories = summary['categories']
        self.assertIn('authentication', categories)
        self.assertIn('rate_limiting', categories)
        self.assertIn('media_upload', categories)


class IntegrationTests(TestCase):
    """Integration tests for the complete error handling system."""
    
    def setUp(self):
        self.error_handler = LinkedInImageErrorHandler()
        self.monitor = LinkedInImageMonitor()
        self.task_monitor = LinkedInTaskMonitor()
        cache.clear()
    
    def test_end_to_end_error_handling(self):
        """Test end-to-end error handling workflow."""
        # Create a task
        task_id = self.task_monitor.create_task('integration_test', 999)
        self.task_monitor.start_task(task_id)
        
        # Simulate processing with error
        self.task_monitor.add_task_step(task_id, 'image_download', {
            'image_url': 'https://example.com/test.jpg'
        })
        
        # Simulate error in processing
        error = ConnectionError("Network failed")
        
        # Handle error through error handler
        error_result = self.error_handler.handle_image_processing_error(
            error, 'https://example.com/test.jpg', 'image_download'
        )
        
        # Record failure in monitor
        self.monitor.record_image_processing_failure(
            999, 'https://example.com/test.jpg', 'image_download', error
        )
        
        # Complete task step with error
        self.task_monitor.complete_task_step(task_id, 'image_download', error=error)
        
        # Complete task
        self.task_monitor.complete_task(task_id, error=error)
        
        # Verify all systems recorded the error
        self.assertTrue(error_result['error_handled'])
        self.assertEqual(error_result['error_code'], 'NETWORK_ERROR')
        
        # Check monitor recorded the failure
        success_rates = self.monitor.get_success_rates()
        self.assertEqual(success_rates.get('processing_image_download', 1.0), 0.0)
        
        # Check task completed with failure
        task_summary = self.task_monitor.get_task_summary(task_id)
        self.assertEqual(task_summary['status'], LinkedInTaskStatus.FAILED)
        self.assertEqual(task_summary['error_count'], 1)
    
    def test_retry_with_monitoring(self):
        """Test retry logic with monitoring integration."""
        attempts = 0
        
        def flaky_function():
            nonlocal attempts
            attempts += 1
            
            # Record attempt in monitor
            self.monitor.record_image_processing_attempt(
                888, f'https://example.com/retry-{attempts}.jpg', 'retry_test'
            )
            
            if attempts < 3:
                error = ConnectionError(f"Attempt {attempts} failed")
                self.monitor.record_image_processing_failure(
                    888, f'https://example.com/retry-{attempts}.jpg', 'retry_test', error
                )
                raise error
            
            # Success on third attempt
            self.monitor.record_image_processing_success(
                888, f'https://example.com/retry-{attempts}.jpg', 'retry_test', 1.0
            )
            return "Success"
        
        # Execute with retry
        result, retry_info = self.error_handler.retry_with_backoff(
            flaky_function,
            error_code='NETWORK_ERROR',
            max_retries=3,
            base_delay=0.01
        )
        
        self.assertEqual(result, "Success")
        self.assertEqual(retry_info['attempts'], 3)
        
        # Check monitoring recorded all attempts
        success_rates = self.monitor.get_success_rates()
        # Should have 33% success rate (1 success out of 3 attempts)
        self.assertAlmostEqual(success_rates.get('processing_retry_test', 0), 1/3, places=2)


if __name__ == '__main__':
    unittest.main()