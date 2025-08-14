"""
Django management command for automated schema validation testing.

This command can be used in CI/CD pipelines to validate schema markup
for all published blog posts and generate reports in various formats.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.test import RequestFactory

from blog.models import Post
from blog.services.schema_service import SchemaService
from blog.utils.schema_validation import SchemaValidator, SchemaTestRunner


class Command(BaseCommand):
    """Management command for schema validation testing."""
    
    help = 'Validate schema markup for blog posts and generate reports'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--post-ids',
            nargs='+',
            type=int,
            help='Specific post IDs to validate (default: all published posts)'
        )
        
        parser.add_argument(
            '--output-format',
            choices=['json', 'junit', 'text'],
            default='text',
            help='Output format for validation results (default: text)'
        )
        
        parser.add_argument(
            '--output-file',
            type=str,
            help='File to write validation results (default: stdout)'
        )
        
        parser.add_argument(
            '--fail-on-warnings',
            action='store_true',
            help='Treat warnings as failures (exit code 1)'
        )
        
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Enable strict validation mode'
        )
        
        parser.add_argument(
            '--google-api-key',
            type=str,
            help='Google API key for Rich Results testing'
        )
        
        parser.add_argument(
            '--include-drafts',
            action='store_true',
            help='Include draft posts in validation'
        )
        
        parser.add_argument(
            '--max-posts',
            type=int,
            help='Maximum number of posts to validate (for testing)'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )

    def handle(self, *args, **options):
        """Handle the command execution."""
        try:
            # Set up request factory for URL generation
            factory = RequestFactory()
            request = factory.get('/')
            request.META['HTTP_HOST'] = 'testserver'
            
            # Get posts to validate
            posts = self.get_posts_to_validate(options)
            
            if not posts:
                self.stdout.write(
                    self.style.WARNING('No posts found to validate')
                )
                return
            
            self.stdout.write(
                f'Validating schema markup for {len(posts)} posts...'
            )
            
            # Generate schemas for validation
            schemas, test_names = self.generate_schemas_for_posts(posts, request, options)
            
            # Run validation tests
            test_runner = SchemaTestRunner()
            results = test_runner.run_validation_tests(schemas, test_names)
            
            # Add additional validation if Google API key provided
            if options['google_api_key']:
                self.run_google_api_tests(posts, results, options)
            
            # Generate and output results
            self.output_results(results, test_runner, options)
            
            # Determine exit code
            exit_code = self.determine_exit_code(results, options)
            
            if exit_code != 0:
                sys.exit(exit_code)
                
        except Exception as e:
            raise CommandError(f'Schema validation failed: {str(e)}')

    def get_posts_to_validate(self, options: Dict[str, Any]) -> List[Post]:
        """Get list of posts to validate based on options."""
        if options['post_ids']:
            # Validate specific posts
            posts = Post.objects.filter(id__in=options['post_ids'])
            missing_ids = set(options['post_ids']) - set(posts.values_list('id', flat=True))
            if missing_ids:
                self.stdout.write(
                    self.style.WARNING(f'Posts not found: {missing_ids}')
                )
        else:
            # Validate all posts based on status
            if options['include_drafts']:
                posts = Post.objects.all()
            else:
                posts = Post.objects.filter(status='published')
        
        # Apply max posts limit if specified
        if options['max_posts']:
            posts = posts[:options['max_posts']]
        
        return list(posts.select_related('author').prefetch_related('categories', 'tags'))

    def generate_schemas_for_posts(self, posts: List[Post], request, options: Dict[str, Any]) -> tuple:
        """Generate schema markup for posts."""
        schemas = []
        test_names = []
        
        for post in posts:
            try:
                # Generate article schema
                schema = SchemaService.generate_article_schema(post, request)
                schemas.append(schema)
                test_names.append(f'Post_{post.id}_{post.slug}')
                
                if options['verbose']:
                    self.stdout.write(f'Generated schema for: {post.title}')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to generate schema for post {post.id}: {str(e)}')
                )
                # Add empty schema to maintain test count
                schemas.append({})
                test_names.append(f'Post_{post.id}_ERROR')
        
        return schemas, test_names

    def run_google_api_tests(self, posts: List[Post], results: Dict[str, Any], options: Dict[str, Any]):
        """Run additional Google Rich Results API tests if API key provided."""
        self.stdout.write('Running Google Rich Results API tests...')
        
        api_results = []
        
        for post in posts[:5]:  # Limit API calls to avoid quota issues
            try:
                post_url = f"https://testserver{post.get_absolute_url()}"
                api_result = SchemaValidator.test_google_rich_results_api(
                    post_url, 
                    options['google_api_key']
                )
                api_results.append({
                    'post_id': post.id,
                    'post_title': post.title,
                    'api_result': api_result
                })
                
                if options['verbose']:
                    if api_result['is_available']:
                        self.stdout.write(f'API test completed for: {post.title}')
                    else:
                        self.stdout.write(f'API test failed for: {post.title}')
                        
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'API test error for post {post.id}: {str(e)}')
                )
        
        # Add API results to main results
        results['google_api_tests'] = api_results

    def output_results(self, results: Dict[str, Any], test_runner: SchemaTestRunner, options: Dict[str, Any]):
        """Output validation results in specified format."""
        # Generate output
        output_content = test_runner.export_results(results, options['output_format'])
        
        # Write to file or stdout
        if options['output_file']:
            output_path = Path(options['output_file'])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)
            
            self.stdout.write(
                self.style.SUCCESS(f'Results written to: {output_path}')
            )
        else:
            self.stdout.write(output_content)
        
        # Always show summary to stdout
        if options['output_file']:
            self.show_summary(results)

    def show_summary(self, results: Dict[str, Any]):
        """Show summary of validation results."""
        summary = results['summary']
        
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('VALIDATION SUMMARY')
        self.stdout.write('=' * 50)
        
        self.stdout.write(f"Total Tests: {results['total_tests']}")
        self.stdout.write(f"Passed: {results['passed']}")
        self.stdout.write(f"Failed: {results['failed']}")
        self.stdout.write(f"Warnings: {results['warnings']}")
        self.stdout.write(f"Pass Rate: {summary['pass_rate']:.1f}%")
        
        if summary['status'] == 'PASS':
            self.stdout.write(
                self.style.SUCCESS(f"Overall Status: {summary['status']}")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"Overall Status: {summary['status']}")
            )
        
        # Show failed tests
        failed_tests = [
            test for test in results['test_results'] 
            if test['status'] != 'valid'
        ]
        
        if failed_tests:
            self.stdout.write('\nFailed Tests:')
            for test in failed_tests:
                self.stdout.write(f"  - {test['test_name']}: {test['status']}")

    def determine_exit_code(self, results: Dict[str, Any], options: Dict[str, Any]) -> int:
        """Determine appropriate exit code based on results and options."""
        # Exit with error if any tests failed
        if results['failed'] > 0:
            return 1
        
        # Exit with error if warnings should be treated as failures
        if options['fail_on_warnings'] and results['warnings'] > 0:
            return 1
        
        # Success
        return 0

    def validate_single_post(self, post_id: int, options: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single post and return detailed results."""
        try:
            post = Post.objects.select_related('author').prefetch_related(
                'categories', 'tags'
            ).get(id=post_id)
        except Post.DoesNotExist:
            raise CommandError(f'Post with ID {post_id} not found')
        
        # Set up request
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_HOST'] = 'testserver'
        
        # Generate schema
        schema = SchemaService.generate_article_schema(post, request)
        
        # Run comprehensive validation
        report = SchemaValidator.generate_validation_report(schema)
        
        return {
            'post': {
                'id': post.id,
                'title': post.title,
                'slug': post.slug,
                'status': post.status
            },
            'schema': schema,
            'validation_report': report
        }

    def handle_single_post_validation(self, post_id: int, options: Dict[str, Any]):
        """Handle validation of a single post with detailed output."""
        result = self.validate_single_post(post_id, options)
        
        post_info = result['post']
        report = result['validation_report']
        
        self.stdout.write(f"\nValidating Post: {post_info['title']} (ID: {post_info['id']})")
        self.stdout.write(f"Slug: {post_info['slug']}")
        self.stdout.write(f"Status: {post_info['status']}")
        self.stdout.write('-' * 50)
        
        # Schema.org validation
        schema_org = report['schema_org_validation']
        self.stdout.write(f"Schema.org Compliance: {'✓' if schema_org['is_valid'] else '✗'}")
        if schema_org['errors']:
            self.stdout.write("  Errors:")
            for error in schema_org['errors']:
                self.stdout.write(f"    - {error}")
        if schema_org['warnings']:
            self.stdout.write("  Warnings:")
            for warning in schema_org['warnings']:
                self.stdout.write(f"    - {warning}")
        
        # Google Rich Results validation
        google = report['google_rich_results_validation']
        self.stdout.write(f"Google Rich Results: {'✓' if google['rich_results_eligible'] else '✗'}")
        if google['missing_required']:
            self.stdout.write("  Missing Required:")
            for field in google['missing_required']:
                self.stdout.write(f"    - {field}")
        if google['missing_recommended']:
            self.stdout.write("  Missing Recommended:")
            for field in google['missing_recommended']:
                self.stdout.write(f"    - {field}")
        
        # JSON-LD validation
        json_ld = report['json_ld_validation']
        self.stdout.write(f"JSON-LD Format: {'✓' if json_ld['is_valid'] else '✗'}")
        
        # Overall status
        status_color = self.style.SUCCESS if report['overall_status'] == 'valid' else self.style.ERROR
        self.stdout.write(status_color(f"Overall Status: {report['overall_status'].upper()}"))
        
        # Recommendations
        if report['recommendations']:
            self.stdout.write("\nRecommendations:")
            for rec in report['recommendations']:
                self.stdout.write(f"  - {rec}")
        
        # Output schema if requested
        if options['verbose']:
            self.stdout.write("\nGenerated Schema:")
            self.stdout.write(json.dumps(result['schema'], indent=2))