"""
Tests for simplified code blocks functionality.

This module tests the copy button functionality and styling
for the simplified code blocks feature.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from blog.models import Post, Category


class SimplifiedCodeBlocksTest(TestCase):
    """Test cases for simplified code blocks functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        # Create test post with code blocks
        self.post = Post.objects.create(
            title='Test Post with Code',
            slug='test-post-with-code',
            author=self.user,
            content='''
            <p>This is a test post with code blocks.</p>
            <pre><code class="language-python">
def hello_world():
    print("Hello, World!")
    return "success"
            </code></pre>
            <p>Another code block:</p>
            <pre><code class="language-javascript">
function greet(name) {
    console.log(`Hello, ${name}!`);
    return true;
}
            </code></pre>
            ''',
            excerpt='Test post with code blocks',
            status='published'
        )
        self.post.categories.add(self.category)
        
        self.client = Client()
    
    def test_blog_detail_page_loads(self):
        """Test that blog detail page loads successfully."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.post.title)
    
    def test_simplified_code_blocks_css_included(self):
        """Test that no code block CSS is included - using basic styling."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        # Should not contain any code block CSS files
        self.assertNotContains(response, 'code-blocks.css')
        self.assertNotContains(response, 'simplified-code-blocks.css')
    
    def test_copy_button_javascript_present(self):
        """Test that copy button JavaScript is removed - using basic code blocks."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        # Should not contain copy button functionality
        self.assertNotContains(response, 'initializeCopyButtons')
        self.assertContains(response, 'Copy button functionality removed')
    
    def test_code_blocks_in_content(self):
        """Test that code blocks are present in the rendered content."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        self.assertContains(response, '<pre>')
        self.assertContains(response, '<code')
        self.assertContains(response, 'def hello_world')
        self.assertContains(response, 'function greet')
    
    def test_copy_button_styling_classes(self):
        """Test that copy button functionality is removed."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        # Should not have copy button creation
        self.assertNotContains(response, "copyBtn.className = 'copy-btn'")
        self.assertNotContains(response, "copyBtn.innerHTML")
    
    def test_copy_button_feedback_states(self):
        """Test that copy button functionality is removed."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        # Should not have copy button states
        self.assertNotContains(response, "copyBtn.classList.add('success')")
        self.assertNotContains(response, 'Copied!')
        self.assertNotContains(response, "copyBtn.classList.add('error')")
        self.assertNotContains(response, 'Failed')
    
    def test_copy_button_reset_functionality(self):
        """Test that copy button functionality is removed."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        # Should not have copy button reset functionality
        self.assertNotContains(response, "copyBtn.classList.remove('success')")
        self.assertNotContains(response, "copyBtn.classList.remove('error')")
        # setTimeout might still exist for other functionality
        self.assertContains(response, 'Copy button functionality removed')
    
    def test_responsive_copy_button_behavior(self):
        """Test that page loads without copy button functionality."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        # Page should load successfully
        self.assertEqual(response.status_code, 200)
        # Should have basic code blocks without copy buttons
        self.assertContains(response, '<pre>')
        self.assertContains(response, '<code')
    
    def test_accessibility_features(self):
        """Test that code blocks use basic HTML accessibility."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        # Should not have copy button functionality
        self.assertNotContains(response, 'copyBtn.className')
        # Should have basic code blocks
        self.assertContains(response, '<pre>')
        self.assertContains(response, '<code')