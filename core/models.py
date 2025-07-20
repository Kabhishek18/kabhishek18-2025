import os
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User

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


class HealthMetric(models.Model):
    """
    Model for storing health check metrics and historical data.
    """
    HEALTH_STATUS_CHOICES = [
        ('healthy', '🟢 Healthy'),
        ('warning', '🟡 Warning'),
        ('critical', '🔴 Critical'),
    ]
    
    METRIC_TYPE_CHOICES = [
        ('database', 'Database'),
        ('cache', 'Cache'),
        ('memory', 'Memory'),
        ('disk', 'Disk'),
        ('system_load', 'System Load'),
        ('logs', 'Logs'),
        ('api', 'API'),
        ('celery', 'Celery'),
        ('redis', 'Redis'),
        ('overall', 'Overall System'),
    ]
    
    metric_name = models.CharField(
        max_length=50,
        choices=METRIC_TYPE_CHOICES,
        help_text="Type of health metric"
    )
    metric_value = models.JSONField(
        help_text="Detailed metric data in JSON format"
    )
    status = models.CharField(
        max_length=20,
        choices=HEALTH_STATUS_CHOICES,
        help_text="Health status of this metric"
    )
    message = models.TextField(
        help_text="Human-readable status message"
    )
    response_time = models.FloatField(
        null=True,
        blank=True,
        help_text="Response time in milliseconds"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When this metric was recorded"
    )
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Health Metric"
        verbose_name_plural = "Health Metrics"
        indexes = [
            models.Index(fields=['metric_name', '-timestamp']),
            models.Index(fields=['status', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        status_icon = dict(self.HEALTH_STATUS_CHOICES).get(self.status, '❓')
        return f"{status_icon} {self.get_metric_name_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    @classmethod
    def record_metric(cls, metric_name, metric_value, status, message, response_time=None):
        """
        Convenience method to record a health metric.
        """
        return cls.objects.create(
            metric_name=metric_name,
            metric_value=metric_value,
            status=status,
            message=message,
            response_time=response_time
        )
    
    @classmethod
    def get_latest_metrics(cls, limit=100):
        """
        Get the latest health metrics for all types.
        """
        return cls.objects.select_related().order_by('-timestamp')[:limit]
    
    @classmethod
    def get_metrics_by_type(cls, metric_name, hours=24):
        """
        Get metrics for a specific type within the last N hours.
        """
        since = timezone.now() - timezone.timedelta(hours=hours)
        return cls.objects.filter(
            metric_name=metric_name,
            timestamp__gte=since
        ).order_by('-timestamp')
    
    @classmethod
    def get_critical_metrics(cls, hours=24):
        """
        Get all critical metrics within the last N hours.
        """
        since = timezone.now() - timezone.timedelta(hours=hours)
        return cls.objects.filter(
            status='critical',
            timestamp__gte=since
        ).order_by('-timestamp')
    
    def is_recent(self, minutes=30):
        """
        Check if this metric was recorded within the last N minutes.
        """
        cutoff = timezone.now() - timezone.timedelta(minutes=minutes)
        return self.timestamp >= cutoff


class SystemAlert(models.Model):
    """
    Model for managing system alerts and notifications.
    """
    ALERT_TYPE_CHOICES = [
        ('health_check', 'Health Check Alert'),
        ('performance', 'Performance Alert'),
        ('resource', 'Resource Alert'),
        ('security', 'Security Alert'),
        ('maintenance', 'Maintenance Alert'),
        ('custom', 'Custom Alert'),
    ]
    
    SEVERITY_CHOICES = [
        ('info', '🔵 Info'),
        ('warning', '🟡 Warning'),
        ('critical', '🔴 Critical'),
        ('emergency', '🚨 Emergency'),
    ]
    
    alert_type = models.CharField(
        max_length=50,
        choices=ALERT_TYPE_CHOICES,
        help_text="Type of alert"
    )
    title = models.CharField(
        max_length=200,
        help_text="Alert title"
    )
    message = models.TextField(
        help_text="Detailed alert message"
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        help_text="Alert severity level"
    )
    source_metric = models.CharField(
        max_length=50,
        blank=True,
        help_text="Source health metric that triggered this alert"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional alert metadata"
    )
    resolved = models.BooleanField(
        default=False,
        help_text="Whether this alert has been resolved"
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts',
        help_text="User who resolved this alert"
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this alert was resolved"
    )
    resolution_notes = models.TextField(
        blank=True,
        help_text="Notes about how this alert was resolved"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this alert was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this alert was last updated"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "System Alert"
        verbose_name_plural = "System Alerts"
        indexes = [
            models.Index(fields=['alert_type', '-created_at']),
            models.Index(fields=['severity', '-created_at']),
            models.Index(fields=['resolved', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        severity_icon = dict(self.SEVERITY_CHOICES).get(self.severity, '❓')
        status = "✅" if self.resolved else "🔄"
        return f"{severity_icon} {status} {self.title}"
    
    def resolve(self, user=None, notes=""):
        """
        Mark this alert as resolved.
        """
        self.resolved = True
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        self.save(update_fields=['resolved', 'resolved_by', 'resolved_at', 'resolution_notes', 'updated_at'])
    
    def reopen(self):
        """
        Reopen a resolved alert.
        """
        self.resolved = False
        self.resolved_by = None
        self.resolved_at = None
        self.resolution_notes = ""
        self.save(update_fields=['resolved', 'resolved_by', 'resolved_at', 'resolution_notes', 'updated_at'])
    
    @classmethod
    def create_alert(cls, alert_type, title, message, severity, source_metric=None, metadata=None):
        """
        Convenience method to create a new alert.
        """
        return cls.objects.create(
            alert_type=alert_type,
            title=title,
            message=message,
            severity=severity,
            source_metric=source_metric or '',
            metadata=metadata or {}
        )
    
    @classmethod
    def get_active_alerts(cls):
        """
        Get all unresolved alerts.
        """
        return cls.objects.filter(resolved=False).order_by('-created_at')
    
    @classmethod
    def get_critical_alerts(cls):
        """
        Get all unresolved critical and emergency alerts.
        """
        return cls.objects.filter(
            resolved=False,
            severity__in=['critical', 'emergency']
        ).order_by('-created_at')
    
    @classmethod
    def get_recent_alerts(cls, hours=24):
        """
        Get alerts from the last N hours.
        """
        since = timezone.now() - timezone.timedelta(hours=hours)
        return cls.objects.filter(created_at__gte=since).order_by('-created_at')
    
    def get_age(self):
        """
        Get the age of this alert as a timedelta.
        """
        return timezone.now() - self.created_at
    
    def is_stale(self, hours=24):
        """
        Check if this alert is older than N hours.
        """
        return self.get_age() > timezone.timedelta(hours=hours)
