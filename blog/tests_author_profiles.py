"""
Tests for the enhanced author profile system.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from .models import AuthorProfile, Post, Category, Tag
from .services.author_service import AuthorService
import tempfile
from PIL import Image
import io


class AuthorProfileModelTest(TestCase):
    """Test cases for the AuthorProfile model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testauthor',
            email='test@example.com',
            first_name='Test',
            last_name='Author'
        )
        
        self.guest_user = User.objects.create_user(
            username='guestauthor',
            email='guest@example.com',
            first_name='Guest',
            last_name='Writer'
        )
    
    def test_author_profile_creation(self):
        """Test that AuthorProfile is created automatically with User."""
        # Profile should be created automatically via signals
        self.assertTrue(hasattr(self.user, 'author_profile'))
        self.assertIsInstance(self.user.author_profile, AuthorProfile)
        self.assertTrue(self.user.author_profile.is_active)
        self.assertFalse(self.user.author_profile.is_guest_author)
    
    def test_get_display_name(self):
        """Test the get_display_name method."""
        profile = self.user.author_profile
        
        # With first and last name
        self.assertEqual(profile.get_display_name(), 'Test Author')
        
        # With only first name
        self.user.last_name = ''
        self.user.save()
        self.assertEqual(profile.get_display_name(), 'Test')
        
        # With no names, should use username
        self.user.first_name = ''
        self.user.save()
        self.assertEqual(profile.get_display_name(), 'testauthor')
    
    def test_get_short_bio(self):
        """Test the get_short_bio method."""
        profile = self.user.author_profile
        
        # No bio
        self.assertEqual(profile.get_short_bio(), "")
        
        # Short bio
        profile.bio = "This is a short bio."
        profile.save()
        self.assertEqual(profile.get_short_bio(), "This is a short bio.")
        
        # Long bio that needs truncation
        long_bio = "This is a very long bio that should be truncated. " * 10
        profile.bio = long_bio
        profile.save()
        short_bio = profile.get_short_bio(max_length=50)
        self.assertTrue(len(short_bio) <= 53)  # 50 + '...'
        self.assertTrue(short_bio.endswith('...'))
    
    def test_get_social_links(self):
        """Test the get_social_links method."""
        profile = self.user.author_profile
        
        # No social links
        self.assertEqual(profile.get_social_links(), {})
        
        # Add social links
        profile.website = 'https://example.com'
        profile.twitter = '@testuser'
        profile.linkedin = 'https://linkedin.com/in/testuser'
        profile.github = 'testuser'
        profile.instagram = 'testuser'
        profile.save()
        
        social_links = profile.get_social_links()
        
        self.assertIn('website', social_links)
        self.assertIn('twitter', social_links)
        self.assertIn('linkedin', social_links)
        self.assertIn('github', social_links)
        self.assertIn('instagram', social_links)
        
        # Check Twitter URL formatting
        self.assertEqual(social_links['twitter']['url'], 'https://twitter.com/testuser')
        self.assertEqual(social_links['twitter']['display'], '@testuser')
        
        # Check GitHub URL formatting
        self.assertEqual(social_links['github']['url'], 'https://github.com/testuser')
    
    def test_guest_author_functionality(self):
        """Test guest author specific functionality."""
        profile = self.guest_user.author_profile
        profile.is_guest_author = True
        profile.guest_author_email = 'guest@company.com'
        profile.guest_author_company = 'Tech Company'
        profile.save()
        
        self.assertTrue(profile.is_guest_author)
        self.assertEqual(profile.get_contact_email(), 'guest@company.com')
        
        # Test without guest email
        profile.guest_author_email = ''
        profile.save()
        self.assertEqual(profile.get_contact_email(), 'guest@example.com')
    
    def test_get_post_count(self):
        """Test the get_post_count method."""
        profile = self.user.author_profile
        
        # No posts
        self.assertEqual(profile.get_post_count(), 0)
        
        # Create some posts
        category = Category.objects.create(name='Test Category', slug='test-category')
        
        # Published post
        Post.objects.create(
            title='Published Post',
            slug='published-post',
            author=self.user,
            content='Test content',
            status='published'
        )
        
        # Draft post (shouldn't count)
        Post.objects.create(
            title='Draft Post',
            slug='draft-post',
            author=self.user,
            content='Test content',
            status='draft'
        )
        
        self.assertEqual(profile.get_post_count(), 1)


