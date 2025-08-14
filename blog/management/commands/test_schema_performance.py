"""
Management command to test and measure schema markup performance.

This command provides comprehensive testing of schema markup generation
performance, including cache effectiveness, database query optimization,
and overall page load impact measurement.
"""

import time
import statistics
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.test import RequestFactory
from django.core.cache import caches
from django.template.loader import render_to_string

from blog.models import Post
from blog.services.schema_service import SchemaService
from blog.utils.performance_monitor import (
    performance_monitor, 
    measure_page_load_impact,
    get_cache_statistics,
    log_performance_summary,
    optimize_database_queries
)


class Command(BaseCommand):
    help = 'Test and measure schema markup performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--posts',
            type=int,
            default=10,
            help='Number of posts to test (default: 10)'
        )
        parser.add_argument(
            '--iterations',
            type=int,
            default=3,
            help='Number of iterations per test (default: 3)'
        )
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear cache before testing'
        )
        parser.add_argument(
            '--warm-cache',
            action='store_true',
            help='Warm up cache before performance testing'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed performance metrics'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting schema markup performance testing...')
        )
        
        # Get test parameters
        num_posts = options['posts']
        iterations = options['iterations']
        clear_cache = options['clear_cache']
        warm_cache = options['warm_cache']
        detailed = options['detailed']
        
        # Get test posts
        posts = self.get_test_posts(num_posts)
        if not posts:
            raise CommandError('No posts found for testing')
        
        self.stdout.write(f'Testing with {len(posts)} posts, {iterations} iterations each')
        
        # Clear cache if requested
        if clear_cache:
            self.clear_all_caches()
            self.stdout.write('Cache cleared')
        
        # Warm up cache if requested
        if warm_cache:
            self.warm_up_cache(posts)
            self.stdout.write('Cache warmed up')
        
        # Reset performance monitor
        performance_monitor.reset_metrics()
        
        # Run performance tests
        results = self.run_performance_tests(posts, iterations)
        
        # Display results
        self.display_results(results, detailed)
        
        # Show optimization recommendations
        self.show_recommendations()
        
        self.stdout.write(
            self.style.SUCCESS('Performance testing completed!')
        )

    def get_test_posts(self, num_posts):
        """Get posts for testing with optimized queries."""
        return Post.objects.select_related(
            'author',
            'author__profile'
        ).prefetch_related(
            'categories',
            'tags',
            'media_items'
        ).filter(
            status='published'
        )[:num_posts]

    def clear_all_caches(self):
        """Clear all caches."""
        try:
            caches['default'].clear()
            caches['schema_cache'].clear()
            caches['template_cache'].clear()
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Error clearing cache: {str(e)}')
            )

    def warm_up_cache(self, posts):
        """Warm up cache with test posts."""
        request_factory = RequestFactory()
        request = request_factory.get('/')
        
        for post in posts:
            try:
                # Generate schema to warm up cache
                SchemaService.generate_article_schema(post, request)
                SchemaService.generate_publisher_schema()
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Error warming cache for post {post.id}: {str(e)}')
                )

    def run_performance_tests(self, posts, iterations):
        """Run comprehensive performance tests."""
        results = {
            'schema_generation': [],
            'template_rendering': [],
            'database_queries': [],
            'cache_performance': {},
            'page_load_impact': []
        }
        
        request_factory = RequestFactory()
        request = request_factory.get('/')
        
        self.stdout.write('Running schema generation tests...')
        
        for iteration in range(iterations):
            self.stdout.write(f'  Iteration {iteration + 1}/{iterations}')
            
            for post in posts:
                # Test schema generation
                schema_time, query_count = self.test_schema_generation(post, request)
                results['schema_generation'].append(schema_time)
                results['database_queries'].append(query_count)
                
                # Test template rendering
                template_time = self.test_template_rendering(post, request)
                results['template_rendering'].append(template_time)
                
                # Test overall page load impact
                page_load_time = self.test_page_load_impact(post, request)
                results['page_load_impact'].append(page_load_time)
        
        # Get cache performance metrics
        results['cache_performance'] = get_cache_statistics()
        
        return results

    def test_schema_generation(self, post, request):
        """Test schema generation performance."""
        start_queries = len(connection.queries)
        start_time = time.time()
        
        try:
            schema_data = SchemaService.generate_article_schema(post, request)
            # Validate to ensure quality
            is_valid = SchemaService.validate_schema(schema_data)
            if not is_valid:
                self.stdout.write(
                    self.style.WARNING(f'Invalid schema generated for post {post.id}')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Schema generation failed for post {post.id}: {str(e)}')
            )
        
        end_time = time.time()
        end_queries = len(connection.queries)
        
        generation_time = (end_time - start_time) * 1000  # Convert to milliseconds
        query_count = end_queries - start_queries
        
        return generation_time, query_count

    def test_template_rendering(self, post, request):
        """Test template rendering performance."""
        start_time = time.time()
        
        try:
            # Simulate template rendering
            context = {
                'post': post,
                'request': request
            }
            rendered = render_to_string('blog/partials/schema_markup.html', context)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Template rendering failed for post {post.id}: {str(e)}')
            )
        
        end_time = time.time()
        render_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        return render_time

    def test_page_load_impact(self, post, request):
        """Test overall page load impact."""
        with measure_page_load_impact():
            # Simulate full page rendering with schema
            try:
                schema_data = SchemaService.generate_article_schema(post, request)
                context = {
                    'post': post,
                    'request': request,
                    'schema_data': schema_data
                }
                rendered = render_to_string('blog/partials/schema_markup.html', context)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Page load test failed for post {post.id}: {str(e)}')
                )
                return 0
        
        # Get the measured time from cache
        try:
            cache = caches['default']
            impact_data = cache.get('schema_page_load_impact')
            return impact_data['time_ms'] if impact_data else 0
        except:
            return 0

    def display_results(self, results, detailed=False):
        """Display performance test results."""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('PERFORMANCE TEST RESULTS'))
        self.stdout.write('='*60)
        
        # Schema generation results
        schema_times = results['schema_generation']
        if schema_times:
            self.stdout.write(f'\nSchema Generation Performance:')
            self.stdout.write(f'  Average: {statistics.mean(schema_times):.2f}ms')
            self.stdout.write(f'  Median:  {statistics.median(schema_times):.2f}ms')
            self.stdout.write(f'  Min:     {min(schema_times):.2f}ms')
            self.stdout.write(f'  Max:     {max(schema_times):.2f}ms')
            if len(schema_times) > 1:
                self.stdout.write(f'  StdDev:  {statistics.stdev(schema_times):.2f}ms')
        
        # Template rendering results
        template_times = results['template_rendering']
        if template_times:
            self.stdout.write(f'\nTemplate Rendering Performance:')
            self.stdout.write(f'  Average: {statistics.mean(template_times):.2f}ms')
            self.stdout.write(f'  Median:  {statistics.median(template_times):.2f}ms')
            self.stdout.write(f'  Min:     {min(template_times):.2f}ms')
            self.stdout.write(f'  Max:     {max(template_times):.2f}ms')
        
        # Database query results
        query_counts = results['database_queries']
        if query_counts:
            self.stdout.write(f'\nDatabase Query Performance:')
            self.stdout.write(f'  Average queries: {statistics.mean(query_counts):.1f}')
            self.stdout.write(f'  Max queries:     {max(query_counts)}')
            self.stdout.write(f'  Min queries:     {min(query_counts)}')
        
        # Page load impact
        page_load_times = [t for t in results['page_load_impact'] if t > 0]
        if page_load_times:
            self.stdout.write(f'\nPage Load Impact:')
            self.stdout.write(f'  Average: {statistics.mean(page_load_times):.2f}ms')
            self.stdout.write(f'  Max:     {max(page_load_times):.2f}ms')
        
        # Cache performance
        cache_perf = results['cache_performance']
        if 'performance_monitor' in cache_perf:
            pm_stats = cache_perf['performance_monitor']
            self.stdout.write(f'\nCache Performance:')
            self.stdout.write(f'  Hit Rate: {pm_stats["cache_hit_rate"]:.1f}%')
            self.stdout.write(f'  Total Generations: {pm_stats["total_schema_generations"]}')
        
        # Detailed results
        if detailed:
            self.stdout.write(f'\nDetailed Performance Monitor Report:')
            log_performance_summary()

    def show_recommendations(self):
        """Show optimization recommendations."""
        recommendations = optimize_database_queries()
        
        if recommendations:
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.WARNING('OPTIMIZATION RECOMMENDATIONS'))
            self.stdout.write('='*60)
            
            for i, rec in enumerate(recommendations, 1):
                self.stdout.write(f'{i}. {rec}')
        else:
            self.stdout.write('\n' + self.style.SUCCESS('No optimization recommendations - performance looks good!'))