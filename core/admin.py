from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Page, Template, TemplateFile

@admin.register(TemplateFile)
class TemplateFileAdmin(ModelAdmin):
    """
    Admin configuration for individual, editable template files using Unfold.
    """
    list_display = ('name', 'filename', 'get_include_path')
    search_fields = ('name', 'filename', 'content')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'filename')
        }),
        ('Template Content', {
            'description': 'Enter the HTML code for this template include file. The file will be saved automatically.',
            'fields': ('content',)
        }),
    )

@admin.register(Template)
class TemplateAdmin(ModelAdmin):
    """
    Admin configuration for template sets (collections of files) using Unfold.
    """
    list_display = ('name',)
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
            # 'classes': ('collapse',), # Unfold handles this styling elegantly
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

