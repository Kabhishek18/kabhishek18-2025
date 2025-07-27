"""
Tests for social sharing functionality.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.http import JsonResponse
from unittest.mock import patch
import json

from .models import Post, Category, SocialShare
from .services import SocialShareService


class SocialShareServiceTest(TestCase):
    """Test cases for SocialShareService."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='This is a test post content.',
            excerpt='Test excerpt',
            status='published'
        )
        self.post.categories.add(self.category)
    
    def test_track_share_creates_new_record(self):
        """Test that tracking a share creates a new SocialShare record."""
        # Track a share
        social_share = SocialShareService.track_share(self.post, 'facebook')
        
        # Verify the record was created
        self.assertEqual(social_share.post, self.post)
        self.assertEqual(social_share.platform, 'facebook')
        self.assertEqual(social_share.share_count, 1)
        
        # Verify it exists in the database
        self.assertTrue(
            SocialShare.objects.filter(
                post=self.post, 
                platform='facebook'
            ).exists()
        )
    
    def test_track_share_increments_existing_record(self):
        """Test that tracking a share increments existing record."""
        # Create initial share record
        SocialShare.objects.create(
            post=self.post,
            platform='twitter',
            share_count=5
        )
        
        # Track another share
        social_share = SocialShareService.track_share(self.post, 'twitter')
        
        # Verify the count was incremented
        self.assertEqual(social_share.share_count, 6)
    
    def test_track_share_invalid_platform(self):
        """Test that tracking with invalid platform raises ValueError."""
        with self.assertRaises(ValueError):
            SocialShareService.track_share(self.post, 'invalid_platform')
    
    def test_get_share_counts(self):
        """Test getting share counts for a post."""
        # Create some share records
        SocialShare.objects.create(
            post=self.post,
            platform='facebook',
            share_count=10
        )
        SocialShare.objects.create(
            post=self.post,
            platform='twitter',
            share_count=5
        )
        
        # Get share counts
        share_counts = SocialShareService.get_share_counts(self.post)
        
        # Verify the counts
        self.assertEqual(share_counts['facebook'], 10)
        self.assertEqual(share_counts['twitter'], 5)
        self.assertEqual(share_counts['linkedin'], 0)  # Not created, should be 0
    
    def test_get_total_shares(self):
        """Test getting total share count for a post."""
        # Create some share records
        SocialShare.objects.create(
            post=self.post,
            platform='facebook',
            share_count=10
        )
        SocialShare.objects.create(
            post=self.post,
            platform='twitter',
            share_count=5
        )
        
        # Get total shares
        total_shares = SocialShareService.get_total_shares(self.post)
        
        # Verify the total
        self.assertEqual(total_shares, 15)
    
    def test_generate_share_urls(self):
        """Test generating platform-specific share URLs."""
        share_urls = SocialShareService.generate_share_urls(self.post)
        
        # Verify all platforms are included
        expected_platforms = ['facebook', 'twitter', 'linkedin', 'reddit', 'pinterest', 'whatsapp']
        for platform in expected_platforms:
            self.assertIn(platform, share_urls)
            self.assertIn('url', share_urls[platform])
            self.assertIn('name', share_urls[platform])
            self.assertIn('icon', share_urls[platform])
            self.assertIn('color', share_urls[platform])
        
        # Verify Facebook URL format
        facebook_url = share_urls['facebook']['url']
        self.assertIn('facebook.com/sharer', facebook_url)
        self.assertIn('test-post', facebook_url)
        
        # Verify Twitter URL format
        twitter_url = share_urls['twitter']['url']
        self.assertIn('twitter.com/intent/tweet', twitter_url)
        self.assertIn('Test%20Post', twitter_url)
    
    def test_get_platform_config(self):
        """Test getting platform configuration."""
        facebook_config = SocialShareService.get_platform_config('facebook')
        
        self.assertEqual(facebook_config['name'], 'Facebook')
        self.assertEqual(facebook_config['icon'], 'fab fa-facebook-f')
        self.assertEqual(facebook_config['color'], '#1877f2')
        
        # Test invalid platform
        invalid_config = SocialShareService.get_platform_config('invalid')
        self.assertEqual(invalid_config, {})


