"""
Comprehensive unit tests for all blog models and their methods.
This file provides complete test coverage for all model functionality.
"""
import secrets
import hashlib
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta
from .models import (
    Category, Tag, Post, NewsletterSubscriber, Comment, 
    SocialShare, AuthorProfile, MediaItem
)


class CategoryModelTest(TestCase):
    """Test cases for Category model"""
    
    def setUp(self):
        self.parent_category = Category.objects.create(
            name='Technology',
            slug='technology'
        )
    
    def test_category_creation(self):
        """Test basic category creation"""
        category = Category.objects.create(name='Python')
        self.assertEqual(category.name, 'Python')
        self.assertEqual(category.slug, 'python')  # Auto-generated
        self.assertIsNone(category.parent)
    
    def test_category_slug_auto_generation(self):
        """Test automatic slug generation"""
        category = Category.objects.create(name='Machine Learning & AI')
        self.assertEqual(category.slug, 'machine-learning-ai')
    
    def test_category_with_parent(self):
        """Test subcategory creation"""
        subcategory = Category.objects.create(
            name='Django',
            parent=self.parent_category
        )
        self.assertEqual(subcategory.parent, self.parent_category)
        self.assertIn(subcategory, self.parent_category.subcategories.all())
    
    def test_category_string_representation(self):
        """Test __str__ method"""
        category = Category.objects.create(name='Web Development')
        self.assertEqual(str(category), 'Web Development')
    
    def test_category_unique_constraint(self):
        """Test unique constraint on name"""
        # Create first category with name 'Basics'
        Category.objects.create(name='Basics', parent=self.parent_category)
        
        # Same name should fail due to unique constraint on name field
        with self.assertRaises(IntegrityError):
            Category.objects.create(name='Basics')  # Should fail due to unique name


class TagModelTest(TestCase):
    """Test cases for Tag model"""
    
    def test_tag_creation(self):
        """Test basic tag creation"""
        tag = Tag.objects.create(
            name='Python',
            color='#3776ab',
            description='Python programming language'
        )
        self.assertEqual(tag.name, 'Python')
        self.assertEqual(tag.slug, 'python')  # Auto-generated
        self.assertEqual(tag.color, '#3776ab')
        self.assertEqual(tag.description, 'Python programming language')
    
    def test_tag_slug_auto_generation(self):
        """Test automatic slug generation"""
        tag = Tag.objects.create(name='Machine Learning')
        self.assertEqual(tag.slug, 'machine-learning')
    
    def test_tag_default_color(self):
        """Test default color assignment"""
        tag = Tag.objects.create(name='Django')
        self.assertEqual(tag.color, '#007acc')
    
    def test_tag_string_representation(self):
        """Test __str__ method"""
        tag = Tag.objects.create(name='Web Development')
        self.assertEqual(str(tag), 'Web Development')
    
    def test_get_post_count(self):
        """Test get_post_count method"""
        user = User.objects.create_user('testuser', 'test@example.com')
        tag = Tag.objects.create(name='Python')
        
        # Create published post
        post1 = Post.objects.create(
            title='Python Tutorial',
            author=user,
            content='Content',
            status='published'
        )
        post1.tags.add(tag)
        
        # Create draft post
        post2 = Post.objects.create(
            title='Python Draft',
            author=user,
            content='Content',
            status='draft'
        )
        post2.tags.add(tag)
        
        # Should only count published posts
        self.assertEqual(tag.get_post_count(), 1)


