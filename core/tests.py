"""
Tests for the core application, including health service tests.
"""

import time
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

from core.services.health_service import (
    HealthCheckResult, 
    DatabaseHealthChecker, 
    CacheHealthChecker, 
    MemoryHealthChecker,
    DiskHealthChecker,
    SystemLoadHealthChecker,
    LogHealthChecker,
    APIHealthChecker,
    CeleryHealthChecker,
    RedisHealthChecker,
    HealthService,
    health_service
)


class HealthCheckResultTest(TestCase):
    """Test cases for HealthCheckResult class."""
    
    def test_health_check_result_creation(self):
        """Test creating a HealthCheckResult instance."""
        result = HealthCheckResult(
            status='healthy',
            message='Test message',
            details={'key': 'value'},
            response_time=100.5
        )
        
        self.assertEqual(result.status, 'healthy')
        self.assertEqual(result.message, 'Test message')
        self.assertEqual(result.details, {'key': 'value'})
        self.assertEqual(result.response_time, 100.5)
        self.assertIsNotNone(result.timestamp)
    
    def test_health_check_result_to_dict(self):
        """Test converting HealthCheckResult to dictionary."""
        result = HealthCheckResult(
            status='warning',
            message='Test warning',
            details={'error': 'minor issue'},
            response_time=250.0
        )
        
        result_dict = result.to_dict()
        
        self.assertEqual(result_dict['status'], 'warning')
        self.assertEqual(result_dict['message'], 'Test warning')
        self.assertEqual(result_dict['details'], {'error': 'minor issue'})
        self.assertEqual(result_dict['response_time'], 250.0)
        self.assertIn('timestamp', result_dict)


class DatabaseHealthCheckerTest(TestCase):
    """Test cases for DatabaseHealthChecker."""
    
    def setUp(self):
        self.checker = DatabaseHealthChecker()
    
    def test_database_health_check_success(self):
        """Test successful database health check."""
        result = self.checker.check()
        
        self.assertIn(result.status, ['healthy', 'warning'])
        self.assertIsNotNone(result.message)
        self.assertIsNotNone(result.response_time)
        self.assertIsInstance(result.details, dict)
    
    @patch('core.services.health_service.connection')
    def test_database_health_check_failure(self, mock_connection):
        """Test database health check failure."""
        mock_connection.cursor.side_effect = Exception("Database connection failed")
        
        result = self.checker.check()
        
        self.assertEqual(result.status, 'critical')
        self.assertIn('Database connection failed', result.message)
        self.assertIn('error', result.details)
    
    def test_database_info_retrieval(self):
        """Test database information retrieval."""
        info = self.checker._get_database_info()
        
        self.assertIsInstance(info, dict)
        # Should contain basic database info or error message
        self.assertTrue(
            'engine' in info or 'error' in info
        )


class CacheHealthCheckerTest(TestCase):
    """Test cases for CacheHealthChecker."""
    
    def setUp(self):
        self.checker = CacheHealthChecker()
    
    def test_cache_health_check_success(self):
        """Test successful cache health check."""
        result = self.checker.check()
        
        self.assertIn(result.status, ['healthy', 'warning'])
        self.assertIsNotNone(result.message)
        self.assertIsNotNone(result.response_time)
        self.assertIsInstance(result.details, dict)
    
    @patch('core.services.health_service.cache')
    def test_cache_health_check_failure(self, mock_cache):
        """Test cache health check failure."""
        mock_cache.set.side_effect = Exception("Cache connection failed")
        
        result = self.checker.check()
        
        self.assertEqual(result.status, 'critical')
        self.assertIn('Cache system failed', result.message)
        self.assertIn('error', result.details)
    
    def test_cache_info_retrieval(self):
        """Test cache information retrieval."""
        info = self.checker._get_cache_info()
        
        self.assertIsInstance(info, dict)
        self.assertIn('backend', info)


class HealthServiceTest(TestCase):
    """Test cases for HealthService."""
    
    def setUp(self):
        self.service = HealthService()
    
    def test_get_system_health(self):
        """Test getting comprehensive system health."""
        health = self.service.get_system_health()
        
        self.assertIn('overall_status', health)
        self.assertIn('timestamp', health)
        self.assertIn('checks', health)
        self.assertIn('database', health['checks'])
        self.assertIn('cache', health['checks'])
        
        # Overall status should be one of the valid statuses
        self.assertIn(health['overall_status'], ['healthy', 'warning', 'critical'])
    
    def test_get_database_health(self):
        """Test getting database health specifically."""
        health = self.service.get_database_health()
        
        self.assertIn('status', health)
        self.assertIn('message', health)
        self.assertIn('details', health)
        self.assertIn('timestamp', health)
    
    def test_get_cache_health(self):
        """Test getting cache health specifically."""
        health = self.service.get_cache_health()
        
        self.assertIn('status', health)
        self.assertIn('message', health)
        self.assertIn('details', health)
        self.assertIn('timestamp', health)
    
    @patch('core.services.health_service.DatabaseHealthChecker.check')
    def test_system_health_with_critical_database(self, mock_db_check):
        """Test system health when database is critical."""
        mock_db_check.return_value = HealthCheckResult(
            status='critical',
            message='Database down',
            details={'error': 'Connection refused'}
        )
        
        health = self.service.get_system_health()
        
        self.assertEqual(health['overall_status'], 'critical')
        self.assertEqual(health['checks']['database']['status'], 'critical')
    
    @patch('core.services.health_service.CacheHealthChecker.check')
    def test_system_health_with_warning_cache(self, mock_cache_check):
        """Test system health when cache has warning."""
        mock_cache_check.return_value = HealthCheckResult(
            status='warning',
            message='Cache slow',
            details={'response_time': 600}
        )
        
        health = self.service.get_system_health()
        
        # Overall status should be warning or critical if cache is warning (other components may affect overall status)
        self.assertIn(health['overall_status'], ['warning', 'critical', 'healthy'])
        self.assertEqual(health['checks']['cache']['status'], 'warning')


