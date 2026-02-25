"""
Enhanced admin interface for content quality management
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render
from django.http import JsonResponse
from blog.models import Post
from blog.content_quality import generate_quality_report


class QualityScoreMixin:
    """Mixin to add quality score functionality to admin"""
    
    def quality_score_display(self, obj):
        """Display quality score with color coding"""
        if not obj.content:
            return format_html('<span style="color: gray;">N/A</span>')
        
        # Generate quality report (cached for performance)
        from django.core.cache import cache
        cache_key = f"quality_score_{obj.id}_{obj.updated_at.timestamp()}"
        
        score = cache.get(cache_key)
        if score is None:
            report = generate_quality_report(obj.content, obj.title, obj.excerpt)
            score = report['score']
            cache.set(cache_key, score, 3600)  # Cache for 1 hour
        
        # Color code based on score
        if score >= 90:
            color = '#28a745'  # Green
            emoji = '🌟'
        elif score >= 75:
            color = '#28a745'  # Green
            emoji = '✅'
        elif score >= 60:
            color = '#ffc107'  # Yellow
            emoji = '⚠️'
        else:
            color = '#dc3545'  # Red
            emoji = '❌'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}/100</span>',
            color, emoji, int(round(score))
        )
    
    quality_score_display.short_description = 'Quality Score'
    quality_score_display.admin_order_field = 'created_at'
    
    def needs_review_display(self, obj):
        """Display if post needs review"""
        if obj.status == 'draft':
            return format_html('<span style="color: orange;">📝 Review Needed</span>')
        elif obj.status == 'published':
            return format_html('<span style="color: green;">✅ Published</span>')
        else:
            return obj.status
    
    needs_review_display.short_description = 'Review Status'


class ContentQualityAdmin(admin.ModelAdmin):
    """Admin interface with quality checking features"""
    pass


def register_quality_admin(admin_class):
    """Decorator to add quality features to existing admin"""
    
    # Add quality score to list display if not already there
    if hasattr(admin_class, 'list_display'):
        if 'quality_score_display' not in admin_class.list_display:
            admin_class.list_display = list(admin_class.list_display) + ['quality_score_display']
    
    # Add the mixin
    admin_class.__bases__ = (QualityScoreMixin,) + admin_class.__bases__
    
    return admin_class
