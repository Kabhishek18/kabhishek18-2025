from django import template
from django.utils.safestring import mark_safe
from django.conf import settings
from ..models import MediaItem
from PIL import Image
import os

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

@register.simple_tag
def get_social_image_url(post, request=None):
    """Get the best image URL for social sharing with absolute URL and enhanced fallback logic"""
    image_url = None
    
    # Priority 1: social_image field (specifically for social sharing)
    if post.social_image:
        image_url = post.social_image.url
    # Priority 2: featured_image field
    elif post.featured_image:
        image_url = post.featured_image.url
    # Priority 3: first featured media item (large version preferred)
    else:
        featured_media = post.media_items.filter(is_featured=True, media_type='image').first()
        if featured_media:
            # Prefer larger images for better social sharing
            if featured_media.large_image:
                image_url = featured_media.large_image.url
            elif featured_media.medium_image:
                image_url = featured_media.medium_image.url
            elif featured_media.original_image:
                image_url = featured_media.original_image.url
        else:
            # Priority 4: first image media item (prefer larger versions)
            first_image = post.media_items.filter(media_type='image').first()
            if first_image:
                if first_image.large_image:
                    image_url = first_image.large_image.url
                elif first_image.medium_image:
                    image_url = first_image.medium_image.url
                elif first_image.original_image:
                    image_url = first_image.original_image.url
            else:
                # Priority 5: Look for any image in media items
                any_image = post.media_items.filter(media_type='image').exclude(
                    large_image__isnull=True, 
                    medium_image__isnull=True, 
                    original_image__isnull=True
                ).first()
                if any_image:
                    if any_image.large_image:
                        image_url = any_image.large_image.url
                    elif any_image.medium_image:
                        image_url = any_image.medium_image.url
                    elif any_image.original_image:
                        image_url = any_image.original_image.url
    
    # Convert to absolute URL
    if image_url:
        if request:
            return request.build_absolute_uri(image_url)
        else:
            # Fallback to settings-based absolute URL
            domain = getattr(settings, 'SITE_DOMAIN', 'https://kabhishek18.com')
            return f"{domain.rstrip('/')}{image_url}"
    
    # Enhanced fallback logic - try multiple default images
    fallback_images = [
        "/static/web-app-manifest-512x512.png",
        "/static/apple-touch-icon.png",
        "/static/favicon-32x32.png"
    ]
    
    for default_image in fallback_images:
        try:
            if request:
                return request.build_absolute_uri(default_image)
            else:
                domain = getattr(settings, 'SITE_DOMAIN', 'https://kabhishek18.com')
                return f"{domain.rstrip('/')}{default_image}"
        except Exception:
            continue
    
    # Final fallback - construct a basic URL
    domain = getattr(settings, 'SITE_DOMAIN', 'https://kabhishek18.com')
    return f"{domain.rstrip('/')}/static/web-app-manifest-512x512.png"

@register.simple_tag
def get_image_dimensions(image_field):
    """Get image dimensions for Open Graph tags"""
    if not image_field:
        return {'width': 512, 'height': 512}  # Default dimensions
    
    try:
        # Try to get dimensions from the image file
        if hasattr(image_field, 'path') and os.path.exists(image_field.path):
            with Image.open(image_field.path) as img:
                return {'width': img.width, 'height': img.height}
    except Exception:
        pass
    
    # Return default dimensions if we can't determine actual size
    return {'width': 1200, 'height': 627}  # LinkedIn recommended dimensions

@register.simple_tag
def get_image_alt_text(post):
    """Get appropriate alt text for social sharing image"""
    # Priority 1: social_image with alt text from featured media
    if post.social_image:
        featured_media = post.media_items.filter(is_featured=True, media_type='image').first()
        if featured_media and featured_media.alt_text:
            return featured_media.alt_text
    
    # Priority 2: featured_image with alt text from featured media
    elif post.featured_image:
        featured_media = post.media_items.filter(is_featured=True, media_type='image').first()
        if featured_media and featured_media.alt_text:
            return featured_media.alt_text
    
    # Priority 3: alt text from first image media item
    first_image = post.media_items.filter(media_type='image').first()
    if first_image and first_image.alt_text:
        return first_image.alt_text
    
    # Fallback: generate alt text from post title
    return f"Featured image for: {post.title}"

@register.simple_tag
def get_image_type(image_field):
    """Get MIME type for an image field"""
    if not image_field:
        return 'image/jpeg'
    
    try:
        # Get file extension
        if hasattr(image_field, 'name') and image_field.name:
            ext = os.path.splitext(image_field.name)[1].lower()
            type_mapping = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.svg': 'image/svg+xml',
            }
            return type_mapping.get(ext, 'image/jpeg')
    except Exception:
        pass
    
    return 'image/jpeg'