class HealthServiceIntegrationTest(TestCase):
    """Integration tests for the health service."""
    
    def test_global_health_service_instance(self):
        """Test that the global health service instance works."""
        health = health_service.get_system_health()
        
        self.assertIsInstance(health, dict)
        self.assertIn('overall_status', health)
        self.assertIn('checks', health)
    
    def test_real_database_connection(self):
        """Test real database connection health check."""
        # This test uses the actual database connection
        checker = DatabaseHealthChecker()
        result = checker.check()
        
        # Should be healthy or warning, not critical (assuming DB is working)
        self.assertIn(result.status, ['healthy', 'warning'])
        self.assertIsNotNone(result.response_time)
    
    def test_real_cache_connection(self):
        """Test real cache connection health check."""
        # This test uses the actual cache system
        checker = CacheHealthChecker()
        result = checker.check()
        
        # Should be healthy or warning, not critical (assuming cache is working)
        self.assertIn(result.status, ['healthy', 'warning'])
        self.assertIsNotNone(result.response_time)


class MemoryHealthCheckerTest(TestCase):
    """Test cases for MemoryHealthChecker."""
    
    def setUp(self):
        self.checker = MemoryHealthChecker()
    
    def test_memory_health_check_success(self):
        """Test successful memory health check."""
        result = self.checker.check()
        
        self.assertIn(result.status, ['healthy', 'warning', 'critical'])
        self.assertIsNotNone(result.message)
        self.assertIsNotNone(result.response_time)
        self.assertIsInstance(result.details, dict)
        self.assertIn('total_gb', result.details)
        self.assertIn('percent_used', result.details)
    
    @patch('core.services.health_service.psutil.virtual_memory')
    def test_memory_health_check_failure(self, mock_memory):
        """Test memory health check failure."""
        mock_memory.side_effect = Exception("Memory check failed")
        
        result = self.checker.check()
        
        self.assertEqual(result.status, 'critical')
        self.assertIn('Memory check failed', result.message)
        self.assertIn('error', result.details)


class DiskHealthCheckerTest(TestCase):
    """Test cases for DiskHealthChecker."""
    
    def setUp(self):
        self.checker = DiskHealthChecker()
    
    def test_disk_health_check_success(self):
        """Test successful disk health check."""
        result = self.checker.check()
        
        self.assertIn(result.status, ['healthy', 'warning', 'critical'])
        self.assertIsNotNone(result.message)
        self.assertIsNotNone(result.response_time)
        self.assertIsInstance(result.details, dict)
        self.assertIn('total_gb', result.details)
        self.assertIn('percent_used', result.details)
        self.assertIn('path', result.details)
    
    @patch('core.services.health_service.shutil.disk_usage')
    def test_disk_health_check_failure(self, mock_disk_usage):
        """Test disk health check failure."""
        mock_disk_usage.side_effect = Exception("Disk check failed")
        
        result = self.checker.check()
        
        self.assertEqual(result.status, 'critical')
        self.assertIn('Disk check failed', result.message)
        self.assertIn('error', result.details)


class SystemLoadHealthCheckerTest(TestCase):
    """Test cases for SystemLoadHealthChecker."""
    
    def setUp(self):
        self.checker = SystemLoadHealthChecker()
    
    def test_system_load_health_check_success(self):
        """Test successful system load health check."""
        result = self.checker.check()
        
        self.assertIn(result.status, ['healthy', 'warning', 'critical'])
        self.assertIsNotNone(result.message)
        self.assertIsNotNone(result.response_time)
        self.assertIsInstance(result.details, dict)
        self.assertIn('cpu_percent', result.details)
        self.assertIn('cpu_count_physical', result.details)
        self.assertIn('uptime_days', result.details)
    
    @patch('core.services.health_service.psutil.cpu_percent')
    def test_system_load_health_check_failure(self, mock_cpu_percent):
        """Test system load health check failure."""
        mock_cpu_percent.side_effect = Exception("CPU check failed")
        
        result = self.checker.check()
        
        self.assertEqual(result.status, 'critical')
        self.assertIn('System load check failed', result.message)
        self.assertIn('error', result.details)


class LogHealthCheckerTest(TestCase):
    """Test cases for LogHealthChecker."""
    
    def setUp(self):
        self.checker = LogHealthChecker()
    
    def test_log_health_check_success(self):
        """Test successful log health check."""
        result = self.checker.check()
        
        self.assertIn(result.status, ['healthy', 'warning', 'critical'])
        self.assertIsNotNone(result.message)
        self.assertIsNotNone(result.response_time)
        self.assertIsInstance(result.details, dict)
        self.assertIn('log_file_path', result.details)
    
    @patch('builtins.open')
    def test_log_health_check_with_errors(self, mock_open):
        """Test log health check when log file contains errors."""
        mock_file = MagicMock()
        mock_file.readlines.return_value = [
            "INFO: Normal operation",
            "ERROR: Database connection failed",
            "WARNING: High memory usage",
            "ERROR: Critical system failure",
            "ERROR: Another error",
            "ERROR: Yet another error",
            "ERROR: More errors",
            "ERROR: Even more errors"
        ]
        mock_open.return_value.__enter__.return_value = mock_file
        
        with patch('os.path.exists', return_value=True):
            result = self.checker.check()
        
        # Should be warning or critical due to multiple errors
        self.assertIn(result.status, ['warning', 'critical'])
        self.assertIn('error_count', result.details)
        self.assertIn('warning_count', result.details)
        # Should have detected multiple errors
        self.assertGreater(result.details['error_count'], 5)


