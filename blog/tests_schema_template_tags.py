"""
Unit tests for schema template tags.

Tests all template tags for generating Schema.org structured data markup
including inclusion tags, simple tags, and filters for date formatting
and content processing.
"""

import json
from datetime import datetime, timezone, date
from unittest.mock import Mock, patch

from django.test import TestCase, RequestFactory
from django.template import Context, Template
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from blog.models import Post, Category, Tag, AuthorProfile
from blog.templatetags.schema_tags import (
    render_article_schema,
    get_article_schema_json,
    get_author_schema_json,
    get_publisher_schema_json,
    get_breadcrumb_schema_json,
    get_article_schema_data,
    get_author_schema_data,
    to_schema_date,
    to_schema_duration,
    schema_escape,
    truncate_headline,
    validate_schema,
    schema_debug_info
)


class SchemaTemplateTagsTestCase(TestCase):
    """Test cases for schema template tags."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testauthor',
            email='test@example.com',
            first_name='Test',
            last_name='Author'
        )
        
        # Create author profile
        self.author_profile = AuthorProfile.objects.create(
            user=self.user,
            bio='Test author bio for testing template tags.',
            website='https://testauthor.com',
            twitter='testauthor',
            linkedin='https://linkedin.com/in/testauthor'
        )
        
        # Create test post
        self.post = Post.objects.create(
            title='Test Blog Post for Template Tags',
            slug='test-blog-post-template-tags',
            author=self.user,
            content='<p>This is test content for template tag testing.</p>',
            excerpt='Test excerpt for template tags',
            status='published'
        )
        
        # Create request object
        self.request = self.factory.get('/blog/test-post/')
        self.request.META['HTTP_HOST'] = 'testserver'
        
        # Create template context
        self.context = Context({'request': self.request, 'post': self.post})

    def test_render_article_schema_inclusion_tag(self):
        """Test the render_article_schema inclusion tag."""
        result = render_article_schema(self.context, self.post)
        
        # Verify context variables
        self.assertIn('schema_json', result)
        self.assertIn('schema_data', result)
        self.assertIn('is_valid', result)
        self.assertIn('post', result)
        
        # Verify schema data
        self.assertIsInstance(result['schema_data'], dict)
        self.assertEqual(result['schema_data']['@type'], 'Article')
        self.assertEqual(result['post'], self.post)
        
        # Verify JSON is valid
        self.assertIsInstance(result['schema_json'], str)
        try:
            parsed = json.loads(result['schema_json'])
            self.assertIsInstance(parsed, dict)
        except json.JSONDecodeError:
            self.fail("Generated schema_json is not valid JSON")

    def test_render_article_schema_with_error(self):
        """Test render_article_schema with error conditions."""
        # Create a mock post that will cause errors
        mock_post = Mock()
        mock_post.id = 999
        mock_post.get_absolute_url.side_effect = Exception("Test error")
        
        result = render_article_schema(self.context, mock_post)
        
        # Should handle errors gracefully
        self.assertEqual(result['schema_json'], '{}')
        self.assertEqual(result['schema_data'], {})
        self.assertFalse(result['is_valid'])

    def test_get_article_schema_json_simple_tag(self):
        """Test the get_article_schema_json simple tag."""
        result = get_article_schema_json(self.context, self.post)
        
        # Should return SafeString JSON
        self.assertIsInstance(result, str)
        
        # Should be valid JSON
        try:
            parsed = json.loads(result)
            self.assertEqual(parsed['@type'], 'Article')
            self.assertEqual(parsed['headline'], self.post.title)
        except json.JSONDecodeError:
            self.fail("get_article_schema_json returned invalid JSON")

    def test_get_author_schema_json_simple_tag(self):
        """Test the get_author_schema_json simple tag."""
        result = get_author_schema_json(self.context, self.user)
        
        # Should return SafeString JSON
        self.assertIsInstance(result, str)
        
        # Should be valid JSON
        try:
            parsed = json.loads(result)
            self.assertEqual(parsed['@type'], 'Person')
            self.assertEqual(parsed['name'], 'Test Author')
        except json.JSONDecodeError:
            self.fail("get_author_schema_json returned invalid JSON")

    def test_get_publisher_schema_json_simple_tag(self):
        """Test the get_publisher_schema_json simple tag."""
        result = get_publisher_schema_json()
        
        # Should return SafeString JSON
        self.assertIsInstance(result, str)
        
        # Should be valid JSON
        try:
            parsed = json.loads(result)
            self.assertEqual(parsed['@type'], 'Organization')
            self.assertIn('name', parsed)
        except json.JSONDecodeError:
            self.fail("get_publisher_schema_json returned invalid JSON")

    def test_get_breadcrumb_schema_json_simple_tag(self):
        """Test the get_breadcrumb_schema_json simple tag."""
        result = get_breadcrumb_schema_json(self.context, self.post)
        
        # Should return SafeString JSON
        self.assertIsInstance(result, str)
        
        # Should be valid JSON
        try:
            parsed = json.loads(result)
            self.assertEqual(parsed['@type'], 'BreadcrumbList')
            self.assertIn('itemListElement', parsed)
        except json.JSONDecodeError:
            self.fail("get_breadcrumb_schema_json returned invalid JSON")

    def test_get_article_schema_data_simple_tag(self):
        """Test the get_article_schema_data simple tag."""
        result = get_article_schema_data(self.post, self.request)
        
        # Should return dictionary
        self.assertIsInstance(result, dict)
        self.assertEqual(result['@type'], 'Article')
        self.assertEqual(result['headline'], self.post.title)

    def test_get_author_schema_data_simple_tag(self):
        """Test the get_author_schema_data simple tag."""
        result = get_author_schema_data(self.user, self.request)
        
        # Should return dictionary
        self.assertIsInstance(result, dict)
        self.assertEqual(result['@type'], 'Person')
        self.assertEqual(result['name'], 'Test Author')

    def test_to_schema_date_filter_datetime(self):
        """Test to_schema_date filter with datetime objects."""
        # Test with datetime
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        result = to_schema_date(dt)
        self.assertEqual(result, '2024-01-15T14:30:00+00:00')
        
        # Test with naive datetime
        dt_naive = datetime(2024, 1, 15, 14, 30, 0)
        result = to_schema_date(dt_naive)
        self.assertEqual(result, '2024-01-15T14:30:00')

    def test_to_schema_date_filter_date(self):
        """Test to_schema_date filter with date objects."""
        d = date(2024, 1, 15)
        result = to_schema_date(d)
        self.assertEqual(result, '2024-01-15T00:00:00')

    def test_to_schema_date_filter_string(self):
        """Test to_schema_date filter with string dates."""
        # Test ISO string
        iso_string = '2024-01-15T14:30:00Z'
        result = to_schema_date(iso_string)
        self.assertEqual(result, '2024-01-15T14:30:00+00:00')
        
        # Test invalid string
        invalid_string = 'not a date'
        result = to_schema_date(invalid_string)
        self.assertEqual(result, 'not a date')

    def test_to_schema_date_filter_empty(self):
        """Test to_schema_date filter with empty values."""
        self.assertEqual(to_schema_date(None), "")
        self.assertEqual(to_schema_date(""), "")

    def test_to_schema_duration_filter(self):
        """Test to_schema_duration filter."""
        # Test minutes
        self.assertEqual(to_schema_duration(5), "PT5M")
        self.assertEqual(to_schema_duration(30), "PT30M")
        
        # Test hours
        self.assertEqual(to_schema_duration(60), "PT1H")
        self.assertEqual(to_schema_duration(90), "PT1H30M")
        self.assertEqual(to_schema_duration(120), "PT2H")
        
        # Test string input
        self.assertEqual(to_schema_duration("15"), "PT15M")
        self.assertEqual(to_schema_duration("75.5"), "PT75M")
        
        # Test empty values
        self.assertEqual(to_schema_duration(None), "")
        self.assertEqual(to_schema_duration(""), "")
        self.assertEqual(to_schema_duration(0), "PT0M")

    def test_schema_escape_filter(self):
        """Test schema_escape filter."""
        # Test basic escaping
        text = 'Text with "quotes" and <tags>'
        result = schema_escape(text)
        self.assertIn('\\"', result)
        self.assertNotIn('<', result)
        
        # Test newlines and tabs
        text_with_whitespace = 'Line 1\nLine 2\tTabbed'
        result = schema_escape(text_with_whitespace)
        self.assertIn('\\n', result)
        self.assertIn('\\t', result)
        
        # Test empty values
        self.assertEqual(schema_escape(None), "")
        self.assertEqual(schema_escape(""), "")

    def test_truncate_headline_filter(self):
        """Test truncate_headline filter."""
        # Test long headline
        long_title = "This is a very long headline that exceeds the recommended length for SEO optimization and should be truncated"
        result = truncate_headline(long_title)
        self.assertTrue(len(result) <= 110)
        self.assertTrue(result.endswith('...'))
        
        # Test custom length
        result_custom = truncate_headline(long_title, 50)
        self.assertTrue(len(result_custom) <= 50)
        
        # Test short headline
        short_title = "Short title"
        result_short = truncate_headline(short_title)
        self.assertEqual(result_short, short_title)
        
        # Test empty values
        self.assertEqual(truncate_headline(None), "")
        self.assertEqual(truncate_headline(""), "")

    def test_validate_schema_simple_tag(self):
        """Test validate_schema simple tag."""
        # Test valid schema
        valid_schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "Test",
            "author": {"@type": "Person", "name": "Author"},
            "publisher": {"@type": "Organization", "name": "Publisher"},
            "datePublished": "2024-01-01T00:00:00Z"
        }
        self.assertTrue(validate_schema(valid_schema))
        
        # Test invalid schema
        invalid_schema = {"@type": "Article"}
        self.assertFalse(validate_schema(invalid_schema))

    def test_schema_debug_info_simple_tag(self):
        """Test schema_debug_info simple tag."""
        schema_data = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "Test",
            "author": {"@type": "Person", "name": "Author"},
            "publisher": {"@type": "Organization", "name": "Publisher"},
            "datePublished": "2024-01-01T00:00:00Z"
        }
        
        result = schema_debug_info(schema_data)
        self.assertIn("Article", result)
        self.assertIn("Has Context: True", result)
        self.assertIn("All Required Fields Present", result)
        
        # Test empty schema
        empty_result = schema_debug_info({})
        self.assertIn("Empty schema data", empty_result)

    def test_template_integration(self):
        """Test template tags integration in actual templates."""
        # Test inclusion tag in template
        template_content = """
        {% load schema_tags %}
        {% render_article_schema post %}
        """
        template = Template(template_content)
        rendered = template.render(self.context)
        
        # Should contain script tag
        self.assertIn('<script type="application/ld+json">', rendered)
        self.assertIn('</script>', rendered)
        
        # Test simple tag in template
        template_content = """
        {% load schema_tags %}
        {% get_article_schema_json post as schema_json %}
        {{ schema_json|safe }}
        """
        template = Template(template_content)
        rendered = template.render(self.context)
        
        # Should contain JSON
        self.assertIn('"@type": "Article"', rendered)

    def test_template_filters_in_template(self):
        """Test template filters in actual templates."""
        # Test date filter
        template_content = """
        {% load schema_tags %}
        {{ post.created_at|to_schema_date }}
        """
        template = Template(template_content)
        rendered = template.render(self.context)
        
        # Should contain ISO date
        self.assertRegex(rendered.strip(), r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
        
        # Test duration filter
        template_content = """
        {% load schema_tags %}
        {{ "5"|to_schema_duration }}
        """
        template = Template(template_content)
        rendered = template.render(Context())
        
        self.assertEqual(rendered.strip(), "PT5M")
        
        # Test headline truncation
        template_content = """
        {% load schema_tags %}
        {{ "Very long title that should be truncated"|truncate_headline:20 }}
        """
        template = Template(template_content)
        rendered = template.render(Context())
        
        self.assertTrue(len(rendered.strip()) <= 20)

    def test_error_handling_in_templates(self):
        """Test error handling in template context."""
        # Test with None post
        context_with_none = Context({'request': self.request, 'post': None})
        
        template_content = """
        {% load schema_tags %}
        {% render_article_schema post %}
        """
        template = Template(template_content)
        
        # Should not raise exception
        try:
            rendered = template.render(context_with_none)
            # Should render something (even if empty)
            self.assertIsInstance(rendered, str)
        except Exception as e:
            self.fail(f"Template rendering failed with None post: {e}")

    def test_context_requirement(self):
        """Test that context-dependent tags work correctly."""
        # Test without request in context
        context_no_request = Context({'post': self.post})
        
        result = get_article_schema_json(context_no_request, self.post)
        
        # Should still work but URLs might be relative
        self.assertIsInstance(result, str)
        try:
            parsed = json.loads(result)
            self.assertEqual(parsed['@type'], 'Article')
        except json.JSONDecodeError:
            self.fail("Schema generation failed without request context")

    def test_performance_with_large_content(self):
        """Test template tag performance with large content."""
        # Create post with large content
        large_content = "<p>" + "Large content paragraph. " * 1000 + "</p>"
        large_post = Post.objects.create(
            title='Large Content Post',
            slug='large-content-post',
            author=self.user,
            content=large_content,
            status='published'
        )
        
        # Test that schema generation completes in reasonable time
        import time
        start_time = time.time()
        
        result = get_article_schema_json(self.context, large_post)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within 1 second
        self.assertLess(execution_time, 1.0)
        
        # Should still produce valid JSON
        try:
            parsed = json.loads(result)
            self.assertEqual(parsed['@type'], 'Article')
        except json.JSONDecodeError:
            self.fail("Schema generation failed for large content")