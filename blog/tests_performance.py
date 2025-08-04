"""
Performance tests for search and content discovery features.
Tests query optimization, caching, and response times.
"""
import time
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.test.utils import override_settings
from unittest.mock import patch
from .models import Post, Category, Tag, Comment, SocialShare, NewsletterSubscriber
from .services import ContentDiscoveryService, SocialShareService
from .services.content_discovery_service import ContentDiscoveryService as CDService
from .services.social_share_service import SocialShareService as SSService


class SearchPerformanceTest(TestCase):
    """Test performance of search functionality"""
    
    def setUp(self):
        """Set up test data"""
        cache.clear()
        
        # Create test users
        self.users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='testpass123'
            )
            self.users.append(user)
        
        # Create categories
        self.categories = []
        category_names = ['Technology', 'Science', 'Programming', 'AI', 'Web Development']
        for name in category_names:
            category = Category.objects.create(name=name)
            self.categories.append(category)
        
        # Create tags
        self.tags = []
        tag_names = ['Python', 'Django', 'JavaScript', 'React', 'Machine Learning', 
                    'Data Science', 'Web Design', 'API', 'Database', 'Testing']
        for name in tag_names:
            tag = Tag.objects.create(name=name)
            self.tags.append(tag)
        
        # Create posts with varying content
        self.posts = []
        for i in range(100):
            post = Post.objects.create(
                title=f'Test Post {i}: {tag_names[i % len(tag_names)]} Tutorial',
                slug=f'test-post-{i}',
                author=self.users[i % len(self.users)],
                content=f'This is test content for post {i}. It contains information about '
                       f'{tag_names[i % len(tag_names)]} and {category_names[i % len(category_names)]}. '
                       f'This post has detailed explanations and examples. ' * 10,
                excerpt=f'Excerpt for post {i} about {tag_names[i % len(tag_names)]}',
                status='published',
                view_count=i * 10,
                is_featured=(i % 10 == 0)  # Every 10th post is featured
            )
            
            # Add categories and tags
            post.categories.add(self.categories[i % len(self.categories)])
            post.tags.add(self.tags[i % len(self.tags)])
            if i % 3 == 0:  # Add second tag to some posts
                post.tags.add(self.tags[(i + 1) % len(self.tags)])
            
            self.posts.append(post)
        
        self.client = Client()
    
    def test_search_query_performance(self):
        """Test search query performance with large dataset"""
        search_terms = ['Python', 'Django', 'JavaScript', 'Tutorial', 'Test']
        
        for term in search_terms:
            start_time = time.time()
            
            # Perform search
            response = self.client.get(reverse('blog:search'), {'q': term})
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Should complete within reasonable time
            self.assertLess(execution_time, 2.0, f"Search for '{term}' took too long: {execution_time}s")
            self.assertEqual(response.status_code, 200)
    
    def test_search_database_queries(self):
        """Test that search uses optimized database queries"""
        with self.assertNumQueries(3):  # Should be optimized with select_related/prefetch_related
            response = self.client.get(reverse('blog:search'), {'q': 'Python'})
            self.assertEqual(response.status_code, 200)
    
    def test_category_filtering_performance(self):
        """Test performance of category filtering"""
        for category in self.categories[:3]:  # Test first 3 categories
            start_time = time.time()
            
            response = self.client.get(reverse('blog:category_posts', kwargs={
                'category_slug': category.slug
            }))
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.assertLess(execution_time, 1.0, f"Category filtering took too long: {execution_time}s")
            self.assertEqual(response.status_code, 200)
    
    def test_tag_filtering_performance(self):
        """Test performance of tag filtering"""
        for tag in self.tags[:3]:  # Test first 3 tags
            start_time = time.time()
            
            response = self.client.get(reverse('blog:tag_posts', kwargs={
                'tag_slug': tag.slug
            }))
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.assertLess(execution_time, 1.0, f"Tag filtering took too long: {execution_time}s")
            self.assertEqual(response.status_code, 200)
    
    def test_pagination_performance(self):
        """Test pagination performance with large datasets"""
        pages_to_test = [1, 2, 5, 10]
        
        for page in pages_to_test:
            start_time = time.time()
            
            response = self.client.get(reverse('blog:list'), {'page': page})
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.assertLess(execution_time, 1.0, f"Page {page} took too long: {execution_time}s")
            if page <= 10:  # Should have content for first 10 pages
                self.assertEqual(response.status_code, 200)


