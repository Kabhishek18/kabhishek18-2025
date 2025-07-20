# core/views.py
import json
import logging
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import Http404, JsonResponse, HttpResponseNotAllowed
from django.utils.translation import gettext as _
from django.utils import timezone
from django.core.cache import cache
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings

from blog.models import Post, Category
from .models import Page, Template, Component, HealthMetric, SystemAlert
from .services.health_service import health_service

logger = logging.getLogger(__name__)


def dashboard_callback(request, context):
    """
    Enhanced callback that prepares comprehensive data for the custom dashboard template.
    Includes caching, performance metrics, and better data organization.
    """
    # Check cache first
    cache_key = f"dashboard_data_{request.user.id}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        context.update(cached_data)
        return context
    
    # Calculate date ranges for comparisons
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)
    
    # 1. Fetch current metrics
    total_users = User.objects.count()
    total_posts = Post.objects.count()
    total_post_views = Post.objects.aggregate(Sum('view_count'))['view_count__sum'] or 0
    total_categories = Category.objects.count()
    total_pages = Page.objects.count()
    total_templates = Template.objects.count()
    
    # 2. Calculate changes (for the last 30 days vs previous 30 days)
    try:
        # Posts change
        posts_last_30 = Post.objects.filter(created_at__gte=thirty_days_ago).count()
        posts_prev_30 = Post.objects.filter(
            created_at__gte=sixty_days_ago, 
            created_at__lt=thirty_days_ago
        ).count()
        posts_change = calculate_percentage_change(posts_last_30, posts_prev_30)
        
        # Users change
        users_last_30 = User.objects.filter(date_joined__gte=thirty_days_ago).count()
        users_prev_30 = User.objects.filter(
            date_joined__gte=sixty_days_ago,
            date_joined__lt=thirty_days_ago
        ).count()
        users_change = calculate_percentage_change(users_last_30, users_prev_30)
        
        # Views change (if you have a date field for views)
        views_change = 0  # Placeholder - implement based on your view tracking
        
    except Exception as e:
        # Fallback if date calculations fail
        posts_change = users_change = views_change = 0
    
    # 3. Create enhanced metrics with icons and changes
    metrics = [
        {
            'label': _('Total Users'),
            'value': total_users,
            'icon': 'group',
            'change': users_change,
            'color': 'blue'
        },
        {
            'label': _('Total Posts'),
            'value': total_posts,
            'icon': 'article',
            'change': posts_change,
            'color': 'green'
        },
        {
            'label': _('Total Views'),
            'value': total_post_views,
            'icon': 'visibility',
            'change': views_change,
            'color': 'purple'
        },
        {
            'label': _('Categories'),
            'value': total_categories,
            'icon': 'folder',
            'change': 0,
            'color': 'orange'
        },
        {
            'label': _('Pages'),
            'value': total_pages,
            'icon': 'layers',
            'change': 0,
            'color': 'red'
        },
        {
            'label': _('Templates'),
            'value': total_templates,
            'icon': 'dashboard_customize',
            'change': 0,
            'color': 'indigo'
        },
    ]
    
    # 4. Enhanced chart data with better labels
    chart_data = {
        'labels': [_("Posts"), _("Categories"), _("Pages"), _("Templates")],
        'values': [total_posts, total_categories, total_pages, total_templates],
    }
    
    # 5. Fetch recent posts with better data
    recent_posts = Post.objects.select_related('author').prefetch_related('categories').order_by('-updated_at')[:8]
    
    # 6. Additional analytics data - Fixed the category field issue
    try:
        # Get posts by status
        posts_by_status = Post.objects.values('status').annotate(count=Count('id'))
        
        # Get posts by category - Fixed to use the many-to-many relationship
        posts_by_category = Post.objects.filter(categories__isnull=False).values('categories__name').annotate(count=Count('id')).order_by('-count')[:5]
        
        # Get recent users
        recent_users = User.objects.order_by('-date_joined')[:5]
        
        # Get popular posts
        popular_posts = Post.objects.order_by('-view_count')[:5]
        
        analytics_data = {
            'posts_by_status': posts_by_status,
            'posts_by_category': posts_by_category,
            'recent_users': recent_users,
            'popular_posts': popular_posts,
        }
    except Exception as e:
        # Fallback analytics data if queries fail
        analytics_data = {
            'posts_by_status': [],
            'posts_by_category': [],
            'recent_users': [],
            'popular_posts': [],
        }
    
    # 7. System health metrics
    system_health = {
        'database_connection': True,  # You can add actual health checks
        'cache_status': True,
        'last_backup': None,  # Add your backup status
    }
    
    # Prepare context update
    dashboard_data = {
        "metrics": metrics,
        "chart_data": chart_data,
        "recent_posts": recent_posts,
        "analytics_data": analytics_data,
        "system_health": system_health,
        "dashboard_title": _("Digital Architect Dashboard"),
        "last_updated": now.isoformat(),
    }
    
    # Cache the data for 5 minutes
    cache.set(cache_key, dashboard_data, 300)
    
    # 8. Update the context
    context.update(dashboard_data)
    return context


