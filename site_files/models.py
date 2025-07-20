from django.db import models
from django.utils import timezone

class SiteFilesConfig(models.Model):
    """
    Configuration settings for the Site Files Updater.
    This model will store settings for the site files updater, including
    file paths, update frequency, and other configuration options.
    """
    # Site information
    site_name = models.CharField(max_length=255, default='My Site', 
                                help_text="Name of the website")
    site_url = models.URLField(default='https://example.com', 
                              help_text="Base URL of the website (e.g., https://example.com)")
    
    # File paths
    sitemap_path = models.CharField(max_length=255, default='static/Sitemap.xml', 
                                   help_text="Path to the sitemap file relative to the project root")
    robots_path = models.CharField(max_length=255, default='static/robots.txt', 
                                  help_text="Path to the robots.txt file relative to the project root")
    security_path = models.CharField(max_length=255, default='static/security.txt', 
                                    help_text="Path to the security.txt file relative to the project root")
    llms_path = models.CharField(max_length=255, default='static/humans.txt', 
                               help_text="Path to the LLMs.txt file relative to the project root")
    
    # Schedule settings
    update_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        default='daily',
        help_text="How often the site files should be updated"
    )
    
    # Feature flags
    update_sitemap = models.BooleanField(default=True, 
                                        help_text="Enable automatic sitemap updates")
    update_robots = models.BooleanField(default=True, 
                                       help_text="Enable automatic robots.txt updates")
    update_security = models.BooleanField(default=True, 
                                         help_text="Enable automatic security.txt updates")
    update_llms = models.BooleanField(default=True, 
                                     help_text="Enable automatic LLMs.txt updates")
    
    # Timestamps
    last_update = models.DateTimeField(null=True, blank=True, 
                                      help_text="When the site files were last updated")
    created_at = models.DateTimeField(auto_now_add=True, 
                                     help_text="When this configuration was created")
    updated_at = models.DateTimeField(auto_now=True, 
                                     help_text="When this configuration was last modified")
    
    def __str__(self):
        return f"Site Files Configuration: {self.site_name}"
    
    def save(self, *args, **kwargs):
        # Ensure there's only one configuration instance
        if not self.pk and SiteFilesConfig.objects.exists():
            # If trying to create a second instance, update the existing one instead
            existing = SiteFilesConfig.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Site Files Configuration'
        verbose_name_plural = 'Site Files Configuration'