class ContentDiscoveryPerformanceTest(TestCase):
    """Test performance of content discovery features"""
    
    def setUp(self):
        """Set up test data"""
        cache.clear()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create categories and tags
        self.categories = [
            Category.objects.create(name=f'Category {i}') for i in range(10)
        ]
        self.tags = [
            Tag.objects.create(name=f'Tag {i}') for i in range(20)
        ]
        
        # Create posts
        self.posts = []
        for i in range(200):
            post = Post.objects.create(
                title=f'Performance Test Post {i}',
                slug=f'performance-test-post-{i}',
                author=self.user,
                content=f'Content for performance test post {i}. ' * 50,
                excerpt=f'Excerpt for post {i}',
                status='published',
                view_count=i * 5,
                is_featured=(i % 20 == 0)
            )
            
            # Add relationships
            post.categories.add(self.categories[i % len(self.categories)])
            post.tags.add(self.tags[i % len(self.tags)])
            if i % 2 == 0:
                post.tags.add(self.tags[(i + 1) % len(self.tags)])
            
            self.posts.append(post)
        
        # Create comments and social shares for engagement
        for i in range(0, 50, 5):  # Every 5th post gets engagement
            post = self.posts[i]
            
            # Add comments
            for j in range(3):
                Comment.objects.create(
                    post=post,
                    author_name=f'Commenter {j}',
                    author_email=f'commenter{j}@example.com',
                    content=f'Comment {j} on post {i}',
                    is_approved=True,
                    ip_address='127.0.0.1'
                )
            
            # Add social shares
            SocialShare.objects.create(
                post=post,
                platform='facebook',
                share_count=i // 5 + 1
            )
            SocialShare.objects.create(
                post=post,
                platform='twitter',
                share_count=i // 10 + 1
            )
    
    def test_featured_posts_performance(self):
        """Test performance of getting featured posts"""
        start_time = time.time()
        
        featured_posts = ContentDiscoveryService.get_featured_posts(limit=10)
        list(featured_posts)  # Force evaluation
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 0.5, f"Featured posts took too long: {execution_time}s")
    
    def test_related_posts_performance(self):
        """Test performance of related posts algorithm"""
        test_post = self.posts[50]  # Use middle post
        
        start_time = time.time()
        
        related_posts = ContentDiscoveryService.get_related_posts(test_post, limit=5)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 1.0, f"Related posts took too long: {execution_time}s")
        self.assertGreater(len(related_posts), 0)
    
    def test_popular_posts_performance(self):
        """Test performance of popular posts calculation"""
        timeframes = ['week', 'month', 'year', 'all']
        
        for timeframe in timeframes:
            start_time = time.time()
            
            popular_posts = ContentDiscoveryService.get_popular_posts(
                timeframe=timeframe, 
                limit=10
            )
            list(popular_posts)  # Force evaluation
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.assertLess(execution_time, 1.0, 
                          f"Popular posts ({timeframe}) took too long: {execution_time}s")
    
    def test_trending_tags_performance(self):
        """Test performance of trending tags calculation"""
        start_time = time.time()
        
        trending_tags = ContentDiscoveryService.get_trending_tags(limit=10)
        list(trending_tags)  # Force evaluation
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 0.5, f"Trending tags took too long: {execution_time}s")
    
    def test_content_discovery_database_queries(self):
        """Test database query optimization for content discovery"""
        test_post = self.posts[50]
        
        # Test featured posts queries
        with self.assertNumQueries(1):
            list(CDService.get_featured_posts(limit=5))
        
        # Test popular posts queries
        with self.assertNumQueries(1):
            list(CDService.get_popular_posts(timeframe='week', limit=5))
        
        # Test trending tags queries
        with self.assertNumQueries(1):
            list(CDService.get_trending_tags(limit=5))


