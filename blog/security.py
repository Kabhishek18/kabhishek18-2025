"""
Security utilities for blog engagement features.

This module provides security validation, rate limiting, and audit logging
functionality for the blog application.
"""

import re
import time
import hashlib
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from django.core.cache import cache
from django.conf import settings


class ContentValidator:
    """Validates user-generated content for security and spam"""
    
    # Spam patterns to detect
    SPAM_PATTERNS = [
        r'viagra|cialis|casino|poker|lottery',
        r'make money|earn \$|get rich|work from home',
        r'click here|visit now|act now|limited time',
        r'free money|guaranteed income|no investment',
        r'weight loss|lose weight|diet pills',
        r'replica|rolex|designer|handbags',
        r'mortgage|refinance|credit repair|debt',
        r'pharmacy|prescription|medication',
    ]
    
    # Suspicious URL patterns
    SUSPICIOUS_URL_PATTERNS = [
        r'bit\.ly|tinyurl|t\.co|goo\.gl',  # URL shorteners
        r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',  # IP addresses
        r'localhost|127\.0\.0\.1',  # Local addresses
        r'\.tk|\.ml|\.ga|\.cf',  # Suspicious TLDs
    ]
    
    @classmethod
    def validate_comment_content(cls, content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate comment content for spam and malicious patterns.
        
        Args:
            content: Comment content to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not content or not content.strip():
            return False, "Comment content cannot be empty"
        
        content = content.strip()
        
        # Check length limits
        if len(content) < 3:
            return False, "Comment is too short"
        
        if len(content) > 5000:
            return False, "Comment is too long (maximum 5000 characters)"
        
        # Check for spam patterns
        spam_score = cls._calculate_spam_score(content)
        if spam_score > 0.7:
            return False, "Comment appears to be spam"
        
        # Check for excessive repetition
        if cls._is_too_repetitive(content):
            return False, "Comment contains too much repetitive content"
        
        # Check for malicious HTML/JavaScript
        if cls._contains_malicious_code(content):
            return False, "Comment contains potentially malicious content"
        
        return True, None
    
    @classmethod
    def _contains_malicious_code(cls, content: str) -> bool:
        """Check for malicious HTML/JavaScript patterns"""
        malicious_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'data:text/html',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
        ]
        
        content_lower = content.lower()
        for pattern in malicious_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE | re.DOTALL):
                return True
        
        return False
    
    @classmethod
    def sanitize_html_content(cls, content: str) -> str:
        """
        Sanitize HTML content by removing dangerous tags and attributes.
        
        Args:
            content: HTML content to sanitize
            
        Returns:
            Sanitized HTML content
        """
        # Remove script tags and their content
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove dangerous tags
        dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form', 'input', 'button']
        for tag in dangerous_tags:
            content = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', content, flags=re.IGNORECASE | re.DOTALL)
            content = re.sub(f'<{tag}[^>]*/?>', '', content, flags=re.IGNORECASE)
        
        # Remove event handlers
        content = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', content, flags=re.IGNORECASE)
        
        # Remove javascript: and vbscript: URLs
        content = re.sub(r'(javascript|vbscript):[^"\']*', '', content, flags=re.IGNORECASE)
        
        return content
    
    @classmethod
    def validate_email(cls, email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email address format and check for suspicious patterns.
        
        Args:
            email: Email address to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email address is required"
        
        email = email.strip().lower()
        
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
    
    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate URL format and check for malicious patterns.
        
        Args:
            url: URL to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return True, None  # URL is optional
        
        url = url.strip()
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                return False, "Invalid URL format"
        except Exception:
            return False, "Invalid URL format"
        
        # Check for suspicious patterns
        for pattern in cls.SUSPICIOUS_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return False, "Suspicious URL detected"
        
        return True, None
    
    @classmethod
    def _calculate_spam_score(cls, content: str) -> float:
        """Calculate spam probability score (0.0 to 1.0)"""
        score = 0.0
        content_lower = content.lower()
        
        # Check for spam patterns
        for pattern in cls.SPAM_PATTERNS:
            matches = len(re.findall(pattern, content_lower))
            score += matches * 0.3
        
        # Check for excessive capitalization
        if len(content) > 20:
            caps_ratio = sum(1 for c in content if c.isupper()) / len(content)
            if caps_ratio > 0.5:
                score += 0.4
        
        # Check for excessive punctuation
        punct_count = len(re.findall(r'[!?]{2,}', content))
        score += punct_count * 0.2
        
        # Check for excessive numbers
        number_ratio = len(re.findall(r'\d', content)) / len(content) if content else 0
        if number_ratio > 0.3:
            score += 0.3
        
        return min(score, 1.0)
    
    @classmethod
    def _is_too_repetitive(cls, content: str) -> bool:
        """Check if content is too repetitive (spam indicator)"""
        words = content.lower().split()
        if len(words) < 5:
            return False
        
        unique_words = set(words)
        repetition_ratio = len(unique_words) / len(words)
        
        return repetition_ratio < 0.3  # Less than 30% unique words


class SecurityHeaders:
    """Manages security headers for HTTP responses"""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """
        Get recommended security headers.
        
        Returns:
            Dictionary of security headers
        """
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Content-Security-Policy': (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
                "https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' "
                "https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "media-src 'self' https:; "
                "frame-src https://www.youtube.com https://player.vimeo.com; "
                "connect-src 'self';"
            )
        }


