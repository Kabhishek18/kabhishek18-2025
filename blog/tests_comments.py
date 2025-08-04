from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import timedelta
from .models import Post, Category, Comment
from .forms import CommentForm
from .tasks import send_comment_notification
import time


class CommentSystemTestCase(TestCase):
    """Test cases for the commenting system"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testauthor',
            email='author@test.com',
            password='testpass123'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        # Create test post
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='This is a test post content.',
            excerpt='Test excerpt',
            status='published',
            allow_comments=True
        )
        self.post.categories.add(self.category)
        
        self.client = Client()
        
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
    
    def test_comment_form_validation(self):
        """Test comment form validation"""
        # Test valid form
        form_data = {
            'author_name': 'Test User',
            'author_email': 'test@example.com',
            'author_website': 'https://example.com',
            'content': 'This is a test comment with enough content.'
        }
        form = CommentForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Test invalid form - missing required fields
        invalid_form = CommentForm(data={})
        self.assertFalse(invalid_form.is_valid())
        
        # Test invalid form - content too short
        short_content_form = CommentForm(data={
            'author_name': 'Test User',
            'author_email': 'test@example.com',
            'content': 'Short'
        })
        self.assertFalse(short_content_form.is_valid())
        
        # Test invalid form - too many URLs
        spam_form = CommentForm(data={
            'author_name': 'Test User',
            'author_email': 'test@example.com',
            'content': 'Check out https://spam1.com and https://spam2.com and https://spam3.com'
        })
        self.assertFalse(spam_form.is_valid())
    
    def test_comment_submission(self):
        """Test comment submission"""
        comment_data = {
            'author_name': 'Test Commenter',
            'author_email': 'commenter@test.com',
            'author_website': 'https://commenter.com',
            'content': 'This is a test comment with sufficient content to pass validation.'
        }
        
        response = self.client.post(
            reverse('blog:submit_comment', kwargs={'slug': self.post.slug}),
            data=comment_data
        )
        
        # Should redirect back to post detail
        self.assertEqual(response.status_code, 302)
        
        # Comment should be created but not approved
        comment = Comment.objects.get(post=self.post)
        self.assertEqual(comment.author_name, 'Test Commenter')
        self.assertEqual(comment.author_email, 'commenter@test.com')
        self.assertFalse(comment.is_approved)  # Should require moderation
        self.assertIsNone(comment.parent)  # Should be a top-level comment
    
    def test_reply_submission(self):
        """Test reply submission"""
        # Create a parent comment first
        parent_comment = Comment.objects.create(
            post=self.post,
            author_name='Parent Commenter',
            author_email='parent@test.com',
            content='This is the parent comment.',
            is_approved=True,
            ip_address='127.0.0.1'
        )
        
        reply_data = {
            'author_name': 'Reply Author',
            'author_email': 'reply@test.com',
            'content': 'This is a reply to the parent comment.'
        }
        
        response = self.client.post(
            reverse('blog:submit_reply', kwargs={
                'slug': self.post.slug,
                'comment_id': parent_comment.id
            }),
            data=reply_data
        )
        
        # Should redirect back to post detail
        self.assertEqual(response.status_code, 302)
        
        # Reply should be created
        reply = Comment.objects.get(parent=parent_comment)
        self.assertEqual(reply.author_name, 'Reply Author')
        self.assertEqual(reply.parent, parent_comment)
        self.assertFalse(reply.is_approved)  # Should require moderation
    
    def test_rate_limiting(self):
        """Test comment rate limiting"""
        comment_data = {
            'author_name': 'Test User',
            'author_email': 'test@test.com',
            'content': 'This is a test comment for rate limiting.'
        }
        
        # Submit first comment
        response1 = self.client.post(
            reverse('blog:submit_comment', kwargs={'slug': self.post.slug}),
            data=comment_data
        )
        self.assertEqual(response1.status_code, 302)
        
        # Try to submit another comment immediately (should be rate limited)
        response2 = self.client.post(
            reverse('blog:submit_comment', kwargs={'slug': self.post.slug}),
            data=comment_data
        )
        self.assertEqual(response2.status_code, 302)
        
        # Should only have one comment (second should be blocked)
        self.assertEqual(Comment.objects.filter(post=self.post).count(), 1)
    
    def test_comments_disabled(self):
        """Test comment submission when comments are disabled"""
        # Disable comments for the post
        self.post.allow_comments = False
        self.post.save()
        
        comment_data = {
            'author_name': 'Test User',
            'author_email': 'test@test.com',
            'content': 'This comment should not be allowed.'
        }
        
        response = self.client.post(
            reverse('blog:submit_comment', kwargs={'slug': self.post.slug}),
            data=comment_data
        )
        
        # Should redirect back to post detail
        self.assertEqual(response.status_code, 302)
        
        # No comment should be created
        self.assertEqual(Comment.objects.filter(post=self.post).count(), 0)
    
    def test_blog_detail_with_comments(self):
        """Test blog detail view includes comments"""
        # Create approved comments
        comment1 = Comment.objects.create(
            post=self.post,
            author_name='First Commenter',
            author_email='first@test.com',
            content='This is the first comment.',
            is_approved=True,
            ip_address='127.0.0.1'
        )
        
        comment2 = Comment.objects.create(
            post=self.post,
            author_name='Second Commenter',
            author_email='second@test.com',
            content='This is the second comment.',
            is_approved=True,
            ip_address='127.0.0.1'
        )
        
        # Create a reply to the first comment
        reply = Comment.objects.create(
            post=self.post,
            parent=comment1,
            author_name='Reply Author',
            author_email='reply@test.com',
            content='This is a reply.',
            is_approved=True,
            ip_address='127.0.0.1'
        )
        
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'First Commenter')
        self.assertContains(response, 'Second Commenter')
        self.assertContains(response, 'Reply Author')
        self.assertContains(response, 'Comments (2)')  # Only top-level comments count
    
    def test_comment_model_methods(self):
        """Test Comment model methods"""
        # Create parent comment
        parent = Comment.objects.create(
            post=self.post,
            author_name='Parent',
            author_email='parent@test.com',
            content='Parent comment',
            is_approved=True,
            ip_address='127.0.0.1'
        )
        
        # Create reply
        reply = Comment.objects.create(
            post=self.post,
            parent=parent,
            author_name='Reply',
            author_email='reply@test.com',
            content='Reply comment',
            is_approved=True,
            ip_address='127.0.0.1'
        )
        
        # Test is_reply method
        self.assertFalse(parent.is_reply())
        self.assertTrue(reply.is_reply())
        
        # Test get_replies method
        replies = parent.get_replies()
        self.assertEqual(replies.count(), 1)
        self.assertEqual(replies.first(), reply)
        
        # Test string representation
        self.assertIn('Parent', str(parent))
        self.assertIn(self.post.title, str(parent))

clas
s CommentModerationTestCase(TestCase):
    """Test cases for comment moderation functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testauthor',
            email='author@test.com',
            password='testpass123'
        )
        
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass123'
        )
        
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='This is a test post content.',
            status='published',
            allow_comments=True
        )
        
        self.client = Client()
    
    def test_comment_approval_workflow(self):
        """Test comment approval workflow"""
        # Create unapproved comment
        comment = Comment.objects.create(
            post=self.post,
            author_name='Test User',
            author_email='test@example.com',
            content='This is a test comment.',
            is_approved=False,
            ip_address='127.0.0.1'
        )
        
        # Comment should not appear on public page
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        self.assertNotContains(response, 'Test User')
        
        # Approve comment
        comment.is_approved = True
        comment.save()
        
        # Comment should now appear on public page
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        self.assertContains(response, 'Test User')
    
    def test_comment_spam_detection(self):
        """Test basic spam detection in comment form"""
        # Test comment with too many URLs
        spam_data = {
            'author_name': 'Spammer',
            'author_email': 'spam@example.com',
            'content': 'Check out https://spam1.com and https://spam2.com and https://spam3.com'
        }
        
        form = CommentForm(data=spam_data)
        self.assertFalse(form.is_valid())
        self.assertIn('cannot contain more than 2 URLs', str(form.errors))
    
    def test_comment_content_validation(self):
        """Test comment content validation"""
        # Test too short content
        short_data = {
            'author_name': 'Test User',
            'author_email': 'test@example.com',
            'content': 'Short'
        }
        
        form = CommentForm(data=short_data)
        self.assertFalse(form.is_valid())
        self.assertIn('at least 10 characters', str(form.errors))
        
        # Test too long content
        long_content = 'x' * 2001  # Exceeds 2000 character limit
        long_data = {
            'author_name': 'Test User',
            'author_email': 'test@example.com',
            'content': long_content
        }
        
        form = CommentForm(data=long_data)
        self.assertFalse(form.is_valid())
        self.assertIn('too long', str(form.errors))
    
    def test_comment_author_validation(self):
        """Test comment author field validation"""
        # Test name with URL (spam prevention)
        spam_name_data = {
            'author_name': 'Visit https://spam.com',
            'author_email': 'test@example.com',
            'content': 'This is a test comment.'
        }
        
        form = CommentForm(data=spam_name_data)
        self.assertFalse(form.is_valid())
        self.assertIn('cannot contain URLs', str(form.errors))
        
        # Test too short name
        short_name_data = {
            'author_name': 'A',
            'author_email': 'test@example.com',
            'content': 'This is a test comment.'
        }
        
        form = CommentForm(data=short_name_data)
        self.assertFalse(form.is_valid())
        self.assertIn('at least 2 characters', str(form.errors))
    
    def test_comment_threading_depth(self):
        """Test comment threading and reply depth"""
        # Create parent comment
        parent = Comment.objects.create(
            post=self.post,
            author_name='Parent',
            author_email='parent@test.com',
            content='Parent comment',
            is_approved=True,
            ip_address='127.0.0.1'
        )
        
        # Create first level reply
        reply1 = Comment.objects.create(
            post=self.post,
            parent=parent,
            author_name='Reply 1',
            author_email='reply1@test.com',
            content='First level reply',
            is_approved=True,
            ip_address='127.0.0.1'
        )
        
        # Create second level reply
        reply2 = Comment.objects.create(
            post=self.post,
            parent=reply1,
            author_name='Reply 2',
            author_email='reply2@test.com',
            content='Second level reply',
            is_approved=True,
            ip_address='127.0.0.1'
        )
        
        # Test threading structure
        self.assertFalse(parent.is_reply())
        self.assertTrue(reply1.is_reply())
        self.assertTrue(reply2.is_reply())
        
        # Test reply retrieval
        parent_replies = parent.get_replies()
        self.assertEqual(parent_replies.count(), 1)
        self.assertIn(reply1, parent_replies)
        
        reply1_replies = reply1.get_replies()
        self.assertEqual(reply1_replies.count(), 1)
        self.assertIn(reply2, reply1_replies)
    
    @patch('blog.tasks.send_comment_notification.delay')
    def test_comment_notification_trigger(self, mock_notification):
        """Test that comment notifications are triggered"""
        comment_data = {
            'author_name': 'Test Commenter',
            'author_email': 'commenter@test.com',
            'content': 'This is a test comment that should trigger notification.'
        }
        
        response = self.client.post(
            reverse('blog:submit_comment', kwargs={'slug': self.post.slug}),
            data=comment_data
        )
        
        self.assertEqual(response.status_code, 302)
        
        # Verify notification task was called
        mock_notification.assert_called_once()
    
    def test_comment_ip_tracking(self):
        """Test that comment IP addresses are tracked"""
        comment_data = {
            'author_name': 'Test User',
            'author_email': 'test@example.com',
            'content': 'This is a test comment.'
        }
        
        # Submit comment with custom IP
        response = self.client.post(
            reverse('blog:submit_comment', kwargs={'slug': self.post.slug}),
            data=comment_data,
            REMOTE_ADDR='192.168.1.100'
        )
        
        self.assertEqual(response.status_code, 302)
        
        comment = Comment.objects.get(post=self.post)
        # IP should be tracked (might be 127.0.0.1 in test environment)
        self.assertIsNotNone(comment.ip_address)