class CachingPerformanceTest(TestCase):
    """Test caching performance and effectiveness"""
    
    def setUp(self):
        """Set up test data"""
        cache.clear()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test posts
        self.posts = []
        for i in range(50):
            post = Post.objects.create(
                title=f'Cache Test Post {i}',
                slug=f'cache-test-post-{i}',
                author=self.user,
                content=f'Content for cache test post {i}',
                status='published',
                is_featured=(i % 10 == 0),
                view_count=i * 10
            )
            self.posts.append(post)
    
    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'test-cache',
        }
    })
    def test_featured_posts_caching(self):
        """Test that featured posts are cached effectively"""
        cache.clear()
        
        # First call should hit database
        start_time = time.time()
        featured_posts1 = list(ContentDiscoveryService.get_featured_posts(limit=5))
        first_call_time = time.time() - start_time
        
        # Second call should use cache
        start_time = time.time()
        featured_posts2 = list(ContentDiscoveryService.get_featured_posts(limit=5))
        second_call_time = time.time() - start_time
        
        # Results should be the same
        self.assertEqual(len(featured_posts1), len(featured_posts2))
        
        # Second call should be faster (cached)
        # Note: This might be flaky in fast test environments
        if first_call_time > 0.001:  # Only test if first call took measurable time
            self.assertLess(second_call_time, first_call_time)
    
    def test_cache_invalidation(self):
        """Test that caches are properly invalidated"""
        cache.clear()
        
        # Populate cache
        featured_posts1 = list(ContentDiscoveryService.get_featured_posts(limit=5))
        
        # Create new featured post
        new_post = Post.objects.create(
            title='New Featured Post',
            slug='new-featured-post',
            author=self.user,
            content='New featured content',
            status='published',
            is_featured=True
        )
        
        # Clear caches (simulating cache invalidation)
        ContentDiscoveryService.clear_content_caches()
        
        # Get featured posts again
        featured_posts2 = list(ContentDiscoveryService.get_featured_posts(limit=5))
        
        # Should include new post
        post_titles = [post.title for post in featured_posts2]
        self.assertIn('New Featured Post', post_titles)
    
    def test_view_count_update_performance(self):
        """Test performance of view count updates"""
        test_post = self.posts[0]
        original_count = test_post.view_count
        
        start_time = time.time()
        
        # Update view count multiple times
        for _ in range(10):
            ContentDiscoveryService.update_view_count(test_post)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete quickly
        self.assertLess(execution_time, 0.5, f"View count updates took too long: {execution_time}s")
        
        # Verify count was updated
        test_post.refresh_from_db()
        self.assertEqual(test_post.view_count, original_count + 10)


