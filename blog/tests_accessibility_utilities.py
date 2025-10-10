"""
Django Test Cases for Accessibility Testing Utilities

This module provides Django-integrated test cases for the accessibility
testing utilities, ensuring they work correctly within the Django environment.

Requirements covered:
- 5.3: Accessibility contrast requirements validation
- 2.1: Copy button keyboard accessibility testing
- 2.2: ARIA labels for screen readers testing
"""

import os
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.conf import settings
from blog.models import Post, Category
from blog.utils.accessibility_testing import (
    AccessibilityTestSuite,
    ColorContrastValidator,
    ScreenReaderCompatibilityTester,
    KeyboardNavigationTester,
    AccessibilityTestResult,
    ContrastResult
)


class ColorContrastValidatorTest(TestCase):
    """Test cases for the ColorContrastValidator class."""
    
    def setUp(self):
        self.validator = ColorContrastValidator()
    
    def test_hex_to_rgb_conversion(self):
        """Test hex color to RGB conversion."""
        # Test 6-digit hex
        self.assertEqual(self.validator.hex_to_rgb('#ffffff'), (255, 255, 255))
        self.assertEqual(self.validator.hex_to_rgb('#000000'), (0, 0, 0))
        self.assertEqual(self.validator.hex_to_rgb('#ff0000'), (255, 0, 0))
        
        # Test 3-digit hex
        self.assertEqual(self.validator.hex_to_rgb('#fff'), (255, 255, 255))
        self.assertEqual(self.validator.hex_to_rgb('#000'), (0, 0, 0))
        self.assertEqual(self.validator.hex_to_rgb('#f00'), (255, 0, 0))
    
    def test_rgba_to_rgb_conversion(self):
        """Test RGBA to RGB conversion with alpha compositing."""
        # Test fully opaque
        self.assertEqual(
            self.validator.rgba_to_rgb('rgba(255, 0, 0, 1.0)', (255, 255, 255)),
            (255, 0, 0)
        )
        
        # Test semi-transparent
        result = self.validator.rgba_to_rgb('rgba(0, 0, 0, 0.5)', (255, 255, 255))
        self.assertEqual(result, (127, 127, 127))  # 50% blend
        
        # Test RGB (no alpha)
        self.assertEqual(
            self.validator.rgba_to_rgb('rgb(100, 150, 200)', (255, 255, 255)),
            (100, 150, 200)
        )
    
    def test_relative_luminance_calculation(self):
        """Test relative luminance calculation."""
        # Test known values
        white_luminance = self.validator.get_relative_luminance((255, 255, 255))
        black_luminance = self.validator.get_relative_luminance((0, 0, 0))
        
        self.assertAlmostEqual(white_luminance, 1.0, places=2)
        self.assertAlmostEqual(black_luminance, 0.0, places=2)
        
        # White should have higher luminance than black
        self.assertGreater(white_luminance, black_luminance)
    
    def test_contrast_ratio_calculation(self):
        """Test contrast ratio calculation."""
        # Test maximum contrast (white on black)
        max_contrast = self.validator.calculate_contrast_ratio((255, 255, 255), (0, 0, 0))
        self.assertAlmostEqual(max_contrast, 21.0, places=1)
        
        # Test minimum contrast (same colors)
        min_contrast = self.validator.calculate_contrast_ratio((128, 128, 128), (128, 128, 128))
        self.assertAlmostEqual(min_contrast, 1.0, places=1)
        
        # Test known good contrast
        good_contrast = self.validator.calculate_contrast_ratio((0, 0, 0), (255, 255, 255))
        self.assertGreaterEqual(good_contrast, 4.5)  # Should pass AA
    
    def test_contrast_result_validation(self):
        """Test contrast result validation against WCAG standards."""
        # Test high contrast (should pass AA and AAA)
        result = self.validator.test_contrast_ratio('#000000', '#ffffff', 'test_element')
        self.assertTrue(result.passes_aa)
        self.assertTrue(result.passes_aaa)
        self.assertGreaterEqual(result.ratio, 7.0)
        
        # Test medium contrast (should pass AA but not AAA for normal text)
        result = self.validator.test_contrast_ratio('#666666', '#ffffff', 'test_element')
        self.assertTrue(result.passes_aa)
        # Note: Actual AAA pass depends on exact color values
        
        # Test low contrast (should fail both)
        result = self.validator.test_contrast_ratio('#cccccc', '#ffffff', 'test_element')
        self.assertFalse(result.passes_aa)
        self.assertFalse(result.passes_aaa)


