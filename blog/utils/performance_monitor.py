"""
Performance monitoring utilities for schema markup generation.

This module provides tools to measure and monitor the performance impact
of schema markup generation on page load times and database queries.
"""

import time
import logging
from contextlib import contextmanager
from typing import Dict, Any, Optional
from functools import wraps

from django.db import connection
from django.conf import settings
from django.core.cache import caches

logger = logging.getLogger(__name__)


class SchemaPerformanceMonitor:
    """Monitor performance metrics for schema markup generation."""
    
    def __init__(self):
        self.metrics = {
            'schema_generation_time': [],
            'template_render_time': [],
            'cache_hit_rate': {'hits': 0, 'misses': 0},
            'database_queries': [],
        }
    
    @contextmanager
    def measure_schema_generation(self, post_id: int):
        """
        Context manager to measure schema generation time.
        
        Args:
            post_id: ID of the post being processed
        """
        start_time = time.time()
        start_queries = len(connection.queries)
        
        try:
            yield
        finally:
            end_time = time.time()
            end_queries = len(connection.queries)
            
            generation_time = (end_time - start_time) * 1000  # Convert to milliseconds
            query_count = end_queries - start_queries
            
            self.metrics['schema_generation_time'].append({
                'post_id': post_id,
                'time_ms': generation_time,
                'query_count': query_count,
                'timestamp': time.time()
            })
            
            logger.info(f"Schema generation for post {post_id}: {generation_time:.2f}ms, {query_count} queries")
    
    @contextmanager
    def measure_template_render(self, template_name: str, post_id: int):
        """
        Context manager to measure template rendering time.
        
        Args:
            template_name: Name of the template being rendered
            post_id: ID of the post being processed
        """
        start_time = time.time()
        
        try:
            yield
        finally:
            end_time = time.time()
            render_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            self.metrics['template_render_time'].append({
                'template': template_name,
                'post_id': post_id,
                'time_ms': render_time,
                'timestamp': time.time()
            })
            
            logger.info(f"Template {template_name} render for post {post_id}: {render_time:.2f}ms")
    
    def record_cache_hit(self, cache_type: str):
        """Record a cache hit."""
        self.metrics['cache_hit_rate']['hits'] += 1
        logger.debug(f"Cache hit: {cache_type}")
    
    def record_cache_miss(self, cache_type: str):
        """Record a cache miss."""
        self.metrics['cache_hit_rate']['misses'] += 1
        logger.debug(f"Cache miss: {cache_type}")
    
    def get_cache_hit_rate(self) -> float:
        """
        Calculate cache hit rate as a percentage.
        
        Returns:
            Cache hit rate as a percentage (0-100)
        """
        total = self.metrics['cache_hit_rate']['hits'] + self.metrics['cache_hit_rate']['misses']
        if total == 0:
            return 0.0
        return (self.metrics['cache_hit_rate']['hits'] / total) * 100
    
    def get_average_generation_time(self) -> float:
        """
        Get average schema generation time in milliseconds.
        
        Returns:
            Average generation time in milliseconds
        """
        times = [m['time_ms'] for m in self.metrics['schema_generation_time']]
        return sum(times) / len(times) if times else 0.0
    
    def get_average_template_time(self) -> float:
        """
        Get average template rendering time in milliseconds.
        
        Returns:
            Average template rendering time in milliseconds
        """
        times = [m['time_ms'] for m in self.metrics['template_render_time']]
        return sum(times) / len(times) if times else 0.0
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """
        Get database query statistics.
        
        Returns:
            Dictionary with query statistics
        """
        query_counts = [m['query_count'] for m in self.metrics['schema_generation_time']]
        if not query_counts:
            return {'average': 0, 'max': 0, 'min': 0, 'total': 0}
        
        return {
            'average': sum(query_counts) / len(query_counts),
            'max': max(query_counts),
            'min': min(query_counts),
            'total': sum(query_counts)
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report.
        
        Returns:
            Dictionary containing performance metrics
        """
        return {
            'cache_hit_rate': self.get_cache_hit_rate(),
            'average_generation_time_ms': self.get_average_generation_time(),
            'average_template_time_ms': self.get_average_template_time(),
            'query_statistics': self.get_query_statistics(),
            'total_schema_generations': len(self.metrics['schema_generation_time']),
            'total_template_renders': len(self.metrics['template_render_time']),
        }
    
    def reset_metrics(self):
        """Reset all performance metrics."""
        self.metrics = {
            'schema_generation_time': [],
            'template_render_time': [],
            'cache_hit_rate': {'hits': 0, 'misses': 0},
            'database_queries': [],
        }
        logger.info("Performance metrics reset")


# Global performance monitor instance
performance_monitor = SchemaPerformanceMonitor()


def monitor_schema_performance(func):
    """
    Decorator to monitor schema generation performance.
    
    Args:
        func: Function to monitor
        
    Returns:
        Wrapped function with performance monitoring
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract post_id if available
        post_id = None
        if args and hasattr(args[0], 'id'):
            post_id = args[0].id
        elif 'post' in kwargs and hasattr(kwargs['post'], 'id'):
            post_id = kwargs['post'].id
        
        if post_id:
            with performance_monitor.measure_schema_generation(post_id):
                return func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    
    return wrapper


def monitor_template_performance(template_name: str):
    """
    Decorator to monitor template rendering performance.
    
    Args:
        template_name: Name of the template being monitored
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract post_id if available
            post_id = None
            if args and hasattr(args[0], 'id'):
                post_id = args[0].id
            elif 'post' in kwargs and hasattr(kwargs['post'], 'id'):
                post_id = kwargs['post'].id
            
            if post_id:
                with performance_monitor.measure_template_render(template_name, post_id):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


@contextmanager
def measure_page_load_impact():
    """
    Context manager to measure overall page load impact.
    
    Usage:
        with measure_page_load_impact():
            # Code that affects page load time
            pass
    """
    start_time = time.time()
    start_queries = len(connection.queries)
    
    try:
        yield
    finally:
        end_time = time.time()
        end_queries = len(connection.queries)
        
        total_time = (end_time - start_time) * 1000  # Convert to milliseconds
        query_count = end_queries - start_queries
        
        logger.info(f"Page load impact: {total_time:.2f}ms, {query_count} queries")
        
        # Store in cache for monitoring dashboard
        try:
            cache = caches['default']
            cache.set('schema_page_load_impact', {
                'time_ms': total_time,
                'query_count': query_count,
                'timestamp': time.time()
            }, 300)  # 5 minutes
        except Exception as e:
            logger.warning(f"Failed to cache page load impact: {str(e)}")


def get_cache_statistics() -> Dict[str, Any]:
    """
    Get cache statistics for schema-related caches.
    
    Returns:
        Dictionary with cache statistics
    """
    stats = {}
    
    try:
        # Get schema cache stats
        schema_cache = caches['schema_cache']
        if hasattr(schema_cache, 'get_stats'):
            stats['schema_cache'] = schema_cache.get_stats()
        
        # Get template cache stats
        template_cache = caches['template_cache']
        if hasattr(template_cache, 'get_stats'):
            stats['template_cache'] = template_cache.get_stats()
        
        # Add performance monitor stats
        stats['performance_monitor'] = performance_monitor.get_performance_report()
        
    except Exception as e:
        logger.error(f"Error getting cache statistics: {str(e)}")
        stats['error'] = str(e)
    
    return stats


def log_performance_summary():
    """Log a summary of performance metrics."""
    report = performance_monitor.get_performance_report()
    
    logger.info("Schema Performance Summary:")
    logger.info(f"  Cache Hit Rate: {report['cache_hit_rate']:.1f}%")
    logger.info(f"  Avg Generation Time: {report['average_generation_time_ms']:.2f}ms")
    logger.info(f"  Avg Template Time: {report['average_template_time_ms']:.2f}ms")
    logger.info(f"  Avg Queries per Generation: {report['query_statistics']['average']:.1f}")
    logger.info(f"  Total Generations: {report['total_schema_generations']}")


def optimize_database_queries():
    """
    Provide recommendations for optimizing database queries.
    
    Returns:
        List of optimization recommendations
    """
    recommendations = []
    
    query_stats = performance_monitor.get_query_statistics()
    
    if query_stats['average'] > 5:
        recommendations.append(
            "High average query count detected. Consider using select_related() and "
            "prefetch_related() when fetching posts for schema generation."
        )
    
    if query_stats['max'] > 10:
        recommendations.append(
            "Very high maximum query count detected. Review N+1 query patterns "
            "in schema generation code."
        )
    
    cache_hit_rate = performance_monitor.get_cache_hit_rate()
    if cache_hit_rate < 50:
        recommendations.append(
            f"Low cache hit rate ({cache_hit_rate:.1f}%). Consider increasing cache "
            "timeout or reviewing cache invalidation strategy."
        )
    
    avg_time = performance_monitor.get_average_generation_time()
    if avg_time > 100:
        recommendations.append(
            f"High average generation time ({avg_time:.2f}ms). Consider optimizing "
            "schema generation logic or increasing cache usage."
        )
    
    return recommendations