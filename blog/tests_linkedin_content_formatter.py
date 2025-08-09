"""
Unit tests for LinkedIn content formatting utilities.
"""

import os
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import Mock, patch
from blog.models import Post, Tag, Category, MediaItem
from blog.services.linkedin_content_formatter import (
    LinkedInContentFormatter,
    format_blog_post_for_linkedin,
    get_blog_post_hashtags,
    get_blog_post_featured_image,
    validate_linkedin_content
)


class LinkedInContentFormatterTest(TestCase):
    """Test cases for LinkedInContentFormatter class."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test tags
        self.tag1 = Tag.objects.create(name='Python', slug='python')
        self.tag2 = Tag.objects.create(name='Django Framework', slug='django-framework')
        self.tag3 = Tag.objects.create(name='Web Development', slug='web-development')
        self.tag4 = Tag.objects.create(name='API Design', slug='api-design')
        self.tag5 = Tag.objects.create(name='Testing', slug='testing')
        self.tag6 = Tag.objects.create(name='DevOps', slug='devops')
        
        # Create test category
        self.category = Category.objects.create(name='Technology', slug='technology')
        
        # Create test post
        self.post = Post.objects.create(
            title='Test Blog Post About Django Development',
            slug='test-blog-post',
            author=self.user,
            content='<p>This is a test blog post content with <strong>HTML tags</strong>. It contains multiple paragraphs.</p><p>This is the second paragraph with more content to test excerpt extraction.</p>',
            excerpt='This is a test excerpt for the blog post.',
            status='published'
        )
        self.post.tags.add(self.tag1, self.tag2, self.tag3)
        self.post.categories.add(self.category)
        
        # Create formatter instance
        self.formatter = LinkedInContentFormatter(base_url='https://example.com')
    
    def test_format_title(self):
        """Test title formatting and truncation."""
        # Normal title
        title = self.formatter._format_title('Test Blog Post')
        self.assertEqual(title, 'Test Blog Post')
        
        # Long title that needs truncation
        long_title = 'A' * 250
        formatted_title = self.formatter._format_title(long_title)
        self.assertLessEqual(len(formatted_title), 200)
        self.assertTrue(formatted_title.endswith('...'))
        
        # Empty title
        empty_title = self.formatter._format_title('')
        self.assertEqual(empty_title, '')
        
        # Title with extra whitespace
        whitespace_title = self.formatter._format_title('  Test Title  ')
        self.assertEqual(whitespace_title, 'Test Title')
    
    def test_format_excerpt(self):
        """Test excerpt formatting and truncation."""
        # Normal excerpt
        excerpt = self.formatter._format_excerpt('This is a test excerpt.')
        self.assertEqual(excerpt, 'This is a test excerpt.')
        
        # Excerpt with HTML tags
        html_excerpt = self.formatter._format_excerpt('<p>This is <strong>HTML</strong> excerpt.</p>')
        self.assertEqual(html_excerpt, 'This is HTML excerpt.')
        
        # Long excerpt that needs truncation
        long_excerpt = 'A' * 350
        formatted_excerpt = self.formatter._format_excerpt(long_excerpt)
        self.assertLessEqual(len(formatted_excerpt), 300)
        self.assertTrue(formatted_excerpt.endswith('...'))
        
        # Excerpt with extra whitespace
        whitespace_excerpt = self.formatter._format_excerpt('This  has   extra    spaces.')
        self.assertEqual(whitespace_excerpt, 'This has extra spaces.')
    
    def test_extract_excerpt_from_content(self):
        """Test excerpt extraction from blog content."""
        # Content with multiple paragraphs
        content = '<p>First paragraph content.</p><p>Second paragraph content.</p>'
        excerpt = self.formatter._extract_excerpt_from_content(content)
        self.assertEqual(excerpt, 'First paragraph content.')
        
        # Content with very long first paragraph
        long_content = '<p>' + 'A' * 400 + '</p>'
        excerpt = self.formatter._extract_excerpt_from_content(long_content)
        self.assertLessEqual(len(excerpt), 300)
        
        # Content with sentences
        sentence_content = 'First sentence. Second sentence. Third sentence.'
        excerpt = self.formatter._extract_excerpt_from_content(sentence_content)
        self.assertIn('First sentence.', excerpt)
        
        # Empty content
        empty_excerpt = self.formatter._extract_excerpt_from_content('')
        self.assertEqual(empty_excerpt, '')
    
    def test_generate_hashtags(self):
        """Test hashtag generation from blog post tags."""
        hashtags = self.formatter._generate_hashtags(self.post)
        
        # Should contain hashtags for the assigned tags
        self.assertIn('#python', hashtags)
        self.assertIn('#djangoFramework', hashtags)
        self.assertIn('#webDevelopment', hashtags)
        
        # Should not exceed maximum hashtags
        hashtag_count = len(hashtags.split())
        self.assertLessEqual(hashtag_count, self.formatter.MAX_HASHTAGS)
    
    def test_format_hashtag(self):
        """Test individual hashtag formatting."""
        # Simple tag
        hashtag = self.formatter._format_hashtag('Python')
        self.assertEqual(hashtag, '#python')
        
        # Multi-word tag
        hashtag = self.formatter._format_hashtag('Django Framework')
        self.assertEqual(hashtag, '#djangoFramework')
        
        # Tag with special characters
        hashtag = self.formatter._format_hashtag('API-Design')
        self.assertEqual(hashtag, '#apiDesign')
        
        # Tag with numbers
        hashtag = self.formatter._format_hashtag('Python3')
        self.assertEqual(hashtag, '#python3')
        
        # Invalid tag (only numbers)
        hashtag = self.formatter._format_hashtag('123')
        self.assertEqual(hashtag, '')
        
        # Empty tag
        hashtag = self.formatter._format_hashtag('')
        self.assertEqual(hashtag, '')
    
    @patch('blog.models.Post.get_absolute_url')
    def test_get_post_url(self, mock_get_absolute_url):
        """Test blog post URL generation."""
        mock_get_absolute_url.return_value = '/blog/test-post/'
        
        url = self.formatter._get_post_url(self.post)
        self.assertEqual(url, 'https://example.com/blog/test-post/')
    
    def test_format_post_content_with_excerpt(self):
        """Test full post content formatting with excerpt."""
        content = self.formatter.format_post_content(self.post, include_excerpt=True)
        
        # Should contain title
        self.assertIn(self.post.title, content)
        
        # Should contain excerpt
        self.assertIn(self.post.excerpt, content)
        
        # Should contain URL
        self.assertIn('https://example.com', content)
        
        # Should contain hashtags
        self.assertIn('#python', content)
        
        # Should not exceed character limit
        self.assertLessEqual(len(content), self.formatter.MAX_POST_LENGTH)
    
    def test_format_post_content_without_excerpt(self):
        """Test post content formatting without excerpt."""
        content = self.formatter.format_post_content(self.post, include_excerpt=False)
        
        # Should contain title
        self.assertIn(self.post.title, content)
        
        # Should not contain excerpt
        self.assertNotIn(self.post.excerpt, content)
        
        # Should contain URL
        self.assertIn('https://example.com', content)
        
        # Should contain hashtags
        self.assertIn('#python', content)
    
    def test_format_post_content_no_excerpt_field(self):
        """Test formatting when post has no excerpt field."""
        # Create post without excerpt
        post_no_excerpt = Post.objects.create(
            title='Post Without Excerpt',
            slug='post-without-excerpt',
            author=self.user,
            content='<p>This is content without excerpt.</p>',
            status='published'
        )
        
        content = self.formatter.format_post_content(post_no_excerpt, include_excerpt=True)
        
        # Should extract excerpt from content
        self.assertIn('This is content without excerpt.', content)
    
    def test_apply_character_limit(self):
        """Test character limit application with intelligent truncation."""
        # Create very long content
        long_title = 'A' * 100
        long_excerpt = 'B' * 200
        url = 'https://example.com/blog/test/'
        hashtags = '\n\n#tag1 #tag2 #tag3'
        
        long_content = f"{long_title}\n\n{long_excerpt}\n\n{url}{hashtags}"
        
        # Make it exceed the limit
        very_long_content = long_content + 'C' * 3000
        
        truncated = self.formatter._apply_character_limit(very_long_content, url, hashtags)
        
        # Should be within limit
        self.assertLessEqual(len(truncated), self.formatter.MAX_POST_LENGTH)
        
        # Should preserve URL
        self.assertIn(url, truncated)
    
    def test_get_featured_image_url_with_featured_image(self):
        """Test featured image URL extraction with featured_image field."""
        # Create a mock image file
        image_content = b'fake image content'
        image_file = SimpleUploadedFile(
            name='test_image.jpg',
            content=image_content,
            content_type='image/jpeg'
        )
        
        # Update post with featured image
        self.post.featured_image = image_file
        self.post.save()
        
        image_url = self.formatter.get_featured_image_url(self.post)
        
        # Should return full URL
        self.assertIsNotNone(image_url)
        self.assertTrue(image_url.startswith('https://example.com'))
        self.assertTrue(image_url.endswith('.jpg'))
        
        # Clean up
        if self.post.featured_image:
            self.post.featured_image.delete()
    
    def test_get_featured_image_url_no_image(self):
        """Test featured image URL extraction when no image exists."""
        image_url = self.formatter.get_featured_image_url(self.post)
        self.assertIsNone(image_url)
    
    def test_validate_content_valid(self):
        """Test content validation with valid content."""
        valid_content = "Test Title\n\nTest content\n\nhttps://example.com/blog/test/\n\n#python #django"
        
        is_valid, errors = self.formatter.validate_content(valid_content)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_content_too_long(self):
        """Test content validation with content that's too long."""
        long_content = 'A' * 3500
        
        is_valid, errors = self.formatter.validate_content(long_content)
        
        self.assertFalse(is_valid)
        self.assertIn('exceeds LinkedIn limit', errors[0])
    
    def test_validate_content_empty(self):
        """Test content validation with empty content."""
        is_valid, errors = self.formatter.validate_content('')
        
        self.assertFalse(is_valid)
        self.assertIn('cannot be empty', errors[0])
    
    def test_validate_content_no_url(self):
        """Test content validation with no URL."""
        content_no_url = "Test Title\n\nTest content\n\n#python"
        
        is_valid, errors = self.formatter.validate_content(content_no_url)
        
        self.assertFalse(is_valid)
        self.assertIn('should include a URL', errors[0])
    
    def test_validate_content_too_many_hashtags(self):
        """Test content validation with too many hashtags."""
        content_many_hashtags = "Test\n\nhttps://example.com\n\n#tag1 #tag2 #tag3 #tag4 #tag5 #tag6 #tag7"
        
        is_valid, errors = self.formatter.validate_content(content_many_hashtags)
        
        self.assertFalse(is_valid)
        self.assertIn('Too many hashtags', errors[0])
    
    def test_format_for_preview(self):
        """Test preview formatting functionality."""
        preview = self.formatter.format_for_preview(self.post)
        
        # Should contain all expected keys
        expected_keys = [
            'full_content', 'title', 'excerpt', 'url', 'hashtags',
            'featured_image_url', 'character_count', 'is_valid', 'validation_errors'
        ]
        
        for key in expected_keys:
            self.assertIn(key, preview)
        
        # Should have valid content
        self.assertTrue(preview['is_valid'])
        self.assertEqual(len(preview['validation_errors']), 0)
        
        # Should have correct character count
        self.assertEqual(preview['character_count'], len(preview['full_content']))