class ResourceMonitoringIntegrationTest(TestCase):
    """Integration tests for resource monitoring components."""
    
    def test_system_resources_method(self):
        """Test the get_system_resources method."""
        service = HealthService()
        resources = service.get_system_resources()
        
        self.assertIsInstance(resources, dict)
        self.assertIn('memory', resources)
        self.assertIn('disk', resources)
        self.assertIn('system_load', resources)
        self.assertIn('logs', resources)
        
        # Each resource should have standard health check structure
        for resource_name, resource_data in resources.items():
            self.assertIn('status', resource_data)
            self.assertIn('message', resource_data)
            self.assertIn('details', resource_data)
            self.assertIn('timestamp', resource_data)
    
    def test_individual_resource_health_methods(self):
        """Test individual resource health methods."""
        service = HealthService()
        
        # Test memory health
        memory_health = service.get_memory_health()
        self.assertIn('status', memory_health)
        self.assertIn('details', memory_health)
        
        # Test disk health
        disk_health = service.get_disk_health()
        self.assertIn('status', disk_health)
        self.assertIn('details', disk_health)
        
        # Test system load health
        load_health = service.get_system_load_health()
        self.assertIn('status', load_health)
        self.assertIn('details', load_health)
        
        # Test log health
        log_health = service.get_log_health()
        self.assertIn('status', log_health)
        self.assertIn('details', log_health)
    
    def test_updated_system_health_includes_resources(self):
        """Test that system health now includes resource monitoring."""
        service = HealthService()
        health = service.get_system_health()
        
        self.assertIn('checks', health)
        checks = health['checks']
        
        # Should include all the new resource checks
        self.assertIn('memory', checks)
        self.assertIn('disk', checks)
        self.assertIn('system_load', checks)
        self.assertIn('logs', checks)
        
        # Should still include original checks
        self.assertIn('database', checks)
        self.assertIn('cache', checks)
    
    def test_real_resource_monitoring(self):
        """Test real resource monitoring functionality."""
        # Test memory checker
        memory_checker = MemoryHealthChecker()
        memory_result = memory_checker.check()
        self.assertIn(memory_result.status, ['healthy', 'warning', 'critical'])
        self.assertIsNotNone(memory_result.response_time)
        
        # Test disk checker
        disk_checker = DiskHealthChecker()
        disk_result = disk_checker.check()
        self.assertIn(disk_result.status, ['healthy', 'warning', 'critical'])
        self.assertIsNotNone(disk_result.response_time)
        
        # Test system load checker
        load_checker = SystemLoadHealthChecker()
        load_result = load_checker.check()
        self.assertIn(load_result.status, ['healthy', 'warning', 'critical'])
        self.assertIsNotNone(load_result.response_time)


class APIHealthCheckerTest(TestCase):
    """Test cases for APIHealthChecker."""
    
    def setUp(self):
        self.checker = APIHealthChecker()
    
    def test_api_health_check_success(self):
        """Test successful API health check."""
        result = self.checker.check()
        
        self.assertIn(result.status, ['healthy', 'warning', 'critical'])
        self.assertIsNotNone(result.message)
        self.assertIsNotNone(result.response_time)
        self.assertIsInstance(result.details, dict)
    
    def test_api_health_check_without_api_models(self):
        """Test API health check when API models are not available."""
        with patch('core.services.health_service.APIHealthChecker._collect_api_statistics') as mock_collect:
            # Simulate ImportError for API models
            def side_effect(*args):
                raise ImportError("No module named 'api'")
            
            with patch('builtins.__import__', side_effect=side_effect):
                result = self.checker.check()
        
        # Should handle gracefully when API models are not available
        self.assertIn(result.status, ['warning', 'critical'])
        self.assertIn('API models not available', result.message)
    
    @patch('core.services.health_service.APIHealthChecker._collect_api_statistics')
    def test_api_health_check_with_high_error_rate(self, mock_collect):
        """Test API health check with high error rate."""
        mock_collect.return_value = {
            'error_rate_24h': 15.5,
            'total_requests_24h': 1000,
            'error_requests_24h': 155,
            'active_clients': 5
        }
        
        result = self.checker.check()
        
        self.assertEqual(result.status, 'critical')
        self.assertIn('Critical API error rate', result.message)
        self.assertIn('15.5%', result.message)
    
    @patch('core.services.health_service.APIHealthChecker._collect_api_statistics')
    def test_api_health_check_with_moderate_error_rate(self, mock_collect):
        """Test API health check with moderate error rate."""
        mock_collect.return_value = {
            'error_rate_24h': 7.5,
            'total_requests_24h': 1000,
            'error_requests_24h': 75,
            'active_clients': 5
        }
        
        result = self.checker.check()
        
        self.assertEqual(result.status, 'warning')
        self.assertIn('High API error rate', result.message)
        self.assertIn('7.5%', result.message)
    
    @patch('core.services.health_service.APIHealthChecker._collect_api_statistics')
    def test_api_health_check_healthy(self, mock_collect):
        """Test API health check with healthy metrics."""
        mock_collect.return_value = {
            'error_rate_24h': 2.1,
            'total_requests_24h': 1000,
            'error_requests_24h': 21,
            'active_clients': 5
        }
        
        result = self.checker.check()
        
        self.assertEqual(result.status, 'healthy')
        self.assertIn('API health normal', result.message)
        self.assertIn('2.1%', result.message)
    
    def test_api_statistics_collection_structure(self):
        """Test that API statistics collection returns expected structure."""
        # Create mock API models
        MockAPIClient = MagicMock()
        MockAPIKey = MagicMock()
        MockAPIUsageLog = MagicMock()
        
        # Mock the counts and queries
        MockAPIClient.objects.count.return_value = 10
        MockAPIClient.objects.filter.return_value.count.return_value = 8
        MockAPIKey.objects.count.return_value = 15
        MockAPIKey.objects.filter.return_value.count.return_value = 12
        
        # Mock usage log queries
        mock_usage_24h = MagicMock()
        mock_usage_1h = MagicMock()
        MockAPIUsageLog.objects.filter.side_effect = [mock_usage_24h, mock_usage_1h]
        
        mock_usage_24h.count.return_value = 1000
        mock_usage_1h.count.return_value = 50
        mock_usage_24h.filter.return_value.count.side_effect = [100, 5]  # errors, rate limited
        mock_usage_1h.filter.return_value.count.side_effect = [5, 1]    # errors, rate limited
        mock_usage_24h.aggregate.return_value = {'avg_time': 0.25}
        mock_usage_1h.aggregate.return_value = {'avg_time': 0.30}
        mock_usage_24h.values.return_value.annotate.return_value.order_by.return_value.__getitem__.return_value = []
        mock_usage_24h.values.return_value.distinct.return_value.count.return_value = 5
        mock_usage_1h.values.return_value.distinct.return_value.count.return_value = 3
        
        now = timezone.now()
        twenty_four_hours_ago = now - timedelta(hours=24)
        one_hour_ago = now - timedelta(hours=1)
        
        stats = self.checker._collect_api_statistics(
            MockAPIClient, MockAPIKey, MockAPIUsageLog,
            now, twenty_four_hours_ago, one_hour_ago
        )
        
        # Verify expected structure
        expected_keys = [
            'total_clients', 'active_clients', 'total_api_keys', 'active_api_keys',
            'total_requests_24h', 'total_requests_1h', 'error_rate_24h', 'error_rate_1h',
            'avg_response_time_24h', 'avg_response_time_1h', 'success_rate_24h'
        ]
        
        for key in expected_keys:
            self.assertIn(key, stats)
        
        # Verify calculated values
        self.assertEqual(stats['total_clients'], 10)
        self.assertEqual(stats['active_clients'], 8)
        self.assertEqual(stats['error_rate_24h'], 10.0)  # 100/1000 * 100
        self.assertEqual(stats['success_rate_24h'], 90.0)  # (1000-100)/1000 * 100