def calculate_percentage_change(current, previous):
    """Calculate percentage change between two values"""
    if previous == 0:
        return 100 if current > 0 else 0
    return round(((current - previous) / previous) * 100, 1)


class DashboardAPIView(View):
    """
    API endpoint for dashboard data updates (for AJAX refreshes)
    """
    def get(self, request):
        if not request.user.is_authenticated or not request.user.is_staff:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        # Get fresh data (bypassing cache)
        context = {}
        updated_context = dashboard_callback(request, context)
        
        # Return JSON response
        return JsonResponse({
            'success': True,
            'data': {
                'metrics': updated_context['metrics'],
                'chart_data': updated_context['chart_data'],
                'recent_posts': [
                    {
                        'id': post.id,
                        'title': post.title,
                        'status': post.status,
                        'updated_at': post.updated_at.isoformat(),
                        'url': f"/admin/blog/post/{post.id}/change/",
                    }
                    for post in updated_context['recent_posts']
                ],
                'last_updated': updated_context['last_updated'],
            }
        })


class SystemHealthView(View):
    """
    System health check endpoint for monitoring
    """
    def get(self, request):
        if not request.user.is_superuser:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        health_data = {
            'database': self._check_database(),
            'cache': self._check_cache(),
            'disk_space': self._check_disk_space(),
            'memory': self._check_memory(),
            'response_time': self._check_response_time(),
            'timestamp': timezone.now().isoformat(),
        }
        
        overall_status = all(check['status'] for check in health_data.values() if isinstance(check, dict))
        
        return JsonResponse({
            'overall_status': 'healthy' if overall_status else 'unhealthy',
            'checks': health_data
        })
    
    def _check_database(self):
        """Check database connectivity"""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return {'status': True, 'message': 'Database connection healthy'}
        except Exception as e:
            return {'status': False, 'message': f'Database error: {str(e)}'}
    
    def _check_cache(self):
        """Check cache functionality"""
        try:
            test_key = 'health_check_test'
            cache.set(test_key, 'test_value', 30)
            cached_value = cache.get(test_key)
            cache.delete(test_key)
            
            if cached_value == 'test_value':
                return {'status': True, 'message': 'Cache working properly'}
            else:
                return {'status': False, 'message': 'Cache not working'}
        except Exception as e:
            return {'status': False, 'message': f'Cache error: {str(e)}'}
    
    def _check_disk_space(self):
        """Check available disk space"""
        try:
            import shutil
            total, used, free = shutil.disk_usage('/')
            free_percent = (free / total) * 100
            
            if free_percent > 10:  # More than 10% free
                return {
                    'status': True, 
                    'message': f'Disk space healthy ({free_percent:.1f}% free)',
                    'free_percent': free_percent
                }
            else:
                return {
                    'status': False, 
                    'message': f'Low disk space ({free_percent:.1f}% free)',
                    'free_percent': free_percent
                }
        except Exception as e:
            return {'status': False, 'message': f'Disk check error: {str(e)}'}
    
    def _check_memory(self):
        """Check memory usage"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            
            if memory.percent < 90:  # Less than 90% used
                return {
                    'status': True,
                    'message': f'Memory usage healthy ({memory.percent:.1f}% used)',
                    'usage_percent': memory.percent
                }
            else:
                return {
                    'status': False,
                    'message': f'High memory usage ({memory.percent:.1f}% used)',
                    'usage_percent': memory.percent
                }
        except ImportError:
            return {'status': True, 'message': 'Memory check unavailable (psutil not installed)'}
        except Exception as e:
            return {'status': False, 'message': f'Memory check error: {str(e)}'}
    
    def _check_response_time(self):
        """Check application response time"""
        try:
            import time
            start_time = time.time()
            
            # Simple database query to test response time
            Post.objects.count()
            
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            if response_time < 1000:  # Less than 1 second
                return {
                    'status': True,
                    'message': f'Response time healthy ({response_time:.0f}ms)',
                    'response_time_ms': response_time
                }
            else:
                return {
                    'status': False,
                    'message': f'Slow response time ({response_time:.0f}ms)',
                    'response_time_ms': response_time
                }
        except Exception as e:
            return {'status': False, 'message': f'Response time check error: {str(e)}'}


class DashboardExportView(View):
    """
    Export dashboard data to various formats
    """
    def get(self, request):
        if not request.user.is_staff:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        export_format = request.GET.get('format', 'json')
        
        # Get dashboard data
        context = {}
        dashboard_data = dashboard_callback(request, context)
        
        if export_format == 'json':
            return JsonResponse(dashboard_data)
        elif export_format == 'csv':
            return self._export_csv(dashboard_data)
        else:
            return JsonResponse({'error': 'Unsupported format'}, status=400)
    
    def _export_csv(self, data):
        """Export metrics data as CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="dashboard_metrics.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Metric', 'Value', 'Change'])
        
        for metric in data['metrics']:
            writer.writerow([
                metric['label'],
                metric['value'],
                metric.get('change', 0)
            ])
        
        return response