class ConvenienceFunctionsTest(TestCase):
    """Test cases for convenience functions."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.tag = Tag.objects.create(name='Python', slug='python')
        
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='Test content',
            excerpt='Test excerpt',
            status='published'
        )
        self.post.tags.add(self.tag)
    
    def test_format_blog_post_for_linkedin(self):
        """Test convenience function for formatting blog post."""
        content = format_blog_post_for_linkedin(self.post)
        
        self.assertIn(self.post.title, content)
        self.assertIn(self.post.excerpt, content)
        self.assertIn('#python', content)
    
    def test_get_blog_post_hashtags(self):
        """Test convenience function for getting hashtags."""
        hashtags = get_blog_post_hashtags(self.post)
        
        self.assertIn('#python', hashtags)
    
    def test_get_blog_post_featured_image(self):
        """Test convenience function for getting featured image."""
        image_url = get_blog_post_featured_image(self.post)
        
        # Should return None when no image
        self.assertIsNone(image_url)
    
    def test_validate_linkedin_content(self):
        """Test convenience function for content validation."""
        valid_content = "Test\n\nhttps://example.com\n\n#python"
        
        is_valid, errors = validate_linkedin_content(valid_content)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)


class EdgeCasesTest(TestCase):
    """Test edge cases and error conditions."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.formatter = LinkedInContentFormatter()
    
    def test_post_with_no_tags(self):
        """Test formatting post with no tags."""
        post = Post.objects.create(
            title='Post Without Tags',
            slug='post-without-tags',
            author=self.user,
            content='Content without tags',
            status='published'
        )
        
        content = self.formatter.format_post_content(post)
        
        # Should not contain hashtags
        self.assertNotIn('#', content)
        
        # Should still be valid
        is_valid, errors = self.formatter.validate_content(content)
        self.assertTrue(is_valid)
    
    def test_post_with_special_characters_in_title(self):
        """Test formatting post with special characters in title."""
        post = Post.objects.create(
            title='Post with "Quotes" & Special Characters!',
            slug='post-special-chars',
            author=self.user,
            content='Content with special chars',
            status='published'
        )
        
        content = self.formatter.format_post_content(post)
        
        # Should preserve special characters in title
        self.assertIn('Post with "Quotes" & Special Characters!', content)
    
    def test_post_with_very_short_content(self):
        """Test formatting post with very short content."""
        post = Post.objects.create(
            title='Short',
            slug='short',
            author=self.user,
            content='Hi',
            excerpt='Hi',
            status='published'
        )
        
        content = self.formatter.format_post_content(post)
        
        # Should still be valid
        is_valid, errors = self.formatter.validate_content(content)
        self.assertTrue(is_valid)
    
    @override_settings(ALLOWED_HOSTS=['testserver'])
    def test_base_url_fallback(self):
        """Test base URL fallback when sites framework is not available."""
        formatter = LinkedInContentFormatter()
        
        # Should use fallback URL
        self.assertTrue(formatter.base_url.startswith('https://'))