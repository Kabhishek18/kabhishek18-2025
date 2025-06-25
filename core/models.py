import os
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError

class TemplateFile(models.Model):
    """
    Represents a single, editable HTML template file that is stored
    both in the database and on the filesystem.
    """
    name = models.CharField(max_length=100, unique=True, help_text="A friendly name for this file (e.g., 'Homepage Hero Section').")
    filename = models.SlugField(max_length=100, unique=True, help_text="The .html file name (e.g., 'hero-section'). Do not include .html.")
    content = models.TextField(blank=True, help_text="The HTML content of the template file.")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_include_path(self):
        """Returns the relative path for use in Django's {% include %} tag."""
        return f"includes/{self.filename}.html"

    def _get_full_filepath(self):
        """Helper to get the absolute physical path of the file."""
        return os.path.join(settings.BASE_DIR, 'templates', self.get_include_path())

    def save(self, *args, **kwargs):
        """
        Overrides the save method to ensure the filename is a slug and that
        the file content is written to the physical file on the server.
        """
        self.filename = slugify(self.filename)
        super().save(*args, **kwargs)

        filepath = self._get_full_filepath()
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.content)
        except IOError as e:
            raise ValidationError(f"Could not write to template file: {filepath}. Error: {e}")

    def delete(self, *args, **kwargs):
        """Overrides the delete method to also delete the physical file."""
        filepath = self._get_full_filepath()
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError as e:
                # Log the error but don't prevent the DB record from being deleted
                print(f"Error deleting file {filepath}: {e}")
        super().delete(*args, **kwargs)

    @classmethod
    def sync_from_filesystem(cls):
        """
        Scans the 'templates/includes/' directory and creates DB records for
        any .html files that don't already exist. This method is idempotent
        and prevents the 'Duplicate entry' error.
        """
        includes_dir = os.path.join(settings.BASE_DIR, 'templates', 'includes')
        if not os.path.isdir(includes_dir):
            return 0  # Directory doesn't exist, nothing to sync

        existing_filenames = set(cls.objects.values_list('filename', flat=True))
        created_count = 0

        for item in os.listdir(includes_dir):
            if item.endswith('.html'):
                file_slug = slugify(os.path.splitext(item)[0])
                
                # THIS IS THE FIX: Skip if a file with this slug already exists in the DB.
                if file_slug in existing_filenames:
                    continue

                try:
                    friendly_name_base = file_slug.replace('-', ' ').replace('_', ' ').title()
                    friendly_name = friendly_name_base
                    
                    # Ensure the friendly name is also unique, append slug if not
                    counter = 2
                    while cls.objects.filter(name=friendly_name).exists():
                        friendly_name = f"{friendly_name_base} ({counter})"
                        counter += 1

                    filepath = os.path.join(includes_dir, item)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    cls.objects.create(name=friendly_name, filename=file_slug, content=content)
                    existing_filenames.add(file_slug) # Add to our set to avoid re-checking DB
                    created_count += 1
                except Exception as e:
                    print(f"Warning: Could not create template for file {item}: {e}")
        
        return created_count


class Template(models.Model):
    """
    A model to group multiple TemplateFile objects into a single, selectable "Template".
    This allows for building complex pages by combining smaller includes.
    """
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


class Page(models.Model):
    """
    Represents a single content page on the website, which can be rendered
    using a selected Template.
    """
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
        help_text="Select a pre-defined template set to render on this page."
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
        # Ensure only one page is marked as the homepage
        if self.is_homepage:
            Page.objects.filter(is_homepage=True).exclude(pk=self.pk).update(is_homepage=False)
        super().save(*args, **kwargs)

