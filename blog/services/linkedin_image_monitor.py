"""
LinkedIn Image Processing Monitoring Service.

This service provides comprehensive monitoring and dashboard functionality for
LinkedIn image integration, including success rates, performance metrics,
and real-time status tracking.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Q
from django.conf import settings
from ..linkedin_models import LinkedInPost
from .linkedin_error_logger import LinkedInErrorLogger


logger = logging.getLogger(__name__)


class LinkedInImageMonitor:
    """
    Comprehensive monitoring service for LinkedIn image processing.
    
    Provides:
    - Real-time success rate tracking
    - Performance metrics collection
    - Dashboard data aggregation
    - Alert threshold monitoring
    - Historical trend analysis
    """
    
    def __init__(self):
        self.cache_prefix = 'linkedin_image_monitor'
        self.cache_ttl = 3600  # 1 hour
        self.error_logger = LinkedInErrorLogger()
        
        # Monitoring thresholds
        self.thresholds = {
            'success_rate_warning': 0.85,    # 85%
            'success_rate_critical': 0.70,   # 70%
            'processing_time_warning': 30,    # 30 seconds
            'processing_time_critical': 60,   # 60 seconds
            'error_rate_warning': 0.10,      # 10%
            'error_rate_critical': 0.20,     # 20%
        }
    
    def record_image_processing_attempt(self, post_id: int, image_url: str, 
                                      processing_step: str, context: Dict[str, Any] = None):
        """
        Record an image processing attempt for monitoring.
        
        Args:
            post_id: Blog post ID
            image_url: URL of the image being processed
            processing_step: Current processing step
            context: Additional context information
        """
        attempt_data = {
            'post_id': post_id,
            'image_url': image_url,
            'processing_step': processing_step,
            'timestamp': timezone.now().isoformat(),
            'status': 'in_progress',
            'context': context or {}
        }
        
        # Store attempt data
        attempt_key = f"{self.cache_prefix}_attempt_{post_id}_{int(timezone.now().timestamp())}"
        cache.set(attempt_key, attempt_data, timeout=self.cache_ttl)
        
        # Update step-specific metrics
        self._update_step_metrics(processing_step, 'attempt')
        
        logger.debug(f"Recorded image processing attempt for post {post_id}, step: {processing_step}")
    
    def record_image_processing_success(self, post_id: int, image_url: str, 
                                      processing_step: str, processing_time: float,
                                      result_data: Dict[str, Any] = None):
        """
        Record a successful image processing completion.
        
        Args:
            post_id: Blog post ID
            image_url: URL of the processed image
            processing_step: Completed processing step
            processing_time: Time taken for processing in seconds
            result_data: Additional result information
        """
        success_data = {
            'post_id': post_id,
            'image_url': image_url,
            'processing_step': processing_step,
            'processing_time': processing_time,
            'timestamp': timezone.now().isoformat(),
            'status': 'success',
            'result_data': result_data or {}
        }
        
        # Store success data
        success_key = f"{self.cache_prefix}_success_{post_id}_{int(timezone.now().timestamp())}"
        cache.set(success_key, success_data, timeout=self.cache_ttl)
        
        # Update metrics
        self._update_step_metrics(processing_step, 'success')
        self._update_performance_metrics(processing_step, processing_time)
        
        # Check performance thresholds
        self._check_performance_thresholds(processing_step, processing_time)
        
        logger.debug(f"Recorded image processing success for post {post_id}, "
                    f"step: {processing_step}, time: {processing_time:.2f}s")
    
    def record_image_processing_failure(self, post_id: int, image_url: str, 
                                      processing_step: str, error: Exception,
                                      processing_time: float = None,
                                      error_context: Dict[str, Any] = None):
        """
        Record an image processing failure.
        
        Args:
            post_id: Blog post ID
            image_url: URL of the image that failed
            processing_step: Processing step where failure occurred
            error: The exception that occurred
            processing_time: Time taken before failure (if available)
            error_context: Additional error context
        """
        failure_data = {
            'post_id': post_id,
            'image_url': image_url,
            'processing_step': processing_step,
            'error_message': str(error),
            'error_type': type(error).__name__,
            'processing_time': processing_time,
            'timestamp': timezone.now().isoformat(),
            'status': 'failure',
            'error_context': error_context or {}
        }
        
        # Store failure data
        failure_key = f"{self.cache_prefix}_failure_{post_id}_{int(timezone.now().timestamp())}"
        cache.set(failure_key, failure_data, timeout=self.cache_ttl)
        
        # Update metrics
        self._update_step_metrics(processing_step, 'failure')
        
        if processing_time:
            self._update_performance_metrics(processing_step, processing_time)
        
        # Check error rate thresholds
        self._check_error_rate_thresholds(processing_step)
        
        logger.warning(f"Recorded image processing failure for post {post_id}, "
                      f"step: {processing_step}, error: {error}")
    
    def record_image_upload_attempt(self, post_id: int, image_url: str, 
                                   upload_stage: str, context: Dict[str, Any] = None):
        """
        Record an image upload attempt for monitoring.
        
        Args:
            post_id: Blog post ID
            image_url: URL of the image being uploaded
            upload_stage: Current upload stage
            context: Additional context information
        """
        attempt_data = {
            'post_id': post_id,
            'image_url': image_url,
            'upload_stage': upload_stage,
            'timestamp': timezone.now().isoformat(),
            'status': 'in_progress',
            'context': context or {}
        }
        
        # Store attempt data
        attempt_key = f"{self.cache_prefix}_upload_attempt_{post_id}_{int(timezone.now().timestamp())}"
        cache.set(attempt_key, attempt_data, timeout=self.cache_ttl)
        
        # Update upload metrics
        self._update_upload_metrics(upload_stage, 'attempt')
        
        logger.debug(f"Recorded image upload attempt for post {post_id}, stage: {upload_stage}")
    
    def record_image_upload_success(self, post_id: int, image_url: str, 
                                   upload_stage: str, upload_time: float,
                                   media_id: str = None, result_data: Dict[str, Any] = None):
        """
        Record a successful image upload completion.
        
        Args:
            post_id: Blog post ID
            image_url: URL of the uploaded image
            upload_stage: Completed upload stage
            upload_time: Time taken for upload in seconds
            media_id: LinkedIn media ID (if available)
            result_data: Additional result information
        """
        success_data = {
            'post_id': post_id,
            'image_url': image_url,
            'upload_stage': upload_stage,
            'upload_time': upload_time,
            'media_id': media_id,
            'timestamp': timezone.now().isoformat(),
            'status': 'success',
            'result_data': result_data or {}
        }
        
        # Store success data
        success_key = f"{self.cache_prefix}_upload_success_{post_id}_{int(timezone.now().timestamp())}"
        cache.set(success_key, success_data, timeout=self.cache_ttl)
        
        # Update metrics
        self._update_upload_metrics(upload_stage, 'success')
        self._update_upload_performance_metrics(upload_stage, upload_time)
        
        # Check performance thresholds
        self._check_upload_performance_thresholds(upload_stage, upload_time)
        
        logger.debug(f"Recorded image upload success for post {post_id}, "
                    f"stage: {upload_stage}, time: {upload_time:.2f}s, media_id: {media_id}")
    
    def record_image_upload_failure(self, post_id: int, image_url: str, 
                                   upload_stage: str, error: Exception,
                                   upload_time: float = None,
                                   error_context: Dict[str, Any] = None):
        """
        Record an image upload failure.
        
        Args:
            post_id: Blog post ID
            image_url: URL of the image that failed to upload
            upload_stage: Upload stage where failure occurred
            error: The exception that occurred
            upload_time: Time taken before failure (if available)
            error_context: Additional error context
        """
        failure_data = {
            'post_id': post_id,
            'image_url': image_url,
            'upload_stage': upload_stage,
            'error_message': str(error),
            'error_type': type(error).__name__,
            'upload_time': upload_time,
            'timestamp': timezone.now().isoformat(),
            'status': 'failure',
            'error_context': error_context or {}
        }
        
        # Store failure data
        failure_key = f"{self.cache_prefix}_upload_failure_{post_id}_{int(timezone.now().timestamp())}"
        cache.set(failure_key, failure_data, timeout=self.cache_ttl)
        
        # Update metrics
        self._update_upload_metrics(upload_stage, 'failure')
        
        if upload_time:
            self._update_upload_performance_metrics(upload_stage, upload_time)
        
        # Check error rate thresholds
        self._check_upload_error_rate_thresholds(upload_stage)
        
        logger.warning(f"Recorded image upload failure for post {post_id}, "
                      f"stage: {upload_stage}, error: {error}")
    
    def get_dashboard_data(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            dict: Dashboard data with metrics and statistics
        """
        dashboard_data = {
            'generated_at': timezone.now().isoformat(),
            'period_hours': hours,
            'overview': self._get_overview_metrics(),
            'processing_metrics': self._get_processing_metrics(),
            'upload_metrics': self._get_upload_metrics(),
            'performance_metrics': self._get_performance_metrics(),
            'error_analysis': self._get_error_analysis(),
            'trends': self._get_trend_analysis(hours),
            'alerts': self._get_active_alerts(),
            'recommendations': self._get_recommendations()
        }
        
        return dashboard_data
    
    def get_success_rates(self) -> Dict[str, float]:
        """
        Get current success rates for different operations.
        
        Returns:
            dict: Success rates by operation type
        """
        processing_metrics = cache.get(f"{self.cache_prefix}_processing_metrics", {})
        upload_metrics = cache.get(f"{self.cache_prefix}_upload_metrics", {})
        
        success_rates = {}
        
        # Calculate processing success rates
        for step, metrics in processing_metrics.items():
            attempts = metrics.get('attempts', 0)
            successes = metrics.get('successes', 0)
            
            if attempts > 0:
                success_rates[f'processing_{step}'] = successes / attempts
            else:
                success_rates[f'processing_{step}'] = 0.0
        
        # Calculate upload success rates
        for stage, metrics in upload_metrics.items():
            attempts = metrics.get('attempts', 0)
            successes = metrics.get('successes', 0)
            
            if attempts > 0:
                success_rates[f'upload_{stage}'] = successes / attempts
            else:
                success_rates[f'upload_{stage}'] = 0.0
        
        # Calculate overall success rate
        total_attempts = sum(metrics.get('attempts', 0) for metrics in {**processing_metrics, **upload_metrics}.values())
        total_successes = sum(metrics.get('successes', 0) for metrics in {**processing_metrics, **upload_metrics}.values())
        
        if total_attempts > 0:
            success_rates['overall'] = total_successes / total_attempts
        else:
            success_rates['overall'] = 0.0
        
        return success_rates
    
    def _update_step_metrics(self, step: str, metric_type: str):
        """
        Update metrics for a specific processing step.
        
        Args:
            step: Processing step name
            metric_type: Type of metric ('attempt', 'success', 'failure')
        """
        metrics_key = f"{self.cache_prefix}_processing_metrics"
        current_metrics = cache.get(metrics_key, {})
        
        if step not in current_metrics:
            current_metrics[step] = {
                'attempts': 0,
                'successes': 0,
                'failures': 0,
                'last_updated': timezone.now().isoformat()
            }
        
        current_metrics[step][f'{metric_type}s'] += 1
        current_metrics[step]['last_updated'] = timezone.now().isoformat()
        
        cache.set(metrics_key, current_metrics, timeout=self.cache_ttl)
    
    def _update_upload_metrics(self, stage: str, metric_type: str):
        """
        Update metrics for a specific upload stage.
        
        Args:
            stage: Upload stage name
            metric_type: Type of metric ('attempt', 'success', 'failure')
        """
        metrics_key = f"{self.cache_prefix}_upload_metrics"
        current_metrics = cache.get(metrics_key, {})
        
        if stage not in current_metrics:
            current_metrics[stage] = {
                'attempts': 0,
                'successes': 0,
                'failures': 0,
                'last_updated': timezone.now().isoformat()
            }
        
        current_metrics[stage][f'{metric_type}s'] += 1
        current_metrics[stage]['last_updated'] = timezone.now().isoformat()
        
        cache.set(metrics_key, current_metrics, timeout=self.cache_ttl)
    
    def _update_performance_metrics(self, step: str, processing_time: float):
        """
        Update performance metrics for processing times.
        
        Args:
            step: Processing step name
            processing_time: Time taken in seconds
        """
        perf_key = f"{self.cache_prefix}_performance_{step}"
        current_perf = cache.get(perf_key, {
            'total_time': 0.0,
            'count': 0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'times': []
        })
        
        current_perf['total_time'] += processing_time
        current_perf['count'] += 1
        current_perf['min_time'] = min(current_perf['min_time'], processing_time)
        current_perf['max_time'] = max(current_perf['max_time'], processing_time)
        
        # Keep last 100 times for percentile calculations
        current_perf['times'].append(processing_time)
        if len(current_perf['times']) > 100:
            current_perf['times'] = current_perf['times'][-100:]
        
        cache.set(perf_key, current_perf, timeout=self.cache_ttl)
    
    def _update_upload_performance_metrics(self, stage: str, upload_time: float):
        """
        Update performance metrics for upload times.
        
        Args:
            stage: Upload stage name
            upload_time: Time taken in seconds
        """
        perf_key = f"{self.cache_prefix}_upload_performance_{stage}"
        current_perf = cache.get(perf_key, {
            'total_time': 0.0,
            'count': 0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'times': []
        })
        
        current_perf['total_time'] += upload_time
        current_perf['count'] += 1
        current_perf['min_time'] = min(current_perf['min_time'], upload_time)
        current_perf['max_time'] = max(current_perf['max_time'], upload_time)
        
        # Keep last 100 times for percentile calculations
        current_perf['times'].append(upload_time)
        if len(current_perf['times']) > 100:
            current_perf['times'] = current_perf['times'][-100:]
        
        cache.set(perf_key, current_perf, timeout=self.cache_ttl)
    
    def _check_performance_thresholds(self, step: str, processing_time: float):
        """
        Check if processing time exceeds performance thresholds.
        
        Args:
            step: Processing step name
            processing_time: Time taken in seconds
        """
        if processing_time > self.thresholds['processing_time_critical']:
            logger.critical(f"ALERT: Critical processing time for {step}: {processing_time:.2f}s")
        elif processing_time > self.thresholds['processing_time_warning']:
            logger.warning(f"WARNING: Slow processing time for {step}: {processing_time:.2f}s")
    
    def _check_upload_performance_thresholds(self, stage: str, upload_time: float):
        """
        Check if upload time exceeds performance thresholds.
        
        Args:
            stage: Upload stage name
            upload_time: Time taken in seconds
        """
        if upload_time > self.thresholds['processing_time_critical']:
            logger.critical(f"ALERT: Critical upload time for {stage}: {upload_time:.2f}s")
        elif upload_time > self.thresholds['processing_time_warning']:
            logger.warning(f"WARNING: Slow upload time for {stage}: {upload_time:.2f}s")
    
    def _check_error_rate_thresholds(self, step: str):
        """
        Check if error rates exceed thresholds for a processing step.
        
        Args:
            step: Processing step name
        """
        metrics_key = f"{self.cache_prefix}_processing_metrics"
        metrics = cache.get(metrics_key, {})
        
        step_metrics = metrics.get(step, {})
        attempts = step_metrics.get('attempts', 0)
        failures = step_metrics.get('failures', 0)
        
        if attempts > 5:  # Only check after sufficient data
            error_rate = failures / attempts
            
            if error_rate > self.thresholds['error_rate_critical']:
                logger.critical(f"ALERT: Critical error rate for {step}: {error_rate:.2%}")
            elif error_rate > self.thresholds['error_rate_warning']:
                logger.warning(f"WARNING: High error rate for {step}: {error_rate:.2%}")
    
    def _check_upload_error_rate_thresholds(self, stage: str):
        """
        Check if error rates exceed thresholds for an upload stage.
        
        Args:
            stage: Upload stage name
        """
        metrics_key = f"{self.cache_prefix}_upload_metrics"
        metrics = cache.get(metrics_key, {})
        
        stage_metrics = metrics.get(stage, {})
        attempts = stage_metrics.get('attempts', 0)
        failures = stage_metrics.get('failures', 0)
        
        if attempts > 3:  # Lower threshold for upload checks
            error_rate = failures / attempts
            
            if error_rate > self.thresholds['error_rate_critical']:
                logger.critical(f"ALERT: Critical upload error rate for {stage}: {error_rate:.2%}")
            elif error_rate > self.thresholds['error_rate_warning']:
                logger.warning(f"WARNING: High upload error rate for {stage}: {error_rate:.2%}")
    
    def _get_overview_metrics(self) -> Dict[str, Any]:
        """Get overview metrics for the dashboard."""
        success_rates = self.get_success_rates()
        
        return {
            'overall_success_rate': success_rates.get('overall', 0.0),
            'total_operations': self._get_total_operations(),
            'active_alerts': len(self._get_active_alerts()),
            'system_health': self._determine_system_health(success_rates)
        }
    
    def _get_processing_metrics(self) -> Dict[str, Any]:
        """Get processing-specific metrics."""
        return cache.get(f"{self.cache_prefix}_processing_metrics", {})
    
    def _get_upload_metrics(self) -> Dict[str, Any]:
        """Get upload-specific metrics."""
        return cache.get(f"{self.cache_prefix}_upload_metrics", {})
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics with averages and percentiles."""
        performance_data = {}
        
        # Get all performance cache keys
        cache_keys = [
            key for key in cache._cache.keys() 
            if key.startswith(f"{self.cache_prefix}_performance_") or 
               key.startswith(f"{self.cache_prefix}_upload_performance_")
        ]
        
        for key in cache_keys:
            perf_data = cache.get(key, {})
            if perf_data.get('count', 0) > 0:
                times = perf_data.get('times', [])
                
                # Calculate statistics
                avg_time = perf_data['total_time'] / perf_data['count']
                
                stats = {
                    'average_time': avg_time,
                    'min_time': perf_data.get('min_time', 0),
                    'max_time': perf_data.get('max_time', 0),
                    'count': perf_data['count']
                }
                
                # Calculate percentiles if we have enough data
                if len(times) >= 10:
                    sorted_times = sorted(times)
                    stats.update({
                        'p50': sorted_times[len(sorted_times) // 2],
                        'p90': sorted_times[int(len(sorted_times) * 0.9)],
                        'p95': sorted_times[int(len(sorted_times) * 0.95)]
                    })
                
                operation_name = key.replace(f"{self.cache_prefix}_", "").replace("_performance_", "_")
                performance_data[operation_name] = stats
        
        return performance_data
    
    def _get_error_analysis(self) -> Dict[str, Any]:
        """Get error analysis data."""
        return self.error_logger.get_error_summary()
    
    def _get_trend_analysis(self, hours: int) -> Dict[str, Any]:
        """Get trend analysis for the specified period."""
        # This would typically analyze historical data
        # For now, return basic trend information
        return {
            'period_hours': hours,
            'trend_direction': 'stable',  # Could be 'improving', 'degrading', 'stable'
            'note': 'Trend analysis requires historical data collection'
        }
    
    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get list of active alerts."""
        alerts = []
        success_rates = self.get_success_rates()
        
        # Check success rate alerts
        for operation, rate in success_rates.items():
            if rate < self.thresholds['success_rate_critical']:
                alerts.append({
                    'type': 'critical',
                    'operation': operation,
                    'message': f'Critical success rate: {rate:.2%}',
                    'threshold': self.thresholds['success_rate_critical']
                })
            elif rate < self.thresholds['success_rate_warning']:
                alerts.append({
                    'type': 'warning',
                    'operation': operation,
                    'message': f'Low success rate: {rate:.2%}',
                    'threshold': self.thresholds['success_rate_warning']
                })
        
        return alerts
    
    def _get_recommendations(self) -> List[str]:
        """Get system recommendations based on current metrics."""
        recommendations = []
        success_rates = self.get_success_rates()
        
        overall_rate = success_rates.get('overall', 0.0)
        
        if overall_rate < 0.8:
            recommendations.append("Overall success rate is low. Review error logs and consider system optimization.")
        
        if overall_rate < 0.5:
            recommendations.append("Critical success rate detected. Consider disabling image processing temporarily.")
        
        # Check for specific operation issues
        for operation, rate in success_rates.items():
            if 'processing' in operation and rate < 0.7:
                recommendations.append(f"Image processing issues detected in {operation}. Review image validation logic.")
            elif 'upload' in operation and rate < 0.8:
                recommendations.append(f"Upload issues detected in {operation}. Check LinkedIn API connectivity.")
        
        if not recommendations:
            recommendations.append("System is operating within normal parameters.")
        
        return recommendations
    
    def _get_total_operations(self) -> int:
        """Get total number of operations performed."""
        processing_metrics = cache.get(f"{self.cache_prefix}_processing_metrics", {})
        upload_metrics = cache.get(f"{self.cache_prefix}_upload_metrics", {})
        
        total = 0
        for metrics in processing_metrics.values():
            total += metrics.get('attempts', 0)
        
        for metrics in upload_metrics.values():
            total += metrics.get('attempts', 0)
        
        return total
    
    def _determine_system_health(self, success_rates: Dict[str, float]) -> str:
        """
        Determine overall system health based on success rates.
        
        Args:
            success_rates: Dictionary of success rates
            
        Returns:
            str: Health status ('excellent', 'good', 'fair', 'poor', 'critical')
        """
        overall_rate = success_rates.get('overall', 0.0)
        
        if overall_rate >= 0.95:
            return 'excellent'
        elif overall_rate >= 0.85:
            return 'good'
        elif overall_rate >= 0.70:
            return 'fair'
        elif overall_rate >= 0.50:
            return 'poor'
        else:
            return 'critical'