class PostModelTest(TestCase):
    """Test cases for Post model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.category = Category.objects.create(name='Technology')
        self.tag = Tag.objects.create(name='Python')
    
    def test_post_creation(self):
        """Test basic post creation"""
        post = Post.objects.create(
            title='Test Post',
            author=self.user,
            content='This is test content',
            excerpt='Test excerpt',
            status='published'
        )
        self.assertEqual(post.title, 'Test Post')
        self.assertEqual(post.slug, 'test-post')  # Auto-generated
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.status, 'published')
        self.assertTrue(post.allow_comments)  # Default
        self.assertTrue(post.table_of_contents)  # Default
        self.assertFalse(post.is_featured)  # Default
    
    def test_post_slug_auto_generation(self):
        """Test automatic slug generation"""
        post = Post.objects.create(
            title='How to Learn Python Programming',
            author=self.user,
            content='Content'
        )
        self.assertEqual(post.slug, 'how-to-learn-python-programming')
    
    def test_post_with_relationships(self):
        """Test post with categories and tags"""
        post = Post.objects.create(
            title='Python Tutorial',
            author=self.user,
            content='Content',
            status='published'
        )
        post.categories.add(self.category)
        post.tags.add(self.tag)
        
        self.assertIn(self.category, post.categories.all())
        self.assertIn(self.tag, post.tags.all())
    
    def test_post_string_representation(self):
        """Test __str__ method"""
        post = Post.objects.create(
            title='Test Post',
            author=self.user,
            content='Content'
        )
        self.assertEqual(str(post), 'Test Post')
    
    def test_get_reading_time(self):
        """Test reading time calculation"""
        # Short content
        short_post = Post.objects.create(
            title='Short Post',
            author=self.user,
            content='Short content'
        )
        self.assertEqual(short_post.get_reading_time(), 1)  # Minimum 1 minute
        
        # Long content
        long_content = ' '.join(['word'] * 400)  # ~400 words
        long_post = Post.objects.create(
            title='Long Post',
            author=self.user,
            content=long_content
        )
        # Should be around 2 minutes (400 words / 200 wpm)
        self.assertGreaterEqual(long_post.get_reading_time(), 2)


class NewsletterSubscriberModelTest(TestCase):
    """Test cases for NewsletterSubscriber model"""
    
    def test_subscriber_creation(self):
        """Test basic subscriber creation"""
        subscriber = NewsletterSubscriber.objects.create(
            email='test@example.com'
        )
        self.assertEqual(subscriber.email, 'test@example.com')
        self.assertFalse(subscriber.is_confirmed)  # Default
        self.assertTrue(subscriber.confirmation_token)  # Auto-generated
        self.assertTrue(subscriber.unsubscribe_token)  # Auto-generated
        self.assertIsNone(subscriber.confirmed_at)
    
    def test_token_generation(self):
        """Test automatic token generation"""
        subscriber = NewsletterSubscriber.objects.create(
            email='test@example.com'
        )
        self.assertEqual(len(subscriber.confirmation_token), 64)  # SHA256 hex
        self.assertEqual(len(subscriber.unsubscribe_token), 64)  # SHA256 hex
        self.assertNotEqual(subscriber.confirmation_token, subscriber.unsubscribe_token)
    
    def test_token_uniqueness(self):
        """Test that tokens are unique"""
        subscriber1 = NewsletterSubscriber.objects.create(email='test1@example.com')
        subscriber2 = NewsletterSubscriber.objects.create(email='test2@example.com')
        
        self.assertNotEqual(subscriber1.confirmation_token, subscriber2.confirmation_token)
        self.assertNotEqual(subscriber1.unsubscribe_token, subscriber2.unsubscribe_token)
    
    def test_email_uniqueness(self):
        """Test email uniqueness constraint"""
        NewsletterSubscriber.objects.create(email='test@example.com')
        
        with self.assertRaises(IntegrityError):
            NewsletterSubscriber.objects.create(email='test@example.com')
    
    def test_string_representation(self):
        """Test __str__ method"""
        # Unconfirmed subscriber
        subscriber = NewsletterSubscriber.objects.create(email='test@example.com')
        self.assertEqual(str(subscriber), 'test@example.com ?')
        
        # Confirmed subscriber
        subscriber.is_confirmed = True
        subscriber.save()
        self.assertEqual(str(subscriber), 'test@example.com ✓')
    
    def test_generate_token_method(self):
        """Test _generate_token method"""
        subscriber = NewsletterSubscriber()
        token = subscriber._generate_token()
        self.assertEqual(len(token), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in token))


class CommentModelTest(TestCase):
    """Test cases for Comment model"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com')
        self.post = Post.objects.create(
            title='Test Post',
            author=self.user,
            content='Content',
            status='published'
        )
    
    def test_comment_creation(self):
        """Test basic comment creation"""
        comment = Comment.objects.create(
            post=self.post,
            author_name='John Doe',
            author_email='john@example.com',
            author_website='https://johndoe.com',
            content='Great post!',
            ip_address='127.0.0.1'
        )
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.author_name, 'John Doe')
        self.assertEqual(comment.author_email, 'john@example.com')
        self.assertEqual(comment.author_website, 'https://johndoe.com')
        self.assertEqual(comment.content, 'Great post!')
        self.assertFalse(comment.is_approved)  # Default
        self.assertIsNone(comment.parent)  # Top-level comment
    
    def test_comment_reply(self):
        """Test comment reply functionality"""
        parent_comment = Comment.objects.create(
            post=self.post,
            author_name='John Doe',
            author_email='john@example.com',
            content='Great post!',
            ip_address='127.0.0.1'
        )
        
        reply = Comment.objects.create(
            post=self.post,
            parent=parent_comment,
            author_name='Jane Smith',
            author_email='jane@example.com',
            content='I agree!',
            ip_address='127.0.0.1'
        )
        
        self.assertEqual(reply.parent, parent_comment)
        self.assertTrue(reply.is_reply())
        self.assertFalse(parent_comment.is_reply())
    
    def test_get_replies(self):
        """Test get_replies method"""
        parent_comment = Comment.objects.create(
            post=self.post,
            author_name='John Doe',
            author_email='john@example.com',
            content='Great post!',
            is_approved=True,
            ip_address='127.0.0.1'
        )
        
        # Create approved reply
        reply1 = Comment.objects.create(
            post=self.post,
            parent=parent_comment,
            author_name='Jane Smith',
            author_email='jane@example.com',
            content='I agree!',
            is_approved=True,
            ip_address='127.0.0.1'
        )
        
        # Create unapproved reply
        reply2 = Comment.objects.create(
            post=self.post,
            parent=parent_comment,
            author_name='Spam User',
            author_email='spam@example.com',
            content='Spam content',
            is_approved=False,
            ip_address='127.0.0.1'
        )
        
        replies = parent_comment.get_replies()
        self.assertEqual(replies.count(), 1)  # Only approved replies
        self.assertIn(reply1, replies)
        self.assertNotIn(reply2, replies)
    
    def test_string_representation(self):
        """Test __str__ method"""
        comment = Comment.objects.create(
            post=self.post,
            author_name='John Doe',
            author_email='john@example.com',
            content='Great post!',
            ip_address='127.0.0.1'
        )
        expected = f"Comment by John Doe on {self.post.title}"
        self.assertEqual(str(comment), expected)


