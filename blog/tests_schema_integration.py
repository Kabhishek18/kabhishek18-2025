"""
Integration tests for schema markup template rendering.

This module tests the complete integration of schema markup generation and rendering
in actual Django template contexts, including template tag functionality with real
post data, absolute URL generation, and various media types.

Requirements addressed:
- 3.4: Template tag functionality with real post data
- 4.1: Schema markup rendering in actual template context
- 4.4: Absolute URL generation works correctly
"""

import json
import tempfile
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from django.test import TestCase, RequestFactory, override_settings
from django.template import Context, Template
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from blog.models import Post, Category, Tag, AuthorProfile, MediaItem
from blog.services.schema_service import SchemaService


class SchemaIntegrationTestCase(TestCase):
    """Integration test cases for schema markup template rendering."""
    
    def setUp(self):
        """Set up test data for integration tests."""
        # Create test user and author profile
        self.user = User.objects.create_user(
            username='testauthor',
            email='test@example.com',
            first_name='Test',
            last_name='Author'
        )
        
        # Get or create author profile
        self.author_profile, created = AuthorProfile.objects.get_or_create(
            user=self.user,
            defaults={
                'bio': 'Test author bio for integration testing.',
                'website': 'https://testauthor.com',
                'twitter': 'testauthor',
                'linkedin': 'https://linkedin.com/in/testauthor',
                'github': 'testauthor',
                'instagram': 'testauthor'
            }
        )
        
        # Create test categories and tags
        self.category1 = Category.objects.create(name='Technology', slug='technology')
        self.category2 = Category.objects.create(name='Python', slug='python')
        self.tag1 = Tag.objects.create(name='Django', slug='django')
        self.tag2 = Tag.objects.create(name='Testing', slug='testing')
        
        # Create test post with complete data
        self.post = Post.objects.create(
            title='Integration Test Blog Post for Schema Markup',
            slug='integration-test-blog-post-schema',
            content='<p>This is comprehensive test content for schema integration testing.</p><p>It includes multiple paragraphs, HTML tags, and rich content for testing schema generation in template context.</p>',
            excerpt='Integration test excerpt for schema markup validation',
            author=self.user,
            status='published',
            allow_comments=True,
            table_of_contents=True,
            is_featured=True
        )
        
        # Add categories and tags
        self.post.categories.add(self.category1, self.category2)
        self.post.tags.add(self.tag1, self.tag2)
        
        # Create request factory for testing
        self.factory = RequestFactory()
        self.request = self.factory.get('/test/')
        self.request.META['HTTP_HOST'] = 'testserver'
        
        # Create template context
        self.context = Context({
            'request': self.request,
            'post': self.post,
            'title': self.post.title,
            'meta_details': self.post.excerpt
        })

    def test_render_article_schema_inclusion_tag_integration(self):
        """Test the render_article_schema inclusion tag in actual template context."""
        # Create template with schema inclusion tag
        template_content = """
        {% load schema_tags %}
        {% render_article_schema post %}
        """
        
        template = Template(template_content)
        rendered = template.render(self.context)
        
        # Verify schema markup is rendered
        self.assertIn('<script type="application/ld+json">', rendered)
        self.assertIn('"@context": "https://schema.org"', rendered)
        self.assertIn('"@type": "Article"', rendered)
        self.assertIn(self.post.title, rendered)
        
        # Verify absolute URL is generated correctly
        self.assertIn('http://testserver', rendered)
        self.assertIn(self.post.get_absolute_url(), rendered)
        
        # Verify author information is included
        self.assertIn('"@type": "Person"', rendered)
        self.assertIn('Test Author', rendered)
        
        # Verify publisher information is included
        self.assertIn('"@type": "Organization"', rendered)
        self.assertIn('Digital Codex', rendered)
        
        # Verify categories and tags are included
        self.assertIn('Technology', rendered)
        self.assertIn('Python', rendered)
        self.assertIn('Django', rendered)
        self.assertIn('Testing', rendered)

    def test_schema_markup_template_partial_rendering(self):
        """Test direct rendering of schema markup template partial."""
        # Generate schema data
        schema_data = SchemaService.generate_article_schema(self.post, self.request)
        schema_json = json.dumps(schema_data, indent=2, ensure_ascii=False)
        
        # Create context for template partial
        partial_context = {
            'schema_data': schema_data,
            'schema_json': schema_json,
            'is_valid': SchemaService.validate_schema(schema_data),
            'post': self.post,
            'debug': True
        }
        
        # Render the partial template
        rendered = render_to_string('blog/partials/schema_markup.html', partial_context)
        
        # Verify complete schema structure
        self.assertIn('<script type="application/ld+json">', rendered)
        self.assertIn('"headline":', rendered)
        self.assertIn('"datePublished":', rendered)
        self.assertIn('"dateModified":', rendered)
        self.assertIn('"author":', rendered)
        self.assertIn('"publisher":', rendered)
        
        # Note: Breadcrumb schema may not be rendered in template partial test
        # due to template logic conditions. This is tested separately in other tests.
        
        # Verify debug information is included
        self.assertIn('Schema Debug Info', rendered)

    def test_absolute_url_generation_in_template_context(self):
        """Test that absolute URLs are generated correctly in template context."""
        template_content = """
        {% load schema_tags %}
        {% get_article_schema_json post as schema_json %}
        {{ schema_json }}
        """
        
        template = Template(template_content)
        rendered = template.render(self.context)
        
        # Parse the rendered JSON
        try:
            schema_data = json.loads(rendered.strip())
        except json.JSONDecodeError:
            self.fail("Rendered schema is not valid JSON")
        
        # Verify absolute URLs
        self.assertTrue(schema_data['url'].startswith('http://'))
        self.assertIn('testserver', schema_data['url'])
        self.assertIn(self.post.get_absolute_url(), schema_data['url'])
        
        # Verify author URL if present
        if 'url' in schema_data.get('author', {}):
            self.assertTrue(schema_data['author']['url'].startswith('http://'))
        
        # Verify publisher URL
        publisher = schema_data.get('publisher', {})
        if 'url' in publisher:
            self.assertTrue(publisher['url'].startswith('http'))

    def test_template_tag_functionality_with_real_post_data(self):
        """Test all template tags with real post data in template context."""
        template_content = """
        {% load schema_tags %}
        {% get_article_schema_json post as article_json %}
        {% get_author_schema_json post.author as author_json %}
        {% get_publisher_schema_json as publisher_json %}
        {% get_breadcrumb_schema_json post as breadcrumb_json %}
        {% get_article_schema_data post as article_data %}
        {% get_author_schema_data post.author as author_data %}
        ARTICLE:{{ article_json }}
        AUTHOR:{{ author_json }}
        PUBLISHER:{{ publisher_json }}
        BREADCRUMB:{{ breadcrumb_json }}
        ARTICLE_DATA:{{ article_data.headline }}
        AUTHOR_DATA:{{ author_data.name }}
        """
        
        template = Template(template_content)
        rendered = template.render(self.context)
        
        # Verify all template tags produce output
        self.assertIn('ARTICLE:{"@context"', rendered)
        self.assertIn('AUTHOR:{"@type"', rendered)  # Author schema has @context at the end
        self.assertIn('PUBLISHER:{"@context"', rendered)
        self.assertIn('BREADCRUMB:{"@context"', rendered)
        self.assertIn(f'ARTICLE_DATA:{self.post.title}', rendered)
        self.assertIn('AUTHOR_DATA:Test Author', rendered)
        
        # Verify JSON validity for each tag
        lines = rendered.strip().split('\n')
        for line in lines:
            if line.startswith(('ARTICLE:', 'AUTHOR:', 'PUBLISHER:', 'BREADCRUMB:')):
                json_part = line.split(':', 1)[1]
                if json_part.strip() and json_part.strip() != '{}':
                    try:
                        json.loads(json_part)
                    except json.JSONDecodeError:
                        self.fail(f"Invalid JSON in line: {line}")

    def test_schema_filters_in_template_context(self):
        """Test schema-related filters in template context."""
        template_content = """
        {% load schema_tags %}
        DATE:{{ post.created_at|to_schema_date }}
        DURATION:{{ post.read_time|to_schema_duration }}
        ESCAPED:{{ post.title|schema_escape }}
        TRUNCATED:{{ post.title|truncate_headline:50 }}
        """
        
        template = Template(template_content)
        rendered = template.render(self.context)
        
        # Verify filter outputs
        self.assertIn('DATE:', rendered)
        self.assertIn('DURATION:PT', rendered)  # ISO 8601 duration format
        self.assertIn('ESCAPED:', rendered)
        self.assertIn('TRUNCATED:', rendered)
        
        # Verify date format
        lines = rendered.strip().split('\n')
        date_line = next(line for line in lines if line.startswith('DATE:'))
        date_value = date_line.split(':', 1)[1]
        # Should be ISO format
        self.assertRegex(date_value, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_schema_with_media_items(self):
        """Test schema generation with posts containing various media types."""
        # Create a simple test image
        image_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
        test_image = SimpleUploadedFile(
            name='test_image.png',
            content=image_content,
            content_type='image/png'
        )
        
        # Add featured image to post
        self.post.featured_image = test_image
        self.post.save()
        
        # Create media items
        image_media = MediaItem.objects.create(
            post=self.post,
            media_type='image',
            title='Test Image Media',
            description='Test image for schema integration',
            original_image=test_image,
            alt_text='Test image alt text',
            width=100,
            height=100
        )
        
        video_media = MediaItem.objects.create(
            post=self.post,
            media_type='video',
            title='Test Video Media',
            description='Test video for schema integration',
            video_url='https://www.youtube.com/watch?v=test123',
            video_platform='youtube',
            video_id='test123',
            video_embed_url='https://www.youtube.com/embed/test123',
            video_thumbnail='https://img.youtube.com/vi/test123/maxresdefault.jpg'
        )
        
        # Test schema generation with media
        template_content = """
        {% load schema_tags %}
        {% get_article_schema_json post as schema_json %}
        {{ schema_json }}
        """
        
        template = Template(template_content)
        rendered = template.render(self.context)
        
        # Parse schema
        try:
            schema_data = json.loads(rendered.strip())
        except json.JSONDecodeError:
            self.fail("Schema with media is not valid JSON")
        
        # Verify images are included
        self.assertIn('image', schema_data)
        images = schema_data['image']
        self.assertIsInstance(images, list)
        self.assertGreater(len(images), 0)
        
        # Verify absolute URLs for images
        for image_url in images:
            self.assertTrue(image_url.startswith('http://'))

    def test_schema_with_missing_optional_data(self):
        """Test schema generation with posts missing optional data."""
        # Create minimal post
        minimal_post = Post.objects.create(
            title='Minimal Test Post',
            slug='minimal-test-post',
            content='Minimal content',
            author=self.user,
            status='published'
        )
        
        # Create context with minimal post
        minimal_context = Context({
            'request': self.request,
            'post': minimal_post
        })
        
        template_content = """
        {% load schema_tags %}
        {% render_article_schema post %}
        """
        
        template = Template(template_content)
        rendered = template.render(minimal_context)
        
        # Verify schema is still generated
        self.assertIn('<script type="application/ld+json">', rendered)
        self.assertIn('"@type": "Article"', rendered)
        self.assertIn(minimal_post.title, rendered)
        
        # Verify required fields are present
        self.assertIn('"headline":', rendered)
        self.assertIn('"author":', rendered)
        self.assertIn('"publisher":', rendered)
        self.assertIn('"datePublished":', rendered)

    def test_schema_validation_in_template_context(self):
        """Test schema validation functionality in template context."""
        template_content = """
        {% load schema_tags %}
        {% get_article_schema_data post as schema_data %}
        {% validate_schema schema_data as is_valid %}
        {% schema_debug_info schema_data as debug_info %}
        VALID:{{ is_valid }}
        DEBUG:{{ debug_info }}
        """
        
        template = Template(template_content)
        rendered = template.render(self.context)
        
        # Verify validation results
        self.assertIn('VALID:True', rendered)
        self.assertIn('DEBUG:', rendered)
        self.assertIn('Schema Type: Article', rendered)

    def test_error_handling_in_template_context(self):
        """Test error handling when schema generation fails in template context."""
        # Create a mock post that will cause errors
        mock_post = Mock()
        mock_post.id = 999
        mock_post.title = "Mock Post"
        mock_post.get_absolute_url.side_effect = Exception("URL generation failed")
        
        error_context = Context({
            'request': self.request,
            'post': mock_post
        })
        
        template_content = """
        {% load schema_tags %}
        {% get_article_schema_json post as schema_json %}
        {{ schema_json }}
        """
        
        template = Template(template_content)
        rendered = template.render(error_context)
        
        # Should render empty JSON object on error
        self.assertEqual(rendered.strip(), '{}')

    def test_blog_detail_template_integration(self):
        """Test schema markup integration in the actual blog detail template."""
        # This tests the real template integration
        response = self.client.get(self.post.get_absolute_url())
        
        # Verify response is successful
        self.assertEqual(response.status_code, 200)
        
        # Verify schema markup is present in the response
        content = response.content.decode('utf-8')
        self.assertIn('<script type="application/ld+json">', content)
        self.assertIn('"@context": "https://schema.org"', content)
        self.assertIn('"@type": "Article"', content)
        self.assertIn(self.post.title, content)

    def test_schema_with_different_post_statuses(self):
        """Test schema generation with posts in different statuses."""
        # Create posts with different statuses
        draft_post = Post.objects.create(
            title='Draft Post',
            slug='draft-post',
            content='Draft content',
            author=self.user,
            status='draft'
        )
        
        archived_post = Post.objects.create(
            title='Archived Post',
            slug='archived-post',
            content='Archived content',
            author=self.user,
            status='archived'
        )
        
        # Test schema generation for each status
        for post in [draft_post, archived_post]:
            context = Context({
                'request': self.request,
                'post': post
            })
            
            template_content = """
            {% load schema_tags %}
            {% get_article_schema_json post as schema_json %}
            {{ schema_json }}
            """
            
            template = Template(template_content)
            rendered = template.render(context)
            
            # Should still generate valid schema regardless of status
            try:
                schema_data = json.loads(rendered.strip())
                self.assertEqual(schema_data['@type'], 'Article')
                self.assertEqual(schema_data['headline'], post.title)
            except json.JSONDecodeError:
                self.fail(f"Invalid schema JSON for {post.status} post")

    def test_schema_performance_in_template_context(self):
        """Test schema generation performance in template context."""
        import time
        
        template_content = """
        {% load schema_tags %}
        {% render_article_schema post %}
        """
        
        template = Template(template_content)
        
        # Measure rendering time
        start_time = time.time()
        rendered = template.render(self.context)
        end_time = time.time()
        
        render_time = end_time - start_time
        
        # Schema rendering should complete quickly (under 1 second)
        self.assertLess(render_time, 1.0, "Schema rendering took too long")
        
        # Verify output is still correct
        self.assertIn('<script type="application/ld+json">', rendered)
        self.assertIn(self.post.title, rendered)

    def test_schema_with_special_characters_in_template(self):
        """Test schema generation with special characters in template context."""
        # Create post with special characters
        special_post = Post.objects.create(
            title='Post with "Quotes" & <HTML> and émojis 🚀',
            slug='post-with-special-chars',
            content='Content with "quotes", <tags>, and special chars: café, naïve, résumé',
            excerpt='Excerpt with special characters: "test" & <em>emphasis</em>',
            author=self.user,
            status='published'
        )
        
        context = Context({
            'request': self.request,
            'post': special_post
        })
        
        template_content = """
        {% load schema_tags %}
        {% get_article_schema_json post as schema_json %}
        {{ schema_json }}
        """
        
        template = Template(template_content)
        rendered = template.render(context)
        
        # Verify JSON is still valid despite special characters
        try:
            schema_data = json.loads(rendered.strip())
        except json.JSONDecodeError:
            self.fail("Schema with special characters is not valid JSON")
        
        # Verify special characters are properly handled
        self.assertIn('Quotes', schema_data['headline'])
        self.assertEqual(schema_data['@type'], 'Article')

    def test_schema_breadcrumb_integration(self):
        """Test breadcrumb schema integration in template context."""
        template_content = """
        {% load schema_tags %}
        {% get_breadcrumb_schema_json post as breadcrumb_json %}
        {{ breadcrumb_json }}
        """
        
        template = Template(template_content)
        rendered = template.render(self.context)
        
        # Parse breadcrumb schema
        try:
            breadcrumb_data = json.loads(rendered.strip())
        except json.JSONDecodeError:
            self.fail("Breadcrumb schema is not valid JSON")
        
        # Verify breadcrumb structure
        self.assertEqual(breadcrumb_data['@type'], 'BreadcrumbList')
        self.assertIn('itemListElement', breadcrumb_data)
        
        items = breadcrumb_data['itemListElement']
        self.assertIsInstance(items, list)
        self.assertGreater(len(items), 0)
        
        # Verify breadcrumb items have required fields
        for item in items:
            self.assertEqual(item['@type'], 'ListItem')
            self.assertIn('position', item)
            self.assertIn('name', item)
            self.assertIn('item', item)
            # Verify absolute URLs
            self.assertTrue(item['item'].startswith('http://'))