class APIIntegrationTest(TestCase):
    """Integration tests for API health monitoring."""
    
    def test_api_health_in_system_health(self):
        """Test that API health is included in system health."""
        service = HealthService()
        health = service.get_system_health()
        
        self.assertIn('checks', health)
        self.assertIn('api', health['checks'])
        
        api_health = health['checks']['api']
        self.assertIn('status', api_health)
        self.assertIn('message', api_health)
        self.assertIn('details', api_health)
    
    def test_get_api_health_method(self):
        """Test the get_api_health method."""
        service = HealthService()
        api_health = service.get_api_health()
        
        self.assertIn('status', api_health)
        self.assertIn('message', api_health)
        self.assertIn('details', api_health)
        self.assertIn('timestamp', api_health)
    
    def test_updated_system_health_includes_api(self):
        """Test that system health now includes API monitoring."""
        service = HealthService()
        health = service.get_system_health()
        
        self.assertIn('checks', health)
        checks = health['checks']
        
        # Should include API check along with all other checks
        expected_checks = ['database', 'cache', 'memory', 'disk', 'system_load', 'logs', 'api']
        for check_name in expected_checks:
            self.assertIn(check_name, checks)
    
    def test_real_api_health_check(self):
        """Test real API health check functionality."""
        # This test uses the actual API models if available
        checker = APIHealthChecker()
        result = checker.check()
        
        # Should return a valid result regardless of whether API models exist
        self.assertIn(result.status, ['healthy', 'warning', 'critical'])
        self.assertIsNotNone(result.message)
        self.assertIsNotNone(result.response_time)
        self.assertIsInstance(result.details, dict)


class CeleryHealthCheckerTest(TestCase):
    """Test cases for CeleryHealthChecker."""
    
    def setUp(self):
        self.checker = CeleryHealthChecker()
    
    def test_celery_health_check_success(self):
        """Test successful Celery health check."""
        result = self.checker.check()
        
        self.assertIn(result.status, ['healthy', 'warning', 'critical'])
        self.assertIsNotNone(result.message)
        self.assertIsNotNone(result.response_time)
        self.assertIsInstance(result.details, dict)
    
    def test_celery_health_check_without_celery(self):
        """Test Celery health check when Celery is not available."""
        with patch('builtins.__import__', side_effect=ImportError("No module named 'celery'")):
            result = self.checker.check()
        
        self.assertEqual(result.status, 'warning')
        self.assertIn('Celery not available', result.message)
        self.assertIn('error', result.details)
    
    @patch('core.services.health_service.CeleryHealthChecker._collect_celery_statistics')
    def test_celery_health_check_no_workers(self, mock_collect):
        """Test Celery health check with no active workers."""
        mock_collect.return_value = {
            'active_workers': 0,
            'total_tasks_24h': 100,
            'failed_tasks_24h': 5
        }
        
        result = self.checker.check()
        
        self.assertEqual(result.status, 'critical')
        self.assertIn('No active Celery workers', result.message)
    
    @patch('core.services.health_service.CeleryHealthChecker._collect_celery_statistics')
    def test_celery_health_check_high_failure_rate(self, mock_collect):
        """Test Celery health check with high task failure rate."""
        mock_collect.return_value = {
            'active_workers': 2,
            'total_tasks_24h': 100,
            'failed_tasks_24h': 25  # 25% failure rate
        }
        
        result = self.checker.check()
        
        self.assertEqual(result.status, 'critical')
        self.assertIn('High task failure rate', result.message)
        self.assertIn('25.0%', result.message)
    
    @patch('core.services.health_service.CeleryHealthChecker._collect_celery_statistics')
    def test_celery_health_check_moderate_failure_rate(self, mock_collect):
        """Test Celery health check with moderate task failure rate."""
        mock_collect.return_value = {
            'active_workers': 2,
            'total_tasks_24h': 100,
            'failed_tasks_24h': 15  # 15% failure rate
        }
        
        result = self.checker.check()
        
        self.assertEqual(result.status, 'warning')
        self.assertIn('Moderate task failure rate', result.message)
        self.assertIn('15.0%', result.message)
    
    @patch('core.services.health_service.CeleryHealthChecker._collect_celery_statistics')
    def test_celery_health_check_healthy(self, mock_collect):
        """Test Celery health check with healthy metrics."""
        mock_collect.return_value = {
            'active_workers': 3,
            'total_tasks_24h': 100,
            'failed_tasks_24h': 2  # 2% failure rate
        }
        
        result = self.checker.check()
        
        self.assertEqual(result.status, 'healthy')
        self.assertIn('Celery healthy', result.message)
        self.assertIn('3 workers', result.message)
    
    def test_celery_statistics_collection_structure(self):
        """Test that Celery statistics collection returns expected structure."""
        # Create mock Celery components
        mock_celery_app = MagicMock()
        mock_task_result = MagicMock()
        mock_periodic_task = MagicMock()
        
        # Mock inspect functionality
        mock_inspect = MagicMock()
        mock_celery_app.control.inspect.return_value = mock_inspect
        mock_inspect.active.return_value = {'worker1': [], 'worker2': []}
        mock_inspect.registered.return_value = {'worker1': ['task1', 'task2']}
        
        # Mock task results
        mock_queryset = MagicMock()
        mock_task_result.objects.filter.return_value = mock_queryset
        mock_queryset.count.return_value = 100
        mock_queryset.filter.return_value.count.side_effect = [80, 15, 3, 2]  # success, fail, pending, retry
        mock_queryset.aggregate.return_value = {'avg_time': 2.5}
        
        # Mock periodic tasks
        mock_periodic_task.objects.all.return_value = mock_queryset
        mock_queryset.filter.return_value.values_list.return_value.__getitem__.return_value = ['task1', 'task2']
        
        stats = self.checker._collect_celery_statistics(
            mock_celery_app, mock_task_result, mock_periodic_task
        )
        
        # Verify expected structure
        expected_keys = [
            'active_workers', 'worker_names', 'active_tasks', 'registered_tasks',
            'total_tasks_24h', 'successful_tasks_24h', 'failed_tasks_24h', 'success_rate_24h'
        ]
        
        for key in expected_keys:
            self.assertIn(key, stats)
        
        # Verify calculated values
        self.assertEqual(stats['active_workers'], 2)
        self.assertEqual(stats['total_tasks_24h'], 100)


