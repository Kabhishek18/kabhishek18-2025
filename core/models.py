import os
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError

# NEW: Model to represent a single, editable template file.
class TemplateFile(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="A friendly name for this file (e.g., 'Homepage Hero Section').")
    filename = models.SlugField(max_length=100, unique=True, help_text="The .html file name (e.g., 'hero-section'). Do not include .html.")
    content = models.TextField(blank=True, help_text="The HTML content of the template file.")
    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_include_path(self):
        """Returns the full path for use in Django's {% include %} tag."""
        return f"includes/{self.filename}.html"
    
    def _get_full_filepath(self):
        """Helper to get the absolute physical path of the file."""
        # Assumes a project-level 'templates' directory configured in settings.py
        return os.path.join(settings.BASE_DIR, 'templates', self.get_include_path())

    def save(self, *args, **kwargs):
        # First, save the model instance to the database
        super().save(*args, **kwargs)

        # Then, write the content to the physical file
        filepath = self._get_full_filepath()
        try:
            # Ensure the 'includes' directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.content)
        except IOError as e:
            # If file writing fails, raise a validation error to show in the admin
            raise ValidationError(f"Could not write to template file: {filepath}. Error: {e}")

    def delete(self, *args, **kwargs):
        """
        Overrides the delete method to also delete the physical file.
        """
        filepath = self._get_full_filepath()
        
        # First, delete the physical file
        if os.path.exists(filepath):
            os.remove(filepath)
            
        # Then, delete the model instance from the database
        super().delete(*args, **kwargs)


class Template(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="A unique name for this template set (e.g., 'Homepage Layout').")    
    files = models.ManyToManyField(
        TemplateFile,
        blank=True,
        help_text="Select the files that make up this template set. They will be included in order."
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# Page model remains largely the same, just linking to the updated Template model.
class Page(models.Model):
    NAVBAR_CHOICES = [
        ('HOME', 'Home Page Navbar'),
        ('BLOG', 'Blog/Detail Page Navbar'),
        ('GENERIC', 'Generic Back-to-Home Navbar'),
    ]
    title = models.CharField(max_length=200, unique=True, help_text="The main title of the page.")
    slug = models.SlugField(max_length=200, unique=True, blank=True, help_text="The URL-friendly version of the title. Leave blank to auto-generate.")
    content = models.TextField(blank=True, help_text="Main content of the page, can include HTML. This is shown if no template is selected.")
    meta_description = models.CharField(max_length=255, blank=True, help_text="Brief description for SEO, used in meta tags.")
    template = models.ForeignKey(
        Template,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Select a pre-defined template set to render on this page. If none is selected, the 'content' field will be displayed."
    )
    is_published = models.BooleanField(default=True, help_text="Uncheck to make this page a draft and hide it from the public.")
    is_homepage = models.BooleanField(default=False, help_text="Set this as the main home page. Only one page can be the homepage.")
    navbar_type = models.CharField(max_length=10, choices=NAVBAR_CHOICES, default='GENERIC', help_text="Select the type of navigation bar to display on this page.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.is_homepage:
            Page.objects.filter(is_homepage=True).exclude(pk=self.pk).update(is_homepage=False)
        super().save(*args, **kwargs)
