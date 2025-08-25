"""
Tests for image posting admin configuration enhancements.
"""
from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from blog.models import Post, Category
from blog.linkedin_models import LinkedInConfig
from blog.admin import LinkedInConfigAdmin
from blog.admin_forms import LinkedInConfigAdminForm
import json


class ImagePostingAdminConfigTest(TestCase):
    """Test image posting admin configuration functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='password'
        )
        
        # Create test categories
        self.tech_category = Category.objects.create(
            name='Technology',
            slug='technology'
        )
        self.news_category = Category.objects.create(
            name='News',
            slug='news'
        )
        
        # Create test post
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            content='Test content',
            status='published',
            author=self.user
        )
        self.post.categories.add(self.tech_category)
        
        # Create LinkedIn config
        self.config = LinkedInConfig.objects.create(
            client_id='test_client_id',
            is_active=True,
            enable_image_posting=True,
            image_posting_strategy='category_based',
            category_image_overrides={
                'technology': {'enable_images': True, 'description': 'Always include images for tech'},
                'news': {'enable_images': False, 'description': 'Never include images for news'}
            }
        )
        
        self.admin_site = AdminSite()
        self.admin = LinkedInConfigAdmin(LinkedInConfig, self.admin_site)
    
    def test_category_image_overrides_field_exists(self):
        """Test that category_image_overrides field exists in the model."""
        self.assertTrue(hasattr(self.config, 'category_image_overrides'))
        self.assertIsInstance(self.config.category_image_overrides, dict)
    
    def test_should_include_images_with_category_overrides(self):
        """Test should_include_images method with category overrides."""
        # Test with technology category (should include images)
        result = self.config.should_include_images(self.post)
        self.assertTrue(result)
        
        # Test with news category (should not include images)
        self.post.categories.clear()
        self.post.categories.add(self.news_category)
        result = self.config.should_include_images(self.post)
        self.assertFalse(result)
    
    def test_should_include_images_with_always_strategy(self):
        """Test should_include_images with 'always' strategy."""
        self.config.image_posting_strategy = 'always'
        self.config.save()
        
        result = self.config.should_include_images(self.post)
        self.assertTrue(result)
    
    def test_should_include_images_with_never_strategy(self):
        """Test should_include_images with 'never' strategy."""
        self.config.image_posting_strategy = 'never'
        self.config.save()
        
        result = self.config.should_include_images(self.post)
        self.assertFalse(result)
    
    def test_should_include_images_with_disabled_global_setting(self):
        """Test should_include_images when globally disabled."""
        self.config.enable_image_posting = False
        self.config.save()
        
        result = self.config.should_include_images(self.post)
        self.assertFalse(result)
    
    def test_admin_form_validation_valid_category_overrides(self):
        """Test admin form validation with valid category overrides."""
        form_data = {
            'client_id': 'test_client',
            'is_active': True,
            'enable_image_posting': True,
            'image_posting_strategy': 'category_based',
            'category_image_overrides': {
                'technology': {'enable_images': True},
                'news': {'enable_images': False}
            }
        }
        
        form = LinkedInConfigAdminForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
    
    def test_admin_form_validation_invalid_category_overrides(self):
        """Test admin form validation with invalid category overrides."""
        form_data = {
            'client_id': 'test_client',
            'is_active': True,
            'enable_image_posting': True,
            'image_posting_strategy': 'category_based',
            'category_image_overrides': {
                'technology': 'invalid_value'  # Should be boolean or dict
            }
        }
        
        form = LinkedInConfigAdminForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('category_image_overrides', form.errors)
    
    def test_admin_form_validation_boolean_category_overrides(self):
        """Test admin form validation with boolean category overrides."""
        form_data = {
            'client_id': 'test_client',
            'is_active': True,
            'enable_image_posting': True,
            'image_posting_strategy': 'category_based',
            'category_image_overrides': {
                'technology': True,  # Simple boolean override
                'news': False
            }
        }
        
        form = LinkedInConfigAdminForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
    
    def test_preview_image_posting_decisions_action(self):
        """Test the preview image posting decisions admin action."""
        request = self.factory.get('/admin/')
        request.user = self.user
        
        # Add messages framework
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        # Test the action
        queryset = LinkedInConfig.objects.filter(id=self.config.id)
        self.admin.preview_image_posting_decisions(request, queryset)
        
        # Check that messages were added (indicating the action ran)
        message_list = list(messages)
        self.assertTrue(len(message_list) > 0)
    
    def test_generate_image_posting_preview_method(self):
        """Test the _generate_image_posting_preview method."""
        config_data = {
            'enable_image_posting': True,
            'image_posting_strategy': 'category_based',
            'category_image_overrides': {
                'technology': {'enable_images': True}
            }
        }
        
        decision, details = self.admin._generate_image_posting_preview(self.post, config_data)
        
        self.assertTrue(decision)
        self.assertIn('decision', details)
        self.assertIn('reason', details)
        self.assertIn('categories', details)
        self.assertEqual(details['decision'], 'Include images')
    
    def test_config_display_includes_category_overrides(self):
        """Test that the admin display includes category override information."""
        display_text = self.admin.hashtag_config_display(self.config)
        
        self.assertIn('Category Overrides', display_text)
        self.assertIn('technology', display_text)
    
    def test_model_validation_with_category_overrides(self):
        """Test model validation with category overrides."""
        # Valid configuration should not raise ValidationError
        try:
            self.config.full_clean()
        except Exception as e:
            self.fail(f"Valid configuration raised ValidationError: {e}")
        
        # Invalid configuration should raise ValidationError
        self.config.category_image_overrides = "invalid_json"
        with self.assertRaises(Exception):
            self.config.full_clean()
    
    def test_should_include_images_with_no_categories(self):
        """Test should_include_images when post has no categories."""
        # Remove all categories from post
        self.post.categories.clear()
        
        # With category_based strategy, should default to True
        result = self.config.should_include_images(self.post)
        self.assertTrue(result)
    
    def test_should_include_images_with_multiple_categories(self):
        """Test should_include_images when post has multiple categories."""
        # Add both categories to post
        self.post.categories.add(self.tech_category, self.news_category)
        
        # Should use the first category's override (technology = True)
        result = self.config.should_include_images(self.post)
        self.assertTrue(result)
        
        # Change technology to False and test again
        self.config.category_image_overrides['technology']['enable_images'] = False
        self.config.save()
        
        result = self.config.should_include_images(self.post)
        self.assertFalse(result)


class ImagePostingAdminFormTest(TestCase):
    """Test image posting admin form functionality."""
    
    def test_form_includes_image_posting_fields(self):
        """Test that the form includes image posting configuration fields."""
        form = LinkedInConfigAdminForm()
        
        self.assertIn('enable_image_posting', form.fields)
        self.assertIn('image_posting_strategy', form.fields)
        self.assertIn('category_image_overrides', form.fields)
        self.assertIn('image_posting_preview', form.fields)
    
    def test_form_widget_for_category_overrides(self):
        """Test that the form uses the correct widget for category overrides."""
        form = LinkedInConfigAdminForm()
        
        from blog.admin_widgets import CategoryImageOverridesWidget
        self.assertIsInstance(
            form.fields['category_image_overrides'].widget,
            CategoryImageOverridesWidget
        )
    
    def test_form_widget_for_image_posting_preview(self):
        """Test that the form uses the correct widget for image posting preview."""
        form = LinkedInConfigAdminForm()
        
        from blog.admin_widgets import ImagePostingPreviewWidget
        self.assertIsInstance(
            form.fields['image_posting_preview'].widget,
            ImagePostingPreviewWidget
        )
    
    def test_clean_category_image_overrides_with_json_string(self):
        """Test cleaning category overrides from JSON string."""
        form_data = {
            'client_id': 'test_client',
            'is_active': True,
            'enable_image_posting': True,
            'image_posting_strategy': 'category_based',
            'category_image_overrides': '{"technology": {"enable_images": true}}'
        }
        
        form = LinkedInConfigAdminForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        cleaned_overrides = form.cleaned_data['category_image_overrides']
        self.assertIsInstance(cleaned_overrides, dict)
        self.assertIn('technology', cleaned_overrides)
    
    def test_clean_category_image_overrides_empty(self):
        """Test cleaning empty category overrides."""
        form_data = {
            'client_id': 'test_client',
            'is_active': True,
            'enable_image_posting': True,
            'image_posting_strategy': 'always',
            'category_image_overrides': ''
        }
        
        form = LinkedInConfigAdminForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        cleaned_overrides = form.cleaned_data['category_image_overrides']
        self.assertEqual(cleaned_overrides, {})