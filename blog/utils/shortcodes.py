import re
from django.utils.safestring import mark_safe
from ..models import MediaItem

class MediaShortcodeProcessor:
    """Process media shortcodes in blog post content"""
    
    @staticmethod
    def process_content(content, post):
        """Process all media shortcodes in content"""
        if not content:
            return content
            
        # Process different types of media shortcodes
        content = MediaShortcodeProcessor._process_image_shortcodes(content, post)
        content = MediaShortcodeProcessor._process_video_shortcodes(content, post)
        content = MediaShortcodeProcessor._process_gallery_shortcodes(content, post)
        content = MediaShortcodeProcessor._process_media_shortcodes(content, post)
        
        return content
    
    @staticmethod
    def _process_image_shortcodes(content, post):
        """Process [image id="123"] shortcodes"""
        pattern = r'\[image\s+id="(\d+)"(?:\s+size="(thumbnail|medium|large|original)")?\]'
        
        def replace_image(match):
            media_id = int(match.group(1))
            size = match.group(2) or 'medium'
            
            try:
                media = post.media_items.get(id=media_id, media_type='image')
                return MediaShortcodeProcessor._render_image(media, size)
            except MediaItem.DoesNotExist:
                return f'[Image {media_id} not found]'
        
        return re.sub(pattern, replace_image, content)
    
    @staticmethod
    def _process_video_shortcodes(content, post):
        """Process [video id="123"] shortcodes"""
        pattern = r'\[video\s+id="(\d+)"\]'
        
        def replace_video(match):
            media_id = int(match.group(1))
            
            try:
                media = post.media_items.get(id=media_id, media_type='video')
                return MediaShortcodeProcessor._render_video(media)
            except MediaItem.DoesNotExist:
                return f'[Video {media_id} not found]'
        
        return re.sub(pattern, replace_video, content)
    
    @staticmethod
    def _process_gallery_shortcodes(content, post):
        """Process [gallery id="123"] shortcodes"""
        pattern = r'\[gallery\s+id="(\d+)"(?:\s+columns="(\d+)")?\]'
        
        def replace_gallery(match):
            media_id = int(match.group(1))
            columns = int(match.group(2)) if match.group(2) else 3
            
            try:
                media = post.media_items.get(id=media_id, media_type='gallery')
                return MediaShortcodeProcessor._render_gallery(media, columns)
            except MediaItem.DoesNotExist:
                return f'[Gallery {media_id} not found]'
        
        return re.sub(pattern, replace_gallery, content)
    
    @staticmethod
    def _process_media_shortcodes(content, post):
        """Process generic [media id="123"] shortcodes"""
        pattern = r'\[media\s+id="(\d+)"\]'
        
        def replace_media(match):
            media_id = int(match.group(1))
            
            try:
                media = post.media_items.get(id=media_id)
                if media.media_type == 'image':
                    return MediaShortcodeProcessor._render_image(media)
                elif media.media_type == 'video':
                    return MediaShortcodeProcessor._render_video(media)
                elif media.media_type == 'gallery':
                    return MediaShortcodeProcessor._render_gallery(media)
                else:
                    return f'[Unsupported media type: {media.media_type}]'
            except MediaItem.DoesNotExist:
                return f'[Media {media_id} not found]'
        
        return re.sub(pattern, replace_media, content)
    
    @staticmethod
    def _render_image(media, size='medium'):
        """Render image HTML"""
        image_field = getattr(media, f'{size}_image', None) or media.original_image
        if not image_field:
            return '[Image not available]'
        
        html = f'''
        <figure class="shortcode-image">
            <img src="{image_field.url}" 
                 alt="{media.alt_text or media.title or ''}" 
                 class="responsive-image"
                 loading="lazy">
            {f'<figcaption>{media.title}</figcaption>' if media.title else ''}
            {f'<p class="image-description">{media.description}</p>' if media.description else ''}
        </figure>
        '''
        return html
    
    @staticmethod
    def _render_video(media):
        """Render video HTML"""
        if not media.video_embed_url:
            return '[Video embed URL not available]'
        
        embed_code = media.get_video_embed_code()
        if not embed_code:
            return '[Video embed code not available]'
        
        html = f'''
        <div class="shortcode-video">
            {embed_code}
            {f'<h4 class="video-title">{media.title}</h4>' if media.title else ''}
            {f'<p class="video-description">{media.description}</p>' if media.description else ''}
        </div>
        '''
        return html
    
    @staticmethod
    def _render_gallery(media, columns=3):
        """Render gallery HTML"""
        if not media.gallery_images:
            return '[Gallery images not available]'
        
        images_html = ''
        for i, image in enumerate(media.gallery_images):
            if 'processed' in image and 'medium' in image['processed']:
                images_html += f'''
                <div class="gallery-item">
                    <img src="{image['processed']['medium']}" 
                         alt="{image.get('alt_text', '')}"
                         onclick="openGalleryLightbox({media.id}, {i})"
                         loading="lazy">
                </div>
                '''
        
        html = f'''
        <div class="shortcode-gallery" data-gallery-id="{media.id}">
            {f'<h4 class="gallery-title">{media.title}</h4>' if media.title else ''}
            <div class="gallery-grid" style="grid-template-columns: repeat({columns}, 1fr);">
                {images_html}
            </div>
            {f'<p class="gallery-description">{media.description}</p>' if media.description else ''}
        </div>
        '''
        return html