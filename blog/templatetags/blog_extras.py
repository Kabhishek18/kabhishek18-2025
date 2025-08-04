"""
Custom template tags and filters for the blog app.
"""
from django import template
from django.utils.safestring import mark_safe
from django.urls import reverse
from urllib.parse import quote

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary using a key.
    Usage: {{ dict|get_item:key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0


@register.filter
def social_share_url(post, platform):
    """
    Generate a social sharing URL for a post and platform.
    Usage: {{ post|social_share_url:"facebook" }}
    """
    from ..services import SocialShareService
    
    share_urls = SocialShareService.generate_share_urls(post)
    return share_urls.get(platform, {}).get('url', '')


@register.inclusion_tag('blog/includes/social_share_widget.html', takes_context=True)
def social_share_widget(context, post):
    """
    Render the social sharing widget for a post.
    Usage: {% social_share_widget post %}
    """
    from ..services import SocialShareService
    
    request = context.get('request')
    share_urls = SocialShareService.generate_share_urls(post, request)
    share_counts = SocialShareService.get_share_counts(post)
    total_shares = SocialShareService.get_total_shares(post)
    
    return {
        'post': post,
        'share_urls': share_urls,
        'share_counts': share_counts,
        'total_shares': total_shares,
        'request': request,
    }


@register.simple_tag
def social_meta_tags(post, request=None):
    """
    Generate Open Graph and Twitter Card meta tags for a post.
    Usage: {% social_meta_tags post request %}
    """
    if request:
        post_url = request.build_absolute_uri(
            reverse('blog:detail', kwargs={'slug': post.slug})
        )
        site_url = request.build_absolute_uri('/')
    else:
        post_url = reverse('blog:detail', kwargs={'slug': post.slug})
        site_url = '/'
    
    # Determine the image to use for social sharing
    social_image_url = ''
    if post.social_image:
        social_image_url = post.social_image.url
    elif post.featured_image:
        social_image_url = post.featured_image.url
    
    if social_image_url and request:
        social_image_url = request.build_absolute_uri(social_image_url)
    
    # Prepare description
    description = post.excerpt or (post.content[:160] + '...' if len(post.content) > 160 else post.content)
    description = description.replace('\n', ' ').replace('\r', ' ')
    
    # Generate meta tags
    meta_tags = f'''
    <!-- Open Graph Meta Tags -->
    <meta property="og:title" content="{post.title}">
    <meta property="og:description" content="{description}">
    <meta property="og:url" content="{post_url}">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="Digital Codex">
    <meta property="article:published_time" content="{post.created_at.isoformat()}">
    <meta property="article:author" content="{post.author.get_full_name() or post.author.username}">
    '''
    
    if social_image_url:
        meta_tags += f'''
    <meta property="og:image" content="{social_image_url}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
        '''
    
    # Add categories as tags
    if post.categories.exists():
        for category in post.categories.all():
            meta_tags += f'<meta property="article:section" content="{category.name}">\n    '
    
    # Add tags
    if post.tags.exists():
        for tag in post.tags.all():
            meta_tags += f'<meta property="article:tag" content="{tag.name}">\n    '
    
    # Twitter Card Meta Tags
    meta_tags += f'''
    <!-- Twitter Card Meta Tags -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{post.title}">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:site" content="@kabhishek18">
    <meta name="twitter:creator" content="@kabhishek18">
    '''
    
    if social_image_url:
        meta_tags += f'<meta name="twitter:image" content="{social_image_url}">\n    '
    
    return mark_safe(meta_tags.strip())


@register.filter
def truncate_words_html(value, arg):
    """
    Truncate HTML content to a specified number of words while preserving HTML structure.
    Usage: {{ content|truncate_words_html:30 }}
    """
    from django.utils.html import strip_tags
    from django.utils.text import Truncator
    
    # Strip HTML tags and truncate
    plain_text = strip_tags(value)
    truncator = Truncator(plain_text)
    return truncator.words(arg, html=True)