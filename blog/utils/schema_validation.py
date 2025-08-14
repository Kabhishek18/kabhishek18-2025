"""
Schema validation utilities for Schema.org compliance and Google Rich Results testing.

This module provides comprehensive validation tools for structured data markup,
including Schema.org compliance checking, Google Rich Results validation,
and JSON-LD format validation.
"""

import json
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Comprehensive schema validation utility for Schema.org and Google Rich Results."""
    
    # Schema.org required properties by type
    REQUIRED_PROPERTIES = {
        'Article': ['headline', 'author', 'datePublished'],
        'Person': ['name'],
        'Organization': ['name'],
        'BreadcrumbList': ['itemListElement'],
        'WebPage': ['@id'],
        'ImageObject': ['url']
    }
    
    # Google Rich Results requirements
    GOOGLE_RICH_RESULTS_REQUIREMENTS = {
        'Article': {
            'required': ['headline', 'image', 'datePublished', 'dateModified'],
            'recommended': ['author', 'publisher', 'description', 'url']
        }
    }
    
    # Valid Schema.org contexts
    VALID_CONTEXTS = [
        'https://schema.org',
        'http://schema.org',
        'https://schema.org/',
        'http://schema.org/'
    ]

    @staticmethod
    def validate_schema_org_compliance(schema_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate schema data for Schema.org compliance.
        
        Args:
            schema_data: Schema markup dictionary
            
        Returns:
            Dict containing validation results with errors and warnings
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'schema_type': None,
            'missing_required': [],
            'missing_recommended': []
        }
        
        try:
            # Basic structure validation
            if not isinstance(schema_data, dict):
                result['errors'].append('Schema data must be a dictionary')
                result['is_valid'] = False
                return result
            
            # Check for @context
            context = schema_data.get('@context')
            if not context:
                result['errors'].append('Missing @context property')
                result['is_valid'] = False
            elif context not in SchemaValidator.VALID_CONTEXTS:
                result['warnings'].append(f'Non-standard @context: {context}')
            
            # Check for @type
            schema_type = schema_data.get('@type')
            if not schema_type:
                result['errors'].append('Missing @type property')
                result['is_valid'] = False
                return result
            
            result['schema_type'] = schema_type
            
            # Validate required properties for schema type
            required_props = SchemaValidator.REQUIRED_PROPERTIES.get(schema_type, [])
            for prop in required_props:
                if not schema_data.get(prop):
                    result['missing_required'].append(prop)
                    result['errors'].append(f'Missing required property: {prop}')
                    result['is_valid'] = False
            
            # Validate nested schemas
            SchemaValidator._validate_nested_schemas(schema_data, result)
            
            # Validate data types and formats
            SchemaValidator._validate_data_formats(schema_data, result)
            
            # Validate URLs
            SchemaValidator._validate_urls(schema_data, result)
            
        except Exception as e:
            result['errors'].append(f'Validation error: {str(e)}')
            result['is_valid'] = False
            logger.error(f'Schema validation error: {str(e)}')
        
        return result

    @staticmethod
    def validate_google_rich_results(schema_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate schema data for Google Rich Results compliance.
        
        Args:
            schema_data: Schema markup dictionary
            
        Returns:
            Dict containing Google Rich Results validation results
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'missing_required': [],
            'missing_recommended': [],
            'rich_results_eligible': False
        }
        
        try:
            schema_type = schema_data.get('@type')
            if not schema_type:
                result['errors'].append('Missing @type property')
                result['is_valid'] = False
                return result
            
            # Check Google Rich Results requirements
            google_reqs = SchemaValidator.GOOGLE_RICH_RESULTS_REQUIREMENTS.get(schema_type)
            if not google_reqs:
                result['warnings'].append(f'No Google Rich Results requirements defined for {schema_type}')
                return result
            
            # Check required fields for Google Rich Results
            for field in google_reqs['required']:
                if not schema_data.get(field):
                    result['missing_required'].append(field)
                    result['errors'].append(f'Missing required field for Google Rich Results: {field}')
                    result['is_valid'] = False
            
            # Check recommended fields
            for field in google_reqs['recommended']:
                if not schema_data.get(field):
                    result['missing_recommended'].append(field)
                    result['warnings'].append(f'Missing recommended field for Google Rich Results: {field}')
            
            # Additional Google-specific validations
            if schema_type == 'Article':
                SchemaValidator._validate_google_article_requirements(schema_data, result)
            
            # Set rich results eligibility
            result['rich_results_eligible'] = result['is_valid'] and len(result['missing_required']) == 0
            
        except Exception as e:
            result['errors'].append(f'Google Rich Results validation error: {str(e)}')
            result['is_valid'] = False
            logger.error(f'Google Rich Results validation error: {str(e)}')
        
        return result

    @staticmethod
    def validate_json_ld_format(json_ld_string: str) -> Dict[str, Any]:
        """
        Validate JSON-LD format and structure.
        
        Args:
            json_ld_string: JSON-LD markup as string
            
        Returns:
            Dict containing JSON-LD validation results
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'parsed_data': None
        }
        
        try:
            # Parse JSON
            try:
                parsed_data = json.loads(json_ld_string)
                result['parsed_data'] = parsed_data
            except json.JSONDecodeError as e:
                result['errors'].append(f'Invalid JSON format: {str(e)}')
                result['is_valid'] = False
                return result
            
            # Validate JSON-LD structure
            if isinstance(parsed_data, dict):
                # Single schema object
                SchemaValidator._validate_json_ld_object(parsed_data, result)
            elif isinstance(parsed_data, list):
                # Array of schema objects
                for i, obj in enumerate(parsed_data):
                    if not isinstance(obj, dict):
                        result['errors'].append(f'Array item {i} is not a valid JSON-LD object')
                        result['is_valid'] = False
                    else:
                        SchemaValidator._validate_json_ld_object(obj, result, f'Item {i}: ')
            else:
                result['errors'].append('JSON-LD must be an object or array of objects')
                result['is_valid'] = False
            
        except Exception as e:
            result['errors'].append(f'JSON-LD validation error: {str(e)}')
            result['is_valid'] = False
            logger.error(f'JSON-LD validation error: {str(e)}')
        
        return result

    @staticmethod
    def test_google_rich_results_api(url: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Test URL with Google Rich Results Test API (if available).
        
        Args:
            url: URL to test
            api_key: Google API key (optional)
            
        Returns:
            Dict containing API test results
        """
        result = {
            'is_available': False,
            'test_results': None,
            'errors': [],
            'warnings': []
        }
        
        try:
            if not api_key:
                result['warnings'].append('No Google API key provided - API testing not available')
                return result
            
            # Google Rich Results Test API endpoint
            api_url = 'https://searchconsole.googleapis.com/v1/urlTestingTools/richResults:run'
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'url': url,
                'inspectionUrl': url
            }
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result['is_available'] = True
                result['test_results'] = response.json()
            else:
                result['errors'].append(f'API request failed: {response.status_code} - {response.text}')
            
        except requests.RequestException as e:
            result['errors'].append(f'API request error: {str(e)}')
        except Exception as e:
            result['errors'].append(f'Google Rich Results API test error: {str(e)}')
            logger.error(f'Google Rich Results API test error: {str(e)}')
        
        return result

    @staticmethod
    def generate_validation_report(schema_data: Dict[str, Any], url: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive validation report for schema data.
        
        Args:
            schema_data: Schema markup dictionary
            url: Optional URL for additional testing
            
        Returns:
            Dict containing comprehensive validation report
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'schema_org_validation': None,
            'google_rich_results_validation': None,
            'json_ld_validation': None,
            'overall_status': 'unknown',
            'recommendations': []
        }
        
        try:
            # Schema.org validation
            report['schema_org_validation'] = SchemaValidator.validate_schema_org_compliance(schema_data)
            
            # Google Rich Results validation
            report['google_rich_results_validation'] = SchemaValidator.validate_google_rich_results(schema_data)
            
            # JSON-LD validation
            json_ld_string = json.dumps(schema_data)
            report['json_ld_validation'] = SchemaValidator.validate_json_ld_format(json_ld_string)
            
            # Generate recommendations
            report['recommendations'] = SchemaValidator._generate_recommendations(
                report['schema_org_validation'],
                report['google_rich_results_validation'],
                report['json_ld_validation']
            )
            
            # Determine overall status
            all_valid = all([
                report['schema_org_validation']['is_valid'],
                report['google_rich_results_validation']['is_valid'],
                report['json_ld_validation']['is_valid']
            ])
            
            if all_valid:
                report['overall_status'] = 'valid'
            elif any([
                report['schema_org_validation']['is_valid'],
                report['google_rich_results_validation']['is_valid'],
                report['json_ld_validation']['is_valid']
            ]):
                report['overall_status'] = 'partial'
            else:
                report['overall_status'] = 'invalid'
            
        except Exception as e:
            report['overall_status'] = 'error'
            report['error'] = str(e)
            logger.error(f'Validation report generation error: {str(e)}')
        
        return report

    @staticmethod
    def _validate_nested_schemas(schema_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate nested schema objects."""
        for key, value in schema_data.items():
            if isinstance(value, dict) and '@type' in value:
                # This is a nested schema object
                nested_result = SchemaValidator.validate_schema_org_compliance(value)
                if not nested_result['is_valid']:
                    result['errors'].extend([f'{key}.{error}' for error in nested_result['errors']])
                    result['is_valid'] = False
                result['warnings'].extend([f'{key}.{warning}' for warning in nested_result['warnings']])
            elif isinstance(value, list):
                # Check for nested schemas in arrays
                for i, item in enumerate(value):
                    if isinstance(item, dict) and '@type' in item:
                        nested_result = SchemaValidator.validate_schema_org_compliance(item)
                        if not nested_result['is_valid']:
                            result['errors'].extend([f'{key}[{i}].{error}' for error in nested_result['errors']])
                            result['is_valid'] = False
                        result['warnings'].extend([f'{key}[{i}].{warning}' for warning in nested_result['warnings']])

    @staticmethod
    def _validate_data_formats(schema_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate data formats (dates, URLs, etc.)."""
        # Validate date formats
        date_fields = ['datePublished', 'dateModified', 'dateCreated']
        for field in date_fields:
            if field in schema_data:
                date_value = schema_data[field]
                if not SchemaValidator._is_valid_iso_date(date_value):
                    result['warnings'].append(f'Invalid or non-ISO date format in {field}: {date_value}')
        
        # Validate duration formats
        if 'timeRequired' in schema_data:
            duration = schema_data['timeRequired']
            if not SchemaValidator._is_valid_iso_duration(duration):
                result['warnings'].append(f'Invalid ISO 8601 duration format: {duration}')

    @staticmethod
    def _validate_urls(schema_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate URL formats."""
        url_fields = ['url', 'sameAs', 'image']
        
        for field in url_fields:
            if field in schema_data:
                value = schema_data[field]
                if isinstance(value, str):
                    if not SchemaValidator._is_valid_url(value):
                        result['warnings'].append(f'Invalid URL format in {field}: {value}')
                elif isinstance(value, list):
                    for i, url in enumerate(value):
                        if isinstance(url, str) and not SchemaValidator._is_valid_url(url):
                            result['warnings'].append(f'Invalid URL format in {field}[{i}]: {url}')

    @staticmethod
    def _validate_google_article_requirements(schema_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate Google-specific Article requirements."""
        # Image requirements
        if 'image' in schema_data:
            images = schema_data['image']
            if isinstance(images, list) and len(images) == 0:
                result['warnings'].append('Article has empty image array')
            elif isinstance(images, str):
                # Single image should be converted to array
                result['warnings'].append('Article image should be an array for better Google compatibility')
        
        # Headline length
        if 'headline' in schema_data:
            headline = schema_data['headline']
            if len(headline) > 110:
                result['warnings'].append(f'Headline exceeds recommended 110 characters: {len(headline)} chars')
        
        # Author validation
        if 'author' in schema_data:
            author = schema_data['author']
            if isinstance(author, dict):
                if author.get('@type') != 'Person':
                    result['warnings'].append('Article author should be of type Person')
                if not author.get('name'):
                    result['errors'].append('Article author must have a name')
                    result['is_valid'] = False

    @staticmethod
    def _validate_json_ld_object(obj: Dict[str, Any], result: Dict[str, Any], prefix: str = '') -> None:
        """Validate individual JSON-LD object."""
        # Check for @context in top-level objects
        if '@context' not in obj:
            result['warnings'].append(f'{prefix}Missing @context property')
        
        # Check for @type
        if '@type' not in obj:
            result['errors'].append(f'{prefix}Missing @type property')
            result['is_valid'] = False
        
        # Validate that all values are JSON-serializable
        try:
            json.dumps(obj)
        except (TypeError, ValueError) as e:
            result['errors'].append(f'{prefix}Object contains non-serializable data: {str(e)}')
            result['is_valid'] = False

    @staticmethod
    def _is_valid_iso_date(date_string: str) -> bool:
        """Check if string is a valid ISO 8601 date."""
        if not isinstance(date_string, str):
            return False
        
        # Common ISO 8601 patterns
        iso_patterns = [
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$',
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$',
            r'^\d{4}-\d{2}-\d{2}$'
        ]
        
        return any(re.match(pattern, date_string) for pattern in iso_patterns)

    @staticmethod
    def _is_valid_iso_duration(duration_string: str) -> bool:
        """Check if string is a valid ISO 8601 duration."""
        if not isinstance(duration_string, str):
            return False
        
        # ISO 8601 duration pattern (simplified)
        pattern = r'^PT(\d+H)?(\d+M)?(\d+S)?$'
        return bool(re.match(pattern, duration_string))

    @staticmethod
    def _is_valid_url(url_string: str) -> bool:
        """Check if string is a valid URL."""
        if not isinstance(url_string, str):
            return False
        
        try:
            result = urlparse(url_string)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @staticmethod
    def _generate_recommendations(schema_org_result: Dict, google_result: Dict, json_ld_result: Dict) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Schema.org recommendations
        if not schema_org_result['is_valid']:
            recommendations.append('Fix Schema.org compliance errors before deployment')
        
        if schema_org_result['warnings']:
            recommendations.append('Address Schema.org warnings to improve compliance')
        
        # Google Rich Results recommendations
        if google_result['missing_recommended']:
            recommendations.append('Add recommended fields for better Google Rich Results eligibility')
        
        if not google_result['rich_results_eligible']:
            recommendations.append('Schema is not eligible for Google Rich Results - fix required fields')
        
        # JSON-LD recommendations
        if not json_ld_result['is_valid']:
            recommendations.append('Fix JSON-LD format errors')
        
        # General recommendations
        if not recommendations:
            recommendations.append('Schema markup is valid and ready for production')
        
        return recommendations


class SchemaTestRunner:
    """Test runner for automated schema validation in CI/CD pipelines."""
    
    def __init__(self, test_config: Optional[Dict[str, Any]] = None):
        """
        Initialize test runner with configuration.
        
        Args:
            test_config: Configuration dictionary for test runner
        """
        self.config = test_config or {}
        self.results = []
    
    def run_validation_tests(self, schemas: List[Dict[str, Any]], test_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run validation tests on multiple schemas.
        
        Args:
            schemas: List of schema dictionaries to test
            test_names: Optional list of test names for identification
            
        Returns:
            Dict containing test results summary
        """
        results = {
            'total_tests': len(schemas),
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'test_results': [],
            'summary': {}
        }
        
        for i, schema in enumerate(schemas):
            test_name = test_names[i] if test_names and i < len(test_names) else f'Schema_{i+1}'
            
            # Run validation
            report = SchemaValidator.generate_validation_report(schema)
            
            test_result = {
                'test_name': test_name,
                'status': report['overall_status'],
                'report': report
            }
            
            results['test_results'].append(test_result)
            
            # Update counters
            if report['overall_status'] == 'valid':
                results['passed'] += 1
            else:
                results['failed'] += 1
            
            # Count warnings
            warning_count = sum([
                len(report['schema_org_validation']['warnings']),
                len(report['google_rich_results_validation']['warnings']),
                len(report['json_ld_validation']['warnings'])
            ])
            results['warnings'] += warning_count
        
        # Generate summary
        results['summary'] = {
            'pass_rate': (results['passed'] / results['total_tests']) * 100 if results['total_tests'] > 0 else 0,
            'total_warnings': results['warnings'],
            'status': 'PASS' if results['failed'] == 0 else 'FAIL'
        }
        
        return results
    
    def export_results(self, results: Dict[str, Any], format: str = 'json') -> str:
        """
        Export test results in specified format.
        
        Args:
            results: Test results dictionary
            format: Export format ('json', 'junit', 'text')
            
        Returns:
            Formatted results string
        """
        if format == 'json':
            return json.dumps(results, indent=2)
        elif format == 'junit':
            return self._export_junit_xml(results)
        elif format == 'text':
            return self._export_text_report(results)
        else:
            raise ValueError(f'Unsupported export format: {format}')
    
    def _export_junit_xml(self, results: Dict[str, Any]) -> str:
        """Export results in JUnit XML format."""
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<testsuite name="Schema Validation Tests" tests="{results["total_tests"]}" failures="{results["failed"]}" time="0">',
        ]
        
        for test_result in results['test_results']:
            test_name = test_result['test_name']
            status = test_result['status']
            
            if status == 'valid':
                xml_lines.append(f'  <testcase name="{test_name}" classname="SchemaValidation" time="0"/>')
            else:
                xml_lines.append(f'  <testcase name="{test_name}" classname="SchemaValidation" time="0">')
                xml_lines.append(f'    <failure message="Schema validation failed">')
                xml_lines.append(f'      Status: {status}')
                xml_lines.append(f'    </failure>')
                xml_lines.append(f'  </testcase>')
        
        xml_lines.append('</testsuite>')
        return '\n'.join(xml_lines)
    
    def _export_text_report(self, results: Dict[str, Any]) -> str:
        """Export results in text format."""
        lines = [
            'Schema Validation Test Report',
            '=' * 40,
            f'Total Tests: {results["total_tests"]}',
            f'Passed: {results["passed"]}',
            f'Failed: {results["failed"]}',
            f'Warnings: {results["warnings"]}',
            f'Pass Rate: {results["summary"]["pass_rate"]:.1f}%',
            f'Overall Status: {results["summary"]["status"]}',
            '',
            'Individual Test Results:',
            '-' * 25
        ]
        
        for test_result in results['test_results']:
            lines.append(f'{test_result["test_name"]}: {test_result["status"].upper()}')
        
        return '\n'.join(lines)