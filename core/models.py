import os
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError

class Component(models.Model):
    """
    Represents a single, editable HTML component that is stored in the database.
    """
    name = models.CharField(max_length=100, unique=True, help_text="A friendly name for this component (e.g., 'Homepage Hero Section').")
    slug = models.SlugField(max_length=200, unique=True, blank=True, help_text="The URL-friendly version of the title. Leave blank to auto-generate.")
    content = models.TextField(blank=True, help_text="The HTML content of the component.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Overrides the save method to ensure the filename is a slug.
        """
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Template(models.Model):
    """
    A model to group multiple TemplateFile objects into a single, selectable "Template".
    This allows for building complex pages by combining smaller includes.
    """
    name = models.CharField(max_length=100, unique=True, help_text="A unique name for this template set (e.g., 'Homepage Layout').")    
    files = models.ManyToManyField(
        Component,
        blank=True,
        help_text="Select the files that make up this template set. They will be included in order."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
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