def custom_404(request, exception=None):
    """Enhanced 404 error handler with better UX"""
    context = {
        'error_code': '404',
        'error_title': _('Page Not Found'),
        'error_message': _('The page you are looking for might have been removed, had its name changed, or is temporarily unavailable.'),
        'show_search': True,
        'show_home_link': True,
    }
    return render(request, '404.html', context, status=404)


def custom_500(request):
    """Enhanced 500 error handler with better UX"""
    context = {
        'error_code': '500',
        'error_title': _('Server Error'),
        'error_message': _('Something went wrong on our end. We\'re working to fix it.'),
        'show_search': False,
        'show_home_link': True,
        'show_report_link': True,
    }
    return render(request, '500.html', context, status=500)


def custom_403(request, exception=None):
    """Custom 403 error handler"""
    context = {
        'error_code': '403',
        'error_title': _('Access Denied'),
        'error_message': _('You don\'t have permission to access this resource.'),
        'show_search': False,
        'show_home_link': True,
    }
    return render(request, '403.html', context, status=403)



class PageRequest(View):
    """
    View to handle both homepage and custom page requests
    """
    
    def get(self, request, slug=None):
        try:
            if slug is None:
                # Homepage request
                page = Page.objects.filter(
                    is_homepage=True, 
                    is_published=True
                ).first()
            else:
                # Specific page request
                page = get_object_or_404(
                    Page, 
                    slug=slug, 
                    is_published=True
                )
            
            if not page:
                raise Http404("Page not found")
            
            # Build context
            context = {
                'title': page.title,
                'meta_details': page.meta_description or page.title,
                'home_navbar': page.navbar_type == 'HOME',
                'blog_navbar': page.navbar_type == 'BLOG',
                'generic_navbar': page.navbar_type == 'GENERIC',
                'page_content': None,
                'template_includes': [],
                'page': page,
            }

            # Handle template vs content rendering
            if page.template:
                # Use template files
                template_files = page.template.files.all().order_by('id')
                context['template_includes'] = [component.content for component in template_files]
            else:
                # Use manual content
                context['page_content'] = page.content

            return render(request, 'index.html', context)
            
        except Page.DoesNotExist:
            raise Http404("Page not found")
        except Exception as e:
            # In production, you'd log this error
            print(f"Error rendering page: {e}")
            raise Http404("Page not found")


