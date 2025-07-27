from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.urls import reverse
from django.utils.html import strip_tags
from django.contrib.auth.models import User
from django.core.validators import EmailValidator
import readtime
import secrets
import hashlib


# A model to represent categories for organizing blog posts.
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subcategories',
        help_text="Select a parent category to create a subcategory"
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
        unique_together = ['name', 'parent']  # Allow same name in different parent categories
    
    
    def save(self, *args, **kwargs):
        # Auto-generate the slug from the name if it's not provided.
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# A model to represent tags for organizing and categorizing blog posts
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, help_text="Tag name (e.g., 'Python', 'Django')")
    slug = models.SlugField(max_length=50, unique=True, blank=True, help_text="URL-friendly version of the tag name")
    color = models.CharField(max_length=7, default='#007acc', help_text="Hex color code for tag display (e.g., #007acc)")
    description = models.TextField(blank=True, help_text="Optional description of what this tag represents")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
        ]

    def save(self, *args, **kwargs):
        # Auto-generate the slug from the name if it's not provided
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_post_count(self):
        """Return the number of posts associated with this tag"""
        return self.posts.filter(status='published').count()


# The main model for a single blog post.
class Post(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('scheduled', 'Scheduled'),
        ('archived', 'Archived'),
    )
    
    title = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True, help_text="URL-friendly version of the title. Leave blank to auto-generate.")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='blog_posts',
        help_text="The user who authored the post."
    )
    content = models.TextField(help_text="The main content of the post. Can contain HTML.")
    excerpt = models.TextField(blank=True, help_text="A short summary for list views and meta descriptions.")
    featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True, help_text="An optional header image for the post.")
    categories = models.ManyToManyField(Category, related_name="posts", blank=True, help_text="Select one or more categories for this post.")
    tags = models.ManyToManyField(Tag, related_name='posts', blank=True, help_text="Select tags for this post to improve discoverability.")
    
    # Social and engagement features
    allow_comments = models.BooleanField(default=True, help_text="Allow readers to comment on this post.")
    social_image = models.ImageField(upload_to='social_images/', blank=True, null=True, help_text="Custom image for social media sharing. If not provided, featured_image will be used.")
    table_of_contents = models.BooleanField(default=True, help_text="Automatically generate table of contents for this post.")
    
    # Meta fields for display
    read_time = models.PositiveIntegerField(default=5, help_text="Estimated time to read the article in minutes.")
    view_count = models.PositiveIntegerField(default=0, editable=False, help_text="Automatically tracked view count.")
    is_featured = models.BooleanField(default=False, help_text="Mark as featured to display prominently on the blog's main page.")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    meta_data = models.TextField(blank=True, help_text="List of Links")


    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_featured']),
        ]


    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Auto-generate a slug if one is not provided.
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

        if self.content:
            self.read_time = readtime.of_text(strip_tags(self.content)).minutes or 1
        
    def get_reading_time(self):
        """Calculate reading time based on content"""
        if self.content:
            return readtime.of_text(strip_tags(self.content)).minutes or 1
        return self.read_time

# Enhanced model to store email addresses for the newsletter with confirmation workflow
class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True, validators=[EmailValidator()], help_text="Subscriber's email address")
    is_confirmed = models.BooleanField(default=False, help_text="Whether the email subscription has been confirmed")
    confirmation_token = models.CharField(max_length=64, unique=True, blank=True, help_text="Token for email confirmation")
    unsubscribe_token = models.CharField(max_length=64, unique=True, blank=True, help_text="Token for unsubscribing")
    subscribed_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True, help_text="When the subscription was confirmed")
    preferences = models.JSONField(default=dict, blank=True, help_text="Email preferences (frequency, categories, etc.)")

    class Meta:
        ordering = ['-subscribed_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_confirmed']),
            models.Index(fields=['confirmation_token']),
            models.Index(fields=['unsubscribe_token']),
        ]

    def save(self, *args, **kwargs):
        # Generate tokens if they don't exist
        if not self.confirmation_token:
            self.confirmation_token = self._generate_token()
        if not self.unsubscribe_token:
            self.unsubscribe_token = self._generate_token()
        super().save(*args, **kwargs)

    def _generate_token(self):
        """Generate a secure random token"""
        return hashlib.sha256(secrets.token_bytes(32)).hexdigest()

    def __str__(self):
        status = "✓" if self.is_confirmed else "?"
        return f"{self.email} {status}"


