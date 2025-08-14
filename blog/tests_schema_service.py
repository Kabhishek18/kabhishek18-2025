"""
Unit tests for the SchemaService class.

Tests all methods for generating Schema.org structured data markup
including article, author, and publisher schemas with validation
and error handling.
"""

import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from blog.models import Post, Category, Tag, AuthorProfile, MediaItem
from blog.services.schema_service import SchemaService


class SchemaServiceTestCase(TestCase):
    """Test cases for SchemaService."""
    
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
            bio='Test author bio for testing schema generation.',
            website='https://testauthor.com',
            twitter='testauthor',
            linkedin='https://linkedin.com/in/testauthor',
            github='testauthor'
        )
        
        # Create test categories and tags
        self.category = Category.objects.create(name='Technology', slug='technology')
        self.tag1 = Tag.objects.create(name='Python', slug='python')
        self.tag2 = Tag.objects.create(name='Django', slug='django')
        
        # Create test post
        self.post = Post.objects.create(
            title='Test Blog Post for Schema Generation',
            slug='test-blog-post-schema',
            author=self.user,
            content='<p>This is test content for schema generation testing. It contains multiple paragraphs and HTML tags.</p><p>Second paragraph with more content.</p>',
            excerpt='Test excerpt for schema generation',
            status='published'
        )
        self.post.categories.add(self.category)
        self.post.tags.add(self.tag1, self.tag2)
        
        # Create request object
        self.request = self.factory.get('/blog/test-post/')
        self.request.META['HTTP_HOST'] = 'testserver'

    def test_generate_article_schema_complete(self):
        """Test article schema generation with complete post data."""
        schema = SchemaService.generate_article_schema(self.post, self.request)
        
        # Verify basic structure
        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'Article')
        self.assertEqual(schema['headline'], self.post.title)
        self.assertIn('http://testserver', schema['url'])
        
        # Verify dates
        self.assertIsInstance(schema['datePublished'], str)
        self.assertIsInstance(schema['dateModified'], str)
        
        # Verify author
        self.assertIsInstance(schema['author'], dict)
        self.assertEqual(schema['author']['@type'], 'Person')
        self.assertEqual(schema['author']['name'], 'Test Author')
        
        # Verify publisher
        self.assertIsInstance(schema['publisher'], dict)
        self.assertEqual(schema['publisher']['@type'], 'Organization')
        
        # Verify content-derived fields
        self.assertEqual(schema['description'], self.post.excerpt)
        self.assertIn('wordCount', schema)
        self.assertIn('timeRequired', schema)
        self.assertTrue(schema['timeRequired'].startswith('PT'))
        self.assertTrue(schema['timeRequired'].endswith('M'))
        
        # Verify categories and tags
        self.assertEqual(schema['articleSection'], ['Technology'])
        self.assertCountEqual(schema['keywords'], ['Python', 'Django'])
        
        # Verify main entity
        self.assertIn('mainEntityOfPage', schema)
        self.assertEqual(schema['mainEntityOfPage']['@type'], 'WebPage')

    def test_generate_article_schema_minimal_data(self):
        """Test article schema generation with minimal post data."""
        # Create minimal post
        minimal_post = Post.objects.create(
            title='Minimal Post',
            slug='minimal-post',
            author=self.user,
            content='Minimal content',
            status='published'
        )
        
        schema = SchemaService.generate_article_schema(minimal_post, self.request)
        
        # Verify required fields are present
        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'Article')
        self.assertEqual(schema['headline'], 'Minimal Post')
        self.assertIn('author', schema)
        self.assertIn('publisher', schema)
        self.assertIn('datePublished', schema)
        self.assertIn('dateModified', schema)

    def test_generate_article_schema_without_request(self):
        """Test article schema generation without request object."""
        with patch.object(settings, 'SITE_DOMAIN', 'example.com'):
            schema = SchemaService.generate_article_schema(self.post)
            
            self.assertIn('https://example.com', schema['url'])
            self.assertEqual(schema['@type'], 'Article')

    def test_generate_article_schema_with_images(self):
        """Test article schema generation with featured image and media items."""
        # Create a simple test image file
        image_content = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b'
        test_image = SimpleUploadedFile(
            name='test_image.gif',
            content=image_content,
            content_type='image/gif'
        )
        
        # Add featured image to post
        self.post.featured_image = test_image
        self.post.save()
        
        # Create media item
        MediaItem.objects.create(
            post=self.post,
            media_type='image',
            original_image=test_image,
            title='Test Media Image'
        )
        
        schema = SchemaService.generate_article_schema(self.post, self.request)
        
        # Verify images are included
        self.assertIn('image', schema)
        self.assertIsInstance(schema['image'], list)
        self.assertTrue(len(schema['image']) > 0)

    def test_generate_author_schema_with_profile(self):
        """Test author schema generation with complete author profile."""
        schema = SchemaService.generate_author_schema(self.user, self.request)
        
        # Verify basic structure
        self.assertEqual(schema['@type'], 'Person')
        self.assertEqual(schema['name'], 'Test Author')
        self.assertEqual(schema['description'], self.author_profile.bio)
        
        # Verify social media links
        self.assertIn('sameAs', schema)
        same_as = schema['sameAs']
        self.assertIn('https://testauthor.com', same_as)
        self.assertIn('https://twitter.com/testauthor', same_as)
        self.assertIn('https://linkedin.com/in/testauthor', same_as)
        self.assertIn('https://github.com/testauthor', same_as)

    def test_generate_author_schema_without_profile(self):
        """Test author schema generation for user without author profile."""
        # Create user without profile
        user_no_profile = User.objects.create_user(
            username='noprofile',
            email='noprofile@example.com'
        )
        
        schema = SchemaService.generate_author_schema(user_no_profile, self.request)
        
        # Verify minimal schema
        self.assertEqual(schema['@type'], 'Person')
        self.assertEqual(schema['name'], 'noprofile')
        self.assertNotIn('sameAs', schema)
        self.assertNotIn('description', schema)

    def test_generate_author_schema_with_author_profile_instance(self):
        """Test author schema generation when passed AuthorProfile instance."""
        schema = SchemaService.generate_author_schema(self.author_profile, self.request)
        
        self.assertEqual(schema['@type'], 'Person')
        self.assertEqual(schema['name'], 'Test Author')
        self.assertEqual(schema['description'], self.author_profile.bio)

    def test_generate_publisher_schema_default(self):
        """Test publisher schema generation with default settings."""
        schema = SchemaService.generate_publisher_schema()
        
        # Verify structure
        self.assertEqual(schema['@type'], 'Organization')
        self.assertIn('name', schema)
        self.assertIn('url', schema)
        self.assertIn('logo', schema)
        
        # Verify logo structure
        logo = schema['logo']
        self.assertEqual(logo['@type'], 'ImageObject')
        self.assertIn('url', logo)
        self.assertIn('width', logo)
        self.assertIn('height', logo)

    def test_generate_publisher_schema_custom_settings(self):
        """Test publisher schema generation with custom settings."""
        with patch.object(settings, 'SITE_NAME', 'Custom Site'):
            with patch.object(settings, 'SITE_URL', 'https://custom.com'):
                schema = SchemaService.generate_publisher_schema()
                
                self.assertEqual(schema['name'], 'Custom Site')
                self.assertEqual(schema['url'], 'https://custom.com')

    def test_generate_breadcrumb_schema(self):
        """Test breadcrumb schema generation."""
        schema = SchemaService.generate_breadcrumb_schema(self.post, self.request)
        
        # Verify structure
        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'BreadcrumbList')
        self.assertIn('itemListElement', schema)
        
        # Verify breadcrumb items
        items = schema['itemListElement']
        self.assertTrue(len(items) >= 2)  # At least Home and current post
        
        # Verify first item is Home
        self.assertEqual(items[0]['@type'], 'ListItem')
        self.assertEqual(items[0]['position'], 1)
        self.assertEqual(items[0]['name'], 'Home')
        
        # Verify last item is current post
        last_item = items[-1]
        self.assertEqual(last_item['name'], self.post.title)

    def test_validate_schema_valid_article(self):
        """Test schema validation with valid article schema."""
        schema = SchemaService.generate_article_schema(self.post, self.request)
        self.assertTrue(SchemaService.validate_schema(schema))

    def test_validate_schema_valid_person(self):
        """Test schema validation with valid person schema."""
        schema = SchemaService.generate_author_schema(self.user, self.request)
        self.assertTrue(SchemaService.validate_schema(schema))

    def test_validate_schema_valid_organization(self):
        """Test schema validation with valid organization schema."""
        schema = SchemaService.generate_publisher_schema()
        self.assertTrue(SchemaService.validate_schema(schema))

    def test_validate_schema_invalid_missing_context(self):
        """Test schema validation with missing context."""
        invalid_schema = {
            "@type": "Article",
            "headline": "Test"
        }
        self.assertFalse(SchemaService.validate_schema(invalid_schema))

    def test_validate_schema_invalid_missing_type(self):
        """Test schema validation with missing type."""
        invalid_schema = {
            "@context": "https://schema.org",
            "headline": "Test"
        }
        self.assertFalse(SchemaService.validate_schema(invalid_schema))

    def test_validate_schema_invalid_missing_required_fields(self):
        """Test schema validation with missing required fields."""
        invalid_schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "Test"
            # Missing author, publisher, datePublished
        }
        self.assertFalse(SchemaService.validate_schema(invalid_schema))

    def test_validate_schema_invalid_not_dict(self):
        """Test schema validation with non-dictionary input."""
        self.assertFalse(SchemaService.validate_schema("not a dict"))
        self.assertFalse(SchemaService.validate_schema(None))
        self.assertFalse(SchemaService.validate_schema([]))

    def test_truncate_headline(self):
        """Test headline truncation for SEO optimization."""
        long_title = "This is a very long title that exceeds the recommended length for SEO and should be truncated properly"
        truncated = SchemaService._truncate_headline(long_title, 50)
        
        self.assertTrue(len(truncated) <= 50)
        self.assertTrue(truncated.endswith('...'))
        
        # Test short title remains unchanged
        short_title = "Short title"
        self.assertEqual(SchemaService._truncate_headline(short_title, 50), short_title)

    def test_clean_text(self):
        """Test text cleaning functionality."""
        html_text = "<p>This is <strong>HTML</strong> content with   extra   spaces.</p>"
        cleaned = SchemaService._clean_text(html_text)
        
        self.assertEqual(cleaned, "This is HTML content with extra spaces.")
        
        # Test empty text
        self.assertEqual(SchemaService._clean_text(""), "")
        self.assertEqual(SchemaService._clean_text(None), "")

    def test_get_post_images(self):
        """Test getting post images for schema markup."""
        # Create test image
        image_content = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b'
        test_image = SimpleUploadedFile(
            name='test_image.gif',
            content=image_content,
            content_type='image/gif'
        )
        
        self.post.featured_image = test_image
        self.post.save()
        
        images = SchemaService._get_post_images(self.post, self.request)
        
        self.assertIsInstance(images, list)
        self.assertTrue(len(images) > 0)
        self.assertTrue(all(img.startswith('http') for img in images))

    def test_get_minimal_article_schema(self):
        """Test minimal article schema generation as fallback."""
        schema = SchemaService._get_minimal_article_schema(self.post, self.request)
        
        # Verify minimal required fields
        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'Article')
        self.assertEqual(schema['headline'], self.post.title)
        self.assertIn('url', schema)
        self.assertIn('datePublished', schema)
        self.assertIn('author', schema)
        self.assertIn('publisher', schema)

    def test_error_handling_invalid_post(self):
        """Test error handling with invalid post data."""
        # Create a mock post that will cause errors
        mock_post = Mock()
        mock_post.id = 999
        mock_post.title = None  # This should cause issues
        mock_post.get_absolute_url.side_effect = Exception("URL error")
        
        # Should not raise exception, should return minimal schema or empty dict
        schema = SchemaService.generate_article_schema(mock_post, self.request)
        self.assertIsInstance(schema, dict)

    def test_json_serialization(self):
        """Test that generated schemas can be serialized to JSON."""
        schemas = [
            SchemaService.generate_article_schema(self.post, self.request),
            SchemaService.generate_author_schema(self.user, self.request),
            SchemaService.generate_publisher_schema(),
            SchemaService.generate_breadcrumb_schema(self.post, self.request)
        ]
        
        for schema in schemas:
            if schema:  # Skip empty schemas
                try:
                    json_str = json.dumps(schema)
                    # Verify we can parse it back
                    parsed = json.loads(json_str)
                    self.assertIsInstance(parsed, dict)
                except (TypeError, ValueError) as e:
                    self.fail(f"Schema serialization failed: {e}")

    def test_iso_date_format(self):
        """Test that dates are in ISO 8601 format."""
        schema = SchemaService.generate_article_schema(self.post, self.request)
        
        # Verify date format
        date_published = schema['datePublished']
        date_modified = schema['dateModified']
        
        # Should be able to parse as ISO format
        try:
            datetime.fromisoformat(date_published.replace('Z', '+00:00'))
            datetime.fromisoformat(date_modified.replace('Z', '+00:00'))
        except ValueError as e:
            self.fail(f"Invalid ISO date format: {e}")

    def test_reading_time_format(self):
        """Test that reading time is in ISO 8601 duration format."""
        schema = SchemaService.generate_article_schema(self.post, self.request)
        
        if 'timeRequired' in schema:
            time_required = schema['timeRequired']
            # Should match PT{minutes}M format
            self.assertTrue(time_required.startswith('PT'))
            self.assertTrue(time_required.endswith('M'))
            
            # Extract minutes and verify it's a number
            minutes_str = time_required[2:-1]  # Remove PT and M
            try:
                minutes = int(minutes_str)
                self.assertGreater(minutes, 0)
            except ValueError:
                self.fail(f"Invalid duration format: {time_required}")

    def test_generate_article_schema_with_missing_dates(self):
        """Test article schema generation when post has invalid date fields."""
        # Create a mock post with problematic dates
        mock_post = Mock()
        mock_post.id = 1
        mock_post.title = "Test Post"
        mock_post.slug = "test-post"
        mock_post.content = "Test content"
        mock_post.excerpt = "Test excerpt"
        mock_post.author = self.user
        mock_post.categories.values_list.return_value = []
        mock_post.tags.values_list.return_value = []
        mock_post.media_items.filter.return_value = []
        mock_post.get_absolute_url.return_value = "/test-post/"
        mock_post.get_reading_time.return_value = 5
        
        # Set problematic date attributes
        mock_post.created_at = None
        mock_post.updated_at = None
        
        schema = SchemaService.generate_article_schema(mock_post, self.request)
        
        # Should have fallback dates
        self.assertIn('datePublished', schema)
        self.assertIn('dateModified', schema)
        self.assertEqual(schema['datePublished'], "2024-01-01T00:00:00Z")
        self.assertEqual(schema['dateModified'], "2024-01-01T00:00:00Z")

    def test_generate_author_schema_with_social_media_variations(self):
        """Test author schema generation with various social media username formats."""
        # Test with @ prefix in social media usernames
        self.author_profile.twitter = "@testuser"
        self.author_profile.instagram = "@testuser"
        self.author_profile.save()
        
        schema = SchemaService.generate_author_schema(self.user, self.request)
        
        same_as = schema['sameAs']
        # Should handle @ prefix correctly
        self.assertIn('https://twitter.com/testuser', same_as)
        self.assertIn('https://instagram.com/testuser', same_as)

    def test_generate_author_schema_error_handling(self):
        """Test author schema generation with various error conditions."""
        # Test with None author
        schema = SchemaService.generate_author_schema(None, self.request)
        self.assertEqual(schema['@type'], 'Person')
        self.assertEqual(schema['name'], 'Unknown Author')
        
        # Test with mock author that raises exceptions
        mock_author = Mock()
        mock_author.username = "testuser"
        mock_author.first_name = ""
        mock_author.last_name = ""
        mock_author.author_profile = None
        
        # Make hasattr return False for author_profile
        with patch('builtins.hasattr', return_value=False):
            schema = SchemaService.generate_author_schema(mock_author, self.request)
            self.assertEqual(schema['@type'], 'Person')
            self.assertEqual(schema['name'], 'testuser')

    def test_validate_schema_embedded_schemas(self):
        """Test schema validation for embedded schemas (without @context)."""
        # Test embedded Person schema (like in Article.author)
        embedded_person = {
            "@type": "Person",
            "name": "Test Author"
        }
        self.assertTrue(SchemaService.validate_schema(embedded_person, is_embedded=True))
        
        # Test embedded Organization schema (like in Article.publisher)
        embedded_org = {
            "@type": "Organization",
            "name": "Test Publisher"
        }
        self.assertTrue(SchemaService.validate_schema(embedded_org, is_embedded=True))

    def test_validate_schema_json_serialization_errors(self):
        """Test schema validation with objects that can't be JSON serialized."""
        # Create schema with non-serializable object
        invalid_schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "Test",
            "author": {"@type": "Person", "name": "Test"},
            "publisher": {"@type": "Organization", "name": "Test"},
            "datePublished": "2024-01-01",
            "nonSerializable": object()  # This can't be JSON serialized
        }
        
        self.assertFalse(SchemaService.validate_schema(invalid_schema))

    def test_generate_publisher_schema_error_handling(self):
        """Test publisher schema generation with settings access errors."""
        # Mock settings to raise AttributeError
        with patch('blog.services.schema_service.settings') as mock_settings:
            mock_settings.SITE_NAME = Mock(side_effect=AttributeError("Setting not found"))
            
            schema = SchemaService.generate_publisher_schema()
            
            # Should fall back to default publisher
            self.assertEqual(schema['name'], SchemaService.DEFAULT_PUBLISHER['name'])
            self.assertEqual(schema['url'], SchemaService.DEFAULT_PUBLISHER['url'])

    def test_get_post_images_without_request(self):
        """Test getting post images without request object."""
        # Create test image
        image_content = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b'
        test_image = SimpleUploadedFile(
            name='test_image.gif',
            content=image_content,
            content_type='image/gif'
        )
        
        self.post.featured_image = test_image
        self.post.save()
        
        with patch.object(settings, 'SITE_DOMAIN', 'example.com'):
            images = SchemaService._get_post_images(self.post)
            
            self.assertIsInstance(images, list)
            self.assertTrue(len(images) > 0)
            self.assertTrue(all('https://example.com' in img for img in images))

    def test_get_post_images_error_handling(self):
        """Test image retrieval with various error conditions."""
        # Create mock post that raises exceptions
        mock_post = Mock()
        mock_post.featured_image = None
        mock_post.social_image = None
        mock_post.media_items.filter.side_effect = Exception("Database error")
        
        images = SchemaService._get_post_images(mock_post, self.request)
        
        # Should return empty list on error
        self.assertEqual(images, [])

    def test_generate_breadcrumb_schema_without_request(self):
        """Test breadcrumb schema generation without request object."""
        schema = SchemaService.generate_breadcrumb_schema(self.post)
        
        # Should return empty dict without request
        self.assertEqual(schema, {})

    def test_generate_breadcrumb_schema_url_reverse_error(self):
        """Test breadcrumb schema generation when URL reverse fails."""
        with patch('blog.services.schema_service.reverse', side_effect=Exception("URL not found")):
            schema = SchemaService.generate_breadcrumb_schema(self.post, self.request)
            
            # Should still generate schema with Home and current post
            self.assertEqual(schema['@type'], 'BreadcrumbList')
            items = schema['itemListElement']
            self.assertTrue(len(items) >= 2)

    def test_article_schema_word_count_calculation(self):
        """Test word count calculation in article schema."""
        # Create post with known word count
        test_content = "This is a test post with exactly ten words in it."
        self.post.content = test_content
        self.post.save()
        
        schema = SchemaService.generate_article_schema(self.post, self.request)
        
        # Should calculate word count correctly
        self.assertIn('wordCount', schema)
        expected_words = len(test_content.split())
        self.assertEqual(schema['wordCount'], expected_words)

    def test_article_schema_description_generation(self):
        """Test description generation from content when excerpt is missing."""
        # Remove excerpt and test content-based description
        self.post.excerpt = ""
        self.post.content = "<p>This is the first paragraph of content.</p><p>This is the second paragraph with more details.</p>"
        self.post.save()
        
        schema = SchemaService.generate_article_schema(self.post, self.request)
        
        # Should generate description from content
        self.assertIn('description', schema)
        self.assertIn('This is the first paragraph', schema['description'])
        # Should be truncated to 30 words
        word_count = len(schema['description'].split())
        self.assertLessEqual(word_count, 30)

    def test_standalone_author_schema(self):
        """Test standalone author schema generation with @context."""
        schema = SchemaService.generate_standalone_author_schema(self.user, self.request)
        
        # Should include @context for standalone use
        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'Person')
        self.assertEqual(schema['name'], 'Test Author')

    def test_schema_compliance_with_google_requirements(self):
        """Test that generated schemas meet Google's rich results requirements."""
        schema = SchemaService.generate_article_schema(self.post, self.request)
        
        # Google requires these fields for Article rich results
        required_fields = ['headline', 'image', 'datePublished', 'dateModified']
        for field in required_fields:
            self.assertIn(field, schema, f"Missing required field for Google rich results: {field}")
        
        # Author should be properly structured
        author = schema['author']
        self.assertEqual(author['@type'], 'Person')
        self.assertIn('name', author)
        
        # Publisher should be properly structured
        publisher = schema['publisher']
        self.assertEqual(publisher['@type'], 'Organization')
        self.assertIn('name', publisher)
        self.assertIn('logo', publisher)

    def test_schema_url_generation_edge_cases(self):
        """Test URL generation in various edge cases."""
        # Test with custom SITE_DOMAIN setting
        with patch.object(settings, 'SITE_DOMAIN', 'custom-domain.com'):
            schema = SchemaService.generate_article_schema(self.post)
            self.assertIn('https://custom-domain.com', schema['url'])
        
        # Test with missing SITE_DOMAIN setting
        with patch.object(settings, 'SITE_DOMAIN', None):
            schema = SchemaService.generate_article_schema(self.post)
            # Should fall back to default
            self.assertIn('kabhishek18.com', schema['url'])


