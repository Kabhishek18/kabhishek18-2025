"""
Tests for the Celery tasks in the site_files app.
"""
import sys
from unittest import mock
from django.test import TestCase, override_settings
from django.utils import timezone
from django.core.management import CommandError

from site_files.models import SiteFilesConfig
from site_files.tasks import update_site_files, register_periodic_task, update_periodic_task


class CeleryTaskTests(TestCase):
    """Test cases for the Celery tasks."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a test configuration
        self.config = SiteFilesConfig.objects.create(
            site_name="Test Site",
            site_url="https://example.com",
            update_frequency="daily",
            update_sitemap=True,
            update_robots=True,
            update_security=False,
            update_llms=False
        )
    
    @mock.patch('site_files.tasks.call_command')
    def test_update_site_files_task(self, mock_call_command):
        """Test the update_site_files task."""
        # Call the task
        result = update_site_files()
        
        # Check that call_command was called with the correct arguments
        mock_call_command.assert_called_once_with(
            'update_site_files',
            '--sitemap',
            '--robots',
            '--verbose'
        )
        
        # Check that the task returned a success message
        self.assertIn("completed successfully", result)
        
        # Check that last_update was updated
        self.config.refresh_from_db()
        self.assertIsNotNone(self.config.last_update)
    
    @mock.patch('site_files.tasks.call_command')
    def test_update_site_files_task_no_config(self, mock_call_command):
        """Test the update_site_files task when no configuration exists."""
        # Delete the test configuration
        self.config.delete()
        
        # Call the task
        result = update_site_files()
        
        # Check that call_command was called with the --all argument
        mock_call_command.assert_called_once_with(
            'update_site_files',
            '--all',
            '--verbose'
        )
        
        # Check that the task returned a success message
        self.assertIn("completed successfully", result)
    
    @mock.patch('site_files.tasks.call_command')
    def test_update_site_files_task_no_files_enabled(self, mock_call_command):
        """Test the update_site_files task when no files are enabled for update."""
        # Update configuration to disable all updates
        self.config.update_sitemap = False
        self.config.update_robots = False
        self.config.update_security = False
        self.config.update_llms = False
        self.config.save()
        
        # Call the task
        result = update_site_files()
        
        # Check that call_command was called with the --all argument
        mock_call_command.assert_called_once_with(
            'update_site_files',
            '--all',
            '--verbose'
        )
        
        # Check that the task returned a success message
        self.assertIn("completed successfully", result)
    
    @mock.patch('site_files.tasks.call_command')
    def test_update_site_files_task_error(self, mock_call_command):
        """Test error handling in the update_site_files task."""
        # Configure mock to raise an exception
        mock_call_command.side_effect = CommandError("Test error")
        
        # Call the task
        result = update_site_files()
        
        # Check that the task returned an error message
        self.assertIn("An error occurred", result)
        self.assertIn("Test error", result)
    
    @mock.patch('site_files.tasks.SiteFilesConfig.save')
    @mock.patch('site_files.tasks.call_command')
    def test_update_site_files_task_save_error(self, mock_call_command, mock_save):
        """Test error handling when saving the configuration fails."""
        # Configure mock to raise an exception
        mock_save.side_effect = Exception("Database error")
        
        # Call the task
        result = update_site_files()
        
        # Check that the task returned an error message
        self.assertIn("An error occurred", result)
        self.assertIn("Database error", result)
    
    @mock.patch('django_celery_beat.models.PeriodicTask.objects.create')
    @mock.patch('django_celery_beat.models.PeriodicTask.objects.filter')
    @mock.patch('django_celery_beat.models.CrontabSchedule.objects.get_or_create')
    def test_register_periodic_task_daily(self, mock_get_or_create, mock_filter, mock_create):
        """Test registering a periodic task with daily frequency."""
        # Configure mocks
        mock_filter.return_value.delete.return_value = None
        mock_get_or_create.return_value = (mock.Mock(), True)
        
        # Set daily frequency
        self.config.update_frequency = 'daily'
        self.config.save()
        
        # Call the function
        register_periodic_task()
        
        # Check that the correct schedule was created
        mock_get_or_create.assert_called_once_with(
            minute='0',
            hour='0',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        # Check that the task was created
        mock_create.assert_called_once()
        self.assertEqual(mock_create.call_args[1]['name'], "Update Site Files")
        self.assertEqual(mock_create.call_args[1]['task'], "site_files.tasks.update_site_files")
    
    @mock.patch('django_celery_beat.models.PeriodicTask.objects.create')
    @mock.patch('django_celery_beat.models.PeriodicTask.objects.filter')
    @mock.patch('django_celery_beat.models.CrontabSchedule.objects.get_or_create')
    def test_register_periodic_task_weekly(self, mock_get_or_create, mock_filter, mock_create):
        """Test registering a periodic task with weekly frequency."""
        # Configure mocks
        mock_filter.return_value.delete.return_value = None
        mock_get_or_create.return_value = (mock.Mock(), True)
        
        # Set weekly frequency
        self.config.update_frequency = 'weekly'
        self.config.save()
        
        # Call the function
        register_periodic_task()
        
        # Check that the correct schedule was created
        mock_get_or_create.assert_called_once_with(
            minute='0',
            hour='0',
            day_of_week='0',
            day_of_month='*',
            month_of_year='*',
        )
    
    @mock.patch('django_celery_beat.models.PeriodicTask.objects.create')
    @mock.patch('django_celery_beat.models.PeriodicTask.objects.filter')
    @mock.patch('django_celery_beat.models.CrontabSchedule.objects.get_or_create')
    def test_register_periodic_task_monthly(self, mock_get_or_create, mock_filter, mock_create):
        """Test registering a periodic task with monthly frequency."""
        # Configure mocks
        mock_filter.return_value.delete.return_value = None
        mock_get_or_create.return_value = (mock.Mock(), True)
        
        # Set monthly frequency
        self.config.update_frequency = 'monthly'
        self.config.save()
        
        # Call the function
        register_periodic_task()
        
        # Check that the correct schedule was created
        mock_get_or_create.assert_called_once_with(
            minute='0',
            hour='0',
            day_of_week='*',
            day_of_month='1',
            month_of_year='*',
        )
    
    @mock.patch('django_celery_beat.models.PeriodicTask.objects.create')
    @mock.patch('django_celery_beat.models.PeriodicTask.objects.filter')
    @mock.patch('django_celery_beat.models.CrontabSchedule.objects.get_or_create')
    def test_register_periodic_task_invalid_frequency(self, mock_get_or_create, mock_filter, mock_create):
        """Test registering a periodic task with an invalid frequency."""
        # Configure mocks
        mock_filter.return_value.delete.return_value = None
        mock_get_or_create.return_value = (mock.Mock(), True)
        
        # Set an invalid frequency
        self.config.update_frequency = 'invalid'
        self.config.save()
        
        # Call the function
        register_periodic_task()
        
        # Check that the default (daily) schedule was created
        mock_get_or_create.assert_called_once_with(
            minute='0',
            hour='0',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
    
    @mock.patch('django_celery_beat.models.PeriodicTask.objects.create')
    @mock.patch('django_celery_beat.models.PeriodicTask.objects.filter')
    def test_register_periodic_task_error(self, mock_filter, mock_create):
        """Test error handling in register_periodic_task."""
        # Configure mock to raise an exception
        mock_filter.side_effect = Exception("Test error")
        
        # Call the function
        with mock.patch('site_files.tasks.logger') as mock_logger:
            register_periodic_task()
            
            # Check that the error was logged
            mock_logger.error.assert_called_once()
            self.assertIn("Failed to register periodic task", mock_logger.error.call_args[0][0])
    
    @mock.patch('site_files.tasks.register_periodic_task')
    def test_update_periodic_task_signal(self, mock_register):
        """Test the update_periodic_task signal handler."""
        # Update the configuration to trigger the signal
        self.config.update_frequency = 'weekly'
        self.config.save()
        
        # Check that register_periodic_task was called
        mock_register.assert_called_once()
    
    @mock.patch('site_files.tasks.register_periodic_task')
    def test_ready_function(self, mock_register):
        """Test the ready function."""
        # Import the ready function
        from site_files.tasks import ready
        
        # Call the function
        with mock.patch.object(sys, 'argv', ['manage.py', 'runserver']):
            ready()
            
            # Check that register_periodic_task was called
            mock_register.assert_called_once()
    
    @mock.patch('site_files.tasks.register_periodic_task')
    def test_ready_function_during_migrations(self, mock_register):
        """Test the ready function during migrations."""
        # Import the ready function
        from site_files.tasks import ready
        
        # Call the function with migrate in sys.argv
        with mock.patch.object(sys, 'argv', ['manage.py', 'migrate']):
            ready()
            
            # Check that register_periodic_task was not called
            mock_register.assert_not_called()


if __name__ == '__main__':
    from django.test import runner
    runner.main()
</text>
</invoke>