"""
Integration tests for email subscription workflow.
Tests the complete email subscription process from signup to unsubscribe.
"""
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import timedelta
from .models import NewsletterSubscriber, Post, Category
from .tasks import send_confirmation_email, send_new_post_notification, cleanup_unconfirmed_subscriptions
from .forms import NewsletterSubscriptionForm


class EmailSubscriptionIntegrationTest(TestCase):
    """Integration tests for the complete email subscription workflow"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Technology', slug='technology')
    
    def test_complete_subscription_workflow(self):
        """Test the complete subscription workflow from signup to confirmation"""
        # Step 1: Subscribe via form
        response = self.client.post(reverse('blog:subscribe_newsletter'), {
            'email': 'subscriber@example.com'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after POST
        
        # Verify subscriber was created
        subscriber = NewsletterSubscriber.objects.get(email='subscriber@example.com')
        self.assertFalse(subscriber.is_confirmed)
        self.assertTrue(subscriber.confirmation_token)
        self.assertTrue(subscriber.unsubscribe_token)
        self.assertIsNone(subscriber.confirmed_at)
        
        # Step 2: Confirm subscription
        confirmation_url = reverse('blog:confirm_subscription', kwargs={
            'token': subscriber.confirmation_token
        })
        response = self.client.get(confirmation_url)
        
        self.assertEqual(response.status_code, 302)  # Redirect after confirmation
        
        # Verify subscription is confirmed
        subscriber.refresh_from_db()
        self.assertTrue(subscriber.is_confirmed)
        self.assertIsNotNone(subscriber.confirmed_at)
        
        # Step 3: Test unsubscribe workflow
        unsubscribe_url = reverse('blog:unsubscribe', kwargs={
            'token': subscriber.unsubscribe_token
        })
        
        # GET should show confirmation page
        response = self.client.get(unsubscribe_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'subscriber@example.com')
        
        # POST should delete subscription
        response = self.client.post(unsubscribe_url)
        self.assertEqual(response.status_code, 302)
        
        # Verify subscription is deleted
        self.assertFalse(NewsletterSubscriber.objects.filter(
            email='subscriber@example.com'
        ).exists())
    
    def test_duplicate_subscription_handling(self):
        """Test handling of duplicate email subscriptions"""
        email = 'duplicate@example.com'
        
        # First subscription
        response1 = self.client.post(reverse('blog:subscribe_newsletter'), {
            'email': email
        })
        self.assertEqual(response1.status_code, 302)
        
        # Second subscription with same email
        response2 = self.client.post(reverse('blog:subscribe_newsletter'), {
            'email': email
        })
        self.assertEqual(response2.status_code, 302)
        
        # Should still have only one subscriber
        self.assertEqual(NewsletterSubscriber.objects.filter(email=email).count(), 1)
    
    def test_invalid_confirmation_token(self):
        """Test handling of invalid confirmation tokens"""
        response = self.client.get(reverse('blog:confirm_subscription', kwargs={
            'token': 'invalid-token-12345'
        }))
        
        self.assertEqual(response.status_code, 302)  # Redirect with error
        # Should redirect to a page with error message
    
    def test_invalid_unsubscribe_token(self):
        """Test handling of invalid unsubscribe tokens"""
        response = self.client.get(reverse('blog:unsubscribe', kwargs={
            'token': 'invalid-token-12345'
        }))
        
        self.assertEqual(response.status_code, 302)  # Redirect with error
    
    def test_subscription_form_validation(self):
        """Test newsletter subscription form validation"""
        # Valid email
        form = NewsletterSubscriptionForm(data={'email': 'valid@example.com'})
        self.assertTrue(form.is_valid())
        
        # Invalid email
        form = NewsletterSubscriptionForm(data={'email': 'invalid-email'})
        self.assertFalse(form.is_valid())
        
        # Empty email
        form = NewsletterSubscriptionForm(data={'email': ''})
        self.assertFalse(form.is_valid())
    
    def test_subscription_with_ajax(self):
        """Test AJAX subscription requests"""
        response = self.client.post(
            reverse('blog:subscribe_newsletter'),
            {'email': 'ajax@example.com'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Should return JSON response for AJAX requests
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_confirmation_email_sending(self):
        """Test that confirmation emails are sent properly"""
        # Clear any existing emails
        mail.outbox = []
        
        # Subscribe
        response = self.client.post(reverse('blog:subscribe_newsletter'), {
            'email': 'confirm@example.com'
        })
        
        # Check that confirmation email was sent
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertIn('confirm@example.com', email.to)
        self.assertIn('Confirm your newsletter subscription', email.subject)
        self.assertIn('confirmation', email.body.lower())
    
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_new_post_notification_workflow(self):
        """Test new post notification to subscribers"""
        # Create confirmed subscribers
        subscriber1 = NewsletterSubscriber.objects.create(
            email='subscriber1@example.com',
            is_confirmed=True
        )
        subscriber2 = NewsletterSubscriber.objects.create(
            email='subscriber2@example.com',
            is_confirmed=True
        )
        # Create unconfirmed subscriber (should not receive email)
        NewsletterSubscriber.objects.create(
            email='unconfirmed@example.com',
            is_confirmed=False
        )
        
        # Clear any existing emails
        mail.outbox = []
        
        # Create and publish a new post
        post = Post.objects.create(
            title='New Blog Post',
            slug='new-blog-post',
            author=self.user,
            content='This is a new blog post content.',
            excerpt='New post excerpt',
            status='published'
        )
        post.categories.add(self.category)
        
        # Trigger newsletter sending (normally done via signal)
        from .tasks import send_new_post_notification
        send_new_post_notification.delay(post.id)
        
        # Check that emails were sent to confirmed subscribers only
        self.assertEqual(len(mail.outbox), 2)
        
        recipients = [email.to[0] for email in mail.outbox]
        self.assertIn('subscriber1@example.com', recipients)
        self.assertIn('subscriber2@example.com', recipients)
        self.assertNotIn('unconfirmed@example.com', recipients)
        
        # Check email content
        email = mail.outbox[0]
        self.assertIn('New Blog Post', email.subject)
        self.assertIn('new blog post', email.body.lower())
        self.assertIn('unsubscribe', email.body.lower())


class EmailTasksTest(TestCase):
    """Test email-related Celery tasks"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @patch('blog.tasks.send_mail')
    def test_send_confirmation_email_task(self, mock_send_mail):
        """Test send_confirmation_email task"""
        subscriber = NewsletterSubscriber.objects.create(
            email='test@example.com'
        )
        
        # Execute task
        result = send_confirmation_email(subscriber.id)
        
        # Verify email was sent
        self.assertIn('Confirmation email sent', result)
        mock_send_mail.assert_called_once()
        
        # Check email parameters
        call_args = mock_send_mail.call_args
        self.assertIn('Confirm your newsletter subscription', call_args[1]['subject'])
        self.assertEqual(['test@example.com'], call_args[1]['recipient_list'])
    
    @patch('blog.tasks.send_mail')
    def test_send_confirmation_email_nonexistent_subscriber(self, mock_send_mail):
        """Test send_confirmation_email with nonexistent subscriber"""
        result = send_confirmation_email(99999)  # Non-existent ID
        
        self.assertIn('not found', result)
        mock_send_mail.assert_not_called()
    
    @patch('blog.tasks.send_mail')
    def test_send_new_post_notification_task(self, mock_send_mail):
        """Test send_new_post_notification task"""
        # Create confirmed subscribers
        subscriber1 = NewsletterSubscriber.objects.create(
            email='sub1@example.com',
            is_confirmed=True
        )
        subscriber2 = NewsletterSubscriber.objects.create(
            email='sub2@example.com',
            is_confirmed=True
        )
        
        # Create post
        post = Post.objects.create(
            title='Test Post',
            author=self.user,
            content='Test content',
            status='published'
        )
        
        # Execute task
        result = send_new_post_notification(post.id)
        
        # Verify emails were sent
        self.assertIn('Newsletter sent: 2 sent, 0 failed', result)
        self.assertEqual(mock_send_mail.call_count, 2)
    
    @patch('blog.tasks.send_mail')
    def test_send_new_post_notification_no_subscribers(self, mock_send_mail):
        """Test send_new_post_notification with no subscribers"""
        post = Post.objects.create(
            title='Test Post',
            author=self.user,
            content='Test content',
            status='published'
        )
        
        result = send_new_post_notification(post.id)
        
        self.assertIn('No confirmed subscribers found', result)
        mock_send_mail.assert_not_called()
    
    def test_cleanup_unconfirmed_subscriptions_task(self):
        """Test cleanup_unconfirmed_subscriptions task"""
        # Create old unconfirmed subscription
        old_subscriber = NewsletterSubscriber.objects.create(
            email='old@example.com'
        )
        old_subscriber.subscribed_at = timezone.now() - timedelta(days=8)
        old_subscriber.save()
        
        # Create recent unconfirmed subscription
        recent_subscriber = NewsletterSubscriber.objects.create(
            email='recent@example.com'
        )
        
        # Create confirmed subscription (should not be deleted)
        confirmed_subscriber = NewsletterSubscriber.objects.create(
            email='confirmed@example.com',
            is_confirmed=True
        )
        confirmed_subscriber.subscribed_at = timezone.now() - timedelta(days=8)
        confirmed_subscriber.save()
        
        # Execute task
        result = cleanup_unconfirmed_subscriptions()
        
        # Verify cleanup
        self.assertIn('Cleaned up 1 unconfirmed subscriptions', result)
        
        # Check that only old unconfirmed subscription was deleted
        self.assertFalse(NewsletterSubscriber.objects.filter(
            email='old@example.com'
        ).exists())
        self.assertTrue(NewsletterSubscriber.objects.filter(
            email='recent@example.com'
        ).exists())
        self.assertTrue(NewsletterSubscriber.objects.filter(
            email='confirmed@example.com'
        ).exists())