class SchemaServiceValidationTestCase(TestCase):
    """Additional test cases focusing on schema validation and compliance."""
    
    def setUp(self):
        """Set up test data for validation tests."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='validator',
            email='validator@example.com',
            first_name='Schema',
            last_name='Validator'
        )
        
        self.post = Post.objects.create(
            title='Validation Test Post',
            slug='validation-test-post',
            author=self.user,
            content='Content for validation testing.',
            status='published'
        )
        
        self.request = self.factory.get('/test/')
        self.request.META['HTTP_HOST'] = 'testserver'

    def test_schema_org_compliance_article(self):
        """Test that Article schema complies with Schema.org specifications."""
        schema = SchemaService.generate_article_schema(self.post, self.request)
        
        # Required properties for Article according to Schema.org
        required_properties = ['@context', '@type', 'headline', 'author', 'datePublished']
        for prop in required_properties:
            self.assertIn(prop, schema, f"Missing required Schema.org property: {prop}")
        
        # Verify types
        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'Article')
        self.assertIsInstance(schema['headline'], str)
        self.assertIsInstance(schema['author'], dict)
        self.assertIsInstance(schema['datePublished'], str)

    def test_schema_org_compliance_person(self):
        """Test that Person schema complies with Schema.org specifications."""
        schema = SchemaService.generate_standalone_author_schema(self.user, self.request)
        
        # Required properties for Person according to Schema.org
        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'Person')
        self.assertIn('name', schema)
        self.assertIsInstance(schema['name'], str)

    def test_schema_org_compliance_organization(self):
        """Test that Organization schema complies with Schema.org specifications."""
        schema = SchemaService.generate_publisher_schema()
        
        # Required properties for Organization according to Schema.org
        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'Organization')
        self.assertIn('name', schema)
        self.assertIsInstance(schema['name'], str)

    def test_google_rich_results_requirements(self):
        """Test compliance with Google Rich Results requirements for Article."""
        schema = SchemaService.generate_article_schema(self.post, self.request)
        
        # Google requires these for Article rich results
        google_required = ['headline', 'datePublished', 'dateModified']
        for field in google_required:
            self.assertIn(field, schema, f"Missing Google required field: {field}")
        
        # Author must be Person or Organization
        author = schema['author']
        self.assertIn(author['@type'], ['Person', 'Organization'])
        
        # Publisher must be Organization
        publisher = schema['publisher']
        self.assertEqual(publisher['@type'], 'Organization')
        self.assertIn('name', publisher)

    def test_structured_data_testing_tool_compatibility(self):
        """Test that schemas are compatible with Google's Structured Data Testing Tool."""
        schemas = [
            SchemaService.generate_article_schema(self.post, self.request),
            SchemaService.generate_standalone_author_schema(self.user, self.request),
            SchemaService.generate_publisher_schema(),
        ]
        
        for schema in schemas:
            # Must be valid JSON
            try:
                json_str = json.dumps(schema)
                json.loads(json_str)
            except (TypeError, ValueError) as e:
                self.fail(f"Schema not JSON serializable: {e}")
            
            # Must have required Schema.org properties
            self.assertIn('@context', schema)
            self.assertIn('@type', schema)
            self.assertEqual(schema['@context'], 'https://schema.org')

    def test_validation_with_missing_optional_fields(self):
        """Test validation when optional fields are missing."""
        # Create minimal valid schemas
        minimal_article = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "Test",
            "author": {"@type": "Person", "name": "Test Author"},
            "publisher": {"@type": "Organization", "name": "Test Publisher"},
            "datePublished": "2024-01-01T00:00:00Z"
        }
        
        minimal_person = {
            "@context": "https://schema.org",
            "@type": "Person",
            "name": "Test Person"
        }
        
        minimal_org = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Test Organization"
        }
        
        # All should validate successfully
        self.assertTrue(SchemaService.validate_schema(minimal_article))
        self.assertTrue(SchemaService.validate_schema(minimal_person))
        self.assertTrue(SchemaService.validate_schema(minimal_org))

    def test_validation_error_logging(self):
        """Test that validation errors are properly logged."""
        invalid_schemas = [
            {},  # Empty schema
            {"@type": "Article"},  # Missing context
            {"@context": "https://schema.org"},  # Missing type
            {"@context": "https://schema.org", "@type": "Article"},  # Missing required fields
        ]
        
        with patch('blog.services.schema_service.logger') as mock_logger:
            for schema in invalid_schemas:
                result = SchemaService.validate_schema(schema)
                self.assertFalse(result)
            
            # Should have logged warnings or errors
            self.assertTrue(mock_logger.warning.called or mock_logger.error.called)

    def test_error_recovery_and_fallbacks(self):
        """Test that service gracefully handles errors and provides fallbacks."""
        # Test with completely broken post object
        broken_post = Mock()
        broken_post.id = 999
        broken_post.title = "Test"
        broken_post.get_absolute_url.side_effect = Exception("Broken URL")
        broken_post.created_at = Mock()
        broken_post.created_at.isoformat.side_effect = Exception("Broken date")
        broken_post.updated_at = Mock()
        broken_post.updated_at.isoformat.side_effect = Exception("Broken date")
        broken_post.author = self.user
        broken_post.categories.values_list.side_effect = Exception("Broken categories")
        broken_post.tags.values_list.side_effect = Exception("Broken tags")
        
        # Should not raise exception
        schema = SchemaService.generate_article_schema(broken_post, self.request)
        
        # Should return some form of schema (minimal or empty)
        self.assertIsInstance(schema, dict)

    def test_performance_with_large_content(self):
        """Test schema generation performance with large content."""
        # Create post with large content
        large_content = "This is a test sentence. " * 1000  # ~5000 words
        large_post = Post.objects.create(
            title='Large Content Post',
            slug='large-content-post',
            author=self.user,
            content=large_content,
            status='published'
        )
        
        # Should handle large content without issues
        schema = SchemaService.generate_article_schema(large_post, self.request)
        
        # Verify word count is calculated
        self.assertIn('wordCount', schema)
        self.assertGreater(schema['wordCount'], 4000)
        
        # Verify reading time is reasonable
        self.assertIn('timeRequired', schema)
        reading_time = schema['timeRequired']
        minutes = int(reading_time[2:-1])  # Extract minutes from PT{X}M
        self.assertGreater(minutes, 15)  # Should be more than 15 minutes for 5000 words

    def test_unicode_and_special_characters(self):
        """Test schema generation with unicode and special characters."""
        unicode_post = Post.objects.create(
            title='Test with émojis 🚀 and spëcial chars',
            slug='unicode-test-post',
            author=self.user,
            content='Content with émojis 🎉 and spëcial characters like "quotes" & ampersands.',
            excerpt='Excerpt with spëcial chars',
            status='published'
        )
        
        schema = SchemaService.generate_article_schema(unicode_post, self.request)
        
        # Should handle unicode characters properly
        self.assertEqual(schema['headline'], unicode_post.title)
        self.assertIn('émojis', schema['headline'])
        self.assertIn('🚀', schema['headline'])
        
        # Should be JSON serializable
        try:
            json.dumps(schema, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            self.fail(f"Unicode schema not JSON serializable: {e}")

    def test_html_content_cleaning(self):
        """Test that HTML content is properly cleaned for schema markup."""
        html_post = Post.objects.create(
            title='HTML Content Test',
            slug='html-content-test',
            author=self.user,
            content='<p>This is <strong>bold</strong> and <em>italic</em> text with <a href="#">links</a>.</p>',
            excerpt='<p>HTML <strong>excerpt</strong> content.</p>',
            status='published'
        )
        
        schema = SchemaService.generate_article_schema(html_post, self.request)
        
        # Description should be cleaned of HTML tags
        self.assertNotIn('<p>', schema['description'])
        self.assertNotIn('<strong>', schema['description'])
        self.assertNotIn('</p>', schema['description'])
        self.assertIn('HTML excerpt content.', schema['description'])

    def test_date_format_compliance(self):
        """Test that all dates comply with ISO 8601 format."""
        schema = SchemaService.generate_article_schema(self.post, self.request)
        
        date_fields = ['datePublished', 'dateModified']
        for field in date_fields:
            if field in schema:
                date_value = schema[field]
                # Should be valid ISO 8601 format
                try:
                    # Handle both with and without timezone
                    if date_value.endswith('Z'):
                        datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                    else:
                        datetime.fromisoformat(date_value)
                except ValueError as e:
                    self.fail(f"Invalid ISO 8601 date format in {field}: {date_value} - {e}")

    def test_url_validation_and_security(self):
        """Test URL generation and validation for security."""
        schema = SchemaService.generate_article_schema(self.post, self.request)
        
        # All URLs should be absolute and use HTTPS
        url_fields = ['url']
        if 'image' in schema:
            url_fields.extend(schema['image'])
        
        for field in url_fields:
            if field in schema:
                url = schema[field]
                if isinstance(url, str):
                    self.assertTrue(url.startswith('http'), f"URL should be absolute: {url}")
                elif isinstance(url, list):
                    for u in url:
                        self.assertTrue(u.startswith('http'), f"URL should be absolute: {u}")