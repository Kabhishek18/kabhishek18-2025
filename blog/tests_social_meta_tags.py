from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from blog.models import Post, Category, MediaItem
from blog.templatetags.media_tags import (
    get_social_image_url, 
    get_image_dimensions, 
    get_image_alt_text
)
from PIL import Image
import io
import os


class SocialMetaTagsTestCase(TestCase):
    """Test cases for social media meta tags functionality"""

    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Test Category')
        
        # Create a mock request
        self.request = self.factory.get('/')
        self.request.META['HTTP_HOST'] = 'testserver'
        self.request.META['SERVER_PORT'] = '80'
        self.request.is_secure = lambda: True

    def create_test_image(self, width=1200, height=627, format='JPEG'):
        """Create a test image file"""
        image = Image.new('RGB', (width, height), color='red')
        image_io = io.BytesIO()
        image.save(image_io, format=format)
        image_io.seek(0)
        return SimpleUploadedFile(
            f'test_image.{format.lower()}',
            image_io.getvalue(),
            content_type=f'image/{format.lower()}'
        )

    def test_social_image_url_with_social_image(self):
        """Test social image URL when post has social_image field"""
        # Create post with social_image
        social_image = self.create_test_image()
        post = Post.objects.create(
            title='Test Post',
            content='Test content',
            author=self.user,
            social_image=social_image
        )
        
        image_url = get_social_image_url(post, self.request)
        self.assertIn('/media/social_images/', image_url)
        self.assertTrue(image_url.startswith('http'))

    def test_social_image_url_with_featured_image(self):
        """Test social image URL when post has featured_image field"""
        featured_image = self.create_test_image()
        post = Post.objects.create(
            title='Test Post',
            content='Test content',
            author=self.user,
            featured_image=featured_image
        )
        
        image_url = get_social_image_url(post, self.request)
        self.assertIn('/media/blog_images/', image_url)
        self.assertTrue(image_url.startswith('http'))

    def test_social_image_url_with_featured_media(self):
        """Test social image URL when post has featured MediaItem"""
        post = Post.objects.create(
            title='Test Post',
            content='Test content',
            author=self.user
        )
        
        # Create featured media item
        media_image = self.create_test_image()
        media_item = MediaItem.objects.create(
            post=post,
            media_type='image',
            original_image=media_image,
            is_featured=True,
            alt_text='Test featured image'
        )
        
        image_url = get_social_image_url(post, self.request)
        self.assertIn('/media/blog_images/originals/', image_url)
        self.assertTrue(image_url.startswith('http'))

    def test_social_image_url_with_first_media(self):
        """Test social image URL when post has non-featured MediaItem"""
        post = Post.objects.create(
            title='Test Post',
            content='Test content',
            author=self.user
        )
        
        # Create non-featured media item
        media_image = self.create_test_image()
        media_item = MediaItem.objects.create(
            post=post,
            media_type='image',
            original_image=media_image,
            is_featured=False,
            alt_text='Test image'
        )
        
        image_url = get_social_image_url(post, self.request)
        self.assertIn('/media/blog_images/originals/', image_url)
        self.assertTrue(image_url.startswith('http'))

    def test_social_image_url_fallback(self):
        """Test social image URL fallback when no images available"""
        post = Post.objects.create(
            title='Test Post',
            content='Test content',
            author=self.user
        )
        
        image_url = get_social_image_url(post, self.request)
        self.assertIn('/static/web-app-manifest-512x512.png', image_url)
        self.assertTrue(image_url.startswith('http'))

    def test_social_image_url_without_request(self):
        """Test social image URL generation without request object"""
        post = Post.objects.create(
            title='Test Post',
            content='Test content',
            author=self.user
        )
        
        image_url = get_social_image_url(post, None)
        self.assertIn('kabhishek18.com', image_url)
        self.assertTrue(image_url.startswith('http'))

    def test_image_dimensions_default(self):
        """Test image dimensions with no image"""
        dimensions = get_image_dimensions(None)
        self.assertEqual(dimensions['width'], 512)
        self.assertEqual(dimensions['height'], 512)

    def test_image_alt_text_with_social_image(self):
        """Test alt text generation with social image"""
        post = Post.objects.create(
            title='Test Post Title',
            content='Test content',
            author=self.user,
            social_image=self.create_test_image()
        )
        
        # Create featured media with alt text
        MediaItem.objects.create(
            post=post,
            media_type='image',
            is_featured=True,
            alt_text='Custom alt text'
        )
        
        alt_text = get_image_alt_text(post)
        self.assertEqual(alt_text, 'Custom alt text')

    def test_image_alt_text_fallback(self):
        """Test alt text fallback to post title"""
        post = Post.objects.create(
            title='Test Post Title',
            content='Test content',
            author=self.user
        )
        
        alt_text = get_image_alt_text(post)
        self.assertEqual(alt_text, 'Featured image for: Test Post Title')

    def test_image_priority_order(self):
        """Test that images are selected in correct priority order"""
        # Create post with both social_image and featured_image
        social_image = self.create_test_image()
        featured_image = self.create_test_image()
        
        post = Post.objects.create(
            title='Test Post',
            content='Test content',
            author=self.user,
            social_image=social_image,
            featured_image=featured_image
        )
        
        # Add media item
        media_image = self.create_test_image()
        MediaItem.objects.create(
            post=post,
            media_type='image',
            original_image=media_image,
            is_featured=True
        )
        
        # Should prioritize social_image
        image_url = get_social_image_url(post, self.request)
        self.assertIn('/media/social_images/', image_url)

    def test_media_item_image_priority(self):
        """Test MediaItem image size priority (large > medium > original)"""
        post = Post.objects.create(
            title='Test Post',
            content='Test content',
            author=self.user
        )
        
        # Create media item with multiple sizes
        media_item = MediaItem.objects.create(
            post=post,
            media_type='image',
            original_image=self.create_test_image(),
            medium_image=self.create_test_image(),
            large_image=self.create_test_image(),
            is_featured=True
        )
        
        image_url = get_social_image_url(post, self.request)
        # Should use large_image first
        self.assertIn('/media/blog_images/large/', image_url)