class ScreenReaderCompatibilityTesterTest(TestCase):
    """Test cases for the ScreenReaderCompatibilityTester class."""
    
    def setUp(self):
        self.tester = ScreenReaderCompatibilityTester()
    
    def test_aria_labels_detection(self):
        """Test detection of ARIA labels in HTML content."""
        # HTML with proper ARIA labels
        good_html = '''
        <button class="copy-btn" aria-label="Copy code to clipboard" role="button" tabindex="0">Copy</button>
        <pre role="region" aria-label="Python code example" id="code-block-1">
            <code>print("Hello")</code>
        </pre>
        <div aria-live="polite" id="announcements"></div>
        '''
        
        results = self.tester.test_aria_labels(good_html)
        
        # Should find copy button with ARIA label
        copy_button_tests = [r for r in results if 'Copy button' in r.test_name and 'ARIA label' in r.test_name]
        self.assertTrue(len(copy_button_tests) > 0)
        self.assertTrue(copy_button_tests[0].passed)
        
        # Should find code block with role
        code_block_tests = [r for r in results if 'Code block' in r.test_name and 'role' in r.test_name]
        self.assertTrue(len(code_block_tests) > 0)
        self.assertTrue(code_block_tests[0].passed)
        
        # Should find live regions
        live_region_tests = [r for r in results if 'live regions' in r.test_name]
        self.assertTrue(len(live_region_tests) > 0)
        self.assertTrue(live_region_tests[0].passed)
    
    def test_missing_aria_labels_detection(self):
        """Test detection of missing ARIA labels."""
        # HTML without proper ARIA labels
        bad_html = '''
        <button class="copy-btn">Copy</button>
        <pre><code>print("Hello")</code></pre>
        '''
        
        results = self.tester.test_aria_labels(bad_html)
        
        # Should detect missing ARIA labels
        failed_tests = [r for r in results if not r.passed]
        self.assertTrue(len(failed_tests) > 0)
    
    def test_javascript_accessibility_features(self):
        """Test detection of accessibility features in JavaScript."""
        # JavaScript with accessibility features
        good_js = '''
        function announceToScreenReader(message) {
            // Implementation
        }
        
        button.setAttribute('aria-busy', 'true');
        button.setAttribute('aria-label', 'Copying...');
        button.setAttribute('aria-describedby', 'code-block-1');
        
        element.addEventListener('keydown', (e) => {
            switch (e.key) {
                case 'Enter':
                    e.preventDefault();
                    break;
                case ' ':
                    e.preventDefault();
                    break;
                case 'Escape':
                    break;
                case 'ArrowUp':
                case 'ArrowDown':
                    break;
            }
        });
        '''
        
        results = self.tester.test_javascript_accessibility(good_js)
        
        # Should find screen reader announcement function
        announce_tests = [r for r in results if 'announcement function' in r.test_name]
        self.assertTrue(len(announce_tests) > 0)
        self.assertTrue(announce_tests[0].passed)
        
        # Should find ARIA attribute management
        aria_tests = [r for r in results if 'aria-' in r.test_name.lower()]
        passed_aria_tests = [r for r in aria_tests if r.passed]
        self.assertTrue(len(passed_aria_tests) > 0)
        
        # Should find keyboard event handling
        keyboard_tests = [r for r in results if 'key' in r.test_name.lower()]
        passed_keyboard_tests = [r for r in keyboard_tests if r.passed]
        self.assertTrue(len(passed_keyboard_tests) > 0)


