from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User

# NEW: A Category model to organize posts.
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories" # Correct pluralization in admin
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Post(models.Model):
    title = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    
    # The main content of the blog post, using Markdown or HTML
    content = models.TextField()
    
    # A short summary for list views
    excerpt = models.CharField(max_length=300, blank=True)
    
    # An optional header image
    featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True)

    # NEW: ManyToManyField for categories, allowing a post to have multiple categories.
    categories = models.ManyToManyField(Category, related_name="posts", blank=True)
    
    # NEW: Fields for meta-information seen in blog-detail.html
    read_time = models.PositiveIntegerField(default=5, help_text="Estimated time to read the article in minutes.")
    view_count = models.PositiveIntegerField(default=0, editable=False) # Not editable in admin

    # NEW: Field to mark a post as "featured" on the main blog page.
    is_featured = models.BooleanField(default=False, help_text="Mark this post as featured to display it prominently.")

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Auto-generate a slug if one is not provided
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
