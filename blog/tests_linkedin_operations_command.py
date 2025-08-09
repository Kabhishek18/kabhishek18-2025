"""
Unit tests for LinkedIn Operations Management Command.

This test suite covers:
- Manual posting functionality
- API connectivity testing
- Bulk posting operations
- Credential validation and refresh
- Status and monitoring commands

Requirements covered: 1.1, 2.1, 2.3
"""

import json
from io import StringIO
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError

from blog.models import Post, Category, Tag
from blog.linkedin_models import LinkedInConfig, LinkedInPost
from blog.services.linkedin_service import (
    LinkedInAPIService, 
    LinkedInAPIError, 
    LinkedInAuthenticationError,
    LinkedInRateLimitError,
    LinkedInContentError
)


class LinkedInOperationsCommandTest(TransactionTestCase):
    """Test LinkedIn operations management command."""
    
    def setUp(self):
        """Set up test data."""
        # Clear any existing configurations
        LinkedInConfig.objects.all().delete()
        LinkedInPost.objects.all().delete()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test category and tags
        self.category = Category.objects.create(name='Technology', slug='technology')
        self.tag1 = Tag.objects.create(name='Python', slug='python')
        self.tag2 = Tag.objects.create(name='Django', slug='django')
        
        # Create test blog post
        self.post = Post.objects.create(
            title='Test Blog Post for LinkedIn',
            slug='test-blog-post-linkedin',
            author=self.user,
            content='This is a test blog post content for LinkedIn posting.',
            excerpt='Test excerpt for LinkedIn posting.',
            status='published'
        )
        self.post.categories.add(self.category)
        self.post.tags.add(self.tag1, self.tag2)
        
        # Create LinkedIn configuration
        self.config = LinkedInConfig(
            client_id='test_client_id_12345',
            is_active=True
        )
        self.config.set_client_secret('test_client_secret')
        self.config.set_access_token('test_access_token')
        self.config.token_expires_at = timezone.now() + timedelta(hours=1)
        self.config.save()
    
    def test_command_help_display(self):
        """Test that command displays help correctly."""
        out = StringIO()
        call_command('linkedin_operations', stdout=out)
        output = out.getvalue()
        
        self.assertIn('LinkedIn Operations Management Command', output)
        self.assertIn('Available operations:', output)
        self.assertIn('post      - Manually post a blog post to LinkedIn', output)
        self.assertIn('test      - Test LinkedIn API connectivity', output)
        self.assertIn('bulk      - Bulk post existing published posts', output)
        self.assertIn('credentials - Validate and refresh LinkedIn credentials', output)
        self.assertIn('status    - Show LinkedIn posting status and statistics', output)
    
    def test_status_command_with_no_posts(self):
        """Test status command when no LinkedIn posts exist."""
        out = StringIO()
        call_command('linkedin_operations', 'status', '--stats', stdout=out)
        output = out.getvalue()
        
        self.assertIn('LinkedIn Posting Status', output)
        self.assertIn('Total LinkedIn posts: 0', output)
        self.assertIn('Successful: 0', output)
        self.assertIn('Failed: 0', output)
        self.assertIn('Pending/Retrying: 0', output)
        self.assertIn('No posts found.', output)
    
    def test_status_command_with_posts(self):
        """Test status command with existing LinkedIn posts."""
        # Create test LinkedIn posts
        linkedin_post1 = LinkedInPost.objects.create(
            post=self.post,
            status='success',
            linkedin_post_id='test_post_id_1',
            posted_at=timezone.now()
        )
        
        linkedin_post2 = LinkedInPost.objects.create(
            post=self.post,
            status='failed',
            error_message='Test error message',
            attempt_count=3
        )
        
        out = StringIO()
        call_command('linkedin_operations', 'status', '--stats', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Total LinkedIn posts: 2', output)
        self.assertIn('Successful: 1', output)
        self.assertIn('Failed: 1', output)
        self.assertIn('Success rate: 50.0%', output)
    
    def test_credentials_status_command(self):
        """Test credentials status command."""
        out = StringIO()
        call_command('linkedin_operations', 'credentials', 'status', stdout=out)
        output = out.getvalue()
        
        self.assertIn('LinkedIn Credential Status:', output)
        self.assertIn(f'Configuration ID: {self.config.id}', output)
        self.assertIn('Active: True', output)
        self.assertIn('Client ID: test_client_id_12345', output)
        self.assertIn('Has Client Secret: ✓', output)
        self.assertIn('Has Access Token: ✓', output)
    
    def test_credentials_status_no_config(self):
        """Test credentials status command with no configuration."""
        LinkedInConfig.objects.all().delete()
        
        with self.assertRaises(CommandError) as cm:
            call_command('linkedin_operations', 'credentials', 'status')
        
        self.assertIn('No active LinkedIn configuration found', str(cm.exception))
    
    def test_api_test_command_not_configured(self):
        """Test API test command when LinkedIn is not configured."""
        LinkedInConfig.objects.all().delete()
        
        out = StringIO()
        call_command('linkedin_operations', 'test', '--auth', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Testing LinkedIn API connectivity...', output)
        self.assertIn('1. Configuration Test:', output)
        self.assertIn('✗ LinkedIn integration is not configured', output)
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.authenticate')
    def test_api_test_command_configured(self, mock_authenticate):
        """Test API test command when LinkedIn is configured."""
        mock_authenticate.return_value = True
        
        out = StringIO()
        call_command('linkedin_operations', 'test', '--auth', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Testing LinkedIn API connectivity...', output)
        self.assertIn('1. Configuration Test:', output)
        self.assertIn('✓ LinkedIn integration is configured', output)
        self.assertIn('2. Authentication Test:', output)
        self.assertIn('✓ Authentication successful', output)
        self.assertIn('Authentication test completed successfully.', output)
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.authenticate')
    @patch('blog.services.linkedin_service.LinkedInAPIService.get_user_profile')
    def test_api_test_command_with_profile(self, mock_get_profile, mock_authenticate):
        """Test API test command with profile access."""
        mock_authenticate.return_value = True
        mock_get_profile.return_value = {
            'id': 'test_profile_id',
            'localizedFirstName': 'Test',
            'localizedLastName': 'User'
        }
        
        out = StringIO()
        call_command('linkedin_operations', 'test', '--profile', '--verbose', stdout=out)
        output = out.getvalue()
        
        self.assertIn('✓ LinkedIn integration is configured', output)
        self.assertIn('✓ Authentication successful', output)
        self.assertIn('3. Profile Access Test:', output)
        self.assertIn('✓ Profile access successful', output)
        self.assertIn('Name: Test User', output)
        self.assertIn('Profile ID: test_profile_id', output)
        self.assertIn('All API connectivity tests completed successfully!', output)
    
    def test_bulk_command_no_posts(self):
        """Test bulk command when no posts are available."""
        Post.objects.all().delete()
        
        out = StringIO()
        call_command('linkedin_operations', 'bulk', '--dry-run', stdout=out)
        output = out.getvalue()
        
        self.assertIn('LinkedIn Bulk Posting Operation', output)
        self.assertIn('No posts found matching the criteria.', output)
    
    def test_bulk_command_dry_run(self):
        """Test bulk command in dry run mode."""
        out = StringIO()
        call_command('linkedin_operations', 'bulk', '--dry-run', '--limit', '1', stdout=out)
        output = out.getvalue()
        
        self.assertIn('LinkedIn Bulk Posting Operation', output)
        self.assertIn('Found 1 posts to process', output)
        self.assertIn(f'Processing post 1/1: "{self.post.title}"', output)
        self.assertIn('DRY RUN: Would post the following content:', output)
        self.assertIn('Bulk posting operation completed!', output)
        self.assertIn('Successful: 1', output)
    
    def test_bulk_command_with_filters(self):
        """Test bulk command with various filters."""
        # Test category filter
        out = StringIO()
        call_command('linkedin_operations', 'bulk', '--dry-run', '--category', 'Technology', stdout=out)
        output = out.getvalue()
        self.assertIn('Filter: Category contains "Technology"', output)
        
        # Test author filter
        out = StringIO()
        call_command('linkedin_operations', 'bulk', '--dry-run', '--author', 'testuser', stdout=out)
        output = out.getvalue()
        self.assertIn('Filter: Author "testuser"', output)
        
        # Test days filter
        out = StringIO()
        call_command('linkedin_operations', 'bulk', '--dry-run', '--days', '7', stdout=out)
        output = out.getvalue()
        self.assertIn('Filter: Posts from last 7 days', output)
    
    def test_manual_post_command_post_not_found(self):
        """Test manual post command with non-existent post ID."""
        with self.assertRaises(CommandError) as cm:
            call_command('linkedin_operations', 'post', '999')
        
        self.assertIn('Blog post with ID 999 not found', str(cm.exception))
    
    def test_manual_post_command_post_not_published(self):
        """Test manual post command with non-published post."""
        self.post.status = 'draft'
        self.post.save()
        
        with self.assertRaises(CommandError) as cm:
            call_command('linkedin_operations', 'post', str(self.post.id))
        
        self.assertIn('is not published (status: draft)', str(cm.exception))
    
    def test_manual_post_command_dry_run(self):
        """Test manual post command in dry run mode."""
        out = StringIO()
        call_command('linkedin_operations', 'post', str(self.post.id), '--dry-run', stdout=out)
        output = out.getvalue()
        
        self.assertIn(f'Manual LinkedIn posting for post ID: {self.post.id}', output)
        self.assertIn(f'Post: "{self.post.title}"', output)
        self.assertIn('Author: testuser', output)
        self.assertIn('Formatted LinkedIn content:', output)
        self.assertIn('DRY RUN: Content formatted successfully. No actual posting performed.', output)
    
    def test_manual_post_command_already_posted(self):
        """Test manual post command with already posted content."""
        # Create existing LinkedIn post
        LinkedInPost.objects.create(
            post=self.post,
            status='success',
            linkedin_post_id='existing_post_id'
        )
        
        out = StringIO()
        call_command('linkedin_operations', 'post', str(self.post.id), stdout=out)
        output = out.getvalue()
        
        self.assertIn('was already posted to LinkedIn successfully', output)
        self.assertIn('Use --force to post again.', output)
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.create_post')
    @patch('blog.services.linkedin_service.LinkedInAPIService.authenticate')
    def test_manual_post_command_success(self, mock_authenticate, mock_create_post):
        """Test successful manual post command."""
        mock_authenticate.return_value = True
        mock_create_post.return_value = {'id': 'new_linkedin_post_id'}
        
        out = StringIO()
        call_command('linkedin_operations', 'post', str(self.post.id), stdout=out)
        output = out.getvalue()
        
        self.assertIn('Posting to LinkedIn...', output)
        self.assertIn('✓ Successfully posted to LinkedIn!', output)
        self.assertIn('LinkedIn Post ID: new_linkedin_post_id', output)
        
        # Verify LinkedIn post was created in database
        linkedin_post = LinkedInPost.objects.get(post=self.post)
        self.assertEqual(linkedin_post.status, 'success')
        self.assertEqual(linkedin_post.linkedin_post_id, 'new_linkedin_post_id')
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.create_post')
    @patch('blog.services.linkedin_service.LinkedInAPIService.authenticate')
    def test_manual_post_command_failure(self, mock_authenticate, mock_create_post):
        """Test manual post command with API failure."""
        mock_authenticate.return_value = True
        mock_create_post.side_effect = LinkedInAPIError('Test API error', error_code='TEST_ERROR')
        
        with self.assertRaises(CommandError) as cm:
            call_command('linkedin_operations', 'post', str(self.post.id))
        
        self.assertIn('LinkedIn posting failed: Test API error', str(cm.exception))
        
        # Verify LinkedIn post was marked as failed in database
        linkedin_post = LinkedInPost.objects.get(post=self.post)
        self.assertEqual(linkedin_post.status, 'retrying')  # Should be retrying since it's retryable
        self.assertEqual(linkedin_post.error_message, 'Test API error')
        self.assertEqual(linkedin_post.error_code, 'TEST_ERROR')
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.refresh_access_token')
    def test_credentials_refresh_command_success(self, mock_refresh):
        """Test successful credentials refresh command."""
        mock_refresh.return_value = True
        
        out = StringIO()
        call_command('linkedin_operations', 'credentials', 'refresh', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Refreshing LinkedIn access token...', output)
        self.assertIn('✓ Access token refreshed successfully', output)
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.refresh_access_token')
    def test_credentials_refresh_command_failure(self, mock_refresh):
        """Test credentials refresh command failure."""
        mock_refresh.side_effect = LinkedInAPIError('Token refresh failed')
        
        out = StringIO()
        call_command('linkedin_operations', 'credentials', 'refresh', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Refreshing LinkedIn access token...', output)
        self.assertIn('✗ Token refresh error: Token refresh failed', output)
    
    @patch('blog.services.linkedin_service.LinkedInAPIService.authenticate')
    def test_credentials_validate_command(self, mock_authenticate):
        """Test credentials validation command."""
        mock_authenticate.return_value = True
        
        with patch.object(self.config, 'validate_credentials') as mock_validate:
            mock_validate.return_value = {
                'client_secret_valid': True,
                'access_token_valid': True,
                'refresh_token_valid': False,
                'errors': []
            }
            
            out = StringIO()
            call_command('linkedin_operations', 'credentials', 'validate', stdout=out)
            output = out.getvalue()
            
            self.assertIn('Validating LinkedIn credentials...', output)
            self.assertIn('Client Secret: ✓ Valid', output)
            self.assertIn('Access Token: ✓ Valid', output)
            self.assertIn('Refresh Token: ⚠ Missing/Invalid', output)
            self.assertIn('✓ API authentication successful', output)
    
    def test_command_error_handling(self):
        """Test command error handling for invalid operations."""
        with self.assertRaises(SystemExit):
            call_command('linkedin_operations', 'invalid_operation')
    
    def test_bulk_command_with_existing_posts(self):
        """Test bulk command excludes already posted content."""
        # Create existing LinkedIn post
        LinkedInPost.objects.create(
            post=self.post,
            status='success',
            linkedin_post_id='existing_post_id'
        )
        
        out = StringIO()
        call_command('linkedin_operations', 'bulk', '--dry-run', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Filter: Excluding already posted posts', output)
        self.assertIn('No posts found matching the criteria.', output)
    
    def test_bulk_command_force_repost(self):
        """Test bulk command with force flag to repost existing content."""
        # Create existing LinkedIn post
        LinkedInPost.objects.create(
            post=self.post,
            status='success',
            linkedin_post_id='existing_post_id'
        )
        
        out = StringIO()
        call_command('linkedin_operations', 'bulk', '--dry-run', '--force', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Found 1 posts to process', output)
        self.assertIn('DRY RUN: Would post the following content:', output)


class LinkedInOperationsCommandIntegrationTest(TransactionTestCase):
    """Integration tests for LinkedIn operations command with real-like scenarios."""
    
    def setUp(self):
        """Set up test data for integration tests."""
        # Clear any existing data
        LinkedInConfig.objects.all().delete()
        LinkedInPost.objects.all().delete()
        Post.objects.all().delete()
        User.objects.all().delete()
        
        # Create test users
        self.user1 = User.objects.create_user(
            username='author1',
            email='author1@example.com',
            first_name='John',
            last_name='Doe'
        )
        
        self.user2 = User.objects.create_user(
            username='author2',
            email='author2@example.com',
            first_name='Jane',
            last_name='Smith'
        )
        
        # Create categories and tags
        self.tech_category = Category.objects.create(name='Technology', slug='technology')
        self.business_category = Category.objects.create(name='Business', slug='business')
        
        self.python_tag = Tag.objects.create(name='Python', slug='python')
        self.django_tag = Tag.objects.create(name='Django', slug='django')
        self.ai_tag = Tag.objects.create(name='AI', slug='ai')
        
        # Create multiple test posts
        self.posts = []
        for i in range(5):
            post = Post.objects.create(
                title=f'Test Blog Post {i+1}',
                slug=f'test-blog-post-{i+1}',
                author=self.user1 if i % 2 == 0 else self.user2,
                content=f'This is test blog post content {i+1} for LinkedIn posting.',
                excerpt=f'Test excerpt {i+1} for LinkedIn posting.',
                status='published',
                created_at=timezone.now() - timedelta(days=i)
            )
            post.categories.add(self.tech_category if i % 2 == 0 else self.business_category)
            post.tags.add(self.python_tag, self.django_tag)
            self.posts.append(post)
        
        # Create LinkedIn configuration
        self.config = LinkedInConfig(
            client_id='integration_test_client_id',
            is_active=True
        )
        self.config.set_client_secret('integration_test_secret')
        self.config.set_access_token('integration_test_token')
        self.config.token_expires_at = timezone.now() + timedelta(hours=2)
        self.config.save()
    
    def test_bulk_operation_with_multiple_posts(self):
        """Test bulk operation with multiple posts and various filters."""
        # Test bulk operation with limit
        out = StringIO()
        call_command('linkedin_operations', 'bulk', '--dry-run', '--limit', '3', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Found 3 posts to process', output)
        self.assertIn('Bulk posting operation completed!', output)
        self.assertIn('Successful: 3', output)
        
        # Test with author filter
        out = StringIO()
        call_command('linkedin_operations', 'bulk', '--dry-run', '--author', 'author1', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Filter: Author "author1"', output)
        # Should find 3 posts by author1 (posts 0, 2, 4)
        self.assertIn('Found 3 posts to process', output)
        
        # Test with category filter
        out = StringIO()
        call_command('linkedin_operations', 'bulk', '--dry-run', '--category', 'Technology', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Filter: Category contains "Technology"', output)
        # Should find 3 posts in Technology category (posts 0, 2, 4)
        self.assertIn('Found 3 posts to process', output)
        
        # Test with days filter
        out = StringIO()
        call_command('linkedin_operations', 'bulk', '--dry-run', '--days', '2', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Filter: Posts from last 2 days', output)
        # Should find posts from last 2 days (posts 0, 1)
        self.assertIn('Found 2 posts to process', output)
    
    def test_status_command_with_mixed_post_statuses(self):
        """Test status command with posts in various states."""
        # Create LinkedIn posts in different states
        LinkedInPost.objects.create(
            post=self.posts[0],
            status='success',
            linkedin_post_id='success_post_1',
            posted_at=timezone.now() - timedelta(hours=1)
        )
        
        LinkedInPost.objects.create(
            post=self.posts[1],
            status='failed',
            error_message='Rate limit exceeded',
            error_code='RATE_LIMIT',
            attempt_count=3
        )
        
        LinkedInPost.objects.create(
            post=self.posts[2],
            status='retrying',
            error_message='Temporary server error',
            attempt_count=1,
            next_retry_at=timezone.now() + timedelta(minutes=30)
        )
        
        LinkedInPost.objects.create(
            post=self.posts[3],
            status='pending'
        )
        
        # Test general status
        out = StringIO()
        call_command('linkedin_operations', 'status', '--stats', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Total LinkedIn posts: 4', output)
        self.assertIn('Successful: 1', output)
        self.assertIn('Failed: 1', output)
        self.assertIn('Pending/Retrying: 2', output)
        self.assertIn('Success rate: 25.0%', output)
        
        # Test failed posts filter
        out = StringIO()
        call_command('linkedin_operations', 'status', '--failed', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Showing failed posts only:', output)
        self.assertIn('✗ Test Blog Post 2', output)
        self.assertIn('Status: Failed', output)
        self.assertIn('Error: Rate limit exceeded', output)
        self.assertIn('Error Code: RATE_LIMIT', output)
        
        # Test pending posts filter
        out = StringIO()
        call_command('linkedin_operations', 'status', '--pending', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Showing pending/retrying posts only:', output)
        self.assertIn('🔄 Test Blog Post 3', output)
        self.assertIn('Status: Retrying', output)
        self.assertIn('⏳ Test Blog Post 4', output)
        self.assertIn('Status: Pending', output)
    
    def test_comprehensive_workflow(self):
        """Test a comprehensive workflow combining multiple operations."""
        # 1. Check initial status
        out = StringIO()
        call_command('linkedin_operations', 'status', '--stats', stdout=out)
        output = out.getvalue()
        self.assertIn('Total LinkedIn posts: 0', output)
        
        # 2. Test API connectivity
        with patch('blog.services.linkedin_service.LinkedInAPIService.authenticate') as mock_auth:
            mock_auth.return_value = True
            
            out = StringIO()
            call_command('linkedin_operations', 'test', '--auth', stdout=out)
            output = out.getvalue()
            self.assertIn('✓ Authentication successful', output)
        
        # 3. Perform bulk dry run
        out = StringIO()
        call_command('linkedin_operations', 'bulk', '--dry-run', '--limit', '2', stdout=out)
        output = out.getvalue()
        self.assertIn('Found 2 posts to process', output)
        self.assertIn('Successful: 2', output)
        
        # 4. Manually post one item (dry run)
        out = StringIO()
        call_command('linkedin_operations', 'post', str(self.posts[0].id), '--dry-run', stdout=out)
        output = out.getvalue()
        self.assertIn('DRY RUN: Content formatted successfully', output)
        
        # 5. Check credentials status
        out = StringIO()
        call_command('linkedin_operations', 'credentials', 'status', stdout=out)
        output = out.getvalue()
        self.assertIn('LinkedIn Credential Status:', output)
        self.assertIn('Active: True', output)