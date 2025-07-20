# System Health Dashboard Deployment Guide

This document provides instructions for deploying and configuring the System Health Dashboard in production environments.

## Prerequisites

Before deploying the health dashboard, ensure the following prerequisites are met:

1. **Python Dependencies**:
   ```bash
   pip install psutil redis
   ```

2. **Django Configuration**:
   - Django 3.2 or higher
   - Django REST Framework (if using the API endpoints)

3. **Database**:
   - Properly configured database with sufficient permissions
   - Migrations applied: `python manage.py migrate`

4. **Redis** (optional but recommended):
   - Redis server for caching and improved performance
   - Properly configured in Django settings

## Configuration Settings

Add the following settings to your Django `settings.py` file:

```python
# Health Dashboard Settings
HEALTH_DASHBOARD_REFRESH_INTERVAL = 30000  # milliseconds (30 seconds)
HEALTH_SERVICE_MAX_WORKERS = 4  # Maximum parallel health checks
HEALTH_SERVICE_CACHE_TIMEOUT = 60  # seconds
HEALTH_SERVICE_CRITICAL_CACHE_TIMEOUT = 10  # seconds
HEALTH_METRICS_RETENTION_DAYS = 7  # days to keep metrics in database

# Security Settings
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# If using HTTPS (recommended for production)
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

## Database Considerations

The health dashboard stores metrics in the database. Consider the following:

1. **Table Size**: With default settings, the `HealthMetric` table can grow to contain approximately:
   - 1,000-5,000 records per day depending on system activity
   - ~35,000 records per week with default retention

2. **Indexing**: The model includes appropriate indexes, but consider monitoring query performance.

3. **Cleanup**: Automatic cleanup is implemented, but you may want to set up a cron job for additional maintenance:
   ```python
   # Example management command to run daily
   from django.core.management.base import BaseCommand
   from core.models import HealthMetric
   from django.utils import timezone
   from datetime import timedelta

   class Command(BaseCommand):
       help = 'Clean up old health metrics'

       def handle(self, *args, **options):
           cutoff = timezone.now() - timedelta(days=7)
           deleted, _ = HealthMetric.objects.filter(timestamp__lt=cutoff).delete()
           self.stdout.write(f"Deleted {deleted} old health metrics")
   ```

## Performance Optimization

For optimal performance in production:

1. **Caching**:
   - Ensure Redis is properly configured
   - Consider increasing cache timeouts for non-critical environments

2. **Database**:
   - Consider adding a database index on `(metric_name, status)` if you frequently query by these fields
   - Monitor the size of the `HealthMetric` table and adjust retention as needed

3. **Worker Processes**:
   - Adjust `HEALTH_SERVICE_MAX_WORKERS` based on your server's CPU cores
   - For servers with 4+ cores, setting this to 4-6 is recommended

4. **Memory Usage**:
   - Monitor memory usage of the health service, especially if you have many concurrent users
   - Consider limiting dashboard access to specific admin IPs if needed

## Security Hardening

Additional security measures to consider:

1. **IP Restrictions**:
   - Consider restricting access to admin IPs using a web server configuration or middleware

2. **Rate Limiting**:
   - The dashboard includes basic rate limiting, but consider additional rate limiting at the web server level

3. **Audit Logging**:
   - Enable audit logging for all dashboard access:
   ```python
   # Example middleware
   class HealthDashboardAuditMiddleware:
       def __init__(self, get_response):
           self.get_response = get_response

       def __call__(self, request):
           if request.path.startswith('/core/dashboard/health/'):
               # Log access
               if request.user.is_authenticated:
                   logger.info(f"Health dashboard accessed by {request.user.username} from {request.META.get('REMOTE_ADDR')}")
               else:
                   logger.warning(f"Unauthorized health dashboard access attempt from {request.META.get('REMOTE_ADDR')}")
           
           return self.get_response(request)
   ```

4. **Content Security Policy**:
   - The dashboard sets a basic CSP header, but consider customizing it for your environment

## Monitoring the Monitor

Since the health dashboard itself could experience issues, consider:

1. **External Monitoring**:
   - Set up external monitoring to periodically check the health dashboard endpoint
   - Configure alerts if the dashboard becomes unavailable

2. **Logging**:
   - Ensure proper logging configuration to capture dashboard errors
   - Consider sending critical dashboard errors to a separate log file or monitoring system

3. **Fallback Mechanism**:
   - The dashboard includes fallback mechanisms for component failures
   - Test these mechanisms by temporarily disabling services

## Troubleshooting

Common issues and solutions:

1. **Dashboard Slow to Load**:
   - Check database query performance
   - Verify Redis connection and performance
   - Consider increasing cache timeouts
   - Check for resource-intensive health checks

2. **Missing Metrics**:
   - Verify that the health service is running properly
   - Check for exceptions in the logs
   - Verify database connectivity

3. **High CPU Usage**:
   - Reduce the number of parallel health checks
   - Increase cache timeouts
   - Check for inefficient health checks

4. **Memory Leaks**:
   - Monitor memory usage over time
   - Check for resource leaks in custom health checks
   - Consider restarting the application server periodically

## Backup and Recovery

1. **Database Backup**:
   - Include the `HealthMetric` and `SystemAlert` tables in your regular backup strategy
   - Consider a separate backup schedule if metrics volume is high

2. **Recovery Procedure**:
   - The dashboard can function with an empty metrics database
   - After recovery, it will begin collecting new metrics automatically

## Upgrade Procedure

When upgrading the health dashboard:

1. **Database Migrations**:
   - Apply any new migrations: `python manage.py migrate`

2. **Configuration Changes**:
   - Check for new configuration options in the documentation
   - Update settings as needed

3. **Testing**:
   - Test the dashboard in a staging environment before deploying to production
   - Verify all health checks are functioning properly

4. **Rollback Plan**:
   - Have a rollback plan in case of issues
   - Consider keeping a backup of the previous version's code and configuration