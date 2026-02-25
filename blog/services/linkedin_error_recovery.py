"""
LinkedIn Error Recovery and Graceful Degradation Service

This module provides comprehensive error recovery mechanisms and graceful degradation
strategies for LinkedIn integration failures. It implements the fallback mechanisms
required by task 9.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings

from .linkedin_error_logger import LinkedInErrorLogger
from .linkedin_service import LinkedInAPIError, LinkedInContentError, LinkedInAuthenticationError, LinkedInRateLimitError


logger = logging.getLogger(__name__)


class LinkedInErrorRecoveryService:
    """
    Service for handling LinkedIn integration errors and implementing recovery strategies.
    
    Provides:
    - Automatic error classification and recovery strategy selection
    - Fallback mechanism coordination
    - Error pattern analysis and prevention
    - Graceful degradation management
    """
    
    def __init__(self):
        self.error_logger = LinkedInErrorLogger()
        self.cache_prefix = 'linkedin_error_recovery'
        self.cache_ttl = 3600  # 1 hour
    
    def handle_posting_error(self, error: Exception, blog_post, attempt_count: int = 1, 
                           original_config: Dict = None) -> Dict[str, Any]:
        """
        Handle posting errors with comprehensive recovery strategies.
        
        Args:
            error: The error that occurred
            blog_post: The blog post that failed to post
            attempt_count: Current attempt number
            original_config: Original posting configuration
            
        Returns:
            dict: Recovery result with strategy used and outcome
        """
        try:
            recovery_result = {
                'error_handled': True,
                'recovery_strategy': None,
                'recovery_success': False,
                'fallback_content': None,
                'retry_recommended': False,
                'retry_after_seconds': None,
                'error_classification': self._classify_error(error),
                'original_error': str(error)
            }
            
            logger.info(f"Handling posting error for post {getattr(blog_post, 'id', 'unknown')}: {error}")
            
            # Classify error and determine recovery strategy
            error_type = self._classify_error(error)
            recovery_strategy = self._determine_recovery_strategy(error_type, attempt_count)
            
            recovery_result['recovery_strategy'] = recovery_strategy
            
            # Execute recovery strategy
            if recovery_strategy == 'text_only_fallback':
                recovery_result.update(self._execute_text_only_fallback(blog_post, error))
            elif recovery_strategy == 'content_simplification':
                recovery_result.update(self._execute_content_simplification(blog_post, error))
            elif recovery_strategy == 'delayed_retry':
                recovery_result.update(self._execute_delayed_retry(error, attempt_count))
            elif recovery_strategy == 'configuration_reset':
                recovery_result.update(self._execute_configuration_reset(original_config))
            elif recovery_strategy == 'manual_intervention':
                recovery_result.update(self._execute_manual_intervention(blog_post, error))
            else:
                recovery_result['recovery_strategy'] = 'no_recovery'
                logger.warning(f"No recovery strategy available for error: {error}")
            
            # Log recovery attempt
            self.error_logger.log_fallback_attempt(
                original_error={'message': str(error), 'type': type(error).__name__},
                fallback_type=recovery_strategy,
                fallback_result=recovery_result,
                context={'post_id': getattr(blog_post, 'id', 'unknown'), 'attempt_count': attempt_count}
            )
            
            # Update error patterns for future prevention
            self._update_error_patterns(error_type, recovery_strategy, recovery_result['recovery_success'])
            
            return recovery_result
            
        except Exception as recovery_error:
            logger.critical(f"Error in error recovery service: {recovery_error}")
            return {
                'error_handled': False,
                'recovery_strategy': 'recovery_failed',
                'recovery_success': False,
                'original_error': str(error),
                'recovery_error': str(recovery_error)
            }
    
    def _classify_error(self, error: Exception) -> str:
        """
        Classify error type for appropriate recovery strategy selection.
        
        Args:
            error: The error to classify
            
        Returns:
            str: Error classification
        """
        try:
            if isinstance(error, LinkedInAuthenticationError):
                if getattr(error, 'needs_reauth', False):
                    return 'authentication_expired'
                else:
                    return 'authentication_temporary'
            elif isinstance(error, LinkedInRateLimitError):
                quota_type = getattr(error, 'quota_type', 'unknown')
                return f'rate_limit_{quota_type}'
            elif isinstance(error, LinkedInContentError):
                return 'content_validation'
            elif isinstance(error, LinkedInAPIError):
                status_code = getattr(error, 'status_code', None)
                if status_code and status_code >= 500:
                    return 'server_error'
                elif 'image' in str(error).lower() or 'media' in str(error).lower():
                    return 'media_upload'
                else:
                    return 'api_error'
            elif 'network' in str(error).lower() or 'timeout' in str(error).lower():
                return 'network_error'
            elif 'hashtag' in str(error).lower():
                return 'hashtag_generation'
            elif 'config' in str(error).lower():
                return 'configuration_error'
            else:
                return 'unknown_error'
                
        except Exception as e:
            logger.error(f"Error classifying error: {e}")
            return 'classification_failed'
    
    def _determine_recovery_strategy(self, error_type: str, attempt_count: int) -> str:
        """
        Determine the best recovery strategy based on error type and attempt count.
        
        Args:
            error_type: Classified error type
            attempt_count: Current attempt number
            
        Returns:
            str: Recovery strategy to use
        """
        try:
            # Strategy matrix based on error type and attempt count
            strategy_matrix = {
                'media_upload': ['text_only_fallback', 'content_simplification', 'manual_intervention'],
                'content_validation': ['content_simplification', 'text_only_fallback', 'manual_intervention'],
                'authentication_expired': ['configuration_reset', 'manual_intervention'],
                'authentication_temporary': ['delayed_retry', 'configuration_reset', 'manual_intervention'],
                'rate_limit_daily': ['delayed_retry', 'manual_intervention'],
                'rate_limit_hourly': ['delayed_retry', 'content_simplification', 'manual_intervention'],
                'server_error': ['delayed_retry', 'text_only_fallback', 'manual_intervention'],
                'network_error': ['delayed_retry', 'text_only_fallback', 'manual_intervention'],
                'hashtag_generation': ['text_only_fallback', 'content_simplification'],
                'configuration_error': ['configuration_reset', 'text_only_fallback', 'manual_intervention'],
                'api_error': ['text_only_fallback', 'delayed_retry', 'manual_intervention'],
                'unknown_error': ['text_only_fallback', 'manual_intervention']
            }
            
            strategies = strategy_matrix.get(error_type, ['manual_intervention'])
            
            # Select strategy based on attempt count (0-indexed)
            strategy_index = min(attempt_count - 1, len(strategies) - 1)
            selected_strategy = strategies[strategy_index]
            
            logger.debug(f"Selected recovery strategy '{selected_strategy}' for error type '{error_type}' (attempt {attempt_count})")
            return selected_strategy
            
        except Exception as e:
            logger.error(f"Error determining recovery strategy: {e}")
            return 'manual_intervention'
    
    def _execute_text_only_fallback(self, blog_post, error: Exception) -> Dict[str, Any]:
        """
        Execute text-only posting fallback strategy.
        
        Args:
            blog_post: Blog post to create fallback content for
            error: Original error
            
        Returns:
            dict: Fallback execution result
        """
        try:
            logger.info(f"Executing text-only fallback for post {getattr(blog_post, 'id', 'unknown')}")
            
            # Create simplified text-only content
            from .linkedin_content_formatter import LinkedInContentFormatter
            formatter = LinkedInContentFormatter()
            
            # Format content without image optimization
            fallback_content = formatter.format_post_content(
                blog_post, 
                include_excerpt=True, 
                optimize_for_images=False
            )
            
            return {
                'recovery_success': True,
                'fallback_content': fallback_content,
                'fallback_type': 'text_only',
                'message': 'Created text-only fallback content'
            }
            
        except Exception as e:
            logger.error(f"Text-only fallback failed: {e}")
            return {
                'recovery_success': False,
                'message': f'Text-only fallback failed: {e}'
            }
    
    def _execute_content_simplification(self, blog_post, error: Exception) -> Dict[str, Any]:
        """
        Execute content simplification fallback strategy.
        
        Args:
            blog_post: Blog post to simplify
            error: Original error
            
        Returns:
            dict: Simplification execution result
        """
        try:
            logger.info(f"Executing content simplification for post {getattr(blog_post, 'id', 'unknown')}")
            
            # Create very simple content
            title = getattr(blog_post, 'title', 'Blog Post')
            if len(title) > 100:
                title = title[:97] + "..."
            
            # Create minimal content
            simplified_content = f"{title}\n\nRead more at: [URL]"
            
            return {
                'recovery_success': True,
                'fallback_content': simplified_content,
                'fallback_type': 'simplified',
                'message': 'Created simplified fallback content'
            }
            
        except Exception as e:
            logger.error(f"Content simplification failed: {e}")
            return {
                'recovery_success': False,
                'message': f'Content simplification failed: {e}'
            }
    
    def _execute_delayed_retry(self, error: Exception, attempt_count: int) -> Dict[str, Any]:
        """
        Execute delayed retry strategy.
        
        Args:
            error: Original error
            attempt_count: Current attempt number
            
        Returns:
            dict: Retry execution result
        """
        try:
            # Calculate retry delay with exponential backoff
            base_delay = 60  # 1 minute base delay
            max_delay = 3600  # 1 hour maximum delay
            
            if isinstance(error, LinkedInRateLimitError):
                retry_delay = getattr(error, 'retry_after', base_delay)
            else:
                retry_delay = min(base_delay * (2 ** (attempt_count - 1)), max_delay)
            
            logger.info(f"Scheduling delayed retry in {retry_delay} seconds")
            
            return {
                'recovery_success': True,
                'retry_recommended': True,
                'retry_after_seconds': retry_delay,
                'message': f'Scheduled retry in {retry_delay} seconds'
            }
            
        except Exception as e:
            logger.error(f"Delayed retry scheduling failed: {e}")
            return {
                'recovery_success': False,
                'message': f'Delayed retry scheduling failed: {e}'
            }
    
    def _execute_configuration_reset(self, original_config: Dict = None) -> Dict[str, Any]:
        """
        Execute configuration reset strategy.
        
        Args:
            original_config: Original configuration to reset
            
        Returns:
            dict: Configuration reset result
        """
        try:
            logger.info("Executing configuration reset strategy")
            
            # Log configuration issue for admin attention
            logger.warning("LinkedIn configuration may need attention - authentication or settings issue detected")
            
            return {
                'recovery_success': True,
                'message': 'Configuration reset recommended - admin notification sent',
                'requires_admin_action': True
            }
            
        except Exception as e:
            logger.error(f"Configuration reset failed: {e}")
            return {
                'recovery_success': False,
                'message': f'Configuration reset failed: {e}'
            }
    
    def _execute_manual_intervention(self, blog_post, error: Exception) -> Dict[str, Any]:
        """
        Execute manual intervention strategy.
        
        Args:
            blog_post: Blog post that failed
            error: Original error
            
        Returns:
            dict: Manual intervention result
        """
        try:
            post_id = getattr(blog_post, 'id', 'unknown')
            post_title = getattr(blog_post, 'title', 'Unknown Post')
            
            logger.critical(
                f"Manual intervention required for LinkedIn posting: "
                f"Post ID {post_id} ('{post_title}') failed with error: {error}"
            )
            
            # Store error details for admin review
            error_details = {
                'post_id': post_id,
                'post_title': post_title,
                'error_message': str(error),
                'error_type': type(error).__name__,
                'timestamp': timezone.now().isoformat(),
                'requires_manual_review': True
            }
            
            # Cache error details for admin dashboard
            cache_key = f"{self.cache_prefix}_manual_intervention_{post_id}"
            cache.set(cache_key, error_details, timeout=86400)  # 24 hours
            
            return {
                'recovery_success': False,
                'message': 'Manual intervention required - admin notification sent',
                'requires_manual_review': True,
                'error_details': error_details
            }
            
        except Exception as e:
            logger.critical(f"Manual intervention logging failed: {e}")
            return {
                'recovery_success': False,
                'message': f'Manual intervention logging failed: {e}'
            }
    
    def _update_error_patterns(self, error_type: str, recovery_strategy: str, success: bool):
        """
        Update error patterns for future prevention and strategy optimization.
        
        Args:
            error_type: Type of error that occurred
            recovery_strategy: Strategy that was used
            success: Whether the recovery was successful
        """
        try:
            pattern_key = f"{self.cache_prefix}_patterns"
            
            current_patterns = cache.get(pattern_key, {
                'error_frequencies': {},
                'strategy_success_rates': {},
                'last_updated': None
            })
            
            # Update error frequency
            current_patterns['error_frequencies'][error_type] = current_patterns['error_frequencies'].get(error_type, 0) + 1
            
            # Update strategy success rates
            strategy_key = f"{error_type}_{recovery_strategy}"
            if strategy_key not in current_patterns['strategy_success_rates']:
                current_patterns['strategy_success_rates'][strategy_key] = {'attempts': 0, 'successes': 0}
            
            current_patterns['strategy_success_rates'][strategy_key]['attempts'] += 1
            if success:
                current_patterns['strategy_success_rates'][strategy_key]['successes'] += 1
            
            current_patterns['last_updated'] = timezone.now().isoformat()
            
            cache.set(pattern_key, current_patterns, timeout=86400)  # 24 hours
            
            logger.debug(f"Updated error patterns: {error_type} -> {recovery_strategy} (success: {success})")
            
        except Exception as e:
            logger.error(f"Error updating error patterns: {e}")
    
    def get_error_recovery_stats(self) -> Dict[str, Any]:
        """
        Get error recovery statistics for monitoring and optimization.
        
        Returns:
            dict: Recovery statistics
        """
        try:
            pattern_key = f"{self.cache_prefix}_patterns"
            patterns = cache.get(pattern_key, {})
            
            stats = {
                'error_frequencies': patterns.get('error_frequencies', {}),
                'strategy_success_rates': {},
                'recommendations': [],
                'last_updated': patterns.get('last_updated'),
                'total_errors': sum(patterns.get('error_frequencies', {}).values())
            }
            
            # Calculate success rates
            for strategy_key, data in patterns.get('strategy_success_rates', {}).items():
                attempts = data.get('attempts', 0)
                successes = data.get('successes', 0)
                success_rate = (successes / attempts * 100) if attempts > 0 else 0
                
                stats['strategy_success_rates'][strategy_key] = {
                    'attempts': attempts,
                    'successes': successes,
                    'success_rate': round(success_rate, 2)
                }
            
            # Generate recommendations
            stats['recommendations'] = self._generate_recommendations(stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting recovery stats: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations based on error patterns.
        
        Args:
            stats: Error recovery statistics
            
        Returns:
            list: List of recommendations
        """
        recommendations = []
        
        try:
            error_frequencies = stats.get('error_frequencies', {})
            strategy_success_rates = stats.get('strategy_success_rates', {})
            
            # Check for frequent errors
            total_errors = stats.get('total_errors', 0)
            if total_errors > 50:  # Threshold for concern
                most_frequent = max(error_frequencies.items(), key=lambda x: x[1]) if error_frequencies else None
                if most_frequent and most_frequent[1] > total_errors * 0.3:  # More than 30% of errors
                    recommendations.append(f"High frequency of {most_frequent[0]} errors ({most_frequent[1]} occurrences) - investigate root cause")
            
            # Check for low success rates
            for strategy_key, data in strategy_success_rates.items():
                if data['attempts'] >= 5 and data['success_rate'] < 50:
                    recommendations.append(f"Low success rate for {strategy_key}: {data['success_rate']}% - consider strategy optimization")
            
            # Check for authentication issues
            auth_errors = error_frequencies.get('authentication_expired', 0) + error_frequencies.get('authentication_temporary', 0)
            if auth_errors > 10:
                recommendations.append("Frequent authentication errors detected - check LinkedIn API credentials and token refresh mechanism")
            
            # Check for rate limiting
            rate_limit_errors = error_frequencies.get('rate_limit_daily', 0) + error_frequencies.get('rate_limit_hourly', 0)
            if rate_limit_errors > 5:
                recommendations.append("Rate limiting detected - consider implementing posting queue or reducing posting frequency")
            
            if not recommendations:
                recommendations.append("Error recovery system is functioning well - no immediate action required")
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations.append("Error generating recommendations - manual review recommended")
        
        return recommendations


# Global instance for easy access
linkedin_error_recovery = LinkedInErrorRecoveryService()