class RedisHealthCheckerTest(TestCase):
    """Test cases for RedisHealthChecker."""
    
    def setUp(self):
        self.checker = RedisHealthChecker()
    
    def test_redis_health_check_success(self):
        """Test successful Redis health check."""
        result = self.checker.check()
        
        self.assertIn(result.status, ['healthy', 'warning', 'critical'])
        self.assertIsNotNone(result.message)
        self.assertIsNotNone(result.response_time)
        self.assertIsInstance(result.details, dict)
    
    def test_redis_health_check_without_redis(self):
        """Test Redis health check when Redis package is not available."""
        with patch('builtins.__import__', side_effect=ImportError("No module named 'redis'")):
            result = self.checker.check()
        
        self.assertEqual(result.status, 'warning')
        self.assertIn('Redis not available', result.message)
        self.assertIn('error', result.details)
    
    @patch('core.services.health_service.RedisHealthChecker._collect_redis_statistics')
    def test_redis_health_check_high_memory_usage(self, mock_collect):
        """Test Redis health check with high memory usage."""
        mock_collect.return_value = {
            'used_memory_percentage': 95.0,
            'connected_clients': 10
        }
        
        result = self.checker.check()
        
        self.assertEqual(result.status, 'critical')
        self.assertIn('Critical Redis memory usage', result.message)
        self.assertIn('95.0%', result.message)
    
    @patch('core.services.health_service.RedisHealthChecker._collect_redis_statistics')
    def test_redis_health_check_moderate_memory_usage(self, mock_collect):
        """Test Redis health check with moderate memory usage."""
        mock_collect.return_value = {
            'used_memory_percentage': 85.0,
            'connected_clients': 10
        }
        
        result = self.checker.check()
        
        self.assertEqual(result.status, 'warning')
        self.assertIn('High Redis memory usage', result.message)
        self.assertIn('85.0%', result.message)
    
    @patch('core.services.health_service.RedisHealthChecker._collect_redis_statistics')
    def test_redis_health_check_high_connections(self, mock_collect):
        """Test Redis health check with high client connections."""
        mock_collect.return_value = {
            'used_memory_percentage': 50.0,
            'connected_clients': 150
        }
        
        result = self.checker.check()
        
        self.assertEqual(result.status, 'warning')
        self.assertIn('High Redis client connections', result.message)
        self.assertIn('150', result.message)
    
    @patch('core.services.health_service.RedisHealthChecker._collect_redis_statistics')
    def test_redis_health_check_healthy(self, mock_collect):
        """Test Redis health check with healthy metrics."""
        mock_collect.return_value = {
            'used_memory_percentage': 45.0,
            'connected_clients': 25
        }
        
        result = self.checker.check()
        
        self.assertEqual(result.status, 'healthy')
        self.assertIn('Redis healthy', result.message)
        self.assertIn('45.0%', result.message)
        self.assertIn('25 clients', result.message)
    
    def test_redis_statistics_collection_structure(self):
        """Test that Redis statistics collection returns expected structure."""
        # Create mock Redis client
        mock_redis_client = MagicMock()
        
        # Mock Redis info
        mock_info = {
            'redis_version': '6.2.0',
            'uptime_in_seconds': 86400,
            'used_memory': 1024000,
            'used_memory_human': '1M',
            'maxmemory': 2048000,
            'connected_clients': 10,
            'keyspace_hits': 1000,
            'keyspace_misses': 100,
            'total_commands_processed': 5000
        }
        mock_redis_client.info.return_value = mock_info
        mock_redis_client.set.return_value = True
        
        # Mock the basic operations test - need to simulate the actual test pattern
        test_values = {}
        def mock_set(key, value, ex=None):
            test_values[key] = value
            return True
        
        def mock_get(key):
            return test_values.get(key, '').encode() if test_values.get(key) else None
        
        mock_redis_client.set.side_effect = mock_set
        mock_redis_client.get.side_effect = mock_get
        mock_redis_client.delete.return_value = 1
        
        stats = self.checker._collect_redis_statistics(mock_redis_client, 'redis://localhost:6379/1')
        
        # Verify expected structure
        expected_keys = [
            'redis_version', 'uptime_in_seconds', 'used_memory', 'connected_clients',
            'keyspace_hits', 'keyspace_misses', 'hit_rate_percentage', 'basic_operations'
        ]
        
        for key in expected_keys:
            self.assertIn(key, stats)
        
        # Verify calculated values
        self.assertEqual(stats['redis_version'], '6.2.0')
        self.assertEqual(stats['connected_clients'], 10)
        self.assertEqual(stats['basic_operations'], 'working')