@register.simple_tag
def get_linkedin_optimized_image(post, request=None):
    """Get LinkedIn-optimized image (1200x627) if available"""
    # Look for large images that are close to LinkedIn's preferred dimensions
    media_items = post.media_items.filter(media_type='image')
    
    for media_item in media_items:
        if media_item.large_image:
            dimensions = get_image_dimensions(media_item.large_image)
            # Check if dimensions are close to LinkedIn's preferred 1200x627
            if (1100 <= dimensions['width'] <= 1300 and 
                600 <= dimensions['height'] <= 700):
                if request:
                    return request.build_absolute_uri(media_item.large_image.url)
                else:
                    domain = getattr(settings, 'SITE_DOMAIN', 'https://kabhishek18.com')
                    return f"{domain.rstrip('/')}{media_item.large_image.url}"
    
    return None

@register.simple_tag
def get_fallback_images(post, request=None):
    """Get fallback images for social sharing when primary image is not available"""
    fallback_images = []
    
    # Get all available images from the post
    available_images = []
    
    # Add featured image if available
    if post.featured_image:
        available_images.append({
            'field': post.featured_image,
            'priority': 1
        })
    
    # Add social image if available and different from featured
    if post.social_image and post.social_image != post.featured_image:
        available_images.append({
            'field': post.social_image,
            'priority': 0  # Highest priority
        })
    
    # Add media items
    for media_item in post.media_items.filter(media_type='image')[:3]:  # Limit to 3 fallbacks
        if media_item.large_image:
            available_images.append({
                'field': media_item.large_image,
                'priority': 2
            })
        elif media_item.medium_image:
            available_images.append({
                'field': media_item.medium_image,
                'priority': 3
            })
        elif media_item.original_image:
            available_images.append({
                'field': media_item.original_image,
                'priority': 4
            })
    
    # Sort by priority and process
    available_images.sort(key=lambda x: x['priority'])
    
    for img_data in available_images[:4]:  # Limit to 4 total images
        image_field = img_data['field']
        dimensions = get_image_dimensions(image_field)
        
        # Build absolute URL
        if request:
            url = request.build_absolute_uri(image_field.url)
        else:
            domain = getattr(settings, 'SITE_DOMAIN', 'https://kabhishek18.com')
            url = f"{domain.rstrip('/')}{image_field.url}"
        
        fallback_images.append({
            'url': url,
            'width': dimensions['width'],
            'height': dimensions['height'],
            'alt': get_image_alt_text(post),
            'type': get_image_type(image_field)
        })
    
    # Add default fallback if no images available
    if not fallback_images:
        default_image = "/static/web-app-manifest-512x512.png"
        if request:
            url = request.build_absolute_uri(default_image)
        else:
            domain = getattr(settings, 'SITE_DOMAIN', 'https://kabhishek18.com')
            url = f"{domain.rstrip('/')}{default_image}"
        
        fallback_images.append({
            'url': url,
            'width': 512,
            'height': 512,
            'alt': f"Default image for: {post.title}",
            'type': 'image/png'
        })
    
    return fallback_images

@register.inclusion_tag('blog/partials/social_meta_tags.html')
def render_social_meta_tags(post, request):
    """Render comprehensive social media meta tags with enhanced image support"""
    image_url = get_social_image_url(post, request)
    
    # Get image dimensions and metadata
    dimensions = {'width': 1200, 'height': 627}  # Default LinkedIn-optimized dimensions
    image_type = 'image/jpeg'  # Default type
    
    if post.social_image:
        dimensions = get_image_dimensions(post.social_image)
        image_type = get_image_type(post.social_image)
    elif post.featured_image:
        dimensions = get_image_dimensions(post.featured_image)
        image_type = get_image_type(post.featured_image)
    else:
        # Try to get dimensions from media items
        featured_media = post.media_items.filter(is_featured=True, media_type='image').first()
        if featured_media:
            if featured_media.large_image:
                dimensions = get_image_dimensions(featured_media.large_image)
                image_type = get_image_type(featured_media.large_image)
            elif featured_media.medium_image:
                dimensions = get_image_dimensions(featured_media.medium_image)
                image_type = get_image_type(featured_media.medium_image)
            elif featured_media.original_image:
                dimensions = get_image_dimensions(featured_media.original_image)
                image_type = get_image_type(featured_media.original_image)
    
    alt_text = get_image_alt_text(post)
    
    # Get LinkedIn-optimized image if available
    linkedin_optimized_image = get_linkedin_optimized_image(post, request)
    
    # Get fallback images for better social sharing
    fallback_images = get_fallback_images(post, request)
    
    # Build canonical URL
    canonical_url = ''
    if request:
        try:
            from django.urls import reverse
            canonical_url = request.build_absolute_uri(
                reverse('blog:detail', kwargs={'slug': post.slug})
            )
        except Exception:
            canonical_url = request.build_absolute_uri()
    else:
        # Fallback without request
        domain = getattr(settings, 'SITE_DOMAIN', 'https://kabhishek18.com')
        canonical_url = f"{domain.rstrip('/')}/blog/{post.slug}/"
    
    return {
        'post': post,
        'request': request,
        'image_url': image_url,
        'image_width': dimensions['width'],
        'image_height': dimensions['height'],
        'image_alt': alt_text,
        'image_type': image_type,
        'linkedin_optimized_image': linkedin_optimized_image,
        'fallback_images': fallback_images,
        'canonical_url': canonical_url,
    }