class SocialShareViewTest(TestCase):
    """Test cases for social sharing views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='This is a test post content.',
            excerpt='Test excerpt',
            status='published'
        )
    
    def test_track_social_share_success(self):
        """Test successful social share tracking."""
        url = reverse('blog:track_social_share', kwargs={'slug': self.post.slug})
        
        response = self.client.post(url, {
            'platform': 'facebook'
        })
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['platform'], 'facebook')
        self.assertEqual(data['share_count'], 1)
        self.assertEqual(data['total_shares'], 1)
        
        # Verify the record was created
        self.assertTrue(
            SocialShare.objects.filter(
                post=self.post,
                platform='facebook'
            ).exists()
        )
    
    def test_track_social_share_missing_platform(self):
        """Test social share tracking with missing platform."""
        url = reverse('blog:track_social_share', kwargs={'slug': self.post.slug})
        
        response = self.client.post(url, {})
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Platform is required')
    
    def test_track_social_share_invalid_platform(self):
        """Test social share tracking with invalid platform."""
        url = reverse('blog:track_social_share', kwargs={'slug': self.post.slug})
        
        response = self.client.post(url, {
            'platform': 'invalid_platform'
        })
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_track_social_share_nonexistent_post(self):
        """Test social share tracking with nonexistent post."""
        url = reverse('blog:track_social_share', kwargs={'slug': 'nonexistent-post'})
        
        response = self.client.post(url, {
            'platform': 'facebook'
        })
        
        self.assertEqual(response.status_code, 404)
    
    def test_track_social_share_get_method(self):
        """Test that GET method is not allowed for share tracking."""
        url = reverse('blog:track_social_share', kwargs={'slug': self.post.slug})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 405)  # Method not allowed


class BlogDetailViewTest(TestCase):
    """Test cases for blog detail view with social sharing."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='This is a test post content.',
            excerpt='Test excerpt',
            status='published'
        )
        
        # Create some share records
        SocialShare.objects.create(
            post=self.post,
            platform='facebook',
            share_count=10
        )
        SocialShare.objects.create(
            post=self.post,
            platform='twitter',
            share_count=5
        )
    
    def test_blog_detail_includes_social_sharing_data(self):
        """Test that blog detail view includes social sharing data."""
        url = reverse('blog:detail', kwargs={'slug': self.post.slug})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that social sharing data is in context
        self.assertIn('share_urls', response.context)
        self.assertIn('share_counts', response.context)
        self.assertIn('total_shares', response.context)
        
        # Verify share counts
        share_counts = response.context['share_counts']
        self.assertEqual(share_counts['facebook'], 10)
        self.assertEqual(share_counts['twitter'], 5)
        
        # Verify total shares
        total_shares = response.context['total_shares']
        self.assertEqual(total_shares, 15)
        
        # Verify share URLs are generated
        share_urls = response.context['share_urls']
        self.assertIn('facebook', share_urls)
        self.assertIn('twitter', share_urls)


class SocialShareModelTest(TestCase):
    """Test cases for SocialShare model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='This is a test post content.',
            status='published'
        )
    
    def test_social_share_creation(self):
        """Test creating a SocialShare instance."""
        social_share = SocialShare.objects.create(
            post=self.post,
            platform='facebook',
            share_count=5
        )
        
        self.assertEqual(social_share.post, self.post)
        self.assertEqual(social_share.platform, 'facebook')
        self.assertEqual(social_share.share_count, 5)
        self.assertEqual(str(social_share), f"{self.post.title} shared on Facebook (5 times)")
    
    def test_increment_share_count(self):
        """Test incrementing share count."""
        social_share = SocialShare.objects.create(
            post=self.post,
            platform='twitter',
            share_count=3
        )
        
        # Increment the count
        social_share.increment_share_count()
        
        # Verify the count was incremented
        social_share.refresh_from_db()
        self.assertEqual(social_share.share_count, 4)
    
    def test_unique_together_constraint(self):
        """Test that post and platform combination is unique."""
        # Create first record
        SocialShare.objects.create(
            post=self.post,
            platform='linkedin',
            share_count=1
        )
        
        # Try to create duplicate - should raise IntegrityError
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            SocialShare.objects.create(
                post=self.post,
                platform='linkedin',
                share_count=2
            )