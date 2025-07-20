from django.contrib import admin
from .models import SiteFilesConfig

@admin.register(SiteFilesConfig)
class SiteFilesConfigAdmin(admin.ModelAdmin):
    """
    Admin interface for the SiteFilesConfig model.
    Provides a user-friendly interface for managing site files configuration.
    """
    list_display = ('site_name', 'site_url', 'update_frequency', 'last_update', 'updated_at')
    
    fieldsets = (
        ('Site Information', {
            'fields': ('site_name', 'site_url'),
        }),
        ('File Paths', {
            'fields': ('sitemap_path', 'robots_path', 'security_path', 'llms_path'),
            'classes': ('collapse',),
        }),
        ('Update Settings', {
            'fields': ('update_frequency', 'update_sitemap', 'update_robots', 'update_security', 'update_llms'),
        }),
        ('Status', {
            'fields': ('last_update',),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('last_update', 'created_at', 'updated_at')
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of the configuration object
        return False
    
    def has_add_permission(self, request):
        # Only allow adding if no configuration exists
        return not SiteFilesConfig.objects.exists()
