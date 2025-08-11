from django import template
from django.utils.safestring import mark_safe
from ..models import MediaItem

register = template.Library()

@register.inclusion_tag('blog/partials/media_item.html')
def render_media_item(media_item):
    """Render a single media item"""
    return {'media': media_item}

@register.inclusion_tag('blog/partials/media_gallery.html')
def render_media_gallery(post, media_type=None):
    """Render all media items for a post"""
    media_items = post.media_items.all()
    if media_type:
        media_items = media_items.filter(media_type=media_type)
    return {'media_items': media_items, 'post': post}

@register.simple_tag
def get_featured_media(post):
    """Get the featured media item for a post"""
    return post.media_items.filter(is_featured=True).first()

@register.simple_tag
def get_post_images(post):
    """Get all images for a post"""
    return post.media_items.filter(media_type='image').order_by('order')

@register.simple_tag
def get_post_videos(post):
    """Get all videos for a post"""
    return post.media_items.filter(media_type='video').order_by('order')

@register.filter
def media_embed_code(media_item):
    """Generate embed code for media item"""
    if media_item.media_type == 'video':
        return mark_safe(media_item.get_video_embed_code() or '')
    elif media_item.media_type == 'image':
        img_url = media_item.medium_image.url if media_item.medium_image else media_item.original_image.url
        return mark_safe(f'<img src="{img_url}" alt="{media_item.alt_text}" class="blog-image">')
    return ''

@register.filter
def process_media_shortcodes(content, post):
    """Process media shortcodes in blog content"""
    from ..utils.shortcodes import MediaShortcodeProcessor
    return mark_safe(MediaShortcodeProcessor.process_content(content, post))