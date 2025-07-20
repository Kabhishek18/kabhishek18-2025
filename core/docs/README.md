# System Health Dashboard

## Overview

The System Health Dashboard is a comprehensive monitoring solution for Django applications. It provides real-time insights into system health, performance metrics, and operational data through an intuitive web interface integrated with the Django admin.

## Documentation Index

- [Health Dashboard Documentation](health_dashboard.md) - Main documentation and user guide
- [Security Hardening](health_dashboard_security.md) - Security measures and best practices
- [Deployment Guide](health_dashboard_deployment.md) - Deployment instructions and configuration

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

## Quick Start

1. Ensure you have superuser access to the Django admin
2. Navigate to `/core/dashboard/health/` or click "System Health" in the admin navigation
3. View real-time system health metrics and alerts
4. The dashboard automatically refreshes every 30 seconds

## Architecture

The health dashboard consists of the following components:

1. **Health Service** - Core service that collects and aggregates health metrics
2. **Health Checkers** - Individual components that check specific system aspects
3. **Dashboard View** - Web interface for displaying health data
4. **API Endpoints** - JSON endpoints for real-time updates
5. **Data Models** - Database models for storing metrics and alerts

## Performance Optimizations

The dashboard includes several performance optimizations:

- Parallel execution of health checks
- Caching of health check results
- Adaptive refresh intervals based on system status
- Efficient DOM updates using requestAnimationFrame
- Minimized DOM operations through targeted updates
- CSS optimizations for smoother animations
- Resource cleanup to prevent memory leaks
- Exponential backoff for failed requests

## Security Features

Security is a top priority for the health dashboard:

- Superuser-only access control
- CSRF protection for all requests
- Rate limiting for API endpoints
- Secure error handling
- HTTP security headers
- Content Security Policy
- Input validation and sanitization

## Customization

The health dashboard can be customized through Django settings:

```python
# Health Dashboard Settings
HEALTH_DASHBOARD_REFRESH_INTERVAL = 30000  # milliseconds
HEALTH_SERVICE_MAX_WORKERS = 4  # Maximum parallel health checks
HEALTH_SERVICE_CACHE_TIMEOUT = 60  # seconds
HEALTH_SERVICE_CRITICAL_CACHE_TIMEOUT = 10  # seconds
HEALTH_METRICS_RETENTION_DAYS = 7  # days
```

## Contributing

When contributing to the health dashboard, please follow these guidelines:

1. Write comprehensive tests for new features
2. Follow security best practices
3. Optimize for performance
4. Document all changes
5. Follow Django coding style

## License

This project is licensed under the same license as the main application.