class AuthorServiceTest(TestCase):
    """Test cases for the AuthorService."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testauthor',
            email='test@example.com',
            first_name='Test',
            last_name='Author'
        )
        
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        
        # Create some posts
        for i in range(3):
            Post.objects.create(
                title=f'Test Post {i+1}',
                slug=f'test-post-{i+1}',
                author=self.user,
                content='Test content',
                status='published'
            )
    
    def test_get_author_profile(self):
        """Test getting or creating author profile."""
        profile = AuthorService.get_author_profile(self.user)
        self.assertIsInstance(profile, AuthorProfile)
        self.assertEqual(profile.user, self.user)
    
    def test_get_author_posts(self):
        """Test getting author posts."""
        posts = AuthorService.get_author_posts(self.user)
        self.assertEqual(posts.count(), 3)
        
        # Test with limit
        limited_posts = AuthorService.get_author_posts(self.user, limit=2)
        self.assertEqual(len(limited_posts), 2)
        
        # Test with status filter
        draft_posts = AuthorService.get_author_posts(self.user, status='draft')
        self.assertEqual(draft_posts.count(), 0)
    
    def test_get_all_active_authors(self):
        """Test getting all active authors."""
        authors = AuthorService.get_all_active_authors()
        self.assertEqual(authors.count(), 1)
        self.assertEqual(authors.first(), self.user)
        
        # Deactivate author
        profile = self.user.author_profile
        profile.is_active = False
        profile.save()
        
        authors = AuthorService.get_all_active_authors()
        self.assertEqual(authors.count(), 0)
    
    def test_create_guest_author(self):
        """Test creating a guest author."""
        user, profile = AuthorService.create_guest_author(
            username='guestwriter',
            email='guest@example.com',
            first_name='Guest',
            last_name='Writer',
            bio='Guest author bio',
            website='https://guestsite.com'
        )
        
        self.assertIsInstance(user, User)
        self.assertIsInstance(profile, AuthorProfile)
        self.assertTrue(profile.is_guest_author)
        self.assertEqual(profile.bio, 'Guest author bio')
        self.assertEqual(profile.website, 'https://guestsite.com')
        self.assertEqual(profile.guest_author_email, 'guest@example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_update_author_profile(self):
        """Test updating author profile."""
        profile = AuthorService.update_author_profile(
            self.user,
            bio='Updated bio',
            website='https://updated.com'
        )
        
        self.assertEqual(profile.bio, 'Updated bio')
        self.assertEqual(profile.website, 'https://updated.com')
    
    def test_get_author_stats(self):
        """Test getting author statistics."""
        stats = AuthorService.get_author_stats(self.user)
        
        self.assertEqual(stats['total_posts'], 3)
        self.assertEqual(stats['total_views'], 0)  # No views yet
        self.assertEqual(stats['total_comments'], 0)  # No comments yet
        self.assertIsNotNone(stats['latest_post'])
        self.assertIsNotNone(stats['most_viewed_post'])
    
    def test_search_authors(self):
        """Test searching authors."""
        # Search by first name
        results = AuthorService.search_authors('Test')
        self.assertEqual(results.count(), 1)
        
        # Search by username
        results = AuthorService.search_authors('testauthor')
        self.assertEqual(results.count(), 1)
        
        # Search with no results
        results = AuthorService.search_authors('nonexistent')
        self.assertEqual(results.count(), 0)


class AuthorViewsTest(TestCase):
    """Test cases for author-related views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testauthor',
            email='test@example.com',
            first_name='Test',
            last_name='Author'
        )
        
        self.guest_user = User.objects.create_user(
            username='guestauthor',
            email='guest@example.com',
            first_name='Guest',
            last_name='Writer'
        )
        
        # Set up guest author
        guest_profile = self.guest_user.author_profile
        guest_profile.is_guest_author = True
        guest_profile.guest_author_company = 'Tech Company'
        guest_profile.bio = 'Guest author bio'
        guest_profile.save()
        
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        
        # Create some posts
        for i in range(5):
            Post.objects.create(
                title=f'Test Post {i+1}',
                slug=f'test-post-{i+1}',
                author=self.user,
                content='Test content',
                status='published'
            )
        
        # Create a post in specific category
        Post.objects.create(
            title='Category Post',
            slug='category-post',
            author=self.user,
            content='Test content',
            status='published'
        ).categories.add(self.category)
    
    def test_author_list_view(self):
        """Test the author list view."""
        response = self.client.get(reverse('blog:author_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Author')
        self.assertContains(response, 'Guest Writer')
        self.assertContains(response, 'Our Authors')
    
    def test_author_list_search(self):
        """Test author list search functionality."""
        response = self.client.get(reverse('blog:author_list'), {'q': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Author')
        self.assertNotContains(response, 'Guest Writer')
    
    def test_author_list_filter_by_type(self):
        """Test author list filtering by type."""
        # Filter for guest authors
        response = self.client.get(reverse('blog:author_list'), {'type': 'guest'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Guest Writer')
        self.assertNotContains(response, 'Test Author')
        
        # Filter for staff authors
        response = self.client.get(reverse('blog:author_list'), {'type': 'staff'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Author')
        self.assertNotContains(response, 'Guest Writer')
    
    def test_author_detail_view(self):
        """Test the author detail view."""
        response = self.client.get(reverse('blog:author_detail', kwargs={'username': 'testauthor'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Author')
        self.assertContains(response, 'Test Post 1')
        self.assertContains(response, '5 articles published')
    
    def test_author_detail_inactive_author(self):
        """Test author detail view for inactive author."""
        profile = self.user.author_profile
        profile.is_active = False
        profile.save()
        
        response = self.client.get(reverse('blog:author_detail', kwargs={'username': 'testauthor'}))
        self.assertEqual(response.status_code, 302)  # Should redirect
    
    def test_author_posts_by_category_view(self):
        """Test the author posts by category view."""
        response = self.client.get(reverse('blog:author_posts_by_category', kwargs={
            'username': 'testauthor',
            'category_slug': 'test-category'
        }))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Author')
        self.assertContains(response, 'Test Category')
        self.assertContains(response, 'Category Post')
        self.assertContains(response, '1 article in Test Category')
    
    def test_author_detail_nonexistent_user(self):
        """Test author detail view for nonexistent user."""
        response = self.client.get(reverse('blog:author_detail', kwargs={'username': 'nonexistent'}))
        self.assertEqual(response.status_code, 404)
    
    def test_author_posts_by_category_nonexistent_category(self):
        """Test author posts by category view for nonexistent category."""
        response = self.client.get(reverse('blog:author_posts_by_category', kwargs={
            'username': 'testauthor',
            'category_slug': 'nonexistent'
        }))
        self.assertEqual(response.status_code, 404)


class AuthorProfileIntegrationTest(TestCase):
    """Integration tests for the author profile system."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testauthor',
            email='test@example.com',
            first_name='Test',
            last_name='Author'
        )
        
        # Update profile with social links
        profile = self.user.author_profile
        profile.bio = 'Test author biography'
        profile.website = 'https://testauthor.com'
        profile.twitter = 'testauthor'
        profile.linkedin = 'https://linkedin.com/in/testauthor'
        profile.save()
        
        self.category = Category.objects.create(name='Tech', slug='tech')
        self.tag = Tag.objects.create(name='Python', slug='python', color='#3776ab')
        
        # Create a post
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='Test content',
            excerpt='Test excerpt',
            status='published'
        )
        self.post.categories.add(self.category)
        self.post.tags.add(self.tag)
    
    def test_author_bio_widget_in_post_detail(self):
        """Test that author bio widget appears in post detail."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': 'test-post'}))
        self.assertEqual(response.status_code, 200)
        
        # Check for author bio widget elements
        self.assertContains(response, 'Test Author')
        self.assertContains(response, 'Test author biography')
        self.assertContains(response, 'https://testauthor.com')
        self.assertContains(response, 'twitter.com/testauthor')
        self.assertContains(response, 'View all posts by Test Author')
    
    def test_author_profile_links_navigation(self):
        """Test navigation between author profile and posts."""
        # Visit author detail page
        response = self.client.get(reverse('blog:author_detail', kwargs={'username': 'testauthor'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Post')
        
        # Visit post detail and check author link
        response = self.client.get(reverse('blog:detail', kwargs={'slug': 'test-post'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('blog:author_detail', kwargs={'username': 'testauthor'}))
    
    def test_guest_author_display(self):
        """Test guest author display functionality."""
        # Create guest author
        guest_user, guest_profile = AuthorService.create_guest_author(
            username='guestwriter',
            email='guest@company.com',
            first_name='Guest',
            last_name='Writer',
            bio='Guest author from external company',
            guest_author_company='External Corp'
        )
        
        # Create post by guest author
        guest_post = Post.objects.create(
            title='Guest Post',
            slug='guest-post',
            author=guest_user,
            content='Guest content',
            status='published'
        )
        
        # Check post detail shows guest author info
        response = self.client.get(reverse('blog:detail', kwargs={'slug': 'guest-post'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Guest Writer')
        self.assertContains(response, 'External Corp')
        self.assertContains(response, 'Guest Author')
        
        # Check author detail page
        response = self.client.get(reverse('blog:author_detail', kwargs={'username': 'guestwriter'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Guest Author')
        self.assertContains(response, 'External Corp')