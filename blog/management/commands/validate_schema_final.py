"""
Django management command for final schema markup validation.

This command performs comprehensive validation of schema markup implementation
including Google Rich Results Test simulation and Schema.org compliance checking.

Usage:
    python manage.py validate_schema_final
    python manage.py validate_schema_final --post-id 1
    python manage.py validate_schema_final --all-posts
    python manage.py validate_schema_final --external-validation
"""

import json
import requests
import time
from datetime import datetime
from urllib.parse import urljoin

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.test import RequestFactory
from django.urls import reverse
from django.contrib.sites.models import Site

from blog.models import Post
from blog.services.schema_service import SchemaService


class Command(BaseCommand):
    help = 'Perform final validation of schema markup implementation'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--post-id',
            type=int,
            help='Validate schema for specific post ID'
        )
        
        parser.add_argument(
            '--all-posts',
            action='store_true',
            help='Validate schema for all published posts'
        )
        
        parser.add_argument(
            '--external-validation',
            action='store_true',
            help='Attempt external validation using Google Rich Results Test API'
        )
        
        parser.add_argument(
            '--output-format',
            choices=['text', 'json'],
            default='text',
            help='Output format for validation results'
        )
        
        parser.add_argument(
            '--save-results',
            help='Save validation results to file'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        self.stdout.write(
            self.style.SUCCESS('Starting final schema markup validation...')
        )
        
        validation_results = {
            'timestamp': datetime.now().isoformat(),
            'total_posts_tested': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'warnings': [],
            'errors': [],
            'post_results': []
        }
        
        try:
            # Determine which posts to validate
            posts_to_validate = self._get_posts_to_validate(options)
            validation_results['total_posts_tested'] = len(posts_to_validate)
            
            # Validate each post
            for post in posts_to_validate:
                post_result = self._validate_post_schema(post, options)
                validation_results['post_results'].append(post_result)
                
                if post_result['is_valid']:
                    validation_results['successful_validations'] += 1
                else:
                    validation_results['failed_validations'] += 1
                
                # Add warnings and errors to summary
                validation_results['warnings'].extend(post_result.get('warnings', []))
                validation_results['errors'].extend(post_result.get('errors', []))
            
            # Perform external validation if requested
            if options['external_validation']:
                self._perform_external_validation(validation_results, posts_to_validate)
            
            # Output results
            self._output_results(validation_results, options)
            
            # Save results if requested
            if options['save_results']:
                self._save_results(validation_results, options['save_results'])
            
            # Summary
            self._print_summary(validation_results)
            
        except Exception as e:
            raise CommandError(f'Validation failed: {str(e)}')
    
    def _get_posts_to_validate(self, options):
        """Get list of posts to validate based on options."""
        if options['post_id']:
            try:
                return [Post.objects.get(id=options['post_id'], status='published')]
            except Post.DoesNotExist:
                raise CommandError(f'Post with ID {options["post_id"]} not found')
        
        elif options['all_posts']:
            return Post.objects.filter(status='published').order_by('-created_at')
        
        else:
            # Default: validate recent posts
            return Post.objects.filter(status='published').order_by('-created_at')[:5]
    
    def _validate_post_schema(self, post, options):
        """Validate schema markup for a single post."""
        self.stdout.write(f'Validating schema for post: {post.title}')
        
        result = {
            'post_id': post.id,
            'post_title': post.title,
            'post_slug': post.slug,
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'schema_data': {},
            'validation_details': {}
        }
        
        try:
            # Create mock request for URL generation
            request = self._create_mock_request()
            
            # Generate schema data
            schema_data = SchemaService.generate_article_schema(post, request)
            result['schema_data'] = schema_data
            
            # Validate schema structure
            is_valid = SchemaService.validate_schema(schema_data)
            result['validation_details']['schema_service_validation'] = is_valid
            
            if not is_valid:
                result['is_valid'] = False
                result['errors'].append('Schema failed SchemaService validation')
            
            # Validate required fields for Google Rich Results
            self._validate_google_rich_results_requirements(schema_data, result)
            
            # Validate JSON-LD format
            self._validate_json_ld_format(schema_data, result)
            
            # Validate URL structure
            self._validate_url_structure(schema_data, result)
            
            # Validate date formats
            self._validate_date_formats(schema_data, result)
            
            # Validate nested schema objects
            self._validate_nested_schemas(schema_data, result)
            
            # Performance validation
            self._validate_performance(post, request, result)
            
        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f'Exception during validation: {str(e)}')
        
        return result
    
    def _validate_google_rich_results_requirements(self, schema_data, result):
        """Validate Google Rich Results requirements."""
        required_fields = ['headline', 'author', 'publisher', 'datePublished', 'url']
        
        for field in required_fields:
            if field not in schema_data:
                result['is_valid'] = False
                result['errors'].append(f'Missing required field for Google Rich Results: {field}')
        
        # Validate headline length
        headline = schema_data.get('headline', '')
        if len(headline) > 110:
            result['warnings'].append(f'Headline length ({len(headline)}) exceeds recommended 110 characters')
        
        # Validate author structure
        author = schema_data.get('author', {})
        if not isinstance(author, dict) or author.get('@type') != 'Person':
            result['errors'].append('Author must be a Person schema object')
        elif 'name' not in author:
            result['errors'].append('Author must have a name field')
        
        # Validate publisher structure
        publisher = schema_data.get('publisher', {})
        if not isinstance(publisher, dict) or publisher.get('@type') != 'Organization':
            result['errors'].append('Publisher must be an Organization schema object')
        elif 'name' not in publisher:
            result['errors'].append('Publisher must have a name field')
        
        # Validate logo if present
        if 'logo' in publisher:
            logo = publisher['logo']
            if not isinstance(logo, dict) or logo.get('@type') != 'ImageObject':
                result['warnings'].append('Publisher logo should be an ImageObject')
    
    def _validate_json_ld_format(self, schema_data, result):
        """Validate JSON-LD format compliance."""
        try:
            # Test JSON serialization
            json_string = json.dumps(schema_data, ensure_ascii=False, indent=2)
            
            # Test deserialization
            parsed_data = json.loads(json_string)
            
            if parsed_data != schema_data:
                result['errors'].append('Schema data changes during JSON serialization/deserialization')
            
            # Validate @context
            if schema_data.get('@context') != 'https://schema.org':
                result['errors'].append('Invalid or missing @context for Schema.org')
            
            # Validate @type
            if not schema_data.get('@type'):
                result['errors'].append('Missing @type field')
            
        except (TypeError, ValueError) as e:
            result['is_valid'] = False
            result['errors'].append(f'JSON-LD serialization error: {str(e)}')
    
    def _validate_url_structure(self, schema_data, result):
        """Validate URL structure and format."""
        url_fields = ['url']
        
        # Check main URL
        for field in url_fields:
            if field in schema_data:
                url = schema_data[field]
                if not isinstance(url, str) or not url.startswith('http'):
                    result['errors'].append(f'{field} must be an absolute URL starting with http/https')
        
        # Check author URL if present
        author = schema_data.get('author', {})
        if 'url' in author:
            if not author['url'].startswith('http'):
                result['errors'].append('Author URL must be absolute')
        
        # Check image URLs if present
        images = schema_data.get('image', [])
        if images:
            for i, image_url in enumerate(images):
                if not isinstance(image_url, str) or not image_url.startswith('http'):
                    result['errors'].append(f'Image URL {i} must be absolute')
    
    def _validate_date_formats(self, schema_data, result):
        """Validate date format compliance (ISO 8601)."""
        date_fields = ['datePublished', 'dateModified']
        
        for field in date_fields:
            if field in schema_data:
                date_value = schema_data[field]
                if not self._is_valid_iso_date(date_value):
                    result['errors'].append(f'{field} is not in valid ISO 8601 format: {date_value}')
    
    def _validate_nested_schemas(self, schema_data, result):
        """Validate nested schema objects."""
        # Validate author schema
        author = schema_data.get('author', {})
        if author:
            if not SchemaService.validate_schema(author, is_embedded=True):
                result['errors'].append('Author schema validation failed')
        
        # Validate publisher schema
        publisher = schema_data.get('publisher', {})
        if publisher:
            if not SchemaService.validate_schema(publisher, is_embedded=True):
                result['errors'].append('Publisher schema validation failed')
    
    def _validate_performance(self, post, request, result):
        """Validate schema generation performance."""
        start_time = time.time()
        
        # Generate schema multiple times to test performance
        for _ in range(3):
            SchemaService.generate_article_schema(post, request)
        
        end_time = time.time()
        avg_time = (end_time - start_time) / 3
        
        result['validation_details']['avg_generation_time'] = avg_time
        
        if avg_time > 0.1:  # 100ms threshold
            result['warnings'].append(f'Schema generation is slow: {avg_time:.3f}s average')
    
    def _perform_external_validation(self, validation_results, posts):
        """Attempt external validation using available tools."""
        self.stdout.write('Attempting external validation...')
        
        external_results = {
            'attempted': True,
            'google_rich_results': [],
            'schema_org_validator': []
        }
        
        # Note: This is a simulation since we can't actually call external APIs
        # In a real implementation, you would integrate with:
        # - Google Rich Results Test API
        # - Schema.org validator
        # - Other validation services
        
        for post in posts[:3]:  # Limit to first 3 posts for external validation
            try:
                # Simulate Google Rich Results Test
                google_result = self._simulate_google_rich_results_test(post)
                external_results['google_rich_results'].append(google_result)
                
                # Simulate Schema.org validation
                schema_org_result = self._simulate_schema_org_validation(post)
                external_results['schema_org_validator'].append(schema_org_result)
                
            except Exception as e:
                external_results['google_rich_results'].append({
                    'post_id': post.id,
                    'error': str(e)
                })
        
        validation_results['external_validation'] = external_results
    
    def _simulate_google_rich_results_test(self, post):
        """Simulate Google Rich Results Test validation."""
        # In a real implementation, this would call the actual API
        # For now, we simulate the validation based on our schema
        
        request = self._create_mock_request()
        schema_data = SchemaService.generate_article_schema(post, request)
        
        # Simulate Google's validation criteria
        issues = []
        warnings = []
        
        # Check required fields
        required_fields = ['headline', 'author', 'publisher', 'datePublished']
        for field in required_fields:
            if field not in schema_data:
                issues.append(f'Missing required field: {field}')
        
        # Check recommended fields
        recommended_fields = ['image', 'dateModified', 'description']
        for field in recommended_fields:
            if field not in schema_data:
                warnings.append(f'Missing recommended field: {field}')
        
        return {
            'post_id': post.id,
            'post_title': post.title,
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'rich_results_eligible': len(issues) == 0 and len(warnings) <= 1
        }
    
    def _simulate_schema_org_validation(self, post):
        """Simulate Schema.org validator results."""
        request = self._create_mock_request()
        schema_data = SchemaService.generate_article_schema(post, request)
        
        # Simulate Schema.org validation
        is_valid = SchemaService.validate_schema(schema_data)
        
        return {
            'post_id': post.id,
            'post_title': post.title,
            'valid': is_valid,
            'schema_type': schema_data.get('@type', 'Unknown'),
            'context': schema_data.get('@context', 'Missing')
        }
    
    def _output_results(self, validation_results, options):
        """Output validation results in requested format."""
        if options['output_format'] == 'json':
            self.stdout.write(json.dumps(validation_results, indent=2, default=str))
        else:
            self._output_text_results(validation_results)
    
    def _output_text_results(self, validation_results):
        """Output results in text format."""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('SCHEMA VALIDATION RESULTS')
        self.stdout.write('='*60)
        
        # Summary
        self.stdout.write(f'Total posts tested: {validation_results["total_posts_tested"]}')
        self.stdout.write(f'Successful validations: {validation_results["successful_validations"]}')
        self.stdout.write(f'Failed validations: {validation_results["failed_validations"]}')
        
        # Individual post results
        for post_result in validation_results['post_results']:
            self.stdout.write(f'\n--- Post: {post_result["post_title"]} ---')
            
            if post_result['is_valid']:
                self.stdout.write(self.style.SUCCESS('✓ VALID'))
            else:
                self.stdout.write(self.style.ERROR('✗ INVALID'))
            
            # Errors
            if post_result['errors']:
                self.stdout.write(self.style.ERROR('Errors:'))
                for error in post_result['errors']:
                    self.stdout.write(f'  - {error}')
            
            # Warnings
            if post_result['warnings']:
                self.stdout.write(self.style.WARNING('Warnings:'))
                for warning in post_result['warnings']:
                    self.stdout.write(f'  - {warning}')
            
            # Performance info
            if 'avg_generation_time' in post_result['validation_details']:
                avg_time = post_result['validation_details']['avg_generation_time']
                self.stdout.write(f'Average generation time: {avg_time:.3f}s')
        
        # External validation results
        if 'external_validation' in validation_results:
            self._output_external_validation_results(validation_results['external_validation'])
    
    def _output_external_validation_results(self, external_results):
        """Output external validation results."""
        self.stdout.write('\n' + '-'*40)
        self.stdout.write('EXTERNAL VALIDATION RESULTS')
        self.stdout.write('-'*40)
        
        # Google Rich Results
        if external_results['google_rich_results']:
            self.stdout.write('\nGoogle Rich Results Test (Simulated):')
            for result in external_results['google_rich_results']:
                if 'error' in result:
                    self.stdout.write(f'  Post {result["post_id"]}: ERROR - {result["error"]}')
                else:
                    status = '✓' if result['valid'] else '✗'
                    eligible = '✓' if result.get('rich_results_eligible', False) else '✗'
                    self.stdout.write(f'  {result["post_title"]}: {status} Valid, {eligible} Rich Results Eligible')
        
        # Schema.org validation
        if external_results['schema_org_validator']:
            self.stdout.write('\nSchema.org Validation (Simulated):')
            for result in external_results['schema_org_validator']:
                status = '✓' if result['valid'] else '✗'
                self.stdout.write(f'  {result["post_title"]}: {status} {result["schema_type"]}')
    
    def _save_results(self, validation_results, filename):
        """Save validation results to file."""
        try:
            with open(filename, 'w') as f:
                json.dump(validation_results, f, indent=2, default=str)
            self.stdout.write(f'Results saved to: {filename}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to save results: {str(e)}'))
    
    def _print_summary(self, validation_results):
        """Print validation summary."""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('VALIDATION SUMMARY')
        self.stdout.write('='*60)
        
        total = validation_results['total_posts_tested']
        successful = validation_results['successful_validations']
        failed = validation_results['failed_validations']
        
        if failed == 0:
            self.stdout.write(self.style.SUCCESS(f'All {total} posts passed validation! ✓'))
        else:
            self.stdout.write(self.style.WARNING(f'{successful}/{total} posts passed validation'))
            self.stdout.write(self.style.ERROR(f'{failed} posts failed validation'))
        
        # Common issues summary
        all_errors = validation_results['errors']
        if all_errors:
            error_counts = {}
            for error in all_errors:
                error_counts[error] = error_counts.get(error, 0) + 1
            
            self.stdout.write('\nMost common issues:')
            for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                self.stdout.write(f'  {count}x: {error}')
    
    def _create_mock_request(self):
        """Create a mock request for URL generation."""
        factory = RequestFactory()
        request = factory.get('/')
        
        # Set the host based on settings or default
        if hasattr(settings, 'SITE_DOMAIN'):
            request.META['HTTP_HOST'] = settings.SITE_DOMAIN
        else:
            request.META['HTTP_HOST'] = 'kabhishek18.com'
        
        return request
    
    def _is_valid_iso_date(self, date_string):
        """Validate ISO 8601 date format."""
        try:
            datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            return True
        except (ValueError, AttributeError):
            return False