# Model for storing and managing blog post comments
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', help_text="The blog post this comment belongs to")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies', help_text="Parent comment for threaded replies")
    author_name = models.CharField(max_length=100, help_text="Name of the comment author")
    author_email = models.EmailField(help_text="Email of the comment author (not displayed publicly)")
    author_website = models.URLField(blank=True, help_text="Optional website URL of the comment author")
    content = models.TextField(help_text="The comment content")
    is_approved = models.BooleanField(default=False, help_text="Whether this comment has been approved for display")
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(help_text="IP address of the commenter for moderation purposes")
    user_agent = models.TextField(blank=True, help_text="Browser user agent for spam detection")

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'is_approved']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_approved']),
        ]

    def __str__(self):
        return f"Comment by {self.author_name} on {self.post.title}"

    def get_replies(self):
        """Get all approved replies to this comment"""
        return self.replies.filter(is_approved=True).order_by('created_at')

    def is_reply(self):
        """Check if this comment is a reply to another comment"""
        return self.parent is not None


# Model for tracking social media shares of blog posts
class SocialShare(models.Model):
    PLATFORM_CHOICES = [
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter'),
        ('linkedin', 'LinkedIn'),
        ('reddit', 'Reddit'),
        ('pinterest', 'Pinterest'),
        ('whatsapp', 'WhatsApp'),
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='social_shares', help_text="The blog post that was shared")
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, help_text="Social media platform where the post was shared")
    share_count = models.PositiveIntegerField(default=0, help_text="Number of times this post has been shared on this platform")
    last_shared = models.DateTimeField(auto_now=True, help_text="When this post was last shared on this platform")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['post', 'platform']
        ordering = ['-share_count']
        indexes = [
            models.Index(fields=['post', 'platform']),
            models.Index(fields=['share_count']),
        ]

    def __str__(self):
        return f"{self.post.title} shared on {self.get_platform_display()} ({self.share_count} times)"

    def increment_share_count(self):
        """Increment the share count for this platform"""
        self.share_count += 1
        self.save(update_fields=['share_count', 'last_shared'])