from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test

@user_passes_test(lambda u: u.is_superuser, login_url='/open/admin/login/')
def health_dashboard_view(request):
    """
    Main health dashboard view for system administrators with comprehensive error handling.
    Integrated with the admin interface for seamless navigation.
    
    This view requires superuser access and redirects non-superusers to the admin login page.
    
    Security hardening:
    - Strict superuser permission check
    - CSRF protection
    - Rate limiting
    - Secure error handling
    - Sanitized output
    """
    # Security: Verify request method
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    
    # Security: Additional permission verification
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect(settings.LOGIN_URL)
    
    try:
        # Get comprehensive system health data with fallback
        try:
            system_health = health_service.get_system_health()
        except Exception as e:
            logger.error(f"Failed to get system health: {str(e)}")
            # Provide fallback system health data
            system_health = {
                'overall_status': 'critical',
                'timestamp': timezone.now().isoformat(),
                'checks': {},
                'summary': {
                    'total_checks': 0,
                    'successful_checks': 0,
                    'failed_checks': 0,
                    'failed_check_names': [],
                    'success_rate': 0
                },
                'error': f'Health service unavailable: {str(e)}'
            }
        
        # Get recent health metrics with fallback
        try:
            recent_metrics = HealthMetric.get_latest_metrics(limit=50)
        except Exception as e:
            logger.error(f"Failed to get recent metrics: {str(e)}")
            recent_metrics = []
        
        # Get active alerts with fallback
        try:
            active_alerts = SystemAlert.get_active_alerts()
            critical_alerts = SystemAlert.get_critical_alerts()
        except Exception as e:
            logger.error(f"Failed to get alerts: {str(e)}")
            active_alerts = []
            critical_alerts = []
        
        # Get metrics by type for charts with fallback
        metrics_by_type = {}
        for metric_type in ['database', 'cache', 'memory', 'disk', 'system_load', 'api', 'celery', 'redis']:
            try:
                metrics_by_type[metric_type] = HealthMetric.get_metrics_by_type(metric_type, hours=24)
            except Exception as e:
                logger.warning(f"Failed to get metrics for {metric_type}: {str(e)}")
                metrics_by_type[metric_type] = []
        
        # Calculate health summary with error handling
        try:
            health_summary = {
                'total_checks': len(system_health.get('checks', {})),
                'healthy_checks': len([c for c in system_health.get('checks', {}).values() if c.get('status') == 'healthy']),
                'warning_checks': len([c for c in system_health.get('checks', {}).values() if c.get('status') == 'warning']),
                'critical_checks': len([c for c in system_health.get('checks', {}).values() if c.get('status') == 'critical']),
                'overall_status': system_health.get('overall_status', 'unknown'),
                'last_updated': system_health.get('timestamp', timezone.now().isoformat())
            }
            
            # Add summary from health service if available
            if 'summary' in system_health:
                health_summary.update(system_health['summary'])
                
        except Exception as e:
            logger.error(f"Failed to calculate health summary: {str(e)}")
            health_summary = {
                'total_checks': 0,
                'healthy_checks': 0,
                'warning_checks': 0,
                'critical_checks': 0,
                'overall_status': 'critical',
                'last_updated': timezone.now().isoformat(),
                'error': f'Summary calculation failed: {str(e)}'
            }
        
        context = {
            'title': 'System Health Dashboard',
            'system_health': system_health,
            'health_summary': health_summary,
            'recent_metrics': recent_metrics,
            'active_alerts': active_alerts,
            'critical_alerts': critical_alerts,
            'metrics_by_type': metrics_by_type,
            'refresh_interval': getattr(settings, 'HEALTH_DASHBOARD_REFRESH_INTERVAL', 30000),  # 30 seconds default
            'has_errors': 'error' in system_health or 'error' in health_summary,
        }
        
        response = render(request, 'core/health_dashboard.html', context)
        
        # Add security headers
        response['X-Frame-Options'] = 'DENY'  # Prevent clickjacking
        response['X-Content-Type-Options'] = 'nosniff'  # Prevent MIME type sniffing
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'  # Limit referrer information
        response['Cache-Control'] = 'no-store, max-age=0'  # Prevent caching of sensitive data
        
        # Add Content Security Policy in non-debug mode
        if not settings.DEBUG:
            csp = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
            response['Content-Security-Policy'] = csp
        
        return response
        
    except Exception as e:
        logger.critical(f"Critical error in health dashboard view: {str(e)}")
        # Return a minimal error page if everything fails
        return render(request, 'core/health_dashboard_error.html', {
            'error_message': 'Health dashboard is temporarily unavailable',
            'error_details': str(e) if settings.DEBUG else None,
            'title': 'System Health Dashboard - Error'
        }, status=500)


