"""
Tests for enhanced Open Graph meta tags functionality.
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.template import Template, Context
from django.core.files.uploadedfile import SimpleUploadedFile
from blog.models import Post, MediaItem
from blog.templatetags.media_tags import (
    get_social_image_url, 
    get_image_dimensions, 
    get_image_type,
    get_linkedin_optimized_image,
    get_fallback_images,
    render_social_meta_tags
)
import tempfile
import os
from PIL import Image


class EnhancedSocialMetaTagsTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.factory = RequestFactory()
        
        # Create a test post
        self.post = Post.objects.create(
            title='Test Post for Social Meta Tags',
            slug='test-post-social-meta',
            author=self.user,
            content='This is a test post for social meta tags.',
            excerpt='Test excerpt for social sharing',
            status='published'
        )
        
        # Create test images
        self.create_test_images()
    
    def create_test_images(self):
        """Create test image files"""
        # Create a temporary image for featured_image
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            image = Image.new('RGB', (1200, 800), color='red')
            image.save(tmp_file, format='JPEG')
            tmp_file.seek(0)
            
            self.post.featured_image.save(
                'test_featured.jpg',
                SimpleUploadedFile(
                    'test_featured.jpg',
                    tmp_file.read(),
                    content_type='image/jpeg'
                )
            )
        
        # Create a temporary image for social_image
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            image = Image.new('RGB', (1200, 627), color='blue')
            image.save(tmp_file, format='PNG')
            tmp_file.seek(0)
            
            self.post.social_image.save(
                'test_social.png',
                SimpleUploadedFile(
                    'test_social.png',
                    tmp_file.read(),
                    content_type='image/png'
                )
            )
        
        self.post.save()
    
    def test_get_social_image_url_with_social_image(self):
        """Test that social_image takes priority"""
        request = self.factory.get('/')
        request.META['HTTP_HOST'] = 'testserver'
        request.META['wsgi.url_scheme'] = 'http'
        
        image_url = get_social_image_url(self.post, request)
        self.assertIn('test_social.png', image_url)
        self.assertTrue(image_url.startswith('http://testserver'))
    
    def test_get_social_image_url_fallback_to_featured(self):
        """Test fallback to featured_image when social_image is not available"""
        # Remove social_image
        self.post.social_image.delete()
        self.post.save()
        
        request = self.factory.get('/')
        request.META['HTTP_HOST'] = 'testserver'
        request.META['wsgi.url_scheme'] = 'http'
        
        image_url = get_social_image_url(self.post, request)
        self.assertIn('test_featured.jpg', image_url)
        self.assertTrue(image_url.startswith('http://testserver'))
    
    def test_get_social_image_url_without_request(self):
        """Test image URL generation without request object"""
        image_url = get_social_image_url(self.post, None)
        self.assertIn('test_social.png', image_url)
        self.assertTrue(image_url.startswith('https://kabhishek18.com'))
    
    def test_get_image_dimensions(self):
        """Test image dimensions extraction"""
        dimensions = get_image_dimensions(self.post.social_image)
        self.assertEqual(dimensions['width'], 1200)
        self.assertEqual(dimensions['height'], 627)
        
        dimensions = get_image_dimensions(self.post.featured_image)
        self.assertEqual(dimensions['width'], 1200)
        self.assertEqual(dimensions['height'], 800)
    
    def test_get_image_type(self):
        """Test image type detection"""
        image_type = get_image_type(self.post.social_image)
        self.assertEqual(image_type, 'image/png')
        
        image_type = get_image_type(self.post.featured_image)
        self.assertEqual(image_type, 'image/jpeg')
    
    def test_get_fallback_images(self):
        """Test fallback images generation"""
        request = self.factory.get('/')
        request.META['HTTP_HOST'] = 'testserver'
        request.META['wsgi.url_scheme'] = 'http'
        
        fallback_images = get_fallback_images(self.post, request)
        self.assertIsInstance(fallback_images, list)
        self.assertGreater(len(fallback_images), 0)
        
        # Check structure of fallback images
        for img in fallback_images:
            self.assertIn('url', img)
            self.assertIn('width', img)
            self.assertIn('height', img)
            self.assertIn('alt', img)
            self.assertIn('type', img)
    
    def test_render_social_meta_tags_template_tag(self):
        """Test the render_social_meta_tags template tag"""
        request = self.factory.get('/')
        request.META['HTTP_HOST'] = 'testserver'
        request.META['wsgi.url_scheme'] = 'http'
        
        # Test the template tag function directly
        context_data = render_social_meta_tags(self.post, request)
        
        self.assertIn('post', context_data)
        self.assertIn('image_url', context_data)
        self.assertIn('image_width', context_data)
        self.assertIn('image_height', context_data)
        self.assertIn('image_alt', context_data)
        self.assertIn('image_type', context_data)
        self.assertIn('canonical_url', context_data)
        
        # Verify values
        self.assertEqual(context_data['post'], self.post)
        self.assertIn('test_social.png', context_data['image_url'])
        self.assertEqual(context_data['image_width'], 1200)
        self.assertEqual(context_data['image_height'], 627)
        self.assertEqual(context_data['image_type'], 'image/png')
    
    def test_social_meta_tags_template_rendering(self):
        """Test that the social meta tags template renders correctly"""
        template_content = '''
        {% load media_tags %}
        {% render_social_meta_tags post request %}
        '''
        
        template = Template(template_content)
        request = self.factory.get('/')
        request.META['HTTP_HOST'] = 'testserver'
        request.META['wsgi.url_scheme'] = 'http'
        
        context = Context({
            'post': self.post,
            'request': request
        })
        
        rendered = template.render(context)
        
        # Check for essential Open Graph tags
        self.assertIn('og:title', rendered)
        self.assertIn('og:description', rendered)
        self.assertIn('og:image', rendered)
        self.assertIn('og:image:width', rendered)
        self.assertIn('og:image:height', rendered)
        self.assertIn('og:image:alt', rendered)
        self.assertIn('og:image:type', rendered)
        
        # Check for Twitter Card tags
        self.assertIn('twitter:card', rendered)
        self.assertIn('twitter:image', rendered)
        
        # Check for LinkedIn-specific tags
        self.assertIn('og:locale', rendered)
        
        # Verify image URL is included
        self.assertIn('test_social.png', rendered)
    
    def test_fallback_when_no_images(self):
        """Test fallback behavior when post has no images"""
        # Create a post without images
        post_no_images = Post.objects.create(
            title='Post Without Images',
            slug='post-without-images',
            author=self.user,
            content='This post has no images.',
            excerpt='No images here',
            status='published'
        )
        
        request = self.factory.get('/')
        request.META['HTTP_HOST'] = 'testserver'
        request.META['wsgi.url_scheme'] = 'http'
        
        image_url = get_social_image_url(post_no_images, request)
        self.assertIn('web-app-manifest-512x512.png', image_url)
        
        fallback_images = get_fallback_images(post_no_images, request)
        self.assertGreater(len(fallback_images), 0)
        self.assertIn('web-app-manifest-512x512.png', fallback_images[0]['url'])
    
    def tearDown(self):
        """Clean up test files"""
        if self.post.featured_image:
            if os.path.exists(self.post.featured_image.path):
                os.remove(self.post.featured_image.path)
        
        if self.post.social_image:
            if os.path.exists(self.post.social_image.path):
                os.remove(self.post.social_image.path)