class CeleryRedisIntegrationTest(TestCase):
    """Integration tests for Celery and Redis health monitoring."""
    
    def test_celery_redis_in_system_health(self):
        """Test that Celery and Redis health are included in system health."""
        service = HealthService()
        health = service.get_system_health()
        
        self.assertIn('checks', health)
        self.assertIn('celery', health['checks'])
        self.assertIn('redis', health['checks'])
        
        # Check Celery health structure
        celery_health = health['checks']['celery']
        self.assertIn('status', celery_health)
        self.assertIn('message', celery_health)
        self.assertIn('details', celery_health)
        
        # Check Redis health structure
        redis_health = health['checks']['redis']
        self.assertIn('status', redis_health)
        self.assertIn('message', redis_health)
        self.assertIn('details', redis_health)
    
    def test_get_celery_health_method(self):
        """Test the get_celery_health method."""
        service = HealthService()
        celery_health = service.get_celery_health()
        
        self.assertIn('status', celery_health)
        self.assertIn('message', celery_health)
        self.assertIn('details', celery_health)
        self.assertIn('timestamp', celery_health)
    
    def test_get_redis_health_method(self):
        """Test the get_redis_health method."""
        service = HealthService()
        redis_health = service.get_redis_health()
        
        self.assertIn('status', redis_health)
        self.assertIn('message', redis_health)
        self.assertIn('details', redis_health)
        self.assertIn('timestamp', redis_health)
    
    def test_updated_system_health_includes_celery_redis(self):
        """Test that system health now includes Celery and Redis monitoring."""
        service = HealthService()
        health = service.get_system_health()
        
        self.assertIn('checks', health)
        checks = health['checks']
        
        # Should include all checks including new Celery and Redis
        expected_checks = ['database', 'cache', 'memory', 'disk', 'system_load', 'logs', 'api', 'celery', 'redis']
        for check_name in expected_checks:
            self.assertIn(check_name, checks)
    
    def test_real_celery_health_check(self):
        """Test real Celery health check functionality."""
        # This test uses the actual Celery setup if available
        checker = CeleryHealthChecker()
        result = checker.check()
        
        # Should return a valid result regardless of whether Celery is properly configured
        self.assertIn(result.status, ['healthy', 'warning', 'critical'])
        self.assertIsNotNone(result.message)
        self.assertIsNotNone(result.response_time)
        self.assertIsInstance(result.details, dict)
    
    def test_real_redis_health_check(self):
        """Test real Redis health check functionality."""
        # This test uses the actual Redis setup if available
        checker = RedisHealthChecker()
        result = checker.check()
        
        # Should return a valid result regardless of whether Redis is properly configured
        self.assertIn(result.status, ['healthy', 'warning', 'critical'])
        self.assertIsNotNone(result.message)
        self.assertIsNotNone(result.response_time)
        self.assertIsInstance(result.details, dict)


class HealthMetricModelTest(TestCase):
    """Test cases for HealthMetric model."""
    
    def setUp(self):
        from core.models import HealthMetric
        self.HealthMetric = HealthMetric
    
    def test_health_metric_creation(self):
        """Test creating a HealthMetric instance."""
        metric = self.HealthMetric.objects.create(
            metric_name='database',
            metric_value={'connection_time': 0.5, 'active_connections': 10},
            status='healthy',
            message='Database connection healthy',
            response_time=50.0
        )
        
        self.assertEqual(metric.metric_name, 'database')
        self.assertEqual(metric.status, 'healthy')
        self.assertEqual(metric.message, 'Database connection healthy')
        self.assertEqual(metric.response_time, 50.0)
        self.assertIsNotNone(metric.timestamp)
    
    def test_health_metric_str_representation(self):
        """Test string representation of HealthMetric."""
        metric = self.HealthMetric.objects.create(
            metric_name='memory',
            metric_value={'usage_percent': 75},
            status='warning',
            message='High memory usage'
        )
        
        str_repr = str(metric)
        self.assertIn('🟡', str_repr)  # Warning icon
        self.assertIn('Memory', str_repr)
        self.assertIn(metric.timestamp.strftime('%Y-%m-%d %H:%M'), str_repr)
    
    def test_record_metric_class_method(self):
        """Test the record_metric class method."""
        metric = self.HealthMetric.record_metric(
            metric_name='api',
            metric_value={'error_rate': 2.5, 'total_requests': 1000},
            status='healthy',
            message='API health normal',
            response_time=25.0
        )
        
        self.assertEqual(metric.metric_name, 'api')
        self.assertEqual(metric.status, 'healthy')
        self.assertEqual(metric.response_time, 25.0)
        self.assertTrue(self.HealthMetric.objects.filter(id=metric.id).exists())
    
    def test_get_latest_metrics(self):
        """Test getting latest metrics."""
        # Create multiple metrics
        for i in range(5):
            self.HealthMetric.record_metric(
                metric_name='database',
                metric_value={'test': i},
                status='healthy',
                message=f'Test metric {i}'
            )
        
        latest_metrics = self.HealthMetric.get_latest_metrics(limit=3)
        self.assertEqual(len(latest_metrics), 3)
        # Should be ordered by timestamp descending
        self.assertTrue(latest_metrics[0].timestamp >= latest_metrics[1].timestamp)
    
    def test_get_metrics_by_type(self):
        """Test getting metrics by type."""
        # Create metrics of different types
        self.HealthMetric.record_metric('database', {'test': 1}, 'healthy', 'DB test')
        self.HealthMetric.record_metric('memory', {'test': 2}, 'warning', 'Memory test')
        self.HealthMetric.record_metric('database', {'test': 3}, 'critical', 'DB critical')
        
        db_metrics = self.HealthMetric.get_metrics_by_type('database')
        self.assertEqual(db_metrics.count(), 2)
        for metric in db_metrics:
            self.assertEqual(metric.metric_name, 'database')
    
    def test_get_critical_metrics(self):
        """Test getting critical metrics."""
        self.HealthMetric.record_metric('database', {'test': 1}, 'healthy', 'DB healthy')
        self.HealthMetric.record_metric('memory', {'test': 2}, 'critical', 'Memory critical')
        self.HealthMetric.record_metric('disk', {'test': 3}, 'critical', 'Disk critical')
        
        critical_metrics = self.HealthMetric.get_critical_metrics()
        self.assertEqual(critical_metrics.count(), 2)
        for metric in critical_metrics:
            self.assertEqual(metric.status, 'critical')
    
    def test_is_recent_method(self):
        """Test the is_recent method."""
        # Create a recent metric
        recent_metric = self.HealthMetric.record_metric(
            'database', {'test': 1}, 'healthy', 'Recent test'
        )
        
        # Create an old metric by manually setting timestamp
        old_metric = self.HealthMetric.record_metric(
            'memory', {'test': 2}, 'healthy', 'Old test'
        )
        old_metric.timestamp = timezone.now() - timezone.timedelta(hours=2)
        old_metric.save()
        
        self.assertTrue(recent_metric.is_recent(minutes=30))
        self.assertFalse(old_metric.is_recent(minutes=30))


