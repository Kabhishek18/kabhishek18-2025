# blog/forms.py
from django import forms
from django.core.validators import EmailValidator
from django.utils.html import strip_tags
from .models import NewsletterSubscriber, Comment
from .security_clean import ContentSanitizer
import re

class NewsletterSubscriptionForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'newsletter-input',
                'placeholder': 'Enter your email'
            })
        }
    
    def clean_email(self):
        """Validate email with enhanced security checks"""
        email = self.cleaned_data.get('email', '').strip()
        
        # Use security validator
        is_valid, error_message = ContentSanitizer.validate_email_content(email)
        if not is_valid:
            raise forms.ValidationError(error_message)
        
        return email


class CommentForm(forms.ModelForm):
    """Form for submitting comments with validation and spam prevention"""
    
    class Meta:
        model = Comment
        fields = ['author_name', 'author_email', 'author_website', 'content']
        widgets = {
            'author_name': forms.TextInput(attrs={
                'class': 'comment-input',
                'placeholder': 'Your Name *',
                'required': True,
                'maxlength': 100
            }),
            'author_email': forms.EmailInput(attrs={
                'class': 'comment-input',
                'placeholder': 'Your Email *',
                'required': True
            }),
            'author_website': forms.URLInput(attrs={
                'class': 'comment-input',
                'placeholder': 'Your Website (optional)'
            }),
            'content': forms.Textarea(attrs={
                'class': 'comment-textarea',
                'placeholder': 'Write your comment here... *',
                'required': True,
                'rows': 4,
                'maxlength': 2000
            })
        }
    
    def clean_author_name(self):
        """Validate and clean author name with enhanced security"""
        name = self.cleaned_data.get('author_name', '').strip()
        
        # Use security sanitizer
        name = ContentSanitizer.sanitize_user_input(name, allow_html=False)
        
        if not name:
            raise forms.ValidationError("Name is required.")
        
        if len(name) < 2:
            raise forms.ValidationError("Name must be at least 2 characters long.")
        
        # Check for suspicious patterns
        if re.search(r'https?://', name, re.IGNORECASE):
            raise forms.ValidationError("Name cannot contain URLs.")
        
        return name
    
    def clean_author_email(self):
        """Validate email address with enhanced security"""
        email = self.cleaned_data.get('author_email', '').strip()
        
        # Use security validator
        is_valid, error_message = ContentSanitizer.validate_email_content(email)
        if not is_valid:
            raise forms.ValidationError(error_message)
        
        return email.lower()
    
    def clean_author_website(self):
        """Validate website URL with enhanced security"""
        website = self.cleaned_data.get('author_website', '').strip()
        
        if website:
            # Basic URL validation (can be enhanced later)
            if not website.startswith(('http://', 'https://', 'www.')):
                if '.' not in website:
                    raise forms.ValidationError("Please enter a valid website URL.")
            
            # Add protocol if missing
            if not website.startswith(('http://', 'https://')):
                website = 'http://' + website
        
        return website
    
    def clean_content(self):
        """Validate and clean comment content with enhanced security"""
        content = self.cleaned_data.get('content', '').strip()
        
        # Basic content validation
        if not content:
            raise forms.ValidationError("Comment content is required.")
        
        if len(content) < 10:
            raise forms.ValidationError("Comment must be at least 10 characters long.")
        
        if len(content) > 2000:
            raise forms.ValidationError("Comment is too long (maximum 2000 characters).")
        
        # Sanitize content
        content = ContentSanitizer.sanitize_comment_content(content)
        
        return content


