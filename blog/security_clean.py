"""
Security utilities for blog engagement features.

This module provides input validation, sanitization, and security measures
for user-generated content in the blog system.
"""

import re
import html
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags, escape
from django.conf import settings
from typing import Dict, List, Optional, Tuple
import hashlib
import time
from urllib.parse import urlparse


class ContentSanitizer:
    """Handles sanitization of user-generated content"""
    
    # Allowed HTML tags for comments (very restrictive)
    ALLOWED_COMMENT_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'i', 'b',
        'blockquote', 'code', 'pre'
    ]
    
    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        '*': ['class'],
        'blockquote': ['cite'],
        'code': ['class'],
        'pre': ['class']
    }
    
    # Protocols allowed in links
    ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']
    
    @classmethod
    def sanitize_comment_content(cls, content: str) -> str:
        """
        Sanitize comment content to prevent XSS attacks.
        
        Args:
            content: Raw comment content
            
        Returns:
            Sanitized content safe for display
        """
        if not content:
            return ""
        
        # Strip all HTML tags for now (can be enhanced later with bleach)
        sanitized = strip_tags(content)
        
        # Escape any remaining HTML entities
        sanitized = escape(sanitized)
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized
    
    @classmethod
    def sanitize_user_input(cls, content: str, allow_html: bool = False) -> str:
        """
        Sanitize general user input.
        
        Args:
            content: Raw user input
            allow_html: Whether to allow HTML tags
            
        Returns:
            Sanitized content safe for display
        """
        if not content:
            return ""
        
        if not allow_html:
            # Strip all HTML tags
            sanitized = strip_tags(content)
            # Escape any remaining HTML entities
            sanitized = escape(sanitized)
        else:
            # For now, just escape - can be enhanced with bleach later
            sanitized = escape(content)
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized
    
    @classmethod
    def validate_email_content(cls, email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email address for newsletter subscription.
        
        Args:
            email: Email address to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email address is required"
        
        # Basic format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return False, "Invalid email address format"
        
        # Check for suspicious patterns
        suspicious_domains = [
            '10minutemail.com', 'tempmail.org', 'guerrillamail.com',
            'mailinator.com', 'throwaway.email'
        ]
        
        domain = email.split('@')[1]
        if domain in suspicious_domains:
            return False, "Temporary email addresses are not allowed"
        
        return True, None


class RateLimiter:
    """Simple rate limiting for user actions"""
    
    def __init__(self):
        self.attempts = {}
    
    def is_rate_limited(self, identifier: str, max_attempts: int = 5, window_minutes: int = 15) -> bool:
        """
        Check if an identifier is rate limited.
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            max_attempts: Maximum attempts allowed
            window_minutes: Time window in minutes
            
        Returns:
            True if rate limited, False otherwise
        """
        current_time = time.time()
        window_seconds = window_minutes * 60
        
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        
        # Clean old attempts
        self.attempts[identifier] = [
            attempt_time for attempt_time in self.attempts[identifier]
            if current_time - attempt_time < window_seconds
        ]
        
        # Check if rate limited
        if len(self.attempts[identifier]) >= max_attempts:
            return True
        
        # Record this attempt
        self.attempts[identifier].append(current_time)
        return False


class SecurityAuditLogger:
    """Logs security-related events"""
    
    @staticmethod
    def log_failed_login(request, username: str):
        """Log failed login attempt"""
        pass  # Placeholder for logging implementation
    
    @staticmethod
    def log_suspicious_activity(request, activity_type: str, details: str):
        """Log suspicious activity"""
        pass  # Placeholder for logging implementation
    
    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'unknown'


# Global instances
rate_limiter = RateLimiter()