class SocialShareModelTest(TestCase):
    """Test cases for SocialShare model"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com')
        self.post = Post.objects.create(
            title='Test Post',
            author=self.user,
            content='Content',
            status='published'
        )
    
    def test_social_share_creation(self):
        """Test basic social share creation"""
        share = SocialShare.objects.create(
            post=self.post,
            platform='facebook',
            share_count=5
        )
        self.assertEqual(share.post, self.post)
        self.assertEqual(share.platform, 'facebook')
        self.assertEqual(share.share_count, 5)
    
    def test_increment_share_count(self):
        """Test increment_share_count method"""
        share = SocialShare.objects.create(
            post=self.post,
            platform='twitter',
            share_count=3
        )
        
        original_count = share.share_count
        share.increment_share_count()
        
        share.refresh_from_db()
        self.assertEqual(share.share_count, original_count + 1)
    
    def test_unique_together_constraint(self):
        """Test unique constraint on post and platform"""
        SocialShare.objects.create(
            post=self.post,
            platform='facebook',
            share_count=1
        )
        
        # Should not be able to create another share for same post/platform
        with self.assertRaises(IntegrityError):
            SocialShare.objects.create(
                post=self.post,
                platform='facebook',
                share_count=2
            )
    
    def test_string_representation(self):
        """Test __str__ method"""
        share = SocialShare.objects.create(
            post=self.post,
            platform='facebook',
            share_count=5
        )
        expected = f"{self.post.title} shared on Facebook (5 times)"
        self.assertEqual(str(share), expected)


class AuthorProfileModelTest(TestCase):
    """Test cases for AuthorProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='John',
            last_name='Doe'
        )
    
    def test_author_profile_creation(self):
        """Test author profile creation"""
        # Profile should be created automatically via signals
        self.assertTrue(hasattr(self.user, 'author_profile'))
        profile = self.user.author_profile
        
        # Update profile with test data
        profile.bio = 'Test author bio'
        profile.website = 'https://johndoe.com'
        profile.twitter = 'johndoe'
        profile.linkedin = 'https://linkedin.com/in/johndoe'
        profile.github = 'johndoe'
        profile.save()
        
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.bio, 'Test author bio')
        self.assertEqual(profile.website, 'https://johndoe.com')
        self.assertFalse(profile.is_guest_author)  # Default
        self.assertTrue(profile.is_active)  # Default
    
    def test_get_display_name(self):
        """Test get_display_name method"""
        profile = self.user.author_profile
        
        # With first and last name
        self.assertEqual(profile.get_display_name(), 'John Doe')
        
        # With only first name
        self.user.last_name = ''
        self.user.save()
        self.assertEqual(profile.get_display_name(), 'John')
        
        # With no names
        self.user.first_name = ''
        self.user.save()
        self.assertEqual(profile.get_display_name(), 'testuser')
    
    def test_get_short_bio(self):
        """Test get_short_bio method"""
        profile = self.user.author_profile
        
        # No bio
        self.assertEqual(profile.get_short_bio(), "")
        
        # Short bio
        profile.bio = "This is a short bio."
        profile.save()
        self.assertEqual(profile.get_short_bio(), "This is a short bio.")
        
        # Long bio
        long_bio = "This is a very long bio that should be truncated. " * 10
        profile.bio = long_bio
        profile.save()
        short_bio = profile.get_short_bio(max_length=50)
        self.assertTrue(len(short_bio) <= 53)  # 50 + '...'
        self.assertTrue(short_bio.endswith('...'))
    
    def test_get_social_links(self):
        """Test get_social_links method"""
        profile = self.user.author_profile
        profile.website = 'https://johndoe.com'
        profile.twitter = '@johndoe'
        profile.linkedin = 'https://linkedin.com/in/johndoe'
        profile.github = 'johndoe'
        profile.instagram = 'johndoe'
        profile.save()
        
        social_links = profile.get_social_links()
        
        self.assertIn('website', social_links)
        self.assertIn('twitter', social_links)
        self.assertIn('linkedin', social_links)
        self.assertIn('github', social_links)
        self.assertIn('instagram', social_links)
        
        # Check URL formatting
        self.assertEqual(social_links['twitter']['url'], 'https://twitter.com/johndoe')
        self.assertEqual(social_links['github']['url'], 'https://github.com/johndoe')
    
    def test_get_post_count(self):
        """Test get_post_count method"""
        profile = self.user.author_profile
        
        # No posts
        self.assertEqual(profile.get_post_count(), 0)
        
        # Create published post
        Post.objects.create(
            title='Published Post',
            author=self.user,
            content='Content',
            status='published'
        )
        
        # Create draft post
        Post.objects.create(
            title='Draft Post',
            author=self.user,
            content='Content',
            status='draft'
        )
        
        # Should only count published posts
        self.assertEqual(profile.get_post_count(), 1)
    
    def test_get_contact_email(self):
        """Test get_contact_email method"""
        profile = self.user.author_profile
        
        # Regular author
        self.assertEqual(profile.get_contact_email(), 'test@example.com')
        
        # Guest author with separate email
        profile.is_guest_author = True
        profile.guest_author_email = 'guest@company.com'
        profile.save()
        self.assertEqual(profile.get_contact_email(), 'guest@company.com')
    
    def test_string_representation(self):
        """Test __str__ method"""
        profile = self.user.author_profile
        self.assertEqual(str(profile), 'John Doe - Author Profile')


