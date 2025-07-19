# models.py - API Models including ScriptRunner and Authentication Models

import uuid
import secrets
import hashlib
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import validate_ipv4_address, validate_ipv6_address
from django.core.exceptions import ValidationError

class ScriptRunner(models.Model):
    EXECUTION_STATUS = [
        ('pending', '⏳ Pending'),
        ('running', '🔄 Running'),
        ('completed', '✅ Completed'),
        ('failed', '❌ Failed'),
        ('timeout', '⏰ Timeout'),
    ]
    
    # Basic fields (you already have these)
    name = models.CharField(max_length=200, default="Script")
    script_code = models.TextField(help_text="Write your Python script here")
    output = models.TextField(blank=True, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(blank=True, null=True)
    
    # NEW ENHANCED FIELDS - Add these to your existing model
    execution_status = models.CharField(
        max_length=20, 
        choices=EXECUTION_STATUS, 
        default='pending',
        help_text="Current execution status"
    )
    
    execution_time = models.FloatField(
        null=True, 
        blank=True, 
        help_text="Execution time in seconds"
    )
    
    execution_count = models.IntegerField(
        default=0,
        help_text="Number of times this script has been executed"
    )
    
    timeout_seconds = models.IntegerField(
        default=30, 
        help_text="Maximum execution time in seconds"
    )
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="User who created this script"
    )
    
    is_favorite = models.BooleanField(
        default=False,
        help_text="Mark as favorite script"
    )
    
    class Meta:
        verbose_name = "Script Runner"
        verbose_name_plural = "Script Runners"
        ordering = ['-executed_at', '-created_at']
    
    def __str__(self):
        status_icon = dict(self.EXECUTION_STATUS).get(self.execution_status, '❓')
        return f"{status_icon} {self.name}"

# OPTIONAL: Add these models if you want categories and templates

class ScriptCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default="📝")
    
    class Meta:
        verbose_name_plural = "Script Categories"
    
    def __str__(self):
        return f"{self.icon} {self.name}"

class ScriptTemplate(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    template_code = models.TextField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"📋 {self.name}"

# API Authentication Models

def validate_ip_list(value):
    """Validate comma-separated list of IP addresses"""
    if not value:
        return
    
    ips = [ip.strip() for ip in value.split(',')]
    for ip in ips:
        try:
            validate_ipv4_address(ip)
        except ValidationError:
            try:
                validate_ipv6_address(ip)
            except ValidationError:
                raise ValidationError(f'Invalid IP address: {ip}')


class APIClient(models.Model):
    """
    Represents an external application that can access the API
    """
    client_id = models.UUIDField(
        unique=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for this client"
    )
    name = models.CharField(
        max_length=200,
        help_text="Friendly name for this API client"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the client application"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this client can access the API"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        help_text="User who created this client"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Permission settings
    can_read_posts = models.BooleanField(
        default=True,
        help_text="Can read blog posts"
    )
    can_write_posts = models.BooleanField(
        default=False,
        help_text="Can create and update blog posts"
    )
    can_delete_posts = models.BooleanField(
        default=False,
        help_text="Can delete blog posts"
    )
    can_manage_categories = models.BooleanField(
        default=False,
        help_text="Can manage blog categories"
    )
    can_access_users = models.BooleanField(
        default=False,
        help_text="Can access user information"
    )
    can_access_pages = models.BooleanField(
        default=True,
        help_text="Can access page content"
    )
    
    # Rate limiting
    requests_per_minute = models.IntegerField(
        default=60,
        help_text="Maximum requests per minute"
    )
    requests_per_hour = models.IntegerField(
        default=1000,
        help_text="Maximum requests per hour"
    )
    
    # IP restrictions
    allowed_ips = models.TextField(
        blank=True,
        validators=[validate_ip_list],
        help_text="Comma-separated list of allowed IP addresses (leave blank for no restriction)"
    )
    
    class Meta:
        verbose_name = "API Client"
        verbose_name_plural = "API Clients"
        ordering = ['name']
    
    def __str__(self):
        status = "🟢" if self.is_active else "🔴"
        return f"{status} {self.name}"
    
    def get_allowed_ip_list(self):
        """Return list of allowed IPs"""
        if not self.allowed_ips:
            return []
        return [ip.strip() for ip in self.allowed_ips.split(',')]


class APIKey(models.Model):
    """
    API keys for client authentication with expiration
    """
    client = models.ForeignKey(
        APIClient, 
        on_delete=models.CASCADE, 
        related_name='api_keys'
    )
    key_hash = models.CharField(
        max_length=128, 
        unique=True,
        help_text="Hashed version of the API key"
    )
    encryption_key = models.CharField(
        max_length=256,
        help_text="Encryption key for secure communications"
    )
    expires_at = models.DateTimeField(
        help_text="When this key expires"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this key is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Last time this key was used"
    )
    usage_count = models.IntegerField(
        default=0,
        help_text="Number of times this key has been used"
    )
    
    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        ordering = ['-created_at']
    
    def __str__(self):
        status = "🟢" if self.is_active and not self.is_expired() else "🔴"
        return f"{status} {self.client.name} - {self.created_at.strftime('%Y-%m-%d')}"
    
    def is_expired(self):
        """Check if the key has expired"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if the key is valid (active and not expired)"""
        return self.is_active and not self.is_expired()
    
    def update_usage(self):
        """Update usage statistics"""
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])
    
    @classmethod
    def generate_key_pair(cls, client, expiration_hours=24):
        """Generate a new API key pair for a client"""
        from .utils import APIKeyGenerator
        
        # Generate key pair using utility
        key_data = APIKeyGenerator.generate_key_pair(expiration_hours)
        
        # Create the APIKey instance
        api_key_instance = cls.objects.create(
            client=client,
            key_hash=key_data['key_hash'],
            encryption_key=key_data['encryption_key'],
            expires_at=key_data['expires_at']
        )
        
        return {
            'api_key': key_data['api_key'],
            'api_key_instance': api_key_instance,
            'expires_at': key_data['expires_at']
        }


class APIUsageLog(models.Model):
    """
    Log of API usage for monitoring and analytics
    """
    client = models.ForeignKey(
        APIClient, 
        on_delete=models.CASCADE,
        related_name='usage_logs'
    )
    api_key = models.ForeignKey(
        APIKey,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    endpoint = models.CharField(
        max_length=200,
        help_text="API endpoint that was accessed"
    )
    method = models.CharField(
        max_length=10,
        help_text="HTTP method used"
    )
    status_code = models.IntegerField(
        help_text="HTTP response status code"
    )
    response_time = models.FloatField(
        help_text="Response time in seconds"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(
        help_text="Client IP address"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Client user agent string"
    )
    request_size = models.IntegerField(
        default=0,
        help_text="Request size in bytes"
    )
    response_size = models.IntegerField(
        default=0,
        help_text="Response size in bytes"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if request failed"
    )
    
    class Meta:
        verbose_name = "API Usage Log"
        verbose_name_plural = "API Usage Logs"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['client', '-timestamp']),
            models.Index(fields=['endpoint', '-timestamp']),
            models.Index(fields=['status_code', '-timestamp']),
        ]
    
    def __str__(self):
        status_emoji = "✅" if 200 <= self.status_code < 300 else "❌"
        return f"{status_emoji} {self.client.name} - {self.method} {self.endpoint} ({self.status_code})"