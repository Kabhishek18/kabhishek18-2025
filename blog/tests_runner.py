"""
Comprehensive test runner for blog engagement features.
Runs all tests and provides detailed coverage and performance reports.
"""
import unittest
import time
import sys
from django.test import TestCase
from django.test.runner import DiscoverRunner
from django.core.management import call_command
from django.conf import settings
from io import StringIO


class BlogEngagementTestRunner:
    """Custom test runner for blog engagement features"""
    
    def __init__(self):
        self.test_modules = [
            'blog.tests',  # Original newsletter tests
            'blog.tests_models_comprehensive',  # Model tests
            'blog.tests_email_integration',  # Email workflow tests
            'blog.tests_comments',  # Comment system tests
            'blog.tests_social_sharing',  # Social sharing tests
            'blog.tests_author_profiles',  # Author profile tests
            'blog.tests_content_discovery',  # Content discovery tests
            'blog.tests_multimedia',  # Multimedia tests
            'blog.tests_table_of_contents',  # TOC tests
            'blog.tests_performance',  # Performance tests
        ]
        
        self.results = {}
        self.total_tests = 0
        self.total_failures = 0
        self.total_errors = 0
        self.total_time = 0
    
    def run_all_tests(self):
        """Run all test modules and collect results"""
        print("=" * 80)
        print("BLOG ENGAGEMENT FEATURES - COMPREHENSIVE TEST SUITE")
        print("=" * 80)
        print()
        
        overall_start_time = time.time()
        
        for module in self.test_modules:
            print(f"Running tests for {module}...")
            print("-" * 60)
            
            start_time = time.time()
            result = self._run_module_tests(module)
            end_time = time.time()
            
            execution_time = end_time - start_time
            self.results[module] = {
                'result': result,
                'time': execution_time,
                'tests': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors)
            }
            
            self.total_tests += result.testsRun
            self.total_failures += len(result.failures)
            self.total_errors += len(result.errors)
            
            print(f"Tests: {result.testsRun}, "
                  f"Failures: {len(result.failures)}, "
                  f"Errors: {len(result.errors)}, "
                  f"Time: {execution_time:.2f}s")
            print()
        
        overall_end_time = time.time()
        self.total_time = overall_end_time - overall_start_time
        
        self._print_summary()
        self._print_detailed_results()
        
        return self.total_failures == 0 and self.total_errors == 0
    
    def _run_module_tests(self, module_name):
        """Run tests for a specific module"""
        # Capture stdout to avoid cluttering output
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            # Import the module
            __import__(module_name)
            
            # Create test suite
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromName(module_name)
            
            # Run tests
            runner = unittest.TextTestRunner(stream=StringIO(), verbosity=0)
            result = runner.run(suite)
            
            return result
            
        except ImportError as e:
            print(f"Warning: Could not import {module_name}: {e}")
            # Create a dummy result
            result = unittest.TestResult()
            result.testsRun = 0
            return result
        
        finally:
            sys.stdout = old_stdout
    
    def _print_summary(self):
        """Print test execution summary"""
        print("=" * 80)
        print("TEST EXECUTION SUMMARY")
        print("=" * 80)
        print(f"Total Tests Run: {self.total_tests}")
        print(f"Total Failures: {self.total_failures}")
        print(f"Total Errors: {self.total_errors}")
        print(f"Total Time: {self.total_time:.2f} seconds")
        print(f"Success Rate: {((self.total_tests - self.total_failures - self.total_errors) / max(self.total_tests, 1) * 100):.1f}%")
        print()
        
        if self.total_failures == 0 and self.total_errors == 0:
            print("🎉 ALL TESTS PASSED! 🎉")
        else:
            print("❌ SOME TESTS FAILED")
        print()
    
    def _print_detailed_results(self):
        """Print detailed results for each module"""
        print("=" * 80)
        print("DETAILED RESULTS BY MODULE")
        print("=" * 80)
        
        for module, data in self.results.items():
            status = "✅ PASS" if (data['failures'] == 0 and data['errors'] == 0) else "❌ FAIL"
            print(f"{module:<40} {status}")
            print(f"  Tests: {data['tests']:<3} Failures: {data['failures']:<3} "
                  f"Errors: {data['errors']:<3} Time: {data['time']:.2f}s")
            
            # Print failure details if any
            if data['failures'] > 0:
                print("  Failures:")
                for failure in data['result'].failures:
                    print(f"    - {failure[0]}")
            
            if data['errors'] > 0:
                print("  Errors:")
                for error in data['result'].errors:
                    print(f"    - {error[0]}")
            
            print()
    
    def run_coverage_report(self):
        """Generate coverage report"""
        try:
            import coverage
            
            print("=" * 80)
            print("GENERATING COVERAGE REPORT")
            print("=" * 80)
            
            # Initialize coverage
            cov = coverage.Coverage()
            cov.start()
            
            # Run tests
            self.run_all_tests()
            
            # Stop coverage and generate report
            cov.stop()
            cov.save()
            
            print("\nCoverage Report:")
            print("-" * 40)
            cov.report(show_missing=True)
            
            # Generate HTML report
            cov.html_report(directory='htmlcov')
            print("\nHTML coverage report generated in 'htmlcov' directory")
            
        except ImportError:
            print("Coverage.py not installed. Install with: pip install coverage")
        except Exception as e:
            print(f"Error generating coverage report: {e}")


class BlogEngagementTestCase(TestCase):
    """Base test case for blog engagement features"""
    
    @classmethod
    def setUpClass(cls):
        """Set up class-level test data"""
        super().setUpClass()
        # Any common setup for all blog engagement tests
    
    def setUp(self):
        """Set up test data for each test"""
        # Clear cache before each test
        from django.core.cache import cache
        cache.clear()
    
    def tearDown(self):
        """Clean up after each test"""
        # Clear cache after each test
        from django.core.cache import cache
        cache.clear()
    
    def assertQueryCountLessThan(self, num, func, *args, **kwargs):
        """Assert that a function executes fewer than num queries"""
        from django.test.utils import override_settings
        from django.db import connection
        
        with override_settings(DEBUG=True):
            initial_queries = len(connection.queries)
            func(*args, **kwargs)
            final_queries = len(connection.queries)
            
            query_count = final_queries - initial_queries
            self.assertLess(query_count, num, 
                          f"Expected fewer than {num} queries, got {query_count}")
    
    def assertExecutionTimeLessThan(self, max_time, func, *args, **kwargs):
        """Assert that a function executes in less than max_time seconds"""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        self.assertLess(execution_time, max_time,
                       f"Expected execution time < {max_time}s, got {execution_time:.3f}s")
        
        return result


def run_comprehensive_tests():
    """Main function to run comprehensive tests"""
    runner = BlogEngagementTestRunner()
    success = runner.run_all_tests()
    
    if not success:
        sys.exit(1)
    
    return success


def run_with_coverage():
    """Run tests with coverage report"""
    runner = BlogEngagementTestRunner()
    runner.run_coverage_report()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--coverage':
        run_with_coverage()
    else:
        run_comprehensive_tests()