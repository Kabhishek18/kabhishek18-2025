"""
LinkedIn Task Monitoring Service for image processing tasks.

This service provides task-specific monitoring for LinkedIn image processing,
including task lifecycle tracking, performance monitoring, and failure analysis.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from .linkedin_error_handler import LinkedInImageErrorHandler
from .linkedin_image_monitor import LinkedInImageMonitor


logger = logging.getLogger(__name__)


class LinkedInTaskStatus:
    """Task status constants"""
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    RETRYING = 'retrying'
    CANCELLED = 'cancelled'


class LinkedInTaskMonitor:
    """
    Task-specific monitoring service for LinkedIn image processing.
    
    Provides:
    - Task lifecycle tracking
    - Performance monitoring per task
    - Failure analysis and recovery tracking
    - Task queue health monitoring
    - Detailed task execution logs
    """
    
    def __init__(self):
        self.cache_prefix = 'linkedin_task_monitor'
        self.cache_ttl = 7200  # 2 hours
        self.error_handler = LinkedInImageErrorHandler()
        self.image_monitor = LinkedInImageMonitor()
        
        # Task performance thresholds
        self.task_thresholds = {
            'image_selection': {'warning': 5, 'critical': 10},      # seconds
            'image_download': {'warning': 15, 'critical': 30},      # seconds
            'image_processing': {'warning': 20, 'critical': 45},    # seconds
            'image_validation': {'warning': 3, 'critical': 8},      # seconds
            'image_upload': {'warning': 30, 'critical': 60},        # seconds
            'post_creation': {'warning': 10, 'critical': 20},       # seconds
        }
    
    def create_task(self, task_type: str, post_id: int, context: Dict[str, Any] = None) -> str:
        """
        Create a new monitored task.
        
        Args:
            task_type: Type of task (e.g., 'image_processing', 'image_upload')
            post_id: Blog post ID
            context: Additional task context
            
        Returns:
            str: Unique task ID
        """
        task_id = str(uuid.uuid4())
        
        task_data = {
            'task_id': task_id,
            'task_type': task_type,
            'post_id': post_id,
            'status': LinkedInTaskStatus.PENDING,
            'created_at': timezone.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'duration': None,
            'context': context or {},
            'steps': [],
            'errors': [],
            'retry_count': 0,
            'max_retries': 3
        }
        
        # Store task data
        task_key = f"{self.cache_prefix}_task_{task_id}"
        cache.set(task_key, task_data, timeout=self.cache_ttl)
        
        # Update task queue metrics
        self._update_queue_metrics(task_type, 'created')
        
        logger.info(f"Created LinkedIn task {task_id} for post {post_id}, type: {task_type}")
        
        return task_id
    
    def start_task(self, task_id: str) -> bool:
        """
        Mark a task as started.
        
        Args:
            task_id: Task ID
            
        Returns:
            bool: True if task was successfully started
        """
        task_key = f"{self.cache_prefix}_task_{task_id}"
        task_data = cache.get(task_key)
        
        if not task_data:
            logger.error(f"Task {task_id} not found")
            return False
        
        if task_data['status'] != LinkedInTaskStatus.PENDING:
            logger.warning(f"Task {task_id} is not in pending status: {task_data['status']}")
            return False
        
        task_data.update({
            'status': LinkedInTaskStatus.RUNNING,
            'started_at': timezone.now().isoformat()
        })
        
        cache.set(task_key, task_data, timeout=self.cache_ttl)
        
        # Update queue metrics
        self._update_queue_metrics(task_data['task_type'], 'started')
        
        logger.info(f"Started LinkedIn task {task_id}")
        
        return True
    
    def add_task_step(self, task_id: str, step_name: str, step_data: Dict[str, Any] = None) -> bool:
        """
        Add a step to a running task.
        
        Args:
            task_id: Task ID
            step_name: Name of the step
            step_data: Additional step data
            
        Returns:
            bool: True if step was added successfully
        """
        task_key = f"{self.cache_prefix}_task_{task_id}"
        task_data = cache.get(task_key)
        
        if not task_data:
            logger.error(f"Task {task_id} not found")
            return False
        
        step_info = {
            'step_name': step_name,
            'started_at': timezone.now().isoformat(),
            'completed_at': None,
            'duration': None,
            'status': 'running',
            'data': step_data or {}
        }
        
        task_data['steps'].append(step_info)
        cache.set(task_key, task_data, timeout=self.cache_ttl)
        
        # Record step start in image monitor
        self.image_monitor.record_image_processing_attempt(
            post_id=task_data['post_id'],
            image_url=step_data.get('image_url', '') if step_data else '',
            processing_step=step_name,
            context={'task_id': task_id}
        )
        
        logger.debug(f"Added step '{step_name}' to task {task_id}")
        
        return True
    
    def complete_task_step(self, task_id: str, step_name: str, 
                          step_result: Dict[str, Any] = None, error: Exception = None) -> bool:
        """
        Mark a task step as completed (successfully or with error).
        
        Args:
            task_id: Task ID
            step_name: Name of the step to complete
            step_result: Result data from the step
            error: Error that occurred (if any)
            
        Returns:
            bool: True if step was completed successfully
        """
        task_key = f"{self.cache_prefix}_task_{task_id}"
        task_data = cache.get(task_key)
        
        if not task_data:
            logger.error(f"Task {task_id} not found")
            return False
        
        # Find the step
        step_found = False
        for step in task_data['steps']:
            if step['step_name'] == step_name and step['status'] == 'running':
                completed_at = timezone.now()
                started_at = datetime.fromisoformat(step['started_at'].replace('Z', '+00:00'))
                duration = (completed_at - started_at).total_seconds()
                
                step.update({
                    'completed_at': completed_at.isoformat(),
                    'duration': duration,
                    'status': 'success' if error is None else 'failed',
                    'result': step_result or {},
                    'error': str(error) if error else None
                })
                
                step_found = True
                
                # Check performance thresholds
                self._check_step_performance_thresholds(step_name, duration)
                
                # Record in image monitor
                if error is None:
                    self.image_monitor.record_image_processing_success(
                        post_id=task_data['post_id'],
                        image_url=step.get('data', {}).get('image_url', ''),
                        processing_step=step_name,
                        processing_time=duration,
                        result_data=step_result
                    )
                else:
                    self.image_monitor.record_image_processing_failure(
                        post_id=task_data['post_id'],
                        image_url=step.get('data', {}).get('image_url', ''),
                        processing_step=step_name,
                        error=error,
                        processing_time=duration
                    )
                
                break
        
        if not step_found:
            logger.warning(f"Running step '{step_name}' not found in task {task_id}")
            return False
        
        cache.set(task_key, task_data, timeout=self.cache_ttl)
        
        logger.debug(f"Completed step '{step_name}' for task {task_id} "
                    f"({'success' if error is None else 'failed'})")
        
        return True
    
    def complete_task(self, task_id: str, result: Dict[str, Any] = None, error: Exception = None) -> bool:
        """
        Mark a task as completed.
        
        Args:
            task_id: Task ID
            result: Task result data
            error: Error that caused task failure (if any)
            
        Returns:
            bool: True if task was completed successfully
        """
        task_key = f"{self.cache_prefix}_task_{task_id}"
        task_data = cache.get(task_key)
        
        if not task_data:
            logger.error(f"Task {task_id} not found")
            return False
        
        completed_at = timezone.now()
        started_at = datetime.fromisoformat(task_data['started_at'].replace('Z', '+00:00'))
        duration = (completed_at - started_at).total_seconds()
        
        task_data.update({
            'status': LinkedInTaskStatus.SUCCESS if error is None else LinkedInTaskStatus.FAILED,
            'completed_at': completed_at.isoformat(),
            'duration': duration,
            'result': result or {},
            'final_error': str(error) if error else None
        })
        
        if error:
            task_data['errors'].append({
                'error': str(error),
                'error_type': type(error).__name__,
                'timestamp': completed_at.isoformat(),
                'step': 'task_completion'
            })
        
        cache.set(task_key, task_data, timeout=self.cache_ttl)
        
        # Update queue metrics
        status = 'completed' if error is None else 'failed'
        self._update_queue_metrics(task_data['task_type'], status)
        
        # Update task performance metrics
        self._update_task_performance_metrics(task_data['task_type'], duration, error is None)
        
        logger.info(f"Completed LinkedIn task {task_id} "
                   f"({'success' if error is None else 'failed'}, {duration:.2f}s)")
        
        return True
    
    def retry_task(self, task_id: str, reason: str = None) -> bool:
        """
        Mark a task for retry.
        
        Args:
            task_id: Task ID
            reason: Reason for retry
            
        Returns:
            bool: True if task was marked for retry
        """
        task_key = f"{self.cache_prefix}_task_{task_id}"
        task_data = cache.get(task_key)
        
        if not task_data:
            logger.error(f"Task {task_id} not found")
            return False
        
        if task_data['retry_count'] >= task_data['max_retries']:
            logger.warning(f"Task {task_id} has exceeded max retries ({task_data['max_retries']})")
            return False
        
        task_data.update({
            'status': LinkedInTaskStatus.RETRYING,
            'retry_count': task_data['retry_count'] + 1,
            'retry_reason': reason,
            'retry_at': timezone.now().isoformat()
        })
        
        # Clear previous steps for retry
        task_data['steps'] = []
        
        cache.set(task_key, task_data, timeout=self.cache_ttl)
        
        # Update queue metrics
        self._update_queue_metrics(task_data['task_type'], 'retried')
        
        logger.info(f"Marked task {task_id} for retry (attempt {task_data['retry_count']})")
        
        return True
    
    def cancel_task(self, task_id: str, reason: str = None) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: Task ID
            reason: Reason for cancellation
            
        Returns:
            bool: True if task was cancelled
        """
        task_key = f"{self.cache_prefix}_task_{task_id}"
        task_data = cache.get(task_key)
        
        if not task_data:
            logger.error(f"Task {task_id} not found")
            return False
        
        task_data.update({
            'status': LinkedInTaskStatus.CANCELLED,
            'cancelled_at': timezone.now().isoformat(),
            'cancellation_reason': reason
        })
        
        cache.set(task_key, task_data, timeout=self.cache_ttl)
        
        # Update queue metrics
        self._update_queue_metrics(task_data['task_type'], 'cancelled')
        
        logger.info(f"Cancelled LinkedIn task {task_id}: {reason}")
        
        return True
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            dict: Task status information or None if not found
        """
        task_key = f"{self.cache_prefix}_task_{task_id}"
        return cache.get(task_key)
    
    def get_task_summary(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a summary of task execution.
        
        Args:
            task_id: Task ID
            
        Returns:
            dict: Task summary or None if not found
        """
        task_data = self.get_task_status(task_id)
        
        if not task_data:
            return None
        
        summary = {
            'task_id': task_id,
            'task_type': task_data['task_type'],
            'post_id': task_data['post_id'],
            'status': task_data['status'],
            'duration': task_data.get('duration'),
            'retry_count': task_data['retry_count'],
            'step_count': len(task_data['steps']),
            'error_count': len(task_data['errors']),
            'created_at': task_data['created_at'],
            'completed_at': task_data.get('completed_at')
        }
        
        # Add step summary
        if task_data['steps']:
            successful_steps = sum(1 for step in task_data['steps'] if step['status'] == 'success')
            failed_steps = sum(1 for step in task_data['steps'] if step['status'] == 'failed')
            
            summary.update({
                'successful_steps': successful_steps,
                'failed_steps': failed_steps,
                'step_success_rate': successful_steps / len(task_data['steps']) if task_data['steps'] else 0
            })
        
        return summary
    
    def get_queue_metrics(self) -> Dict[str, Any]:
        """
        Get task queue metrics.
        
        Returns:
            dict: Queue metrics by task type
        """
        metrics_key = f"{self.cache_prefix}_queue_metrics"
        return cache.get(metrics_key, {})
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get task performance metrics.
        
        Returns:
            dict: Performance metrics by task type
        """
        perf_key = f"{self.cache_prefix}_performance_metrics"
        return cache.get(perf_key, {})
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """
        Get list of currently active tasks.
        
        Returns:
            list: List of active task summaries
        """
        active_tasks = []
        
        # This is a simplified implementation
        # In a real system, you'd maintain an index of active tasks
        # For now, we'll return an empty list as we don't have a way to enumerate cache keys
        
        return active_tasks
    
    def cleanup_completed_tasks(self, hours: int = 24) -> int:
        """
        Clean up completed tasks older than specified hours.
        
        Args:
            hours: Hours after which to clean up completed tasks
            
        Returns:
            int: Number of tasks cleaned up
        """
        # This would require maintaining an index of tasks
        # For now, return 0 as we rely on cache TTL for cleanup
        return 0
    
    def _update_queue_metrics(self, task_type: str, metric_type: str):
        """
        Update task queue metrics.
        
        Args:
            task_type: Type of task
            metric_type: Type of metric ('created', 'started', 'completed', 'failed', 'retried', 'cancelled')
        """
        metrics_key = f"{self.cache_prefix}_queue_metrics"
        current_metrics = cache.get(metrics_key, {})
        
        if task_type not in current_metrics:
            current_metrics[task_type] = {
                'created': 0,
                'started': 0,
                'completed': 0,
                'failed': 0,
                'retried': 0,
                'cancelled': 0,
                'last_updated': timezone.now().isoformat()
            }
        
        current_metrics[task_type][metric_type] += 1
        current_metrics[task_type]['last_updated'] = timezone.now().isoformat()
        
        cache.set(metrics_key, current_metrics, timeout=self.cache_ttl)
    
    def _update_task_performance_metrics(self, task_type: str, duration: float, success: bool):
        """
        Update task performance metrics.
        
        Args:
            task_type: Type of task
            duration: Task duration in seconds
            success: Whether task was successful
        """
        perf_key = f"{self.cache_prefix}_performance_metrics"
        current_perf = cache.get(perf_key, {})
        
        if task_type not in current_perf:
            current_perf[task_type] = {
                'total_duration': 0.0,
                'count': 0,
                'success_count': 0,
                'min_duration': float('inf'),
                'max_duration': 0.0,
                'durations': []
            }
        
        task_perf = current_perf[task_type]
        task_perf['total_duration'] += duration
        task_perf['count'] += 1
        
        if success:
            task_perf['success_count'] += 1
        
        task_perf['min_duration'] = min(task_perf['min_duration'], duration)
        task_perf['max_duration'] = max(task_perf['max_duration'], duration)
        
        # Keep last 50 durations for percentile calculations
        task_perf['durations'].append(duration)
        if len(task_perf['durations']) > 50:
            task_perf['durations'] = task_perf['durations'][-50:]
        
        cache.set(perf_key, current_perf, timeout=self.cache_ttl)
    
    def _check_step_performance_thresholds(self, step_name: str, duration: float):
        """
        Check if step duration exceeds performance thresholds.
        
        Args:
            step_name: Name of the step
            duration: Duration in seconds
        """
        thresholds = self.task_thresholds.get(step_name, {'warning': 30, 'critical': 60})
        
        if duration > thresholds['critical']:
            logger.critical(f"ALERT: Critical performance for step '{step_name}': {duration:.2f}s")
        elif duration > thresholds['warning']:
            logger.warning(f"WARNING: Slow performance for step '{step_name}': {duration:.2f}s")
    
    def get_task_health_report(self) -> Dict[str, Any]:
        """
        Get comprehensive task health report.
        
        Returns:
            dict: Task health report
        """
        queue_metrics = self.get_queue_metrics()
        performance_metrics = self.get_performance_metrics()
        
        report = {
            'generated_at': timezone.now().isoformat(),
            'queue_health': self._analyze_queue_health(queue_metrics),
            'performance_health': self._analyze_performance_health(performance_metrics),
            'recommendations': self._generate_task_recommendations(queue_metrics, performance_metrics)
        }
        
        return report
    
    def _analyze_queue_health(self, queue_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze queue health based on metrics.
        
        Args:
            queue_metrics: Queue metrics data
            
        Returns:
            dict: Queue health analysis
        """
        health = {
            'status': 'healthy',
            'issues': [],
            'task_types': {}
        }
        
        for task_type, metrics in queue_metrics.items():
            created = metrics.get('created', 0)
            completed = metrics.get('completed', 0)
            failed = metrics.get('failed', 0)
            
            if created > 0:
                success_rate = completed / created
                failure_rate = failed / created
                
                task_health = {
                    'success_rate': success_rate,
                    'failure_rate': failure_rate,
                    'status': 'healthy'
                }
                
                if failure_rate > 0.2:  # 20% failure rate
                    task_health['status'] = 'unhealthy'
                    health['issues'].append(f'High failure rate for {task_type}: {failure_rate:.2%}')
                    if health['status'] == 'healthy':
                        health['status'] = 'degraded'
                elif failure_rate > 0.1:  # 10% failure rate
                    task_health['status'] = 'degraded'
                    health['issues'].append(f'Elevated failure rate for {task_type}: {failure_rate:.2%}')
                    if health['status'] == 'healthy':
                        health['status'] = 'degraded'
                
                health['task_types'][task_type] = task_health
        
        return health
    
    def _analyze_performance_health(self, performance_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze performance health based on metrics.
        
        Args:
            performance_metrics: Performance metrics data
            
        Returns:
            dict: Performance health analysis
        """
        health = {
            'status': 'healthy',
            'issues': [],
            'task_types': {}
        }
        
        for task_type, metrics in performance_metrics.items():
            count = metrics.get('count', 0)
            
            if count > 0:
                avg_duration = metrics['total_duration'] / count
                max_duration = metrics.get('max_duration', 0)
                
                task_health = {
                    'average_duration': avg_duration,
                    'max_duration': max_duration,
                    'status': 'healthy'
                }
                
                # Check against thresholds (using generic thresholds if specific not found)
                warning_threshold = 30
                critical_threshold = 60
                
                if avg_duration > critical_threshold:
                    task_health['status'] = 'critical'
                    health['issues'].append(f'Critical average duration for {task_type}: {avg_duration:.2f}s')
                    health['status'] = 'critical'
                elif avg_duration > warning_threshold:
                    task_health['status'] = 'degraded'
                    health['issues'].append(f'Slow average duration for {task_type}: {avg_duration:.2f}s')
                    if health['status'] == 'healthy':
                        health['status'] = 'degraded'
                
                health['task_types'][task_type] = task_health
        
        return health
    
    def _generate_task_recommendations(self, queue_metrics: Dict[str, Any], 
                                     performance_metrics: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations based on task metrics.
        
        Args:
            queue_metrics: Queue metrics data
            performance_metrics: Performance metrics data
            
        Returns:
            list: List of recommendations
        """
        recommendations = []
        
        # Analyze queue metrics
        for task_type, metrics in queue_metrics.items():
            created = metrics.get('created', 0)
            failed = metrics.get('failed', 0)
            
            if created > 0:
                failure_rate = failed / created
                
                if failure_rate > 0.2:
                    recommendations.append(f"High failure rate for {task_type} tasks. Review error logs and consider system optimization.")
                elif failure_rate > 0.1:
                    recommendations.append(f"Monitor {task_type} tasks closely due to elevated failure rate.")
        
        # Analyze performance metrics
        for task_type, metrics in performance_metrics.items():
            count = metrics.get('count', 0)
            
            if count > 0:
                avg_duration = metrics['total_duration'] / count
                
                if avg_duration > 60:
                    recommendations.append(f"Optimize {task_type} performance - average duration is {avg_duration:.2f}s.")
                elif avg_duration > 30:
                    recommendations.append(f"Consider optimizing {task_type} performance.")
        
        if not recommendations:
            recommendations.append("Task system is operating within normal parameters.")
        
        return recommendations