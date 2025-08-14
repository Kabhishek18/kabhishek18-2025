"""
Unit tests for schema validation utilities.

Tests all validation methods for Schema.org compliance, Google Rich Results,
JSON-LD format validation, and automated testing utilities.
"""

import json
from datetime import datetime
from unittest.mock import Mock, patch

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User

from blog.models import Post, Category, Tag, AuthorProfile
from blog.services.schema_service import SchemaService
from blog.utils.schema_validation import SchemaValidator, SchemaTestRunner


class SchemaValidatorTestCase(TestCase):
    """Test cases for SchemaValidator utility."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        
        # Create test user and post
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        
        self.post = Post.objects.create(
            title='Test Post for Schema Validation',
            slug='test-post-schema-validation',
            author=self.user,
            content='Test content for schema validation testing.',
            excerpt='Test excerpt',
            status='published'
        )
        
        self.request = self.factory.get('/test/')
        self.request.META['HTTP_HOST'] = 'testserver'
        
        # Generate valid schema for testing
        self.valid_article_schema = SchemaService.generate_article_schema(self.post, self.request)

    def test_validate_schema_org_compliance_valid_article(self):
        """Test Schema.org validation with valid Article schema."""
        result = SchemaValidator.validate_schema_org_compliance(self.valid_article_schema)
        
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['schema_type'], 'Article')
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(len(result['missing_required']), 0)

    def test_validate_schema_org_compliance_missing_context(self):
        """Test Schema.org validation with missing @context."""
        invalid_schema = self.valid_article_schema.copy()
        del invalid_schema['@context']
        
        result = SchemaValidator.validate_schema_org_compliance(invalid_schema)
        
        self.assertFalse(result['is_valid'])
        self.assertIn('Missing @context property', result['errors'])

    def test_validate_schema_org_compliance_missing_type(self):
        """Test Schema.org validation with missing @type."""
        invalid_schema = self.valid_article_schema.copy()
        del invalid_schema['@type']
        
        result = SchemaValidator.validate_schema_org_compliance(invalid_schema)
        
        self.assertFalse(result['is_valid'])
        self.assertIn('Missing @type property', result['errors'])

    def test_validate_schema_org_compliance_missing_required_fields(self):
        """Test Schema.org validation with missing required fields."""
        invalid_schema = {
            '@context': 'https://schema.org',
            '@type': 'Article',
            'headline': 'Test Article'
            # Missing author, datePublished
        }
        
        result = SchemaValidator.validate_schema_org_compliance(invalid_schema)
        
        self.assertFalse(result['is_valid'])
        self.assertIn('author', result['missing_required'])
        self.assertIn('datePublished', result['missing_required'])

    def test_validate_schema_org_compliance_invalid_context(self):
        """Test Schema.org validation with invalid @context."""
        invalid_schema = self.valid_article_schema.copy()
        invalid_schema['@context'] = 'https://invalid-context.org'
        
        result = SchemaValidator.validate_schema_org_compliance(invalid_schema)
        
        self.assertTrue(result['is_valid'])  # Still valid, just warning
        self.assertIn('Non-standard @context', result['warnings'][0])

    def test_validate_schema_org_compliance_person_schema(self):
        """Test Schema.org validation with Person schema."""
        person_schema = {
            '@context': 'https://schema.org',
            '@type': 'Person',
            'name': 'Test Person'
        }
        
        result = SchemaValidator.validate_schema_org_compliance(person_schema)
        
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['schema_type'], 'Person')

    def test_validate_schema_org_compliance_organization_schema(self):
        """Test Schema.org validation with Organization schema."""
        org_schema = {
            '@context': 'https://schema.org',
            '@type': 'Organization',
            'name': 'Test Organization'
        }
        
        result = SchemaValidator.validate_schema_org_compliance(org_schema)
        
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['schema_type'], 'Organization')

    def test_validate_schema_org_compliance_nested_schemas(self):
        """Test Schema.org validation with nested schemas."""
        schema_with_nested = self.valid_article_schema.copy()
        schema_with_nested['author'] = {
            '@type': 'Person'
            # Missing required 'name' field
        }
        
        result = SchemaValidator.validate_schema_org_compliance(schema_with_nested)
        
        self.assertFalse(result['is_valid'])
        self.assertTrue(any('author.' in error for error in result['errors']))

    def test_validate_schema_org_compliance_invalid_input(self):
        """Test Schema.org validation with invalid input types."""
        # Test with non-dictionary input
        result = SchemaValidator.validate_schema_org_compliance("not a dict")
        self.assertFalse(result['is_valid'])
        self.assertIn('Schema data must be a dictionary', result['errors'])
        
        # Test with None input
        result = SchemaValidator.validate_schema_org_compliance(None)
        self.assertFalse(result['is_valid'])

    def test_validate_google_rich_results_valid_article(self):
        """Test Google Rich Results validation with valid Article."""
        result = SchemaValidator.validate_google_rich_results(self.valid_article_schema)
        
        self.assertTrue(result['is_valid'])
        self.assertTrue(result['rich_results_eligible'])

    def test_validate_google_rich_results_missing_required(self):
        """Test Google Rich Results validation with missing required fields."""
        incomplete_schema = {
            '@context': 'https://schema.org',
            '@type': 'Article',
            'headline': 'Test Article'
            # Missing image, datePublished, dateModified
        }
        
        result = SchemaValidator.validate_google_rich_results(incomplete_schema)
        
        self.assertFalse(result['is_valid'])
        self.assertFalse(result['rich_results_eligible'])
        self.assertIn('image', result['missing_required'])
        self.assertIn('datePublished', result['missing_required'])
        self.assertIn('dateModified', result['missing_required'])

    def test_validate_google_rich_results_missing_recommended(self):
        """Test Google Rich Results validation with missing recommended fields."""
        minimal_schema = {
            '@context': 'https://schema.org',
            '@type': 'Article',
            'headline': 'Test Article',
            'image': ['https://example.com/image.jpg'],
            'datePublished': '2024-01-01T00:00:00Z',
            'dateModified': '2024-01-01T00:00:00Z'
            # Missing author, publisher, description, url (recommended)
        }
        
        result = SchemaValidator.validate_google_rich_results(minimal_schema)
        
        self.assertTrue(result['is_valid'])
        self.assertTrue(result['rich_results_eligible'])
        self.assertIn('author', result['missing_recommended'])
        self.assertIn('publisher', result['missing_recommended'])

    def test_validate_google_rich_results_unsupported_type(self):
        """Test Google Rich Results validation with unsupported schema type."""
        unsupported_schema = {
            '@context': 'https://schema.org',
            '@type': 'UnsupportedType',
            'name': 'Test'
        }
        
        result = SchemaValidator.validate_google_rich_results(unsupported_schema)
        
        self.assertIn('No Google Rich Results requirements defined', result['warnings'][0])

    def test_validate_json_ld_format_valid_json(self):
        """Test JSON-LD format validation with valid JSON."""
        json_string = json.dumps(self.valid_article_schema)
        result = SchemaValidator.validate_json_ld_format(json_string)
        
        self.assertTrue(result['is_valid'])
        self.assertIsNotNone(result['parsed_data'])

    def test_validate_json_ld_format_invalid_json(self):
        """Test JSON-LD format validation with invalid JSON."""
        invalid_json = '{"@context": "https://schema.org", "@type": "Article", "headline": "Test"'  # Missing closing brace
        result = SchemaValidator.validate_json_ld_format(invalid_json)
        
        self.assertFalse(result['is_valid'])
        self.assertIn('Invalid JSON format', result['errors'][0])

    def test_validate_json_ld_format_array_of_objects(self):
        """Test JSON-LD format validation with array of schema objects."""
        schema_array = [
            self.valid_article_schema,
            {
                '@context': 'https://schema.org',
                '@type': 'Person',
                'name': 'Test Person'
            }
        ]
        
        json_string = json.dumps(schema_array)
        result = SchemaValidator.validate_json_ld_format(json_string)
        
        self.assertTrue(result['is_valid'])
        self.assertIsInstance(result['parsed_data'], list)

    def test_validate_json_ld_format_invalid_structure(self):
        """Test JSON-LD format validation with invalid structure."""
        invalid_structure = '"just a string"'
        result = SchemaValidator.validate_json_ld_format(invalid_structure)
        
        self.assertFalse(result['is_valid'])
        self.assertIn('JSON-LD must be an object or array', result['errors'][0])

    def test_generate_validation_report_comprehensive(self):
        """Test comprehensive validation report generation."""
        report = SchemaValidator.generate_validation_report(self.valid_article_schema)
        
        self.assertIn('timestamp', report)
        self.assertIn('schema_org_validation', report)
        self.assertIn('google_rich_results_validation', report)
        self.assertIn('json_ld_validation', report)
        self.assertIn('overall_status', report)
        self.assertIn('recommendations', report)
        
        self.assertEqual(report['overall_status'], 'valid')

    def test_generate_validation_report_partial_validity(self):
        """Test validation report with partially valid schema."""
        partial_schema = {
            '@context': 'https://schema.org',
            '@type': 'Article',
            'headline': 'Test Article',
            'author': {'@type': 'Person', 'name': 'Test Author'},
            'datePublished': '2024-01-01T00:00:00Z'
            # Missing some Google Rich Results requirements
        }
        
        report = SchemaValidator.generate_validation_report(partial_schema)
        
        # Should be valid for Schema.org but not fully compliant with Google Rich Results
        self.assertTrue(report['schema_org_validation']['is_valid'])
        self.assertFalse(report['google_rich_results_validation']['is_valid'])

    def test_is_valid_iso_date(self):
        """Test ISO date validation helper method."""
        # Valid ISO dates
        valid_dates = [
            '2024-01-01T00:00:00Z',
            '2024-01-01T00:00:00+00:00',
            '2024-01-01T00:00:00.000Z',
            '2024-01-01T00:00:00',
            '2024-01-01'
        ]
        
        for date_str in valid_dates:
            self.assertTrue(SchemaValidator._is_valid_iso_date(date_str), f'Failed for: {date_str}')
        
        # Invalid dates
        invalid_dates = [
            '2024/01/01',
            'January 1, 2024',
            '2024-13-01',  # Invalid month
            '2024-01-32',  # Invalid day
            'not a date',
            None,
            123
        ]
        
        for date_str in invalid_dates:
            self.assertFalse(SchemaValidator._is_valid_iso_date(date_str), f'Should fail for: {date_str}')

    def test_is_valid_iso_duration(self):
        """Test ISO duration validation helper method."""
        # Valid durations
        valid_durations = [
            'PT5M',
            'PT1H30M',
            'PT2H',
            'PT45S',
            'PT1H30M45S'
        ]
        
        for duration in valid_durations:
            self.assertTrue(SchemaValidator._is_valid_iso_duration(duration), f'Failed for: {duration}')
        
        # Invalid durations
        invalid_durations = [
            '5 minutes',
            'PT',
            'P1D',  # Days not supported in this simplified pattern
            'not a duration',
            None,
            123
        ]
        
        for duration in invalid_durations:
            self.assertFalse(SchemaValidator._is_valid_iso_duration(duration), f'Should fail for: {duration}')

    def test_is_valid_url(self):
        """Test URL validation helper method."""
        # Valid URLs
        valid_urls = [
            'https://example.com',
            'http://example.com',
            'https://example.com/path',
            'https://subdomain.example.com',
            'https://example.com:8080/path?query=value'
        ]
        
        for url in valid_urls:
            self.assertTrue(SchemaValidator._is_valid_url(url), f'Failed for: {url}')
        
        # Invalid URLs
        invalid_urls = [
            'not a url',
            'example.com',  # Missing scheme
            'ftp://example.com',  # Different scheme (still valid URL but might not be expected)
            '',
            None,
            123
        ]
        
        for url in invalid_urls:
            if url == 'ftp://example.com':
                continue  # This is actually a valid URL
            self.assertFalse(SchemaValidator._is_valid_url(url), f'Should fail for: {url}')

    def test_validate_data_formats(self):
        """Test data format validation."""
        schema_with_dates = {
            '@context': 'https://schema.org',
            '@type': 'Article',
            'headline': 'Test',
            'datePublished': '2024-01-01T00:00:00Z',
            'dateModified': 'invalid-date',
            'timeRequired': 'PT5M',
            'author': {'@type': 'Person', 'name': 'Test'},
            'publisher': {'@type': 'Organization', 'name': 'Test'}
        }
        
        result = SchemaValidator.validate_schema_org_compliance(schema_with_dates)
        
        # Should have warning about invalid date
        self.assertTrue(any('Invalid or non-ISO date format' in warning for warning in result['warnings']))

    def test_validate_urls_in_schema(self):
        """Test URL validation in schema data."""
        schema_with_urls = {
            '@context': 'https://schema.org',
            '@type': 'Article',
            'headline': 'Test',
            'url': 'invalid-url',
            'image': ['https://example.com/image.jpg', 'invalid-image-url'],
            'author': {'@type': 'Person', 'name': 'Test'},
            'publisher': {'@type': 'Organization', 'name': 'Test'},
            'datePublished': '2024-01-01T00:00:00Z'
        }
        
        result = SchemaValidator.validate_schema_org_compliance(schema_with_urls)
        
        # Should have warnings about invalid URLs
        url_warnings = [w for w in result['warnings'] if 'Invalid URL format' in w]
        self.assertTrue(len(url_warnings) > 0)

    @patch('requests.post')
    def test_google_rich_results_api_success(self, mock_post):
        """Test Google Rich Results API testing with successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'richResultsItems': []}
        mock_post.return_value = mock_response
        
        result = SchemaValidator.test_google_rich_results_api('https://example.com', 'test-api-key')
        
        self.assertTrue(result['is_available'])
        self.assertIsNotNone(result['test_results'])
        self.assertEqual(len(result['errors']), 0)

    @patch('requests.post')
    def test_google_rich_results_api_failure(self, mock_post):
        """Test Google Rich Results API testing with failed response."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_post.return_value = mock_response
        
        result = SchemaValidator.test_google_rich_results_api('https://example.com', 'test-api-key')
        
        self.assertFalse(result['is_available'])
        self.assertIsNone(result['test_results'])
        self.assertTrue(len(result['errors']) > 0)

    def test_google_rich_results_api_no_key(self):
        """Test Google Rich Results API testing without API key."""
        result = SchemaValidator.test_google_rich_results_api('https://example.com')
        
        self.assertFalse(result['is_available'])
        self.assertIn('No Google API key provided', result['warnings'][0])

    def test_google_article_specific_validation(self):
        """Test Google-specific Article validation rules."""
        # Test long headline
        long_headline_schema = self.valid_article_schema.copy()
        long_headline_schema['headline'] = 'A' * 150  # Exceeds 110 character limit
        
        result = SchemaValidator.validate_google_rich_results(long_headline_schema)
        
        headline_warnings = [w for w in result['warnings'] if 'Headline exceeds recommended' in w]
        self.assertTrue(len(headline_warnings) > 0)
        
        # Test invalid author type
        invalid_author_schema = self.valid_article_schema.copy()
        invalid_author_schema['author'] = {'@type': 'Organization', 'name': 'Test Org'}
        
        result = SchemaValidator.validate_google_rich_results(invalid_author_schema)
        
        author_warnings = [w for w in result['warnings'] if 'author should be of type Person' in w]
        self.assertTrue(len(author_warnings) > 0)


class SchemaTestRunnerTestCase(TestCase):
    """Test cases for SchemaTestRunner utility."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        
        # Create test user and post
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            content='Test content',
            status='published'
        )
        
        self.request = self.factory.get('/test/')
        self.request.META['HTTP_HOST'] = 'testserver'
        
        # Create test schemas
        self.valid_schema = SchemaService.generate_article_schema(self.post, self.request)
        self.invalid_schema = {
            '@type': 'Article',
            'headline': 'Test'
            # Missing required fields
        }
        
        self.test_runner = SchemaTestRunner()

    def test_run_validation_tests_all_valid(self):
        """Test running validation tests with all valid schemas."""
        schemas = [self.valid_schema, self.valid_schema]
        test_names = ['Test 1', 'Test 2']
        
        results = self.test_runner.run_validation_tests(schemas, test_names)
        
        self.assertEqual(results['total_tests'], 2)
        self.assertEqual(results['passed'], 2)
        self.assertEqual(results['failed'], 0)
        self.assertEqual(results['summary']['status'], 'PASS')
        self.assertEqual(results['summary']['pass_rate'], 100.0)

    def test_run_validation_tests_mixed_results(self):
        """Test running validation tests with mixed valid/invalid schemas."""
        schemas = [self.valid_schema, self.invalid_schema]
        test_names = ['Valid Test', 'Invalid Test']
        
        results = self.test_runner.run_validation_tests(schemas, test_names)
        
        self.assertEqual(results['total_tests'], 2)
        self.assertEqual(results['passed'], 1)
        self.assertEqual(results['failed'], 1)
        self.assertEqual(results['summary']['status'], 'FAIL')
        self.assertEqual(results['summary']['pass_rate'], 50.0)

    def test_run_validation_tests_without_names(self):
        """Test running validation tests without providing test names."""
        schemas = [self.valid_schema]
        
        results = self.test_runner.run_validation_tests(schemas)
        
        self.assertEqual(results['test_results'][0]['test_name'], 'Schema_1')

    def test_export_results_json(self):
        """Test exporting results in JSON format."""
        schemas = [self.valid_schema]
        results = self.test_runner.run_validation_tests(schemas)
        
        json_output = self.test_runner.export_results(results, 'json')
        
        # Should be valid JSON
        parsed = json.loads(json_output)
        self.assertIsInstance(parsed, dict)
        self.assertIn('total_tests', parsed)

    def test_export_results_junit(self):
        """Test exporting results in JUnit XML format."""
        schemas = [self.valid_schema, self.invalid_schema]
        results = self.test_runner.run_validation_tests(schemas)
        
        junit_output = self.test_runner.export_results(results, 'junit')
        
        # Should contain XML structure
        self.assertIn('<?xml version="1.0"', junit_output)
        self.assertIn('<testsuite', junit_output)
        self.assertIn('<testcase', junit_output)
        self.assertIn('</testsuite>', junit_output)

    def test_export_results_text(self):
        """Test exporting results in text format."""
        schemas = [self.valid_schema]
        results = self.test_runner.run_validation_tests(schemas)
        
        text_output = self.test_runner.export_results(results, 'text')
        
        # Should contain expected text elements
        self.assertIn('Schema Validation Test Report', text_output)
        self.assertIn('Total Tests:', text_output)
        self.assertIn('Pass Rate:', text_output)

    def test_export_results_unsupported_format(self):
        """Test exporting results with unsupported format."""
        schemas = [self.valid_schema]
        results = self.test_runner.run_validation_tests(schemas)
        
        with self.assertRaises(ValueError):
            self.test_runner.export_results(results, 'unsupported')

    def test_junit_xml_with_failures(self):
        """Test JUnit XML export with test failures."""
        schemas = [self.invalid_schema]
        results = self.test_runner.run_validation_tests(schemas)
        
        junit_output = self.test_runner.export_results(results, 'junit')
        
        # Should contain failure information
        self.assertIn('<failure', junit_output)
        self.assertIn('Schema validation failed', junit_output)

    def test_text_report_formatting(self):
        """Test text report formatting with multiple tests."""
        schemas = [self.valid_schema, self.invalid_schema]
        test_names = ['Valid Schema', 'Invalid Schema']
        results = self.test_runner.run_validation_tests(schemas, test_names)
        
        text_output = self.test_runner.export_results(results, 'text')
        
        # Should contain individual test results
        self.assertIn('Valid Schema: VALID', text_output)
        self.assertIn('Invalid Schema:', text_output)  # Status might be different

    def test_warning_counting(self):
        """Test that warnings are properly counted across tests."""
        # Create schema with warnings but no errors
        warning_schema = {
            '@context': 'https://schema.org',
            '@type': 'Article',
            'headline': 'A' * 150,  # Too long, will generate warning
            'author': {'@type': 'Person', 'name': 'Test'},
            'publisher': {'@type': 'Organization', 'name': 'Test'},
            'datePublished': '2024-01-01T00:00:00Z',
            'dateModified': '2024-01-01T00:00:00Z',
            'image': ['https://example.com/image.jpg']
        }
        
        schemas = [warning_schema]
        results = self.test_runner.run_validation_tests(schemas)
        
        # Should count warnings
        self.assertGreater(results['warnings'], 0)

    def test_empty_schema_list(self):
        """Test running validation tests with empty schema list."""
        results = self.test_runner.run_validation_tests([])
        
        self.assertEqual(results['total_tests'], 0)
        self.assertEqual(results['passed'], 0)
        self.assertEqual(results['failed'], 0)
        self.assertEqual(results['summary']['pass_rate'], 0)

    def test_test_runner_configuration(self):
        """Test test runner with custom configuration."""
        config = {'strict_mode': True, 'timeout': 30}
        runner = SchemaTestRunner(config)
        
        self.assertEqual(runner.config, config)

    def test_results_summary_calculation(self):
        """Test that results summary is calculated correctly."""
        schemas = [self.valid_schema, self.valid_schema, self.invalid_schema]
        results = self.test_runner.run_validation_tests(schemas)
        
        # 2 passed, 1 failed = 66.67% pass rate
        expected_pass_rate = (2 / 3) * 100
        self.assertAlmostEqual(results['summary']['pass_rate'], expected_pass_rate, places=1)
        self.assertEqual(results['summary']['status'], 'FAIL')  # Any failures = FAIL