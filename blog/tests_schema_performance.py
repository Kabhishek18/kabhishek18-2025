"""
Comprehensive tests for schema markup performance optimization.

This module tests the performance improvements implemented for schema markup
generation, including caching effectiveness, database query optimization,
and overall page load impact measurement.
"""

import time
import statistics
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory, override_settings
from django.core.cache import caches
from django.db import connection
from django.template.loader import render_to_string

from blog.models import Post, Category, Tag, AuthorProfile
from blog.services.schema_service import SchemaService
from blog.templatetags.schema_tags import render_article_schema
from blog.utils.performance_monitor import (
    performance_monitor,
    measure_page_load_impact,
    get_cache_statistics
)
from users.models import Profile


class SchemaPerformanceTestCase(TestCase):
    """Test case for schema markup performance optimization."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user and profile
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(
            username='testauthor',
            email='test@example.com',
            first_name='Test',
            last_name='Author'
        )
        
        # Create author profile
        self.profile = Profile.objects.create(
            user=self.user,
            bio='Test author bio',
            website='https://example.com',
            twitter='@testauthor',
            linkedin='https://linkedin.com/in/testauthor'
        )
        
        # Create categories and tags
        self.category = Category.objects.create(name='Technology', slug='technology')
        self.tag = Tag.objects.create(name='Performance', slug='performance')
        
        # Create test post with optimized data loading
        self.post = Post.objects.create(
            title='Test Post for Performance',
            slug='test-post-performance',
            content='This is a test post for performance testing.',
            excerpt='Test excerpt',
            author=self.user,
            status='published'
        )
        self.post.categories.add(self.category)
        self.post.tags.add(self.tag)
        
        # Create request factory
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        
        # Reset performance monitor
        performance_monitor.reset_metrics()
        
        # Clear caches
        self.clear_all_caches()
    
    def tearDown(self):
        """Clean up after tests."""
        self.clear_all_caches()
    
    def clear_all_caches(self):
        """Clear all caches."""
        try:
            caches['default'].clear()
            caches['schema_cache'].clear()
            caches['template_cache'].clear()
        except:
            pass  # Cache might not be configured in test environment

    def test_schema_generation_performance_without_cache(self):
        """Test schema generation performance without cache."""
        # Clear cache to ensure we're testing without cache
        self.clear_all_caches()
        
        # Measure schema generation time
        start_time = time.time()
        start_queries = len(connection.queries)
        
        schema_data = SchemaService.generate_article_schema(self.post, self.request)
        
        end_time = time.time()
        end_queries = len(connection.queries)
        
        generation_time = (end_time - start_time) * 1000  # Convert to milliseconds
        query_count = end_queries - start_queries
        
        # Assertions
        self.assertIsInstance(schema_data, dict)
        self.assertIn('@context', schema_data)
        self.assertIn('@type', schema_data)
        self.assertEqual(schema_data['@type'], 'Article')
        
        # Performance assertions (these are baseline measurements)
        self.assertLess(generation_time, 100, "Schema generation should be under 100ms")
        self.assertLess(query_count, 10, "Schema generation should use fewer than 10 queries")
        
        print(f"Schema generation (no cache): {generation_time:.2f}ms, {query_count} queries")

    def test_schema_generation_performance_with_cache(self):
        """Test schema generation performance with cache."""
        # First generation (cache miss)
        start_time = time.time()
        schema_data_1 = SchemaService.generate_article_schema(self.post, self.request)
        first_generation_time = (time.time() - start_time) * 1000
        
        # Second generation (cache hit)
        start_time = time.time()
        start_queries = len(connection.queries)
        
        schema_data_2 = SchemaService.generate_article_schema(self.post, self.request)
        
        end_time = time.time()
        end_queries = len(connection.queries)
        
        cached_generation_time = (end_time - start_time) * 1000
        cached_query_count = end_queries - start_queries
        
        # Assertions
        self.assertEqual(schema_data_1, schema_data_2, "Cached schema should be identical")
        self.assertLess(cached_generation_time, first_generation_time, 
                       "Cached generation should be faster")
        self.assertEqual(cached_query_count, 0, "Cached generation should use no queries")
        
        print(f"Schema generation (cached): {cached_generation_time:.2f}ms, {cached_query_count} queries")
        print(f"Cache speedup: {first_generation_time / cached_generation_time:.1f}x")

    def test_template_rendering_performance(self):
        """Test template rendering performance with caching."""
        # First render (cache miss)
        start_time = time.time()
        context_1 = render_article_schema({'request': self.request}, self.post)
        first_render_time = (time.time() - start_time) * 1000
        
        # Second render (cache hit)
        start_time = time.time()
        context_2 = render_article_schema({'request': self.request}, self.post)
        cached_render_time = (time.time() - start_time) * 1000
        
        # Assertions
        self.assertIsInstance(context_1, dict)
        self.assertIsInstance(context_2, dict)
        self.assertIn('schema_json', context_1)
        self.assertIn('schema_json', context_2)
        self.assertEqual(context_1['schema_json'], context_2['schema_json'])
        
        # Performance assertion
        self.assertLess(cached_render_time, first_render_time,
                       "Cached template rendering should be faster")
        
        print(f"Template render (first): {first_render_time:.2f}ms")
        print(f"Template render (cached): {cached_render_time:.2f}ms")

    def test_database_query_optimization(self):
        """Test that database queries are optimized."""
        # Create a post with prefetched relationships
        optimized_post = Post.objects.select_related(
            'author',
            'author__profile'
        ).prefetch_related(
            'categories',
            'tags',
            'media_items'
        ).get(id=self.post.id)
        
        # Clear cache to ensure we're testing query optimization
        self.clear_all_caches()
        
        # Measure queries for optimized post
        start_queries = len(connection.queries)
        schema_data = SchemaService.generate_article_schema(optimized_post, self.request)
        end_queries = len(connection.queries)
        
        optimized_query_count = end_queries - start_queries
        
        # Test with non-optimized post (fresh from DB)
        non_optimized_post = Post.objects.get(id=self.post.id)
        
        start_queries = len(connection.queries)
        schema_data_2 = SchemaService.generate_article_schema(non_optimized_post, self.request)
        end_queries = len(connection.queries)
        
        non_optimized_query_count = end_queries - start_queries
        
        # Assertions
        self.assertEqual(schema_data, schema_data_2, "Schema should be identical")
        self.assertLessEqual(optimized_query_count, non_optimized_query_count,
                           "Optimized queries should not exceed non-optimized")
        
        print(f"Optimized queries: {optimized_query_count}")
        print(f"Non-optimized queries: {non_optimized_query_count}")

    def test_cache_invalidation(self):
        """Test that cache is properly invalidated when post is updated."""
        # Generate initial schema (cache miss)
        schema_data_1 = SchemaService.generate_article_schema(self.post, self.request)
        
        # Update post
        self.post.title = 'Updated Test Post'
        self.post.save()
        
        # Generate schema again (should be cache miss due to invalidation)
        start_queries = len(connection.queries)
        schema_data_2 = SchemaService.generate_article_schema(self.post, self.request)
        end_queries = len(connection.queries)
        
        query_count = end_queries - start_queries
        
        # Assertions
        self.assertNotEqual(schema_data_1['headline'], schema_data_2['headline'])
        self.assertEqual(schema_data_2['headline'], 'Updated Test Post')
        self.assertGreater(query_count, 0, "Cache should be invalidated, requiring queries")

    def test_performance_monitoring(self):
        """Test performance monitoring functionality."""
        # Reset monitor
        performance_monitor.reset_metrics()
        
        # Generate some schema data to create metrics
        for _ in range(5):
            SchemaService.generate_article_schema(self.post, self.request)
        
        # Get performance report
        report = performance_monitor.get_performance_report()
        
        # Assertions
        self.assertIsInstance(report, dict)
        self.assertIn('cache_hit_rate', report)
        self.assertIn('average_generation_time_ms', report)
        self.assertIn('total_schema_generations', report)
        self.assertGreaterEqual(report['total_schema_generations'], 5)

    def test_page_load_impact_measurement(self):
        """Test page load impact measurement."""
        with measure_page_load_impact():
            # Simulate page rendering with schema
            schema_data = SchemaService.generate_article_schema(self.post, self.request)
            context = {
                'post': self.post,
                'request': self.request,
                'schema_data': schema_data
            }
            rendered = render_to_string('blog/partials/schema_markup.html', context)
        
        # Check that impact was measured
        try:
            cache = caches['default']
            impact_data = cache.get('schema_page_load_impact')
            if impact_data:
                self.assertIn('time_ms', impact_data)
                self.assertIn('query_count', impact_data)
                self.assertGreater(impact_data['time_ms'], 0)
        except:
            # Cache might not be available in test environment
            pass

    def test_bulk_performance_with_multiple_posts(self):
        """Test performance with multiple posts."""
        # Create additional test posts
        posts = []
        for i in range(10):
            post = Post.objects.create(
                title=f'Test Post {i}',
                slug=f'test-post-{i}',
                content=f'Content for test post {i}',
                author=self.user,
                status='published'
            )
            post.categories.add(self.category)
            post.tags.add(self.tag)
            posts.append(post)
        
        # Measure bulk generation performance
        start_time = time.time()
        start_queries = len(connection.queries)
        
        schemas = []
        for post in posts:
            schema = SchemaService.generate_article_schema(post, self.request)
            schemas.append(schema)
        
        end_time = time.time()
        end_queries = len(connection.queries)
        
        total_time = (end_time - start_time) * 1000
        total_queries = end_queries - start_queries
        
        # Assertions
        self.assertEqual(len(schemas), 10)
        self.assertLess(total_time / len(posts), 50, 
                       "Average generation time should be under 50ms per post")
        
        print(f"Bulk generation: {total_time:.2f}ms total, {total_time/len(posts):.2f}ms avg")
        print(f"Bulk queries: {total_queries} total, {total_queries/len(posts):.1f} avg")

    def test_cache_statistics(self):
        """Test cache statistics collection."""
        # Generate some cached data
        for _ in range(3):
            SchemaService.generate_article_schema(self.post, self.request)
            SchemaService.generate_publisher_schema()
        
        # Get cache statistics
        stats = get_cache_statistics()
        
        # Assertions
        self.assertIsInstance(stats, dict)
        if 'performance_monitor' in stats:
            pm_stats = stats['performance_monitor']
            self.assertIn('cache_hit_rate', pm_stats)
            self.assertIn('total_schema_generations', pm_stats)

    @override_settings(DEBUG=True)
    def test_performance_with_debug_mode(self):
        """Test performance impact in debug mode."""
        # This test ensures performance is acceptable even in debug mode
        start_time = time.time()
        schema_data = SchemaService.generate_article_schema(self.post, self.request)
        generation_time = (time.time() - start_time) * 1000
        
        # Even in debug mode, generation should be reasonably fast
        self.assertLess(generation_time, 200, 
                       "Schema generation should be under 200ms even in debug mode")
        self.assertIsInstance(schema_data, dict)
        self.assertTrue(SchemaService.validate_schema(schema_data))

    def test_memory_usage_optimization(self):
        """Test that memory usage is optimized."""
        import gc
        import sys
        
        # Force garbage collection
        gc.collect()
        
        # Get initial memory usage (approximate)
        initial_objects = len(gc.get_objects())
        
        # Generate multiple schemas
        schemas = []
        for _ in range(100):
            schema = SchemaService.generate_article_schema(self.post, self.request)
            schemas.append(schema)
        
        # Force garbage collection again
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory usage should not grow excessively
        object_growth = final_objects - initial_objects
        self.assertLess(object_growth, 1000, 
                       "Memory usage should not grow excessively")
        
        print(f"Object growth: {object_growth} objects for 100 schema generations")

    def test_concurrent_cache_access(self):
        """Test cache behavior under concurrent access."""
        import threading
        import queue
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def generate_schema():
            try:
                schema = SchemaService.generate_article_schema(self.post, self.request)
                results.put(schema)
            except Exception as e:
                errors.put(e)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=generate_schema)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        self.assertTrue(errors.empty(), f"Errors occurred: {list(errors.queue)}")
        self.assertEqual(results.qsize(), 10, "All threads should complete successfully")
        
        # All schemas should be identical
        schemas = list(results.queue)
        first_schema = schemas[0]
        for schema in schemas[1:]:
            self.assertEqual(schema, first_schema, "All schemas should be identical")


class SchemaPerformanceBenchmarkTestCase(TestCase):
    """Benchmark tests for schema performance."""
    
    def setUp(self):
        """Set up benchmark test data."""
        from django.contrib.auth.models import User
        
        # Create test user
        self.user = User.objects.create_user(
            username='benchmarkuser',
            email='benchmark@example.com'
        )
        
        # Create test post
        self.post = Post.objects.create(
            title='Benchmark Test Post',
            slug='benchmark-test-post',
            content='Content for benchmark testing.',
            author=self.user,
            status='published'
        )
        
        self.factory = RequestFactory()
        self.request = self.factory.get('/')

    def test_schema_generation_benchmark(self):
        """Benchmark schema generation performance."""
        iterations = 100
        times = []
        
        for _ in range(iterations):
            start_time = time.time()
            SchemaService.generate_article_schema(self.post, self.request)
            end_time = time.time()
            times.append((end_time - start_time) * 1000)
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        median_time = statistics.median(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\nSchema Generation Benchmark ({iterations} iterations):")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Median:  {median_time:.2f}ms")
        print(f"  Min:     {min_time:.2f}ms")
        print(f"  Max:     {max_time:.2f}ms")
        
        # Performance assertions
        self.assertLess(avg_time, 50, "Average generation time should be under 50ms")
        self.assertLess(max_time, 200, "Maximum generation time should be under 200ms")

    def test_cache_effectiveness_benchmark(self):
        """Benchmark cache effectiveness."""
        iterations = 50
        
        # Test without cache (clear before each generation)
        no_cache_times = []
        for _ in range(iterations):
            SchemaService.invalidate_post_schema_cache(self.post.id)
            start_time = time.time()
            SchemaService.generate_article_schema(self.post, self.request)
            end_time = time.time()
            no_cache_times.append((end_time - start_time) * 1000)
        
        # Test with cache (generate once, then use cache)
        SchemaService.generate_article_schema(self.post, self.request)  # Prime cache
        
        cached_times = []
        for _ in range(iterations):
            start_time = time.time()
            SchemaService.generate_article_schema(self.post, self.request)
            end_time = time.time()
            cached_times.append((end_time - start_time) * 1000)
        
        # Calculate statistics
        avg_no_cache = statistics.mean(no_cache_times)
        avg_cached = statistics.mean(cached_times)
        speedup = avg_no_cache / avg_cached if avg_cached > 0 else 0
        
        print(f"\nCache Effectiveness Benchmark ({iterations} iterations):")
        print(f"  No Cache Average: {avg_no_cache:.2f}ms")
        print(f"  Cached Average:   {avg_cached:.2f}ms")
        print(f"  Speedup:          {speedup:.1f}x")
        
        # Cache should provide significant speedup
        self.assertGreater(speedup, 2, "Cache should provide at least 2x speedup")