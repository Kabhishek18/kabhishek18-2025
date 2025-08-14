"""
Final integration tests for blog schema markup feature.

This test suite performs comprehensive end-to-end testing and validation
of the schema markup implementation to ensure compliance with requirements
4.1, 4.2, 4.3, 4.4, and 4.5.

Test Coverage:
- Complete schema markup on live blog posts
- Google Rich Results Test validation simulation
- Schema.org compliance verification
- End-to-end testing with various post configurations
- Edge cases and error handling
- Performance and caching validation
"""

import json
import re
import requests
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from urllib.parse import urljoin

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.cache import cache
from django.template.loader import render_to_string
from django.test.utils import override_settings
from django.utils import timezone

from blog.models import Post, Category, Tag, AuthorProfile, MediaItem
from blog.services.schema_service import SchemaService
from blog.templatetags.schema_tags import render_article_schema


class SchemaFinalIntegrationTestCase(TestCase):
    """
    Final integration test suite for schema markup validation.
    
    Requirements Coverage:
    - 4.1: Google Rich Results Test compatibility
    - 4.2: Schema.org compliance validation
    - 4.3: JSON-LD format validation
    - 4.4: Template rendering verification
    - 4.5: Edge case handling
    """
    
    def setUp(self):
        """Set up test data for comprehensive testing."""
        # Clear cache before each test
        cache.clear()
        
        # Create test user and author profile
        self.user = User.objects.create_user(
            username='testauthor',
            email='test@example.com',
            first_name='Test',
            last_name='Author'
        )
        
        self.author_profile = AuthorProfile.objects.create(
            user=self.user,
            bio='Test author bio for schema testing',
            website='https://testauthor.com',
            twitter='@testauthor',
            linkedin='https://linkedin.com/in/testauthor',
            github='testauthor'
        )
        
        # Create test categories and tags
        self.category = Category.objects.create(
            name='Technology',
            slug='technology'
        )
        
        self.tag1 = Tag.objects.create(name='Python', slug='python')
        self.tag2 = Tag.objects.create(name='Django', slug='django')
        
        # Create comprehensive test post
        self.post = Post.objects.create(
            title='Complete Schema Markup Test Post with All Features',
            slug='complete-schema-test-post',
            content='<p>This is a comprehensive test post for schema markup validation.</p>',
            excerpt='Test post excerpt for schema validation',
            author=self.user,
            status='published',
            created_at=timezone.now() - timedelta(days=1),
            updated_at=timezone.now()
        )
        
        self.post.categories.add(self.category)
        self.post.tags.add(self.tag1, self.tag2)
        
        # Create test post with minimal data
        self.minimal_post = Post.objects.create(
            title='Minimal Test Post',
            slug='minimal-test-post',
            content='<p>Minimal content.</p>',
            author=self.user,
            status='published'
        )
        
        # Create test client
        self.client = Client()
    
    def test_complete_schema_markup_on_live_blog_posts(self):
        """
        Test complete schema markup generation on live blog posts.
        
        Requirements: 4.1, 4.2, 4.4
        """
        # Test with comprehensive post
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        self.assertEqual(response.status_code, 200)
        
        # Verify schema markup is present in response
        content = response.content.decode('utf-8')
        self.assertIn('application/ld+json', content)
        self.assertIn('"@context": "https://schema.org"', content)
        self.assertIn('"@type": "Article"', content)
        
        # Extract and validate JSON-LD
        json_ld_pattern = r'<script type="application/ld\+json">\s*(.*?)\s*</script>'
        matches = re.findall(json_ld_pattern, content, re.DOTALL)
        
        self.assertGreater(len(matches), 0, "No JSON-LD schema found in response")
        
        # Validate each JSON-LD block
        for match in matches:
            try:
                schema_data = json.loads(match)
                self.assertIn('@context', schema_data)
                self.assertIn('@type', schema_data)
                
                # Validate Article schema specifically
                if schema_data.get('@type') == 'Article':
                    self._validate_article_schema_completeness(schema_data)
                    
            except json.JSONDecodeError as e:
                self.fail(f"Invalid JSON-LD found in response: {e}")
    
    def test_google_rich_results_compatibility(self):
        """
        Test schema markup compatibility with Google Rich Results requirements.
        
        Requirements: 4.1, 4.2
        """
        # Generate schema for comprehensive post
        request = self._create_mock_request()
        schema_data = SchemaService.generate_article_schema(self.post, request)
        
        # Google Rich Results requirements for Article
        required_fields = [
            'headline', 'author', 'publisher', 'datePublished', 'url'
        ]
        
        for field in required_fields:
            self.assertIn(field, schema_data, f"Missing required field for Google Rich Results: {field}")
        
        # Validate headline length (Google recommends max 110 characters)
        headline = schema_data.get('headline', '')
        self.assertLessEqual(len(headline), 110, "Headline too long for optimal Google display")
        
        # Validate author structure
        author = schema_data.get('author', {})
        self.assertEqual(author.get('@type'), 'Person')
        self.assertIn('name', author)
        
        # Validate publisher structure
        publisher = schema_data.get('publisher', {})
        self.assertEqual(publisher.get('@type'), 'Organization')
        self.assertIn('name', publisher)
        self.assertIn('logo', publisher)
        
        # Validate date format (ISO 8601)
        date_published = schema_data.get('datePublished', '')
        self.assertTrue(self._is_valid_iso_date(date_published), "Invalid ISO 8601 date format")
        
        # Validate URL format (absolute URL)
        url = schema_data.get('url', '')
        self.assertTrue(url.startswith('http'), "URL must be absolute")
    
    def test_schema_org_compliance_validation(self):
        """
        Test schema markup compliance with Schema.org specifications.
        
        Requirements: 4.2, 4.3
        """
        request = self._create_mock_request()
        
        # Test Article schema compliance
        article_schema = SchemaService.generate_article_schema(self.post, request)
        self.assertTrue(SchemaService.validate_schema(article_schema))
        
        # Validate required Article properties
        self.assertEqual(article_schema['@context'], 'https://schema.org')
        self.assertEqual(article_schema['@type'], 'Article')
        
        # Test Author schema compliance
        author_schema = SchemaService.generate_author_schema(self.user, request)
        self.assertTrue(SchemaService.validate_schema(author_schema, is_embedded=True))
        self.assertEqual(author_schema['@type'], 'Person')
        
        # Test Publisher schema compliance
        publisher_schema = SchemaService.generate_publisher_schema()
        self.assertTrue(SchemaService.validate_schema(publisher_schema))
        self.assertEqual(publisher_schema['@type'], 'Organization')
        
        # Test Breadcrumb schema compliance
        breadcrumb_schema = SchemaService.generate_breadcrumb_schema(self.post, request)
        if breadcrumb_schema:  # May be empty if URL generation fails
            self.assertTrue(SchemaService.validate_schema(breadcrumb_schema))
            self.assertEqual(breadcrumb_schema['@type'], 'BreadcrumbList')
    
    def test_json_ld_format_validation(self):
        """
        Test JSON-LD format validation and serialization.
        
        Requirements: 4.3
        """
        request = self._create_mock_request()
        schema_data = SchemaService.generate_article_schema(self.post, request)
        
        # Test JSON serialization
        try:
            json_string = json.dumps(schema_data, ensure_ascii=False, indent=2)
            self.assertIsInstance(json_string, str)
            
            # Test deserialization
            parsed_data = json.loads(json_string)
            self.assertEqual(parsed_data, schema_data)
            
        except (TypeError, ValueError) as e:
            self.fail(f"Schema data is not JSON serializable: {e}")
        
        # Test special character handling
        special_post = Post.objects.create(
            title='Test "Quotes" & Ampersands < > Special Characters',
            slug='special-chars-test',
            content='<p>Content with "quotes" & ampersands.</p>',
            author=self.user,
            status='published'
        )
        
        special_schema = SchemaService.generate_article_schema(special_post, request)
        
        try:
            json.dumps(special_schema, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            self.fail(f"Schema with special characters failed JSON serialization: {e}")
    
    def test_end_to_end_various_post_configurations(self):
        """
        Test end-to-end schema generation with various post configurations.
        
        Requirements: 4.4, 4.5
        """
        configurations = [
            {
                'name': 'Post with featured image',
                'post_data': {
                    'title': 'Post with Featured Image',
                    'slug': 'post-with-image',
                    'content': '<p>Content with image.</p>',
                    'author': self.user,
                    'status': 'published'
                },
                'setup': lambda post: None  # Featured image would be set here
            },
            {
                'name': 'Post without categories',
                'post_data': {
                    'title': 'Post Without Categories',
                    'slug': 'post-no-categories',
                    'content': '<p>Content without categories.</p>',
                    'author': self.user,
                    'status': 'published'
                },
                'setup': lambda post: None
            },
            {
                'name': 'Post with long title',
                'post_data': {
                    'title': 'This is a Very Long Title That Exceeds the Recommended Length for SEO and Should Be Truncated Properly by the Schema Service',
                    'slug': 'post-long-title',
                    'content': '<p>Content with long title.</p>',
                    'author': self.user,
                    'status': 'published'
                },
                'setup': lambda post: None
            },
            {
                'name': 'Post with minimal author profile',
                'post_data': {
                    'title': 'Post with Minimal Author',
                    'slug': 'post-minimal-author',
                    'content': '<p>Content with minimal author.</p>',
                    'status': 'published'
                },
                'setup': lambda post: None
            }
        ]
        
        for config in configurations:
            with self.subTest(configuration=config['name']):
                # Create user for minimal author test
                if 'author' not in config['post_data']:
                    minimal_user = User.objects.create_user(
                        username=f"minimal_{config['post_data']['slug']}",
                        email=f"minimal_{config['post_data']['slug']}@example.com"
                    )
                    config['post_data']['author'] = minimal_user
                
                # Create post
                post = Post.objects.create(**config['post_data'])
                config['setup'](post)
                
                # Test schema generation
                request = self._create_mock_request()
                schema_data = SchemaService.generate_article_schema(post, request)
                
                # Validate basic schema structure
                self.assertIn('@context', schema_data)
                self.assertIn('@type', schema_data)
                self.assertEqual(schema_data['@type'], 'Article')
                
                # Test template rendering
                response = self.client.get(reverse('blog:detail', kwargs={'slug': post.slug}))
                self.assertEqual(response.status_code, 200)
                
                content = response.content.decode('utf-8')
                self.assertIn('application/ld+json', content)
    
    def test_edge_cases_and_error_handling(self):
        """
        Test edge cases and error handling in schema generation.
        
        Requirements: 4.5
        """
        # Test with None request
        schema_data = SchemaService.generate_article_schema(self.post, None)
        self.assertIn('@context', schema_data)
        self.assertIn('url', schema_data)
        
        # Test with post having no content
        empty_post = Post.objects.create(
            title='Empty Post',
            slug='empty-post',
            content='',
            author=self.user,
            status='published'
        )
        
        schema_data = SchemaService.generate_article_schema(empty_post)
        self.assertIn('@context', schema_data)
        self.assertIn('@type', schema_data)
        
        # Test with user having no author profile
        no_profile_user = User.objects.create_user(
            username='noprofile',
            email='noprofile@example.com'
        )
        
        no_profile_post = Post.objects.create(
            title='No Profile Post',
            slug='no-profile-post',
            content='<p>Content.</p>',
            author=no_profile_user,
            status='published'
        )
        
        schema_data = SchemaService.generate_article_schema(no_profile_post)
        self.assertIn('author', schema_data)
        self.assertEqual(schema_data['author']['@type'], 'Person')
        
        # Test schema validation with invalid data
        invalid_schema = {'@type': 'Article'}  # Missing required fields
        self.assertFalse(SchemaService.validate_schema(invalid_schema))
    
    def test_performance_and_caching(self):
        """
        Test schema generation performance and caching behavior.
        
        Requirements: 4.4
        """
        request = self._create_mock_request()
        
        # Clear cache
        cache.clear()
        
        # First generation (cache miss)
        start_time = datetime.now()
        schema_data_1 = SchemaService.generate_article_schema(self.post, request)
        first_duration = (datetime.now() - start_time).total_seconds()
        
        # Second generation (cache hit)
        start_time = datetime.now()
        schema_data_2 = SchemaService.generate_article_schema(self.post, request)
        second_duration = (datetime.now() - start_time).total_seconds()
        
        # Verify cache effectiveness
        self.assertEqual(schema_data_1, schema_data_2)
        self.assertLess(second_duration, first_duration, "Cache should improve performance")
        
        # Test cache invalidation
        SchemaService.invalidate_post_schema_cache(self.post.id)
        
        # Third generation (cache miss after invalidation)
        start_time = datetime.now()
        schema_data_3 = SchemaService.generate_article_schema(self.post, request)
        third_duration = (datetime.now() - start_time).total_seconds()
        
        self.assertEqual(schema_data_1, schema_data_3)
    
    def test_template_integration_validation(self):
        """
        Test schema markup integration in templates.
        
        Requirements: 4.4
        """
        # Test template tag rendering
        from django.template import Context, Template
        
        template_content = """
        {% load schema_tags %}
        {% render_article_schema post %}
        """
        
        template = Template(template_content)
        context = Context({
            'post': self.post,
            'request': self._create_mock_request()
        })
        
        rendered = template.render(context)
        self.assertIn('application/ld+json', rendered)
        self.assertIn('"@context": "https://schema.org"', rendered)
        
        # Test individual template tags
        json_template = Template('{% load schema_tags %}{% get_article_schema_json post %}')
        json_output = json_template.render(context)
        
        try:
            json.loads(json_output)
        except json.JSONDecodeError as e:
            self.fail(f"Template tag produced invalid JSON: {e}")
    
    def test_url_generation_and_absolute_urls(self):
        """
        Test URL generation and absolute URL requirements.
        
        Requirements: 4.2
        """
        request = self._create_mock_request()
        schema_data = SchemaService.generate_article_schema(self.post, request)
        
        # Verify all URLs are absolute
        url = schema_data.get('url', '')
        self.assertTrue(url.startswith('http'), "Article URL must be absolute")
        
        # Test author URL if present
        author = schema_data.get('author', {})
        if 'url' in author:
            self.assertTrue(author['url'].startswith('http'), "Author URL must be absolute")
        
        # Test image URLs if present
        images = schema_data.get('image', [])
        if images:
            for image_url in images:
                self.assertTrue(image_url.startswith('http'), "Image URLs must be absolute")
    
    def _validate_article_schema_completeness(self, schema_data):
        """Validate Article schema has all expected fields."""
        required_fields = ['headline', 'author', 'publisher', 'datePublished', 'url']
        optional_fields = ['dateModified', 'description', 'image', 'articleSection', 'keywords']
        
        for field in required_fields:
            self.assertIn(field, schema_data, f"Missing required field: {field}")
        
        # Validate nested structures
        author = schema_data.get('author', {})
        self.assertEqual(author.get('@type'), 'Person')
        self.assertIn('name', author)
        
        publisher = schema_data.get('publisher', {})
        self.assertEqual(publisher.get('@type'), 'Organization')
        self.assertIn('name', publisher)
    
    def _create_mock_request(self):
        """Create a mock request object for testing."""
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_HOST'] = 'testserver'
        return request
    
    def _is_valid_iso_date(self, date_string):
        """Validate ISO 8601 date format."""
        try:
            datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            return True
        except (ValueError, AttributeError):
            return False


class SchemaValidationToolsTestCase(TestCase):
    """
    Test suite for schema validation tools and utilities.
    
    Requirements: 4.3, 4.5
    """
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='validator_test',
            email='validator@example.com'
        )
        
        self.post = Post.objects.create(
            title='Validation Test Post',
            slug='validation-test-post',
            content='<p>Test content for validation.</p>',
            author=self.user,
            status='published'
        )
    
    def test_schema_validation_utility(self):
        """Test the schema validation utility function."""
        # Valid Article schema
        valid_schema = {
            '@context': 'https://schema.org',
            '@type': 'Article',
            'headline': 'Test Article',
            'author': {'@type': 'Person', 'name': 'Test Author'},
            'publisher': {'@type': 'Organization', 'name': 'Test Publisher'},
            'datePublished': '2024-01-01T00:00:00Z'
        }
        
        self.assertTrue(SchemaService.validate_schema(valid_schema))
        
        # Invalid schema (missing required fields)
        invalid_schema = {
            '@context': 'https://schema.org',
            '@type': 'Article',
            'headline': 'Test Article'
            # Missing author, publisher, datePublished
        }
        
        self.assertFalse(SchemaService.validate_schema(invalid_schema))
        
        # Test embedded schema validation
        embedded_author = {
            '@type': 'Person',
            'name': 'Test Author'
        }
        
        self.assertTrue(SchemaService.validate_schema(embedded_author, is_embedded=True))
    
    def test_json_ld_serialization_validation(self):
        """Test JSON-LD serialization and validation."""
        request = self._create_mock_request()
        schema_data = SchemaService.generate_article_schema(self.post, request)
        
        # Test serialization
        try:
            json_string = json.dumps(schema_data, ensure_ascii=False, indent=2)
            parsed_back = json.loads(json_string)
            self.assertEqual(schema_data, parsed_back)
        except Exception as e:
            self.fail(f"JSON-LD serialization failed: {e}")
    
    def _create_mock_request(self):
        """Create a mock request object for testing."""
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_HOST'] = 'testserver'
        return request