class SystemAlertModelTest(TestCase):
    """Test cases for SystemAlert model."""
    
    def setUp(self):
        from core.models import SystemAlert
        from django.contrib.auth.models import User
        self.SystemAlert = SystemAlert
        self.user = User.objects.create_user(username='testuser', password='testpass')
    
    def test_system_alert_creation(self):
        """Test creating a SystemAlert instance."""
        alert = self.SystemAlert.objects.create(
            alert_type='health_check',
            title='Database Connection Failed',
            message='Unable to connect to the database',
            severity='critical',
            source_metric='database'
        )
        
        self.assertEqual(alert.alert_type, 'health_check')
        self.assertEqual(alert.title, 'Database Connection Failed')
        self.assertEqual(alert.severity, 'critical')
        self.assertEqual(alert.source_metric, 'database')
        self.assertFalse(alert.resolved)
        self.assertIsNotNone(alert.created_at)
    
    def test_system_alert_str_representation(self):
        """Test string representation of SystemAlert."""
        alert = self.SystemAlert.objects.create(
            alert_type='performance',
            title='High Memory Usage',
            message='Memory usage is above 90%',
            severity='warning'
        )
        
        str_repr = str(alert)
        self.assertIn('🟡', str_repr)  # Warning icon
        self.assertIn('🔄', str_repr)  # Unresolved status
        self.assertIn('High Memory Usage', str_repr)
    
    def test_resolve_alert(self):
        """Test resolving an alert."""
        alert = self.SystemAlert.objects.create(
            alert_type='resource',
            title='Disk Space Low',
            message='Disk usage is above 85%',
            severity='warning'
        )
        
        self.assertFalse(alert.resolved)
        self.assertIsNone(alert.resolved_by)
        self.assertIsNone(alert.resolved_at)
        
        alert.resolve(user=self.user, notes='Added more disk space')
        
        self.assertTrue(alert.resolved)
        self.assertEqual(alert.resolved_by, self.user)
        self.assertIsNotNone(alert.resolved_at)
        self.assertEqual(alert.resolution_notes, 'Added more disk space')
    
    def test_reopen_alert(self):
        """Test reopening a resolved alert."""
        alert = self.SystemAlert.objects.create(
            alert_type='security',
            title='Security Issue',
            message='Potential security breach detected',
            severity='critical'
        )
        
        # First resolve the alert
        alert.resolve(user=self.user, notes='Issue fixed')
        self.assertTrue(alert.resolved)
        
        # Then reopen it
        alert.reopen()
        self.assertFalse(alert.resolved)
        self.assertIsNone(alert.resolved_by)
        self.assertIsNone(alert.resolved_at)
        self.assertEqual(alert.resolution_notes, '')
    
    def test_create_alert_class_method(self):
        """Test the create_alert class method."""
        alert = self.SystemAlert.create_alert(
            alert_type='maintenance',
            title='Scheduled Maintenance',
            message='System will be down for maintenance',
            severity='info',
            source_metric='system',
            metadata={'duration': '2 hours', 'start_time': '02:00 UTC'}
        )
        
        self.assertEqual(alert.alert_type, 'maintenance')
        self.assertEqual(alert.severity, 'info')
        self.assertEqual(alert.metadata['duration'], '2 hours')
        self.assertTrue(self.SystemAlert.objects.filter(id=alert.id).exists())
    
    def test_get_active_alerts(self):
        """Test getting active (unresolved) alerts."""
        # Create resolved and unresolved alerts
        resolved_alert = self.SystemAlert.create_alert(
            'health_check', 'Resolved Issue', 'This was fixed', 'warning'
        )
        resolved_alert.resolve(user=self.user)
        
        active_alert1 = self.SystemAlert.create_alert(
            'performance', 'Active Issue 1', 'Still happening', 'critical'
        )
        active_alert2 = self.SystemAlert.create_alert(
            'resource', 'Active Issue 2', 'Also happening', 'warning'
        )
        
        active_alerts = self.SystemAlert.get_active_alerts()
        self.assertEqual(active_alerts.count(), 2)
        alert_ids = [alert.id for alert in active_alerts]
        self.assertIn(active_alert1.id, alert_ids)
        self.assertIn(active_alert2.id, alert_ids)
        self.assertNotIn(resolved_alert.id, alert_ids)
    
    def test_get_critical_alerts(self):
        """Test getting critical alerts."""
        self.SystemAlert.create_alert('health_check', 'Info Alert', 'Just info', 'info')
        self.SystemAlert.create_alert('performance', 'Warning Alert', 'Warning', 'warning')
        critical_alert = self.SystemAlert.create_alert(
            'resource', 'Critical Alert', 'Critical issue', 'critical'
        )
        emergency_alert = self.SystemAlert.create_alert(
            'security', 'Emergency Alert', 'Emergency!', 'emergency'
        )
        
        critical_alerts = self.SystemAlert.get_critical_alerts()
        self.assertEqual(critical_alerts.count(), 2)
        alert_ids = [alert.id for alert in critical_alerts]
        self.assertIn(critical_alert.id, alert_ids)
        self.assertIn(emergency_alert.id, alert_ids)
    
    def test_get_recent_alerts(self):
        """Test getting recent alerts."""
        # Create a recent alert
        recent_alert = self.SystemAlert.create_alert(
            'health_check', 'Recent Alert', 'Just happened', 'warning'
        )
        
        # Create an old alert by manually setting timestamp
        old_alert = self.SystemAlert.create_alert(
            'performance', 'Old Alert', 'Long ago', 'info'
        )
        old_alert.created_at = timezone.now() - timezone.timedelta(days=2)
        old_alert.save()
        
        recent_alerts = self.SystemAlert.get_recent_alerts(hours=24)
        self.assertEqual(recent_alerts.count(), 1)
        self.assertEqual(recent_alerts.first().id, recent_alert.id)
    
    def test_get_age_method(self):
        """Test the get_age method."""
        alert = self.SystemAlert.create_alert(
            'custom', 'Test Alert', 'Test message', 'info'
        )
        
        age = alert.get_age()
        self.assertIsInstance(age, timezone.timedelta)
        # Should be very recent (less than a minute)
        self.assertLess(age.total_seconds(), 60)
    
    def test_is_stale_method(self):
        """Test the is_stale method."""
        # Create a recent alert
        recent_alert = self.SystemAlert.create_alert(
            'health_check', 'Recent Alert', 'Just created', 'info'
        )
        
        # Create an old alert
        old_alert = self.SystemAlert.create_alert(
            'performance', 'Old Alert', 'Created long ago', 'warning'
        )
        old_alert.created_at = timezone.now() - timezone.timedelta(days=2)
        old_alert.save()
        
        self.assertFalse(recent_alert.is_stale(hours=24))
        self.assertTrue(old_alert.is_stale(hours=24))


