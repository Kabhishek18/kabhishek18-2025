"""
Comprehensive error handling and retry system for LinkedIn image integration.

This module provides:
- Detailed error categorization and logging
- Retry logic with exponential backoff
- Error recovery strategies
- Performance monitoring and alerting
"""

import time
import random
import logging
from typing import Dict, Any, Optional, Callable, Tuple, List
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from .linkedin_error_logger import LinkedInErrorLogger


logger = logging.getLogger(__name__)


class LinkedInImageError(Exception):
    """Base exception for LinkedIn image processing errors"""
    
    def __init__(self, message: str, error_code: str = None, is_retryable: bool = None, 
                 retry_after: int = None, context: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code or 'UNKNOWN_ERROR'
        self.is_retryable = is_retryable if is_retryable is not None else self._determine_retryable()
        self.retry_after = retry_after
        self.context = context or {}
        super().__init__(self.message)
    
    def _determine_retryable(self) -> bool:
        """Determine if error is retryable based on error code"""
        retryable_codes = [
            'NETWORK_ERROR',
            'TIMEOUT_ERROR',
            'SERVER_ERROR',
            'RATE_LIMIT_EXCEEDED',
            'TEMPORARY_FAILURE',
            'IMAGE_DOWNLOAD_FAILED',
            'PROCESSING_TIMEOUT'
        ]
        return self.error_code in retryable_codes


class ImageProcessingError(LinkedInImageError):
    """Specific exception for image processing failures"""
    
    def __init__(self, message: str, image_url: str = None, processing_step: str = None, **kwargs):
        self.image_url = image_url
        self.processing_step = processing_step
        super().__init__(message, **kwargs)


class ImageUploadError(LinkedInImageError):
    """Specific exception for image upload failures"""
    
    def __init__(self, message: str, upload_stage: str = None, media_id: str = None, **kwargs):
        self.upload_stage = upload_stage
        self.media_id = media_id
        super().__init__(message, **kwargs)


class LinkedInImageErrorHandler:
    """
    Comprehensive error handling system for LinkedIn image integration.
    
    Provides:
    - Structured error logging with detailed categorization
    - Retry logic with exponential backoff
    - Error recovery and fallback strategies
    - Performance monitoring and alerting
    """
    
    # Error codes for image processing
    ERROR_CODES = {
        # Image processing errors
        'IMAGE_DOWNLOAD_FAILED': {
            'retryable': True,
            'max_retries': 3,
            'base_delay': 2,
            'severity': 'error'
        },
        'IMAGE_PROCESSING_FAILED': {
            'retryable': False,
            'max_retries': 0,
            'base_delay': 0,
            'severity': 'error'
        },
        'IMAGE_VALIDATION_FAILED': {
            'retryable': False,
            'max_retries': 0,
            'base_delay': 0,
            'severity': 'warning'
        },
        'IMAGE_TOO_LARGE': {
            'retryable': True,
            'max_retries': 2,
            'base_delay': 1,
            'severity': 'warning'
        },
        'UNSUPPORTED_FORMAT': {
            'retryable': True,
            'max_retries': 1,
            'base_delay': 1,
            'severity': 'warning'
        },
        
        # Upload errors
        'UPLOAD_TIMEOUT': {
            'retryable': True,
            'max_retries': 3,
            'base_delay': 5,
            'severity': 'error'
        },
        'UPLOAD_FAILED': {
            'retryable': True,
            'max_retries': 2,
            'base_delay': 3,
            'severity': 'error'
        },
        'MEDIA_REGISTRATION_FAILED': {
            'retryable': True,
            'max_retries': 2,
            'base_delay': 2,
            'severity': 'error'
        },
        'QUOTA_EXCEEDED': {
            'retryable': True,
            'max_retries': 1,
            'base_delay': 3600,  # 1 hour
            'severity': 'warning'
        },
        
        # Network errors
        'NETWORK_ERROR': {
            'retryable': True,
            'max_retries': 3,
            'base_delay': 2,
            'severity': 'warning'
        },
        'TIMEOUT_ERROR': {
            'retryable': True,
            'max_retries': 3,
            'base_delay': 5,
            'severity': 'warning'
        },
        
        # Server errors
        'SERVER_ERROR': {
            'retryable': True,
            'max_retries': 2,
            'base_delay': 10,
            'severity': 'error'
        },
        'RATE_LIMIT_EXCEEDED': {
            'retryable': True,
            'max_retries': 1,
            'base_delay': 300,  # 5 minutes
            'severity': 'warning'
        }
    }
    
    def __init__(self):
        self.error_logger = LinkedInErrorLogger()
        self.cache_prefix = 'linkedin_image_error_handler'
        self.metrics_cache_ttl = 3600  # 1 hour
        
        # Performance thresholds
        self.performance_thresholds = {
            'max_processing_time': 30,  # seconds
            'max_upload_time': 60,      # seconds
            'max_retry_attempts': 5,
            'error_rate_threshold': 0.1  # 10%
        }
    
    def handle_image_processing_error(self, error: Exception, image_url: str, 
                                    processing_step: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle image processing errors with comprehensive logging and recovery.
        
        Args:
            error: The exception that occurred
            image_url: URL of the image being processed
            processing_step: Step where the error occurred
            context: Additional context information
            
        Returns:
            dict: Error handling result with recovery suggestions
        """
        error_details = self._extract_error_details(error, {
            'image_url': image_url,
            'processing_step': processing_step,
            'context': context or {}
        })
        
        # Log the error with detailed context
        self.error_logger.log_media_upload_error(
            error_details=error_details,
            context={
                'image_url': image_url,
                'processing_step': processing_step,
                'error_type': 'image_processing',
                **context or {}
            }
        )
        
        # Update metrics
        self._update_processing_metrics(error_details, processing_step)
        
        # Determine recovery strategy
        recovery_strategy = self._determine_recovery_strategy(error_details, processing_step)
        
        # Check if we should alert
        self._check_processing_alert_thresholds(error_details, processing_step)
        
        return {
            'error_handled': True,
            'error_code': error_details.get('error_code'),
            'is_retryable': error_details.get('is_retryable', False),
            'recovery_strategy': recovery_strategy,
            'processing_step': processing_step,
            'image_url': image_url
        }
    
    def handle_image_upload_error(self, error: Exception, image_url: str, 
                                upload_stage: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle image upload errors with comprehensive logging and recovery.
        
        Args:
            error: The exception that occurred
            image_url: URL of the image being uploaded
            upload_stage: Stage where the error occurred
            context: Additional context information
            
        Returns:
            dict: Error handling result with recovery suggestions
        """
        error_details = self._extract_error_details(error, {
            'image_url': image_url,
            'upload_stage': upload_stage,
            'context': context or {}
        })
        
        # Log the error with detailed context
        self.error_logger.log_media_upload_error(
            error_details=error_details,
            context={
                'image_url': image_url,
                'upload_stage': upload_stage,
                'error_type': 'image_upload',
                **context or {}
            }
        )
        
        # Update metrics
        self._update_upload_metrics(error_details, upload_stage)
        
        # Determine recovery strategy
        recovery_strategy = self._determine_recovery_strategy(error_details, upload_stage)
        
        # Check if we should alert
        self._check_upload_alert_thresholds(error_details, upload_stage)
        
        return {
            'error_handled': True,
            'error_code': error_details.get('error_code'),
            'is_retryable': error_details.get('is_retryable', False),
            'recovery_strategy': recovery_strategy,
            'upload_stage': upload_stage,
            'image_url': image_url
        }
    
    def retry_with_backoff(self, func: Callable, error_code: str = None, 
                          max_retries: int = None, base_delay: float = None,
                          context: Dict[str, Any] = None) -> Tuple[Any, Dict[str, Any]]:
        """
        Execute a function with exponential backoff retry logic.
        
        Args:
            func: Function to execute
            error_code: Specific error code for retry configuration
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            context: Additional context for logging
            
        Returns:
            tuple: (result, retry_info)
        """
        # Get retry configuration
        retry_config = self.ERROR_CODES.get(error_code, {}) if error_code else {}
        max_retries = max_retries or retry_config.get('max_retries', 3)
        base_delay = base_delay or retry_config.get('base_delay', 2)
        
        retry_info = {
            'attempts': 0,
            'total_delay': 0,
            'errors': [],
            'success': False
        }
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            retry_info['attempts'] = attempt + 1
            
            try:
                start_time = time.time()
                result = func()
                execution_time = time.time() - start_time
                
                retry_info.update({
                    'success': True,
                    'execution_time': execution_time,
                    'final_attempt': attempt + 1
                })
                
                # Log successful retry if there were previous failures
                if attempt > 0:
                    logger.info(f"Function succeeded after {attempt + 1} attempts "
                              f"(total delay: {retry_info['total_delay']:.2f}s)")
                    
                    self._log_retry_success(retry_info, context)
                
                return result, retry_info
                
            except Exception as e:
                last_error = e
                retry_info['errors'].append({
                    'attempt': attempt + 1,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'timestamp': timezone.now().isoformat()
                })
                
                # If this is the last attempt, don't delay
                if attempt >= max_retries:
                    break
                
                # Calculate delay with exponential backoff and jitter
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                retry_info['total_delay'] += delay
                
                logger.warning(f"Attempt {attempt + 1} failed: {e}. "
                             f"Retrying in {delay:.2f} seconds...")
                
                # Log retry attempt
                self._log_retry_attempt(attempt + 1, delay, e, context)
                
                time.sleep(delay)
        
        # All retries failed
        retry_info['final_error'] = str(last_error)
        
        logger.error(f"Function failed after {max_retries + 1} attempts. "
                    f"Total delay: {retry_info['total_delay']:.2f}s. "
                    f"Final error: {last_error}")
        
        self._log_retry_failure(retry_info, context)
        
        # Re-raise the last error
        raise last_error
    
    def _extract_error_details(self, error: Exception, additional_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extract comprehensive error details from an exception.
        
        Args:
            error: The exception to analyze
            additional_context: Additional context information
            
        Returns:
            dict: Comprehensive error details
        """
        error_details = {
            'message': str(error),
            'error_type': type(error).__name__,
            'timestamp': timezone.now().isoformat(),
            'is_retryable': False,
            'error_code': 'UNKNOWN_ERROR'
        }
        
        # Extract specific error information
        if isinstance(error, LinkedInImageError):
            error_details.update({
                'error_code': error.error_code,
                'is_retryable': error.is_retryable,
                'retry_after': error.retry_after,
                'context': error.context
            })
        elif isinstance(error, (ConnectionError, TimeoutError)):
            error_details.update({
                'error_code': 'NETWORK_ERROR',
                'is_retryable': True
            })
        elif 'timeout' in str(error).lower():
            error_details.update({
                'error_code': 'TIMEOUT_ERROR',
                'is_retryable': True
            })
        elif 'too large' in str(error).lower() or 'file size' in str(error).lower():
            error_details.update({
                'error_code': 'IMAGE_TOO_LARGE',
                'is_retryable': True
            })
        elif 'format' in str(error).lower() and 'unsupported' in str(error).lower():
            error_details.update({
                'error_code': 'UNSUPPORTED_FORMAT',
                'is_retryable': True
            })
        elif 'quota' in str(error).lower() or 'limit' in str(error).lower():
            error_details.update({
                'error_code': 'QUOTA_EXCEEDED',
                'is_retryable': True,
                'retry_after': 3600  # 1 hour
            })
        
        # Add additional context
        if additional_context:
            error_details.update(additional_context)
        
        return error_details
    
    def _determine_recovery_strategy(self, error_details: Dict[str, Any], operation_step: str) -> Dict[str, Any]:
        """
        Determine the best recovery strategy for an error.
        
        Args:
            error_details: Comprehensive error details
            operation_step: Step where the error occurred
            
        Returns:
            dict: Recovery strategy information
        """
        error_code = error_details.get('error_code', 'UNKNOWN_ERROR')
        
        recovery_strategy = {
            'strategy_type': 'none',
            'recommended_action': 'manual_intervention',
            'can_retry': error_details.get('is_retryable', False),
            'fallback_available': False
        }
        
        # Determine strategy based on error code and operation step
        if error_code == 'IMAGE_DOWNLOAD_FAILED':
            recovery_strategy.update({
                'strategy_type': 'retry_with_fallback',
                'recommended_action': 'retry_download_then_fallback_image',
                'can_retry': True,
                'fallback_available': True,
                'fallback_type': 'alternative_image'
            })
        
        elif error_code == 'IMAGE_TOO_LARGE':
            recovery_strategy.update({
                'strategy_type': 'process_and_retry',
                'recommended_action': 'resize_image_and_retry',
                'can_retry': True,
                'fallback_available': True,
                'processing_required': 'resize'
            })
        
        elif error_code == 'UNSUPPORTED_FORMAT':
            recovery_strategy.update({
                'strategy_type': 'convert_and_retry',
                'recommended_action': 'convert_format_and_retry',
                'can_retry': True,
                'fallback_available': True,
                'processing_required': 'format_conversion'
            })
        
        elif error_code == 'UPLOAD_TIMEOUT':
            recovery_strategy.update({
                'strategy_type': 'retry_with_delay',
                'recommended_action': 'retry_upload_with_longer_timeout',
                'can_retry': True,
                'fallback_available': True,
                'fallback_type': 'text_only_post'
            })
        
        elif error_code == 'QUOTA_EXCEEDED':
            recovery_strategy.update({
                'strategy_type': 'delayed_retry',
                'recommended_action': 'schedule_retry_after_quota_reset',
                'can_retry': True,
                'fallback_available': True,
                'fallback_type': 'text_only_post',
                'retry_after': error_details.get('retry_after', 3600)
            })
        
        elif error_code in ['NETWORK_ERROR', 'TIMEOUT_ERROR']:
            recovery_strategy.update({
                'strategy_type': 'retry_with_backoff',
                'recommended_action': 'retry_with_exponential_backoff',
                'can_retry': True,
                'fallback_available': True,
                'fallback_type': 'text_only_post'
            })
        
        elif operation_step in ['image_processing', 'image_validation']:
            recovery_strategy.update({
                'strategy_type': 'fallback_to_alternative',
                'recommended_action': 'try_alternative_image_or_text_only',
                'can_retry': False,
                'fallback_available': True,
                'fallback_type': 'alternative_image_or_text_only'
            })
        
        return recovery_strategy
    
    def _update_processing_metrics(self, error_details: Dict[str, Any], processing_step: str):
        """
        Update processing error metrics for monitoring.
        
        Args:
            error_details: Error details
            processing_step: Processing step where error occurred
        """
        metrics_key = f"{self.cache_prefix}_processing_metrics"
        
        current_metrics = cache.get(metrics_key, {
            'total_attempts': 0,
            'total_errors': 0,
            'error_by_step': {},
            'error_by_code': {},
            'last_updated': timezone.now().isoformat()
        })
        
        current_metrics['total_attempts'] += 1
        current_metrics['total_errors'] += 1
        current_metrics['last_updated'] = timezone.now().isoformat()
        
        # Track errors by processing step
        if processing_step not in current_metrics['error_by_step']:
            current_metrics['error_by_step'][processing_step] = 0
        current_metrics['error_by_step'][processing_step] += 1
        
        # Track errors by error code
        error_code = error_details.get('error_code', 'UNKNOWN_ERROR')
        if error_code not in current_metrics['error_by_code']:
            current_metrics['error_by_code'][error_code] = 0
        current_metrics['error_by_code'][error_code] += 1
        
        cache.set(metrics_key, current_metrics, timeout=self.metrics_cache_ttl)
    
    def _update_upload_metrics(self, error_details: Dict[str, Any], upload_stage: str):
        """
        Update upload error metrics for monitoring.
        
        Args:
            error_details: Error details
            upload_stage: Upload stage where error occurred
        """
        metrics_key = f"{self.cache_prefix}_upload_metrics"
        
        current_metrics = cache.get(metrics_key, {
            'total_attempts': 0,
            'total_errors': 0,
            'error_by_stage': {},
            'error_by_code': {},
            'last_updated': timezone.now().isoformat()
        })
        
        current_metrics['total_attempts'] += 1
        current_metrics['total_errors'] += 1
        current_metrics['last_updated'] = timezone.now().isoformat()
        
        # Track errors by upload stage
        if upload_stage not in current_metrics['error_by_stage']:
            current_metrics['error_by_stage'][upload_stage] = 0
        current_metrics['error_by_stage'][upload_stage] += 1
        
        # Track errors by error code
        error_code = error_details.get('error_code', 'UNKNOWN_ERROR')
        if error_code not in current_metrics['error_by_code']:
            current_metrics['error_by_code'][error_code] = 0
        current_metrics['error_by_code'][error_code] += 1
        
        cache.set(metrics_key, current_metrics, timeout=self.metrics_cache_ttl)
    
    def _check_processing_alert_thresholds(self, error_details: Dict[str, Any], processing_step: str):
        """
        Check if processing error rates exceed alert thresholds.
        
        Args:
            error_details: Error details
            processing_step: Processing step where error occurred
        """
        metrics_key = f"{self.cache_prefix}_processing_metrics"
        metrics = cache.get(metrics_key, {})
        
        total_attempts = metrics.get('total_attempts', 0)
        total_errors = metrics.get('total_errors', 0)
        
        if total_attempts > 10:  # Only alert after sufficient data
            error_rate = total_errors / total_attempts
            
            if error_rate > self.performance_thresholds['error_rate_threshold']:
                logger.critical(
                    f"ALERT: High image processing error rate: {error_rate:.2%} "
                    f"({total_errors}/{total_attempts}) in processing step: {processing_step}"
                )
        
        # Check for specific error code frequency
        error_code = error_details.get('error_code', 'UNKNOWN_ERROR')
        error_count = metrics.get('error_by_code', {}).get(error_code, 0)
        
        if error_count >= 5:
            logger.critical(
                f"ALERT: Frequent {error_code} errors in image processing: "
                f"{error_count} occurrences in last hour"
            )
    
    def _check_upload_alert_thresholds(self, error_details: Dict[str, Any], upload_stage: str):
        """
        Check if upload error rates exceed alert thresholds.
        
        Args:
            error_details: Error details
            upload_stage: Upload stage where error occurred
        """
        metrics_key = f"{self.cache_prefix}_upload_metrics"
        metrics = cache.get(metrics_key, {})
        
        total_attempts = metrics.get('total_attempts', 0)
        total_errors = metrics.get('total_errors', 0)
        
        if total_attempts > 10:  # Only alert after sufficient data
            error_rate = total_errors / total_attempts
            
            if error_rate > self.performance_thresholds['error_rate_threshold']:
                logger.critical(
                    f"ALERT: High image upload error rate: {error_rate:.2%} "
                    f"({total_errors}/{total_attempts}) in upload stage: {upload_stage}"
                )
        
        # Check for specific error code frequency
        error_code = error_details.get('error_code', 'UNKNOWN_ERROR')
        error_count = metrics.get('error_by_code', {}).get(error_code, 0)
        
        if error_count >= 3:  # Lower threshold for upload errors
            logger.critical(
                f"ALERT: Frequent {error_code} errors in image upload: "
                f"{error_count} occurrences in last hour"
            )
    
    def _log_retry_attempt(self, attempt: int, delay: float, error: Exception, context: Dict[str, Any] = None):
        """
        Log retry attempt details.
        
        Args:
            attempt: Attempt number
            delay: Delay before retry
            error: Error that triggered retry
            context: Additional context
        """
        logger.info(f"Retry attempt {attempt}: {error} (waiting {delay:.2f}s)")
        
        # Store retry metrics
        retry_key = f"{self.cache_prefix}_retry_metrics"
        retry_metrics = cache.get(retry_key, {'attempts': 0, 'total_delay': 0})
        retry_metrics['attempts'] += 1
        retry_metrics['total_delay'] += delay
        cache.set(retry_key, retry_metrics, timeout=self.metrics_cache_ttl)
    
    def _log_retry_success(self, retry_info: Dict[str, Any], context: Dict[str, Any] = None):
        """
        Log successful retry completion.
        
        Args:
            retry_info: Information about the retry process
            context: Additional context
        """
        logger.info(f"Retry successful after {retry_info['attempts']} attempts "
                   f"(total delay: {retry_info['total_delay']:.2f}s)")
    
    def _log_retry_failure(self, retry_info: Dict[str, Any], context: Dict[str, Any] = None):
        """
        Log retry failure after all attempts exhausted.
        
        Args:
            retry_info: Information about the retry process
            context: Additional context
        """
        logger.error(f"All retry attempts failed: {retry_info['attempts']} attempts, "
                    f"total delay: {retry_info['total_delay']:.2f}s, "
                    f"final error: {retry_info.get('final_error')}")
    
    def get_error_metrics_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive error metrics summary.
        
        Returns:
            dict: Error metrics summary
        """
        processing_metrics = cache.get(f"{self.cache_prefix}_processing_metrics", {})
        upload_metrics = cache.get(f"{self.cache_prefix}_upload_metrics", {})
        retry_metrics = cache.get(f"{self.cache_prefix}_retry_metrics", {})
        
        summary = {
            'generated_at': timezone.now().isoformat(),
            'processing_metrics': processing_metrics,
            'upload_metrics': upload_metrics,
            'retry_metrics': retry_metrics,
            'performance_analysis': self._analyze_performance_metrics(processing_metrics, upload_metrics)
        }
        
        return summary
    
    def _analyze_performance_metrics(self, processing_metrics: Dict[str, Any], 
                                   upload_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze performance metrics and provide insights.
        
        Args:
            processing_metrics: Processing error metrics
            upload_metrics: Upload error metrics
            
        Returns:
            dict: Performance analysis
        """
        analysis = {
            'overall_health': 'good',
            'issues_detected': [],
            'recommendations': []
        }
        
        # Analyze processing metrics
        if processing_metrics:
            total_attempts = processing_metrics.get('total_attempts', 0)
            total_errors = processing_metrics.get('total_errors', 0)
            
            if total_attempts > 0:
                error_rate = total_errors / total_attempts
                
                if error_rate > 0.2:  # 20% error rate
                    analysis['overall_health'] = 'poor'
                    analysis['issues_detected'].append(f'High processing error rate: {error_rate:.2%}')
                    analysis['recommendations'].append('Review image processing pipeline')
                elif error_rate > 0.1:  # 10% error rate
                    analysis['overall_health'] = 'fair'
                    analysis['issues_detected'].append(f'Elevated processing error rate: {error_rate:.2%}')
        
        # Analyze upload metrics
        if upload_metrics:
            total_attempts = upload_metrics.get('total_attempts', 0)
            total_errors = upload_metrics.get('total_errors', 0)
            
            if total_attempts > 0:
                error_rate = total_errors / total_attempts
                
                if error_rate > 0.15:  # 15% error rate
                    analysis['overall_health'] = 'poor'
                    analysis['issues_detected'].append(f'High upload error rate: {error_rate:.2%}')
                    analysis['recommendations'].append('Review LinkedIn API integration')
                elif error_rate > 0.05:  # 5% error rate
                    if analysis['overall_health'] == 'good':
                        analysis['overall_health'] = 'fair'
                    analysis['issues_detected'].append(f'Elevated upload error rate: {error_rate:.2%}')
        
        return analysis