class MediaUploadForm(forms.Form):
    """Form for uploading multimedia content with drag-and-drop support"""
    
    MEDIA_TYPE_CHOICES = [
        ('image', 'Single Image'),
        ('gallery', 'Image Gallery'),
        ('video', 'Video Embed'),
    ]
    
    media_type = forms.ChoiceField(
        choices=MEDIA_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'media-type-select',
            'id': 'media-type-select'
        })
    )
    
    title = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'media-input',
            'placeholder': 'Media title (optional)'
        })
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'media-textarea',
            'placeholder': 'Description or caption (optional)',
            'rows': 3
        })
    )
    
    alt_text = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'media-input',
            'placeholder': 'Alt text for accessibility'
        })
    )
    
    # Image upload fields
    image_file = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'media-file-input',
            'accept': 'image/*',
            'multiple': False
        })
    )
    
    # Gallery upload field - handled separately in view
    gallery_files = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Gallery files will be handled via JavaScript"
    )
    
    # Video embed field
    video_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'media-input',
            'placeholder': 'YouTube or Vimeo URL'
        })
    )
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        media_type = cleaned_data.get('media_type')
        image_file = cleaned_data.get('image_file')
        gallery_files = self.files.getlist('gallery_files')
        video_url = cleaned_data.get('video_url')
        
        if media_type == 'image' and not image_file:
            raise forms.ValidationError("Please upload an image file.")
        
        if media_type == 'gallery' and not gallery_files:
            raise forms.ValidationError("Please upload at least one image for the gallery.")
        
        if media_type == 'video' and not video_url:
            raise forms.ValidationError("Please provide a video URL.")
        
        return cleaned_data
    
    def clean_image_file(self):
        """Validate uploaded image"""
        image_file = self.cleaned_data.get('image_file')
        
        if image_file:
            # Import here to avoid circular imports
            from .services.multimedia_service import multimedia_service
            
            is_valid, error_message = multimedia_service.validate_image_upload(image_file)
            if not is_valid:
                raise forms.ValidationError(error_message)
        
        return image_file
    
    def clean_video_url(self):
        """Validate video URL"""
        video_url = self.cleaned_data.get('video_url')
        
        if video_url:
            # Import here to avoid circular imports
            from .services.multimedia_service import multimedia_service
            
            video_info = multimedia_service.extract_video_embed(video_url)
            if not video_info:
                raise forms.ValidationError(
                    "Unsupported video URL. Please use YouTube or Vimeo URLs."
                )
        
        return video_url


class ImageGalleryForm(forms.Form):
    """Form for creating and managing image galleries"""
    
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'gallery-input',
            'placeholder': 'Gallery title'
        })
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'gallery-textarea',
            'placeholder': 'Gallery description (optional)',
            'rows': 3
        })
    )
    
    images = forms.CharField(
        widget=forms.HiddenInput(),
        help_text="Gallery images will be handled via JavaScript"
    )
    
    def clean_images(self):
        """Validate gallery images"""
        images = self.files.getlist('images')
        
        if not images:
            raise forms.ValidationError("Please select at least one image.")
        
        if len(images) > 20:
            raise forms.ValidationError("Maximum 20 images allowed per gallery.")
        
        # Import here to avoid circular imports
        from .services.multimedia_service import multimedia_service
        
        for image in images:
            is_valid, error_message = multimedia_service.validate_image_upload(image)
            if not is_valid:
                raise forms.ValidationError(f"Invalid image '{image.name}': {error_message}")
        
        return images


class VideoEmbedForm(forms.Form):
    """Form for embedding videos from supported platforms"""
    
    video_url = forms.URLField(
        widget=forms.URLInput(attrs={
            'class': 'video-input',
            'placeholder': 'Enter YouTube or Vimeo URL'
        }),
        help_text="Supported platforms: YouTube, Vimeo"
    )
    
    title = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'video-input',
            'placeholder': 'Video title (optional)'
        })
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'video-textarea',
            'placeholder': 'Video description (optional)',
            'rows': 3
        })
    )
    
    def clean_video_url(self):
        """Validate and extract video information"""
        video_url = self.cleaned_data.get('video_url')
        
        if video_url:
            # Import here to avoid circular imports
            from .services.multimedia_service import multimedia_service
            
            video_info = multimedia_service.extract_video_embed(video_url)
            if not video_info:
                raise forms.ValidationError(
                    "Unsupported video URL. Please use YouTube or Vimeo URLs."
                )
            
            # Store video info for later use
            self.video_info = video_info
        
        return video_url