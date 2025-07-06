from django.contrib import admin
from django.db import models
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import WysiwygWidget
from .models import Post, Category, NewsletterSubscriber
from ckeditor.widgets import CKEditorWidget


@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = ('title', 'author', 'status', 'is_featured', 'created_at')
    list_filter = ('status', 'is_featured', 'categories', 'author')
    search_fields = ('title', 'excerpt', 'content')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('status', 'is_featured')
    filter_horizontal = ('categories',)

    # Use CKEditor for content fields
    formfield_overrides = {
        models.TextField: {"widget": CKEditorWidget(config_name='default')},
    }
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'content':
            kwargs['widget'] = CKEditorWidget(config_name='default')
        elif db_field.name == 'excerpt':
            kwargs['widget'] = CKEditorWidget(config_name='basic')
        elif db_field.name == 'meta_data':
            kwargs['widget'] = admin.widgets.AdminTextareaWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    fieldsets = (
        ("Main Content", {
            'fields': ('title', 'slug', 'author', 'status', 'excerpt', 'content')
        }),
        ("Organization & Media", {
            'fields': ('categories', 'is_featured', 'featured_image')
        }),
        ("SEO & Meta", {
            'classes': ('collapse',),
            'fields': ('read_time', 'view_count', 'meta_data')
        }),
    )
    
    readonly_fields = ('view_count',)

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    """
    Admin configuration for Categories.
    """
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(ModelAdmin):
    """
    Admin configuration for Newsletter Subscribers.
    """
    list_display = ('email', 'subscribed_at')
    readonly_fields = ('subscribed_at',)