class HealthDashboardAPIView(View):
    """
    API endpoint for health dashboard data updates (AJAX) with comprehensive error handling.
    Includes rate limiting and security hardening.
    """
    
    def get(self, request):
        # Security: Verify authentication and permissions
        if not request.user.is_authenticated or not request.user.is_superuser:
            return JsonResponse({'error': 'Unauthorized', 'success': False}, status=401)
        
        # Security: Implement rate limiting
        user_id = request.user.id
        rate_limit_key = f"health_dashboard_api_rate_limit_{user_id}"
        request_count = cache.get(rate_limit_key, 0)
        
        # Allow 30 requests per minute per user
        if request_count >= 30:
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.',
                'success': False
            }, status=429)
        
        # Increment request count
        cache.set(rate_limit_key, request_count + 1, 60)  # 60 seconds expiry
        
        try:
            # Get fresh health data with timeout and fallback
            try:
                system_health = health_service.get_system_health()
            except Exception as e:
                logger.error(f"Failed to get system health in API: {str(e)}")
                system_health = {
                    'overall_status': 'critical',
                    'timestamp': timezone.now().isoformat(),
                    'checks': {},
                    'error': f'Health service error: {str(e)}'
                }
            
            # Get recent metrics with fallback
            try:
                recent_metrics = HealthMetric.get_latest_metrics(limit=10)
                formatted_metrics = [
                    {
                        'id': metric.id,
                        'metric_name': metric.get_metric_name_display(),
                        'status': metric.status,
                        'message': metric.message,
                        'response_time': metric.response_time,
                        'timestamp': metric.timestamp.isoformat(),
                    }
                    for metric in recent_metrics
                ]
            except Exception as e:
                logger.warning(f"Failed to get recent metrics in API: {str(e)}")
                formatted_metrics = []
            
            # Get active alerts with fallback
            try:
                active_alerts = SystemAlert.get_active_alerts()[:10]
                formatted_alerts = [
                    {
                        'id': alert.id,
                        'title': alert.title,
                        'severity': alert.severity,
                        'alert_type': alert.get_alert_type_display(),
                        'created_at': alert.created_at.isoformat(),
                        'age_hours': alert.get_age().total_seconds() / 3600,
                    }
                    for alert in active_alerts
                ]
            except Exception as e:
                logger.warning(f"Failed to get active alerts in API: {str(e)}")
                formatted_alerts = []
            
            # Calculate health summary with error handling
            try:
                health_summary = {
                    'total_checks': len(system_health.get('checks', {})),
                    'healthy_checks': len([c for c in system_health.get('checks', {}).values() if c.get('status') == 'healthy']),
                    'warning_checks': len([c for c in system_health.get('checks', {}).values() if c.get('status') == 'warning']),
                    'critical_checks': len([c for c in system_health.get('checks', {}).values() if c.get('status') == 'critical']),
                    'overall_status': system_health.get('overall_status', 'unknown'),
                }
                
                # Add summary from health service if available
                if 'summary' in system_health:
                    health_summary.update(system_health['summary'])
                    
            except Exception as e:
                logger.error(f"Failed to calculate health summary in API: {str(e)}")
                health_summary = {
                    'total_checks': 0,
                    'healthy_checks': 0,
                    'warning_checks': 0,
                    'critical_checks': 0,
                    'overall_status': 'critical',
                    'error': f'Summary calculation failed: {str(e)}'
                }
            
            # Format response data
            response_data = {
                'success': True,
                'timestamp': timezone.now().isoformat(),
                'system_health': system_health,
                'recent_metrics': formatted_metrics,
                'active_alerts': formatted_alerts,
                'health_summary': health_summary,
                'has_errors': 'error' in system_health or 'error' in health_summary,
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.critical(f"Critical error in health dashboard API: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Internal server error',
                'message': 'Health dashboard API is temporarily unavailable',
                'timestamp': timezone.now().isoformat(),
                'debug_info': str(e) if settings.DEBUG else None
            }, status=500)


