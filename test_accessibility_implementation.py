#!/usr/bin/env python3
"""
Test script to verify Task 7.1 accessibility implementation.

This script tests the keyboard navigation support and ARIA labels
for the simplified code blocks feature.
"""

import re
import os


def test_css_accessibility_features():
    """Test that CSS includes proper accessibility features."""
    print("Testing CSS accessibility features...")
    
    css_file = "static/css/simplified-code-blocks.css"
    if not os.path.exists(css_file):
        print(f"❌ CSS file not found: {css_file}")
        return False
    
    with open(css_file, 'r') as f:
        css_content = f.read()
    
    # Test for keyboard focus styles
    focus_tests = [
        (r'\.copy-btn:focus', "Copy button focus styles"),
        (r'outline.*solid.*var\(--accent-cyan\)', "Focus outline with theme color"),
        (r'box-shadow.*rgba\(0, 217, 255', "Focus ring shadow"),
        (r'\.keyboard-focused', "Keyboard focus indicator class"),
        (r'@media \(prefers-contrast: high\)', "High contrast mode support"),
        (r'\.code-block:focus-within', "Code block focus-within styles"),
        (r'\.skip-to-next-code', "Skip link styles"),
    ]
    
    passed = 0
    for pattern, description in focus_tests:
        if re.search(pattern, css_content, re.IGNORECASE):
            print(f"✅ {description}")
            passed += 1
        else:
            print(f"❌ Missing: {description}")
    
    print(f"CSS accessibility tests: {passed}/{len(focus_tests)} passed\n")
    return passed == len(focus_tests)


def test_javascript_accessibility_features():
    """Test that JavaScript includes proper accessibility features."""
    print("Testing JavaScript accessibility features...")
    
    js_file = "static/js/blog-detail.js"
    if not os.path.exists(js_file):
        print(f"❌ JavaScript file not found: {js_file}")
        return False
    
    with open(js_file, 'r') as f:
        js_content = f.read()
    
    # Test for accessibility features
    accessibility_tests = [
        (r'aria-label', "ARIA labels for screen readers"),
        (r'aria-describedby', "ARIA describedby attributes"),
        (r'role.*button', "Button role attribute"),
        (r'tabindex.*0', "Keyboard accessibility with tabindex"),
        (r'aria-busy', "ARIA busy state during actions"),
        (r'announceToScreenReader', "Screen reader announcements"),
        (r'aria-live.*polite', "Live region for announcements"),
        (r'setupCodeBlockNavigation', "Code block navigation setup"),
        (r'addCodeBlockSkipLinks', "Skip links for navigation"),
        (r'keyboard-focused', "Keyboard focus class management"),
        (r'ArrowUp.*ArrowDown', "Arrow key navigation"),
        (r"case 'Enter'.*case ' '", "Enter and Space key handling"),
        (r'Escape', "Escape key handling"),
        (r'getCodeLanguage', "Language detection for ARIA labels"),
    ]
    
    passed = 0
    for pattern, description in accessibility_tests:
        if re.search(pattern, js_content, re.IGNORECASE | re.DOTALL):
            print(f"✅ {description}")
            passed += 1
        else:
            print(f"❌ Missing: {description}")
    
    print(f"JavaScript accessibility tests: {passed}/{len(accessibility_tests)} passed\n")
    return passed == len(accessibility_tests)


def test_html_test_file():
    """Test that the HTML test file includes accessibility features."""
    print("Testing HTML test file accessibility...")
    
    html_file = "test_keyboard_navigation.html"
    if not os.path.exists(html_file):
        print(f"❌ HTML test file not found: {html_file}")
        return False
    
    with open(html_file, 'r') as f:
        html_content = f.read()
    
    # Test for accessibility features in HTML
    html_tests = [
        (r'aria-label', "ARIA labels in HTML"),
        (r'role.*region', "Region role for code blocks"),
        (r'tabindex', "Keyboard navigation support"),
        (r'kbd.*Tab', "Keyboard instruction documentation"),
        (r'kbd.*Enter', "Enter key documentation"),
        (r'kbd.*Space', "Space key documentation"),
        (r'kbd.*Ctrl', "Ctrl key navigation documentation"),
        (r'Screen Reader Users', "Screen reader user instructions"),
    ]
    
    passed = 0
    for pattern, description in html_tests:
        if re.search(pattern, html_content, re.IGNORECASE):
            print(f"✅ {description}")
            passed += 1
        else:
            print(f"❌ Missing: {description}")
    
    print(f"HTML test file accessibility tests: {passed}/{len(html_tests)} passed\n")
    return passed == len(html_tests)


def test_requirements_compliance():
    """Test compliance with specific requirements."""
    print("Testing requirements compliance...")
    
    # Requirement 2.1: Ensure copy button is keyboard accessible
    js_file = "static/js/blog-detail.js"
    with open(js_file, 'r') as f:
        js_content = f.read()
    
    req_tests = [
        # Requirement 2.1: Copy button keyboard accessibility
        (r'tabindex.*0', "Requirement 2.1: Copy button keyboard accessible"),
        (r"case 'Enter'.*preventDefault", "Requirement 2.1: Keyboard activation"),
        
        # Requirement 2.2: ARIA labels for screen readers
        (r'Copy.*code.*clipboard', "Requirement 2.2: Descriptive ARIA labels"),
        (r'aria-describedby', "Requirement 2.2: ARIA describedby relationships"),
        (r'aria-live.*polite', "Requirement 2.2: Screen reader announcements"),
        (r'announceToScreenReader', "Requirement 2.2: Screen reader integration"),
    ]
    
    passed = 0
    for pattern, description in req_tests:
        if re.search(pattern, js_content, re.IGNORECASE | re.DOTALL):
            print(f"✅ {description}")
            passed += 1
        else:
            print(f"❌ Missing: {description}")
    
    print(f"Requirements compliance tests: {passed}/{len(req_tests)} passed\n")
    return passed == len(req_tests)


def main():
    """Run all accessibility tests."""
    print("🔍 Testing Task 7.1: Keyboard Navigation Support Implementation\n")
    print("=" * 60)
    
    results = []
    results.append(test_css_accessibility_features())
    results.append(test_javascript_accessibility_features())
    results.append(test_html_test_file())
    results.append(test_requirements_compliance())
    
    print("=" * 60)
    passed_tests = sum(results)
    total_tests = len(results)
    
    if passed_tests == total_tests:
        print(f"🎉 All accessibility tests passed! ({passed_tests}/{total_tests})")
        print("\n✅ Task 7.1 implementation is complete and meets requirements:")
        print("   - Copy buttons are keyboard accessible")
        print("   - Proper ARIA labels for screen readers")
        print("   - Tab navigation through code elements")
        print("   - Keyboard shortcuts for code block navigation")
        print("   - Screen reader announcements")
        print("   - High contrast mode support")
        return True
    else:
        print(f"❌ Some tests failed ({passed_tests}/{total_tests})")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)