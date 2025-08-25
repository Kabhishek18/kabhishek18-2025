"""
Tests for LinkedIn hashtag admin configuration functionality.
"""
import json
from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from unittest.mock import Mock, patch

from .admin import LinkedInConfigAdmin
from .admin_forms import LinkedInConfigAdminForm
from .admin_widgets import HashtagRulesWidget, HashtagBlacklistWidget
from .linkedin_models import LinkedInConfig
from .models import Post, Category


class HashtagAdminConfigTest(TestCase):
    """Test hashtag configuration in admin interface"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        self.admin_site = AdminSite()
        self.admin = LinkedInConfigAdmin(LinkedInConfig, self.admin_site)
        
        # Create test user
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass'
        )
        
        # Create test LinkedIn config
        self.config = LinkedInConfig.objects.create(
            client_id='test_client_id',
            is_active=True,
            enable_hashtags=True,
            max_hashtags=5,
            custom_hashtag_rules={
                'technology': {
                    'required_hashtags': ['#Tech', '#Programming'],
                    'suggested_hashtags': ['#Development', '#Coding'],
                    'max_hashtags': 3
                }
            },
            hashtag_blacklist=['spam', 'clickbait']
        )
        
        # Create test post
        self.category = Category.objects.create(name='Technology', slug='technology')
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            content='Test content about programming',
            status='published',
            author=self.user
        )
        self.post.categories.add(self.category)
    
    def test_hashtag_status_display(self):
        """Test hashtag status display in admin list"""
        status = self.admin.hashtag_status(self.config)
        self.assertIn('Max: 5', status)
        self.assertIn('Rules: 1', status)
        self.assertIn('Blacklist: 2', status)
    
    def test_hashtag_status_disabled(self):
        """Test hashtag status when disabled"""
        self.config.enable_hashtags = False
        status = self.admin.hashtag_status(self.config)
        self.assertIn('Disabled', status)
    
    def test_hashtag_config_display(self):
        """Test hashtag configuration summary display"""
        display = self.admin.hashtag_config_display(self.config)
        self.assertIn('Hashtags: Enabled', display)
        self.assertIn('Max: 5', display)
        self.assertIn('Custom Rules: 1 categories', display)
        self.assertIn('Blacklist: 2 terms', display)
    
    def test_validate_hashtag_config_action(self):
        """Test hashtag configuration validation action"""
        request = self.factory.get('/')
        request.user = self.user
        
        # Add messages framework
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        # Test valid configuration
        queryset = LinkedInConfig.objects.filter(id=self.config.id)
        self.admin.validate_hashtag_config(request, queryset)
        
        # Check that no error messages were added
        message_list = list(messages)
        success_messages = [m for m in message_list if m.level_tag == 'success']
        self.assertTrue(len(success_messages) > 0)
    
    def test_preview_posts_view(self):
        """Test preview posts API endpoint"""
        request = self.factory.get('/admin/blog/linkedinconfig/preview-posts/')
        request.user = self.user
        
        response = self.admin.preview_posts_view(request)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('posts', data)
        self.assertTrue(len(data['posts']) > 0)
        self.assertEqual(data['posts'][0]['title'], 'Test Post')
    
    def test_preview_hashtags_view(self):
        """Test hashtag preview API endpoint"""
        request_data = {
            'post_id': self.post.id,
            'config': {
                'enable_hashtags': True,
                'max_hashtags': 5,
                'custom_hashtag_rules': {},
                'hashtag_blacklist': []
            }
        }
        
        request = self.factory.post(
            '/admin/blog/linkedinconfig/preview-hashtags/',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        request.user = self.user
        
        with patch('blog.admin.LinkedInConfigAdmin._generate_preview_hashtags') as mock_generate:
            mock_generate.return_value = (['#Tech', '#Programming'], {'source': 'test'})
            
            response = self.admin.preview_hashtags_view(request)
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertEqual(data['hashtags'], ['#Tech', '#Programming'])


class HashtagAdminFormTest(TestCase):
    """Test hashtag admin form functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass'
        )
    
    def test_form_validation_valid_data(self):
        """Test form validation with valid data"""
        form_data = {
            'client_id': 'test_client_id',
            'is_active': True,
            'enable_hashtags': True,
            'max_hashtags': 5,
            'custom_hashtag_rules': {
                'technology': {
                    'required_hashtags': ['#Tech', '#Programming'],
                    'suggested_hashtags': ['#Development'],
                    'max_hashtags': 3
                }
            },
            'hashtag_blacklist': ['spam', 'clickbait'],
            'enable_image_posting': True,
            'image_posting_strategy': 'always'
        }
        
        form = LinkedInConfigAdminForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
    
    def test_form_validation_invalid_max_hashtags(self):
        """Test form validation with invalid max_hashtags"""
        form_data = {
            'client_id': 'test_client_id',
            'is_active': True,
            'enable_hashtags': True,
            'max_hashtags': -1,  # Invalid
            'enable_image_posting': True,
            'image_posting_strategy': 'always'
        }
        
        form = LinkedInConfigAdminForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('max_hashtags', form.errors)
    
    def test_form_validation_invalid_hashtag_rules(self):
        """Test form validation with invalid hashtag rules"""
        form_data = {
            'client_id': 'test_client_id',
            'is_active': True,
            'enable_hashtags': True,
            'max_hashtags': 5,
            'custom_hashtag_rules': {
                'technology': {
                    'required_hashtags': ['invalid_hashtag'],  # Missing #
                }
            },
            'enable_image_posting': True,
            'image_posting_strategy': 'always'
        }
        
        form = LinkedInConfigAdminForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('custom_hashtag_rules', form.errors)
    
    def test_hashtag_validation(self):
        """Test hashtag validation logic"""
        form = LinkedInConfigAdminForm()
        
        # Valid hashtags
        self.assertTrue(form._is_valid_hashtag('#Tech'))
        self.assertTrue(form._is_valid_hashtag('#Programming123'))
        self.assertTrue(form._is_valid_hashtag('#Tech_Tips'))
        
        # Invalid hashtags
        self.assertFalse(form._is_valid_hashtag('#123Tech'))  # Starts with number
        self.assertFalse(form._is_valid_hashtag('#Tech-Tips'))  # Contains hyphen
        self.assertFalse(form._is_valid_hashtag('#Tech Tips'))  # Contains space
        self.assertFalse(form._is_valid_hashtag(''))  # Empty
    
    def test_blacklist_cleaning(self):
        """Test hashtag blacklist cleaning"""
        form_data = {
            'client_id': 'test_client_id',
            'is_active': True,
            'enable_hashtags': True,
            'max_hashtags': 5,
            'hashtag_blacklist': ['SPAM', 'spam', 'Clickbait', '  urgent  '],
            'enable_image_posting': True,
            'image_posting_strategy': 'always'
        }
        
        form = LinkedInConfigAdminForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Check that blacklist is cleaned (lowercase, no duplicates, trimmed)
        cleaned_blacklist = form.cleaned_data['hashtag_blacklist']
        self.assertEqual(set(cleaned_blacklist), {'spam', 'clickbait', 'urgent'})


