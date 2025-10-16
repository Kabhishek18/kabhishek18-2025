"""
Custom admin forms for roadmap app
"""
from django import forms
from django.contrib import admin
from .models import ResumeParserConfig
from .admin_widgets import APIKeyWidget


class ResumeParserConfigForm(forms.ModelForm):
    """
    Custom form for Resume Parser Configuration with enhanced widgets and validation
    """
    
    class Meta:
        model = ResumeParserConfig
        fields = '__all__'
        widgets = {
            'gemini_api_key': APIKeyWidget(attrs={
                'placeholder': 'Enter your Google Gemini API key'
            }),
            'max_file_size_mb': forms.NumberInput(attrs={
                'min': 1,
                'max': 100,
                'step': 1,
                'class': 'vIntegerField'
            }),
            'processing_timeout_seconds': forms.NumberInput(attrs={
                'min': 30,
                'max': 3600,
                'step': 30,
                'class': 'vIntegerField'
            }),
            'temp_file_cleanup_timeout': forms.NumberInput(attrs={
                'min': 60,
                'max': 3600,
                'step': 60,
                'class': 'vIntegerField'
            }),
            'spacy_model': forms.TextInput(attrs={
                'placeholder': 'en_core_web_sm',
                'class': 'vTextField',
                'style': 'width: 200px;'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text for complex fields
        self.fields['gemini_api_key'].help_text = (
            "Your Google Gemini API key. Get one from the Google AI Studio. "
            "Leave blank to disable Gemini backend."
        )
        
        self.fields['max_file_size_mb'].help_text = (
            "Maximum file size allowed for PDF uploads (1-100 MB). "
            "Larger files may cause memory issues."
        )
        
        self.fields['processing_timeout_seconds'].help_text = (
            "Maximum time to wait for resume processing (30-3600 seconds). "
            "Increase for complex resumes or slow backends."
        )
        
        self.fields['temp_file_cleanup_timeout'].help_text = (
            "Time to keep temporary files before cleanup (60-3600 seconds). "
            "Should be longer than processing timeout."
        )
        
        self.fields['spacy_model'].help_text = (
            "spaCy model name to use for NLP processing. "
            "Common options: en_core_web_sm, en_core_web_md, en_core_web_lg"
        )
        
        self.fields['default_backend'].help_text = (
            "Default AI backend to use. 'Auto' tries backends in order: "
            "Gemini → spaCy → Rule-based"
        )
        
        self.fields['enable_fallback_processing'].help_text = (
            "If enabled, system will try alternative backends when the primary fails"
        )
        
        self.fields['enable_confidence_scoring'].help_text = (
            "Include confidence scores in API responses to indicate extraction quality"
        )
    
    def clean_max_file_size_mb(self):
        """Validate file size limit"""
        size = self.cleaned_data.get('max_file_size_mb')
        if size and (size < 1 or size > 100):
            raise forms.ValidationError("File size must be between 1 and 100 MB")
        return size
    
    def clean_processing_timeout_seconds(self):
        """Validate processing timeout"""
        timeout = self.cleaned_data.get('processing_timeout_seconds')
        if timeout and (timeout < 30 or timeout > 3600):
            raise forms.ValidationError("Processing timeout must be between 30 and 3600 seconds")
        return timeout
    
    def clean_temp_file_cleanup_timeout(self):
        """Validate cleanup timeout"""
        cleanup_timeout = self.cleaned_data.get('temp_file_cleanup_timeout')
        processing_timeout = self.cleaned_data.get('processing_timeout_seconds')
        
        if cleanup_timeout and (cleanup_timeout < 60 or cleanup_timeout > 3600):
            raise forms.ValidationError("Cleanup timeout must be between 60 and 3600 seconds")
        
        if cleanup_timeout and processing_timeout and cleanup_timeout < processing_timeout:
            raise forms.ValidationError(
                "Cleanup timeout should be longer than processing timeout to avoid "
                "deleting files during processing"
            )
        
        return cleanup_timeout
    
    def clean_gemini_api_key(self):
        """Validate Gemini API key format"""
        api_key = self.cleaned_data.get('gemini_api_key')
        
        if api_key:
            # Basic validation - Gemini API keys typically start with specific patterns
            if not api_key.strip():
                return None
            
            # Remove whitespace
            api_key = api_key.strip()
            
            # Basic format check (this is a simple check, actual validation happens during usage)
            if len(api_key) < 20:
                raise forms.ValidationError(
                    "API key appears to be too short. Please check your Gemini API key."
                )
        
        return api_key or None
    
    def clean_spacy_model(self):
        """Validate spaCy model name"""
        model = self.cleaned_data.get('spacy_model')
        
        if model:
            model = model.strip()
            
            # Check for common model names
            valid_models = [
                'en_core_web_sm', 'en_core_web_md', 'en_core_web_lg',
                'en', 'en_core_web_trf'
            ]
            
            if model not in valid_models:
                # Don't raise error, just warn in help text
                # The actual validation happens when the model is loaded
                pass
        
        return model