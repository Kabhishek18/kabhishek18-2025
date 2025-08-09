"""
LinkedIn Task Monitoring and Failure Handling Service.

This service provides monitoring capabilities for LinkedIn posting tasks,
including failure analysis, performance metrics, and alerting.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from ..linkedin_models import LinkedInPost, LinkedInConfig


logger = logging.getLogger(__name__)


class LinkedInTaskMonitor:
    """
    Service for monitoring LinkedIn posting tasks and handling failures.
    """
    
    # Cache keys for metrics
    CACHE_KEY_SUCCESS_RATE = 'linkedin_task_success_rate'
    CACHE_KEY_ERROR_COUNTS = 'linkedin_task_error_counts'
    CACHE_KEY_PERFORMANCE_METRICS = 'linkedin_task_performance'
    
    # Cache TTL (1 hour)
    CACHE_TTL = 3600
    
    def __init__(self):
        self.config = LinkedInConfig.get_active_config()
    
    def get_task_statistics(self, hours: int = 24) -> Dict:
        """
        Get comprehensive task statistics for the specified time period.
        
        Args:
            hours: Number of hours to look back for statistics
            
        Returns:
            dict: Task statistics including success rates, error counts, etc.
        """
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # Get all LinkedIn posts from the specified period
        posts = LinkedInPost.objects.filter(created_at__gte=cutoff_time)
        
        total_posts = posts.count()
        successful_posts = posts.filter(status='success').count()
        failed_posts = posts.filter(status='failed').count()
        retrying_posts = posts.filter(status='retrying').count()
        pending_posts = posts.filter(status='pending').count()
        
        # Calculate success rate
        success_rate = (successful_posts / total_posts * 100) if total_posts > 0 else 0
        
        # Get error breakdown
        error_breakdown = self._get_error_breakdown(posts.filter(status__in=['failed', 'retrying']))
        
        # Get performance metrics
        performance_metrics = self._get_performance_metrics(posts.filter(status='success'))
        
        return {
            'period_hours': hours,
            'total_posts': total_posts,
            'successful_posts': successful_posts,
            'failed_posts': failed_posts,
            'retrying_posts': retrying_posts,
            'pending_posts': pending_posts,
            'success_rate': round(success_rate, 2),
            'error_breakdown': error_breakdown,
            'performance_metrics': performance_metrics,
            'generated_at': timezone.now().isoformat()
        }
    
    def _get_error_breakdown(self, failed_posts) -> Dict:
        """
        Analyze error patterns in failed posts.
        
        Args:
            failed_posts: QuerySet of failed/retrying LinkedIn posts
            
        Returns:
            dict: Error breakdown by type and frequency
        """
        error_counts = {}
        error_codes = {}
        
        for post in failed_posts:
            if post.error_message:
                # Categorize errors
                error_category = self._categorize_error(post.error_message, post.error_code)
                error_counts[error_category] = error_counts.get(error_category, 0) + 1
            
            if post.error_code:
                error_codes[post.error_code] = error_codes.get(post.error_code, 0) + 1
        
        return {
            'by_category': error_counts,
            'by_code': error_codes,
            'total_errors': failed_posts.count()
        }
    
    def _categorize_error(self, error_message: str, error_code: str = None) -> str:
        """
        Categorize errors into common types for analysis.
        
        Args:
            error_message: Error message from the failed post
            error_code: Optional error code
            
        Returns:
            str: Error category
        """
        error_message_lower = error_message.lower()
        
        # Authentication errors
        if any(term in error_message_lower for term in ['auth', 'token', 'unauthorized', 'forbidden']):
            return 'authentication'
        
        # Rate limiting
        if any(term in error_message_lower for term in ['rate limit', 'throttle', 'quota']):
            return 'rate_limiting'
        
        # Network errors
        if any(term in error_message_lower for term in ['network', 'timeout', 'connection', 'dns']):
            return 'network'
        
        # Content errors
        if any(term in error_message_lower for term in ['content', 'invalid', 'format', 'length']):
            return 'content_validation'
        
        # Server errors
        if any(term in error_message_lower for term in ['server error', '500', 'internal']):
            return 'server_error'
        
        # API errors
        if error_code:
            return f'api_error_{error_code}'
        
        return 'unknown'
    
    def _get_performance_metrics(self, successful_posts) -> Dict:
        """
        Calculate performance metrics for successful posts.
        
        Args:
            successful_posts: QuerySet of successful LinkedIn posts
            
        Returns:
            dict: Performance metrics
        """
        if not successful_posts.exists():
            return {
                'average_attempts': 0,
                'first_attempt_success_rate': 0,
                'average_posting_time': 0
            }
        
        total_attempts = sum(post.attempt_count for post in successful_posts)
        first_attempt_successes = successful_posts.filter(attempt_count=1).count()
        
        # Calculate average posting time (time from creation to success)
        posting_times = []
        for post in successful_posts:
            if post.posted_at and post.created_at:
                posting_time = (post.posted_at - post.created_at).total_seconds()
                posting_times.append(posting_time)
        
        average_posting_time = sum(posting_times) / len(posting_times) if posting_times else 0
        
        return {
            'average_attempts': round(total_attempts / successful_posts.count(), 2),
            'first_attempt_success_rate': round(first_attempt_successes / successful_posts.count() * 100, 2),
            'average_posting_time_seconds': round(average_posting_time, 2)
        }
    
    def get_health_status(self) -> Dict:
        """
        Get overall health status of LinkedIn integration.
        
        Returns:
            dict: Health status information
        """
        # Check configuration
        config_status = self._check_configuration_health()
        
        # Check recent performance
        recent_stats = self.get_task_statistics(hours=1)  # Last hour
        
        # Determine overall health
        health_score = self._calculate_health_score(config_status, recent_stats)
        
        return {
            'overall_health': self._get_health_level(health_score),
            'health_score': health_score,
            'configuration_status': config_status,
            'recent_performance': recent_stats,
            'recommendations': self._get_health_recommendations(config_status, recent_stats),
            'checked_at': timezone.now().isoformat()
        }
    
    def _check_configuration_health(self) -> Dict:
        """
        Check the health of LinkedIn configuration.
        
        Returns:
            dict: Configuration health status
        """
        if not self.config:
            return {
                'status': 'critical',
                'issues': ['No LinkedIn configuration found'],
                'is_active': False,
                'has_credentials': False,
                'token_valid': False
            }
        
        issues = []
        
        # Check if configuration is active
        if not self.config.is_active:
            issues.append('LinkedIn integration is disabled')
        
        # Check credentials
        if not self.config.has_valid_credentials():
            if self.config.is_token_expired():
                issues.append('Access token has expired')
            else:
                issues.append('Invalid or missing credentials')
        
        # Check token expiration soon
        if self.config.needs_token_refresh(buffer_minutes=60):
            issues.append('Access token expires within 1 hour')
        
        status = 'healthy'
        if issues:
            status = 'warning' if len(issues) == 1 and 'expires within' in issues[0] else 'critical'
        
        return {
            'status': status,
            'issues': issues,
            'is_active': self.config.is_active,
            'has_credentials': bool(self.config.get_access_token()),
            'token_valid': not self.config.is_token_expired(),
            'token_expires_at': self.config.token_expires_at.isoformat() if self.config.token_expires_at else None
        }
    
    def _calculate_health_score(self, config_status: Dict, recent_stats: Dict) -> int:
        """
        Calculate overall health score (0-100).
        
        Args:
            config_status: Configuration health status
            recent_stats: Recent performance statistics
            
        Returns:
            int: Health score from 0 (critical) to 100 (excellent)
        """
        score = 100
        
        # Configuration health (40% of score)
        if config_status['status'] == 'critical':
            score -= 40
        elif config_status['status'] == 'warning':
            score -= 20
        
        # Recent performance (60% of score)
        if recent_stats['total_posts'] > 0:
            success_rate = recent_stats['success_rate']
            
            if success_rate < 50:
                score -= 60
            elif success_rate < 80:
                score -= 30
            elif success_rate < 95:
                score -= 15
        
        return max(0, score)
    
    def _get_health_level(self, score: int) -> str:
        """
        Convert health score to descriptive level.
        
        Args:
            score: Health score (0-100)
            
        Returns:
            str: Health level description
        """
        if score >= 90:
            return 'excellent'
        elif score >= 70:
            return 'good'
        elif score >= 50:
            return 'warning'
        else:
            return 'critical'
    
    def _get_health_recommendations(self, config_status: Dict, recent_stats: Dict) -> List[str]:
        """
        Generate health improvement recommendations.
        
        Args:
            config_status: Configuration health status
            recent_stats: Recent performance statistics
            
        Returns:
            list: List of recommendation strings
        """
        recommendations = []
        
        # Configuration recommendations
        if not config_status['is_active']:
            recommendations.append('Enable LinkedIn integration in configuration')
        
        if not config_status['token_valid']:
            recommendations.append('Refresh LinkedIn access token')
        
        if 'expires within' in str(config_status.get('issues', [])):
            recommendations.append('Schedule token refresh to prevent expiration')
        
        # Performance recommendations
        if recent_stats['total_posts'] > 0:
            success_rate = recent_stats['success_rate']
            
            if success_rate < 80:
                recommendations.append('Investigate frequent posting failures')
            
            error_breakdown = recent_stats.get('error_breakdown', {})
            top_errors = error_breakdown.get('by_category', {})
            
            if 'authentication' in top_errors:
                recommendations.append('Check LinkedIn API credentials and permissions')
            
            if 'rate_limiting' in top_errors:
                recommendations.append('Reduce posting frequency to avoid rate limits')
            
            if 'network' in top_errors:
                recommendations.append('Check network connectivity and DNS resolution')
        
        return recommendations
    
    def alert_on_failures(self, threshold_percentage: float = 50.0, time_window_hours: int = 1) -> Optional[Dict]:
        """
        Check if failure rate exceeds threshold and generate alert.
        
        Args:
            threshold_percentage: Failure rate threshold for alerting
            time_window_hours: Time window to check for failures
            
        Returns:
            dict: Alert information if threshold exceeded, None otherwise
        """
        stats = self.get_task_statistics(hours=time_window_hours)
        
        if stats['total_posts'] == 0:
            return None
        
        failure_rate = 100 - stats['success_rate']
        
        if failure_rate >= threshold_percentage:
            alert = {
                'alert_type': 'high_failure_rate',
                'severity': 'critical' if failure_rate >= 80 else 'warning',
                'failure_rate': failure_rate,
                'threshold': threshold_percentage,
                'time_window_hours': time_window_hours,
                'total_posts': stats['total_posts'],
                'failed_posts': stats['failed_posts'],
                'error_breakdown': stats['error_breakdown'],
                'generated_at': timezone.now().isoformat()
            }
            
            logger.warning(f"LinkedIn posting failure rate alert: {failure_rate}% failures in last {time_window_hours} hours")
            return alert
        
        return None
    
    def get_retry_queue_status(self) -> Dict:
        """
        Get status of posts waiting for retry.
        
        Returns:
            dict: Retry queue status information
        """
        retrying_posts = LinkedInPost.objects.filter(status='retrying')
        ready_for_retry = LinkedInPost.get_posts_ready_for_retry()
        
        # Group by next retry time
        retry_schedule = {}
        for post in retrying_posts:
            if post.next_retry_at:
                retry_time = post.next_retry_at.strftime('%Y-%m-%d %H:%M')
                if retry_time not in retry_schedule:
                    retry_schedule[retry_time] = []
                retry_schedule[retry_time].append({
                    'post_id': post.post.id,
                    'post_title': post.post.title,
                    'attempt_count': post.attempt_count,
                    'error_message': post.error_message[:100] + '...' if len(post.error_message) > 100 else post.error_message
                })
        
        return {
            'total_retrying': retrying_posts.count(),
            'ready_for_retry': ready_for_retry.count(),
            'retry_schedule': retry_schedule,
            'checked_at': timezone.now().isoformat()
        }
    
    def log_task_completion(self, task_result: Dict):
        """
        Log task completion for monitoring and analysis.
        
        Args:
            task_result: Result dictionary from the LinkedIn posting task
        """
        if task_result.get('success'):
            logger.info(
                f"LinkedIn posting task completed successfully: "
                f"post_id={task_result.get('post_id')}, "
                f"duration={task_result.get('task_duration', 0):.2f}s, "
                f"attempts={task_result.get('attempt_count', 1)}"
            )
        else:
            logger.error(
                f"LinkedIn posting task failed: "
                f"post_id={task_result.get('post_id')}, "
                f"error={task_result.get('error', 'Unknown')}, "
                f"duration={task_result.get('task_duration', 0):.2f}s, "
                f"attempts={task_result.get('attempt_count', 1)}"
            )
        
        # Cache recent task results for quick access
        self._cache_task_result(task_result)
    
    def _cache_task_result(self, task_result: Dict):
        """
        Cache task result for quick access to recent performance data.
        
        Args:
            task_result: Result dictionary from the LinkedIn posting task
        """
        cache_key = f"linkedin_task_result_{task_result.get('post_id')}"
        cache.set(cache_key, task_result, timeout=self.CACHE_TTL)
        
        # Update aggregated metrics
        self._update_cached_metrics(task_result)
    
    def _update_cached_metrics(self, task_result: Dict):
        """
        Update cached performance metrics with new task result.
        
        Args:
            task_result: Result dictionary from the LinkedIn posting task
        """
        # This is a simplified implementation
        # In production, you might want to use more sophisticated metrics aggregation
        
        metrics_key = self.CACHE_KEY_PERFORMANCE_METRICS
        current_metrics = cache.get(metrics_key, {
            'total_tasks': 0,
            'successful_tasks': 0,
            'total_duration': 0,
            'last_updated': timezone.now().isoformat()
        })
        
        current_metrics['total_tasks'] += 1
        if task_result.get('success'):
            current_metrics['successful_tasks'] += 1
        
        if 'task_duration' in task_result:
            current_metrics['total_duration'] += task_result['task_duration']
        
        current_metrics['last_updated'] = timezone.now().isoformat()
        
        cache.set(metrics_key, current_metrics, timeout=self.CACHE_TTL)