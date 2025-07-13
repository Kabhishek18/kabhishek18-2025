from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Page, Template, Component
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

    