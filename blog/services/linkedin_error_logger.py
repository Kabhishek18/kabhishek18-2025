"""
Comprehensive error logging utility for LinkedIn integration.

This module provides structured logging for all LinkedIn-related errors,
including authentication failures, rate limiting, content errors, and more.
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings


logger = logging.getLogger(__name__)


class LinkedInErrorLogger:
    """
    Comprehensive error logging service for LinkedIn integration.
    
    Provides structured logging with error categorization, metrics tracking,
    and alert generation for critical issues.
    """
    
    # Error severity levels
    SEVERITY_DEBUG = 'debug'
    SEVERITY_INFO = 'info'
    SEVERITY_WARNING = 'warning'
    SEVERITY_ERROR = 'error'
    SEVERITY_CRITICAL = 'critical'
    
    # Error categories
    CATEGORY_AUTHENTICATION = 'authentication'
    CATEGORY_RATE_LIMITING = 'rate_limiting'
    CATEGORY_CONTENT_VALIDATION = 'content_validation'
    CATEGORY_MEDIA_UPLOAD = 'media_upload'
    CATEGORY_NETWORK = 'network'
    CATEGORY_SERVER_ERROR = 'server_error'
    CATEGORY_CONFIGURATION = 'configuration'
    CATEGORY_UNKNOWN = 'unknown'
    
    def __init__(self):
        self.cache_prefix = 'linkedin_error_metrics'
        self.cache_ttl = 3600  # 1 hour
    
    def log_authentication_error(self, error_details: Dict[str, Any], context: Optional[Dict] = None):
        """
        Log authentication-related errors with specific handling.
        
        Args:
            error_details: Dictionary containing error information
            context: Additional context information
        """
        structured_log = self._create_structured_log(
            category=self.CATEGORY_AUTHENTICATION,
            severity=self.SEVERITY_ERROR,
            error_details=error_details,
            context=context
        )
        
        # Determine specific authentication issue
        error_message = error_details.get('message', '')
        error_code = error_details.get('error_code', '')
        
        if any(term in error_message.lower() for term in ['expired', 'invalid_token']):
            structured_log['auth_issue_type'] = 'token_expired'
            structured_log['severity'] = self.SEVERITY_WARNING
            logger.warning(f"LinkedIn token expired: {self._format_log_message(structured_log)}")
        elif any(term in error_message.lower() for term in ['invalid_client', 'unauthorized_client']):
            structured_log['auth_issue_type'] = 'invalid_credentials'
            structured_log['severity'] = self.SEVERITY_CRITICAL
            logger.critical(f"LinkedIn invalid credentials: {self._format_log_message(structured_log)}")
        elif error_code == '403' or 'forbidden' in error_message.lower():
            structured_log['auth_issue_type'] = 'insufficient_permissions'
            structured_log['severity'] = self.SEVERITY_ERROR
            logger.error(f"LinkedIn insufficient permissions: {self._format_log_message(structured_log)}")
        else:
            structured_log['auth_issue_type'] = 'unknown_auth_error'
            logger.error(f"LinkedIn authentication error: {self._format_log_message(structured_log)}")
        
        self._update_error_metrics(structured_log)
        self._check_alert_thresholds(structured_log)
    
    def log_rate_limit_error(self, error_details: Dict[str, Any], context: Optional[Dict] = None):
        """
        Log rate limiting errors with quota tracking.
        
        Args:
            error_details: Dictionary containing error information
            context: Additional context information
        """
        structured_log = self._create_structured_log(
            category=self.CATEGORY_RATE_LIMITING,
            severity=self.SEVERITY_WARNING,
            error_details=error_details,
            context=context
        )
        
        # Extract rate limit specific information
        retry_after = error_details.get('retry_after')
        quota_type = error_details.get('quota_type', 'unknown')
        
        structured_log.update({
            'retry_after_seconds': retry_after,
            'quota_type': quota_type,
            'rate_limit_issue_type': 'quota_exceeded'
        })
        
        if quota_type == 'daily':
            structured_log['severity'] = self.SEVERITY_ERROR
            logger.error(f"LinkedIn daily quota exceeded: {self._format_log_message(structured_log)}")
        else:
            logger.warning(f"LinkedIn rate limit exceeded: {self._format_log_message(structured_log)}")
        
        self._update_error_metrics(structured_log)
        self._track_rate_limit_patterns(structured_log)
    
    def log_content_error(self, error_details: Dict[str, Any], content_data: Optional[Dict] = None, context: Optional[Dict] = None):
        """
        Log content validation errors with content analysis.
        
        Args:
            error_details: Dictionary containing error information
            content_data: The content that failed validation
            context: Additional context information
        """
        structured_log = self._create_structured_log(
            category=self.CATEGORY_CONTENT_VALIDATION,
            severity=self.SEVERITY_ERROR,
            error_details=error_details,
            context=context
        )
        
        # Analyze content issues
        if content_data:
            content_analysis = self._analyze_content_issues(content_data, error_details)
            structured_log.update(content_analysis)
        
        logger.error(f"LinkedIn content validation error: {self._format_log_message(structured_log)}")
        
        self._update_error_metrics(structured_log)
        self._track_content_error_patterns(structured_log)
    
    def log_network_error(self, error_details: Dict[str, Any], context: Optional[Dict] = None):
        """
        Log network-related errors.
        
        Args:
            error_details: Dictionary containing error information
            context: Additional context information
        """
        structured_log = self._create_structured_log(
            category=self.CATEGORY_NETWORK,
            severity=self.SEVERITY_WARNING,
            error_details=error_details,
            context=context
        )
        
        # Categorize network issues
        error_message = error_details.get('message', '').lower()
        
        if 'timeout' in error_message:
            structured_log['network_issue_type'] = 'timeout'
        elif 'connection' in error_message:
            structured_log['network_issue_type'] = 'connection_error'
        elif 'dns' in error_message:
            structured_log['network_issue_type'] = 'dns_resolution'
        else:
            structured_log['network_issue_type'] = 'unknown_network_error'
        
        logger.warning(f"LinkedIn network error: {self._format_log_message(structured_log)}")
        
        self._update_error_metrics(structured_log)
    
    def log_server_error(self, error_details: Dict[str, Any], context: Optional[Dict] = None):
        """
        Log server-side errors from LinkedIn API.
        
        Args:
            error_details: Dictionary containing error information
            context: Additional context information
        """
        structured_log = self._create_structured_log(
            category=self.CATEGORY_SERVER_ERROR,
            severity=self.SEVERITY_ERROR,
            error_details=error_details,
            context=context
        )
        
        status_code = error_details.get('status_code')
        if status_code:
            if status_code >= 500:
                structured_log['server_issue_type'] = 'internal_server_error'
                structured_log['severity'] = self.SEVERITY_ERROR
            elif status_code == 502:
                structured_log['server_issue_type'] = 'bad_gateway'
            elif status_code == 503:
                structured_log['server_issue_type'] = 'service_unavailable'
            elif status_code == 504:
                structured_log['server_issue_type'] = 'gateway_timeout'
        
        logger.error(f"LinkedIn server error: {self._format_log_message(structured_log)}")
        
        self._update_error_metrics(structured_log)
    
    def log_configuration_error(self, error_details: Dict[str, Any], context: Optional[Dict] = None):
        """
        Log configuration-related errors.
        
        Args:
            error_details: Dictionary containing error information
            context: Additional context information
        """
        structured_log = self._create_structured_log(
            category=self.CATEGORY_CONFIGURATION,
            severity=self.SEVERITY_CRITICAL,
            error_details=error_details,
            context=context
        )
        
        logger.critical(f"LinkedIn configuration error: {self._format_log_message(structured_log)}")
        
        self._update_error_metrics(structured_log)
        self._check_alert_thresholds(structured_log)
    
    def log_media_upload_error(self, error_details: Dict[str, Any], context: Optional[Dict] = None):
        """
        Log media upload-related errors with comprehensive tracking.
        
        Args:
            error_details: Dictionary containing error information
            context: Additional context information
        """
        structured_log = self._create_structured_log(
            category=self.CATEGORY_MEDIA_UPLOAD,
            severity=self.SEVERITY_ERROR,
            error_details=error_details,
            context=context
        )
        
        # Analyze media upload specific issues
        error_message = error_details.get('message', '').lower()
        image_url = error_details.get('image_url', '')
        
        # Categorize media upload issues
        if 'timeout' in error_message:
            structured_log['media_issue_type'] = 'upload_timeout'
        elif 'too large' in error_message or 'file size' in error_message:
            structured_log['media_issue_type'] = 'file_too_large'
        elif 'invalid' in error_message and 'format' in error_message:
            structured_log['media_issue_type'] = 'invalid_format'
        elif 'download' in error_message:
            structured_log['media_issue_type'] = 'download_failed'
        elif 'register' in error_message:
            structured_log['media_issue_type'] = 'registration_failed'
        elif 'quota' in error_message or 'limit' in error_message:
            structured_log['media_issue_type'] = 'quota_exceeded'
            structured_log['severity'] = self.SEVERITY_WARNING
        else:
            structured_log['media_issue_type'] = 'unknown_media_error'
        
        # Add media-specific context
        if image_url:
            structured_log['image_url'] = image_url
            # Extract image file extension for analysis
            if '.' in image_url:
                file_extension = image_url.split('.')[-1].lower()
                structured_log['image_format'] = file_extension
        
        # Check if fallback was used
        fallback_used = context and context.get('fallback_to_text', False)
        if fallback_used:
            structured_log['fallback_used'] = True
            structured_log['severity'] = self.SEVERITY_WARNING
            logger.warning(f"LinkedIn media upload failed, fallback used: {self._format_log_message(structured_log)}")
        else:
            logger.error(f"LinkedIn media upload error: {self._format_log_message(structured_log)}")
        
        self._update_error_metrics(structured_log)
        self._track_media_upload_patterns(structured_log)
        
        # Check for critical media upload issues
        if structured_log['media_issue_type'] in ['quota_exceeded', 'registration_failed']:
            self._check_alert_thresholds(structured_log)
    
    def log_fallback_attempt(self, original_error: Dict[str, Any], fallback_type: str, 
                           fallback_result: Dict[str, Any], context: Optional[Dict] = None):
        """
        Log fallback mechanism attempts and results.
        
        Args:
            original_error: The original error that triggered the fallback
            fallback_type: Type of fallback mechanism used
            fallback_result: Result of the fallback attempt
            context: Additional context information
        """
        structured_log = {
            'timestamp': timezone.now().isoformat(),
            'event_type': 'fallback_attempt',
            'fallback_type': fallback_type,
            'original_error': original_error,
            'fallback_result': fallback_result,
            'context': context or {}
        }
        
        if fallback_result.get('fallback_success'):
            logger.info(f"LinkedIn fallback successful: {self._format_log_message(structured_log)}")
        else:
            logger.warning(f"LinkedIn fallback failed: {self._format_log_message(structured_log)}")
        
        self._track_fallback_patterns(structured_log)
    
    def _create_structured_log(self, category: str, severity: str, error_details: Dict[str, Any], 
                              context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create a structured log entry with standard fields.
        
        Args:
            category: Error category
            severity: Error severity level
            error_details: Error details dictionary
            context: Additional context
            
        Returns:
            dict: Structured log entry
        """
        return {
            'timestamp': timezone.now().isoformat(),
            'category': category,
            'severity': severity,
            'error_message': error_details.get('message', ''),
            'error_code': error_details.get('error_code', ''),
            'status_code': error_details.get('status_code'),
            'context': context or {},
            'service': 'linkedin_integration'
        }
    
    def _format_log_message(self, structured_log: Dict[str, Any]) -> str:
        """
        Format structured log for human-readable output.
        
        Args:
            structured_log: Structured log dictionary
            
        Returns:
            str: Formatted log message
        """
        base_message = structured_log.get('error_message', 'Unknown error')
        
        details = []
        if structured_log.get('error_code'):
            details.append(f"Code: {structured_log['error_code']}")
        if structured_log.get('status_code'):
            details.append(f"HTTP: {structured_log['status_code']}")
        
        context = structured_log.get('context', {})
        if context.get('post_title'):
            details.append(f"Post: {context['post_title']}")
        if context.get('attempt_count'):
            details.append(f"Attempt: {context['attempt_count']}")
        
        if details:
            return f"{base_message} ({', '.join(details)})"
        
        return base_message
    
    def _update_error_metrics(self, structured_log: Dict[str, Any]):
        """
        Update cached error metrics for monitoring.
        
        Args:
            structured_log: Structured log entry
        """
        cache_key = f"{self.cache_prefix}_{structured_log['category']}"
        
        current_metrics = cache.get(cache_key, {
            'count': 0,
            'last_occurrence': None,
            'severity_counts': {}
        })
        
        current_metrics['count'] += 1
        current_metrics['last_occurrence'] = structured_log['timestamp']
        
        severity = structured_log['severity']
        current_metrics['severity_counts'][severity] = current_metrics['severity_counts'].get(severity, 0) + 1
        
        cache.set(cache_key, current_metrics, timeout=self.cache_ttl)
    
    def _check_alert_thresholds(self, structured_log: Dict[str, Any]):
        """
        Check if error counts exceed alert thresholds.
        
        Args:
            structured_log: Structured log entry
        """
        if structured_log['severity'] == self.SEVERITY_CRITICAL:
            # Always alert on critical errors
            logger.critical(f"ALERT: Critical LinkedIn error detected: {structured_log['error_message']}")
        
        # Check for error frequency thresholds
        cache_key = f"{self.cache_prefix}_{structured_log['category']}"
        metrics = cache.get(cache_key, {})
        
        error_count = metrics.get('count', 0)
        
        # Alert thresholds
        if structured_log['category'] == self.CATEGORY_AUTHENTICATION and error_count >= 3:
            logger.critical(f"ALERT: Multiple LinkedIn authentication failures: {error_count} in last hour")
        elif structured_log['category'] == self.CATEGORY_RATE_LIMITING and error_count >= 5:
            logger.critical(f"ALERT: Frequent LinkedIn rate limiting: {error_count} in last hour")
        elif error_count >= 10:
            logger.critical(f"ALERT: High LinkedIn error frequency: {error_count} {structured_log['category']} errors in last hour")
    
    def _analyze_content_issues(self, content_data: Dict[str, Any], error_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze content data to identify specific validation issues.
        
        Args:
            content_data: Content that failed validation
            error_details: Error details from LinkedIn API
            
        Returns:
            dict: Content analysis results
        """
        analysis = {
            'content_length': 0,
            'has_media': False,
            'potential_issues': []
        }
        
        # Analyze content length
        content_text = content_data.get('shareCommentary', {}).get('text', '')
        analysis['content_length'] = len(content_text)
        
        if analysis['content_length'] > 3000:  # LinkedIn's character limit
            analysis['potential_issues'].append('content_too_long')
        
        # Check for media
        media = content_data.get('media', [])
        analysis['has_media'] = len(media) > 0
        
        # Check for URL issues
        if media:
            for media_item in media:
                original_url = media_item.get('originalUrl', '')
                if not original_url.startswith(('http://', 'https://')):
                    analysis['potential_issues'].append('invalid_url_format')
        
        # Check for special characters or encoding issues
        try:
            content_text.encode('utf-8')
        except UnicodeEncodeError:
            analysis['potential_issues'].append('encoding_issues')
        
        return analysis
    
    def _track_rate_limit_patterns(self, structured_log: Dict[str, Any]):
        """
        Track rate limiting patterns for analysis.
        
        Args:
            structured_log: Structured log entry
        """
        pattern_key = f"{self.cache_prefix}_rate_limit_pattern"
        
        current_pattern = cache.get(pattern_key, {
            'occurrences': [],
            'quota_types': {}
        })
        
        current_pattern['occurrences'].append(structured_log['timestamp'])
        
        quota_type = structured_log.get('quota_type', 'unknown')
        current_pattern['quota_types'][quota_type] = current_pattern['quota_types'].get(quota_type, 0) + 1
        
        # Keep only last 24 hours of occurrences
        cutoff_time = timezone.now() - timezone.timedelta(hours=24)
        current_pattern['occurrences'] = [
            occurrence for occurrence in current_pattern['occurrences']
            if datetime.fromisoformat(occurrence.replace('Z', '+00:00')) > cutoff_time
        ]
        
        cache.set(pattern_key, current_pattern, timeout=86400)  # 24 hours
    
    def _track_content_error_patterns(self, structured_log: Dict[str, Any]):
        """
        Track content error patterns for analysis.
        
        Args:
            structured_log: Structured log entry
        """
        pattern_key = f"{self.cache_prefix}_content_error_pattern"
        
        current_pattern = cache.get(pattern_key, {
            'issue_types': {},
            'content_lengths': []
        })
        
        potential_issues = structured_log.get('potential_issues', [])
        for issue in potential_issues:
            current_pattern['issue_types'][issue] = current_pattern['issue_types'].get(issue, 0) + 1
        
        content_length = structured_log.get('content_length', 0)
        if content_length > 0:
            current_pattern['content_lengths'].append(content_length)
        
        cache.set(pattern_key, current_pattern, timeout=self.cache_ttl)
    
    def _track_fallback_patterns(self, structured_log: Dict[str, Any]):
        """
        Track fallback mechanism usage patterns.
        
        Args:
            structured_log: Structured log entry
        """
        pattern_key = f"{self.cache_prefix}_fallback_pattern"
        
        current_pattern = cache.get(pattern_key, {
            'fallback_types': {},
            'success_rates': {}
        })
        
        fallback_type = structured_log.get('fallback_type', 'unknown')
        current_pattern['fallback_types'][fallback_type] = current_pattern['fallback_types'].get(fallback_type, 0) + 1
        
        # Track success rates
        if fallback_type not in current_pattern['success_rates']:
            current_pattern['success_rates'][fallback_type] = {'attempts': 0, 'successes': 0}
        
        current_pattern['success_rates'][fallback_type]['attempts'] += 1
        
        if structured_log.get('fallback_result', {}).get('fallback_success'):
            current_pattern['success_rates'][fallback_type]['successes'] += 1
        
        cache.set(pattern_key, current_pattern, timeout=self.cache_ttl)
    
    def _track_media_upload_patterns(self, structured_log: Dict[str, Any]):
        """
        Track media upload error patterns for analysis.
        
        Args:
            structured_log: Structured log entry
        """
        pattern_key = f"{self.cache_prefix}_media_upload_pattern"
        
        current_pattern = cache.get(pattern_key, {
            'issue_types': {},
            'image_formats': {},
            'fallback_usage': 0,
            'total_attempts': 0
        })
        
        current_pattern['total_attempts'] += 1
        
        # Track issue types
        issue_type = structured_log.get('media_issue_type', 'unknown')
        current_pattern['issue_types'][issue_type] = current_pattern['issue_types'].get(issue_type, 0) + 1
        
        # Track image formats that fail
        image_format = structured_log.get('image_format')
        if image_format:
            current_pattern['image_formats'][image_format] = current_pattern['image_formats'].get(image_format, 0) + 1
        
        # Track fallback usage
        if structured_log.get('fallback_used'):
            current_pattern['fallback_usage'] += 1
        
        cache.set(pattern_key, current_pattern, timeout=self.cache_ttl)
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get a summary of errors from the last specified hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            dict: Error summary
        """
        summary = {
            'period_hours': hours,
            'categories': {},
            'total_errors': 0,
            'critical_errors': 0,
            'generated_at': timezone.now().isoformat()
        }
        
        categories = [
            self.CATEGORY_AUTHENTICATION,
            self.CATEGORY_RATE_LIMITING,
            self.CATEGORY_CONTENT_VALIDATION,
            self.CATEGORY_MEDIA_UPLOAD,
            self.CATEGORY_NETWORK,
            self.CATEGORY_SERVER_ERROR,
            self.CATEGORY_CONFIGURATION
        ]
        
        for category in categories:
            cache_key = f"{self.cache_prefix}_{category}"
            metrics = cache.get(cache_key, {})
            
            if metrics:
                summary['categories'][category] = metrics
                summary['total_errors'] += metrics.get('count', 0)
                summary['critical_errors'] += metrics.get('severity_counts', {}).get(self.SEVERITY_CRITICAL, 0)
        
        return summary