class CSRFProtection:
    """Enhanced CSRF protection utilities"""
    
    @staticmethod
    def generate_csrf_token(request) -> str:
        """Generate a CSRF token for the request"""
        from django.middleware.csrf import get_token
        return get_token(request)
    
    @staticmethod
    def validate_csrf_token(request, token: str) -> bool:
        """Validate CSRF token"""
        from django.middleware.csrf import get_token
        expected_token = get_token(request)
        return token == expected_token


class RateLimitTracker:
    """Track rate limiting for various actions"""
    
    def __init__(self, cache_backend=None):
        from django.core.cache import cache
        self.cache = cache_backend or cache
    
    def is_rate_limited(self, identifier: str, action: str, 
                       limit: int, window_seconds: int) -> bool:
        """
        Check if an action is rate limited.
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            action: Action being performed
            limit: Maximum number of actions allowed
            window_seconds: Time window in seconds
            
        Returns:
            True if rate limited, False otherwise
        """
        cache_key = f"rate_limit:{action}:{identifier}"
        current_time = int(time.time())
        window_start = current_time - window_seconds
        
        # Get existing attempts
        attempts = self.cache.get(cache_key, [])
        
        # Filter out old attempts
        recent_attempts = [
            attempt for attempt in attempts 
            if attempt > window_start
        ]
        
        # Check if limit exceeded
        if len(recent_attempts) >= limit:
            return True
        
        # Record this attempt
        recent_attempts.append(current_time)
        self.cache.set(cache_key, recent_attempts, window_seconds)
        
        return False
    
    def get_remaining_attempts(self, identifier: str, action: str,
                             limit: int, window_seconds: int) -> int:
        """Get remaining attempts before rate limit"""
        cache_key = f"rate_limit:{action}:{identifier}"
        current_time = int(time.time())
        window_start = current_time - window_seconds
        
        attempts = self.cache.get(cache_key, [])
        recent_attempts = [
            attempt for attempt in attempts 
            if attempt > window_start
        ]
        
        return max(0, limit - len(recent_attempts))


class SecurityAuditLogger:
    """Log security-related events for monitoring"""
    
    @staticmethod
    def log_suspicious_activity(request, activity_type: str, details: Dict):
        """Log suspicious activity for security monitoring"""
        import logging
        
        logger = logging.getLogger('blog.security')
        
        log_data = {
            'activity_type': activity_type,
            'ip_address': SecurityAuditLogger._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'timestamp': time.time(),
            'details': details
        }
        
        logger.warning(f"Suspicious activity detected: {log_data}")
    
    @staticmethod
    def log_rate_limit_exceeded(request, action: str, identifier: str):
        """Log rate limit violations"""
        SecurityAuditLogger.log_suspicious_activity(
            request, 
            'rate_limit_exceeded',
            {
                'action': action,
                'identifier': identifier
            }
        )
    
    @staticmethod
    def log_spam_attempt(request, content_type: str, content: str):
        """Log spam attempts"""
        SecurityAuditLogger.log_suspicious_activity(
            request,
            'spam_attempt',
            {
                'content_type': content_type,
                'content_preview': content[:100] if content else ''
            }
        )
    
    @staticmethod
    def _get_client_ip(request) -> str:
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'unknown'