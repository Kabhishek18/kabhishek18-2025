# models.py - ADD THESE FIELDS TO YOUR EXISTING ScriptRunner MODEL

from django.db import models
from django.contrib.auth.models import User

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