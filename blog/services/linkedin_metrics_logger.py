"""
Comprehensive metrics logging and monitoring for LinkedIn integration features.

This module provides centralized metrics tracking for hashtag generation,
image posting decisions, and overall LinkedIn integration usage.
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings


logger = logging.getLogger(__name__)


class LinkedInMetricsLogger:
    """
    Centralized metrics logging service for LinkedIn integration features.
    
    Tracks usage patterns, performance metrics, and health indicators
    for hashtag generation and image posting functionality.
    """
    
    def __init__(self):
        self.cache_prefix = 'linkedin_metrics'
        self.cache_ttl = 86400  # 24 hours
    
    def log_feature_usage(self, feature_name: str, post_id: str, success: bool, 
                         execution_time: float, metadata: Optional[Dict] = None):
        """
        Log usage of LinkedIn integration features.
        
        Args:
            feature_name: Name of the feature (hashtag_generation, image_posting, etc.)
            post_id: Blog post ID
            success: Whether the feature executed successfully
            execution_time: Time taken to execute the feature
            metadata: Additional metadata about the feature usage
        """
        try:
            usage_data = {
                'feature_name': feature_name,
                'post_id': post_id,
                'success': success,
                'execution_time_ms': round(execution_time * 1000, 2),
                'timestamp': time.time(),
                'metadata': metadata or {}
            }
            
            # Log appropriate level based on success and performance
            if success:
                if execution_time > 2.0:
                    logger.warning(f"Slow {feature_name} execution for post {post_id}: {execution_time:.3f}s")
                else:
                    logger.debug(f"{feature_name} successful for post {post_id}: {execution_time:.3f}s")
            else:
                logger.warning(f"{feature_name} failed for post {post_id}: {execution_time:.3f}s")
            
            # Cache individual usage data
            cache_key = f"{self.cache_prefix}_usage_{feature_name}_{post_id}"
            cache.set(cache_key, usage_data, timeout=self.cache_ttl)
            
            # Update aggregate metrics
            self._update_feature_aggregate_metrics(feature_name, success, execution_time, metadata)
            
        except Exception as e:
            logger.error(f"Error logging feature usage for {feature_name}: {e}")
    
    def log_configuration_change(self, config_id: int, change_type: str, 
                               old_values: Optional[Dict] = None, new_values: Optional[Dict] = None):
        """
        Log LinkedIn configuration changes for audit and monitoring.
        
        Args:
            config_id: LinkedIn configuration ID
            change_type: Type of change (created, updated, activated, etc.)
            old_values: Previous configuration values
            new_values: New configuration values
        """
        try:
            change_data = {
                'config_id': config_id,
                'change_type': change_type,
                'timestamp': time.time(),
                'old_values': old_values or {},
                'new_values': new_values or {}
            }
            
            # Log configuration changes
            if change_type in ['created', 'activated']:
                logger.info(f"LinkedIn configuration {change_type}: config {config_id}")
            elif change_type in ['updated']:
                logger.info(f"LinkedIn configuration updated: config {config_id}")
                if old_values and new_values:
                    changes = []
                    for key, new_value in new_values.items():
                        old_value = old_values.get(key)
                        if old_value != new_value:
                            changes.append(f"{key}: {old_value} -> {new_value}")
                    if changes:
                        logger.debug(f"Configuration changes for config {config_id}: {', '.join(changes)}")
            elif change_type in ['deactivated', 'deleted']:
                logger.warning(f"LinkedIn configuration {change_type}: config {config_id}")
            
            # Cache configuration change data
            cache_key = f"{self.cache_prefix}_config_change_{config_id}_{int(time.time())}"
            cache.set(cache_key, change_data, timeout=self.cache_ttl)
            
            # Update configuration change metrics
            self._update_config_change_metrics(change_type)
            
        except Exception as e:
            logger.error(f"Error logging configuration change: {e}")
    
    def log_integration_health_check(self, config_id: int, health_status: str, 
                                   checks_performed: List[str], issues_found: List[str]):
        """
        Log LinkedIn integration health check results.
        
        Args:
            config_id: LinkedIn configuration ID
            health_status: Overall health status (healthy, warning, critical)
            checks_performed: List of health checks performed
            issues_found: List of issues discovered during health check
        """
        try:
            health_data = {
                'config_id': config_id,
                'health_status': health_status,
                'checks_performed': checks_performed,
                'issues_found': issues_found,
                'timestamp': time.time()
            }
            
            # Log health check results
            if health_status == 'healthy':
                logger.info(f"LinkedIn integration health check passed for config {config_id}")
            elif health_status == 'warning':
                logger.warning(f"LinkedIn integration health check found warnings for config {config_id}: {issues_found}")
            elif health_status == 'critical':
                logger.error(f"LinkedIn integration health check found critical issues for config {config_id}: {issues_found}")
            
            # Cache health check data
            cache_key = f"{self.cache_prefix}_health_check_{config_id}"
            cache.set(cache_key, health_data, timeout=self.cache_ttl)
            
            # Update health metrics
            self._update_health_metrics(health_status, len(issues_found))
            
        except Exception as e:
            logger.error(f"Error logging health check: {e}")
    
    def _update_feature_aggregate_metrics(self, feature_name: str, success: bool, 
                                        execution_time: float, metadata: Optional[Dict] = None):
        """
        Update aggregate metrics for feature usage.
        
        Args:
            feature_name: Name of the feature
            success: Whether the feature executed successfully
            execution_time: Time taken to execute
            metadata: Additional metadata
        """
        try:
            cache_key = f"{self.cache_prefix}_aggregate_{feature_name}"
            current_metrics = cache.get(cache_key, {
                'total_usage': 0,
                'successful_usage': 0,
                'failed_usage': 0,
                'avg_execution_time': 0,
                'performance_stats': {
                    'fast_executions': 0,  # < 0.5s
                    'normal_executions': 0,  # 0.5s - 2s
                    'slow_executions': 0,  # > 2s
                },
                'last_updated': time.time()
            })
            
            current_metrics['total_usage'] += 1
            current_metrics['last_updated'] = time.time()
            
            if success:
                current_metrics['successful_usage'] += 1
            else:
                current_metrics['failed_usage'] += 1
            
            # Update performance stats
            if execution_time < 0.5:
                current_metrics['performance_stats']['fast_executions'] += 1
            elif execution_time <= 2.0:
                current_metrics['performance_stats']['normal_executions'] += 1
            else:
                current_metrics['performance_stats']['slow_executions'] += 1
            
            # Update average execution time
            if current_metrics['total_usage'] > 0:
                current_avg = current_metrics['avg_execution_time']
                new_avg = ((current_avg * (current_metrics['total_usage'] - 1)) + execution_time) / current_metrics['total_usage']
                current_metrics['avg_execution_time'] = round(new_avg, 3)
            
            cache.set(cache_key, current_metrics, timeout=self.cache_ttl)
            
            # Log periodic statistics
            if current_metrics['total_usage'] % 50 == 0:  # Every 50 usages
                success_rate = (current_metrics['successful_usage'] / current_metrics['total_usage']) * 100
                slow_percentage = (current_metrics['performance_stats']['slow_executions'] / current_metrics['total_usage']) * 100
                
                logger.info(f"{feature_name} usage stats: {current_metrics['total_usage']} total, "
                          f"{success_rate:.1f}% success rate, {slow_percentage:.1f}% slow executions, "
                          f"avg {current_metrics['avg_execution_time']:.3f}s execution time")
            
        except Exception as e:
            logger.error(f"Error updating feature aggregate metrics for {feature_name}: {e}")
    
    def _update_config_change_metrics(self, change_type: str):
        """
        Update metrics for configuration changes.
        
        Args:
            change_type: Type of configuration change
        """
        try:
            cache_key = f"{self.cache_prefix}_config_changes"
            current_metrics = cache.get(cache_key, {
                'total_changes': 0,
                'change_types': {},
                'last_updated': time.time()
            })
            
            current_metrics['total_changes'] += 1
            current_metrics['change_types'][change_type] = current_metrics['change_types'].get(change_type, 0) + 1
            current_metrics['last_updated'] = time.time()
            
            cache.set(cache_key, current_metrics, timeout=self.cache_ttl)
            
        except Exception as e:
            logger.error(f"Error updating config change metrics: {e}")
    
    def _update_health_metrics(self, health_status: str, issue_count: int):
        """
        Update health check metrics.
        
        Args:
            health_status: Health status result
            issue_count: Number of issues found
        """
        try:
            cache_key = f"{self.cache_prefix}_health_metrics"
            current_metrics = cache.get(cache_key, {
                'total_checks': 0,
                'health_statuses': {},
                'total_issues_found': 0,
                'last_updated': time.time()
            })
            
            current_metrics['total_checks'] += 1
            current_metrics['health_statuses'][health_status] = current_metrics['health_statuses'].get(health_status, 0) + 1
            current_metrics['total_issues_found'] += issue_count
            current_metrics['last_updated'] = time.time()
            
            cache.set(cache_key, current_metrics, timeout=self.cache_ttl)
            
        except Exception as e:
            logger.error(f"Error updating health metrics: {e}")
    
    def get_comprehensive_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of all LinkedIn integration metrics.
        
        Returns:
            dict: Comprehensive metrics summary
        """
        try:
            summary = {
                'generated_at': timezone.now().isoformat(),
                'features': {},
                'configuration': {},
                'health': {},
                'overall_status': 'unknown'
            }
            
            # Get feature metrics
            features = ['hashtag_generation', 'image_posting']
            for feature in features:
                cache_key = f"{self.cache_prefix}_aggregate_{feature}"
                feature_metrics = cache.get(cache_key, {})
                if feature_metrics:
                    summary['features'][feature] = self._format_feature_metrics(feature_metrics)
            
            # Get configuration metrics
            config_cache_key = f"{self.cache_prefix}_config_changes"
            config_metrics = cache.get(config_cache_key, {})
            if config_metrics:
                summary['configuration'] = config_metrics
            
            # Get health metrics
            health_cache_key = f"{self.cache_prefix}_health_metrics"
            health_metrics = cache.get(health_cache_key, {})
            if health_metrics:
                summary['health'] = health_metrics
            
            # Assess overall status
            summary['overall_status'] = self._assess_overall_health(summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting comprehensive metrics summary: {e}")
            return {'error': str(e), 'generated_at': timezone.now().isoformat()}
    
    def _format_feature_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format feature metrics for display.
        
        Args:
            metrics: Raw feature metrics
            
        Returns:
            dict: Formatted metrics
        """
        total_usage = metrics.get('total_usage', 0)
        if total_usage == 0:
            return {'status': 'no_usage', 'message': 'No usage recorded'}
        
        successful_usage = metrics.get('successful_usage', 0)
        success_rate = (successful_usage / total_usage) * 100 if total_usage > 0 else 0
        
        performance_stats = metrics.get('performance_stats', {})
        slow_executions = performance_stats.get('slow_executions', 0)
        slow_percentage = (slow_executions / total_usage) * 100 if total_usage > 0 else 0
        
        return {
            'total_usage': total_usage,
            'success_rate_percent': round(success_rate, 1),
            'avg_execution_time_seconds': metrics.get('avg_execution_time', 0),
            'slow_executions_percent': round(slow_percentage, 1),
            'performance_distribution': performance_stats,
            'last_updated': metrics.get('last_updated')
        }
    
    def _assess_overall_health(self, summary: Dict[str, Any]) -> str:
        """
        Assess overall health of LinkedIn integration based on all metrics.
        
        Args:
            summary: Comprehensive metrics summary
            
        Returns:
            str: Overall health status
        """
        try:
            health_scores = []
            
            # Assess feature health
            for feature_name, feature_metrics in summary.get('features', {}).items():
                if isinstance(feature_metrics, dict) and 'success_rate_percent' in feature_metrics:
                    success_rate = feature_metrics['success_rate_percent']
                    slow_percentage = feature_metrics.get('slow_executions_percent', 0)
                    
                    if success_rate >= 90 and slow_percentage <= 10:
                        health_scores.append('healthy')
                    elif success_rate >= 70 and slow_percentage <= 25:
                        health_scores.append('warning')
                    else:
                        health_scores.append('critical')
            
            # Assess health check results
            health_metrics = summary.get('health', {})
            if health_metrics:
                health_statuses = health_metrics.get('health_statuses', {})
                total_checks = health_metrics.get('total_checks', 0)
                
                if total_checks > 0:
                    critical_checks = health_statuses.get('critical', 0)
                    warning_checks = health_statuses.get('warning', 0)
                    
                    critical_percentage = (critical_checks / total_checks) * 100
                    warning_percentage = (warning_checks / total_checks) * 100
                    
                    if critical_percentage > 25:
                        health_scores.append('critical')
                    elif warning_percentage > 50:
                        health_scores.append('warning')
                    else:
                        health_scores.append('healthy')
            
            # Determine overall health
            if not health_scores:
                return 'insufficient_data'
            elif 'critical' in health_scores:
                return 'critical'
            elif 'warning' in health_scores:
                return 'warning'
            else:
                return 'healthy'
                
        except Exception as e:
            logger.error(f"Error assessing overall health: {e}")
            return 'unknown'
    
    def reset_metrics(self, feature_name: Optional[str] = None):
        """
        Reset metrics for a specific feature or all features.
        
        Args:
            feature_name: Name of feature to reset, or None for all features
        """
        try:
            if feature_name:
                # Reset specific feature metrics
                cache_key = f"{self.cache_prefix}_aggregate_{feature_name}"
                cache.delete(cache_key)
                logger.info(f"Reset metrics for feature: {feature_name}")
            else:
                # Reset all LinkedIn metrics
                cache_keys = [
                    f"{self.cache_prefix}_aggregate_hashtag_generation",
                    f"{self.cache_prefix}_aggregate_image_posting",
                    f"{self.cache_prefix}_config_changes",
                    f"{self.cache_prefix}_health_metrics"
                ]
                
                for key in cache_keys:
                    cache.delete(key)
                
                logger.info("Reset all LinkedIn integration metrics")
                
        except Exception as e:
            logger.error(f"Error resetting metrics: {e}")


# Global metrics logger instance
linkedin_metrics_logger = LinkedInMetricsLogger()