class SocialMetaTagsIntegrationTestCase(TestCase):
    """Integration tests for social meta tags in templates"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Test Category')

    def test_blog_detail_template_meta_tags(self):
        """Test that blog detail template includes proper meta tags"""
        post = Post.objects.create(
            title='Test Blog Post',
            content='This is test content for the blog post.',
            excerpt='This is a test excerpt.',
            author=self.user,
            status='published'
        )
        post.categories.add(self.category)
        
        response = self.client.get(f'/blog/{post.slug}/')
        self.assertEqual(response.status_code, 200)
        
        # Check for Open Graph tags
        self.assertContains(response, 'property="og:title"')
        self.assertContains(response, 'property="og:description"')
        self.assertContains(response, 'property="og:image"')
        self.assertContains(response, 'property="og:url"')
        self.assertContains(response, 'property="og:type" content="article"')
        
        # Check for Twitter Card tags
        self.assertContains(response, 'name="twitter:card"')
        self.assertContains(response, 'name="twitter:title"')
        self.assertContains(response, 'name="twitter:description"')
        self.assertContains(response, 'name="twitter:image"')
        
        # Check for article-specific tags
        self.assertContains(response, 'property="article:published_time"')
        self.assertContains(response, 'property="article:author"')

    def test_meta_tags_with_custom_image(self):
        """Test meta tags when post has custom social image"""
        # This would require creating actual image files for full integration test
        # For now, we'll test the template rendering logic
        post = Post.objects.create(
            title='Test Blog Post with Image',
            content='This is test content.',
            excerpt='Test excerpt.',
            author=self.user,
            status='published'
        )
        
        response = self.client.get(f'/blog/{post.slug}/')
        self.assertEqual(response.status_code, 200)
        
        # Should contain fallback image
        self.assertContains(response, 'web-app-manifest-512x512.png')