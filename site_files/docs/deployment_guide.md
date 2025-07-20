# Site Files Updater - Deployment Guide

This guide provides instructions for deploying the Site Files Updater in a production environment.

## Prerequisites

Before deploying the Site Files Updater, ensure you have:

- A Django project set up and running
- Celery and Redis (or another message broker) installed
- Appropriate file permissions for the static files directory

## Installation

1. Add the `site_files` app to your `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps
    'site_files',
]
```

2. Run migrations to create the necessary database tables:

```bash
python manage.py migrate site_files
```

## Static Files Configuration

The Site Files Updater generates files in your static files directory. To ensure these files are properly collected and served, follow these steps:

### 1. Configure Static Files Settings

In your `settings.py`, ensure you have the following settings:

```python
# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
```

### 2. Create Static Directories

Make sure the static directories exist:

```bash
mkdir -p static
mkdir -p staticfiles
```

### 3. Configure collectstatic

When running `collectstatic`, you need to ensure that the generated files are included. Add the following to your `settings.py`:

```python
# Include site files in collectstatic
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]
```

### 4. Run collectstatic

After the Site Files Updater has generated the files, run:

```bash
python manage.py collectstatic --noinput
```

### 5. Automate collectstatic

To automatically run `collectstatic` after the Site Files Updater runs, you can modify the Celery task in `site_files/tasks.py`:

```python
@shared_task
def update_site_files():
    # ... existing code ...
    
    # Run collectstatic after updating files
    from django.core.management import call_command
    call_command('collectstatic', '--noinput')
```

## Celery Worker Setup

The Site Files Updater uses Celery for scheduled tasks. Here's how to set up Celery workers:

### 1. Configure Celery

In your project's `celery.py` file, ensure you import and register the Site Files Updater tasks:

```python
# yourproject/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yourproject.settings')

app = Celery('yourproject')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load tasks from all registered Django app configs
app.autodiscover_tasks()

# Import site_files tasks explicitly to ensure they're registered
from site_files.tasks import register_scheduled_tasks

# Register the scheduled tasks
register_scheduled_tasks()
```

### 2. Start Celery Worker

In a production environment, you should use a process manager like Supervisor to run Celery workers. Here's a sample Supervisor configuration:

```ini
[program:celery_worker]
command=/path/to/venv/bin/celery -A yourproject worker -l info
directory=/path/to/project
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker.error.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
```

### 3. Start Celery Beat

Celery Beat is responsible for scheduling tasks. Here's a sample Supervisor configuration:

```ini
[program:celery_beat]
command=/path/to/venv/bin/celery -A yourproject beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
directory=/path/to/project
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/beat.log
stderr_logfile=/var/log/celery/beat.error.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=10
```

### 4. Create Log Directory

Create the log directory for Celery:

```bash
mkdir -p /var/log/celery
chown www-data:www-data /var/log/celery
```

## File Permissions

The Site Files Updater needs permission to write to the static files directory. Here's how to set up the correct permissions:

### 1. Identify the User Running Django

Determine which user runs your Django application. This is typically:
- `www-data` for Apache
- `nginx` for Nginx with uwsgi
- The name of your system user if running with runserver

### 2. Set Directory Permissions

Set the appropriate permissions for the static files directory:

```bash
# For Apache
sudo chown -R www-data:www-data static
sudo chmod -R 755 static

# For Nginx with uwsgi
sudo chown -R nginx:nginx static
sudo chmod -R 755 static

# For your system user
sudo chown -R yourusername:yourusername static
sudo chmod -R 755 static
```

### 3. Set File Permissions

Ensure that existing files have the correct permissions:

```bash
find static -type f -exec chmod 644 {} \;
```

### 4. Set Default ACLs (Optional)

For more fine-grained control, you can use Access Control Lists (ACLs):

```bash
# Install ACL tools
sudo apt-get install acl

# Set default ACLs for the directory
sudo setfacl -R -d -m u:www-data:rwx static
```

## Monitoring

To ensure the Site Files Updater is running correctly, set up monitoring:

### 1. Check Celery Task Status

You can use the Django admin interface to check the status of Celery tasks:

1. Install django-celery-results:

```bash
pip install django-celery-results
```

2. Add it to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ... other apps
    'django_celery_results',
]
```

3. Run migrations:

```bash
python manage.py migrate
```

4. Configure Celery to use the Django result backend:

```python
# settings.py
CELERY_RESULT_BACKEND = 'django-db'
```

### 2. Log File Monitoring

Set up log monitoring for the Site Files Updater:

```python
# settings.py
LOGGING = {
    # ... existing logging configuration ...
    'loggers': {
        'site_files': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/site_files.log',
            'formatter': 'verbose',
        },
    },
}
```

Create the log directory:

```bash
mkdir -p /var/log/django
chown www-data:www-data /var/log/django
```

## Troubleshooting

### Common Deployment Issues

1. **File Permission Errors**:
   - Check that the Django process has write permissions to the static files directory
   - Verify that the user running Celery has the necessary permissions

2. **Celery Tasks Not Running**:
   - Check that Celery and Celery Beat are running
   - Verify that the tasks are registered correctly
   - Check the Celery logs for errors

3. **Files Not Being Collected by collectstatic**:
   - Ensure the files are being generated in a directory that's included in `STATICFILES_DIRS`
   - Check that the `STATIC_ROOT` directory is writable

4. **Generated Files Not Accessible**:
   - Verify that your web server is configured to serve static files
   - Check that the files exist in the `STATIC_ROOT` directory after running `collectstatic`

## Security Considerations

1. **File Permissions**:
   - Use the principle of least privilege when setting file permissions
   - Only give write access to the specific directories needed by the Site Files Updater

2. **Celery Security**:
   - Use a secure message broker (Redis with password or RabbitMQ with authentication)
   - Run Celery workers with a dedicated user account

3. **Content Security**:
   - Validate the content of generated files to prevent security issues
   - Implement rate limiting for the management command to prevent abuse

## Conclusion

By following this deployment guide, you should have a properly configured Site Files Updater running in your production environment. Remember to monitor the system regularly and check the generated files to ensure they're being updated correctly.