class SocialSharingPerformanceTest(TestCase):
    """Test performance of social sharing functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create posts
        self.posts = []
        for i in range(100):
            post = Post.objects.create(
                title=f'Social Test Post {i}',
                slug=f'social-test-post-{i}',
                author=self.user,
                content=f'Content for social test post {i}',
                status='published'
            )
            self.posts.append(post)
        
        # Create social shares
        platforms = ['facebook', 'twitter', 'linkedin', 'reddit']
        for i, post in enumerate(self.posts[:50]):  # First 50 posts get shares
            for j, platform in enumerate(platforms):
                if (i + j) % 2 == 0:  # Not all posts have all platforms
                    SocialShare.objects.create(
                        post=post,
                        platform=platform,
                        share_count=(i + j) * 2
                    )
        
        self.client = Client()
    
    def test_share_url_generation_performance(self):
        """Test performance of share URL generation"""
        test_post = self.posts[0]
        
        start_time = time.time()
        
        # Generate share URLs multiple times
        for _ in range(100):
            share_urls = SocialShareService.generate_share_urls(
                test_post, 
                self.client.request()
            )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 1.0, f"Share URL generation took too long: {execution_time}s")
    
    def test_share_tracking_performance(self):
        """Test performance of share tracking"""
        test_post = self.posts[0]
        
        start_time = time.time()
        
        # Track multiple shares
        for i in range(50):
            platform = ['facebook', 'twitter', 'linkedin'][i % 3]
            SocialShareService.track_share(test_post, platform)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 1.0, f"Share tracking took too long: {execution_time}s")
    
    def test_share_counts_retrieval_performance(self):
        """Test performance of retrieving share counts"""
        test_posts = self.posts[:20]  # Test first 20 posts
        
        start_time = time.time()
        
        for post in test_posts:
            share_counts = SocialShareService.get_share_counts(post)
            total_shares = SocialShareService.get_total_shares(post)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 1.0, f"Share counts retrieval took too long: {execution_time}s")
    
    def test_most_shared_posts_performance(self):
        """Test performance of getting most shared posts"""
        start_time = time.time()
        
        most_shared = SocialShareService.get_most_shared_posts(limit=10, timeframe='all')
        list(most_shared)  # Force evaluation
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 0.5, f"Most shared posts took too long: {execution_time}s")


class DatabaseOptimizationTest(TestCase):
    """Test database query optimization across all features"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create related data
        self.category = Category.objects.create(name='Test Category')
        self.tag = Tag.objects.create(name='Test Tag')
        
        self.post = Post.objects.create(
            title='Optimization Test Post',
            slug='optimization-test-post',
            author=self.user,
            content='Test content',
            status='published'
        )
        self.post.categories.add(self.category)
        self.post.tags.add(self.tag)
        
        # Create comments
        for i in range(5):
            Comment.objects.create(
                post=self.post,
                author_name=f'Commenter {i}',
                author_email=f'commenter{i}@example.com',
                content=f'Comment {i}',
                is_approved=True,
                ip_address='127.0.0.1'
            )
        
        # Create social shares
        SocialShare.objects.create(
            post=self.post,
            platform='facebook',
            share_count=10
        )
        
        self.client = Client()
    
    def test_blog_detail_query_optimization(self):
        """Test that blog detail view uses optimized queries"""
        with self.assertNumQueries(8):  # Should be optimized
            response = self.client.get(reverse('blog:detail', kwargs={
                'slug': self.post.slug
            }))
            self.assertEqual(response.status_code, 200)
    
    def test_blog_list_query_optimization(self):
        """Test that blog list view uses optimized queries"""
        # Create more posts for realistic test
        for i in range(10):
            post = Post.objects.create(
                title=f'List Test Post {i}',
                slug=f'list-test-post-{i}',
                author=self.user,
                content=f'Content {i}',
                status='published'
            )
            post.categories.add(self.category)
            post.tags.add(self.tag)
        
        with self.assertNumQueries(5):  # Should be optimized with select_related/prefetch_related
            response = self.client.get(reverse('blog:list'))
            self.assertEqual(response.status_code, 200)
    
    def test_search_query_optimization(self):
        """Test that search queries are optimized"""
        with self.assertNumQueries(3):  # Should be optimized
            response = self.client.get(reverse('blog:search'), {'q': 'test'})
            self.assertEqual(response.status_code, 200)
    
    def test_author_posts_query_optimization(self):
        """Test that author posts queries are optimized"""
        with self.assertNumQueries(4):  # Should be optimized
            response = self.client.get(reverse('blog:author_detail', kwargs={
                'username': self.user.username
            }))
            self.assertEqual(response.status_code, 200)


class MemoryUsageTest(TestCase):
    """Test memory usage of various operations"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_large_dataset_memory_usage(self):
        """Test memory usage with large datasets"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create large dataset
        posts = []
        for i in range(1000):
            post = Post.objects.create(
                title=f'Memory Test Post {i}',
                slug=f'memory-test-post-{i}',
                author=self.user,
                content=f'Content for memory test post {i}. ' * 100,
                status='published'
            )
            posts.append(post)
        
        # Perform operations
        featured_posts = list(ContentDiscoveryService.get_featured_posts(limit=10))
        popular_posts = list(ContentDiscoveryService.get_popular_posts(limit=10))
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        self.assertLess(memory_increase, 100 * 1024 * 1024, 
                       f"Memory usage increased by {memory_increase / 1024 / 1024:.2f}MB")
    
    def test_query_result_memory_efficiency(self):
        """Test that query results don't consume excessive memory"""
        # Create test data
        for i in range(100):
            Post.objects.create(
                title=f'Efficiency Test Post {i}',
                slug=f'efficiency-test-post-{i}',
                author=self.user,
                content=f'Content {i}',
                status='published'
            )
        
        # Test that iterating over large querysets is memory efficient
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Use iterator to avoid loading all objects into memory
        post_count = 0
        for post in Post.objects.filter(status='published').iterator():
            post_count += 1
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        self.assertEqual(post_count, 100)
        # Memory increase should be minimal when using iterator
        self.assertLess(memory_increase, 10 * 1024 * 1024,  # Less than 10MB
                       f"Iterator used {memory_increase / 1024 / 1024:.2f}MB")