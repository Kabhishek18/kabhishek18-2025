from django.contrib import admin
from django.db import models
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import WysiwygWidget
from .models import Post, Category, NewsletterSubscriber

@admin.register(Post)
class PostAdmin(ModelAdmin):
    """
    Admin configuration for Blog Posts, providing a rich interface
    for content management with a WYSIWYG editor.
    """
    list_display = ('title', 'author', 'status', 'is_featured', 'created_at')
    list_filter = ('status', 'is_featured', 'categories', 'author')
    search_fields = ('title', 'excerpt', 'content')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('status', 'is_featured')
    
    # Use filter_horizontal for a better ManyToMany widget for categories
    filter_horizontal = ('categories',)

    # Override the default TextField widget with Unfold's WYSIWYG editor
    formfield_overrides = {
        models.TextField: {"widget": WysiwygWidget},
    }
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # Use normal textarea for meta_data field instead of WYSIWYG
        if db_field.name == 'meta_data':
            kwargs['widget'] = admin.widgets.AdminTextareaWidget(attrs={
                'placeholder': 'Enter links and metadata (one per line)\nExample:\nhttps://example.com - Source Article\nhttps://github.com/repo - Related Code'
            })
            return db_field.formfield(**kwargs)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    fieldsets = (
        ("Main Content", {
            'fields': ('title', 'slug', 'author', 'status', 'excerpt', 'content')
        }),
        ("Organization & Media", {
            'fields': ('categories', 'is_featured', 'featured_image')
        }),
        ("SEO & Meta", {
            'classes': ('collapse',), # Make this section collapsible
            'fields': ('read_time', 'view_count', 'meta_data')
        }),
    )
    
    readonly_fields = ('view_count',) # view_count should not be manually editable

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