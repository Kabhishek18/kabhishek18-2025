"""
Custom admin configuration for django-celery-beat integration with Django Unfold.
This module provides enhanced admin interfaces for Celery periodic tasks.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils import timezone
from unfold.admin import ModelAdmin
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
from django_celery_beat.admin import PeriodicTaskAdmin as BasePeriodicTaskAdmin
import json


class UnfoldPeriodicTaskAdmin(BasePeriodicTaskAdmin, ModelAdmin):
    """
    Enhanced PeriodicTask admin with Unfold styling and additional actions.
    """
    list_display = [
        'name', 
        'task', 
        'enabled', 
        'interval', 
        'crontab', 
        'last_run_at', 
        'total_run_count',
        'run_task_action'
    ]
    list_filter = ['enabled', 'one_off', 'last_run_at']
    search_fields = ['name', 'task']
    readonly_fields = ['last_run_at', 'total_run_count', 'date_changed']
    actions = ['enable_tasks', 'disable_tasks', 'run_selected_tasks']
    
    fieldsets = (
        ('Task Information', {
            'fields': ('name', 'task', 'enabled', 'description'),
        }),
        ('Schedule', {
            'fields': ('interval', 'crontab', 'solar', 'clocked'),
            'description': 'Choose one scheduling method'
        }),
        ('Arguments', {
            'fields': ('args', 'kwargs'),
            'classes': ('collapse',),
            'description': 'JSON formatted arguments for the task'
        }),
        ('Execution Options', {
            'fields': ('queue', 'exchange', 'routing_key', 'priority', 'expires', 'one_off'),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('last_run_at', 'total_run_count', 'date_changed'),
            'classes': ('collapse',),
        }),
    )
    
    def run_task_action(self, obj):
        """Add a run button for each task in the list view."""
        if obj.enabled:
            url = reverse('admin:run_periodic_task', args=[obj.pk])
            return format_html(
                '<a class="button" href="{}">Run Now</a>',
                url
            )
        return format_html('<span style="color: #999;">Disabled</span>')
    run_task_action.short_description = 'Actions'
    run_task_action.allow_tags = True
    
    def enable_tasks(self, request, queryset):
        """Enable selected periodic tasks."""
        updated = queryset.update(enabled=True)
        self.message_user(
            request,
            f'{updated} task(s) were successfully enabled.',
            messages.SUCCESS
        )
    enable_tasks.short_description = "Enable selected tasks"
    
    def disable_tasks(self, request, queryset):
        """Disable selected periodic tasks."""
        updated = queryset.update(enabled=False)
        self.message_user(
            request,
            f'{updated} task(s) were successfully disabled.',
            messages.SUCCESS
        )
    disable_tasks.short_description = "Disable selected tasks"
    
    def run_selected_tasks(self, request, queryset):
        """Run selected periodic tasks immediately."""
        from celery import current_app
        
        success_count = 0
        error_count = 0
        
        for task in queryset:
            try:
                # Get the task function
                celery_task = current_app.tasks.get(task.task)
                if celery_task:
                    # Parse arguments
                    args = json.loads(task.args) if task.args else []
                    kwargs = json.loads(task.kwargs) if task.kwargs else {}
                    
                    # Apply the task
                    result = celery_task.apply_async(args=args, kwargs=kwargs)
                    success_count += 1
                    
                    # Update last run time
                    task.last_run_at = timezone.now()
                    task.total_run_count = (task.total_run_count or 0) + 1
                    task.save()
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
        
        if success_count:
            self.message_user(
                request,
                f'{success_count} task(s) were successfully executed.',
                messages.SUCCESS
            )
        if error_count:
            self.message_user(
                request,
                f'{error_count} task(s) failed to execute.',
                messages.ERROR
            )
    
    run_selected_tasks.short_description = "Run selected tasks"
    
    def get_urls(self):
        """Add custom URLs for task actions."""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                'run/<int:task_id>/',
                self.admin_site.admin_view(self.run_task_view),
                name='run_periodic_task',
            ),
        ]
        return custom_urls + urls
    
    def run_task_view(self, request, task_id):
        """View to run a single task."""
        from celery import current_app
        
        try:
            task = PeriodicTask.objects.get(pk=task_id)
            
            # Get the task function
            celery_task = current_app.tasks.get(task.task)
            if celery_task:
                # Parse arguments
                args = json.loads(task.args) if task.args else []
                kwargs = json.loads(task.kwargs) if task.kwargs else {}
                
                # Apply the task
                result = celery_task.apply_async(args=args, kwargs=kwargs)
                
                # Update last run time
                task.last_run_at = timezone.now()
                task.total_run_count = (task.total_run_count or 0) + 1
                task.save()
                
                messages.success(
                    request,
                    f'Task "{task.name}" was successfully executed. Task ID: {result.id}'
                )
            else:
                messages.error(
                    request,
                    f'Task "{task.task}" not found in Celery registry.'
                )
        except PeriodicTask.DoesNotExist:
            messages.error(request, 'Task not found.')
        except Exception as e:
            messages.error(request, f'Error running task: {str(e)}')
        
        return HttpResponseRedirect(reverse('admin:django_celery_beat_periodictask_changelist'))


class UnfoldIntervalScheduleAdmin(ModelAdmin):
    """Enhanced IntervalSchedule admin with Unfold styling."""
    list_display = ['every', 'period']
    list_filter = ['period']
    search_fields = ['every']


class UnfoldCrontabScheduleAdmin(ModelAdmin):
    """Enhanced CrontabSchedule admin with Unfold styling."""
    list_display = ['minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year', 'timezone']
    list_filter = ['timezone']
    search_fields = ['minute', 'hour']


# Unregister the default admin classes
admin.site.unregister(PeriodicTask)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)

# Register the enhanced admin classes
admin.site.register(PeriodicTask, UnfoldPeriodicTaskAdmin)
admin.site.register(IntervalSchedule, UnfoldIntervalScheduleAdmin)
admin.site.register(CrontabSchedule, UnfoldCrontabScheduleAdmin)