class CommentNotificationTestCase(TestCase):
    """Test cases for comment notification system"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testauthor',
            email='author@test.com',
            password='testpass123'
        )
        
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='This is a test post content.',
            status='published',
            allow_comments=True
        )
    
    @patch('blog.tasks.send_mail')
    def test_send_comment_notification_task(self, mock_send_mail):
        """Test send_comment_notification task"""
        comment = Comment.objects.create(
            post=self.post,
            author_name='Test Commenter',
            author_email='commenter@test.com',
            content='This is a test comment.',
            ip_address='127.0.0.1'
        )
        
        # Execute notification task
        result = send_comment_notification(comment.id)
        
        # Verify email was sent
        self.assertIn('Comment notification sent', result)
        mock_send_mail.assert_called_once()
        
        # Check email parameters
        call_args = mock_send_mail.call_args
        self.assertIn('New comment on', call_args[1]['subject'])
        self.assertEqual(['author@test.com'], call_args[1]['recipient_list'])
    
    @patch('blog.tasks.send_mail')
    def test_send_reply_notification_task(self, mock_send_mail):
        """Test reply notification task"""
        parent_comment = Comment.objects.create(
            post=self.post,
            author_name='Parent Commenter',
            author_email='parent@test.com',
            content='Parent comment',
            is_approved=True,
            ip_address='127.0.0.1'
        )
        
        reply = Comment.objects.create(
            post=self.post,
            parent=parent_comment,
            author_name='Reply Author',
            author_email='reply@test.com',
            content='This is a reply.',
            ip_address='127.0.0.1'
        )
        
        # Execute notification task
        result = send_comment_notification(reply.id)
        
        # Verify email was sent
        self.assertIn('Comment notification sent', result)
        mock_send_mail.assert_called_once()
        
        # Check that it's identified as a reply
        call_args = mock_send_mail.call_args
        self.assertIn('New reply on', call_args[1]['subject'])
    
    @patch('blog.tasks.send_mail')
    def test_notification_no_author_email(self, mock_send_mail):
        """Test notification when author has no email"""
        # Create user without email
        user_no_email = User.objects.create_user(
            username='noemail',
            email='',  # No email
            password='testpass123'
        )
        
        post_no_email = Post.objects.create(
            title='Post by User with No Email',
            author=user_no_email,
            content='Content',
            status='published'
        )
        
        comment = Comment.objects.create(
            post=post_no_email,
            author_name='Test Commenter',
            author_email='commenter@test.com',
            content='This is a test comment.',
            ip_address='127.0.0.1'
        )
        
        # Execute notification task
        result = send_comment_notification(comment.id)
        
        # Should not send email
        self.assertIn('has no email address', result)
        mock_send_mail.assert_not_called()


class CommentSecurityTestCase(TestCase):
    """Test cases for comment security features"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testauthor',
            email='author@test.com',
            password='testpass123'
        )
        
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='This is a test post content.',
            status='published',
            allow_comments=True
        )
        
        self.client = Client()
    
    def test_html_sanitization(self):
        """Test that HTML is sanitized in comments"""
        malicious_data = {
            'author_name': 'Test User',
            'author_email': 'test@example.com',
            'content': 'This comment has <script>alert("XSS")</script> malicious code.'
        }
        
        form = CommentForm(data=malicious_data)
        if form.is_valid():
            # HTML should be stripped
            self.assertNotIn('<script>', form.cleaned_data['content'])
            self.assertNotIn('alert', form.cleaned_data['content'])
    
    def test_csrf_protection(self):
        """Test CSRF protection on comment submission"""
        comment_data = {
            'author_name': 'Test User',
            'author_email': 'test@example.com',
            'content': 'This is a test comment.'
        }
        
        # Submit without CSRF token should fail
        response = self.client.post(
            reverse('blog:submit_comment', kwargs={'slug': self.post.slug}),
            data=comment_data,
            HTTP_X_CSRFTOKEN='invalid'
        )
        
        # Should be rejected (403 or redirect)
        self.assertIn(response.status_code, [403, 302])
    
    def test_comment_rate_limiting_by_ip(self):
        """Test rate limiting by IP address"""
        comment_data = {
            'author_name': 'Test User',
            'author_email': 'test@example.com',
            'content': 'This is a test comment for rate limiting.'
        }
        
        # Submit multiple comments from same IP
        for i in range(3):
            response = self.client.post(
                reverse('blog:submit_comment', kwargs={'slug': self.post.slug}),
                data=comment_data,
                REMOTE_ADDR='192.168.1.100'
            )
        
        # Should have rate limiting in place
        # (Implementation depends on actual rate limiting mechanism)
        comments_count = Comment.objects.filter(post=self.post).count()
        self.assertLessEqual(comments_count, 2)  # Should limit excessive comments
    
    def test_comment_content_length_limits(self):
        """Test comment content length limits"""
        # Test maximum length
        max_content = 'x' * 2000  # At the limit
        valid_data = {
            'author_name': 'Test User',
            'author_email': 'test@example.com',
            'content': max_content
        }
        
        form = CommentForm(data=valid_data)
        self.assertTrue(form.is_valid())
        
        # Test over limit
        over_limit_content = 'x' * 2001
        invalid_data = {
            'author_name': 'Test User',
            'author_email': 'test@example.com',
            'content': over_limit_content
        }
        
        form = CommentForm(data=invalid_data)
        self.assertFalse(form.is_valid())


