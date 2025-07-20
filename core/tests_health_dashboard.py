"""
Tests for the Health Dashboard functionality.
"""

import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch, MagicMock
from core.models import HealthMetric, SystemAlert
from core.services.health_service import health_service


class HealthDashboardViewTests(TestCase):
    """Test cases for the health dashboard views."""
    
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
        
        # Create some test health metrics
        HealthMetric.objects.create(
            metric_name='database',
            metric_value={'status': 'healthy'},
            status='healthy',
            message='Database connection healthy',
            response_time=50.0
        )
        
        # Create a test alert
        SystemAlert.objects.create(
            alert_type='health_check',
            title='Test Alert',
            message='This is a test alert',
            severity='warning',
            source_metric='database'
        )
    
    def test_health_dashboard_requires_superuser(self):
        """Test that health dashboard requires superuser access."""
        # Test unauthenticated access
        response = self.client.get(reverse('core:health_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test regular user access
        self.client.login(username='user', password='testpass123')
        response = self.client.get(reverse('core:health_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login page
        self.assertIn('/login/', response.url)  # Check that it redirects to login
        
        # Test superuser access
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:health_dashboard'))
        self.assertEqual(response.status_code, 200)  # Success
        
    def test_admin_navigation_integration(self):
        """Test that health dashboard is properly integrated with admin navigation."""
        # Login as superuser
        self.client.login(username='admin', password='testpass123')
        
        # Get the admin index page
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        
        # Check that the response contains the health dashboard link
        self.assertContains(response, reverse('core:health_dashboard'))
        self.assertContains(response, 'System Health')
        
        # Follow the link to the health dashboard
        response = self.client.get(reverse('core:health_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/health_dashboard.html')
    
    def test_health_dashboard_context(self):
        """Test that health dashboard provides correct context."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:health_dashboard'))
        
        self.assertIn('system_health', response.context)
        self.assertIn('health_summary', response.context)
        self.assertIn('recent_metrics', response.context)
        self.assertIn('active_alerts', response.context)
        
        # Check that we have the test data
        self.assertTrue(len(response.context['recent_metrics']) > 0)
        self.assertTrue(len(response.context['active_alerts']) > 0)
    
    @patch('core.services.health_service.health_service.get_system_health')
    def test_health_dashboard_api_endpoint(self, mock_health_service):
        """Test the health dashboard API endpoint."""
        # Mock the health service response
        mock_health_service.return_value = {
            'overall_status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'checks': {
                'database': {
                    'status': 'healthy',
                    'message': 'Database connection healthy',
                    'response_time': 50.0
                }
            }
        }
        
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
    
    def test_health_dashboard_api_requires_superuser(self):
        """Test that health dashboard API requires superuser access."""
        # Test unauthenticated access
        response = self.client.get(reverse('core:health_dashboard_api'))
        self.assertEqual(response.status_code, 401)
        
        # Test regular user access
        self.client.login(username='user', password='testpass123')
        response = self.client.get(reverse('core:health_dashboard_api'))
        self.assertEqual(response.status_code, 401)
        
        # Test superuser access
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:health_dashboard_api'))
        self.assertEqual(response.status_code, 200)
    
    def test_health_metrics_api_endpoint(self):
        """Test the health metrics API endpoint."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:health_metrics_api'))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertIn('metrics', data)
        self.assertTrue(len(data['metrics']) > 0)
    
    def test_health_metrics_api_with_type_filter(self):
        """Test the health metrics API with type filter."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(
            reverse('core:health_metrics_type_api', kwargs={'metric_type': 'database'})
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['metric_type'], 'database')
        self.assertIn('metrics', data)
    
    def test_system_alerts_api_get(self):
        """Test the system alerts API GET endpoint."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('core:system_alerts_api'))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertIn('alerts', data)
        self.assertTrue(len(data['alerts']) > 0)
    
    def test_system_alerts_api_resolve_alert(self):
        """Test resolving an alert via the API."""
        alert = SystemAlert.objects.first()
        self.assertFalse(alert.resolved)
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(
            reverse('core:system_alerts_api'),
            data=json.dumps({
                'alert_id': alert.id,
                'action': 'resolve',
                'notes': 'Resolved via test'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertIn('alert', data)
        
        # Check that alert was actually resolved
        alert.refresh_from_db()
        self.assertTrue(alert.resolved)
        self.assertEqual(alert.resolved_by, self.superuser)


class HealthServiceTests(TestCase):
    """Test cases for the health service functionality."""
    
    def test_health_service_get_system_health(self):
        """Test that health service returns system health data."""
        health_data = health_service.get_system_health()
        
        self.assertIn('overall_status', health_data)
        self.assertIn('timestamp', health_data)
        self.assertIn('checks', health_data)
        
        # Check that we have the expected health checks
        expected_checks = ['database', 'cache', 'memory', 'disk', 'system_load', 'logs', 'api', 'celery', 'redis']
        for check in expected_checks:
            self.assertIn(check, health_data['checks'])
    
    def test_health_service_individual_checks(self):
        """Test individual health check methods."""
        # Test database health
        db_health = health_service.get_database_health()
        self.assertIn('status', db_health)
        self.assertIn('message', db_health)
        
        # Test cache health
        cache_health = health_service.get_cache_health()
        self.assertIn('status', cache_health)
        self.assertIn('message', cache_health)
        
        # Test memory health
        memory_health = health_service.get_memory_health()
        self.assertIn('status', memory_health)
        self.assertIn('message', memory_health)
    
    @patch('core.services.health_service.psutil.virtual_memory')
    def test_memory_health_checker_warning_threshold(self, mock_memory):
        """Test memory health checker warning threshold."""
        # Mock high memory usage
        mock_memory.return_value = MagicMock(
            percent=85.0,
            total=8 * 1024**3,  # 8GB
            available=1 * 1024**3,  # 1GB
            used=7 * 1024**3  # 7GB
        )
        
        memory_health = health_service.get_memory_health()
        self.assertEqual(memory_health['status'], 'warning')
        self.assertIn('High memory usage', memory_health['message'])
    
    @patch('core.services.health_service.psutil.virtual_memory')
    def test_memory_health_checker_critical_threshold(self, mock_memory):
        """Test memory health checker critical threshold."""
        # Mock critical memory usage
        mock_memory.return_value = MagicMock(
            percent=95.0,
            total=8 * 1024**3,  # 8GB
            available=0.4 * 1024**3,  # 400MB
            used=7.6 * 1024**3  # 7.6GB
        )
        
        memory_health = health_service.get_memory_health()
        self.assertEqual(memory_health['status'], 'critical')
        self.assertIn('Critical memory usage', memory_health['message'])


class HealthMetricModelTests(TestCase):
    """Test cases for the HealthMetric model."""
    
    def test_health_metric_creation(self):
        """Test creating a health metric."""
        metric = HealthMetric.objects.create(
            metric_name='database',
            metric_value={'connection_time': 50.0},
            status='healthy',
            message='Database connection healthy',
            response_time=50.0
        )
        
        self.assertEqual(metric.metric_name, 'database')
        self.assertEqual(metric.status, 'healthy')
        self.assertIsNotNone(metric.timestamp)
    
    def test_health_metric_record_method(self):
        """Test the record_metric class method."""
        metric = HealthMetric.record_metric(
            metric_name='cache',
            metric_value={'hit_rate': 95.0},
            status='healthy',
            message='Cache performing well',
            response_time=25.0
        )
        
        self.assertEqual(metric.metric_name, 'cache')
        self.assertEqual(metric.status, 'healthy')
        self.assertEqual(metric.response_time, 25.0)
    
    def test_health_metric_get_latest_metrics(self):
        """Test getting latest metrics."""
        # Create multiple metrics
        for i in range(5):
            HealthMetric.objects.create(
                metric_name='database',
                metric_value={'test': i},
                status='healthy',
                message=f'Test metric {i}'
            )
        
        latest_metrics = HealthMetric.get_latest_metrics(limit=3)
        self.assertEqual(len(latest_metrics), 3)
        
        # Should be ordered by timestamp descending
        timestamps = [m.timestamp for m in latest_metrics]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
    
    def test_health_metric_get_metrics_by_type(self):
        """Test getting metrics by type."""
        # Create metrics of different types
        HealthMetric.objects.create(
            metric_name='database',
            metric_value={},
            status='healthy',
            message='Database metric'
        )
        HealthMetric.objects.create(
            metric_name='cache',
            metric_value={},
            status='healthy',
            message='Cache metric'
        )
        
        db_metrics = HealthMetric.get_metrics_by_type('database')
        self.assertEqual(len(db_metrics), 1)
        self.assertEqual(db_metrics[0].metric_name, 'database')


class SystemAlertModelTests(TestCase):
    """Test cases for the SystemAlert model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_system_alert_creation(self):
        """Test creating a system alert."""
        alert = SystemAlert.objects.create(
            alert_type='health_check',
            title='Test Alert',
            message='This is a test alert',
            severity='warning',
            source_metric='database'
        )
        
        self.assertEqual(alert.alert_type, 'health_check')
        self.assertEqual(alert.severity, 'warning')
        self.assertFalse(alert.resolved)
        self.assertIsNotNone(alert.created_at)
    
    def test_system_alert_resolve(self):
        """Test resolving an alert."""
        alert = SystemAlert.objects.create(
            alert_type='health_check',
            title='Test Alert',
            message='This is a test alert',
            severity='critical'
        )
        
        self.assertFalse(alert.resolved)
        
        alert.resolve(user=self.user, notes='Fixed the issue')
        
        self.assertTrue(alert.resolved)
        self.assertEqual(alert.resolved_by, self.user)
        self.assertIsNotNone(alert.resolved_at)
        self.assertEqual(alert.resolution_notes, 'Fixed the issue')
    
    def test_system_alert_reopen(self):
        """Test reopening a resolved alert."""
        alert = SystemAlert.objects.create(
            alert_type='health_check',
            title='Test Alert',
            message='This is a test alert',
            severity='warning'
        )
        
        # Resolve the alert
        alert.resolve(user=self.user, notes='Fixed')
        self.assertTrue(alert.resolved)
        
        # Reopen the alert
        alert.reopen()
        self.assertFalse(alert.resolved)
        self.assertIsNone(alert.resolved_by)
        self.assertIsNone(alert.resolved_at)
        self.assertEqual(alert.resolution_notes, '')
    
    def test_system_alert_create_alert_method(self):
        """Test the create_alert class method."""
        alert = SystemAlert.create_alert(
            alert_type='performance',
            title='High CPU Usage',
            message='CPU usage is above 90%',
            severity='critical',
            source_metric='system_load',
            metadata={'cpu_percent': 95.0}
        )
        
        self.assertEqual(alert.alert_type, 'performance')
        self.assertEqual(alert.severity, 'critical')
        self.assertEqual(alert.metadata['cpu_percent'], 95.0)
    
    def test_system_alert_get_active_alerts(self):
        """Test getting active alerts."""
        # Create resolved and unresolved alerts
        SystemAlert.objects.create(
            alert_type='health_check',
            title='Resolved Alert',
            message='This alert is resolved',
            severity='warning',
            resolved=True
        )
        SystemAlert.objects.create(
            alert_type='health_check',
            title='Active Alert',
            message='This alert is active',
            severity='critical'
        )
        
        active_alerts = SystemAlert.get_active_alerts()
        self.assertEqual(len(active_alerts), 1)
        self.assertEqual(active_alerts[0].title, 'Active Alert')
    
    def test_system_alert_get_critical_alerts(self):
        """Test getting critical alerts."""
        # Create alerts of different severities
        SystemAlert.objects.create(
            alert_type='health_check',
            title='Warning Alert',
            message='This is a warning',
            severity='warning'
        )
        SystemAlert.objects.create(
            alert_type='health_check',
            title='Critical Alert',
            message='This is critical',
            severity='critical'
        )
        
        critical_alerts = SystemAlert.get_critical_alerts()
        self.assertEqual(len(critical_alerts), 1)
        self.assertEqual(critical_alerts[0].title, 'Critical Alert')