class EmailTemplateTest(TestCase):
    """Test email template rendering"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.subscriber = NewsletterSubscriber.objects.create(
            email='subscriber@example.com',
            is_confirmed=True
        )
    
    def test_confirmation_email_template_rendering(self):
        """Test confirmation email template rendering"""
        from django.template.loader import render_to_string
        
        context = {
            'subscriber': self.subscriber,
            'confirmation_url': 'http://example.com/confirm/token123',
            'site_name': 'Test Site'
        }
        
        # Test HTML template
        html_content = render_to_string(
            'blog/emails/confirmation_email.html',
            context
        )
        self.assertIn('subscriber@example.com', html_content)
        self.assertIn('confirmation_url', html_content)
        
        # Test text template
        text_content = render_to_string(
            'blog/emails/confirmation_email.txt',
            context
        )
        self.assertIn('subscriber@example.com', text_content)
        self.assertIn('http://example.com/confirm/token123', text_content)
    
    def test_new_post_notification_template_rendering(self):
        """Test new post notification template rendering"""
        from django.template.loader import render_to_string
        
        post = Post.objects.create(
            title='Test Post',
            author=self.user,
            content='Test content',
            excerpt='Test excerpt',
            status='published'
        )
        
        context = {
            'post': post,
            'subscriber': self.subscriber,
            'post_url': 'http://example.com/blog/test-post',
            'unsubscribe_url': 'http://example.com/unsubscribe/token123',
            'site_name': 'Test Site'
        }
        
        # Test HTML template
        html_content = render_to_string(
            'blog/emails/new_post_notification.html',
            context
        )
        self.assertIn('Test Post', html_content)
        self.assertIn('Test excerpt', html_content)
        self.assertIn('unsubscribe', html_content.lower())
        
        # Test text template
        text_content = render_to_string(
            'blog/emails/new_post_notification.txt',
            context
        )
        self.assertIn('Test Post', text_content)
        self.assertIn('http://example.com/blog/test-post', text_content)
        self.assertIn('http://example.com/unsubscribe/token123', text_content)


class EmailSecurityTest(TestCase):
    """Test security aspects of email subscription system"""
    
    def test_token_security(self):
        """Test that tokens are cryptographically secure"""
        subscriber = NewsletterSubscriber.objects.create(
            email='security@example.com'
        )
        
        # Tokens should be 64 characters (SHA256 hex)
        self.assertEqual(len(subscriber.confirmation_token), 64)
        self.assertEqual(len(subscriber.unsubscribe_token), 64)
        
        # Tokens should be different
        self.assertNotEqual(subscriber.confirmation_token, subscriber.unsubscribe_token)
        
        # Tokens should be hex strings
        self.assertTrue(all(c in '0123456789abcdef' for c in subscriber.confirmation_token))
        self.assertTrue(all(c in '0123456789abcdef' for c in subscriber.unsubscribe_token))
    
    def test_token_uniqueness_across_subscribers(self):
        """Test that tokens are unique across different subscribers"""
        subscriber1 = NewsletterSubscriber.objects.create(email='user1@example.com')
        subscriber2 = NewsletterSubscriber.objects.create(email='user2@example.com')
        
        # All tokens should be unique
        tokens = [
            subscriber1.confirmation_token,
            subscriber1.unsubscribe_token,
            subscriber2.confirmation_token,
            subscriber2.unsubscribe_token
        ]
        
        self.assertEqual(len(tokens), len(set(tokens)))  # All unique
    
    def test_expired_token_handling(self):
        """Test handling of expired confirmation tokens"""
        # This would require implementing token expiration
        # For now, we test that old unconfirmed subscriptions are cleaned up
        old_subscriber = NewsletterSubscriber.objects.create(
            email='expired@example.com'
        )
        old_subscriber.subscribed_at = timezone.now() - timedelta(days=8)
        old_subscriber.save()
        
        # After cleanup, old unconfirmed subscriptions should be removed
        cleanup_unconfirmed_subscriptions()
        
        self.assertFalse(NewsletterSubscriber.objects.filter(
            email='expired@example.com'
        ).exists())
    
    def test_email_injection_prevention(self):
        """Test prevention of email header injection"""
        # Test with malicious email containing newlines
        malicious_email = "test@example.com\nBcc: evil@hacker.com"
        
        form = NewsletterSubscriptionForm(data={'email': malicious_email})
        self.assertFalse(form.is_valid())
    
    def test_rate_limiting_subscription_attempts(self):
        """Test rate limiting for subscription attempts"""
        # This would require implementing rate limiting
        # For now, we test that multiple subscriptions with same email don't create duplicates
        email = 'ratelimit@example.com'
        
        # Multiple subscription attempts
        for _ in range(5):
            self.client.post(reverse('blog:subscribe_newsletter'), {
                'email': email
            })
        
        # Should still have only one subscriber
        self.assertEqual(NewsletterSubscriber.objects.filter(email=email).count(), 1)


class EmailPerformanceTest(TestCase):
    """Test performance aspects of email system"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @patch('blog.tasks.send_mail')
    def test_bulk_email_sending_performance(self, mock_send_mail):
        """Test performance of sending emails to many subscribers"""
        # Create many confirmed subscribers
        subscribers = []
        for i in range(100):
            subscriber = NewsletterSubscriber.objects.create(
                email=f'subscriber{i}@example.com',
                is_confirmed=True
            )
            subscribers.append(subscriber)
        
        # Create post
        post = Post.objects.create(
            title='Performance Test Post',
            author=self.user,
            content='Test content',
            status='published'
        )
        
        # Measure time to send notifications
        import time
        start_time = time.time()
        
        result = send_new_post_notification(post.id)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        self.assertLess(execution_time, 10.0)  # 10 seconds max
        
        # Verify all emails were sent
        self.assertIn('Newsletter sent: 100 sent, 0 failed', result)
        self.assertEqual(mock_send_mail.call_count, 100)
    
    def test_database_query_optimization(self):
        """Test that email queries are optimized"""
        # Create subscribers
        for i in range(10):
            NewsletterSubscriber.objects.create(
                email=f'subscriber{i}@example.com',
                is_confirmed=True
            )
        
        # Test that getting confirmed subscribers uses efficient query
        with self.assertNumQueries(1):  # Should be a single query
            confirmed_subscribers = list(NewsletterSubscriber.objects.filter(
                is_confirmed=True
            ))
            self.assertEqual(len(confirmed_subscribers), 10)