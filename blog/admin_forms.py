"""
Custom admin forms for LinkedIn configuration management.
"""
from django import forms
from django.core.exceptions import ValidationError
from django.contrib import messages
from .linkedin_models import LinkedInConfig
from .admin_widgets import HashtagRulesWidget, HashtagBlacklistWidget, HashtagPreviewWidget, CategoryImageOverridesWidget, ImagePostingPreviewWidget
import json
import re


class LinkedInConfigAdminForm(forms.ModelForm):
    """
    Enhanced admin form for LinkedIn configuration with hashtag and image posting support.
    
    This form provides a comprehensive interface for managing LinkedIn integration settings,
    including hashtag generation rules, image posting strategies, and configuration validation.
    
    Features:
    - Secure handling of encrypted credential fields
    - Custom widgets for hashtag rules and blacklist management
    - Image posting strategy configuration with category overrides
    - Real-time preview functionality for testing configurations
    - Comprehensive validation with helpful error messages
    - JSON format validation and formatting assistance
    
    Form Fields:
    - Credential fields: client_secret, access_token, refresh_token (encrypted)
    - Hashtag fields: custom_hashtag_rules, hashtag_blacklist (JSON)
    - Image fields: category_image_overrides (JSON)
    - Preview fields: hashtag_preview, image_posting_preview (display only)
    
    Custom Widgets:
    - HashtagRulesWidget: JSON editor for category-specific hashtag rules
    - HashtagBlacklistWidget: Line-by-line editor for blacklisted terms
    - CategoryImageOverridesWidget: JSON editor for category image settings
    - HashtagPreviewWidget: Preview hashtag generation for existing posts
    - ImagePostingPreviewWidget: Preview image posting decisions
    
    Validation:
    - JSON format validation for all JSON fields
    - Hashtag format validation (LinkedIn compliance)
    - Cross-field validation for configuration consistency
    - Security validation for sensitive credential fields
    
    Usage:
        # In admin.py
        @admin.register(LinkedInConfig)
        class LinkedInConfigAdmin(admin.ModelAdmin):
            form = LinkedInConfigAdminForm
            
        # The form handles all validation and widget rendering automatically
    
    Security Features:
    - Encrypted credential storage with masked display
    - JSON input sanitization and validation
    - Configuration change logging for audit trails
    - Protection against malformed configuration injection
    """
    
    # Sensitive credential fields
    client_secret = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter client secret'}),
        required=False,
        help_text="Leave blank to keep existing value"
    )
    access_token = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter access token'}),
        required=False,
        help_text="Leave blank to keep existing value"
    )
    refresh_token = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter refresh token'}),
        required=False,
        help_text="Leave blank to keep existing value"
    )
    
    # Hashtag configuration fields with custom widgets
    custom_hashtag_rules = forms.CharField(
        widget=HashtagRulesWidget(),
        required=False,
        help_text="Define custom hashtag rules for different categories in JSON format"
    )
    hashtag_blacklist = forms.CharField(
        widget=HashtagBlacklistWidget(),
        required=False,
        help_text="List of words/phrases to exclude from hashtag generation"
    )
    
    # Image posting configuration fields with custom widgets
    category_image_overrides = forms.CharField(
        widget=CategoryImageOverridesWidget(),
        required=False,
        help_text="Override image posting settings for specific categories in JSON format"
    )
    
    # Preview field for image posting decisions (not saved to model)
    image_posting_preview = forms.CharField(
        widget=ImagePostingPreviewWidget(),
        required=False,
        help_text="Preview image posting decisions for existing posts"
    )
    
    # Preview field (not saved to model)
    hashtag_preview = forms.CharField(
        widget=HashtagPreviewWidget(),
        required=False,
        help_text="Preview hashtag generation for existing posts"
    )
    
    class Meta:
        model = LinkedInConfig
        fields = '__all__'
        widgets = {
            'max_hashtags': forms.NumberInput(attrs={
                'min': 0, 
                'max': 30,
                'class': 'vIntegerField'
            }),
            'image_posting_strategy': forms.Select(attrs={
                'class': 'vSelectField'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Don't show actual encrypted values in form
        if self.instance and self.instance.pk:
            self.fields['client_secret'].initial = ''
            self.fields['access_token'].initial = ''
            self.fields['refresh_token'].initial = ''
        
        # Add CSS classes for better styling
        self.fields['enable_hashtags'].widget.attrs.update({'class': 'vCheckboxField'})
        self.fields['enable_image_posting'].widget.attrs.update({'class': 'vCheckboxField'})
        
        # Add help text for hashtag fields
        self.fields['enable_hashtags'].help_text = (
            "Enable automatic hashtag generation for LinkedIn posts. "
            "Hashtags will be generated from post tags, categories, and content."
        )
        self.fields['max_hashtags'].help_text = (
            "Maximum number of hashtags to include in each LinkedIn post. "
            "LinkedIn recommends 3-5 hashtags for optimal reach."
        )
        
        # Set initial values for hashtag fields if they're empty
        if self.instance and self.instance.pk:
            # Convert dict/list to JSON string for display
            if self.instance.custom_hashtag_rules:
                self.fields['custom_hashtag_rules'].initial = json.dumps(self.instance.custom_hashtag_rules, indent=2)
            else:
                self.fields['custom_hashtag_rules'].initial = '{}'
            
            if self.instance.hashtag_blacklist:
                self.fields['hashtag_blacklist'].initial = json.dumps(self.instance.hashtag_blacklist, indent=2)
            else:
                self.fields['hashtag_blacklist'].initial = '[]'
            
            if self.instance.category_image_overrides:
                self.fields['category_image_overrides'].initial = json.dumps(self.instance.category_image_overrides, indent=2)
            else:
                self.fields['category_image_overrides'].initial = '{}'
        else:
            # Set defaults for new instances
            self.fields['custom_hashtag_rules'].initial = '{}'
            self.fields['hashtag_blacklist'].initial = '[]'
            self.fields['category_image_overrides'].initial = '{}'
    
    def clean_max_hashtags(self):
        """Validate max_hashtags field"""
        max_hashtags = self.cleaned_data.get('max_hashtags')
        
        if max_hashtags is not None:
            if max_hashtags < 0:
                raise ValidationError("Maximum hashtags cannot be negative")
            if max_hashtags > 30:
                raise ValidationError("Maximum hashtags cannot exceed 30 (LinkedIn best practices)")
        
        return max_hashtags
    
    def clean_custom_hashtag_rules(self):
        """Validate and clean custom hashtag rules"""
        rules = self.cleaned_data.get('custom_hashtag_rules')
        
        if not rules or rules.strip() == '':
            return {}
        
        # Always expect string input from form
        if isinstance(rules, str):
            rules = rules.strip()
            if rules == '{}' or rules == '':
                return {}
            try:
                rules = json.loads(rules)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON format: {e}")
        
        if not isinstance(rules, dict):
            raise ValidationError("Hashtag rules must be a JSON object")
        
        # Validate each category rule
        for category, rule_config in rules.items():
            if not isinstance(rule_config, dict):
                raise ValidationError(f"Rule for category '{category}' must be an object")
            
            # Validate required_hashtags
            if 'required_hashtags' in rule_config:
                required = rule_config['required_hashtags']
                if not isinstance(required, list):
                    raise ValidationError(f"required_hashtags for '{category}' must be a list")
                
                for hashtag in required:
                    if not self._is_valid_hashtag(hashtag):
                        raise ValidationError(f"Invalid hashtag '{hashtag}' in required_hashtags for '{category}'")
            
            # Validate suggested_hashtags
            if 'suggested_hashtags' in rule_config:
                suggested = rule_config['suggested_hashtags']
                if not isinstance(suggested, list):
                    raise ValidationError(f"suggested_hashtags for '{category}' must be a list")
                
                for hashtag in suggested:
                    if not self._is_valid_hashtag(hashtag):
                        raise ValidationError(f"Invalid hashtag '{hashtag}' in suggested_hashtags for '{category}'")
            
            # Validate max_hashtags
            if 'max_hashtags' in rule_config:
                max_tags = rule_config['max_hashtags']
                if not isinstance(max_tags, int) or max_tags < 0 or max_tags > 30:
                    raise ValidationError(f"max_hashtags for '{category}' must be between 0 and 30")
            
            # Validate priority
            if 'priority' in rule_config:
                priority = rule_config['priority']
                if not isinstance(priority, int) or priority < 1:
                    raise ValidationError(f"priority for '{category}' must be a positive integer")
        
        return rules
    
    def clean_hashtag_blacklist(self):
        """Validate and clean hashtag blacklist"""
        blacklist = self.cleaned_data.get('hashtag_blacklist')
        
        if not blacklist or blacklist.strip() == '':
            return []
        
        # Always expect string input from form
        if isinstance(blacklist, str):
            blacklist = blacklist.strip()
            if blacklist == '[]' or blacklist == '':
                return []
            try:
                blacklist = json.loads(blacklist)
            except json.JSONDecodeError:
                # If it's not JSON, treat as newline-separated list
                blacklist = [line.strip().lower() for line in blacklist.split('\n') if line.strip()]
        
        if not isinstance(blacklist, list):
            raise ValidationError("Hashtag blacklist must be a list")
        
        # Clean and validate blacklist items
        cleaned_blacklist = []
        for item in blacklist:
            if not isinstance(item, str):
                raise ValidationError("All blacklist items must be strings")
            
            cleaned_item = item.strip().lower()
            if cleaned_item and cleaned_item not in cleaned_blacklist:
                # Remove # if present (we'll add it during validation)
                cleaned_item = cleaned_item.lstrip('#')
                if cleaned_item:
                    cleaned_blacklist.append(cleaned_item)
        
        return cleaned_blacklist
    
    def clean_image_posting_strategy(self):
        """Validate image posting strategy"""
        strategy = self.cleaned_data.get('image_posting_strategy')
        valid_strategies = ['always', 'never', 'category_based']
        
        if strategy and strategy not in valid_strategies:
            raise ValidationError(f"Invalid image posting strategy. Must be one of: {', '.join(valid_strategies)}")
        
        return strategy
    
    def clean_category_image_overrides(self):
        """Validate and clean category image overrides"""
        overrides = self.cleaned_data.get('category_image_overrides')
        
        if not overrides or overrides.strip() == '':
            return {}
        
        # Always expect string input from form
        if isinstance(overrides, str):
            overrides = overrides.strip()
            if overrides == '{}' or overrides == '':
                return {}
            try:
                overrides = json.loads(overrides)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON format: {e}")
        
        if not isinstance(overrides, dict):
            raise ValidationError("Category image overrides must be a JSON object")
        
        # Validate each category override
        for category_key, override_config in overrides.items():
            if not isinstance(category_key, str):
                raise ValidationError(f"Category key '{category_key}' must be a string")
            
            if isinstance(override_config, bool):
                # Simple boolean override is valid
                continue
            elif isinstance(override_config, dict):
                # Validate dictionary format
                if 'enable_images' in override_config:
                    enable_images = override_config['enable_images']
                    if not isinstance(enable_images, bool):
                        raise ValidationError(f"enable_images for category '{category_key}' must be a boolean")
                
                # Optional description field
                if 'description' in override_config:
                    description = override_config['description']
                    if not isinstance(description, str):
                        raise ValidationError(f"description for category '{category_key}' must be a string")
            else:
                raise ValidationError(f"Override for category '{category_key}' must be a boolean or object with 'enable_images' field")
        
        return overrides
    
    def clean(self):
        """Perform cross-field validation"""
        cleaned_data = super().clean()
        
        # Validate hashtag configuration consistency
        enable_hashtags = cleaned_data.get('enable_hashtags')
        max_hashtags = cleaned_data.get('max_hashtags')
        
        if enable_hashtags and max_hashtags == 0:
            raise ValidationError(
                "If hashtags are enabled, max_hashtags should be greater than 0"
            )
        
        # Validate image posting configuration consistency
        enable_image_posting = cleaned_data.get('enable_image_posting')
        image_posting_strategy = cleaned_data.get('image_posting_strategy')
        category_image_overrides = cleaned_data.get('category_image_overrides')
        
        if not enable_image_posting and image_posting_strategy != 'never':
            cleaned_data['image_posting_strategy'] = 'never'
        
        # Validate category overrides are only meaningful with category_based strategy
        if category_image_overrides and image_posting_strategy != 'category_based':
            # Issue a warning but don't fail validation
            pass  # Category overrides will be ignored but not removed
        
        return cleaned_data
    
    def _is_valid_hashtag(self, hashtag):
        """
        Validate hashtag format according to LinkedIn standards.
        
        Args:
            hashtag: The hashtag to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(hashtag, str):
            return False
        
        # Remove leading # if present
        tag = hashtag.lstrip('#')
        
        # Check basic requirements
        if not tag:
            return False
        
        # LinkedIn hashtag rules:
        # - Can contain letters, numbers, and underscores
        # - Cannot start with a number
        # - Cannot contain spaces or special characters (except underscore)
        # - Should be between 1 and 100 characters
        if len(tag) > 100:
            return False
        
        # Check pattern: starts with letter or underscore, followed by alphanumeric or underscore
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return bool(re.match(pattern, tag))
    
    def save(self, commit=True):
        """Save the form with proper handling of encrypted fields"""
        instance = super().save(commit=False)
        
        # Only update encrypted fields if new values are provided
        if self.cleaned_data.get('client_secret'):
            instance.set_client_secret(self.cleaned_data['client_secret'])
        
        if self.cleaned_data.get('access_token'):
            instance.set_access_token(self.cleaned_data['access_token'])
        
        if self.cleaned_data.get('refresh_token'):
            instance.set_refresh_token(self.cleaned_data['refresh_token'])
        
        if commit:
            instance.save()
            
            # Log configuration changes
            if self.has_changed():
                changed_fields = ', '.join(self.changed_data)
                instance.log_configuration_change('updated', f'Fields changed: {changed_fields}')
        
        return instance


class HashtagPreviewForm(forms.Form):
    """
    Form for previewing hashtag generation without saving.
    """
    post_id = forms.IntegerField(
        widget=forms.Select(),
        help_text="Select a blog post to preview hashtag generation"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate post choices
        from .models import Post
        posts = Post.objects.filter(status='published').order_by('-created_at')[:50]
        choices = [(post.id, f"{post.title} ({post.created_at.strftime('%Y-%m-%d')})") 
                  for post in posts]
        choices.insert(0, ('', 'Select a post...'))
        
        self.fields['post_id'].widget = forms.Select(choices=choices)