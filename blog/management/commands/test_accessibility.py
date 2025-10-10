"""
Django Management Command for Running Accessibility Tests

This command provides a convenient way to run accessibility tests
for the simplified code blocks feature from the command line.

Usage:
    python manage.py test_accessibility
    python manage.py test_accessibility --report-file accessibility_report.txt
    python manage.py test_accessibility --verbose
    python manage.py test_accessibility --category contrast
"""

import os
import json
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from blog.utils.accessibility_testing import (
    AccessibilityTestSuite,
    run_accessibility_tests
)


class Command(BaseCommand):
    help = 'Run accessibility tests for simplified code blocks feature'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--css-file',
            type=str,
            default='static/css/simplified-code-blocks.css',
            help='Path to CSS file to test (default: static/css/simplified-code-blocks.css)'
        )
        
        parser.add_argument(
            '--js-file',
            type=str,
            default='static/js/blog-detail.js',
            help='Path to JavaScript file to test (default: static/js/blog-detail.js)'
        )
        
        parser.add_argument(
            '--report-file',
            type=str,
            help='Output file for accessibility test report'
        )
        
        parser.add_argument(
            '--category',
            type=str,
            choices=['contrast', 'screen-reader', 'keyboard', 'all'],
            default='all',
            help='Category of tests to run (default: all)'
        )
        
        parser.add_argument(
            '--format',
            type=str,
            choices=['text', 'json'],
            default='text',
            help='Output format for results (default: text)'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )
        
        parser.add_argument(
            '--fail-on-error',
            action='store_true',
            help='Exit with error code if any tests fail'
        )
        
        parser.add_argument(
            '--html-sample',
            type=str,
            help='Path to HTML file to test for screen reader compatibility'
        )
    
    def handle(self, *args, **options):
        """Execute the accessibility tests."""
        self.verbosity = options.get('verbosity', 1)
        self.verbose = options.get('verbose', False)
        
        # Display header
        self.stdout.write(
            self.style.SUCCESS('=' * 60)
        )
        self.stdout.write(
            self.style.SUCCESS('ACCESSIBILITY TESTING - SIMPLIFIED CODE BLOCKS')
        )
        self.stdout.write(
            self.style.SUCCESS('=' * 60)
        )
        
        # Validate file paths
        css_file = options['css_file']
        js_file = options['js_file']
        
        if not os.path.exists(css_file):
            self.stdout.write(
                self.style.WARNING(f'CSS file not found: {css_file}')
            )
            self.stdout.write(
                self.style.WARNING('Some tests may be skipped.')
            )
        
        if not os.path.exists(js_file):
            self.stdout.write(
                self.style.WARNING(f'JavaScript file not found: {js_file}')
            )
            self.stdout.write(
                self.style.WARNING('Some tests may be skipped.')
            )
        
        # Load HTML sample if provided
        html_content = ""
        if options.get('html_sample'):
            html_file = options['html_sample']
            if os.path.exists(html_file):
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                if self.verbose:
                    self.stdout.write(f'Loaded HTML sample from: {html_file}')
            else:
                self.stdout.write(
                    self.style.WARNING(f'HTML sample file not found: {html_file}')
                )
        else:
            # Use default sample HTML
            html_content = self._get_default_html_sample()
        
        # Initialize test suite
        test_suite = AccessibilityTestSuite()
        
        try:
            # Run tests based on category
            category = options['category']
            
            if category == 'all':
                results = test_suite.run_all_tests(css_file, js_file, html_content)
            else:
                results = self._run_category_tests(test_suite, category, css_file, js_file, html_content)
            
            # Display results
            self._display_results(results, options)
            
            # Save report if requested
            if options.get('report_file'):
                self._save_report(test_suite, results, options['report_file'], options['format'])
            
            # Check for failures
            if options.get('fail_on_error') and results['summary']['failed_tests'] > 0:
                raise CommandError(
                    f"Accessibility tests failed: {results['summary']['failed_tests']} out of {results['summary']['total_tests']} tests failed"
                )
            
            # Display success message
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nAccessibility testing completed successfully!"
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Results: {results['summary']['passed_tests']}/{results['summary']['total_tests']} tests passed "
                    f"({results['summary']['pass_rate']:.1f}%)"
                )
            )
            
        except Exception as e:
            raise CommandError(f'Error running accessibility tests: {str(e)}')
    
    def _get_default_html_sample(self):
        """Get default HTML sample for testing."""
        return '''
        <div class="code-block">
            <div class="code-header">
                <span class="code-language">Python</span>
                <button class="copy-btn" aria-label="Copy Python code to clipboard" 
                        role="button" tabindex="0" aria-describedby="code-block-0">
                    <i class="fas fa-copy"></i> Copy
                </button>
            </div>
            <pre id="code-block-0" role="region" aria-label="Python code example">
                <code class="language-python">
def hello_world():
    print("Hello, World!")
    return "success"
                </code>
            </pre>
        </div>
        
        <div class="code-block">
            <div class="code-header">
                <span class="code-language">JavaScript</span>
                <button class="copy-btn" aria-label="Copy JavaScript code to clipboard" 
                        role="button" tabindex="0" aria-describedby="code-block-1">
                    <i class="fas fa-copy"></i> Copy
                </button>
            </div>
            <pre id="code-block-1" role="region" aria-label="JavaScript code example">
                <code class="language-javascript">
function greet(name) {
    console.log(`Hello, ${name}!`);
    return true;
}
                </code>
            </pre>
        </div>
        
        <p>This is a paragraph with <code>inline code</code> that should be accessible.</p>
        
        <div aria-live="polite" id="announcements" class="sr-only"></div>
        <a href="#code-block-1" class="skip-to-next-code">Skip to next code block</a>
        '''
    
    def _run_category_tests(self, test_suite, category, css_file, js_file, html_content):
        """Run tests for a specific category."""
        if self.verbose:
            self.stdout.write(f'Running {category} tests...')
        
        all_results = []
        
        if category == 'contrast':
            results = test_suite.run_contrast_tests(css_file)
            all_results.extend(results)
            
        elif category == 'screen-reader':
            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    js_content = f.read()
            except FileNotFoundError:
                js_content = ""
            
            results = test_suite.run_screen_reader_tests(html_content, js_content)
            all_results.extend(results)
            
        elif category == 'keyboard':
            try:
                with open(css_file, 'r', encoding='utf-8') as f:
                    css_content = f.read()
            except FileNotFoundError:
                css_content = ""
            
            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    js_content = f.read()
            except FileNotFoundError:
                js_content = ""
            
            results = test_suite.run_keyboard_navigation_tests(css_content, js_content)
            all_results.extend(results)
        
        # Format results similar to run_all_tests
        total_tests = len(all_results)
        passed_tests = sum(1 for result in all_results if result.passed)
        failed_tests = total_tests - passed_tests
        
        return {
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'pass_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            'categories': {
                category.replace('-', '_'): {
                    'total': total_tests,
                    'passed': passed_tests,
                    'tests': all_results
                }
            },
            'all_results': all_results,
            'requirements_coverage': {
                '5.3': 'Accessibility contrast requirements',
                '2.1': 'Copy button keyboard accessibility',
                '2.2': 'ARIA labels for screen readers'
            }
        }
    
    def _display_results(self, results, options):
        """Display test results to console."""
        format_type = options.get('format', 'text')
        
        if format_type == 'json':
            # Convert results to JSON-serializable format
            json_results = self._convert_to_json_serializable(results)
            self.stdout.write(json.dumps(json_results, indent=2))
            return
        
        # Text format display
        summary = results['summary']
        
        self.stdout.write('\n' + '=' * 40)
        self.stdout.write('TEST SUMMARY')
        self.stdout.write('=' * 40)
        
        self.stdout.write(f'Total Tests: {summary["total_tests"]}')
        
        if summary['passed_tests'] > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Passed: {summary["passed_tests"]}')
            )
        
        if summary['failed_tests'] > 0:
            self.stdout.write(
                self.style.ERROR(f'Failed: {summary["failed_tests"]}')
            )
        
        self.stdout.write(f'Pass Rate: {summary["pass_rate"]:.1f}%')
        
        # Display category results
        if self.verbose or options.get('verbosity', 1) >= 2:
            self.stdout.write('\n' + '=' * 40)
            self.stdout.write('DETAILED RESULTS')
            self.stdout.write('=' * 40)
            
            for category_name, category_data in results['categories'].items():
                self.stdout.write(f'\n{category_name.upper().replace("_", " ")} TESTS:')
                self.stdout.write(f'Passed: {category_data["passed"]}/{category_data["total"]}')
                
                for test in category_data['tests']:
                    if test.passed:
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✅ {test.test_name}')
                        )
                        if self.verbose:
                            self.stdout.write(f'     {test.message}')
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'  ❌ {test.test_name}')
                        )
                        self.stdout.write(f'     {test.message}')
                        
                        if test.details and self.verbose:
                            for key, value in test.details.items():
                                if isinstance(value, str) and len(value) > 100:
                                    value = value[:100] + "..."
                                self.stdout.write(f'     {key}: {value}')
        
        # Display requirements coverage
        self.stdout.write('\n' + '=' * 40)
        self.stdout.write('REQUIREMENTS COVERAGE')
        self.stdout.write('=' * 40)
        
        for req, description in results['requirements_coverage'].items():
            self.stdout.write(f'{req}: {description}')
    
    def _save_report(self, test_suite, results, report_file, format_type):
        """Save test report to file."""
        try:
            if format_type == 'json':
                json_results = self._convert_to_json_serializable(results)
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(json_results, f, indent=2)
            else:
                report_text = test_suite.generate_report(results, report_file)
            
            self.stdout.write(
                self.style.SUCCESS(f'Report saved to: {report_file}')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error saving report: {str(e)}')
            )
    
    def _convert_to_json_serializable(self, results):
        """Convert results to JSON-serializable format."""
        json_results = {
            'summary': results['summary'],
            'requirements_coverage': results['requirements_coverage'],
            'categories': {}
        }
        
        for category_name, category_data in results['categories'].items():
            json_results['categories'][category_name] = {
                'total': category_data['total'],
                'passed': category_data['passed'],
                'tests': [
                    {
                        'test_name': test.test_name,
                        'passed': test.passed,
                        'message': test.message,
                        'details': test.details
                    }
                    for test in category_data['tests']
                ]
            }
        
        return json_results