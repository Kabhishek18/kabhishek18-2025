"""
Models for the roadmap app (Resume Parser)
"""
import os
from django.db import models


class ResumeParserConfig(models.Model):
    """
    Single configuration instance for the resume parser system.
    Stores API keys, file size limits, and backend preferences.
    """
    BACKEND_CHOICES = [
        ('auto', 'Auto (Gemini -> spaCy -> Rule-based)'),
        ('gemini', 'Gemini AI'),
        ('spacy', 'spaCy NLP'),
        ('rule_based', 'Rule-based'),
    ]
    
    # API Configuration
    gemini_api_key = models.CharField(
        max_length=255, 
        blank=True,
        null=True,
        help_text="Google Gemini API key for AI processing"
    )
    
    # File Processing Configuration
    max_file_size_mb = models.IntegerField(
        default=10,
        help_text="Maximum file size allowed for upload (in MB)"
    )
    
    # Backend Configuration
    default_backend = models.CharField(
        max_length=20,
        choices=BACKEND_CHOICES,
        default='auto',
        help_text="Default AI backend to use for processing"
    )
    
    spacy_model = models.CharField(
        max_length=50,
        default='en_core_web_sm',
        help_text="spaCy model to use for NLP processing"
    )
    
    # Processing Configuration
    processing_timeout_seconds = models.IntegerField(
        default=300,
        help_text="Timeout for resume processing in seconds"
    )
    
    temp_file_cleanup_timeout = models.IntegerField(
        default=300,
        help_text="Timeout for temporary file cleanup in seconds"
    )
    
    # System Configuration
    enable_fallback_processing = models.BooleanField(
        default=True,
        help_text="Enable fallback to other backends if primary fails"
    )
    
    enable_confidence_scoring = models.BooleanField(
        default=True,
        help_text="Enable confidence scoring for extracted data"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Resume Parser Configuration"
        verbose_name_plural = "Resume Parser Configurations"
    
    def __str__(self):
        return f"Resume Parser Config - {self.default_backend} backend"
    
    def save(self, *args, **kwargs):
        """Ensure only one configuration instance exists"""
        if not self.pk and ResumeParserConfig.objects.exists():
            # If this is a new instance and one already exists, update the existing one
            existing = ResumeParserConfig.objects.first()
            existing.gemini_api_key = self.gemini_api_key
            existing.max_file_size_mb = self.max_file_size_mb
            existing.default_backend = self.default_backend
            existing.spacy_model = self.spacy_model
            existing.processing_timeout_seconds = self.processing_timeout_seconds
            existing.temp_file_cleanup_timeout = self.temp_file_cleanup_timeout
            existing.enable_fallback_processing = self.enable_fallback_processing
            existing.enable_confidence_scoring = self.enable_confidence_scoring
            existing.save()
            return existing
        return super().save(*args, **kwargs)
    
    def get_effective_gemini_api_key(self):
        """Get the Gemini API key, falling back to environment variable if not set"""
        if self.gemini_api_key:
            return self.gemini_api_key
        return os.getenv('GEMINI_API_KEY', '')
    
    @classmethod
    def get_config(cls):
        """Get the single configuration instance, create if doesn't exist"""
        config, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'max_file_size_mb': 10,
                'default_backend': 'auto',
                'spacy_model': 'en_core_web_sm',
                'processing_timeout_seconds': 300,
                'temp_file_cleanup_timeout': 300,
                'enable_fallback_processing': True,
                'enable_confidence_scoring': True,
            }
        )
        return config
