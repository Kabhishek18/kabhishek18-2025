from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import logging
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
        self.full_clean()
        super().save(*args, **kwargs)

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