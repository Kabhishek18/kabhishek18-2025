"""
Comprehensive test suite for schema markup edge cases.

This module tests schema generation with various edge cases including:
- Missing featured images
- Posts with no categories or tags
- Guest authors and missing author profiles
- Various content types and special characters
- Graceful handling of all edge cases

Requirements covered: 1.5, 3.3, 4.5
"""

import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.db import IntegrityError

from blog.models import Post, Category, Tag, AuthorProfile, MediaItem
from blog.services.schema_service import SchemaService
from blog.templatetags.schema_tags import (
    render_article_schema, get_article_schema_json, get_author_schema_json
)


class SchemaEdgeCasesTestCase(TestCase):
    """Test cases for schema markup edge cases."""
    
    def setUp(self):
        """Set up test data for edge case testing."""
        self.factory = RequestFactory()
        
        # Create basic user for testing
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        
        # Create request object
        self.request = self.factory.get('/test/')
        self.request.META['HTTP_HOST'] = 'testserver'

    def test_schema_generation_with_missing_featured_image(self):
        """Test schema generation with posts that have no featured image."""
        # Create post without featured image
        post = Post.objects.create(
            title='Post Without Featured Image',
            slug='post-without-featured-image',
            author=self.user,
            content='<p>This post has no featured image.</p>',
            excerpt='Test excerpt without image',
            status='published'
        )
        
        schema = SchemaService.generate_article_schema(post, self.request)
        
        # Verify schema is still generated correctly
        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'Article')
        self.assertEqual(schema['headline'], post.title)
        
        # Image field should either be missing or empty
        if 'image' in schema:
            self.assertEqual(schema['image'], [])
        
        # Other required fields should still be present
        self.assertIn('author', schema)
        self.assertIn('publisher', schema)
        self.assertIn('datePublished', schema)
        self.assertIn('dateModified', schema)

    def test_schema_generation_with_no_categories_or_tags(self):
        """Test schema generation with posts that have no categories or tags."""
        # Create post without categories or tags
        post = Post.objects.create(
            title='Post Without Categories or Tags',
            slug='post-without-categories-tags',
            author=self.user,
            content='<p>This post has no categories or tags.</p>',
            excerpt='Test excerpt without categories or tags',
            status='published'
        )
        
        schema = SchemaService.generate_article_schema(post, self.request)
        
        # Verify schema is still generated correctly
        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'Article')
        self.assertEqual(schema['headline'], post.title)
        
        # Categories and tags fields should be missing or empty
        if 'articleSection' in schema:
            self.assertEqual(schema['articleSection'], [])
        if 'keywords' in schema:
            self.assertEqual(schema['keywords'], [])
        
        # Required fields should still be present
        self.assertIn('author', schema)
        self.assertIn('publisher', schema)
        self.assertIn('datePublished', schema)

    def test_schema_generation_with_guest_author_no_profile(self):
        """Test schema generation with guest authors who have no author profile."""
        # Create guest user without author profile
        guest_user = User.objects.create_user(
            username='guestauthor',
            email='guest@example.com'
        )
        
        post = Post.objects.create(
            title='Post by Guest Author',
            slug='post-by-guest-author',
            author=guest_user,
            content='<p>This post is by a guest author with no profile.</p>',
            excerpt='Guest author post',
            status='published'
        )
        
        schema = SchemaService.generate_article_schema(post, self.request)
        
        # Verify schema is generated with minimal author info
        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'Article')
        
        # Author should have minimal information
        author = schema['author']
        self.assertEqual(author['@type'], 'Person')
        self.assertEqual(author['name'], 'guestauthor')  # Should use username
        
        # Should not have social media links or bio
        self.assertNotIn('sameAs', author)
        self.assertNotIn('description', author)
        self.assertNotIn('url', author)

    def test_schema_generation_with_guest_author_profile(self):
        """Test schema generation with guest authors who have author profiles."""
        # Create guest user with author profile
        guest_user = User.objects.create_user(
            username='guestwriter',
            email='guestwriter@example.com',
            first_name='Guest',
            last_name='Writer'
        )
        
        # Create guest author profile
        guest_profile = AuthorProfile.objects.create(
            user=guest_user,
            bio='I am a guest writer contributing to this blog.',
            website='https://guestwriter.com',
            is_guest_author=True,
            guest_author_email='guest@company.com',
            guest_author_company='Guest Company Inc.'
        )
        
        post = Post.objects.create(
            title='Post by Guest Writer with Profile',
            slug='post-by-guest-writer-profile',
            author=guest_user,
            content='<p>This post is by a guest writer with a profile.</p>',
            excerpt='Guest writer post with profile',
            status='published'
        )
        
        schema = SchemaService.generate_article_schema(post, self.request)
        
        # Verify schema includes guest author information
        author = schema['author']
        self.assertEqual(author['@type'], 'Person')
        self.assertEqual(author['name'], 'Guest Writer')
        self.assertEqual(author['description'], guest_profile.bio)
        
        # Should include website in sameAs
        self.assertIn('sameAs', author)
        self.assertIn('https://guestwriter.com', author['sameAs'])

    def test_schema_generation_with_special_characters_in_content(self):
        """Test schema generation with various special characters in content."""
        # Create post with special characters
        special_content = '''
        <p>This post contains "quotes", 'apostrophes', and special characters: àáâãäåæçèéêë</p>
        <p>It also has symbols: @#$%^&*()_+-=[]{}|;:,.<>?/~`</p>
        <p>Unicode characters: 中文, العربية, русский, 日本語</p>
        <p>HTML entities: &lt;script&gt;alert('test');&lt;/script&gt;</p>
        '''
        
        post = Post.objects.create(
            title='Post with "Special" Characters & Symbols',
            slug='post-with-special-characters',
            author=self.user,
            content=special_content,
            excerpt='Post with special characters & symbols',
            status='published'
        )
        
        schema = SchemaService.generate_article_schema(post, self.request)
        
        # Verify schema is generated correctly
        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'Article')
        
        # Verify special characters are handled properly
        self.assertIn('Special', schema['headline'])
        self.assertIn('Characters', schema['headline'])
        
        # Verify description handles special characters
        if 'description' in schema:
            description = schema['description']
            self.assertIsInstance(description, str)
            # Should not contain HTML tags
            self.assertNotIn('<p>', description)
            self.assertNotIn('</p>', description)
        
        # Verify schema can be serialized to JSON
        try:
            json_str = json.dumps(schema, ensure_ascii=False)
            # Verify we can parse it back
            parsed = json.loads(json_str)
            self.assertIsInstance(parsed, dict)
        except (TypeError, ValueError) as e:
            self.fail(f"Schema with special characters failed JSON serialization: {e}")

    def test_schema_generation_with_empty_content_fields(self):
        """Test schema generation with empty or None content fields."""
        # Create post with minimal content
        post = Post.objects.create(
            title='Post with Empty Fields',
            slug='post-with-empty-fields',
            author=self.user,
            content='',  # Empty content
            excerpt='',  # Empty excerpt
            status='published'
        )
        
        schema = SchemaService.generate_article_schema(post, self.request)
        
        # Verify schema is still generated
        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'Article')
        self.assertEqual(schema['headline'], post.title)
        
        # Description should be handled gracefully
        if 'description' in schema:
            self.assertIsInstance(schema['description'], str)
        
        # Word count should be 0 or minimal
        if 'wordCount' in schema:
            self.assertEqual(schema['wordCount'], 0)
        
        # Reading time should be minimal
        if 'timeRequired' in schema:
            self.assertIn('PT', schema['timeRequired'])

    def test_schema_generation_with_malformed_html_content(self):
        """Test schema generation with malformed HTML content."""
        # Create post with malformed HTML
        malformed_content = '''
        <p>This is a paragraph with <strong>unclosed tag
        <div>Nested divs without proper closing</div>
        <img src="test.jpg" alt="Image without closing tag"
        <script>alert('malicious script');</script>
        <p>Another paragraph with &invalid; entity</p>
        '''
        
        post = Post.objects.create(
            title='Post with Malformed HTML',
            slug='post-with-malformed-html',
            author=self.user,
            content=malformed_content,
            excerpt='Post with malformed HTML content',
            status='published'
        )
        
        schema = SchemaService.generate_article_schema(post, self.request)
        
        # Verify schema is generated despite malformed HTML
        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'Article')
        
        # Description should be cleaned of HTML tags
        if 'description' in schema:
            description = schema['description']
            self.assertNotIn('<script>', description)
            self.assertNotIn('<div>', description)
            self.assertNotIn('<img', description)
        
        # Word count should be calculated from cleaned text
        if 'wordCount' in schema:
            self.assertGreater(schema['wordCount'], 0)

    def test_schema_generation_with_very_long_content(self):
        """Test schema generation with extremely long content."""
        # Create post with very long content
        long_paragraph = "This is a very long paragraph. " * 1000  # 6000+ words
        long_content = f'<p>{long_paragraph}</p>' * 10  # Even longer
        
        post = Post.objects.create(
            title='Post with Very Long Content',
            slug='post-with-very-long-content',
            author=self.user,
            content=long_content,
            excerpt='Post with extremely long content for testing',
            status='published'
        )
        
        schema = SchemaService.generate_article_schema(post, self.request)
        
        # Verify schema is generated
        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'Article')
        
        # Word count should be calculated correctly
        if 'wordCount' in schema:
            self.assertGreater(schema['wordCount'], 50000)  # Should be very high
        
        # Reading time should be reasonable
        if 'timeRequired' in schema:
            self.assertIn('PT', schema['timeRequired'])
            # Extract minutes for validation
            time_str = schema['timeRequired']
            if 'H' in time_str:
                # Format like PT2H30M
                self.assertTrue(time_str.startswith('PT'))
            else:
                # Format like PT150M
                minutes_str = time_str[2:-1]  # Remove PT and M
                minutes = int(minutes_str)
                self.assertGreater(minutes, 100)  # Should be substantial reading time

    def test_schema_generation_with_missing_author_name_fields(self):
        """Test schema generation when author has no first/last name."""
        # Create user with only username
        user_no_name = User.objects.create_user(
            username='usernameonly',
            email='usernameonly@example.com'
            # No first_name or last_name
        )
        
        post = Post.objects.create(
            title='Post by User with No Name Fields',
            slug='post-by-user-no-name',
            author=user_no_name,
            content='<p>This post is by a user with only username.</p>',
            status='published'
        )
        
        schema = SchemaService.generate_article_schema(post, self.request)
        
        # Verify author name falls back to username
        author = schema['author']
        self.assertEqual(author['@type'], 'Person')
        self.assertEqual(author['name'], 'usernameonly')

    def test_schema_generation_with_partial_author_name(self):
        """Test schema generation when author has only first name or last name."""
        # Test with only first name
        user_first_only = User.objects.create_user(
            username='firstnameonly',
            email='firstnameonly@example.com',
            first_name='FirstOnly'
        )
        
        post1 = Post.objects.create(
            title='Post by User with First Name Only',
            slug='post-by-user-first-name-only',
            author=user_first_only,
            content='<p>This post is by a user with only first name.</p>',
            status='published'
        )
        
        schema1 = SchemaService.generate_article_schema(post1, self.request)
        author1 = schema1['author']
        self.assertEqual(author1['name'], 'FirstOnly')
        
        # Test with only last name
        user_last_only = User.objects.create_user(
            username='lastnameonly',
            email='lastnameonly@example.com',
            last_name='LastOnly'
        )
        
        post2 = Post.objects.create(
            title='Post by User with Last Name Only',
            slug='post-by-user-last-name-only',
            author=user_last_only,
            content='<p>This post is by a user with only last name.</p>',
            status='published'
        )
        
        schema2 = SchemaService.generate_article_schema(post2, self.request)
        author2 = schema2['author']
        # Should fall back to username when only last name is present
        self.assertEqual(author2['name'], 'lastnameonly')

    def test_schema_generation_with_invalid_social_media_formats(self):
        """Test schema generation with various social media username formats."""
        # Create user with author profile having various social media formats
        user = User.objects.create_user(
            username='socialuser',
            email='socialuser@example.com',
            first_name='Social',
            last_name='User'
        )
        
        profile = AuthorProfile.objects.create(
            user=user,
            bio='User with various social media formats',
            twitter='@twitteruser',  # With @ prefix
            instagram='instagramuser',  # Without @ prefix
            github='',  # Empty string
            linkedin='not-a-valid-url',  # Invalid URL format
            website='http://example.com'  # Valid website
        )
        
        post = Post.objects.create(
            title='Post by User with Various Social Media Formats',
            slug='post-social-media-formats',
            author=user,
            content='<p>Testing social media format handling.</p>',
            status='published'
        )
        
        schema = SchemaService.generate_article_schema(post, self.request)
        
        # Verify author schema handles various formats
        author = schema['author']
        self.assertEqual(author['@type'], 'Person')
        self.assertEqual(author['name'], 'Social User')
        
        if 'sameAs' in author:
            same_as = author['sameAs']
            # Should handle @ prefix correctly
            twitter_urls = [url for url in same_as if 'twitter.com' in url]
            if twitter_urls:
                self.assertIn('https://twitter.com/twitteruser', twitter_urls[0])
            
            # Should include valid website
            self.assertIn('http://example.com', same_as)
            
            # Should handle invalid LinkedIn URL gracefully
            linkedin_urls = [url for url in same_as if 'not-a-valid-url' in url]
            if linkedin_urls:
                # Should include as-is if it's the provided value
                self.assertIn('not-a-valid-url', linkedin_urls[0])

    def test_schema_generation_with_database_errors(self):
        """Test schema generation when database queries fail."""
        # Create a post
        post = Post.objects.create(
            title='Post for Database Error Testing',
            slug='post-database-error-testing',
            author=self.user,
            content='<p>Testing database error handling.</p>',
            status='published'
        )
        
        # Mock database errors for categories and tags
        with patch.object(post.categories, 'values_list', side_effect=Exception("Database error")):
            with patch.object(post.tags, 'values_list', side_effect=Exception("Database error")):
                schema = SchemaService.generate_article_schema(post, self.request)
                
                # Schema should still be generated
                self.assertEqual(schema['@context'], 'https://schema.org')
                self.assertEqual(schema['@type'], 'Article')
                
                # Categories and tags should be missing or empty due to errors
                if 'articleSection' in schema:
                    self.assertEqual(schema['articleSection'], [])
                if 'keywords' in schema:
                    self.assertEqual(schema['keywords'], [])

    def test_schema_generation_with_media_item_errors(self):
        """Test schema generation when media item queries fail."""
        post = Post.objects.create(
            title='Post for Media Error Testing',
            slug='post-media-error-testing',
            author=self.user,
            content='<p>Testing media error handling.</p>',
            status='published'
        )
        
        # Mock media items query to raise exception
        with patch.object(post.media_items, 'filter', side_effect=Exception("Media query error")):
            schema = SchemaService.generate_article_schema(post, self.request)
            
            # Schema should still be generated
            self.assertEqual(schema['@context'], 'https://schema.org')
            self.assertEqual(schema['@type'], 'Article')
            
            # Images should be empty or missing due to error
            if 'image' in schema:
                # Should not include media item images due to error
                self.assertIsInstance(schema['image'], list)

    def test_schema_generation_with_url_generation_errors(self):
        """Test schema generation when URL generation fails."""
        # Create a mock post that raises exception on get_absolute_url
        mock_post = Mock()
        mock_post.id = 1
        mock_post.title = "Test Post with URL Error"
        mock_post.slug = "test-post-url-error"
        mock_post.content = "Test content"
        mock_post.excerpt = "Test excerpt"
        mock_post.author = self.user
        mock_post.created_at = datetime.now(timezone.utc)
        mock_post.updated_at = datetime.now(timezone.utc)
        mock_post.get_absolute_url.side_effect = Exception("URL generation error")
        mock_post.get_reading_time.return_value = 5
        mock_post.categories.values_list.return_value = []
        mock_post.tags.values_list.return_value = []
        mock_post.media_items.filter.return_value = []
        mock_post.featured_image = None
        mock_post.social_image = None
        
        # Should fall back to minimal schema
        schema = SchemaService.generate_article_schema(mock_post, self.request)
        
        # Should return minimal schema or empty dict
        if schema:
            self.assertIsInstance(schema, dict)
            if '@type' in schema:
                self.assertEqual(schema['@type'], 'Article')

    def test_template_tag_error_handling(self):
        """Test template tag error handling with problematic posts."""
        # Create a mock post that will cause template tag errors
        mock_post = Mock()
        mock_post.id = 999
        mock_post.title = None  # This should cause issues
        mock_post.updated_at = datetime.now(timezone.utc)
        
        # Test render_article_schema inclusion tag
        context = {'request': self.request, 'post': mock_post}
        result = render_article_schema(context, mock_post)
        
        # Should return error state gracefully
        self.assertIsInstance(result, dict)
        self.assertIn('schema_json', result)
        self.assertIn('is_valid', result)
        self.assertFalse(result['is_valid'])
        
        # Test get_article_schema_json simple tag
        json_result = get_article_schema_json(context, mock_post)
        
        # Should return empty JSON object on error
        self.assertEqual(str(json_result), '{}')

    def test_schema_validation_with_edge_case_data(self):
        """Test schema validation with various edge case data structures."""
        # Test with None
        self.assertFalse(SchemaService.validate_schema(None))
        
        # Test with empty dict
        self.assertFalse(SchemaService.validate_schema({}))
        
        # Test with string instead of dict
        self.assertFalse(SchemaService.validate_schema("not a dict"))
        
        # Test with list instead of dict
        self.assertFalse(SchemaService.validate_schema([]))
        
        # Test with dict missing required fields
        incomplete_schema = {
            "@context": "https://schema.org",
            "@type": "Article"
            # Missing required fields
        }
        self.assertFalse(SchemaService.validate_schema(incomplete_schema))
        
        # Test with invalid @context
        invalid_context_schema = {
            "@context": "https://invalid-context.org",
            "@type": "Article",
            "headline": "Test",
            "author": {"@type": "Person", "name": "Test"},
            "publisher": {"@type": "Organization", "name": "Test"},
            "datePublished": "2024-01-01"
        }
        self.assertFalse(SchemaService.validate_schema(invalid_context_schema))

    def test_schema_generation_performance_with_large_datasets(self):
        """Test schema generation performance with posts having many categories/tags."""
        # Create many categories and tags
        categories = []
        tags = []
        
        for i in range(50):  # Create 50 categories
            category = Category.objects.create(
                name=f'Category {i}',
                slug=f'category-{i}'
            )
            categories.append(category)
        
        for i in range(100):  # Create 100 tags
            tag = Tag.objects.create(
                name=f'Tag {i}',
                slug=f'tag-{i}'
            )
            tags.append(tag)
        
        # Create post with many categories and tags
        post = Post.objects.create(
            title='Post with Many Categories and Tags',
            slug='post-many-categories-tags',
            author=self.user,
            content='<p>This post has many categories and tags.</p>',
            status='published'
        )
        
        # Add all categories and tags
        post.categories.set(categories)
        post.tags.set(tags)
        
        # Generate schema and measure basic performance
        import time
        start_time = time.time()
        schema = SchemaService.generate_article_schema(post, self.request)
        end_time = time.time()
        
        # Should complete in reasonable time (less than 1 second)
        execution_time = end_time - start_time
        self.assertLess(execution_time, 1.0, f"Schema generation took too long: {execution_time}s")
        
        # Verify all categories and tags are included
        self.assertEqual(len(schema['articleSection']), 50)
        self.assertEqual(len(schema['keywords']), 100)

    def test_schema_generation_with_unicode_and_emoji_content(self):
        """Test schema generation with Unicode characters and emojis."""
        # Create post with Unicode and emoji content
        unicode_content = '''
        <p>This post contains Unicode: 中文, العربية, русский, 日本語, हिन्दी</p>
        <p>And emojis: 🚀 🎉 💻 🌟 ✨ 🔥 💡 🎯</p>
        <p>Mathematical symbols: ∑ ∏ ∫ ∂ ∇ ∞ ≈ ≠ ≤ ≥</p>
        <p>Currency symbols: $ € £ ¥ ₹ ₿</p>
        '''
        
        post = Post.objects.create(
            title='Post with Unicode 🌍 and Emojis 🎉',
            slug='post-unicode-emojis',
            author=self.user,
            content=unicode_content,
            excerpt='Testing Unicode and emoji handling 🚀',
            status='published'
        )
        
        schema = SchemaService.generate_article_schema(post, self.request)
        
        # Verify schema is generated correctly
        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'Article')
        
        # Verify Unicode characters are preserved in headline
        self.assertIn('🌍', schema['headline'])
        self.assertIn('🎉', schema['headline'])
        
        # Verify description handles Unicode
        if 'description' in schema:
            description = schema['description']
            self.assertIn('🚀', description)
        
        # Verify schema can be serialized to JSON with Unicode
        try:
            json_str = json.dumps(schema, ensure_ascii=False)
            parsed = json.loads(json_str)
            self.assertIsInstance(parsed, dict)
            self.assertIn('🌍', parsed['headline'])
        except (TypeError, ValueError) as e:
            self.fail(f"Schema with Unicode failed JSON serialization: {e}")

    def test_graceful_handling_of_all_edge_cases_combined(self):
        """Test graceful handling when multiple edge cases occur together."""
        # Create user with minimal information
        minimal_user = User.objects.create_user(
            username='minimal',
            email='minimal@example.com'
            # No first_name, last_name
        )
        
        # Create post with multiple edge cases
        post = Post.objects.create(
            title='',  # Empty title - edge case
            slug='edge-case-combination',
            author=minimal_user,  # No author profile
            content='',  # Empty content
            excerpt='',  # Empty excerpt
            status='published'
            # No featured_image, no categories, no tags
        )
        
        # Generate schema despite all edge cases
        schema = SchemaService.generate_article_schema(post, self.request)
        
        # Should still generate a valid schema structure
        self.assertIsInstance(schema, dict)
        
        if schema:  # If not empty dict
            # Should have basic required structure
            if '@context' in schema:
                self.assertEqual(schema['@context'], 'https://schema.org')
            if '@type' in schema:
                self.assertEqual(schema['@type'], 'Article')
            
            # Author should use username as fallback
            if 'author' in schema:
                author = schema['author']
                self.assertEqual(author['@type'], 'Person')
                self.assertEqual(author['name'], 'minimal')
            
            # Should handle empty content gracefully
            if 'wordCount' in schema:
                self.assertEqual(schema['wordCount'], 0)
        
        # Schema validation should handle edge cases
        is_valid = SchemaService.validate_schema(schema)
        # May be invalid due to missing required fields, but shouldn't crash
        self.assertIsInstance(is_valid, bool)

    def tearDown(self):
        """Clean up test data."""
        # Clean up any uploaded files
        import os
        from django.conf import settings
        
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if media_root and os.path.exists(media_root):
            # Clean up test images if any were created
            for root, dirs, files in os.walk(media_root):
                for file in files:
                    if file.startswith('test_') or 'test' in file.lower():
                        try:
                            os.remove(os.path.join(root, file))
                        except OSError:
                            pass  # Ignore cleanup errors