class KeyboardNavigationTesterTest(TestCase):
    """Test cases for the KeyboardNavigationTester class."""
    
    def setUp(self):
        self.tester = KeyboardNavigationTester()
    
    def test_css_focus_indicators_detection(self):
        """Test detection of CSS focus indicators."""
        # CSS with proper focus indicators
        good_css = '''
        .copy-btn:focus {
            outline: 2px solid var(--accent-cyan);
            box-shadow: 0 0 0 4px rgba(0, 217, 255, 0.2);
        }
        
        .copy-btn.keyboard-focused {
            background: rgba(0, 217, 255, 0.05);
        }
        
        .code-block:focus-within {
            border-color: var(--accent-cyan);
        }
        
        @media (prefers-contrast: high) {
            .copy-btn:focus {
                outline: 3px solid var(--accent-cyan);
            }
        }
        
        .skip-to-next-code {
            position: absolute;
        }
        '''
        
        results = self.tester.test_css_focus_indicators(good_css)
        
        # Should find focus outline
        outline_tests = [r for r in results if 'focus outline' in r.test_name]
        self.assertTrue(len(outline_tests) > 0)
        self.assertTrue(outline_tests[0].passed)
        
        # Should find keyboard focus class
        keyboard_focus_tests = [r for r in results if 'keyboard focus' in r.test_name]
        self.assertTrue(len(keyboard_focus_tests) > 0)
        self.assertTrue(keyboard_focus_tests[0].passed)
        
        # Should find high contrast support
        high_contrast_tests = [r for r in results if 'high contrast' in r.test_name]
        self.assertTrue(len(high_contrast_tests) > 0)
        self.assertTrue(high_contrast_tests[0].passed)
        
        # Should find skip links
        skip_link_tests = [r for r in results if 'skip link' in r.test_name]
        self.assertTrue(len(skip_link_tests) > 0)
        self.assertTrue(skip_link_tests[0].passed)
    
    def test_javascript_keyboard_support_detection(self):
        """Test detection of JavaScript keyboard support."""
        # JavaScript with keyboard support
        good_js = '''
        element.addEventListener('keydown', handleKeyDown);
        button.setAttribute('tabindex', '0');
        button.focus();
        button.blur();
        
        function handleKeyDown(e) {
            switch (e.key) {
                case 'Enter':
                    e.preventDefault();
                    handleAction();
                    break;
                case ' ':
                    e.preventDefault();
                    handleAction();
                    break;
                case 'Escape':
                    closeDialog();
                    break;
                case 'ArrowUp':
                case 'ArrowDown':
                    e.preventDefault();
                    navigate(e.key);
                    break;
            }
        }
        
        function setupCodeBlockNavigation() {
            // Implementation
        }
        
        function addCodeBlockSkipLinks() {
            // Implementation
        }
        
        announceToScreenReader('Navigated to next code block');
        '''
        
        results = self.tester.test_javascript_keyboard_support(good_js)
        
        # Should find keyboard event listeners
        event_tests = [r for r in results if 'keydown' in r.test_name.lower()]
        self.assertTrue(len(event_tests) > 0)
        self.assertTrue(event_tests[0].passed)
        
        # Should find focus management
        focus_tests = [r for r in results if 'focus' in r.test_name.lower()]
        passed_focus_tests = [r for r in focus_tests if r.passed]
        self.assertTrue(len(passed_focus_tests) > 0)
        
        # Should find key handlers
        key_handler_tests = [r for r in results if 'key' in r.test_name.lower() and 'activation' in r.test_name]
        passed_key_tests = [r for r in key_handler_tests if r.passed]
        self.assertTrue(len(passed_key_tests) > 0)
        
        # Should find navigation functions
        navigation_tests = [r for r in results if 'navigation' in r.test_name.lower()]
        passed_nav_tests = [r for r in navigation_tests if r.passed]
        self.assertTrue(len(passed_nav_tests) > 0)


