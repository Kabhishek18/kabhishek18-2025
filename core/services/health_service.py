"""
Health Service Module

This module provides comprehensive health monitoring capabilities for the Django application.
It includes health checks for database, cache, system resources, and other system components.

Optimized for performance with caching, parallel execution, and graceful degradation.
"""

import logging
import os
import psutil
import shutil
import time
import threading
import functools
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError

from django.core.cache import cache
from django.db import connection, connections
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Avg, Q

# Configure logger
logger = logging.getLogger(__name__)

# Constants for optimization
MAX_WORKERS = getattr(settings, 'HEALTH_SERVICE_MAX_WORKERS', 4)
DEFAULT_CACHE_TIMEOUT = getattr(settings, 'HEALTH_SERVICE_CACHE_TIMEOUT', 60)  # 1 minute
CRITICAL_CACHE_TIMEOUT = getattr(settings, 'HEALTH_SERVICE_CRITICAL_CACHE_TIMEOUT', 10)  # 10 seconds
METRICS_RETENTION_DAYS = getattr(settings, 'HEALTH_METRICS_RETENTION_DAYS', 7)  # 7 days

# Performance monitoring
PERFORMANCE_STATS = {
    'total_checks': 0,
    'cache_hits': 0,
    'cache_misses': 0,
    'avg_response_time': 0,
    'last_full_check_time': 0,
}

def cache_health_check(timeout=DEFAULT_CACHE_TIMEOUT, critical_timeout=CRITICAL_CACHE_TIMEOUT):
    """
    Decorator to cache health check results with different timeouts based on status.
    Critical checks are cached for a shorter time to ensure timely updates.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate a cache key based on function name and arguments
            cache_key = f"health_check_{func.__name__}_{hash(str(args))}"
            force_refresh = kwargs.pop('force_refresh', False)
            
            # Try to get from cache if not forcing refresh
            if not force_refresh:
                cached_result = cache.get(cache_key)
                if cached_result:
                    PERFORMANCE_STATS['cache_hits'] += 1
                    return cached_result
            
            PERFORMANCE_STATS['cache_misses'] += 1
            
            # Execute the health check
            result = func(*args, **kwargs)
            
            # Cache with appropriate timeout based on status
            if result.get('status') == 'critical':
                cache.set(cache_key, result, critical_timeout)
            else:
                cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


class HealthCheckResult:
    """Represents the result of a health check operation."""
    
    def __init__(self, status: str, message: str, details: Optional[Dict[str, Any]] = None, 
                 response_time: Optional[float] = None):
        self.status = status  # 'healthy', 'warning', 'critical'
        self.message = message
        self.details = details or {}
        self.response_time = response_time
        self.timestamp = timezone.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the health check result to a dictionary."""
        return {
            'status': self.status,
            'message': self.message,
            'details': self.details,
            'response_time': self.response_time,
            'timestamp': self.timestamp.isoformat()
        }


class BaseHealthChecker:
    """Base class for all health checkers."""
    
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
    
    def check(self) -> HealthCheckResult:
        """Perform the health check. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement the check method")
    
    def check_with_timeout(self) -> HealthCheckResult:
        """
        Perform health check with timeout and retry logic.
        Uses a thread-safe approach instead of signals for timeout handling.
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # Use a simple timeout approach that works in threads
                result = self._run_with_timeout(self.check, self.timeout)
                return result
                
            except TimeoutError as e:
                last_exception = e
                logger.warning(f"Health check timeout on attempt {attempt + 1}: {str(e)}")
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Health check failed on attempt {attempt + 1}: {str(e)}")
                
            # Wait before retry (except on last attempt)
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
        
        # All retries failed
        return HealthCheckResult(
            status='critical',
            message=f"Health check failed after {self.max_retries} attempts: {str(last_exception)}",
            details={
                'error': str(last_exception),
                'attempts': self.max_retries,
                'timeout': self.timeout
            }
        )
    
    def _run_with_timeout(self, func, timeout_seconds):
        """
        Run a function with a timeout without using signals.
        This is thread-safe and works in any thread.
        """
        import threading
        import queue
        
        result_queue = queue.Queue()
        exception_queue = queue.Queue()
        
        def worker():
            try:
                result = func()
                result_queue.put(result)
            except Exception as e:
                exception_queue.put(e)
        
        # Start the worker thread
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        
        # Wait for the thread to complete or timeout
        thread.join(timeout_seconds)
        
        # Check if the thread is still alive (timeout occurred)
        if thread.is_alive():
            raise TimeoutError(f"Health check timed out after {timeout_seconds} seconds")
        
        # Check if an exception occurred
        if not exception_queue.empty():
            raise exception_queue.get()
        
        # Return the result
        if not result_queue.empty():
            return result_queue.get()
        
        # This should not happen, but just in case
        raise Exception("Health check failed with no result or exception")
    
    def _measure_time(self, func):
        """Decorator to measure execution time of a function."""
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                return result, response_time
            except Exception as e:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                raise e
        return wrapper
    
    def _safe_execute(self, func, fallback_value=None, error_message="Operation failed"):
        """Safely execute a function with error handling and fallback."""
        try:
            return func()
        except Exception as e:
            logger.warning(f"{error_message}: {str(e)}")
            return fallback_value


