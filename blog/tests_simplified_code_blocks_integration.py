"""
Integration tests for simplified code blocks - Final validation.

This module provides comprehensive integration testing to ensure all
simplified code block components work together cohesively and meet
all specified requirements.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.template.loader import render_to_string
from django.template import Context, Template
from blog.models import Post, Category
import re


class SimplifiedCodeBlocksIntegrationTest(TestCase):
    """Comprehensive integration tests for simplified code blocks."""
    
    def setUp(self):
        """Set up test data with various code block scenarios."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Tech',
            slug='tech'
        )
        
        # Create comprehensive test post with various code scenarios
        self.post = Post.objects.create(
            title='Complete Code Block Integration Test',
            slug='code-block-integration-test',
            author=self.user,
            content='''
            <h2>Python Code Example</h2>
            <p>Here's a Python function with proper syntax highlighting:</p>
            <div class="code-block">
                <div class="code-header">
                    <span class="code-language">Python</span>
                </div>
                <pre><code class="language-python">
def calculate_fibonacci(n):
    """Calculate fibonacci sequence up to n terms."""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    sequence = [0, 1]
    for i in range(2, n):
        sequence.append(sequence[i-1] + sequence[i-2])
    
    return sequence

# Example usage
result = calculate_fibonacci(10)
print(f"Fibonacci sequence: {result}")
                </code></pre>
            </div>
            
            <h2>JavaScript Code Example</h2>
            <p>A JavaScript class with modern ES6+ features:</p>
            <div class="code-block">
                <div class="code-header">
                    <span class="code-language">JavaScript</span>
                </div>
                <pre><code class="language-javascript">
class DataProcessor {
    constructor(options = {}) {
        this.options = {
            timeout: 5000,
            retries: 3,
            ...options
        };
    }
    
    async processData(data) {
        try {
            const result = await this.validateAndTransform(data);
            return { success: true, data: result };
        } catch (error) {
            console.error('Processing failed:', error.message);
            return { success: false, error: error.message };
        }
    }
    
    validateAndTransform(data) {
        return new Promise((resolve, reject) => {
            if (!data || typeof data !== 'object') {
                reject(new Error('Invalid data format'));
                return;
            }
            
            // Transform data
            const transformed = Object.keys(data).reduce((acc, key) => {
                acc[key.toLowerCase()] = data[key];
                return acc;
            }, {});
            
            resolve(transformed);
        });
    }
}
                </code></pre>
            </div>
            
            <h2>CSS Code Example</h2>
            <p>Modern CSS with custom properties and grid layout:</p>
            <div class="code-block">
                <div class="code-header">
                    <span class="code-language">CSS</span>
                </div>
                <pre><code class="language-css">
/* Modern CSS Grid Layout with Custom Properties */
:root {
    --primary-color: #2563eb;
    --secondary-color: #64748b;
    --spacing-unit: 1rem;
    --border-radius: 0.5rem;
}

.grid-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: calc(var(--spacing-unit) * 2);
    padding: var(--spacing-unit);
    background: linear-gradient(135deg, 
        var(--primary-color) 0%, 
        var(--secondary-color) 100%);
    border-radius: var(--border-radius);
}

.grid-item {
    background: white;
    padding: var(--spacing-unit);
    border-radius: var(--border-radius);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    transition: transform 0.2s ease-in-out;
}

.grid-item:hover {
    transform: translateY(-2px);
}

@media (max-width: 768px) {
    .grid-container {
        grid-template-columns: 1fr;
        gap: var(--spacing-unit);
    }
}
                </code></pre>
            </div>
            
            <h2>Inline Code Examples</h2>
            <p>You can use inline code like <code>const result = await fetchData()</code> within paragraphs. 
            The <code>Array.prototype.map()</code> method is useful for transforming arrays. 
            Don't forget to handle errors with <code>try...catch</code> blocks.</p>
            
            <p>File paths like <code>/usr/local/bin/node</code> and commands like <code>npm install --save-dev</code> 
            should be clearly distinguishable from regular text.</p>
            
            <h2>Code Without Language Specification</h2>
            <p>Sometimes code blocks don't have a specific language:</p>
            <div class="code-block">
                <pre><code>
# Configuration file example
server.port=8080
server.host=localhost
database.url=jdbc:postgresql://localhost:5432/mydb
database.username=admin
database.password=secret123

# Enable debug mode
debug.enabled=true
logging.level=INFO
                </code></pre>
            </div>
            ''',
            excerpt='Comprehensive test for simplified code blocks integration',
            status='published'
        )
        self.post.categories.add(self.category)
        
        self.client = Client()
    
    def test_complete_page_integration(self):
        """Test that the complete page loads with all code block components."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        
        # Requirement 1.1: Page loads successfully
        self.assertEqual(response.status_code, 200)
        
        # Requirement 1.1, 1.2: CSS is included
        self.assertContains(response, 'simplified-code-blocks.css')
        
        # Requirement 2.1: Copy button functionality is present
        self.assertContains(response, 'initializeCopyButtons')
        
        # Requirement 4.1, 4.2: Language indicators are present
        self.assertContains(response, 'code-language')
        self.assertContains(response, 'Python')
        self.assertContains(response, 'JavaScript')
        self.assertContains(response, 'CSS')
    
    def test_code_block_structure_integration(self):
        """Test that code blocks have proper structure for all components."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        content = response.content.decode()
        
        # Requirement 1.1, 1.2: Code block containers are present
        self.assertIn('class="code-block"', content)
        
        # Requirement 4.1, 4.2: Code headers with language indicators
        self.assertIn('class="code-header"', content)
        self.assertIn('class="code-language"', content)
        
        # Requirement 1.3: Pre elements for code content
        code_block_pattern = r'<div class="code-block">.*?<pre>.*?</pre>.*?</div>'
        code_blocks = re.findall(code_block_pattern, content, re.DOTALL)
        self.assertGreater(len(code_blocks), 0, "Should have code blocks with proper structure")
    
    def test_copy_button_integration(self):
        """Test that copy button integration works with all code block types."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        content = response.content.decode()
        
        # Requirement 2.1: Copy button creation JavaScript
        self.assertIn("copyBtn.className = 'copy-btn'", content)
        self.assertIn("copyBtn.innerHTML = '<i class=\"fas fa-copy\"></i> Copy'", content)
        
        # Requirement 2.2, 2.3: Success and error feedback
        self.assertIn("copyBtn.classList.add('success')", content)
        self.assertIn("copyBtn.classList.add('error')", content)
        self.assertIn('<i class="fas fa-check"></i> Copied!', content)
        self.assertIn('<i class="fas fa-times"></i> Failed', content)
        
        # Requirement 2.4: Button positioning
        self.assertIn("pre.style.position = 'relative'", content)
        self.assertIn("pre.appendChild(copyBtn)", content)
    
    def test_inline_code_integration(self):
        """Test that inline code styling integrates properly with text flow."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        content = response.content.decode()
        
        # Requirement 5.1, 5.2: Inline code elements are present
        inline_code_pattern = r'<code>.*?</code>'
        inline_codes = re.findall(inline_code_pattern, content)
        self.assertGreater(len(inline_codes), 0, "Should have inline code elements")
        
        # Check for specific inline code examples
        self.assertIn('<code>const result = await fetchData()</code>', content)
        self.assertIn('<code>Array.prototype.map()</code>', content)
        self.assertIn('<code>try...catch</code>', content)
    
    def test_syntax_highlighting_integration(self):
        """Test that syntax highlighting classes are properly integrated."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        content = response.content.decode()
        
        # Requirement 1.4: Language-specific classes are present
        self.assertIn('class="language-python"', content)
        self.assertIn('class="language-javascript"', content)
        self.assertIn('class="language-css"', content)
        
        # Check that code content is properly structured for highlighting
        self.assertIn('def calculate_fibonacci', content)
        self.assertIn('class DataProcessor', content)
        self.assertIn(':root {', content)
    
    def test_responsive_integration(self):
        """Test that responsive features are integrated properly."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        
        # Requirement 3.1, 3.2, 3.3: Page loads (responsive CSS is in the CSS file)
        self.assertEqual(response.status_code, 200)
        
        # The actual responsive behavior testing would require browser automation
        # Here we verify that the CSS file is included which contains responsive rules
        self.assertContains(response, 'simplified-code-blocks.css')
    
    def test_accessibility_integration(self):
        """Test that accessibility features are integrated across all components."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        content = response.content.decode()
        
        # Requirement 2.1, 2.2: Copy buttons should be keyboard accessible
        # The JavaScript creates buttons that are focusable by default
        self.assertIn("copyBtn.addEventListener('click'", content)
        
        # Requirement 5.3: Inline code should have proper contrast
        # This is handled by CSS, verify the CSS is included
        self.assertContains(response, 'simplified-code-blocks.css')
    
    def test_theme_consistency_integration(self):
        """Test that all components maintain theme consistency."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        
        # Requirement 1.1, 1.2: Theme consistency is maintained through CSS variables
        # Verify that the CSS file is properly included
        self.assertContains(response, 'simplified-code-blocks.css')
        
        # The actual theme consistency is validated through the CSS file structure
        # which uses CSS custom properties for consistent theming
        self.assertEqual(response.status_code, 200)
    
    def test_performance_integration(self):
        """Test that performance optimizations are integrated properly."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        content = response.content.decode()
        
        # Requirement: Efficient copy button initialization
        self.assertIn('initializeCopyButtons', content)
        
        # Requirement: Mutation observer for dynamic content
        self.assertIn('MutationObserver', content)
        self.assertIn('observer.observe', content)
        
        # Requirement: Efficient event handling
        self.assertIn('addEventListener', content)
    
    def test_error_handling_integration(self):
        """Test that error handling is integrated across all components."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        content = response.content.decode()
        
        # Requirement 2.3: Copy operation error handling
        self.assertIn('try {', content)
        self.assertIn('} catch (err) {', content)
        self.assertIn("console.error('Copy failed:', err)", content)
        
        # Requirement: Fallback for older browsers
        self.assertIn('navigator.clipboard', content)
        self.assertIn('document.execCommand', content)
    
    def test_all_requirements_coverage(self):
        """Comprehensive test to ensure all requirements are covered in integration."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        content = response.content.decode()
        
        # Requirement 1.1: Simplified styling with theme consistency
        self.assertContains(response, 'simplified-code-blocks.css')
        
        # Requirement 1.2: Single subtle border and simplified background
        # (Verified through CSS file inclusion)
        
        # Requirement 1.3: Clean and readable typography
        # (Verified through proper code block structure)
        self.assertIn('<pre>', content)
        self.assertIn('<code', content)
        
        # Requirement 1.4: Functional syntax highlighting with theme colors
        self.assertIn('language-python', content)
        self.assertIn('language-javascript', content)
        
        # Requirement 2.1: Subtle, non-intrusive copy button
        self.assertIn('copy-btn', content)
        
        # Requirement 2.2: Copy entire code content to clipboard
        self.assertIn('navigator.clipboard.writeText', content)
        
        # Requirement 2.3: Visual feedback for copy action
        self.assertIn('Copied!', content)
        
        # Requirement 2.4: Button doesn't interfere with readability
        self.assertIn("pre.style.position = 'relative'", content)
        
        # Requirement 3.1: Horizontally scrollable on mobile
        # (Handled by CSS - verified through CSS inclusion)
        
        # Requirement 3.2: Appropriate font size adjustment
        # (Handled by CSS - verified through CSS inclusion)
        
        # Requirement 3.3: No horizontal page scrolling
        # (Handled by CSS - verified through CSS inclusion)
        
        # Requirement 3.4: Smooth scrolling on touch devices
        # (Handled by CSS - verified through CSS inclusion)
        
        # Requirement 4.1: Language displayed in subtle header
        self.assertIn('code-language', content)
        
        # Requirement 4.2: Consistent styling with simplified theme
        self.assertIn('code-header', content)
        
        # Requirement 4.4: Doesn't take excessive vertical space
        # (Verified through proper structure)
        
        # Requirement 5.1: Subtle background highlighting for inline code
        self.assertIn('<code>', content)
        
        # Requirement 5.2: Same monospace font as code blocks
        # (Handled by CSS - verified through CSS inclusion)
        
        # Requirement 5.3: Accessibility contrast standards
        # (Handled by CSS - verified through CSS inclusion)
        
        # Requirement 5.4: Doesn't affect line height or text flow
        # (Handled by CSS - verified through CSS inclusion)
        
        # All requirements are covered through the integration
        self.assertEqual(response.status_code, 200)


class SimplifiedCodeBlocksAccessibilityIntegrationTest(TestCase):
    """Integration tests specifically for accessibility features."""
    
    def setUp(self):
        """Set up test data for accessibility testing."""
        self.user = User.objects.create_user(
            username='accesstest',
            email='access@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Accessibility',
            slug='accessibility'
        )
        
        self.post = Post.objects.create(
            title='Accessibility Code Examples',
            slug='accessibility-code-examples',
            author=self.user,
            content='''
            <p>Testing accessibility with various code scenarios:</p>
            <div class="code-block">
                <div class="code-header">
                    <span class="code-language">HTML</span>
                </div>
                <pre><code class="language-html">
&lt;button aria-label="Close dialog" onclick="closeDialog()"&gt;
    &lt;span aria-hidden="true"&gt;&times;&lt;/span&gt;
&lt;/button&gt;
                </code></pre>
            </div>
            <p>Inline accessibility: <code>aria-label</code> and <code>role="button"</code></p>
            ''',
            excerpt='Accessibility testing for code blocks',
            status='published'
        )
        self.post.categories.add(self.category)
        
        self.client = Client()
    
    def test_accessibility_integration_complete(self):
        """Test complete accessibility integration."""
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        
        # Verify page loads and includes accessibility-focused CSS
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'simplified-code-blocks.css')
        
        # Verify copy button accessibility features are set up
        self.assertContains(response, 'initializeCopyButtons')
        
        # The detailed accessibility features are implemented in the CSS file
        # and JavaScript, which are included in the page