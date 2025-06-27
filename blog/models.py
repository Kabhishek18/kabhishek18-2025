from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.urls import reverse
from django.utils.html import strip_tags
import readtime


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

# A model to store email addresses for the newsletter.
class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