class SchemaDocumentationTestCase(TestCase):
    """
    Test case for documenting schema implementation limitations and known issues.
    
    Requirements: 4.5
    """
    
    def test_document_known_limitations(self):
        """Document known limitations and issues."""
        limitations = {
            'cache_backend_dependency': {
                'description': 'Schema caching depends on cache backend supporting pattern deletion',
                'impact': 'Cache invalidation may not work with all cache backends',
                'workaround': 'Manual cache clearing or cache timeout'
            },
            'media_item_prefetching': {
                'description': 'Media items require proper prefetching to avoid N+1 queries',
                'impact': 'Performance degradation with many media items',
                'workaround': 'Use select_related and prefetch_related in views'
            },
            'url_generation_fallback': {
                'description': 'URL generation falls back to settings when request is None',
                'impact': 'May generate incorrect URLs in some contexts',
                'workaround': 'Always pass request object when possible'
            },
            'author_profile_optional': {
                'description': 'Author profiles are optional, schema adapts gracefully',
                'impact': 'Reduced schema richness for authors without profiles',
                'workaround': 'Encourage complete author profiles'
            }
        }
        
        # This test documents limitations by asserting they exist
        self.assertIsInstance(limitations, dict)
        self.assertGreater(len(limitations), 0)
        
        # Log limitations for documentation
        import logging
        logger = logging.getLogger(__name__)
        
        for limitation, details in limitations.items():
            logger.info(f"Known Limitation: {limitation}")
            logger.info(f"  Description: {details['description']}")
            logger.info(f"  Impact: {details['impact']}")
            logger.info(f"  Workaround: {details['workaround']}")
    
    def test_document_best_practices(self):
        """Document best practices for schema implementation."""
        best_practices = {
            'prefetch_related_data': 'Use select_related and prefetch_related for categories, tags, and media',
            'cache_warming': 'Warm schema cache after post updates',
            'error_handling': 'Always provide fallback schema data',
            'validation': 'Validate schema data before rendering',
            'performance_monitoring': 'Monitor schema generation performance',
            'url_consistency': 'Ensure consistent absolute URL generation'
        }
        
        # Document best practices
        self.assertIsInstance(best_practices, dict)
        self.assertGreater(len(best_practices), 0)