class HashtagWidgetTest(TestCase):
    """Test hashtag admin widgets"""
    
    def test_hashtag_rules_widget_render(self):
        """Test hashtag rules widget rendering"""
        widget = HashtagRulesWidget()
        
        test_value = {
            'technology': {
                'required_hashtags': ['#Tech', '#Programming']
            }
        }
        
        html = widget.render('test_field', test_value)
        self.assertIn('hashtag-rules-widget', html)
        self.assertIn('validateHashtagRules', html)
        self.assertIn('formatHashtagRules', html)
    
    def test_hashtag_blacklist_widget_render(self):
        """Test hashtag blacklist widget rendering"""
        widget = HashtagBlacklistWidget()
        
        test_value = ['spam', 'clickbait', 'urgent']
        
        html = widget.render('test_field', test_value)
        self.assertIn('hashtag-blacklist-widget', html)
        self.assertIn('sortBlacklist', html)
        self.assertIn('removeDuplicates', html)
        self.assertIn('spam\nclickbait\nurgent', html)
    
    def test_hashtag_rules_widget_value_extraction(self):
        """Test hashtag rules widget value extraction"""
        widget = HashtagRulesWidget()
        
        # Test JSON string input
        json_data = '{"technology": {"required_hashtags": ["#Tech"]}}'
        result = widget.value_from_datadict({'test_field': json_data}, {}, 'test_field')
        
        expected = {"technology": {"required_hashtags": ["#Tech"]}}
        self.assertEqual(result, expected)
    
    def test_hashtag_blacklist_widget_value_extraction(self):
        """Test hashtag blacklist widget value extraction"""
        widget = HashtagBlacklistWidget()
        
        # Test newline-separated input
        text_data = 'spam\nclickbait\nurgent\n\n'
        result = widget.value_from_datadict({'test_field': text_data}, {}, 'test_field')
        
        expected = ['spam', 'clickbait', 'urgent']
        self.assertEqual(result, expected)


class HashtagConfigIntegrationTest(TestCase):
    """Integration tests for hashtag configuration"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass'
        )
        
        self.config = LinkedInConfig.objects.create(
            client_id='test_client_id',
            is_active=True,
            enable_hashtags=True,
            max_hashtags=5,
            custom_hashtag_rules={
                'technology': {
                    'required_hashtags': ['#Tech', '#Programming'],
                    'suggested_hashtags': ['#Development', '#Coding'],
                    'max_hashtags': 3
                }
            },
            hashtag_blacklist=['spam', 'clickbait']
        )
    
    def test_config_methods(self):
        """Test LinkedInConfig hashtag methods"""
        hashtag_config = self.config.get_hashtag_config()
        
        self.assertTrue(hashtag_config['enable_hashtags'])
        self.assertEqual(hashtag_config['max_hashtags'], 5)
        self.assertIn('technology', hashtag_config['custom_hashtag_rules'])
        self.assertIn('spam', hashtag_config['hashtag_blacklist'])
    
    def test_image_posting_config(self):
        """Test image posting configuration"""
        image_config = self.config.get_image_posting_config()
        
        self.assertTrue(image_config['enable_image_posting'])
        self.assertEqual(image_config['image_posting_strategy'], 'always')
    
    def test_should_include_images(self):
        """Test image inclusion logic"""
        # Test with default settings
        self.assertTrue(self.config.should_include_images())
        
        # Test with disabled image posting
        self.config.enable_image_posting = False
        self.assertFalse(self.config.should_include_images())
        
        # Test with 'never' strategy
        self.config.enable_image_posting = True
        self.config.image_posting_strategy = 'never'
        self.assertFalse(self.config.should_include_images())