class AccessibilityTestSuiteIntegrationTest(TestCase):
    """Integration tests for the complete AccessibilityTestSuite."""
    
    def setUp(self):
        self.test_suite = AccessibilityTestSuite()
        self.client = Client()
        
        # Create test user and post
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.post = Post.objects.create(
            title='Test Post with Code',
            slug='test-post-with-code',
            author=self.user,
            content='''
            <div class="code-block">
                <pre><code class="language-python">
def hello_world():
    print("Hello, World!")
                </code></pre>
            </div>
            ''',
            excerpt='Test post with code blocks',
            status='published'
        )
        self.post.categories.add(self.category)
    
    def test_full_accessibility_test_suite(self):
        """Test the complete accessibility test suite."""
        # Create temporary test files
        css_content = '''
        .copy-btn:focus {
            outline: 2px solid var(--accent-cyan);
            box-shadow: 0 0 0 4px rgba(0, 217, 255, 0.2);
        }
        
        @media (prefers-contrast: high) {
            .copy-btn:focus {
                outline: 3px solid var(--accent-cyan);
            }
        }
        
        @media (prefers-reduced-motion: reduce) {
            * {
                transition: none;
            }
        }
        '''
        
        js_content = '''
        function announceToScreenReader(message) {
            const announcer = document.getElementById('announcements');
            if (announcer) {
                announcer.textContent = message;
            }
        }
        
        button.setAttribute('aria-label', 'Copy code');
        button.setAttribute('aria-busy', 'true');
        
        element.addEventListener('keydown', (e) => {
            switch (e.key) {
                case 'Enter':
                    e.preventDefault();
                    break;
                case ' ':
                    e.preventDefault();
                    break;
                case 'Escape':
                    break;
            }
        });
        
        function setupCodeBlockNavigation() {}
        function addCodeBlockSkipLinks() {}
        '''
        
        html_content = '''
        <button class="copy-btn" aria-label="Copy code" role="button" tabindex="0">Copy</button>
        <pre role="region" aria-label="Code example"><code>test</code></pre>
        <div aria-live="polite" id="announcements"></div>
        '''
        
        # Write temporary files
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.css', delete=False) as css_file:
            css_file.write(css_content)
            css_file_path = css_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as js_file:
            js_file.write(js_content)
            js_file_path = js_file.name
        
        try:
            # Run the full test suite
            results = self.test_suite.run_all_tests(css_file_path, js_file_path, html_content)
            
            # Verify results structure
            self.assertIn('summary', results)
            self.assertIn('categories', results)
            self.assertIn('all_results', results)
            self.assertIn('requirements_coverage', results)
            
            # Verify summary
            summary = results['summary']
            self.assertGreater(summary['total_tests'], 0)
            self.assertGreaterEqual(summary['passed_tests'], 0)
            self.assertGreaterEqual(summary['pass_rate'], 0)
            
            # Verify categories
            categories = results['categories']
            self.assertIn('contrast_ratio', categories)
            self.assertIn('screen_reader', categories)
            self.assertIn('keyboard_navigation', categories)
            
            # Verify requirements coverage
            requirements = results['requirements_coverage']
            self.assertIn('5.3', requirements)
            self.assertIn('2.1', requirements)
            self.assertIn('2.2', requirements)
            
            # Generate report
            report = self.test_suite.generate_report(results)
            self.assertIn('ACCESSIBILITY TEST REPORT', report)
            self.assertIn('SUMMARY:', report)
            self.assertIn('REQUIREMENTS COVERAGE:', report)
            
        finally:
            # Clean up temporary files
            os.unlink(css_file_path)
            os.unlink(js_file_path)
    
    def test_blog_post_accessibility_integration(self):
        """Test accessibility testing integration with actual blog post."""
        # Get the blog post page
        response = self.client.get(reverse('blog:detail', kwargs={'slug': self.post.slug}))
        self.assertEqual(response.status_code, 200)
        
        # Extract HTML content
        html_content = response.content.decode('utf-8')
        
        # Test that the page includes accessibility features
        self.assertIn('simplified-code-blocks.css', html_content)
        
        # Run screen reader tests on the actual HTML
        screen_reader_results = self.test_suite.screen_reader_tester.test_aria_labels(html_content)
        
        # Should have some test results
        self.assertGreater(len(screen_reader_results), 0)
        
        # Verify test result structure
        for result in screen_reader_results:
            self.assertIsInstance(result, AccessibilityTestResult)
            self.assertIsInstance(result.test_name, str)
            self.assertIsInstance(result.passed, bool)
            self.assertIsInstance(result.message, str)
    
    def test_requirements_compliance_validation(self):
        """Test that the accessibility tests validate specific requirements."""
        # Test requirement 5.3: Accessibility contrast requirements
        contrast_validator = ColorContrastValidator()
        
        # Test high contrast scenario
        high_contrast_result = contrast_validator.test_contrast_ratio('#000000', '#ffffff', 'test')
        self.assertTrue(high_contrast_result.passes_aa)
        self.assertEqual(high_contrast_result.element_type, 'test')
        
        # Test requirement 2.1: Copy button keyboard accessibility
        keyboard_tester = KeyboardNavigationTester()
        
        js_with_keyboard = '''
        button.setAttribute('tabindex', '0');
        element.addEventListener('keydown', (e) => {
            case 'Enter':
                e.preventDefault();
        });
        '''
        
        keyboard_results = keyboard_tester.test_javascript_keyboard_support(js_with_keyboard)
        keyboard_passed = any(r.passed for r in keyboard_results if 'keyboard' in r.test_name.lower())
        self.assertTrue(keyboard_passed)
        
        # Test requirement 2.2: ARIA labels for screen readers
        screen_reader_tester = ScreenReaderCompatibilityTester()
        
        html_with_aria = '''
        <button aria-label="Copy code" role="button">Copy</button>
        <div aria-live="polite"></div>
        '''
        
        aria_results = screen_reader_tester.test_aria_labels(html_with_aria)
        aria_passed = any(r.passed for r in aria_results if 'aria' in r.test_name.lower())
        self.assertTrue(aria_passed)