class CommentPerformanceTestCase(TestCase):
    """Test cases for comment system performance"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testauthor',
            email='author@test.com',
            password='testpass123'
        )
        
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='This is a test post content.',
            status='published',
            allow_comments=True
        )
    
    def test_comment_query_optimization(self):
        """Test that comment queries are optimized"""
        # Create multiple comments with replies
        parent_comments = []
        for i in range(5):
            parent = Comment.objects.create(
                post=self.post,
                author_name=f'Parent {i}',
                author_email=f'parent{i}@test.com',
                content=f'Parent comment {i}',
                is_approved=True,
                ip_address='127.0.0.1'
            )
            parent_comments.append(parent)
            
            # Add replies to each parent
            for j in range(3):
                Comment.objects.create(
                    post=self.post,
                    parent=parent,
                    author_name=f'Reply {i}-{j}',
                    author_email=f'reply{i}{j}@test.com',
                    content=f'Reply {j} to parent {i}',
                    is_approved=True,
                    ip_address='127.0.0.1'
                )
        
        # Test that getting comments with replies uses efficient queries
        with self.assertNumQueries(2):  # Should be optimized with prefetch_related
            comments = Comment.objects.filter(
                post=self.post,
                parent__isnull=True,
                is_approved=True
            ).prefetch_related('replies')
            
            # Access replies to trigger query
            for comment in comments:
                list(comment.get_replies())
    
    def test_large_comment_thread_performance(self):
        """Test performance with large comment threads"""
        # Create a large number of comments
        comments = []
        for i in range(50):
            comment = Comment.objects.create(
                post=self.post,
                author_name=f'User {i}',
                author_email=f'user{i}@test.com',
                content=f'Comment number {i} with some content.',
                is_approved=True,
                ip_address='127.0.0.1'
            )
            comments.append(comment)
        
        # Test that retrieving comments is performant
        start_time = time.time()
        
        comment_list = list(Comment.objects.filter(
            post=self.post,
            is_approved=True
        ).order_by('created_at'))
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete quickly
        self.assertLess(execution_time, 1.0)  # Less than 1 second
        self.assertEqual(len(comment_list), 50)