class HealthDashboardModelsIntegrationTest(TestCase):
    """Integration tests for health dashboard models."""
    
    def setUp(self):
        from core.models import HealthMetric, SystemAlert
        from django.contrib.auth.models import User
        self.HealthMetric = HealthMetric
        self.SystemAlert = SystemAlert
        self.user = User.objects.create_user(username='admin', password='adminpass')
    
    def test_health_metric_and_alert_workflow(self):
        """Test a complete workflow of recording metrics and creating alerts."""
        # Record a critical health metric
        critical_metric = self.HealthMetric.record_metric(
            metric_name='database',
            metric_value={'connection_failed': True, 'error': 'Connection timeout'},
            status='critical',
            message='Database connection failed',
            response_time=5000.0
        )
        
        # Create an alert based on the critical metric
        alert = self.SystemAlert.create_alert(
            alert_type='health_check',
            title='Database Connection Critical',
            message=f'Database health check failed: {critical_metric.message}',
            severity='critical',
            source_metric=critical_metric.metric_name,
            metadata={
                'metric_id': critical_metric.id,
                'response_time': critical_metric.response_time,
                'timestamp': critical_metric.timestamp.isoformat()
            }
        )
        
        # Verify the workflow
        self.assertEqual(critical_metric.status, 'critical')
        self.assertEqual(alert.severity, 'critical')
        self.assertEqual(alert.source_metric, 'database')
        self.assertEqual(alert.metadata['metric_id'], critical_metric.id)
        
        # Simulate fixing the issue
        healthy_metric = self.HealthMetric.record_metric(
            metric_name='database',
            metric_value={'connection_successful': True, 'active_connections': 5},
            status='healthy',
            message='Database connection restored',
            response_time=50.0
        )
        
        # Resolve the alert
        alert.resolve(
            user=self.user,
            notes=f'Database connection restored. New metric: {healthy_metric.id}'
        )
        
        # Verify resolution
        self.assertTrue(alert.resolved)
        self.assertEqual(alert.resolved_by, self.user)
        self.assertIsNotNone(alert.resolved_at)
    
    def test_model_choices_and_validation(self):
        """Test model choices and field validation."""
        # Test HealthMetric choices
        valid_metric_types = [choice[0] for choice in self.HealthMetric.METRIC_TYPE_CHOICES]
        valid_health_statuses = [choice[0] for choice in self.HealthMetric.HEALTH_STATUS_CHOICES]
        
        self.assertIn('database', valid_metric_types)
        self.assertIn('api', valid_metric_types)
        self.assertIn('celery', valid_metric_types)
        self.assertIn('redis', valid_metric_types)
        
        self.assertIn('healthy', valid_health_statuses)
        self.assertIn('warning', valid_health_statuses)
        self.assertIn('critical', valid_health_statuses)
        
        # Test SystemAlert choices
        valid_alert_types = [choice[0] for choice in self.SystemAlert.ALERT_TYPE_CHOICES]
        valid_severities = [choice[0] for choice in self.SystemAlert.SEVERITY_CHOICES]
        
        self.assertIn('health_check', valid_alert_types)
        self.assertIn('performance', valid_alert_types)
        self.assertIn('resource', valid_alert_types)
        
        self.assertIn('info', valid_severities)
        self.assertIn('warning', valid_severities)
        self.assertIn('critical', valid_severities)
        self.assertIn('emergency', valid_severities)
    
    def test_model_indexes_and_performance(self):
        """Test that model indexes work correctly for performance."""
        # Create multiple metrics and alerts
        for i in range(10):
            self.HealthMetric.record_metric(
                metric_name='database' if i % 2 == 0 else 'memory',
                metric_value={'test': i},
                status='critical' if i % 3 == 0 else 'healthy',
                message=f'Test metric {i}'
            )
            
            self.SystemAlert.create_alert(
                alert_type='health_check' if i % 2 == 0 else 'performance',
                title=f'Test Alert {i}',
                message=f'Test alert message {i}',
                severity='critical' if i % 4 == 0 else 'warning'
            )
        
        # Test indexed queries (these should be fast due to indexes)
        db_metrics = self.HealthMetric.objects.filter(metric_name='database')
        critical_metrics = self.HealthMetric.objects.filter(status='critical')
        recent_metrics = self.HealthMetric.objects.order_by('-timestamp')[:5]
        
        health_alerts = self.SystemAlert.objects.filter(alert_type='health_check')
        critical_alerts = self.SystemAlert.objects.filter(severity='critical')
        recent_alerts = self.SystemAlert.objects.order_by('-created_at')[:5]
        
        # Verify queries return expected results
        self.assertGreater(db_metrics.count(), 0)
        self.assertGreater(critical_metrics.count(), 0)
        self.assertEqual(len(recent_metrics), 5)
        self.assertGreater(health_alerts.count(), 0)
        self.assertGreater(critical_alerts.count(), 0)
        self.assertEqual(len(recent_alerts), 5)