# Enhanced author profile model for blog authors with bio and social links
class AuthorProfile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='author_profile',
        help_text="The user account associated with this author profile"
    )
    bio = models.TextField(
        max_length=500, 
        blank=True, 
        help_text="Author biography (max 500 characters)"
    )
    website = models.URLField(
        blank=True, 
        help_text="Author's personal or professional website"
    )
    twitter = models.CharField(
        max_length=50, 
        blank=True, 
        help_text="Twitter username (without @)"
    )
    linkedin = models.URLField(
        blank=True, 
        help_text="LinkedIn profile URL"
    )
    github = models.CharField(
        max_length=50, 
        blank=True, 
        help_text="GitHub username"
    )
    instagram = models.CharField(
        max_length=50, 
        blank=True, 
        help_text="Instagram username (without @)"
    )
    profile_picture = models.ImageField(
        upload_to='author_pics/', 
        blank=True, 
        null=True,
        help_text="Author profile picture"
    )
    is_guest_author = models.BooleanField(
        default=False, 
        help_text="Mark as guest author with limited permissions"
    )
    guest_author_email = models.EmailField(
        blank=True,
        help_text="Contact email for guest authors (if different from user email)"
    )
    guest_author_company = models.CharField(
        max_length=100,
        blank=True,
        help_text="Company or organization for guest authors"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this author profile is active and should be displayed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__first_name', 'user__last_name', 'user__username']
        indexes = [
            models.Index(fields=['is_guest_author']),
            models.Index(fields=['is_active']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.get_display_name()} - Author Profile"

    def get_display_name(self):
        """Get the display name for the author"""
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        elif self.user.first_name:
            return self.user.first_name
        else:
            return self.user.username

    def get_short_bio(self, max_length=150):
        """Get a shortened version of the bio"""
        if not self.bio:
            return ""
        if len(self.bio) <= max_length:
            return self.bio
        return self.bio[:max_length].rsplit(' ', 1)[0] + '...'

    def get_social_links(self):
        """Get a dictionary of available social media links"""
        links = {}
        
        if self.website:
            links['website'] = {
                'url': self.website,
                'display': 'Website',
                'icon': 'fas fa-globe'
            }
        
        if self.twitter:
            # Handle both @username and username formats
            username = self.twitter.lstrip('@')
            links['twitter'] = {
                'url': f'https://twitter.com/{username}',
                'display': f'@{username}',
                'icon': 'fab fa-twitter'
            }
        
        if self.linkedin:
            links['linkedin'] = {
                'url': self.linkedin,
                'display': 'LinkedIn',
                'icon': 'fab fa-linkedin'
            }
        
        if self.github:
            links['github'] = {
                'url': f'https://github.com/{self.github}',
                'display': f'@{self.github}',
                'icon': 'fab fa-github'
            }
        
        if self.instagram:
            username = self.instagram.lstrip('@')
            links['instagram'] = {
                'url': f'https://instagram.com/{username}',
                'display': f'@{username}',
                'icon': 'fab fa-instagram'
            }
        
        return links

    def get_post_count(self):
        """Get the number of published posts by this author"""
        return self.user.blog_posts.filter(status='published').count()

    def get_recent_posts(self, limit=5):
        """Get recent published posts by this author"""
        return self.user.blog_posts.filter(status='published').order_by('-created_at')[:limit]

    def get_contact_email(self):
        """Get the appropriate contact email for the author"""
        return self.guest_author_email if self.guest_author_email else self.user.email


# Model for storing multimedia content associated with blog posts
class MediaItem(models.Model):
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('gallery', 'Image Gallery'),
    ]
    
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media_items', help_text="The blog post this media belongs to")
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES, help_text="Type of media content")
    title = models.CharField(max_length=200, blank=True, help_text="Optional title for the media item")
    description = models.TextField(blank=True, help_text="Optional description or caption")
    
    # Image fields
    original_image = models.ImageField(upload_to='blog_images/originals/', blank=True, null=True, help_text="Original uploaded image")
    thumbnail_image = models.ImageField(upload_to='blog_images/thumbnails/', blank=True, null=True, help_text="Thumbnail version")
    medium_image = models.ImageField(upload_to='blog_images/medium/', blank=True, null=True, help_text="Medium size version")
    large_image = models.ImageField(upload_to='blog_images/large/', blank=True, null=True, help_text="Large size version")
    
    # Video fields
    video_url = models.URLField(blank=True, help_text="URL for embedded video (YouTube, Vimeo)")
    video_platform = models.CharField(max_length=20, blank=True, help_text="Video platform (youtube, vimeo)")
    video_id = models.CharField(max_length=50, blank=True, help_text="Platform-specific video ID")
    video_embed_url = models.URLField(blank=True, help_text="Embed URL for the video")
    video_thumbnail = models.URLField(blank=True, help_text="Thumbnail URL for the video")
    
    # Gallery fields
    gallery_images = models.JSONField(default=list, blank=True, help_text="JSON array of gallery image data")
    
    # Metadata
    alt_text = models.CharField(max_length=255, blank=True, help_text="Alt text for accessibility")
    order = models.PositiveIntegerField(default=0, help_text="Display order within the post")
    is_featured = models.BooleanField(default=False, help_text="Use as featured media for the post")
    
    # Technical metadata
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    width = models.PositiveIntegerField(default=0, help_text="Image/video width in pixels")
    height = models.PositiveIntegerField(default=0, help_text="Image/video height in pixels")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['post', 'media_type']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['order']),
        ]

    def __str__(self):
        return f"{self.get_media_type_display()} for {self.post.title}"

    def get_display_image(self):
        """Get the appropriate image for display based on context"""
        if self.media_type == 'image':
            return self.medium_image or self.original_image
        elif self.media_type == 'video':
            return self.video_thumbnail
        return None

    def get_responsive_images(self):
        """Get all available image sizes as a dictionary"""
        images = {}
        if self.original_image:
            images['original'] = {
                'url': self.original_image.url,
                'width': self.width,
                'height': self.height,
            }
        if self.thumbnail_image:
            images['thumbnail'] = {'url': self.thumbnail_image.url}
        if self.medium_image:
            images['medium'] = {'url': self.medium_image.url}
        if self.large_image:
            images['large'] = {'url': self.large_image.url}
        return images

    def get_video_embed_code(self):
        """Generate HTML embed code for videos"""
        if self.media_type != 'video' or not self.video_embed_url:
            return None
        
        return f'''
        <div class="video-embed-container" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden;">
            <iframe src="{self.video_embed_url}" 
                    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" 
                    frameborder="0" 
                    allowfullscreen
                    title="{self.title or 'Embedded Video'}">
            </iframe>
        </div>
        '''

    def save(self, *args, **kwargs):
        # Auto-populate metadata from image if available
        if self.original_image and not self.width:
            try:
                from PIL import Image
                with Image.open(self.original_image.path) as img:
                    self.width = img.width
                    self.height = img.height
                    self.file_size = self.original_image.size
            except Exception:
                pass
        
        super().save(*args, **kwargs)

