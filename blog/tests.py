from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from unittest.mock import patch
from .models import NewsletterSubscriber, Post, Category
from .tasks import send_confirmation_email, send_new_post_notification, cleanup_unconfirmed_subscriptions
from datetime import timedelta


class NewsletterSubscriptionTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_newsletter_subscription_creation(self):
        """Test that newsletter subscription creates subscriber with tokens"""
        response = self.client.post(reverse('blog:subscribe_newsletter'), {
            'email': 'test@example.com'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after POST
        
        subscriber = NewsletterSubscriber.objects.get(email='test@example.com')
        self.assertFalse(subscriber.is_confirmed)
        self.assertTrue(subscriber.confirmation_token)
        self.assertTrue(subscriber.unsubscribe_token)
        self.assertIsNone(subscriber.confirmed_at)

    def test_duplicate_subscription_handling(self):
        """Test handling of duplicate email subscriptions"""
        # Create initial subscription
        NewsletterSubscriber.objects.create(email='test@example.com')
        
        response = self.client.post(reverse('blog:subscribe_newsletter'), {
            'email': 'test@example.com'
        })
        
        self.assertEqual(response.status_code, 302)
        # Should still have only one subscriber
        self.assertEqual(NewsletterSubscriber.objects.filter(email='test@example.com').count(), 1)

    def test_email_confirmation(self):
        """Test email confirmation workflow"""
        subscriber = NewsletterSubscriber.objects.create(email='test@example.com')
        
        response = self.client.get(reverse('blog:confirm_subscription', kwargs={
            'token': subscriber.confirmation_token
        }))
        
        self.assertEqual(response.status_code, 302)  # Redirect after confirmation
        
        subscriber.refresh_from_db()
        self.assertTrue(subscriber.is_confirmed)
        self.assertIsNotNone(subscriber.confirmed_at)

    def test_invalid_confirmation_token(self):
        """Test handling of invalid confirmation tokens"""
        response = self.client.get(reverse('blog:confirm_subscription', kwargs={
            'token': 'invalid-token'
        }))
        
        self.assertEqual(response.status_code, 302)  # Redirect with error

    def test_unsubscribe_workflow(self):
        """Test unsubscribe workflow"""
        subscriber = NewsletterSubscriber.objects.create(
            email='test@example.com',
            is_confirmed=True
        )
        
        # GET request should show confirmation page
        response = self.client.get(reverse('blog:unsubscribe', kwargs={
            'token': subscriber.unsubscribe_token
        }))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test@example.com')
        
        # POST request should delete subscription
        response = self.client.post(reverse('blog:unsubscribe', kwargs={
            'token': subscriber.unsubscribe_token
        }))
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(NewsletterSubscriber.objects.filter(email='test@example.com').exists())


class EmailTaskTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Test Category')

    @patch('blog.tasks.send_mail')
    def test_send_confirmation_email_task(self, mock_send_mail):
        """Test confirmation email task"""
        subscriber = NewsletterSubscriber.objects.create(email='test@example.com')
        
        result = send_confirmation_email(subscriber.id)
        
        self.assertIn('Confirmation email sent', result)
        mock_send_mail.assert_called_once()

    @patch('blog.tasks.send_mail')
    def test_send_new_post_notification_task(self, mock_send_mail):
        """Test new post notification task"""
        # Create confirmed subscribers
        subscriber1 = NewsletterSubscriber.objects.create(
            email='test1@example.com',
            is_confirmed=True
        )
        subscriber2 = NewsletterSubscriber.objects.create(
            email='test2@example.com',
            is_confirmed=True
        )
        # Create unconfirmed subscriber (should not receive email)
        NewsletterSubscriber.objects.create(
            email='test3@example.com',
            is_confirmed=False
        )
        
        post = Post.objects.create(
            title='Test Post',
            content='Test content',
            author=self.user,
            status='published'
        )
        
        result = send_new_post_notification(post.id)
        
        self.assertIn('Newsletter sent: 2 sent, 0 failed', result)
        self.assertEqual(mock_send_mail.call_count, 2)

    def test_cleanup_unconfirmed_subscriptions_task(self):
        """Test cleanup of unconfirmed subscriptions"""
        # Create old unconfirmed subscription
        old_subscriber = NewsletterSubscriber.objects.create(email='old@example.com')
        old_subscriber.subscribed_at = timezone.now() - timedelta(days=8)
        old_subscriber.save()
        
        # Create recent unconfirmed subscription
        recent_subscriber = NewsletterSubscriber.objects.create(email='recent@example.com')
        
        # Create confirmed subscription (should not be deleted)
        confirmed_subscriber = NewsletterSubscriber.objects.create(
            email='confirmed@example.com',
            is_confirmed=True
        )
        confirmed_subscriber.subscribed_at = timezone.now() - timedelta(days=8)
        confirmed_subscriber.save()
        
        result = cleanup_unconfirmed_subscriptions()
        
        self.assertIn('Cleaned up 1 unconfirmed subscriptions', result)
        
        # Check that only the old unconfirmed subscription was deleted
        self.assertFalse(NewsletterSubscriber.objects.filter(email='old@example.com').exists())
        self.assertTrue(NewsletterSubscriber.objects.filter(email='recent@example.com').exists())
        self.assertTrue(NewsletterSubscriber.objects.filter(email='confirmed@example.com').exists())


class NewsletterIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_full_subscription_workflow(self):
        """Test complete subscription workflow from signup to confirmation"""
        # Step 1: Subscribe
        response = self.client.post(reverse('blog:subscribe_newsletter'), {
            'email': 'subscriber@example.com'
        })
        
        self.assertEqual(response.status_code, 302)
        
        subscriber = NewsletterSubscriber.objects.get(email='subscriber@example.com')
        self.assertFalse(subscriber.is_confirmed)
        
        # Step 2: Confirm subscription
        response = self.client.get(reverse('blog:confirm_subscription', kwargs={
            'token': subscriber.confirmation_token
        }))
        
        self.assertEqual(response.status_code, 302)
        
        subscriber.refresh_from_db()
        self.assertTrue(subscriber.is_confirmed)
        
        # Step 3: Unsubscribe
        response = self.client.post(reverse('blog:unsubscribe', kwargs={
            'token': subscriber.unsubscribe_token
        }))
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(NewsletterSubscriber.objects.filter(email='subscriber@example.com').exists())
