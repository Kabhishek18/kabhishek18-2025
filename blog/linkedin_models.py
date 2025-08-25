from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
import logging
import time
from .utils.encryption import credential_encryption

logger = logging.getLogger(__name__)


class LinkedInConfig(models.Model):
    """
    Model for storing LinkedIn API credentials securely.
    Only one active configuration should exist at a time.
    """
    client_id = models.CharField(
        max_length=100,
        help_text="LinkedIn API Client ID"
    )
    client_secret = models.TextField(
        help_text="LinkedIn API Client Secret (encrypted)"
    )
    access_token = models.TextField(
        blank=True,
        help_text="LinkedIn API Access Token (encrypted)"
    )
    refresh_token = models.TextField(
        blank=True,
        help_text="LinkedIn API Refresh Token (encrypted)"
    )
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the access token expires"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this LinkedIn integration is active"
    )
    
    # Hashtag Configuration
    enable_hashtags = models.BooleanField(
        default=True,
        help_text="Enable automatic hashtag generation for LinkedIn posts"
    )
    max_hashtags = models.PositiveIntegerField(
        default=5,
        help_text="Maximum number of hashtags per LinkedIn post"
    )
    custom_hashtag_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom hashtag rules per category (JSON format)"
    )
    hashtag_blacklist = models.JSONField(
        default=list,
        blank=True,
        help_text="Words to exclude from hashtag generation (JSON array)"
    )
    
    # Image Posting Configuration
    enable_image_posting = models.BooleanField(
        default=True,
        help_text="Include images in LinkedIn posts when available"
    )
    image_posting_strategy = models.CharField(
        max_length=20,
        choices=[
            ('always', 'Always include images when available'),
            ('never', 'Never include images (text-only posts)'),
            ('category_based', 'Based on post category settings')
        ],
        default='always',
        help_text="Strategy for including images in LinkedIn posts"
    )
    category_image_overrides = models.JSONField(
        default=dict,
        blank=True,
        help_text="Category-specific image posting overrides (JSON format)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "LinkedIn Configuration"
        verbose_name_plural = "LinkedIn Configurations"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"LinkedIn Config ({status}) - {self.client_id[:10]}..."

    def clean(self):
        """Validate the configuration before saving"""
        # Ensure only one active configuration exists
        if self.is_active:
            existing_active = LinkedInConfig.objects.filter(is_active=True)
            if self.pk:
                existing_active = existing_active.exclude(pk=self.pk)
            if existing_active.exists():
                raise ValidationError("Only one active LinkedIn configuration is allowed.")
        
        # Validate client ID
        self._validate_client_id()
        
        # Validate token expiration
        self._validate_token_expiration()
        
        # Validate hashtag configuration
        self._validate_hashtag_config()
        
        # Validate image posting configuration
        self._validate_image_posting_config()
        
        # Validate that we have required credentials for active configs
        if self.is_active:
            if not self.client_id:
                raise ValidationError("Active configuration must have a client ID")
            
            if not self.client_secret:
                raise ValidationError("Active configuration must have a client secret")
            
            # Check if we have access token for active configs
            if not self.access_token:
                logger.warning("Active LinkedIn configuration has no access token - authentication required")

    def save(self, *args, **kwargs):
        # Track if this is a new instance or update
        is_new = self.pk is None
        old_values = {}
        
        # Get old values for comparison if updating
        if not is_new:
            try:
                old_instance = LinkedInConfig.objects.get(pk=self.pk)
                old_values = {
                    'enable_hashtags': old_instance.enable_hashtags,
                    'max_hashtags': old_instance.max_hashtags,
                    'enable_image_posting': old_instance.enable_image_posting,
                    'image_posting_strategy': old_instance.image_posting_strategy,
                    'is_active': old_instance.is_active
                }
            except LinkedInConfig.DoesNotExist:
                pass
        
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Log configuration changes
        try:
            new_values = {
                'enable_hashtags': self.enable_hashtags,
                'max_hashtags': self.max_hashtags,
                'enable_image_posting': self.enable_image_posting,
                'image_posting_strategy': self.image_posting_strategy,
                'is_active': self.is_active
            }
            
            if is_new:
                self.log_configuration_change('created')
                # Import here to avoid circular import
                try:
                    from .services.linkedin_metrics_logger import linkedin_metrics_logger
                    linkedin_metrics_logger.log_configuration_change(
                        self.id, 'created', None, new_values
                    )
                except ImportError:
                    logger.warning("Could not import linkedin_metrics_logger for configuration logging")
            else:
                # Check if significant values changed
                significant_changes = []
                for key, new_value in new_values.items():
                    old_value = old_values.get(key)
                    if old_value != new_value:
                        significant_changes.append(key)
                
                if significant_changes:
                    self.log_configuration_change('updated', f"Changed: {', '.join(significant_changes)}")
                    # Import here to avoid circular import
                    try:
                        from .services.linkedin_metrics_logger import linkedin_metrics_logger
                        linkedin_metrics_logger.log_configuration_change(
                            self.id, 'updated', old_values, new_values
                        )
                    except ImportError:
                        logger.warning("Could not import linkedin_metrics_logger for configuration logging")
        except Exception as e:
            logger.error(f"Error logging configuration change: {e}")

    def _validate_client_id(self):
        """Validate LinkedIn client ID format"""
        if not self.client_id:
            raise ValidationError("Client ID is required")
        
        if len(self.client_id) < 10:
            raise ValidationError("Client ID appears to be too short")
        
        # LinkedIn client IDs are typically alphanumeric
        if not self.client_id.replace('-', '').replace('_', '').isalnum():
            raise ValidationError("Client ID contains invalid characters")

    def _validate_token_expiration(self):
        """Validate token expiration date"""
        if self.token_expires_at and self.token_expires_at <= timezone.now():
            logger.warning(f"LinkedIn token for config {self.id} has expired")
    
    def _validate_hashtag_config(self):
        """Validate hashtag configuration fields with comprehensive logging"""
        config_issues = []
        
        # Validate max_hashtags is reasonable
        if self.max_hashtags is not None:
            if not isinstance(self.max_hashtags, int):
                config_issues.append(f"max_hashtags must be an integer, got {type(self.max_hashtags)}")
                raise ValidationError("Maximum hashtags must be an integer")
            elif self.max_hashtags < 0:
                config_issues.append(f"max_hashtags is negative: {self.max_hashtags}")
                raise ValidationError("Maximum hashtags must be between 0 and 30")
            elif self.max_hashtags > 30:
                config_issues.append(f"max_hashtags too high: {self.max_hashtags} (LinkedIn recommends ≤5)")
                logger.warning(f"LinkedIn config {self.id}: max_hashtags set to {self.max_hashtags}, which is higher than LinkedIn's recommended limit of 5")
                raise ValidationError("Maximum hashtags must be between 0 and 30")
            elif self.max_hashtags == 0:
                logger.warning(f"LinkedIn config {self.id}: max_hashtags set to 0 - no hashtags will be generated")
        
        # Validate custom_hashtag_rules is a dictionary
        if self.custom_hashtag_rules is not None:
            if not isinstance(self.custom_hashtag_rules, dict):
                config_issues.append(f"custom_hashtag_rules must be a dictionary, got {type(self.custom_hashtag_rules)}")
                raise ValidationError("Custom hashtag rules must be a valid JSON object")
            else:
                # Validate the structure of custom rules
                try:
                    for category, rules in self.custom_hashtag_rules.items():
                        if not isinstance(category, str):
                            config_issues.append(f"Category key must be string: {category}")
                        if rules is not None and not isinstance(rules, (dict, list)):
                            config_issues.append(f"Rules for category '{category}' must be dict or list, got {type(rules)}")
                except Exception as e:
                    config_issues.append(f"Error validating custom hashtag rules: {e}")
                    logger.error(f"LinkedIn config {self.id}: Error validating custom hashtag rules: {e}")
        
        # Validate hashtag_blacklist is a list
        if self.hashtag_blacklist is not None:
            if not isinstance(self.hashtag_blacklist, list):
                config_issues.append(f"hashtag_blacklist must be a list, got {type(self.hashtag_blacklist)}")
                raise ValidationError("Hashtag blacklist must be a valid JSON array")
            else:
                # Validate blacklist items
                try:
                    for i, item in enumerate(self.hashtag_blacklist):
                        if not isinstance(item, str):
                            config_issues.append(f"Blacklist item {i} must be string, got {type(item)}")
                    
                    if len(self.hashtag_blacklist) > 100:
                        logger.warning(f"LinkedIn config {self.id}: hashtag_blacklist is very large ({len(self.hashtag_blacklist)} items)")
                        
                except Exception as e:
                    config_issues.append(f"Error validating hashtag blacklist: {e}")
                    logger.error(f"LinkedIn config {self.id}: Error validating hashtag blacklist: {e}")
        
        # Log configuration issues if any
        if config_issues:
            logger.warning(f"LinkedIn config {self.id} hashtag configuration issues: {config_issues}")
    
    def _validate_image_posting_config(self):
        """Validate image posting configuration fields with comprehensive logging"""
        config_issues = []
        
        # Validate image_posting_strategy is one of the allowed choices
        valid_strategies = ['always', 'never', 'category_based']
        if self.image_posting_strategy:
            if self.image_posting_strategy not in valid_strategies:
                config_issues.append(f"Invalid image posting strategy: {self.image_posting_strategy}")
                logger.error(f"LinkedIn config {self.id}: Invalid image posting strategy '{self.image_posting_strategy}', must be one of: {valid_strategies}")
                raise ValidationError(f"Image posting strategy must be one of: {', '.join(valid_strategies)}")
            else:
                logger.debug(f"LinkedIn config {self.id}: Image posting strategy set to '{self.image_posting_strategy}'")
        
        # Validate category_image_overrides is a dictionary
        if self.category_image_overrides is not None:
            if not isinstance(self.category_image_overrides, dict):
                config_issues.append(f"category_image_overrides must be a dictionary, got {type(self.category_image_overrides)}")
                raise ValidationError("Category image overrides must be a valid JSON object")
            else:
                # Validate the structure of category overrides
                try:
                    for category, override in self.category_image_overrides.items():
                        if not isinstance(category, str):
                            config_issues.append(f"Category key must be string: {category}")
                        
                        if override is not None:
                            if isinstance(override, bool):
                                # Simple boolean override is valid
                                pass
                            elif isinstance(override, dict):
                                # Dictionary override should have valid keys
                                valid_keys = ['enable_images', 'strategy', 'description']
                                for key in override.keys():
                                    if key not in valid_keys:
                                        config_issues.append(f"Invalid key '{key}' in category '{category}' override")
                                
                                # Validate enable_images if present
                                if 'enable_images' in override and not isinstance(override['enable_images'], bool):
                                    config_issues.append(f"enable_images for category '{category}' must be boolean")
                            else:
                                config_issues.append(f"Override for category '{category}' must be boolean or dict, got {type(override)}")
                    
                    logger.debug(f"LinkedIn config {self.id}: Category image overrides configured for {len(self.category_image_overrides)} categories")
                    
                except Exception as e:
                    config_issues.append(f"Error validating category image overrides: {e}")
                    logger.error(f"LinkedIn config {self.id}: Error validating category image overrides: {e}")
        
        # Log configuration issues if any
        if config_issues:
            logger.warning(f"LinkedIn config {self.id} image posting configuration issues: {config_issues}")
        
        # Log configuration summary for monitoring
        if self.enable_image_posting:
            logger.info(f"LinkedIn config {self.id}: Image posting enabled with strategy '{self.image_posting_strategy}'")
            if self.category_image_overrides:
                override_count = len(self.category_image_overrides)
                logger.debug(f"LinkedIn config {self.id}: {override_count} category-specific image overrides configured")
        else:
            logger.info(f"LinkedIn config {self.id}: Image posting globally disabled")

    def _encrypt_field(self, value):
        """Encrypt a field value using the credential encryption utility"""
        if not value:
            return value
        
        try:
            return credential_encryption.encrypt(value)
        except Exception as e:
            logger.error(f"Failed to encrypt field: {e}")
            raise ValidationError(f"Failed to encrypt sensitive data: {e}")

    def _decrypt_field(self, encrypted_value):
        """Decrypt a field value using the credential encryption utility"""
        if not encrypted_value:
            return encrypted_value
        
        try:
            return credential_encryption.decrypt(encrypted_value)
        except Exception as e:
            logger.error(f"Failed to decrypt field: {e}")
            return None

    def set_client_secret(self, value):
        """Set encrypted client secret"""
        self.client_secret = self._encrypt_field(value)

    def get_client_secret(self):
        """Get decrypted client secret"""
        return self._decrypt_field(self.client_secret)

    def set_access_token(self, value):
        """Set encrypted access token"""
        self.access_token = self._encrypt_field(value)

    def get_access_token(self):
        """Get decrypted access token"""
        return self._decrypt_field(self.access_token)

    def set_refresh_token(self, value):
        """Set encrypted refresh token"""
        self.refresh_token = self._encrypt_field(value)

    def get_refresh_token(self):
        """Get decrypted refresh token"""
        return self._decrypt_field(self.refresh_token)

    @classmethod
    def get_active_config(cls):
        """Get the active LinkedIn configuration"""
        try:
            return cls.objects.get(is_active=True)
        except cls.DoesNotExist:
            return None

    def is_token_expired(self):
        """Check if the access token is expired"""
        if not self.token_expires_at:
            return True
        
        from django.utils import timezone
        return timezone.now() >= self.token_expires_at

    def has_valid_credentials(self):
        """Check if the configuration has valid credentials"""
        return (
            self.client_id and 
            self.get_client_secret() and 
            self.get_access_token() and 
            not self.is_token_expired()
        )
    
    def needs_token_refresh(self, buffer_minutes=30):
        """
        Check if token needs refresh (expires within buffer time).
        
        Args:
            buffer_minutes: Minutes before expiration to consider refresh needed
            
        Returns:
            bool: True if token needs refresh
        """
        if not self.token_expires_at:
            return True
        
        buffer_time = timezone.now() + timedelta(minutes=buffer_minutes)
        return self.token_expires_at <= buffer_time
    
    def update_tokens(self, access_token, refresh_token=None, expires_in=None):
        """
        Update access and refresh tokens with expiration.
        
        Args:
            access_token: New access token
            refresh_token: New refresh token (optional)
            expires_in: Token lifetime in seconds (optional)
        """
        self.set_access_token(access_token)
        
        if refresh_token:
            self.set_refresh_token(refresh_token)
        
        if expires_in:
            # Set expiration time with a small buffer
            self.token_expires_at = timezone.now() + timedelta(seconds=expires_in - 300)  # 5 minute buffer
        
        self.save(update_fields=['access_token', 'refresh_token', 'token_expires_at'])
        logger.info(f"Updated tokens for LinkedIn config {self.id}")
    
    def clear_tokens(self):
        """Clear all tokens (for security or re-authentication)"""
        self.access_token = ''
        self.refresh_token = ''
        self.token_expires_at = None
        self.save(update_fields=['access_token', 'refresh_token', 'token_expires_at'])
        logger.info(f"Cleared tokens for LinkedIn config {self.id}")
    
    def get_credential_status(self):
        """
        Get detailed status of credentials for admin display.
        
        Returns:
            dict: Status information
        """
        status = {
            'has_client_id': bool(self.client_id),
            'has_client_secret': bool(self.get_client_secret()),
            'has_access_token': bool(self.get_access_token()),
            'has_refresh_token': bool(self.get_refresh_token()),
            'token_expired': self.is_token_expired(),
            'needs_refresh': self.needs_token_refresh(),
            'is_valid': self.has_valid_credentials(),
        }
        
        if self.token_expires_at:
            status['expires_at'] = self.token_expires_at
            status['expires_in_hours'] = (self.token_expires_at - timezone.now()).total_seconds() / 3600
        
        return status
    
    def validate_credentials(self):
        """
        Validate that credentials are properly encrypted and accessible with comprehensive logging.
        
        Returns:
            dict: Validation results
        """
        results = {
            'client_secret_valid': False,
            'access_token_valid': False,
            'refresh_token_valid': False,
            'errors': []
        }
        
        logger.info(f"Validating LinkedIn credentials for config {self.id}")
        
        # Test client secret
        if self.client_secret:
            try:
                decrypted_secret = self.get_client_secret()
                if decrypted_secret:
                    results['client_secret_valid'] = True
                    logger.debug("LinkedIn client secret validation successful")
                else:
                    error_msg = "Client secret cannot be decrypted"
                    results['errors'].append(error_msg)
                    logger.error(f"LinkedIn credential validation error: {error_msg}")
            except Exception as e:
                error_msg = f"Client secret decryption failed: {e}"
                results['errors'].append(error_msg)
                logger.error(f"LinkedIn credential validation error: {error_msg}")
        else:
            logger.warning("LinkedIn client secret is empty")
        
        # Test access token
        if self.access_token:
            try:
                decrypted_token = self.get_access_token()
                if decrypted_token:
                    results['access_token_valid'] = True
                    logger.debug("LinkedIn access token validation successful")
                else:
                    error_msg = "Access token cannot be decrypted"
                    results['errors'].append(error_msg)
                    logger.error(f"LinkedIn credential validation error: {error_msg}")
            except Exception as e:
                error_msg = f"Access token decryption failed: {e}"
                results['errors'].append(error_msg)
                logger.error(f"LinkedIn credential validation error: {error_msg}")
        else:
            logger.warning("LinkedIn access token is empty")
        
        # Test refresh token
        if self.refresh_token:
            try:
                decrypted_refresh = self.get_refresh_token()
                if decrypted_refresh:
                    results['refresh_token_valid'] = True
                    logger.debug("LinkedIn refresh token validation successful")
                else:
                    error_msg = "Refresh token cannot be decrypted"
                    results['errors'].append(error_msg)
                    logger.error(f"LinkedIn credential validation error: {error_msg}")
            except Exception as e:
                error_msg = f"Refresh token decryption failed: {e}"
                results['errors'].append(error_msg)
                logger.error(f"LinkedIn credential validation error: {error_msg}")
        else:
            logger.debug("LinkedIn refresh token is empty (optional)")
        
        # Log overall validation result
        if results['errors']:
            logger.error(f"LinkedIn credential validation failed with {len(results['errors'])} errors: {results['errors']}")
        else:
            logger.info("LinkedIn credential validation completed successfully")
        
        return results
    
    def log_configuration_change(self, change_type: str, details: str = None):
        """
        Log configuration changes for audit purposes.
        
        Args:
            change_type: Type of change (created, updated, activated, deactivated, etc.)
            details: Additional details about the change
        """
        log_message = f"LinkedIn configuration {change_type} for config {self.id}"
        if details:
            log_message += f": {details}"
        
        if change_type in ['created', 'activated']:
            logger.info(log_message)
        elif change_type in ['deactivated', 'token_cleared']:
            logger.warning(log_message)
        elif change_type in ['deleted', 'credential_error']:
            logger.error(log_message)
        else:
            logger.debug(log_message)
    
    def get_hashtag_config(self):
        """
        Get hashtag configuration as a dictionary.
        
        This method returns the complete hashtag configuration for use by the
        HashtagGenerator class. It includes all hashtag-related settings with
        proper defaults and validation.
        
        Returns:
            dict: Hashtag configuration settings containing:
                - enable_hashtags (bool): Whether hashtag generation is enabled
                - max_hashtags (int): Maximum number of hashtags per post (0-30)
                - custom_hashtag_rules (dict): Category-specific hashtag rules
                - hashtag_blacklist (list): Words to exclude from hashtag generation
        
        Example:
            config = linkedin_config.get_hashtag_config()
            # Returns:
            # {
            #     'enable_hashtags': True,
            #     'max_hashtags': 5,
            #     'custom_hashtag_rules': {
            #         'technology': {
            #             'required_hashtags': ['#Tech', '#Programming'],
            #             'suggested_hashtags': ['#Development', '#Coding'],
            #             'max_hashtags': 4,
            #             'priority': 1
            #         }
            #     },
            #     'hashtag_blacklist': ['spam', 'clickbait']
            # }
        
        Note:
            - Returns empty dict/list for None values to prevent errors
            - All values are validated during model save
            - Configuration is cached for performance
        """
        return {
            'enable_hashtags': self.enable_hashtags,
            'max_hashtags': self.max_hashtags,
            'custom_hashtag_rules': self.custom_hashtag_rules or {},
            'hashtag_blacklist': self.hashtag_blacklist or []
        }
    
    def get_image_posting_config(self):
        """
        Get image posting configuration as a dictionary.
        
        This method returns the complete image posting configuration for use by the
        LinkedInContentFormatter service. It includes all image-related settings
        with proper defaults.
        
        Returns:
            dict: Image posting configuration settings containing:
                - enable_image_posting (bool): Whether image posting is globally enabled
                - image_posting_strategy (str): Strategy for image inclusion
                    - 'always': Include images when available
                    - 'never': Never include images (text-only)
                    - 'category_based': Use category-specific rules
        
        Example:
            config = linkedin_config.get_image_posting_config()
            # Returns:
            # {
            #     'enable_image_posting': True,
            #     'image_posting_strategy': 'category_based'
            # }
        
        Strategy Descriptions:
            - 'always': All posts include images if featured image exists,
                       fallback to text-only if no image available
            - 'never': All posts are text-only, images are ignored
            - 'category_based': Image inclusion based on category_image_overrides
        
        Note:
            - Strategy defaults to 'always' if not set
            - Used in conjunction with should_include_images() for decisions
            - Configuration is validated during model save
        """
        return {
            'enable_image_posting': self.enable_image_posting,
            'image_posting_strategy': self.image_posting_strategy
        }
    
    def should_include_images(self, blog_post=None):
        """
        Determine if images should be included for a specific post based on configuration with error handling.
        
        Args:
            blog_post: The blog post instance (optional, for category-based decisions)
            
        Returns:
            bool: True if images should be included, False otherwise
        """
        start_time = time.time()
        post_id = getattr(blog_post, 'id', 'unknown') if blog_post else 'none'
        post_title = getattr(blog_post, 'title', 'Unknown Title') if blog_post else 'No Post'
        
        try:
            # Check global image posting setting
            if not self.enable_image_posting:
                decision_time = time.time() - start_time
                logger.info(f"Image posting globally disabled for post {post_id} ('{post_title}') - decision made in {decision_time:.3f}s")
                self._log_image_posting_metrics(post_id, 'globally_disabled', False, decision_time, 'global_setting')
                return False
            
            # Get strategy with fallback
            strategy = getattr(self, 'image_posting_strategy', 'always')
            
            if strategy == 'never':
                decision_time = time.time() - start_time
                logger.info(f"Image posting strategy 'never' for post {post_id} ('{post_title}') - decision made in {decision_time:.3f}s")
                self._log_image_posting_metrics(post_id, 'strategy_never', False, decision_time, 'strategy_setting')
                return False
            elif strategy == 'always':
                decision_time = time.time() - start_time
                logger.info(f"Image posting strategy 'always' for post {post_id} ('{post_title}') - decision made in {decision_time:.3f}s")
                self._log_image_posting_metrics(post_id, 'strategy_always', True, decision_time, 'strategy_setting')
                return True
            elif strategy == 'category_based':
                if not blog_post:
                    decision_time = time.time() - start_time
                    logger.debug(f"Category-based strategy but no blog post provided, defaulting to enabled - decision made in {decision_time:.3f}s")
                    self._log_image_posting_metrics('none', 'category_based_no_post', True, decision_time, 'fallback')
                    return True
                
                try:
                    result = self._should_include_images_category_based(blog_post)
                    decision_time = time.time() - start_time
                    logger.info(f"Category-based image decision for post {post_id} ('{post_title}'): {result} - decision made in {decision_time:.3f}s")
                    self._log_image_posting_metrics(post_id, 'category_based_success', result, decision_time, 'category_rules')
                    return result
                except Exception as e:
                    decision_time = time.time() - start_time
                    logger.warning(f"Error in category-based image decision for post {post_id}: {e} - fallback to enabled in {decision_time:.3f}s")
                    self._log_image_posting_metrics(post_id, 'category_based_error', True, decision_time, 'fallback', error=str(e))
                    return True  # Fallback to enabled
            else:
                decision_time = time.time() - start_time
                logger.warning(f"Unknown image posting strategy '{strategy}' for post {post_id}, defaulting to enabled - decision made in {decision_time:.3f}s")
                self._log_image_posting_metrics(post_id, 'unknown_strategy', True, decision_time, 'fallback', error=f"Unknown strategy: {strategy}")
                return True
            
        except Exception as e:
            decision_time = time.time() - start_time
            logger.error(f"Critical error determining image posting decision for post {post_id}: {e} - fallback to enabled in {decision_time:.3f}s")
            self._log_image_posting_metrics(post_id, 'critical_error', True, decision_time, 'fallback', error=str(e))
            # Safe fallback - default to image posting enabled
            return True
    
    def _should_include_images_category_based(self, blog_post):
        """
        Helper method for category-based image posting decisions with error handling.
        
        Args:
            blog_post: The blog post instance
            
        Returns:
            bool: True if images should be included based on category rules
        """
        try:
            # Check if post has categories
            if not hasattr(blog_post, 'categories'):
                logger.debug("Blog post has no categories attribute, defaulting to enabled")
                return True
            
            try:
                if not blog_post.categories.exists():
                    logger.debug("Blog post has no categories, defaulting to enabled")
                    return True
            except Exception as e:
                logger.warning(f"Error checking if categories exist: {e}")
                return True
            
            # Get category-specific overrides with error handling
            try:
                category_overrides = self.category_image_overrides or {}
                if not isinstance(category_overrides, dict):
                    logger.warning(f"Invalid category_image_overrides format: {type(category_overrides)}")
                    category_overrides = {}
            except Exception as e:
                logger.warning(f"Error accessing category_image_overrides: {e}")
                category_overrides = {}
            
            # Check each category for overrides
            try:
                for category in blog_post.categories.all():
                    try:
                        category_key = category.slug if hasattr(category, 'slug') else str(category.id)
                        
                        # Check for explicit override
                        if category_key in category_overrides:
                            override_value = category_overrides[category_key]
                            
                            if isinstance(override_value, bool):
                                logger.debug(f"Category '{category_key}' has explicit image override: {override_value}")
                                return override_value
                            elif isinstance(override_value, dict):
                                enable_images = override_value.get('enable_images', True)
                                logger.debug(f"Category '{category_key}' has dict image override: {enable_images}")
                                return enable_images
                            else:
                                logger.warning(f"Invalid override value for category '{category_key}': {override_value}")
                                
                    except Exception as e:
                        logger.warning(f"Error processing category override: {e}")
                        continue
                
                # No specific override found, use default
                logger.debug("No category-specific image overrides found, defaulting to enabled")
                return True
                
            except Exception as e:
                logger.warning(f"Error iterating through categories: {e}")
                return True
            
        except Exception as e:
            logger.error(f"Critical error in category-based image decision: {e}")
            return True  # Safe fallback
    
    def get_image_posting_strategy_display(self):
        """
        Get human-readable display text for image posting strategy.
        
        Returns:
            str: Display text for the strategy
        """
        strategy_map = {
            'always': 'Always include images when available',
            'never': 'Never include images (text-only posts)',
            'category_based': 'Based on post category settings'
        }
        return strategy_map.get(self.image_posting_strategy, 'Unknown strategy')
    
    def _log_image_posting_metrics(self, post_id, decision_type, include_images, decision_time, 
                                 decision_source, error=None, categories=None):
        """
        Log comprehensive image posting decision metrics for monitoring and analysis.
        
        Args:
            post_id: Blog post ID
            decision_type: Type of decision made (strategy_always, category_based_success, etc.)
            include_images: Whether images will be included
            decision_time: Time taken to make decision
            decision_source: Source of the decision (strategy_setting, category_rules, fallback)
            error: Error message if applicable
            categories: List of post categories if applicable
        """
        try:
            # Create metrics entry
            metrics = {
                'post_id': post_id,
                'decision_type': decision_type,
                'include_images': include_images,
                'decision_time_ms': round(decision_time * 1000, 2),
                'decision_source': decision_source,
                'config_id': self.id,
                'strategy': self.image_posting_strategy,
                'global_enabled': self.enable_image_posting,
                'timestamp': time.time()
            }
            
            if error:
                metrics['error'] = error
            
            if categories:
                metrics['categories'] = categories
            
            # Cache metrics for monitoring dashboard
            cache_key = f"linkedin_image_posting_metrics_{post_id}"
            cache.set(cache_key, metrics, timeout=86400)  # 24 hours
            
            # Update aggregate metrics
            self._update_image_posting_aggregate_metrics(decision_type, include_images, decision_time, bool(error))
            
        except Exception as e:
            logger.error(f"Error logging image posting metrics for post {post_id}: {e}")
    
    def _update_image_posting_aggregate_metrics(self, decision_type, include_images, decision_time, has_error):
        """
        Update aggregate image posting decision metrics for monitoring.
        
        Args:
            decision_type: Type of decision made
            include_images: Whether images will be included
            decision_time: Time taken for decision
            has_error: Whether an error occurred
        """
        try:
            cache_key = "linkedin_image_posting_aggregate_metrics"
            current_metrics = cache.get(cache_key, {
                'total_decisions': 0,
                'images_included_count': 0,
                'images_excluded_count': 0,
                'error_count': 0,
                'avg_decision_time': 0,
                'decision_types': {},
                'last_updated': time.time()
            })
            
            current_metrics['total_decisions'] += 1
            current_metrics['last_updated'] = time.time()
            
            if include_images:
                current_metrics['images_included_count'] += 1
            else:
                current_metrics['images_excluded_count'] += 1
            
            if has_error:
                current_metrics['error_count'] += 1
            
            # Track decision types
            current_metrics['decision_types'][decision_type] = current_metrics['decision_types'].get(decision_type, 0) + 1
            
            # Update average decision time
            if current_metrics['total_decisions'] > 0:
                current_avg = current_metrics['avg_decision_time']
                new_avg = ((current_avg * (current_metrics['total_decisions'] - 1)) + decision_time) / current_metrics['total_decisions']
                current_metrics['avg_decision_time'] = round(new_avg, 3)
            
            cache.set(cache_key, current_metrics, timeout=86400)  # 24 hours
            
        except Exception as e:
            logger.error(f"Error updating image posting aggregate metrics: {e}")
    
    def get_image_posting_metrics_summary(self):
        """
        Get a summary of image posting decision metrics for admin display.
        
        Returns:
            dict: Metrics summary
        """
        try:
            cache_key = "linkedin_image_posting_aggregate_metrics"
            metrics = cache.get(cache_key, {})
            
            if not metrics:
                return {'status': 'no_data', 'message': 'No image posting metrics available'}
            
            total_decisions = metrics.get('total_decisions', 0)
            if total_decisions == 0:
                return {'status': 'no_decisions', 'message': 'No image posting decisions recorded'}
            
            images_included = metrics.get('images_included_count', 0)
            images_excluded = metrics.get('images_excluded_count', 0)
            error_count = metrics.get('error_count', 0)
            
            summary = {
                'status': 'active',
                'total_decisions': total_decisions,
                'images_included_count': images_included,
                'images_excluded_count': images_excluded,
                'images_included_percentage': round((images_included / total_decisions) * 100, 1),
                'error_count': error_count,
                'error_percentage': round((error_count / total_decisions) * 100, 1),
                'avg_decision_time_ms': round(metrics.get('avg_decision_time', 0) * 1000, 2),
                'decision_types': metrics.get('decision_types', {}),
                'last_updated': metrics.get('last_updated')
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting image posting metrics summary: {e}")
            return {'status': 'error', 'message': f'Error retrieving metrics: {e}'}


class LinkedInPost(models.Model):
    """
    Model for tracking LinkedIn posting attempts and results.
    Links to blog posts and stores posting status and metadata.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]

    post = models.ForeignKey(
        'Post',
        on_delete=models.CASCADE,
        related_name='linkedin_posts',
        help_text="The blog post that was posted to LinkedIn"
    )
    linkedin_post_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="LinkedIn post ID returned by the API"
    )
    linkedin_post_url = models.URLField(
        blank=True,
        help_text="Direct URL to the LinkedIn post"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current status of the LinkedIn posting"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if posting failed"
    )
    error_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="LinkedIn API error code if available"
    )
    attempt_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of posting attempts made"
    )
    max_attempts = models.PositiveIntegerField(
        default=3,
        help_text="Maximum number of retry attempts"
    )
    
    # Content that was posted
    posted_title = models.CharField(
        max_length=500,
        blank=True,
        help_text="Title that was posted to LinkedIn"
    )
    posted_content = models.TextField(
        blank=True,
        help_text="Full content that was posted to LinkedIn"
    )
    posted_url = models.URLField(
        blank=True,
        help_text="Blog post URL that was included in the LinkedIn post"
    )
    
    # Image-related fields
    media_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="LinkedIn media IDs for uploaded images"
    )
    image_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="Original image URLs that were processed"
    )
    image_upload_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('skipped', 'Skipped'),
        ],
        default='pending',
        help_text="Status of image upload process"
    )
    image_error_message = models.TextField(
        blank=True,
        help_text="Error message if image upload failed"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the posting attempt was first created"
    )
    posted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the post was successfully posted to LinkedIn"
    )
    last_attempt_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the last posting attempt was made"
    )
    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the next retry attempt should be made"
    )

    class Meta:
        verbose_name = "LinkedIn Post"
        verbose_name_plural = "LinkedIn Posts"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['next_retry_at']),
        ]
        # Ensure one LinkedIn post record per blog post
        unique_together = ['post']

    def __str__(self):
        return f"LinkedIn post for '{self.post.title}' - {self.get_status_display()}"

    def is_successful(self):
        """Check if the post was successfully posted to LinkedIn"""
        return self.status == 'success' and self.linkedin_post_id

    def is_failed(self):
        """Check if the post failed and won't be retried"""
        return self.status == 'failed'

    def can_retry(self):
        """Check if the post can be retried"""
        return (
            self.status in ['failed', 'retrying'] and 
            self.attempt_count < self.max_attempts
        )

    def should_retry_now(self):
        """Check if the post should be retried now"""
        if not self.can_retry():
            return False
        
        if not self.next_retry_at:
            return True
        
        from django.utils import timezone
        return timezone.now() >= self.next_retry_at

    def mark_as_pending(self):
        """Mark the post as pending for posting"""
        self.status = 'pending'
        self.error_message = ''
        self.error_code = ''
        self.save(update_fields=['status', 'error_message', 'error_code'])

    def mark_as_success(self, linkedin_post_id, linkedin_post_url=None):
        """Mark the post as successfully posted with comprehensive logging"""
        from django.utils import timezone
        
        self.status = 'success'
        self.linkedin_post_id = linkedin_post_id
        self.linkedin_post_url = linkedin_post_url or ''
        self.posted_at = timezone.now()
        self.error_message = ''
        self.error_code = ''
        
        # Calculate total time from creation to success
        if self.created_at:
            total_time = (self.posted_at - self.created_at).total_seconds()
            logger.info(
                f"LinkedIn post successful for '{self.post.title}' after {self.attempt_count} attempt(s) "
                f"in {total_time:.2f} seconds. LinkedIn ID: {linkedin_post_id}"
            )
        else:
            logger.info(
                f"LinkedIn post successful for '{self.post.title}' after {self.attempt_count} attempt(s). "
                f"LinkedIn ID: {linkedin_post_id}"
            )
        
        # Log URL if available
        if linkedin_post_url:
            logger.debug(f"LinkedIn post URL for '{self.post.title}': {linkedin_post_url}")
        
        self.save(update_fields=[
            'status', 'linkedin_post_id', 'linkedin_post_url', 
            'posted_at', 'error_message', 'error_code'
        ])

    def mark_as_failed(self, error_message, error_code=None, can_retry=True):
        """Mark the post as failed with error details and comprehensive logging"""
        from django.utils import timezone
        
        self.attempt_count += 1
        self.last_attempt_at = timezone.now()
        self.error_message = error_message
        self.error_code = error_code or ''
        
        # Log the failure with detailed context
        logger.error(
            f"LinkedIn post failed for '{self.post.title}' (attempt {self.attempt_count}): "
            f"{error_message} (Error Code: {error_code or 'None'})"
        )
        
        # Check if we can retry based on attempt count and can_retry parameter
        if can_retry and self.attempt_count < self.max_attempts:
            self.status = 'retrying'
            # Calculate next retry time with exponential backoff
            retry_delay_minutes = 2 ** self.attempt_count  # 2, 4, 8 minutes
            self.next_retry_at = timezone.now() + timezone.timedelta(minutes=retry_delay_minutes)
            
            logger.info(
                f"LinkedIn post for '{self.post.title}' scheduled for retry in {retry_delay_minutes} minutes "
                f"(attempt {self.attempt_count + 1}/{self.max_attempts})"
            )
        else:
            self.status = 'failed'
            self.next_retry_at = None
            
            logger.critical(
                f"LinkedIn post for '{self.post.title}' permanently failed after {self.attempt_count} attempts. "
                f"Final error: {error_message}"
            )
        
        self.save(update_fields=[
            'status', 'attempt_count', 'last_attempt_at', 
            'error_message', 'error_code', 'next_retry_at'
        ])

    def record_posting_attempt(self, title, content, url):
        """Record the content that was attempted to be posted"""
        self.posted_title = title[:500]  # Truncate to field limit
        self.posted_content = content
        self.posted_url = url
        # Only use update_fields if the object already exists in the database
        if self.pk:
            self.save(update_fields=['posted_title', 'posted_content', 'posted_url'])
        # If it's a new object, the fields will be saved when save() is called later

    def has_images(self):
        """Check if the post has associated images"""
        return bool(self.media_ids or self.image_urls)

    def is_image_upload_successful(self):
        """Check if image upload was successful"""
        return self.image_upload_status == 'success'

    def is_image_upload_failed(self):
        """Check if image upload failed"""
        return self.image_upload_status == 'failed'

    def mark_image_upload_success(self, media_ids, image_urls):
        """Mark image upload as successful with media IDs and URLs"""
        self.image_upload_status = 'success'
        self.media_ids = media_ids if isinstance(media_ids, list) else [media_ids]
        self.image_urls = image_urls if isinstance(image_urls, list) else [image_urls]
        self.image_error_message = ''
        
        logger.info(
            f"Image upload successful for LinkedIn post '{self.post.title}'. "
            f"Media IDs: {self.media_ids}, Image URLs: {len(self.image_urls)} images"
        )
        
        if self.pk:
            self.save(update_fields=['image_upload_status', 'media_ids', 'image_urls', 'image_error_message'])

    def mark_image_upload_failed(self, error_message):
        """Mark image upload as failed with error message"""
        self.image_upload_status = 'failed'
        self.image_error_message = error_message
        
        logger.error(
            f"Image upload failed for LinkedIn post '{self.post.title}': {error_message}"
        )
        
        if self.pk:
            self.save(update_fields=['image_upload_status', 'image_error_message'])

    def mark_image_upload_skipped(self, reason="No images available"):
        """Mark image upload as skipped"""
        self.image_upload_status = 'skipped'
        self.image_error_message = reason
        
        logger.debug(
            f"Image upload skipped for LinkedIn post '{self.post.title}': {reason}"
        )
        
        if self.pk:
            self.save(update_fields=['image_upload_status', 'image_error_message'])

    def get_retry_delay_display(self):
        """Get human-readable retry delay"""
        if not self.next_retry_at:
            return "No retry scheduled"
        
        from django.utils import timezone
        now = timezone.now()
        
        if self.next_retry_at <= now:
            return "Ready to retry"
        
        delta = self.next_retry_at - now
        if delta.total_seconds() < 3600:  # Less than 1 hour
            minutes = int(delta.total_seconds() / 60)
            return f"Retry in {minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = int(delta.total_seconds() / 3600)
            return f"Retry in {hours} hour{'s' if hours != 1 else ''}"

    @classmethod
    def get_posts_ready_for_retry(cls):
        """Get all posts that are ready for retry"""
        from django.utils import timezone
        
        return cls.objects.filter(
            status='retrying',
            next_retry_at__lte=timezone.now()
        ).select_related('post')

    @classmethod
    def get_failed_posts(cls):
        """Get all permanently failed posts"""
        return cls.objects.filter(status='failed').select_related('post')

    @classmethod
    def get_successful_posts(cls):
        """Get all successfully posted posts"""
        return cls.objects.filter(status='success').select_related('post')