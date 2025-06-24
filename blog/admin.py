from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Post, Category

# Register the new Category model
@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Post)
class PostAdmin(ModelAdmin):
    # Add new fields to list_display and list_filter
    list_display = ('title', 'author', 'status', 'is_featured', 'created_at')
    list_filter = ('status', 'author', 'categories', 'is_featured')
    search_fields = ('title', 'content', 'excerpt')
    prepopulated_fields = {'slug': ('title',)}
    
    # Use filter_horizontal for a better ManyToMany widget for categories
    filter_horizontal = ('categories',)
    
    # Update fieldsets to include all new model fields
    fieldsets = (
        ('Main Info', {
            'fields': ('title', 'slug', 'author', 'status', 'is_featured')
        }),
        ('Content', {
            'fields': ('excerpt', 'content', 'featured_image')
        }),
        ('Categorization & Meta', {
            'fields': ('categories', 'read_time')
        }),
    )