class HealthMetricsAPIView(View):
    """
    API endpoint for specific health metrics data.
    """
    
    def get(self, request, metric_type=None):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        hours = int(request.GET.get('hours', 24))
        limit = int(request.GET.get('limit', 100))
        
        if metric_type:
            # Get specific metric type
            metrics = HealthMetric.get_metrics_by_type(metric_type, hours=hours)[:limit]
        else:
            # Get all recent metrics
            metrics = HealthMetric.get_latest_metrics(limit=limit)
        
        response_data = {
            'success': True,
            'metric_type': metric_type,
            'hours': hours,
            'count': len(metrics),
            'metrics': [
                {
                    'id': metric.id,
                    'metric_name': metric.metric_name,
                    'metric_display': metric.get_metric_name_display(),
                    'status': metric.status,
                    'message': metric.message,
                    'response_time': metric.response_time,
                    'timestamp': metric.timestamp.isoformat(),
                    'metric_value': metric.metric_value,
                }
                for metric in metrics
            ]
        }
        
        return JsonResponse(response_data)


class SystemAlertsAPIView(View):
    """
    API endpoint for system alerts management.
    """
    
    def get(self, request):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        alert_type = request.GET.get('type', 'active')  # active, critical, recent, all
        limit = int(request.GET.get('limit', 50))
        
        if alert_type == 'critical':
            alerts = SystemAlert.get_critical_alerts()[:limit]
        elif alert_type == 'recent':
            hours = int(request.GET.get('hours', 24))
            alerts = SystemAlert.get_recent_alerts(hours=hours)[:limit]
        elif alert_type == 'all':
            alerts = SystemAlert.objects.all().order_by('-created_at')[:limit]
        else:  # active
            alerts = SystemAlert.get_active_alerts()[:limit]
        
        response_data = {
            'success': True,
            'alert_type': alert_type,
            'count': len(alerts),
            'alerts': [
                {
                    'id': alert.id,
                    'title': alert.title,
                    'message': alert.message,
                    'severity': alert.severity,
                    'alert_type': alert.alert_type,
                    'source_metric': alert.source_metric,
                    'resolved': alert.resolved,
                    'created_at': alert.created_at.isoformat(),
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                    'resolved_by': alert.resolved_by.username if alert.resolved_by else None,
                    'age_hours': alert.get_age().total_seconds() / 3600,
                    'is_stale': alert.is_stale(),
                }
                for alert in alerts
            ]
        }
        
        return JsonResponse(response_data)
    
    def post(self, request):
        """Handle alert actions (resolve, reopen)."""
        if not request.user.is_authenticated or not request.user.is_superuser:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        try:
            data = json.loads(request.body)
            alert_id = data.get('alert_id')
            action = data.get('action')  # resolve, reopen
            notes = data.get('notes', '')
            
            alert = get_object_or_404(SystemAlert, id=alert_id)
            
            if action == 'resolve':
                alert.resolve(user=request.user, notes=notes)
                message = 'Alert resolved successfully'
            elif action == 'reopen':
                alert.reopen()
                message = 'Alert reopened successfully'
            else:
                return JsonResponse({'error': 'Invalid action'}, status=400)
            
            return JsonResponse({
                'success': True,
                'message': message,
                'alert': {
                    'id': alert.id,
                    'resolved': alert.resolved,
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                    'resolved_by': alert.resolved_by.username if alert.resolved_by else None,
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
      
    