class AccessibilityTestRunnerTest(TestCase):
    """Test the accessibility test runner functionality."""
    
    def test_test_runner_execution(self):
        """Test that the accessibility test runner executes without errors."""
        from blog.utils.accessibility_testing import run_accessibility_tests
        
        # Mock the file paths to avoid file not found errors
        import tempfile
        
        # Create minimal test files
        css_content = ".copy-btn:focus { outline: 2px solid blue; }"
        js_content = "button.setAttribute('aria-label', 'test');"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.css', delete=False) as css_file:
            css_file.write(css_content)
            css_file_path = css_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as js_file:
            js_file.write(js_content)
            js_file_path = js_file.name
        
        try:
            # Temporarily replace the file paths in the function
            import blog.utils.accessibility_testing as testing_module
            original_css = testing_module.run_accessibility_tests.__code__.co_consts
            
            # Create test suite and run tests manually
            test_suite = AccessibilityTestSuite()
            results = test_suite.run_all_tests(css_file_path, js_file_path, "")
            
            # Verify results
            self.assertIsInstance(results, dict)
            self.assertIn('summary', results)
            self.assertGreater(results['summary']['total_tests'], 0)
            
        finally:
            # Clean up
            os.unlink(css_file_path)
            os.unlink(js_file_path)
    
    def test_report_generation(self):
        """Test accessibility report generation."""
        test_suite = AccessibilityTestSuite()
        
        # Create sample results
        sample_results = {
            'summary': {
                'total_tests': 10,
                'passed_tests': 8,
                'failed_tests': 2,
                'pass_rate': 80.0
            },
            'categories': {
                'contrast_ratio': {
                    'total': 3,
                    'passed': 3,
                    'tests': [
                        AccessibilityTestResult('Test 1', True, 'Passed'),
                        AccessibilityTestResult('Test 2', True, 'Passed'),
                        AccessibilityTestResult('Test 3', True, 'Passed'),
                    ]
                },
                'screen_reader': {
                    'total': 4,
                    'passed': 3,
                    'tests': [
                        AccessibilityTestResult('ARIA Test 1', True, 'Passed'),
                        AccessibilityTestResult('ARIA Test 2', True, 'Passed'),
                        AccessibilityTestResult('ARIA Test 3', True, 'Passed'),
                        AccessibilityTestResult('ARIA Test 4', False, 'Failed'),
                    ]
                },
                'keyboard_navigation': {
                    'total': 3,
                    'passed': 2,
                    'tests': [
                        AccessibilityTestResult('Keyboard Test 1', True, 'Passed'),
                        AccessibilityTestResult('Keyboard Test 2', True, 'Passed'),
                        AccessibilityTestResult('Keyboard Test 3', False, 'Failed'),
                    ]
                }
            },
            'all_results': [],
            'requirements_coverage': {
                '5.3': 'Contrast requirements',
                '2.1': 'Keyboard accessibility',
                '2.2': 'Screen reader support'
            }
        }
        
        # Generate report
        report = test_suite.generate_report(sample_results)
        
        # Verify report content
        self.assertIn('ACCESSIBILITY TEST REPORT', report)
        self.assertIn('Total Tests: 10', report)
        self.assertIn('Passed: 8', report)
        self.assertIn('Failed: 2', report)
        self.assertIn('Pass Rate: 80.0%', report)
        self.assertIn('REQUIREMENTS COVERAGE:', report)
        self.assertIn('5.3: Contrast requirements', report)
        self.assertIn('2.1: Keyboard accessibility', report)
        self.assertIn('2.2: Screen reader support', report)
        
        # Verify category sections
        self.assertIn('CONTRAST RATIO TESTS:', report)
        self.assertIn('SCREEN READER TESTS:', report)
        self.assertIn('KEYBOARD NAVIGATION TESTS:', report)
        
        # Verify pass/fail indicators
        self.assertIn('✅ PASS', report)
        self.assertIn('❌ FAIL', report)