class MediaItemModelTest(TestCase):
    """Test cases for MediaItem model"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com')
        self.post = Post.objects.create(
            title='Test Post',
            author=self.user,
            content='Content',
            status='published'
        )
    
    def test_image_media_item_creation(self):
        """Test creating image media item"""
        media_item = MediaItem.objects.create(
            post=self.post,
            media_type='image',
            title='Test Image',
            description='A test image',
            alt_text='Test image alt text',
            width=800,
            height=600,
            file_size=1024
        )
        self.assertEqual(media_item.post, self.post)
        self.assertEqual(media_item.media_type, 'image')
        self.assertEqual(media_item.title, 'Test Image')
        self.assertEqual(media_item.width, 800)
        self.assertEqual(media_item.height, 600)
    
    def test_video_media_item_creation(self):
        """Test creating video media item"""
        media_item = MediaItem.objects.create(
            post=self.post,
            media_type='video',
            title='Test Video',
            video_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            video_platform='youtube',
            video_id='dQw4w9WgXcQ',
            video_embed_url='https://www.youtube.com/embed/dQw4w9WgXcQ'
        )
        self.assertEqual(media_item.media_type, 'video')
        self.assertEqual(media_item.video_platform, 'youtube')
        self.assertEqual(media_item.video_id, 'dQw4w9WgXcQ')
    
    def test_gallery_media_item_creation(self):
        """Test creating gallery media item"""
        gallery_data = [
            {'id': 0, 'title': 'Image 1', 'original': 'image1.jpg'},
            {'id': 1, 'title': 'Image 2', 'original': 'image2.jpg'}
        ]
        
        media_item = MediaItem.objects.create(
            post=self.post,
            media_type='gallery',
            title='Test Gallery',
            gallery_images=gallery_data
        )
        self.assertEqual(media_item.media_type, 'gallery')
        self.assertEqual(len(media_item.gallery_images), 2)
    
    def test_get_video_embed_code(self):
        """Test get_video_embed_code method"""
        media_item = MediaItem.objects.create(
            post=self.post,
            media_type='video',
            title='Test Video',
            video_embed_url='https://www.youtube.com/embed/dQw4w9WgXcQ'
        )
        
        embed_code = media_item.get_video_embed_code()
        self.assertIsNotNone(embed_code)
        self.assertIn('iframe', embed_code)
        self.assertIn('https://www.youtube.com/embed/dQw4w9WgXcQ', embed_code)
    
    def test_get_responsive_images(self):
        """Test get_responsive_images method"""
        media_item = MediaItem.objects.create(
            post=self.post,
            media_type='image',
            title='Test Image'
        )
        
        responsive_images = media_item.get_responsive_images()
        self.assertIsInstance(responsive_images, dict)
    
    def test_string_representation(self):
        """Test __str__ method"""
        media_item = MediaItem.objects.create(
            post=self.post,
            media_type='image',
            title='Test Image'
        )
        self.assertEqual(str(media_item), 'Image for Test Post')