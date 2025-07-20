# System Health Dashboard Documentation

## Overview

The System Health Dashboard is a monitoring interface that provides administrators with real-time insights into the application's health status, system metrics, and operational data. This dashboard is accessible through the Django admin interface and provides essential monitoring capabilities for maintaining system reliability.

## Features

- Real-time system health monitoring
- Database connectivity and performance metrics
- Cache system status and performance
- Memory usage monitoring
- Disk space utilization tracking
- System load and performance metrics
- API usage statistics
- Celery worker status monitoring
- Redis connection and performance monitoring
- Automatic alerts for critical issues
- Historical metrics tracking
- Real-time dashboard updates

## Access

The health dashboard is accessible to superusers only through the Django admin interface:

- URL: `/core/dashboard/health/`
- Navigation: Admin Dashboard → System Health

## Dashboard Components

### Health Summary

Provides an overview of the system's health status:

- Overall Status: Healthy, Warning, or Critical
- Total Checks: Number of system components being monitored
- Healthy Services: Number of components reporting healthy status
- Issues Found: Number of components reporting warnings or critical issues

### System Health Checks

Detailed status of individual system components:

- Database: Connection status, query performance, active connections
- Cache: Redis status, memory usage, hit/miss ratios
- Memory: System memory usage, available memory, swap usage
- Disk: Disk space usage, available space, partition information
- System Load: CPU usage, load averages, process count
- Logs: Recent error logs, warning counts
- API: Request counts, error rates, active clients
- Celery: Worker status, queue lengths, task statistics
- Redis: Connection status, memory usage, client count

### Active Alerts

Displays unresolved system alerts:

- Critical alerts are highlighted in red
- Warning alerts are highlighted in yellow
- Each alert shows:
  - Alert title and message
  - Severity level
  - Creation time
  - Source component

### Recent Metrics

Shows the most recent health metrics collected:

- Filterable by metric type
- Displays status, message, and timestamp
- Shows response time for performance monitoring

## Real-time Updates

The dashboard automatically refreshes every 30 seconds to provide up-to-date information:

- Auto-refresh can be paused if needed
- Manual refresh button is available
- Connection status indicator shows if real-time updates are working
- Background updates continue even when the dashboard is not in focus

## Alert Management

Administrators can manage system alerts directly from the dashboard:

- Resolve alerts when issues are fixed
- Add resolution notes for documentation
- Reopen resolved alerts if issues recur
- Filter alerts by type, severity, or status

## API Endpoints

The dashboard provides several API endpoints for programmatic access:

- `/core/api/health/`: Main health dashboard data
- `/core/api/health/metrics/`: Recent health metrics
- `/core/api/health/metrics/<metric_type>/`: Metrics filtered by type
- `/core/api/health/alerts/`: System alerts management

## Security

The health dashboard implements several security measures:

- Superuser-only access control
- CSRF protection for all POST requests
- Rate limiting for API endpoints
- Secure error handling to prevent information leakage
- Timeout handling for slow operations

## Deployment Notes

When deploying the health dashboard to production:

1. Ensure the required Python packages are installed:
   - psutil (for system metrics)
   - redis (for Redis monitoring)

2. Configure the dashboard refresh interval in settings:
   ```python
   HEALTH_DASHBOARD_REFRESH_INTERVAL = 30000  # milliseconds
   ```

3. Set up proper logging for the health service:
   ```python
   LOGGING = {
       # ... existing config ...
       'loggers': {
           'core.services.health_service': {
               'handlers': ['file', 'console'],
               'level': 'WARNING',
               'propagate': True,
           },
       },
   }
   ```

4. Ensure proper permissions for disk access if monitoring disk usage

5. Consider setting up external monitoring to ensure the health dashboard itself is functioning properly

## Troubleshooting

### Dashboard Not Loading

1. Check that the user has superuser permissions
2. Verify database connectivity
3. Check for errors in the Django logs
4. Ensure static files are properly collected

### Metrics Not Updating

1. Check browser console for JavaScript errors
2. Verify network connectivity to the server
3. Check that the health service is running properly
4. Verify Redis connection if using Redis for caching

### False Alerts

1. Review threshold settings in the health service
2. Check for temporary system load that might trigger alerts
3. Verify that all monitored services are properly configured

## Performance Optimization

The health dashboard is optimized for performance:

- Metrics are cached to reduce database load
- API endpoints use pagination to limit response size
- Background updates reduce when the dashboard is not in focus
- Timeout handling prevents long-running checks from blocking the dashboard
- Failed requests automatically retry with exponential backoff