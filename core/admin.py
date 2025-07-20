from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import redirect
from django.utils.html import format_html
from django.utils import timezone
from unfold.admin import ModelAdmin
from .models import Page, Template, Component, HealthMetric, SystemAlert
from django.db import models
from ckeditor.widgets import CKEditorWidget


@admin.register(Component)
class ComponentAdmin(ModelAdmin):
    """
    Admin configuration for individual, editable components using Unfold.
    """
    list_display = ('name','created_at','updated_at' )
    search_fields = ('name', 'content')
    # def formfield_for_dbfield(self, db_field, request, **kwargs):
    #     if db_field.name == 'content':
    #         kwargs['widget'] = CKEditorWidget(config_name='source_only')
    #     return super().formfield_for_dbfield(db_field, request, **kwargs)


    fieldsets = (
        (None, {
            'fields': ('name','slug')
        }),
        ('Component Content', {
            'description': 'Enter the HTML code for this component.',
            'fields': ('content',)
        }),
    )


@admin.register(Template)
class TemplateAdmin(ModelAdmin):
    """
    Admin configuration for template sets (collections of components) using Unfold.
    """
    list_display = ('name','created_at','updated_at' )
    search_fields = ('name',)
    
    # This provides a much better "dual-list" interface for ManyToManyFields,
    # and is styled beautifully by Unfold.
    filter_horizontal = ('files',)


@admin.register(Page)
class PageAdmin(ModelAdmin):
    """
    Admin configuration for the Page model using Unfold.
    """
    list_display = ('title', 'slug', 'template', 'is_published', 'is_homepage')
    list_filter = ('is_published', 'is_homepage', 'template')
    search_fields = ('title', 'content')
    
    # Unfold styles the prepopulated_fields functionality nicely.
    prepopulated_fields = {'slug': ('title',)}
    
    fieldsets = (
        (None, {
            'fields': ('title', 'slug')
        }),
        ('Page Content', {
            'description': "Choose EITHER a template OR enter manual content below. Template takes precedence.",
            'fields': ('template', 'content'),
        }),
        ('SEO & Metadata', {
            'fields': ('meta_description',)
        }),
        ('Page Settings', {
            'fields': ('is_published', 'is_homepage', 'navbar_type')
        }),
    )


@admin.register(HealthMetric)
class HealthMetricAdmin(ModelAdmin):
    """
    Admin configuration for Health Metrics using Unfold.
    """
    list_display = ('metric_name', 'status', 'message', 'response_time', 'timestamp')
    list_filter = ('metric_name', 'status', 'timestamp')
    search_fields = ('message',)
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        (None, {
            'fields': ('metric_name', 'status', 'message')
        }),
        ('Metric Data', {
            'fields': ('metric_value', 'response_time')
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
    
    def has_add_permission(self, request):
        # Health metrics are created automatically, not manually
        return False


@admin.register(SystemAlert)
class SystemAlertAdmin(ModelAdmin):
    """
    Admin configuration for System Alerts using Unfold.
    """
    list_display = ('title', 'alert_type', 'severity', 'resolved', 'created_at', 'resolved_by')
    list_filter = ('alert_type', 'severity', 'resolved', 'created_at')
    search_fields = ('title', 'message')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('alert_type', 'title', 'message', 'severity')
        }),
        ('Source Information', {
            'fields': ('source_metric', 'metadata')
        }),
        ('Resolution', {
            'fields': ('resolved', 'resolved_by', 'resolved_at', 'resolution_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['mark_resolved', 'mark_unresolved']
    
    def mark_resolved(self, request, queryset):
        """Mark selected alerts as resolved."""
        updated = queryset.update(resolved=True, resolved_by=request.user, resolved_at=timezone.now())
        self.message_user(request, f'{updated} alerts marked as resolved.')
    mark_resolved.short_description = "Mark selected alerts as resolved"
    
    def mark_unresolved(self, request, queryset):
        """Mark selected alerts as unresolved."""
        updated = queryset.update(resolved=False, resolved_by=None, resolved_at=None)
        self.message_user(request, f'{updated} alerts marked as unresolved.')
    mark_unresolved.short_description = "Mark selected alerts as unresolved"


# Custom admin site configuration
admin.site.site_header = "System Administration"
admin.site.site_title = "Admin Portal"
admin.site.index_title = "Welcome to System Administration"