"""
Template tags for generating Schema.org structured data markup.

This module provides Django template tags for rendering JSON-LD schema markup
in blog templates to improve SEO and enable rich results in search engines.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.core.cache import caches
from django.template.loader import render_to_string

from blog.services.schema_service import SchemaService
from blog.utils.performance_monitor import performance_monitor, monitor_template_performance

register = template.Library()
logger = logging.getLogger(__name__)


@register.inclusion_tag('blog/partials/schema_markup.html', takes_context=True)
@monitor_template_performance('schema_markup.html')
def render_article_schema(context, post):
    """
    Inclusion tag for rendering complete article schema markup with caching.
    
    Usage:
        {% load schema_tags %}
        {% render_article_schema post %}
    
    Args:
        context: Template context
        post: Post model instance
        
    Returns:
        Context dict for schema_markup.html template
    """
    # Try to get rendered template from cache first
    cache_key = f"schema_template:article:{post.id}:{post.updated_at.timestamp()}"
    
    try:
        template_cache = caches['template_cache']
        cached_context = template_cache.get(cache_key)
        if cached_context:
            logger.debug(f"Schema template cache hit for post {post.id}")
            performance_monitor.record_cache_hit('template_schema')
            return cached_context
        else:
            performance_monitor.record_cache_miss('template_schema')
    except Exception as e:
        logger.warning(f"Schema template cache error for post {post.id}: {str(e)}")
        performance_monitor.record_cache_miss('template_schema')
    
    try:
        request = context.get('request')
        schema_data = SchemaService.generate_article_schema(post, request)
        
        # Validate the schema
        is_valid = SchemaService.validate_schema(schema_data)
        if not is_valid:
            logger.warning(f"Generated schema for post {post.id} failed validation")
        
        # Convert to JSON string for template rendering
        schema_json = json.dumps(schema_data, indent=2, ensure_ascii=False)
        
        context_data = {
            'schema_json': schema_json,
            'schema_data': schema_data,
            'is_valid': is_valid,
            'post': post
        }
        
        # Cache the context data
        try:
            template_cache = caches['template_cache']
            template_cache.set(cache_key, context_data, 1800)  # 30 minutes
            logger.debug(f"Schema template cached for post {post.id}")
        except Exception as e:
            logger.warning(f"Failed to cache schema template for post {post.id}: {str(e)}")
        
        return context_data
        
    except Exception as e:
        logger.error(f"Error in render_article_schema for post {post.id}: {str(e)}")
        return {
            'schema_json': '{}',
            'schema_data': {},
            'is_valid': False,
            'post': post
        }


@register.simple_tag(takes_context=True)
def get_article_schema_json(context, post):
    """
    Simple tag for getting article schema as JSON string.
    
    Usage:
        {% load schema_tags %}
        {% get_article_schema_json post as schema_json %}
    
    Args:
        context: Template context
        post: Post model instance
        
    Returns:
        JSON string of article schema
    """
    try:
        request = context.get('request')
        schema_data = SchemaService.generate_article_schema(post, request)
        return mark_safe(json.dumps(schema_data, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"Error in get_article_schema_json for post {post.id}: {str(e)}")
        return mark_safe('{}')


@register.simple_tag(takes_context=True)
def get_author_schema_json(context, author):
    """
    Simple tag for getting author schema as JSON string.
    
    Usage:
        {% load schema_tags %}
        {% get_author_schema_json post.author as author_json %}
    
    Args:
        context: Template context
        author: User or AuthorProfile model instance
        
    Returns:
        JSON string of author schema
    """
    try:
        request = context.get('request')
        schema_data = SchemaService.generate_standalone_author_schema(author, request)
        return mark_safe(json.dumps(schema_data, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"Error in get_author_schema_json for author {author}: {str(e)}")
        return mark_safe('{}')


@register.simple_tag()
def get_publisher_schema_json():
    """
    Simple tag for getting publisher schema as JSON string.
    
    Usage:
        {% load schema_tags %}
        {% get_publisher_schema_json as publisher_json %}
    
    Returns:
        JSON string of publisher schema
    """
    try:
        schema_data = SchemaService.generate_publisher_schema()
        return mark_safe(json.dumps(schema_data, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"Error in get_publisher_schema_json: {str(e)}")
        return mark_safe('{}')


@register.simple_tag(takes_context=True)
def get_breadcrumb_schema_json(context, post):
    """
    Simple tag for getting breadcrumb schema as JSON string.
    
    Usage:
        {% load schema_tags %}
        {% get_breadcrumb_schema_json post as breadcrumb_json %}
    
    Args:
        context: Template context
        post: Post model instance
        
    Returns:
        JSON string of breadcrumb schema
    """
    try:
        request = context.get('request')
        schema_data = SchemaService.generate_breadcrumb_schema(post, request)
        return mark_safe(json.dumps(schema_data, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"Error in get_breadcrumb_schema_json for post {post.id}: {str(e)}")
        return mark_safe('{}')


@register.simple_tag
def get_article_schema_data(post, request=None):
    """
    Simple tag for getting article schema as Python dict.
    
    Usage:
        {% load schema_tags %}
        {% get_article_schema_data post as schema_data %}
    
    Args:
        post: Post model instance
        request: Optional request object
        
    Returns:
        Dict containing article schema data
    """
    try:
        return SchemaService.generate_article_schema(post, request)
        
    except Exception as e:
        logger.error(f"Error in get_article_schema_data for post {post.id}: {str(e)}")
        return {}


@register.simple_tag
def get_author_schema_data(author, request=None):
    """
    Simple tag for getting author schema as Python dict.
    
    Usage:
        {% load schema_tags %}
        {% get_author_schema_data post.author as author_data %}
    
    Args:
        author: User or AuthorProfile model instance
        request: Optional request object
        
    Returns:
        Dict containing author schema data
    """
    try:
        return SchemaService.generate_author_schema(author, request)
        
    except Exception as e:
        logger.error(f"Error in get_author_schema_data for author {author}: {str(e)}")
        return {}


@register.filter
def to_schema_date(date_value):
    """
    Filter to convert date/datetime to ISO 8601 format for schema markup.
    
    Usage:
        {% load schema_tags %}
        {{ post.created_at|to_schema_date }}
    
    Args:
        date_value: Date or datetime object
        
    Returns:
        ISO 8601 formatted date string
    """
    if not date_value:
        return ""
    
    try:
        # Handle datetime objects
        if hasattr(date_value, 'isoformat'):
            return date_value.isoformat()
        
        # Handle date objects
        elif hasattr(date_value, 'strftime'):
            # Convert date to datetime at midnight
            if hasattr(date_value, 'hour'):
                # Already a datetime
                return date_value.strftime('%Y-%m-%dT%H:%M:%S')
            else:
                # Date object, convert to datetime
                return f"{date_value.strftime('%Y-%m-%d')}T00:00:00"
        
        # Handle string dates
        elif isinstance(date_value, str):
            try:
                # Try to parse as datetime
                dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                return dt.isoformat()
            except:
                return date_value
        
        # Fallback
        return str(date_value)
        
    except Exception as e:
        logger.error(f"Error formatting date {date_value} for schema: {str(e)}")
        return ""


@register.filter
def to_schema_duration(minutes):
    """
    Filter to convert minutes to ISO 8601 duration format.
    
    Usage:
        {% load schema_tags %}
        {{ reading_time|to_schema_duration }}
    
    Args:
        minutes: Number of minutes as integer or string
        
    Returns:
        ISO 8601 duration string (e.g., "PT5M")
    """
    if not minutes:
        return ""
    
    try:
        # Convert to integer if string
        if isinstance(minutes, str):
            minutes = int(float(minutes))
        elif isinstance(minutes, float):
            minutes = int(minutes)
        
        # Format as ISO 8601 duration
        if minutes < 60:
            return f"PT{minutes}M"
        else:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if remaining_minutes > 0:
                return f"PT{hours}H{remaining_minutes}M"
            else:
                return f"PT{hours}H"
                
    except Exception as e:
        logger.error(f"Error formatting duration {minutes} for schema: {str(e)}")
        return ""


@register.filter
def schema_escape(value):
    """
    Filter to safely escape content for JSON-LD schema markup.
    
    Usage:
        {% load schema_tags %}
        {{ post.content|schema_escape }}
    
    Args:
        value: String value to escape
        
    Returns:
        Safely escaped string for JSON
    """
    if not value:
        return ""
    
    try:
        # Convert to string if not already
        str_value = str(value)
        
        # Use Django's escape for HTML entities
        escaped = escape(str_value)
        
        # Additional escaping for JSON
        escaped = escaped.replace('"', '\\"')
        escaped = escaped.replace('\n', '\\n')
        escaped = escaped.replace('\r', '\\r')
        escaped = escaped.replace('\t', '\\t')
        
        return escaped
        
    except Exception as e:
        logger.error(f"Error escaping value for schema: {str(e)}")
        return ""


@register.filter
def truncate_headline(title, max_length=110):
    """
    Filter to truncate headline to optimal SEO length.
    
    Usage:
        {% load schema_tags %}
        {{ post.title|truncate_headline }}
        {{ post.title|truncate_headline:90 }}
    
    Args:
        title: Title string to truncate
        max_length: Maximum length (default: 110)
        
    Returns:
        Truncated title string
    """
    if not title:
        return ""
    
    try:
        max_length = int(max_length)
        if len(title) <= max_length:
            return title
        
        # Truncate at word boundary if possible
        truncated = title[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:  # If we can truncate at a reasonable word boundary
            return truncated[:last_space] + '...'
        else:
            return truncated + '...'
            
    except Exception as e:
        logger.error(f"Error truncating headline {title}: {str(e)}")
        return title


@register.simple_tag
def validate_schema(schema_data):
    """
    Simple tag to validate schema markup.
    
    Usage:
        {% load schema_tags %}
        {% validate_schema schema_data as is_valid %}
    
    Args:
        schema_data: Schema data dictionary
        
    Returns:
        Boolean indicating if schema is valid
    """
    try:
        return SchemaService.validate_schema(schema_data)
    except Exception as e:
        logger.error(f"Error validating schema: {str(e)}")
        return False


@register.simple_tag
def schema_debug_info(schema_data):
    """
    Simple tag for debugging schema markup (development only).
    
    Usage:
        {% load schema_tags %}
        {% schema_debug_info schema_data as debug_info %}
    
    Args:
        schema_data: Schema data dictionary
        
    Returns:
        Debug information string
    """
    try:
        if not schema_data:
            return "Empty schema data"
        
        info = []
        info.append(f"Schema Type: {schema_data.get('@type', 'Unknown')}")
        info.append(f"Has Context: {'@context' in schema_data}")
        info.append(f"Field Count: {len(schema_data)}")
        
        # Check for required fields based on type
        schema_type = schema_data.get('@type')
        if schema_type == 'Article':
            required = ['headline', 'author', 'publisher', 'datePublished']
            missing = [field for field in required if not schema_data.get(field)]
            if missing:
                info.append(f"Missing Required: {', '.join(missing)}")
            else:
                info.append("All Required Fields Present")
        
        return " | ".join(info)
        
    except Exception as e:
        logger.error(f"Error generating schema debug info: {str(e)}")
        return f"Debug Error: {str(e)}"