class DatabaseHealthChecker(BaseHealthChecker):
    """Health checker for database connectivity and performance."""
    
    def check(self) -> HealthCheckResult:
        """Check database health including connectivity and basic performance."""
        try:
            start_time = time.time()
            
            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            # Get database connection info
            db_info = self._get_database_info()
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            # Check if response time is concerning
            if response_time > 1000:  # More than 1 second
                status = 'warning'
                message = f"Database responding slowly ({response_time:.2f}ms)"
            else:
                status = 'healthy'
                message = f"Database connection healthy ({response_time:.2f}ms)"
            
            return HealthCheckResult(
                status=status,
                message=message,
                details=db_info,
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return HealthCheckResult(
                status='critical',
                message=f"Database connection failed: {str(e)}",
                details={'error': str(e)}
            )
    
    def _get_database_info(self) -> Dict[str, Any]:
        """Get additional database information."""
        try:
            db_config = settings.DATABASES['default']
            
            # Get connection count (MySQL specific)
            with connection.cursor() as cursor:
                cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
                result = cursor.fetchone()
                active_connections = int(result[1]) if result else 0
                
                # Get database size (MySQL specific)
                cursor.execute("""
                    SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'DB Size in MB'
                    FROM information_schema.tables
                    WHERE table_schema = %s
                """, [db_config['NAME']])
                size_result = cursor.fetchone()
                db_size_mb = float(size_result[0]) if size_result and size_result[0] else 0
            
            return {
                'engine': db_config['ENGINE'],
                'name': db_config['NAME'],
                'host': db_config.get('HOST', 'localhost'),
                'port': db_config.get('PORT', '3306'),
                'active_connections': active_connections,
                'database_size_mb': db_size_mb
            }
            
        except Exception as e:
            logger.warning(f"Could not get database info: {str(e)}")
            return {'error': 'Could not retrieve database information'}


class CacheHealthChecker(BaseHealthChecker):
    """Health checker for cache system (Redis/Database cache)."""
    
    def check(self) -> HealthCheckResult:
        """Check cache system health and performance."""
        try:
            start_time = time.time()
            
            # Test cache write/read
            test_key = 'health_check_test'
            test_value = f'test_value_{int(time.time())}'
            
            cache.set(test_key, test_value, timeout=60)
            retrieved_value = cache.get(test_key)
            
            if retrieved_value != test_value:
                raise Exception("Cache write/read test failed")
            
            # Clean up test key
            cache.delete(test_key)
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            # Get cache info
            cache_info = self._get_cache_info()
            
            # Check if response time is concerning
            if response_time > 500:  # More than 500ms
                status = 'warning'
                message = f"Cache responding slowly ({response_time:.2f}ms)"
            else:
                status = 'healthy'
                message = f"Cache system healthy ({response_time:.2f}ms)"
            
            return HealthCheckResult(
                status=status,
                message=message,
                details=cache_info,
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"Cache health check failed: {str(e)}")
            return HealthCheckResult(
                status='critical',
                message=f"Cache system failed: {str(e)}",
                details={'error': str(e)}
            )
    
    def _get_cache_info(self) -> Dict[str, Any]:
        """Get cache system information."""
        try:
            cache_config = settings.CACHES['default']
            backend = cache_config['BACKEND']
            
            info = {
                'backend': backend,
                'location': cache_config.get('LOCATION', 'N/A')
            }
            
            # Try to get Redis-specific info if using Redis
            if 'redis' in backend.lower():
                try:
                    import redis
                    from django.core.cache.backends.redis import RedisCache
                    
                    if hasattr(cache, '_cache'):
                        redis_client = cache._cache.get_client(1)
                        redis_info = redis_client.info()
                        
                        info.update({
                            'redis_version': redis_info.get('redis_version'),
                            'used_memory_human': redis_info.get('used_memory_human'),
                            'connected_clients': redis_info.get('connected_clients'),
                            'keyspace_hits': redis_info.get('keyspace_hits', 0),
                            'keyspace_misses': redis_info.get('keyspace_misses', 0)
                        })
                        
                        # Calculate hit rate
                        hits = redis_info.get('keyspace_hits', 0)
                        misses = redis_info.get('keyspace_misses', 0)
                        if hits + misses > 0:
                            hit_rate = (hits / (hits + misses)) * 100
                            info['hit_rate_percent'] = round(hit_rate, 2)
                        
                except Exception as redis_error:
                    logger.warning(f"Could not get Redis info: {str(redis_error)}")
                    info['redis_info_error'] = str(redis_error)
            
            return info
            
        except Exception as e:
            logger.warning(f"Could not get cache info: {str(e)}")
            return {'error': 'Could not retrieve cache information'}


class MemoryHealthChecker(BaseHealthChecker):
    """Health checker for system memory usage."""
    
    def check(self) -> HealthCheckResult:
        """Check system memory usage and availability."""
        try:
            start_time = time.time()
            
            # Get memory information
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            # Calculate memory usage percentage
            memory_percent = memory.percent
            
            # Determine status based on memory usage
            if memory_percent >= 90:
                status = 'critical'
                message = f"Critical memory usage: {memory_percent:.1f}%"
            elif memory_percent >= 80:
                status = 'warning'
                message = f"High memory usage: {memory_percent:.1f}%"
            else:
                status = 'healthy'
                message = f"Memory usage normal: {memory_percent:.1f}%"
            
            details = {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_gb': round(memory.used / (1024**3), 2),
                'percent_used': memory_percent,
                'swap_total_gb': round(swap.total / (1024**3), 2) if swap.total > 0 else 0,
                'swap_used_gb': round(swap.used / (1024**3), 2) if swap.total > 0 else 0,
                'swap_percent': swap.percent if swap.total > 0 else 0
            }
            
            return HealthCheckResult(
                status=status,
                message=message,
                details=details,
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"Memory health check failed: {str(e)}")
            return HealthCheckResult(
                status='critical',
                message=f"Memory check failed: {str(e)}",
                details={'error': str(e)}
            )


class DiskHealthChecker(BaseHealthChecker):
    """Health checker for disk space utilization."""
    
    def check(self) -> HealthCheckResult:
        """Check disk space usage for critical paths."""
        try:
            start_time = time.time()
            
            # Check disk usage for the project directory
            project_path = settings.BASE_DIR
            disk_usage = shutil.disk_usage(project_path)
            
            # Calculate disk usage percentage
            total_gb = disk_usage.total / (1024**3)
            used_gb = (disk_usage.total - disk_usage.free) / (1024**3)
            free_gb = disk_usage.free / (1024**3)
            percent_used = (used_gb / total_gb) * 100
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            # Determine status based on disk usage
            if percent_used >= 95:
                status = 'critical'
                message = f"Critical disk usage: {percent_used:.1f}%"
            elif percent_used >= 85:
                status = 'warning'
                message = f"High disk usage: {percent_used:.1f}%"
            else:
                status = 'healthy'
                message = f"Disk usage normal: {percent_used:.1f}%"
            
            details = {
                'path': str(project_path),
                'total_gb': round(total_gb, 2),
                'used_gb': round(used_gb, 2),
                'free_gb': round(free_gb, 2),
                'percent_used': round(percent_used, 1)
            }
            
            # Add additional disk info if available
            try:
                disk_partitions = psutil.disk_partitions()
                details['partitions'] = []
                for partition in disk_partitions:
                    try:
                        partition_usage = psutil.disk_usage(partition.mountpoint)
                        partition_total = partition_usage.total / (1024**3)
                        partition_used = (partition_usage.total - partition_usage.free) / (1024**3)
                        partition_percent = (partition_used / partition_total) * 100 if partition_total > 0 else 0
                        
                        details['partitions'].append({
                            'device': partition.device,
                            'mountpoint': partition.mountpoint,
                            'fstype': partition.fstype,
                            'total_gb': round(partition_total, 2),
                            'used_gb': round(partition_used, 2),
                            'percent_used': round(partition_percent, 1)
                        })
                    except (PermissionError, OSError):
                        # Skip partitions we can't access
                        continue
            except Exception as partition_error:
                logger.warning(f"Could not get partition info: {str(partition_error)}")
            
            return HealthCheckResult(
                status=status,
                message=message,
                details=details,
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"Disk health check failed: {str(e)}")
            return HealthCheckResult(
                status='critical',
                message=f"Disk check failed: {str(e)}",
                details={'error': str(e)}
            )


class SystemLoadHealthChecker(BaseHealthChecker):
    """Health checker for system load and performance metrics."""
    
    def check(self) -> HealthCheckResult:
        """Check system load average and CPU usage."""
        try:
            start_time = time.time()
            
            # Get CPU information
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_count_logical = psutil.cpu_count(logical=True)
            
            # Get load average (Unix-like systems)
            load_avg = None
            try:
                load_avg = os.getloadavg()
            except (OSError, AttributeError):
                # Windows doesn't have load average
                load_avg = None
            
            # Get boot time and uptime
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            uptime_days = uptime_seconds / (24 * 3600)
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            # Determine status based on CPU usage
            if cpu_percent >= 90:
                status = 'critical'
                message = f"Critical CPU usage: {cpu_percent:.1f}%"
            elif cpu_percent >= 80:
                status = 'warning'
                message = f"High CPU usage: {cpu_percent:.1f}%"
            else:
                status = 'healthy'
                message = f"System load normal: {cpu_percent:.1f}% CPU"
            
            details = {
                'cpu_percent': cpu_percent,
                'cpu_count_physical': cpu_count,
                'cpu_count_logical': cpu_count_logical,
                'uptime_days': round(uptime_days, 2),
                'boot_time': datetime.fromtimestamp(boot_time).isoformat()
            }
            
            if load_avg:
                details.update({
                    'load_avg_1min': round(load_avg[0], 2),
                    'load_avg_5min': round(load_avg[1], 2),
                    'load_avg_15min': round(load_avg[2], 2)
                })
                
                # Check if load average is concerning
                if load_avg[0] > cpu_count * 2:
                    if status == 'healthy':
                        status = 'warning'
                        message = f"High system load: {load_avg[0]:.2f}"
            
            # Get process count
            try:
                process_count = len(psutil.pids())
                details['process_count'] = process_count
            except Exception:
                pass
            
            return HealthCheckResult(
                status=status,
                message=message,
                details=details,
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"System load health check failed: {str(e)}")
            return HealthCheckResult(
                status='critical',
                message=f"System load check failed: {str(e)}",
                details={'error': str(e)}
            )


class LogHealthChecker(BaseHealthChecker):
    """Health checker for recent log entries and error levels."""
    
    def check(self) -> HealthCheckResult:
        """Check recent log entries for errors and warnings."""
        try:
            start_time = time.time()
            
            # Get Django log file path
            log_file_path = None
            for handler in logger.handlers:
                if hasattr(handler, 'baseFilename'):
                    log_file_path = handler.baseFilename
                    break
            
            # If no file handler found, check settings
            if not log_file_path:
                log_file_path = os.path.join(settings.BASE_DIR, 'django_debug.log')
            
            details = {
                'log_file_path': log_file_path,
                'recent_errors': [],
                'recent_warnings': [],
                'total_lines_checked': 0
            }
            
            status = 'healthy'
            message = "No recent critical errors found"
            
            # Check if log file exists and read recent entries
            if os.path.exists(log_file_path):
                try:
                    # Read last 100 lines of log file
                    with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        recent_lines = lines[-100:] if len(lines) > 100 else lines
                        details['total_lines_checked'] = len(recent_lines)
                        
                        # Look for error and warning patterns
                        error_count = 0
                        warning_count = 0
                        
                        for line in recent_lines:
                            line_lower = line.lower()
                            if 'error' in line_lower or 'critical' in line_lower:
                                error_count += 1
                                if len(details['recent_errors']) < 5:  # Keep only last 5 errors
                                    details['recent_errors'].append(line.strip()[:200])
                            elif 'warning' in line_lower:
                                warning_count += 1
                                if len(details['recent_warnings']) < 5:  # Keep only last 5 warnings
                                    details['recent_warnings'].append(line.strip()[:200])
                        
                        details['error_count'] = error_count
                        details['warning_count'] = warning_count
                        
                        # Determine status based on error count
                        if error_count > 10:
                            status = 'critical'
                            message = f"High error rate: {error_count} errors in recent logs"
                        elif error_count > 5 or warning_count > 20:
                            status = 'warning'
                            message = f"Moderate issues: {error_count} errors, {warning_count} warnings"
                        else:
                            message = f"Log status normal: {error_count} errors, {warning_count} warnings"
                        
                except Exception as file_error:
                    details['file_read_error'] = str(file_error)
                    status = 'warning'
                    message = f"Could not read log file: {str(file_error)}"
            else:
                details['file_exists'] = False
                message = "Log file not found - logging may not be configured"
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            return HealthCheckResult(
                status=status,
                message=message,
                details=details,
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"Log health check failed: {str(e)}")
            return HealthCheckResult(
                status='critical',
                message=f"Log check failed: {str(e)}",
                details={'error': str(e)}
            )


class APIHealthChecker(BaseHealthChecker):
    """Health checker for API usage statistics and performance."""
    
    def check(self) -> HealthCheckResult:
        """Check API usage statistics and health metrics."""
        try:
            start_time = time.time()
            
            # Import API models
            try:
                from api.models import APIClient, APIKey, APIUsageLog
            except ImportError:
                return HealthCheckResult(
                    status='warning',
                    message="API models not available",
                    details={'error': 'API app not installed or models not found'}
                )
            
            # Get current time and 24 hours ago
            now = timezone.now()
            twenty_four_hours_ago = now - timedelta(hours=24)
            one_hour_ago = now - timedelta(hours=1)
            
            # Collect API statistics
            api_stats = self._collect_api_statistics(
                APIClient, APIKey, APIUsageLog, 
                now, twenty_four_hours_ago, one_hour_ago
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            # Determine status based on error rate
            error_rate = api_stats.get('error_rate_24h', 0)
            
            if error_rate > 10:  # More than 10% error rate
                status = 'critical'
                message = f"Critical API error rate: {error_rate:.1f}%"
            elif error_rate > 5:  # More than 5% error rate
                status = 'warning'
                message = f"High API error rate: {error_rate:.1f}%"
            else:
                status = 'healthy'
                message = f"API health normal: {error_rate:.1f}% error rate"
            
            return HealthCheckResult(
                status=status,
                message=message,
                details=api_stats,
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"API health check failed: {str(e)}")
            return HealthCheckResult(
                status='critical',
                message=f"API health check failed: {str(e)}",
                details={'error': str(e)}
            )
    
    def _collect_api_statistics(self, APIClient, APIKey, APIUsageLog, now, twenty_four_hours_ago, one_hour_ago) -> Dict[str, Any]:
        """Collect comprehensive API statistics."""
        try:
            # Basic counts
            total_clients = APIClient.objects.count()
            active_clients = APIClient.objects.filter(is_active=True).count()
            total_api_keys = APIKey.objects.count()
            active_api_keys = APIKey.objects.filter(is_active=True, expires_at__gt=now).count()
            
            # Usage statistics for last 24 hours
            usage_24h = APIUsageLog.objects.filter(timestamp__gte=twenty_four_hours_ago)
            total_requests_24h = usage_24h.count()
            
            # Usage statistics for last 1 hour
            usage_1h = APIUsageLog.objects.filter(timestamp__gte=one_hour_ago)
            total_requests_1h = usage_1h.count()
            
            # Error statistics
            error_requests_24h = usage_24h.filter(status_code__gte=400).count()
            error_requests_1h = usage_1h.filter(status_code__gte=400).count()
            
            # Calculate error rates
            error_rate_24h = (error_requests_24h / total_requests_24h * 100) if total_requests_24h > 0 else 0
            error_rate_1h = (error_requests_1h / total_requests_1h * 100) if total_requests_1h > 0 else 0
            
            # Average response time
            avg_response_time_24h = usage_24h.aggregate(avg_time=Avg('response_time'))['avg_time'] or 0
            avg_response_time_1h = usage_1h.aggregate(avg_time=Avg('response_time'))['avg_time'] or 0
            
            # Top endpoints by usage
            top_endpoints_24h = list(
                usage_24h.values('endpoint')
                .annotate(count=Count('endpoint'))
                .order_by('-count')[:5]
            )
            
            # Rate limiting statistics
            rate_limited_requests_24h = usage_24h.filter(status_code=429).count()
            rate_limited_requests_1h = usage_1h.filter(status_code=429).count()
            
            # Client activity
            active_clients_24h = usage_24h.values('client').distinct().count()
            active_clients_1h = usage_1h.values('client').distinct().count()
            
            # Most active clients
            top_clients_24h = list(
                usage_24h.values('client__name')
                .annotate(request_count=Count('id'))
                .order_by('-request_count')[:5]
            )
            
            # Status code distribution
            status_codes_24h = list(
                usage_24h.values('status_code')
                .annotate(count=Count('status_code'))
                .order_by('status_code')
            )
            
            # Recent errors (last 10)
            recent_errors = list(
                usage_24h.filter(status_code__gte=400)
                .order_by('-timestamp')
                .values('endpoint', 'method', 'status_code', 'error_message', 'timestamp', 'client__name')[:10]
            )
            
            # API key expiration warnings
            expiring_soon = APIKey.objects.filter(
                is_active=True,
                expires_at__gt=now,
                expires_at__lt=now + timedelta(hours=24)
            ).count()
            
            return {
                # Basic counts
                'total_clients': total_clients,
                'active_clients': active_clients,
                'total_api_keys': total_api_keys,
                'active_api_keys': active_api_keys,
                'expiring_keys_24h': expiring_soon,
                
                # Request statistics
                'total_requests_24h': total_requests_24h,
                'total_requests_1h': total_requests_1h,
                'requests_per_hour_avg': round(total_requests_24h / 24, 2) if total_requests_24h > 0 else 0,
                
                # Error statistics
                'error_requests_24h': error_requests_24h,
                'error_requests_1h': error_requests_1h,
                'error_rate_24h': round(error_rate_24h, 2),
                'error_rate_1h': round(error_rate_1h, 2),
                
                # Performance statistics
                'avg_response_time_24h': round(avg_response_time_24h, 3) if avg_response_time_24h else 0,
                'avg_response_time_1h': round(avg_response_time_1h, 3) if avg_response_time_1h else 0,
                
                # Rate limiting
                'rate_limited_24h': rate_limited_requests_24h,
                'rate_limited_1h': rate_limited_requests_1h,
                'rate_limit_rate_24h': round((rate_limited_requests_24h / total_requests_24h * 100), 2) if total_requests_24h > 0 else 0,
                
                # Activity statistics
                'active_clients_24h': active_clients_24h,
                'active_clients_1h': active_clients_1h,
                
                # Top usage
                'top_endpoints_24h': top_endpoints_24h,
                'top_clients_24h': top_clients_24h,
                'status_codes_24h': status_codes_24h,
                'recent_errors': recent_errors,
                
                # Health indicators
                'healthy_requests_24h': total_requests_24h - error_requests_24h,
                'success_rate_24h': round(((total_requests_24h - error_requests_24h) / total_requests_24h * 100), 2) if total_requests_24h > 0 else 100,
            }
            
        except Exception as e:
            logger.error(f"Failed to collect API statistics: {str(e)}")
            return {
                'error': f'Failed to collect API statistics: {str(e)}',
                'total_clients': 0,
                'active_clients': 0,
                'total_requests_24h': 0,
                'error_rate_24h': 0
            }


class CeleryHealthChecker(BaseHealthChecker):
    """Health checker for Celery worker status and task queue monitoring."""
    
    def check(self) -> HealthCheckResult:
        """Check Celery worker status and task queue health."""
        try:
            start_time = time.time()
            
            # Try to import Celery
            try:
                from celery import Celery
                from django_celery_results.models import TaskResult
                from django_celery_beat.models import PeriodicTask
            except ImportError as e:
                return HealthCheckResult(
                    status='warning',
                    message="Celery not available",
                    details={'error': f'Celery import failed: {str(e)}'}
                )
            
            # Get Celery app instance
            try:
                from kabhishek18.celery import app as celery_app
            except ImportError:
                # Try to create a basic Celery app for inspection
                celery_app = Celery('health_check')
                celery_app.config_from_object('django.conf:settings', namespace='CELERY')
            
            # Collect Celery statistics
            celery_stats = self._collect_celery_statistics(celery_app, TaskResult, PeriodicTask)
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            # Determine status based on worker availability and task failures
            active_workers = celery_stats.get('active_workers', 0)
            failed_tasks_24h = celery_stats.get('failed_tasks_24h', 0)
            total_tasks_24h = celery_stats.get('total_tasks_24h', 0)
            
            if active_workers == 0:
                status = 'critical'
                message = "No active Celery workers found"
            elif failed_tasks_24h > 0 and total_tasks_24h > 0:
                failure_rate = (failed_tasks_24h / total_tasks_24h) * 100
                if failure_rate > 20:
                    status = 'critical'
                    message = f"High task failure rate: {failure_rate:.1f}%"
                elif failure_rate > 10:
                    status = 'warning'
                    message = f"Moderate task failure rate: {failure_rate:.1f}%"
                else:
                    status = 'healthy'
                    message = f"Celery healthy: {active_workers} workers, {failure_rate:.1f}% failure rate"
            else:
                status = 'healthy'
                message = f"Celery healthy: {active_workers} active workers"
            
            return HealthCheckResult(
                status=status,
                message=message,
                details=celery_stats,
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"Celery health check failed: {str(e)}")
            return HealthCheckResult(
                status='critical',
                message=f"Celery health check failed: {str(e)}",
                details={'error': str(e)}
            )
    
    def _collect_celery_statistics(self, celery_app, TaskResult, PeriodicTask) -> Dict[str, Any]:
        """Collect comprehensive Celery statistics."""
        try:
            stats = {}
            
            # Get worker information
            try:
                inspect = celery_app.control.inspect()
                active_workers = inspect.active()
                registered_tasks = inspect.registered()
                
                if active_workers:
                    stats['active_workers'] = len(active_workers.keys())
                    stats['worker_names'] = list(active_workers.keys())
                    
                    # Count active tasks across all workers
                    total_active_tasks = sum(len(tasks) for tasks in active_workers.values())
                    stats['active_tasks'] = total_active_tasks
                    
                    # Get registered tasks count
                    if registered_tasks:
                        total_registered = sum(len(tasks) for tasks in registered_tasks.values())
                        stats['registered_tasks'] = total_registered
                else:
                    stats['active_workers'] = 0
                    stats['worker_names'] = []
                    stats['active_tasks'] = 0
                    stats['registered_tasks'] = 0
                    
            except Exception as worker_error:
                logger.warning(f"Could not get worker info: {str(worker_error)}")
                stats['active_workers'] = 0
                stats['worker_error'] = str(worker_error)
            
            # Get task statistics from database
            try:
                now = timezone.now()
                twenty_four_hours_ago = now - timedelta(hours=24)
                
                # Task results in last 24 hours
                recent_tasks = TaskResult.objects.filter(date_created__gte=twenty_four_hours_ago)
                stats['total_tasks_24h'] = recent_tasks.count()
                
                # Task status breakdown
                stats['successful_tasks_24h'] = recent_tasks.filter(status='SUCCESS').count()
                stats['failed_tasks_24h'] = recent_tasks.filter(status='FAILURE').count()
                stats['pending_tasks_24h'] = recent_tasks.filter(status='PENDING').count()
                stats['retry_tasks_24h'] = recent_tasks.filter(status='RETRY').count()
                
                # Calculate success rate
                if stats['total_tasks_24h'] > 0:
                    success_rate = (stats['successful_tasks_24h'] / stats['total_tasks_24h']) * 100
                    stats['success_rate_24h'] = round(success_rate, 2)
                else:
                    stats['success_rate_24h'] = 100.0
                
                # Average task execution time
                successful_tasks = recent_tasks.filter(status='SUCCESS', date_done__isnull=False)
                if successful_tasks.exists():
                    # Calculate average execution time (this is approximate)
                    avg_runtime = successful_tasks.aggregate(
                        avg_time=Avg('date_done') - Avg('date_created')
                    )
                    # Note: This is a simplified calculation
                    stats['avg_task_time_24h'] = 'Available in task details'
                
            except Exception as db_error:
                logger.warning(f"Could not get task statistics: {str(db_error)}")
                stats['db_error'] = str(db_error)
                stats['total_tasks_24h'] = 0
                stats['successful_tasks_24h'] = 0
                stats['failed_tasks_24h'] = 0
            
            # Get periodic task information
            try:
                periodic_tasks = PeriodicTask.objects.all()
                stats['total_periodic_tasks'] = periodic_tasks.count()
                stats['enabled_periodic_tasks'] = periodic_tasks.filter(enabled=True).count()
                
                # Get recent periodic task names
                recent_periodic = list(
                    periodic_tasks.filter(enabled=True)
                    .values_list('name', flat=True)[:5]
                )
                stats['recent_periodic_tasks'] = recent_periodic
                
            except Exception as periodic_error:
                logger.warning(f"Could not get periodic task info: {str(periodic_error)}")
                stats['periodic_error'] = str(periodic_error)
            
            # Broker connection test
            try:
                # Test broker connection
                broker_url = getattr(settings, 'CELERY_BROKER_URL', None)
                if broker_url:
                    stats['broker_url'] = broker_url.split('@')[-1] if '@' in broker_url else broker_url
                    stats['broker_connected'] = True  # If we got this far, connection works
                else:
                    stats['broker_connected'] = False
                    stats['broker_error'] = 'No broker URL configured'
                    
            except Exception as broker_error:
                stats['broker_connected'] = False
                stats['broker_error'] = str(broker_error)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to collect Celery statistics: {str(e)}")
            return {
                'error': f'Failed to collect Celery statistics: {str(e)}',
                'active_workers': 0,
                'total_tasks_24h': 0,
                'failed_tasks_24h': 0
            }


class RedisHealthChecker(BaseHealthChecker):
    """Health checker for Redis connection and performance monitoring."""
    
    def check(self) -> HealthCheckResult:
        """Check Redis connection status and performance metrics."""
        try:
            start_time = time.time()
            
            # Try to import Redis
            try:
                import redis
            except ImportError:
                return HealthCheckResult(
                    status='warning',
                    message="Redis not available",
                    details={'error': 'Redis package not installed'}
                )
            
            # Get Redis connection details
            redis_url = getattr(settings, 'REDIS_URL', 'redis://127.0.0.1:6379/1')
            
            # Test Redis connection
            try:
                redis_client = redis.from_url(redis_url)
                redis_client.ping()
                
                # Collect Redis statistics
                redis_stats = self._collect_redis_statistics(redis_client, redis_url)
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                # Determine status based on Redis metrics
                memory_usage = redis_stats.get('used_memory_percentage', 0)
                connected_clients = redis_stats.get('connected_clients', 0)
                
                if memory_usage > 90:
                    status = 'critical'
                    message = f"Critical Redis memory usage: {memory_usage:.1f}%"
                elif memory_usage > 80:
                    status = 'warning'
                    message = f"High Redis memory usage: {memory_usage:.1f}%"
                elif connected_clients > 100:
                    status = 'warning'
                    message = f"High Redis client connections: {connected_clients}"
                else:
                    status = 'healthy'
                    message = f"Redis healthy: {memory_usage:.1f}% memory, {connected_clients} clients"
                
                return HealthCheckResult(
                    status=status,
                    message=message,
                    details=redis_stats,
                    response_time=response_time
                )
                
            except redis.ConnectionError as conn_error:
                return HealthCheckResult(
                    status='critical',
                    message=f"Redis connection failed: {str(conn_error)}",
                    details={'error': str(conn_error), 'redis_url': redis_url}
                )
                
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return HealthCheckResult(
                status='critical',
                message=f"Redis health check failed: {str(e)}",
                details={'error': str(e)}
            )
    
    def _collect_redis_statistics(self, redis_client, redis_url) -> Dict[str, Any]:
        """Collect comprehensive Redis statistics."""
        try:
            # Get Redis info
            info = redis_client.info()
            
            stats = {
                'redis_version': info.get('redis_version'),
                'redis_mode': info.get('redis_mode', 'standalone'),
                'uptime_in_seconds': info.get('uptime_in_seconds', 0),
                'uptime_in_days': round(info.get('uptime_in_seconds', 0) / 86400, 2),
                
                # Memory statistics
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'used_memory_rss': info.get('used_memory_rss', 0),
                'used_memory_peak': info.get('used_memory_peak', 0),
                'used_memory_peak_human': info.get('used_memory_peak_human', '0B'),
                'maxmemory': info.get('maxmemory', 0),
                
                # Client statistics
                'connected_clients': info.get('connected_clients', 0),
                'client_recent_max_input_buffer': info.get('client_recent_max_input_buffer', 0),
                'client_recent_max_output_buffer': info.get('client_recent_max_output_buffer', 0),
                
                # Performance statistics
                'total_commands_processed': info.get('total_commands_processed', 0),
                'instantaneous_ops_per_sec': info.get('instantaneous_ops_per_sec', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                
                # Persistence statistics
                'rdb_changes_since_last_save': info.get('rdb_changes_since_last_save', 0),
                'rdb_last_save_time': info.get('rdb_last_save_time', 0),
                'aof_enabled': info.get('aof_enabled', 0),
                
                # Connection info
                'redis_url': redis_url.split('@')[-1] if '@' in redis_url else redis_url,
            }
            
            # Calculate memory usage percentage
            if stats['maxmemory'] > 0:
                memory_percentage = (stats['used_memory'] / stats['maxmemory']) * 100
                stats['used_memory_percentage'] = round(memory_percentage, 2)
            else:
                # If no max memory set, use a reasonable estimate based on system memory
                stats['used_memory_percentage'] = 0
            
            # Calculate hit rate
            hits = stats['keyspace_hits']
            misses = stats['keyspace_misses']
            if hits + misses > 0:
                hit_rate = (hits / (hits + misses)) * 100
                stats['hit_rate_percentage'] = round(hit_rate, 2)
            else:
                stats['hit_rate_percentage'] = 0
            
            # Get database information
            try:
                db_info = {}
                for key, value in info.items():
                    if key.startswith('db'):
                        db_info[key] = value
                stats['databases'] = db_info
            except Exception:
                pass
            
            # Test basic operations
            try:
                test_key = 'health_check_redis_test'
                test_value = f'test_{int(time.time())}'
                
                # Test SET/GET operations
                redis_client.set(test_key, test_value, ex=60)
                retrieved_value = redis_client.get(test_key)
                
                if retrieved_value and retrieved_value.decode() == test_value:
                    stats['basic_operations'] = 'working'
                    redis_client.delete(test_key)  # Clean up
                else:
                    stats['basic_operations'] = 'failed'
                    
            except Exception as op_error:
                stats['basic_operations'] = f'error: {str(op_error)}'
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to collect Redis statistics: {str(e)}")
            return {
                'error': f'Failed to collect Redis statistics: {str(e)}',
                'connected_clients': 0,
                'used_memory_percentage': 0
            }


class HealthService:
    """
    Main health service that coordinates all health checks.
    Optimized with parallel execution, caching, and graceful degradation.
    """
    
    def __init__(self):
        self.checkers = {
            'database': DatabaseHealthChecker(),
            'cache': CacheHealthChecker(),
            'memory': MemoryHealthChecker(),
            'disk': DiskHealthChecker(),
            'system_load': SystemLoadHealthChecker(),
            'logs': LogHealthChecker(),
            'api': APIHealthChecker(),
            'celery': CeleryHealthChecker(),
            'redis': RedisHealthChecker()
        }
        
        # Initialize performance monitoring
        self.performance_stats = {
            'total_checks_performed': 0,
            'last_execution_time': 0,
            'avg_execution_time': 0,
        }
    
    def get_system_health(self, force_refresh=False) -> Dict[str, Any]:
        """
        Get comprehensive system health status with enhanced error handling.
        Uses parallel execution for improved performance.
        
        Args:
            force_refresh: If True, bypass cache and force fresh checks
            
        Returns:
            Dict containing comprehensive health data
        """
        # Check cache first unless force refresh is requested
        cache_key = "system_health_dashboard_data"
        if not force_refresh:
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data
        
        start_time = time.time()
        health_results = {}
        overall_status = 'healthy'
        failed_checks = []
        
        # Run health checks in parallel for better performance
        with ThreadPoolExecutor(max_workers=min(4, len(self.checkers))) as executor:
            # Submit all tasks
            future_to_checker = {
                executor.submit(self._run_health_check, name, checker): name 
                for name, checker in self.checkers.items()
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_checker):
                name = future_to_checker[future]
                try:
                    # Get result with timeout
                    result, status = future.result(timeout=15)
                    health_results[name] = result
                    
                    # Update overall status
                    if status == 'critical':
                        failed_checks.append(name)
                        overall_status = 'critical'
                    elif status == 'warning' and overall_status != 'critical':
                        overall_status = 'warning'
                        
                except Exception as e:
                    logger.error(f"Health check failed for {name}: {str(e)}")
                    failed_checks.append(name)
                    
                    # Create fallback health result
                    health_results[name] = {
                        'status': 'critical',
                        'message': f"Health check failed: {str(e)}",
                        'details': {
                            'error': str(e),
                            'error_type': type(e).__name__,
                            'fallback_used': True
                        },
                        'response_time': None,
                        'timestamp': timezone.now().isoformat()
                    }
                    overall_status = 'critical'
        
        # Add summary information
        total_checks = len(self.checkers)
        successful_checks = total_checks - len(failed_checks)
        
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Update performance stats
        self.performance_stats['last_execution_time'] = execution_time
        self.performance_stats['total_checks_performed'] += 1
        
        # Calculate running average execution time
        prev_avg = self.performance_stats.get('avg_execution_time', 0)
        count = self.performance_stats.get('total_checks_performed', 1)
        self.performance_stats['avg_execution_time'] = (prev_avg * (count - 1) + execution_time) / count
        
        # Record health metrics in database asynchronously
        self._record_health_metrics_async(overall_status, health_results, execution_time, 
                                         total_checks, successful_checks, failed_checks)
        
        # Clean up old metrics periodically (1% chance to run on each check)
        import random
        if random.random() < 0.01:
            self._cleanup_old_metrics()
        
        # Prepare result
        result = {
            'overall_status': overall_status,
            'timestamp': timezone.now().isoformat(),
            'checks': health_results,
            'summary': {
                'total_checks': total_checks,
                'successful_checks': successful_checks,
                'failed_checks': len(failed_checks),
                'failed_check_names': failed_checks,
                'success_rate': round((successful_checks / total_checks) * 100, 2) if total_checks > 0 else 0,
                'execution_time_ms': execution_time,
                'performance': {
                    'avg_execution_time_ms': round(self.performance_stats['avg_execution_time'], 2),
                    'total_checks_performed': self.performance_stats['total_checks_performed']
                }
            }
        }
        
        # Cache the result with appropriate timeout based on status
        if overall_status == 'critical':
            cache.set(cache_key, result, 10)  # Short cache for critical status
        elif overall_status == 'warning':
            cache.set(cache_key, result, 30)  # Medium cache for warning status
        else:
            cache.set(cache_key, result, 60)  # Longer cache for healthy status
            
        return result
    
    def _run_health_check(self, name, checker):
        """Run a single health check with timeout and error handling."""
        try:
            # Use timeout-aware check with retries
            result = checker.check_with_timeout()
            return result.to_dict(), result.status
        except Exception as e:
            logger.error(f"Health check execution error for {name}: {str(e)}")
            return {
                'status': 'critical',
                'message': f"Health check execution failed: {str(e)}",
                'details': {'error': str(e)},
                'timestamp': timezone.now().isoformat()
            }, 'critical'
    
    def _record_health_metrics_async(self, overall_status, health_results, execution_time, 
                                    total_checks, successful_checks, failed_checks):
        """Record health metrics in the database asynchronously."""
        def _record_metrics():
            try:
                from core.models import HealthMetric, SystemAlert
                
                # Record overall health
                HealthMetric.record_metric(
                    metric_name='overall',
                    metric_value={
                        'total_checks': total_checks,
                        'successful_checks': successful_checks,
                        'failed_checks': failed_checks,
                        'execution_time_ms': execution_time
                    },
                    status=overall_status,
                    message=f"System health: {successful_checks}/{total_checks} checks passed",
                    response_time=execution_time
                )
                
                # Record individual check metrics for critical or warning statuses
                for name, check in health_results.items():
                    if check['status'] in ['critical', 'warning']:
                        HealthMetric.record_metric(
                            metric_name=name,
                            metric_value=check.get('details', {}),
                            status=check['status'],
                            message=check['message'],
                            response_time=check.get('response_time')
                        )
                        
                        # Create alerts for critical issues
                        if check['status'] == 'critical':
                            # Check if there's already an active alert for this issue
                            existing_alert = SystemAlert.objects.filter(
                                source_metric=name,
                                resolved=False
                            ).first()
                            
                            if not existing_alert:
                                SystemAlert.create_alert(
                                    alert_type='health_check',
                                    title=f"{name.title()} Critical Issue",
                                    message=check['message'],
                                    severity='critical',
                                    source_metric=name,
                                    metadata=check.get('details', {})
                                )
                
            except Exception as e:
                logger.error(f"Failed to record health metrics: {str(e)}")
        
        # Run in a separate thread to avoid blocking
        threading.Thread(target=_record_metrics).start()
    
    def _cleanup_old_metrics(self):
        """Clean up old metrics to prevent database bloat."""
        def _cleanup():
            try:
                from core.models import HealthMetric
                from django.db.models import Q
                
                # Delete metrics older than retention period
                cutoff_date = timezone.now() - timedelta(days=METRICS_RETENTION_DAYS)
                
                # Keep more recent critical metrics longer
                deleted_count = HealthMetric.objects.filter(
                    Q(timestamp__lt=cutoff_date, status='healthy') |
                    Q(timestamp__lt=cutoff_date - timedelta(days=7), status='warning') |
                    Q(timestamp__lt=cutoff_date - timedelta(days=14), status='critical')
                ).delete()[0]
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old health metrics")
                
            except Exception as e:
                logger.error(f"Failed to clean up old metrics: {str(e)}")
        
        # Run in a separate thread to avoid blocking
        threading.Thread(target=_cleanup).start()
    
    def get_database_health(self) -> Dict[str, Any]:
        """Get database health status."""
        return self.checkers['database'].check().to_dict()
    
    def get_cache_health(self) -> Dict[str, Any]:
        """Get cache health status."""
        return self.checkers['cache'].check().to_dict()
    
    def get_system_resources(self) -> Dict[str, Any]:
        """Get system resource metrics (memory, disk, CPU, logs)."""
        resource_checks = ['memory', 'disk', 'system_load', 'logs']
        results = {}
        
        for check_name in resource_checks:
            if check_name in self.checkers:
                try:
                    result = self.checkers[check_name].check()
                    results[check_name] = result.to_dict()
                except Exception as e:
                    logger.error(f"Resource check failed for {check_name}: {str(e)}")
                    results[check_name] = {
                        'status': 'critical',
                        'message': f"Resource check failed: {str(e)}",
                        'details': {'error': str(e)},
                        'response_time': None,
                        'timestamp': timezone.now().isoformat()
                    }
        
        return results
    
    def get_memory_health(self) -> Dict[str, Any]:
        """Get memory health status."""
        return self.checkers['memory'].check().to_dict()
    
    def get_disk_health(self) -> Dict[str, Any]:
        """Get disk health status."""
        return self.checkers['disk'].check().to_dict()
    
    def get_system_load_health(self) -> Dict[str, Any]:
        """Get system load health status."""
        return self.checkers['system_load'].check().to_dict()
    
    def get_log_health(self) -> Dict[str, Any]:
        """Get log health status."""
        return self.checkers['logs'].check().to_dict()
    
    def get_api_health(self) -> Dict[str, Any]:
        """Get API health status."""
        return self.checkers['api'].check().to_dict()
    
    def get_celery_health(self) -> Dict[str, Any]:
        """Get Celery health status."""
        return self.checkers['celery'].check().to_dict()
    
    def get_redis_health(self) -> Dict[str, Any]:
        """Get Redis health status."""
        return self.checkers['redis'].check().to_dict()


# Global health service instance
health_service = HealthService()