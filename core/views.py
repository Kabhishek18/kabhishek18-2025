# core/views.py
import json
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.http import Http404, JsonResponse
from django.utils.translation import gettext as _
from django.utils import timezone
from django.core.cache import cache
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test

from blog.models import Post, Category
from .models import Page, Template, Component


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
      
    