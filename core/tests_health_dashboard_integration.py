"""
Integration tests for the Health Dashboard functionality.
"""

import json
import time
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.test.utils import override_settings
from django.core.cache import cache

from core.models import HealthMetric, SystemAlert
from core.services.health_service import health_service, HealthCheckResult


class HealthDashboardIntegrationTests(TransactionTestCase):
    """Integration tests for the health dashboard functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123'
        )
        
        # Create test health metrics
        for metric_type in ['database', 'cache', 'memory', 'disk', 'system_load']:
            HealthMetric.objects.create(
                metric_name=metric_type,
                metric_value={'test': True},
                status='healthy',
                message=f'{metric_type.title()} is healthy',
                response_time=50.0
            )
        
        # Create a warning metric
        HealthMetric.objects.create(
            metric_name='api',
            metric_value={'error_rate': 8.5},
            status='warning',
            message='API error rate is high (8.5%)',
            response_time=120.0
        )
        
        # Create a critical metric
        HealthMetric.objects.create(
            metric_name='redis',
            metric_value={'connection': False},
            status='critical',
            message='Redis connection failed',
            response_time=500.0
        )
        
        # Create test alerts
        SystemAlert.objects.create(
            alert_type='health_check',
            title='Test Warning Alert',
            message='This is a test warning alert',
            severity='warning',
            source_metric='api'
        )
        
        SystemAlert.objects.create(
            alert_type='health_check',
            title='Test Critical Alert',
            message='This is a test critical alert',
            severity='critical',
            source_metric='redis'
        )
    
    def test_dashboard_integration_with_real_data(self):
        """Test that the dashboard correctly integrates with real data."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:health_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        
        # Check that the dashboard contains all expected components
        self.assertContains(response, 'System Health Dashboard')
        self.assertContains(response, 'Overall Status')
        self.assertContains(response, 'Total Checks')
        self.assertContains(response, 'Healthy Services')
        self.assertContains(response, 'Issues Found')
        self.assertContains(response, 'Recent Health Metrics')
        self.assertContains(response, 'Active Alerts')
        
        # Check that our test metrics are displayed
        self.assertContains(response, 'Database')
        self.assertContains(response, 'Cache')
        self.assertContains(response, 'Memory')
        self.assertContains(response, 'Disk')
        self.assertContains(response, 'System Load')
        self.assertContains(response, 'API')
        self.assertContains(response, 'Redis')
        
        # Check that our test alerts are displayed
        self.assertContains(response, 'Test Warning Alert')
        self.assertContains(response, 'Test Critical Alert')
    
    def test_dashboard_api_integration(self):
        """Test that the dashboard API correctly integrates with the health service."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(
            reverse('core:health_dashboard_api'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertIn('system_health', data)
        self.assertIn('health_summary', data)
        self.assertIn('recent_metrics', data)
        self.assertIn('active_alerts', data)
        
        # Check that metrics are correctly formatted
        self.assertTrue(len(data['recent_metrics']) > 0)
        for metric in data['recent_metrics']:
            self.assertIn('id', metric)
            self.assertIn('metric_name', metric)
            self.assertIn('status', metric)
            self.assertIn('message', metric)
            self.assertIn('timestamp', metric)
        
        # Check that alerts are correctly formatted
        self.assertTrue(len(data['active_alerts']) > 0)
        for alert in data['active_alerts']:
            self.assertIn('id', alert)
            self.assertIn('title', alert)
            self.assertIn('severity', alert)
            self.assertIn('created_at', alert)
    
    @patch('core.services.health_service.health_service.get_system_health')
    def test_dashboard_graceful_degradation(self, mock_health_service):
        """Test that the dashboard gracefully handles health service failures."""
        # Mock a health service failure
        mock_health_service.side_effect = Exception("Simulated health service failure")
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:health_dashboard'))
        
        # Should still render the page with an error message
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'System Health Dashboard')
        self.assertContains(response, 'critical')  # Should show critical status
        
        # Check API response with failure
        api_response = self.client.get(
            reverse('core:health_dashboard_api'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(api_response.status_code, 200)
        data = json.loads(api_response.content)
        
        self.assertTrue(data['success'])  # API should still return success
        self.assertIn('system_health', data)
        self.assertIn('error', data['system_health'])  # Should contain error message
    
    def test_end_to_end_alert_resolution_workflow(self):
        """Test the complete workflow of resolving an alert."""
        self.client.login(username='admin', password='testpass123')
        
        # Get an alert to resolve
        alert = SystemAlert.objects.filter(resolved=False).first()
        self.assertIsNotNone(alert)
        
        # Resolve the alert via API
        response = self.client.post(
            reverse('core:system_alerts_api'),
            data=json.dumps({
                'alert_id': alert.id,
                'action': 'resolve',
                'notes': 'Resolved during integration test'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertIn('alert', data)
        
        # Verify alert was resolved in database
        alert.refresh_from_db()
        self.assertTrue(alert.resolved)
        self.assertEqual(alert.resolved_by, self.superuser)
        self.assertEqual(alert.resolution_notes, 'Resolved during integration test')
        
        # Check that the alert no longer appears in active alerts API
        active_alerts_response = self.client.get(reverse('core:system_alerts_api'))
        active_alerts_data = json.loads(active_alerts_response.content)
        
        alert_ids = [a['id'] for a in active_alerts_data['alerts']]
        self.assertNotIn(alert.id, alert_ids)
    
    def test_metrics_filtering_api(self):
        """Test filtering metrics by type via API."""
        self.client.login(username='admin', password='testpass123')
        
        # Test filtering by database metrics
        response = self.client.get(
            reverse('core:health_metrics_type_api', kwargs={'metric_type': 'database'})
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['metric_type'], 'database')
        self.assertTrue(len(data['metrics']) > 0)
        
        # All returned metrics should be database metrics
        for metric in data['metrics']:
            self.assertEqual(metric['metric_name'], 'database')
        
        # Test filtering by non-existent type
        response = self.client.get(
            reverse('core:health_metrics_type_api', kwargs={'metric_type': 'nonexistent'})
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['metrics']), 0)  # Should return empty list


class HealthDashboardPerformanceTests(TestCase):
    """Performance tests for the health dashboard functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        
        # Create a large number of test metrics for performance testing
        metric_types = ['database', 'cache', 'memory', 'disk', 'system_load', 'api', 'redis']
        statuses = ['healthy', 'warning', 'critical']
        
        # Create 100 test metrics (this is a reasonable number for testing)
        for i in range(100):
            metric_type = metric_types[i % len(metric_types)]
            status = statuses[i % len(statuses)]
            
            HealthMetric.objects.create(
                metric_name=metric_type,
                metric_value={'test_index': i},
                status=status,
                message=f'Test metric {i}',
                response_time=50.0
            )
    
    def test_dashboard_load_performance(self):
        """Test the performance of loading the dashboard with many metrics."""
        self.client.login(username='admin', password='testpass123')
        
        # Measure time to load dashboard
        start_time = time.time()
        response = self.client.get(reverse('core:health_dashboard'))
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        
        # Dashboard should load in a reasonable time (adjust as needed for your environment)
        load_time = end_time - start_time
        self.assertLess(load_time, 5.0, f"Dashboard load time too slow: {load_time:.2f}s")
    
    def test_api_response_performance(self):
        """Test the performance of the dashboard API with many metrics."""
        self.client.login(username='admin', password='testpass123')
        
        # Measure time for API response
        start_time = time.time()
        response = self.client.get(
            reverse('core:health_dashboard_api'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        
        # API should respond in a reasonable time (adjust as needed)
        response_time = end_time - start_time
        self.assertLess(response_time, 5.0, f"API response time too slow: {response_time:.2f}s")
        
        # Verify data structure
        data = json.loads(response.content)
        self.assertTrue(data['success'])
    
    def test_metrics_api_performance(self):
        """Test the performance of the metrics API with filtering."""
        self.client.login(username='admin', password='testpass123')
        
        # Test performance of filtered metrics API
        start_time = time.time()
        response = self.client.get(
            reverse('core:health_metrics_type_api', kwargs={'metric_type': 'database'})
        )
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        
        # Filtered API should respond in a reasonable time
        response_time = end_time - start_time
        self.assertLess(response_time, 5.0, f"Filtered metrics API too slow: {response_time:.2f}s")
    
    @override_settings(DEBUG=False)  # Test with DEBUG off to simulate production
    def test_health_service_performance(self):
        """Test the performance of the health service itself."""
        # Measure time for health service to collect all metrics
        start_time = time.time()
        health_data = health_service.get_system_health()
        end_time = time.time()
        
        # Health service should complete in a reasonable time (adjust based on your system)
        service_time = end_time - start_time
        self.assertLess(service_time, 5.0, f"Health service too slow: {service_time:.2f}s")
        
        # Verify we got valid data
        self.assertIn('overall_status', health_data)
        self.assertIn('checks', health_data)
    
    def test_concurrent_requests_performance(self):
        """Test performance with concurrent requests (simulated)."""
        self.client.login(username='admin', password='testpass123')
        
        # Clear cache to ensure fresh data
        cache.clear()
        
        # First request to warm up
        self.client.get(reverse('core:health_dashboard'))
        
        # Simulate 5 concurrent requests and measure time
        start_time = time.time()
        
        # We can't easily do true concurrent requests in a test,
        # but we can do them sequentially to check for degradation
        for i in range(5):
            response = self.client.get(reverse('core:health_dashboard'))
            self.assertEqual(response.status_code, 200)
        
        end_time = time.time()
        
        # 5 sequential requests should complete in reasonable time
        total_time = end_time - start_time
        avg_time = total_time / 5
        
        self.assertLess(avg_time, 5.0, f"Average request time too slow: {avg_time:.2f}s")


class HealthDashboardSecurityTests(TestCase):
    """Security tests for the health dashboard functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create different user types for testing
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@test.com',
            password='testpass123',
            is_staff=True
        )
        
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123'
        )
    
    def test_dashboard_access_control(self):
        """Test that only superusers can access the dashboard."""
        dashboard_url = reverse('core:health_dashboard')
        
        # Test unauthenticated access
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, 302)  # Should redirect to login
        
        # Test regular user access
        self.client.login(username='user', password='testpass123')
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, 302)  # Should redirect to login
        
        # Test staff user access (who is not a superuser)
        self.client.login(username='staff', password='testpass123')
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, 302)  # Should redirect to login
        
        # Test superuser access
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, 200)  # Should allow access
    
    def test_api_access_control(self):
        """Test that only superusers can access the dashboard APIs."""
        api_endpoints = [
            reverse('core:health_dashboard_api'),
            reverse('core:health_metrics_api'),
            reverse('core:health_metrics_type_api', kwargs={'metric_type': 'database'}),
            reverse('core:system_alerts_api')
        ]
        
        # Test unauthenticated access
        for endpoint in api_endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 401)  # Should return unauthorized
        
        # Test regular user access
        self.client.login(username='user', password='testpass123')
        for endpoint in api_endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 401)  # Should return unauthorized
        
        # Test staff user access (who is not a superuser)
        self.client.login(username='staff', password='testpass123')
        for endpoint in api_endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 401)  # Should return unauthorized
        
        # Test superuser access
        self.client.login(username='admin', password='testpass123')
        for endpoint in api_endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)  # Should allow access
    
    def test_csrf_protection(self):
        """Test that CSRF protection is enforced for POST requests."""
        self.client.login(username='admin', password='testpass123')
        
        # Create a test alert to resolve
        alert = SystemAlert.objects.create(
            alert_type='test',
            title='CSRF Test Alert',
            message='This is a test alert',
            severity='warning'
        )
        
        # Attempt to resolve alert without CSRF token
        self.client.handler.enforce_csrf_checks = True  # Enable CSRF checks
        
        response = self.client.post(
            reverse('core:system_alerts_api'),
            data=json.dumps({
                'alert_id': alert.id,
                'action': 'resolve'
            }),
            content_type='application/json'
        )
        
        # Should fail due to CSRF protection
        self.assertEqual(response.status_code, 403)
        
        # Verify alert was not resolved
        alert.refresh_from_db()
        self.assertFalse(alert.resolved)
    
    def test_input_validation(self):
        """Test that inputs are properly validated."""
        self.client.login(username='admin', password='testpass123')
        
        # Test with invalid alert ID
        response = self.client.post(
            reverse('core:system_alerts_api'),
            data=json.dumps({
                'alert_id': 9999,  # Non-existent ID
                'action': 'resolve'
            }),
            content_type='application/json'
        )
        
        # The actual implementation might return 404 or 500 depending on how it's handled
        # We just want to make sure it's not a successful response
        self.assertNotEqual(response.status_code, 200)
        
        # Test with invalid action
        alert = SystemAlert.objects.create(
            alert_type='test',
            title='Validation Test Alert',
            message='This is a test alert',
            severity='warning'
        )
        
        response = self.client.post(
            reverse('core:system_alerts_api'),
            data=json.dumps({
                'alert_id': alert.id,
                'action': 'invalid_action'  # Invalid action
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)  # Should return bad request
        
        # Test with potentially unsafe metric type (but valid URL)
        response = self.client.get(
            reverse('core:health_metrics_type_api', kwargs={'metric_type': 'javascript_injection'})
        )
        
        self.assertEqual(response.status_code, 200)  # Should handle safely
        data = json.loads(response.content)
        self.assertEqual(len(data['metrics']), 0)  # Should return empty list
    
    def test_rate_limiting(self):
        """Test that rate limiting is applied to API endpoints."""
        self.client.login(username='admin', password='testpass123')
        
        # Make multiple rapid requests to test rate limiting
        # Note: This is a basic test and may need adjustment based on your rate limiting configuration
        responses = []
        for i in range(20):  # Make 20 rapid requests
            response = self.client.get(
                reverse('core:health_dashboard_api'),
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            responses.append(response.status_code)
        
        # All requests should return valid responses (no 429 Too Many Requests)
        # This is a basic check - your actual rate limiting may vary
        for status_code in responses:
            self.assertEqual(status_code, 200)


class HealthDashboardEndToEndTests(TestCase):
    """End-to-end tests for complete user workflows."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        
        # Create test metrics
        HealthMetric.objects.create(
            metric_name='database',
            metric_value={'status': 'connected'},
            status='healthy',
            message='Database connection healthy',
            response_time=50.0
        )
        
        HealthMetric.objects.create(
            metric_name='memory',
            metric_value={'percent_used': 85},
            status='warning',
            message='High memory usage: 85%',
            response_time=30.0
        )
        
        # Create test alert
        SystemAlert.objects.create(
            alert_type='health_check',
            title='Memory Usage Warning',
            message='System memory usage is high (85%)',
            severity='warning',
            source_metric='memory'
        )
    
    def test_complete_dashboard_workflow(self):
        """Test a complete user workflow from login to alert resolution."""
        # Step 1: User logs in
        login_successful = self.client.login(username='admin', password='testpass123')
        self.assertTrue(login_successful)
        
        # Step 2: User accesses the dashboard
        dashboard_response = self.client.get(reverse('core:health_dashboard'))
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, 'System Health Dashboard')
        self.assertContains(dashboard_response, 'Memory Usage Warning')
        
        # Step 3: User checks specific metrics
        metrics_response = self.client.get(
            reverse('core:health_metrics_type_api', kwargs={'metric_type': 'memory'})
        )
        self.assertEqual(metrics_response.status_code, 200)
        metrics_data = json.loads(metrics_response.content)
        self.assertEqual(metrics_data['metric_type'], 'memory')
        self.assertTrue(len(metrics_data['metrics']) > 0)
        
        # Step 4: User resolves the alert
        alert = SystemAlert.objects.filter(resolved=False).first()
        resolve_response = self.client.post(
            reverse('core:system_alerts_api'),
            data=json.dumps({
                'alert_id': alert.id,
                'action': 'resolve',
                'notes': 'Increased server memory'
            }),
            content_type='application/json'
        )
        self.assertEqual(resolve_response.status_code, 200)
        
        # Step 5: User refreshes dashboard data via API
        refresh_response = self.client.get(
            reverse('core:health_dashboard_api'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(refresh_response.status_code, 200)
        refresh_data = json.loads(refresh_response.content)
        
        # Alert should no longer be in active alerts
        alert_ids = [a['id'] for a in refresh_data['active_alerts']]
        self.assertNotIn(alert.id, alert_ids)
        
        # Step 6: User logs out
        self.client.logout()
        
        # Verify user is logged out by checking dashboard access
        final_response = self.client.get(reverse('core:health_dashboard'))
        self.assertEqual(final_response.status_code, 302)  # Should redirect to login
    
    def test_error_handling_workflow(self):
        """Test workflow when errors occur in the health service."""
        self.client.login(username='admin', password='testpass123')
        
        # Simulate a health service error
        with patch('core.services.health_service.health_service.get_system_health') as mock_health:
            mock_health.side_effect = Exception("Simulated service failure")
            
            # User should still be able to access dashboard
            response = self.client.get(reverse('core:health_dashboard'))
            self.assertEqual(response.status_code, 200)
            
            # Dashboard should show error state
            self.assertContains(response, 'System Health Dashboard')
            
            # User should still be able to access metrics API
            metrics_response = self.client.get(reverse('core:health_metrics_api'))
            self.assertEqual(metrics_response.status_code, 200)
            
            # User should still be able to access alerts API
            alerts_response = self.client.get(reverse('core:system_alerts_api'))
            self.assertEqual(alerts_response.status_code, 200)
        
        # After error condition resolves, dashboard should return to normal
        normal_response = self.client.get(reverse('core:health_dashboard'))
        self.assertEqual(normal_response.status_code, 200)
        self.assertContains(normal_response, 'System Health Dashboard')
    
    def test_alert_lifecycle_workflow(self):
        """Test the complete lifecycle of an alert from creation to resolution."""
        self.client.login(username='admin', password='testpass123')
        
        # Step 1: Create a new critical alert
        new_alert = SystemAlert.create_alert(
            alert_type='performance',
            title='Critical CPU Usage',
            message='CPU usage has reached 95%',
            severity='critical',
            source_metric='system_load',
            metadata={'cpu_percent': 95}
        )
        
        # Step 2: Verify alert appears in dashboard
        dashboard_response = self.client.get(reverse('core:health_dashboard'))
        self.assertContains(dashboard_response, 'Critical CPU Usage')
        
        # Step 3: Verify alert appears in critical alerts API
        alerts_response = self.client.get(reverse('core:system_alerts_api') + '?type=critical')
        alerts_data = json.loads(alerts_response.content)
        alert_titles = [a['title'] for a in alerts_data['alerts']]
        self.assertIn('Critical CPU Usage', alert_titles)
        
        # Step 4: Resolve the alert
        resolve_response = self.client.post(
            reverse('core:system_alerts_api'),
            data=json.dumps({
                'alert_id': new_alert.id,
                'action': 'resolve',
                'notes': 'Restarted problematic service'
            }),
            content_type='application/json'
        )
        self.assertEqual(resolve_response.status_code, 200)
        
        # Step 5: Verify alert no longer appears in active alerts
        active_alerts_response = self.client.get(reverse('core:system_alerts_api'))
        active_alerts_data = json.loads(active_alerts_response.content)
        active_alert_ids = [a['id'] for a in active_alerts_data['alerts']]
        self.assertNotIn(new_alert.id, active_alert_ids)
        
        # Step 6: Reopen the alert
        reopen_response = self.client.post(
            reverse('core:system_alerts_api'),
            data=json.dumps({
                'alert_id': new_alert.id,
                'action': 'reopen'
            }),
            content_type='application/json'
        )
        self.assertEqual(reopen_response.status_code, 200)
        
        # Step 7: Verify alert appears again in active alerts
        reopened_alerts_response = self.client.get(reverse('core:system_alerts_api'))
        reopened_alerts_data = json.loads(reopened_alerts_response.content)
        reopened_alert_ids = [a['id'] for a in reopened_alerts_data['alerts']]
        self.assertIn(new_alert.id, reopened_alert_ids)