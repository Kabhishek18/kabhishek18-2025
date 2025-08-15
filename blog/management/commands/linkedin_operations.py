"""
Django management command for LinkedIn manual operations.
Provides utilities for manual posting, API testing, bulk operations, and credential management.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from blog.models import Post
from blog.linkedin_models import LinkedInConfig, LinkedInPost
from blog.services.linkedin_service import LinkedInAPIService, LinkedInAPIError
from blog.services.linkedin_content_formatter import LinkedInContentFormatter
import json
import time
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'LinkedIn manual operations: posting, testing, bulk operations, and credential management'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='operation', help='Available operations')
        
        # Manual posting
        post_parser = subparsers.add_parser('post', help='Manually post a blog post to LinkedIn')
        post_parser.add_argument('post_id', type=int, help='Blog post ID to post')
        post_parser.add_argument('--force', action='store_true', help='Force posting even if already posted')
        post_parser.add_argument('--dry-run', action='store_true', help='Show what would be posted without actually posting')
        
        # API connectivity testing
        test_parser = subparsers.add_parser('test', help='Test LinkedIn API connectivity')
        test_parser.add_argument('--profile', action='store_true', help='Test profile access')
        test_parser.add_argument('--auth', action='store_true', help='Test authentication only')
        test_parser.add_argument('--verbose', action='store_true', help='Show detailed test results')
        
        # Bulk posting
        bulk_parser = subparsers.add_parser('bulk', help='Bulk post existing published posts')
        bulk_parser.add_argument('--limit', type=int, default=10, help='Maximum number of posts to process')
        bulk_parser.add_argument('--days', type=int, help='Only posts from last N days')
        bulk_parser.add_argument('--category', help='Only posts from specific category')
        bulk_parser.add_argument('--author', help='Only posts from specific author (username)')
        bulk_parser.add_argument('--dry-run', action='store_true', help='Show what would be posted without actually posting')
        bulk_parser.add_argument('--delay', type=int, default=30, help='Delay between posts in seconds')
        bulk_parser.add_argument('--force', action='store_true', help='Force posting even if already posted')
        
        # Credential validation and refresh
        cred_parser = subparsers.add_parser('credentials', help='Validate and refresh LinkedIn credentials')
        cred_parser.add_argument('action', choices=['validate', 'refresh', 'status'], help='Credential action')
        cred_parser.add_argument('--config-id', type=int, help='Specific configuration ID')
        
        # Status and monitoring
        status_parser = subparsers.add_parser('status', help='Show LinkedIn posting status and statistics')
        status_parser.add_argument('--recent', type=int, default=10, help='Number of recent posts to show')
        status_parser.add_argument('--failed', action='store_true', help='Show only failed posts')
        status_parser.add_argument('--pending', action='store_true', help='Show only pending posts')
        status_parser.add_argument('--stats', action='store_true', help='Show posting statistics')

    def handle(self, *args, **options):
        operation = options.get('operation')
        
        if not operation:
            self.print_help()
            return
        
        try:
            if operation == 'post':
                self.handle_manual_post(options)
            elif operation == 'test':
                self.handle_api_test(options)
            elif operation == 'bulk':
                self.handle_bulk_post(options)
            elif operation == 'credentials':
                self.handle_credentials(options)
            elif operation == 'status':
                self.handle_status(options)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Operation failed: {str(e)}'))
            raise CommandError(str(e))

    def print_help(self):
        """Print help information about available operations"""
        self.stdout.write(self.style.SUCCESS('LinkedIn Operations Management Command'))
        self.stdout.write('')
        self.stdout.write('Available operations:')
        self.stdout.write('  post      - Manually post a blog post to LinkedIn')
        self.stdout.write('  test      - Test LinkedIn API connectivity')
        self.stdout.write('  bulk      - Bulk post existing published posts')
        self.stdout.write('  credentials - Validate and refresh LinkedIn credentials')
        self.stdout.write('  status    - Show LinkedIn posting status and statistics')
        self.stdout.write('')
        self.stdout.write('Use --help with any operation for detailed options.')

    def handle_manual_post(self, options):
        """Handle manual posting of a single blog post"""
        post_id = options['post_id']
        force = options.get('force', False)
        dry_run = options.get('dry_run', False)
        
        self.stdout.write(f'Manual LinkedIn posting for post ID: {post_id}')
        
        # Get the blog post
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            raise CommandError(f'Blog post with ID {post_id} not found')
        
        # Check if post is published
        if post.status != 'published':
            raise CommandError(f'Post "{post.title}" is not published (status: {post.status})')
        
        # Check if already posted
        existing_linkedin_post = LinkedInPost.objects.filter(post=post).first()
        if existing_linkedin_post and existing_linkedin_post.is_successful() and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'Post "{post.title}" was already posted to LinkedIn successfully '
                    f'(LinkedIn ID: {existing_linkedin_post.linkedin_post_id}). '
                    f'Use --force to post again.'
                )
            )
            return
        
        # Initialize LinkedIn service
        linkedin_service = LinkedInAPIService()
        if not linkedin_service.is_configured():
            raise CommandError('LinkedIn integration is not configured')
        
        # Format content with enhanced image integration
        formatter = LinkedInContentFormatter()
        try:
            formatted_data = formatter.format_for_preview(post, include_image_analysis=True)
            formatted_content = {
                'title': formatted_data['title'],
                'content': formatted_data['full_content'],
                'url': formatted_data['url'],
                'image_url': formatted_data.get('best_linkedin_image')  # Enhanced: use best LinkedIn-compatible image
            }
            
            # Show enhanced image information
            if formatted_content['image_url']:
                self.stdout.write(f'LinkedIn-compatible image found: {formatted_content["image_url"]}')
                if formatted_data.get('total_images_count', 0) > 1:
                    self.stdout.write(f'Total images available: {formatted_data["total_images_count"]}')
            else:
                self.stdout.write('No LinkedIn-compatible image found (will post as text-only)')
                if formatted_data.get('total_images_count', 0) > 0:
                    self.stdout.write(f'Note: {formatted_data["total_images_count"]} images found but none are LinkedIn-compatible')
                    
        except Exception as e:
            raise CommandError(f'Failed to format content: {str(e)}')
        
        self.stdout.write(f'Post: "{post.title}"')
        self.stdout.write(f'Author: {post.author.get_full_name() or post.author.username}')
        self.stdout.write(f'Created: {post.created_at}')
        self.stdout.write('')
        self.stdout.write('Formatted LinkedIn content:')
        self.stdout.write('-' * 50)
        self.stdout.write(formatted_content['content'])
        self.stdout.write('-' * 50)
        self.stdout.write(f'URL: {formatted_content["url"]}')
        
        if formatted_content.get('image_url'):
            self.stdout.write(f'Image: {formatted_content["image_url"]}')
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS('DRY RUN: Content formatted successfully. No actual posting performed.'))
            return
        
        # Perform the posting
        self.stdout.write('')
        self.stdout.write('Posting to LinkedIn...')
        
        try:
            # Use the enhanced post_blog_article method for comprehensive image integration and error handling
            linkedin_post = linkedin_service.post_blog_article(post, attempt_count=1)
            
            self.stdout.write(self.style.SUCCESS(f'✓ Successfully posted to LinkedIn!'))
            self.stdout.write(f'LinkedIn Post ID: {linkedin_post.linkedin_post_id}')
            if linkedin_post.linkedin_post_url:
                self.stdout.write(f'LinkedIn Post URL: {linkedin_post.linkedin_post_url}')
            
            # Show image posting results
            if linkedin_post.has_images():
                if linkedin_post.is_image_upload_successful():
                    self.stdout.write(self.style.SUCCESS(f'✓ Image posted successfully'))
                    self.stdout.write(f'Media IDs: {", ".join(linkedin_post.media_ids)}')
                elif linkedin_post.is_image_upload_failed():
                    self.stdout.write(self.style.WARNING(f'⚠ Image upload failed: {linkedin_post.image_error_message}'))
                    self.stdout.write('Post was created as text-only')
            else:
                self.stdout.write('Posted as text-only (no images)')
            
        except LinkedInAPIError as e:
            self.stdout.write(self.style.ERROR(f'✗ Failed to post to LinkedIn: {str(e)}'))
            if hasattr(e, 'error_code') and e.error_code:
                self.stdout.write(f'Error Code: {e.error_code}')
            
            raise CommandError(f'LinkedIn posting failed: {str(e)}')

    def handle_api_test(self, options):
        """Handle LinkedIn API connectivity testing"""
        test_profile = options.get('profile', False)
        test_auth = options.get('auth', False)
        verbose = options.get('verbose', False)
        
        self.stdout.write(self.style.SUCCESS('Testing LinkedIn API connectivity...'))
        self.stdout.write('')
        
        # Initialize service
        linkedin_service = LinkedInAPIService()
        
        # Test configuration
        self.stdout.write('1. Configuration Test:')
        if linkedin_service.is_configured():
            self.stdout.write(self.style.SUCCESS('   ✓ LinkedIn integration is configured'))
            if verbose:
                config = linkedin_service.config
                self.stdout.write(f'   Client ID: {config.client_id}')
                self.stdout.write(f'   Active: {config.is_active}')
        else:
            self.stdout.write(self.style.ERROR('   ✗ LinkedIn integration is not configured'))
            return
        
        # Test authentication
        self.stdout.write('')
        self.stdout.write('2. Authentication Test:')
        try:
            auth_success = linkedin_service.authenticate()
            if auth_success:
                self.stdout.write(self.style.SUCCESS('   ✓ Authentication successful'))
                if verbose:
                    config = linkedin_service.config
                    self.stdout.write(f'   Token expires: {config.token_expires_at}')
                    if config.token_expires_at:
                        time_left = config.token_expires_at - timezone.now()
                        hours_left = time_left.total_seconds() / 3600
                        self.stdout.write(f'   Time remaining: {hours_left:.1f} hours')
            else:
                self.stdout.write(self.style.ERROR('   ✗ Authentication failed'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ Authentication error: {str(e)}'))
            return
        
        if test_auth:
            self.stdout.write(self.style.SUCCESS('Authentication test completed successfully.'))
            return
        
        # Test profile access
        if test_profile or not test_auth:
            self.stdout.write('')
            self.stdout.write('3. Profile Access Test:')
            try:
                profile_data = linkedin_service.get_user_profile()
                if profile_data:
                    self.stdout.write(self.style.SUCCESS('   ✓ Profile access successful'))
                    if verbose and profile_data:
                        # Display profile information safely
                        if 'localizedFirstName' in profile_data:
                            self.stdout.write(f'   Name: {profile_data.get("localizedFirstName", "")} {profile_data.get("localizedLastName", "")}')
                        if 'id' in profile_data:
                            self.stdout.write(f'   Profile ID: {profile_data["id"]}')
                else:
                    self.stdout.write(self.style.WARNING('   ⚠ Profile access returned no data'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ✗ Profile access error: {str(e)}'))
                return
        
        # Test quota status
        self.stdout.write('')
        self.stdout.write('4. Quota Status:')
        try:
            # Check current quota usage from the service
            daily_used = linkedin_service._daily_quota_used
            daily_limit = linkedin_service._daily_quota_limit
            
            self.stdout.write(f'   Daily quota: {daily_used}/{daily_limit} posts')
            
            if daily_used >= daily_limit:
                self.stdout.write(self.style.ERROR('   ✗ Daily quota exceeded'))
            elif daily_used >= daily_limit * 0.8:
                self.stdout.write(self.style.WARNING(f'   ⚠ Quota usage high: {daily_used}/{daily_limit}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'   ✓ Quota available: {daily_limit - daily_used} posts remaining'))
                
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'   ⚠ Could not check quota status: {str(e)}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('All API connectivity tests completed successfully!'))

    def handle_bulk_post(self, options):
        """Handle bulk posting of existing published posts"""
        limit = options.get('limit', 10)
        days = options.get('days')
        category = options.get('category')
        author = options.get('author')
        dry_run = options.get('dry_run', False)
        delay = options.get('delay', 30)
        force = options.get('force', False)
        
        self.stdout.write(self.style.SUCCESS('LinkedIn Bulk Posting Operation'))
        self.stdout.write('')
        
        # Build query for posts
        posts_query = Post.objects.filter(status='published').order_by('-created_at')
        
        # Apply filters
        if days:
            cutoff_date = timezone.now() - timedelta(days=days)
            posts_query = posts_query.filter(created_at__gte=cutoff_date)
            self.stdout.write(f'Filter: Posts from last {days} days')
        
        if category:
            posts_query = posts_query.filter(categories__name__icontains=category)
            self.stdout.write(f'Filter: Category contains "{category}"')
        
        if author:
            posts_query = posts_query.filter(author__username=author)
            self.stdout.write(f'Filter: Author "{author}"')
        
        # Get posts that haven't been successfully posted (unless force is used)
        if not force:
            # Exclude posts that have been successfully posted
            successfully_posted_ids = LinkedInPost.objects.filter(
                status='success'
            ).values_list('post_id', flat=True)
            posts_query = posts_query.exclude(id__in=successfully_posted_ids)
            self.stdout.write('Filter: Excluding already posted posts (use --force to override)')
        
        # Apply limit
        posts = posts_query[:limit]
        total_posts = posts.count()
        
        if total_posts == 0:
            self.stdout.write(self.style.WARNING('No posts found matching the criteria.'))
            return
        
        self.stdout.write(f'Found {total_posts} posts to process')
        self.stdout.write('')
        
        # Initialize LinkedIn service
        linkedin_service = LinkedInAPIService()
        if not linkedin_service.is_configured():
            raise CommandError('LinkedIn integration is not configured')
        
        # Test authentication before starting
        if not linkedin_service.authenticate():
            raise CommandError('LinkedIn authentication failed')
        
        formatter = LinkedInContentFormatter()
        
        # Process posts
        successful_posts = 0
        failed_posts = 0
        skipped_posts = 0
        
        for i, post in enumerate(posts, 1):
            self.stdout.write(f'Processing post {i}/{total_posts}: "{post.title}"')
            
            try:
                # Check if already posted successfully
                existing_linkedin_post = LinkedInPost.objects.filter(post=post).first()
                if existing_linkedin_post and existing_linkedin_post.is_successful() and not force:
                    self.stdout.write(self.style.WARNING(f'  Skipped: Already posted (LinkedIn ID: {existing_linkedin_post.linkedin_post_id})'))
                    skipped_posts += 1
                    continue
                
                # Format content with enhanced image integration
                formatted_data = formatter.format_for_preview(post, include_image_analysis=True)
                formatted_content = {
                    'title': formatted_data['title'],
                    'content': formatted_data['full_content'],
                    'url': formatted_data['url'],
                    'image_url': formatted_data.get('best_linkedin_image')  # Enhanced: use best LinkedIn-compatible image
                }
                
                # Log image status for bulk operations
                if formatted_content['image_url']:
                    self.stdout.write(f'  Image: LinkedIn-compatible image found')
                else:
                    self.stdout.write(f'  Image: Text-only (no compatible image)')
                
                if dry_run:
                    self.stdout.write('  DRY RUN: Would post the following content:')
                    self.stdout.write(f'    Title: {formatted_content["title"][:100]}...')
                    self.stdout.write(f'    URL: {formatted_content["url"]}')
                    successful_posts += 1
                    continue
                
                # Use the enhanced post_blog_article method for comprehensive image integration
                linkedin_post = linkedin_service.post_blog_article(post, attempt_count=1)
                
                # Show results with image information
                success_msg = f'  ✓ Posted successfully (LinkedIn ID: {linkedin_post.linkedin_post_id})'
                if linkedin_post.has_images() and linkedin_post.is_image_upload_successful():
                    success_msg += ' [with image]'
                elif linkedin_post.has_images() and linkedin_post.is_image_upload_failed():
                    success_msg += ' [text-only, image failed]'
                
                self.stdout.write(self.style.SUCCESS(success_msg))
                successful_posts += 1
                
                # Delay between posts (except for the last one)
                if i < total_posts and delay > 0:
                    self.stdout.write(f'  Waiting {delay} seconds before next post...')
                    time.sleep(delay)
                
            except LinkedInAPIError as e:
                # Mark as failed
                if 'linkedin_post' in locals():
                    linkedin_post.mark_as_failed(str(e), getattr(e, 'error_code', None), e.is_retryable)
                
                self.stdout.write(self.style.ERROR(f'  ✗ Failed: {str(e)}'))
                failed_posts += 1
                
                # Continue with next post instead of stopping
                continue
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Unexpected error: {str(e)}'))
                failed_posts += 1
                continue
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Bulk posting operation completed!'))
        self.stdout.write(f'Successful: {successful_posts}')
        self.stdout.write(f'Failed: {failed_posts}')
        self.stdout.write(f'Skipped: {skipped_posts}')
        self.stdout.write(f'Total processed: {successful_posts + failed_posts + skipped_posts}')

    def handle_credentials(self, options):
        """Handle credential validation and refresh operations"""
        action = options['action']
        config_id = options.get('config_id')
        
        # Get configuration
        if config_id:
            try:
                config = LinkedInConfig.objects.get(id=config_id)
            except LinkedInConfig.DoesNotExist:
                raise CommandError(f'Configuration with ID {config_id} not found')
        else:
            config = LinkedInConfig.get_active_config()
            if not config:
                raise CommandError('No active LinkedIn configuration found')
        
        self.stdout.write(f'LinkedIn Credentials Management - Configuration {config.id}')
        self.stdout.write('')
        
        if action == 'validate':
            self._validate_credentials(config)
        elif action == 'refresh':
            self._refresh_credentials(config)
        elif action == 'status':
            self._show_credential_status(config)

    def _validate_credentials(self, config):
        """Validate LinkedIn credentials"""
        self.stdout.write('Validating LinkedIn credentials...')
        self.stdout.write('')
        
        # Basic validation
        validation = config.validate_credentials()
        
        self.stdout.write('Credential Validation Results:')
        self.stdout.write(f'  Client Secret: {"✓ Valid" if validation["client_secret_valid"] else "✗ Invalid"}')
        self.stdout.write(f'  Access Token: {"✓ Valid" if validation["access_token_valid"] else "✗ Invalid"}')
        self.stdout.write(f'  Refresh Token: {"✓ Valid" if validation["refresh_token_valid"] else "⚠ Missing/Invalid"}')
        
        if validation['errors']:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('Validation Errors:'))
            for error in validation['errors']:
                self.stdout.write(f'  • {error}')
        
        # API validation
        self.stdout.write('')
        self.stdout.write('Testing API connectivity...')
        
        linkedin_service = LinkedInAPIService(config)
        try:
            auth_success = linkedin_service.authenticate()
            if auth_success:
                self.stdout.write(self.style.SUCCESS('  ✓ API authentication successful'))
                
                # Test profile access
                try:
                    profile_data = linkedin_service.get_user_profile()
                    if profile_data:
                        self.stdout.write(self.style.SUCCESS('  ✓ Profile access successful'))
                    else:
                        self.stdout.write(self.style.WARNING('  ⚠ Profile access returned no data'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Profile access failed: {str(e)}'))
            else:
                self.stdout.write(self.style.ERROR('  ✗ API authentication failed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ API test error: {str(e)}'))
        
        # Overall status
        self.stdout.write('')
        if config.has_valid_credentials():
            self.stdout.write(self.style.SUCCESS('Overall Status: Credentials are valid and ready for use'))
        else:
            self.stdout.write(self.style.ERROR('Overall Status: Credentials need attention'))

    def _refresh_credentials(self, config):
        """Refresh LinkedIn access token"""
        self.stdout.write('Refreshing LinkedIn access token...')
        
        linkedin_service = LinkedInAPIService(config)
        
        try:
            success = linkedin_service.refresh_access_token()
            if success:
                self.stdout.write(self.style.SUCCESS('✓ Access token refreshed successfully'))
                
                # Show new expiration
                if config.token_expires_at:
                    self.stdout.write(f'New expiration: {config.token_expires_at}')
                    time_left = config.token_expires_at - timezone.now()
                    hours_left = time_left.total_seconds() / 3600
                    self.stdout.write(f'Time remaining: {hours_left:.1f} hours')
            else:
                self.stdout.write(self.style.ERROR('✗ Token refresh failed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Token refresh error: {str(e)}'))

    def _show_credential_status(self, config):
        """Show detailed credential status"""
        status = config.get_credential_status()
        
        self.stdout.write('LinkedIn Credential Status:')
        self.stdout.write(f'  Configuration ID: {config.id}')
        self.stdout.write(f'  Active: {config.is_active}')
        self.stdout.write(f'  Client ID: {config.client_id}')
        self.stdout.write('')
        
        self.stdout.write('Credential Components:')
        self.stdout.write(f'  Has Client Secret: {"✓" if status["has_client_secret"] else "✗"}')
        self.stdout.write(f'  Has Access Token: {"✓" if status["has_access_token"] else "✗"}')
        self.stdout.write(f'  Has Refresh Token: {"✓" if status["has_refresh_token"] else "⚠"}')
        self.stdout.write('')
        
        self.stdout.write('Token Status:')
        self.stdout.write(f'  Token Expired: {"✗ Yes" if status["token_expired"] else "✓ No"}')
        self.stdout.write(f'  Needs Refresh: {"⚠ Yes" if status["needs_refresh"] else "✓ No"}')
        
        if status.get('expires_at'):
            self.stdout.write(f'  Expires At: {status["expires_at"]}')
            if status.get('expires_in_hours') is not None:
                hours = status['expires_in_hours']
                if hours > 0:
                    self.stdout.write(f'  Time Remaining: {hours:.1f} hours')
                else:
                    self.stdout.write(self.style.ERROR(f'  Expired: {abs(hours):.1f} hours ago'))
        
        self.stdout.write('')
        self.stdout.write('Overall Status:')
        if status['is_valid']:
            self.stdout.write(self.style.SUCCESS('  ✓ Ready for API operations'))
        else:
            self.stdout.write(self.style.ERROR('  ✗ Not ready - credentials need attention'))
        
        self.stdout.write('')
        self.stdout.write(f'Created: {config.created_at}')
        self.stdout.write(f'Updated: {config.updated_at}')

    def handle_status(self, options):
        """Handle status and monitoring operations"""
        recent = options.get('recent', 10)
        show_failed = options.get('failed', False)
        show_pending = options.get('pending', False)
        show_stats = options.get('stats', False)
        
        self.stdout.write(self.style.SUCCESS('LinkedIn Posting Status'))
        self.stdout.write('')
        
        if show_stats:
            self._show_posting_statistics()
            self.stdout.write('')
        
        # Build query based on filters
        posts_query = LinkedInPost.objects.select_related('post').order_by('-created_at')
        
        if show_failed:
            posts_query = posts_query.filter(status='failed')
            self.stdout.write('Showing failed posts only:')
        elif show_pending:
            posts_query = posts_query.filter(status__in=['pending', 'retrying'])
            self.stdout.write('Showing pending/retrying posts only:')
        else:
            self.stdout.write(f'Showing {recent} most recent posts:')
        
        posts = posts_query[:recent]
        
        if not posts:
            self.stdout.write(self.style.WARNING('No posts found.'))
            return
        
        # Display posts
        for linkedin_post in posts:
            status_icon = {
                'success': '✓',
                'failed': '✗',
                'pending': '⏳',
                'retrying': '🔄'
            }.get(linkedin_post.status, '?')
            
            status_color = {
                'success': self.style.SUCCESS,
                'failed': self.style.ERROR,
                'pending': self.style.WARNING,
                'retrying': self.style.WARNING
            }.get(linkedin_post.status, lambda x: x)
            
            self.stdout.write('')
            self.stdout.write(f'{status_icon} {linkedin_post.post.title}')
            self.stdout.write(status_color(f'   Status: {linkedin_post.get_status_display()}'))
            self.stdout.write(f'   Created: {linkedin_post.created_at}')
            
            if linkedin_post.is_successful():
                self.stdout.write(f'   Posted: {linkedin_post.posted_at}')
                self.stdout.write(f'   LinkedIn ID: {linkedin_post.linkedin_post_id}')
                if linkedin_post.linkedin_post_url:
                    self.stdout.write(f'   LinkedIn URL: {linkedin_post.linkedin_post_url}')
            
            if linkedin_post.error_message:
                self.stdout.write(self.style.ERROR(f'   Error: {linkedin_post.error_message}'))
                if linkedin_post.error_code:
                    self.stdout.write(f'   Error Code: {linkedin_post.error_code}')
            
            if linkedin_post.attempt_count > 0:
                self.stdout.write(f'   Attempts: {linkedin_post.attempt_count}/{linkedin_post.max_attempts}')
            
            if linkedin_post.next_retry_at:
                self.stdout.write(f'   Next Retry: {linkedin_post.get_retry_delay_display()}')

    def _show_posting_statistics(self):
        """Show posting statistics"""
        self.stdout.write('Posting Statistics:')
        
        # Overall counts
        total_posts = LinkedInPost.objects.count()
        successful_posts = LinkedInPost.objects.filter(status='success').count()
        failed_posts = LinkedInPost.objects.filter(status='failed').count()
        pending_posts = LinkedInPost.objects.filter(status__in=['pending', 'retrying']).count()
        
        self.stdout.write(f'  Total LinkedIn posts: {total_posts}')
        self.stdout.write(f'  Successful: {successful_posts}')
        self.stdout.write(f'  Failed: {failed_posts}')
        self.stdout.write(f'  Pending/Retrying: {pending_posts}')
        
        if total_posts > 0:
            success_rate = (successful_posts / total_posts) * 100
            self.stdout.write(f'  Success rate: {success_rate:.1f}%')
        
        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_posts = LinkedInPost.objects.filter(created_at__gte=week_ago).count()
        recent_successful = LinkedInPost.objects.filter(
            created_at__gte=week_ago, 
            status='success'
        ).count()
        
        self.stdout.write('')
        self.stdout.write('Last 7 days:')
        self.stdout.write(f'  Posts attempted: {recent_posts}')
        self.stdout.write(f'  Posts successful: {recent_successful}')
        
        # Posts ready for retry
        retry_ready = LinkedInPost.objects.filter(
            status='retrying',
            next_retry_at__lte=timezone.now()
        ).count()
        
        if retry_ready > 0:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(f'Posts ready for retry: {retry_ready}'))

    def _build_linkedin_post_url(self, linkedin_post_id):
        """Build LinkedIn post URL from post ID"""
        if not linkedin_post_id:
            return None
        
        # LinkedIn post URLs follow the pattern:
        # https://www.linkedin.com/feed/update/urn:li:share:{post_id}
        # or https://www.linkedin.com/feed/update/urn:li:ugcPost:{post_id}
        
        # Extract the actual ID from the URN format if needed
        if linkedin_post_id.startswith('urn:li:'):
            return f"https://www.linkedin.com/feed/update/{linkedin_post_id}"
        else:
            # Assume it's already a clean ID
            return f"https://www.linkedin.com/feed/update/urn:li:ugcPost:{linkedin_post_id}"