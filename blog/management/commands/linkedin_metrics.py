"""
Management command to view LinkedIn integration metrics and monitoring data.

This command provides comprehensive reporting on:
- Hashtag generation performance and patterns
- Image posting decisions and outcomes
- Configuration usage statistics
- Error rates and fallback mechanism usage
- API quota utilization
"""

import json
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from blog.services.linkedin_metrics_logger import LinkedInMetricsLogger
from blog.services.linkedin_error_logger import LinkedInErrorLogger


class Command(BaseCommand):
    help = 'Display LinkedIn integration metrics and monitoring data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Number of hours to look back for metrics (default: 24)'
        )
        parser.add_argument(
            '--format',
            choices=['table', 'json'],
            default='table',
            help='Output format (default: table)'
        )
        parser.add_argument(
            '--category',
            choices=['all', 'hashtags', 'images', 'errors', 'quota', 'fallbacks'],
            default='all',
            help='Specific category to display (default: all)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed metrics and breakdowns'
        )
    
    def handle(self, *args, **options):
        hours = options['hours']
        output_format = options['format']
        category = options['category']
        verbose = options['verbose']
        
        try:
            metrics_logger = LinkedInMetricsLogger()
            error_logger = LinkedInErrorLogger()
            
            self.stdout.write(
                self.style.SUCCESS(f'\nLinkedIn Integration Metrics Report')
            )
            self.stdout.write(f'Generated at: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}')
            self.stdout.write(f'Period: Last {hours} hours\n')
            
            if category in ['all', 'hashtags']:
                self._display_hashtag_metrics(metrics_logger, output_format, verbose)
            
            if category in ['all', 'images']:
                self._display_image_posting_metrics(metrics_logger, output_format, verbose)
            
            if category in ['all', 'errors']:
                self._display_error_metrics(error_logger, hours, output_format, verbose)
            
            if category in ['all', 'quota']:
                self._display_quota_metrics(metrics_logger, output_format, verbose)
            
            if category in ['all', 'fallbacks']:
                self._display_fallback_metrics(metrics_logger, output_format, verbose)
            
            if output_format == 'json':
                # Output complete metrics as JSON
                complete_metrics = metrics_logger.get_metrics_summary(hours)
                error_summary = error_logger.get_error_summary(hours)
                complete_metrics['error_summary'] = error_summary
                
                self.stdout.write('\n' + json.dumps(complete_metrics, indent=2))
        
        except Exception as e:
            raise CommandError(f'Error generating metrics report: {e}')
    
    def _display_hashtag_metrics(self, metrics_logger, output_format, verbose):
        """Display hashtag generation metrics."""
        self.stdout.write(self.style.HTTP_INFO('\n📊 Hashtag Generation Metrics'))
        self.stdout.write('=' * 50)
        
        try:
            hashtag_metrics = metrics_logger._get_hashtag_metrics_summary()
            
            if hashtag_metrics.get('status') == 'no_data':
                self.stdout.write(self.style.WARNING('No hashtag generation data available'))
                return
            
            if hashtag_metrics.get('status') == 'no_attempts':
                self.stdout.write(self.style.WARNING('No hashtag generation attempts recorded'))
                return
            
            # Basic metrics
            total_attempts = hashtag_metrics.get('total_attempts', 0)
            successful_attempts = hashtag_metrics.get('successful_attempts', 0)
            failed_attempts = hashtag_metrics.get('failed_attempts', 0)
            success_rate = hashtag_metrics.get('success_rate_percentage', 0)
            total_hashtags = hashtag_metrics.get('total_hashtags_generated', 0)
            avg_time = hashtag_metrics.get('avg_generation_time_ms', 0)
            
            self.stdout.write(f'Total Attempts: {total_attempts}')
            self.stdout.write(f'Successful: {successful_attempts} ({success_rate}%)')
            self.stdout.write(f'Failed: {failed_attempts}')
            self.stdout.write(f'Total Hashtags Generated: {total_hashtags}')
            self.stdout.write(f'Average Generation Time: {avg_time}ms')
            
            if total_attempts > 0:
                avg_hashtags_per_post = total_hashtags / successful_attempts if successful_attempts > 0 else 0
                self.stdout.write(f'Average Hashtags per Post: {avg_hashtags_per_post:.1f}')
            
            # Source usage breakdown
            if verbose:
                source_usage = hashtag_metrics.get('source_usage', {})
                if source_usage:
                    self.stdout.write('\nHashtag Sources:')
                    for source, count in source_usage.items():
                        percentage = (count / total_hashtags * 100) if total_hashtags > 0 else 0
                        self.stdout.write(f'  {source.title()}: {count} ({percentage:.1f}%)')
                
                # Error patterns
                error_patterns = hashtag_metrics.get('error_patterns', {})
                if error_patterns:
                    self.stdout.write('\nTop Error Patterns:')
                    sorted_errors = sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)
                    for error, count in sorted_errors[:5]:
                        self.stdout.write(f'  {error}: {count} occurrences')
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error displaying hashtag metrics: {e}'))
    
    def _display_image_posting_metrics(self, metrics_logger, output_format, verbose):
        """Display image posting decision metrics."""
        self.stdout.write(self.style.HTTP_INFO('\n🖼️  Image Posting Metrics'))
        self.stdout.write('=' * 50)
        
        try:
            image_metrics = metrics_logger._get_image_posting_metrics_summary()
            
            if image_metrics.get('status') == 'no_data':
                self.stdout.write(self.style.WARNING('No image posting data available'))
                return
            
            if image_metrics.get('status') == 'no_decisions':
                self.stdout.write(self.style.WARNING('No image posting decisions recorded'))
                return
            
            # Basic metrics
            total_decisions = image_metrics.get('total_decisions', 0)
            images_included = image_metrics.get('images_included', 0)
            images_excluded = image_metrics.get('images_excluded', 0)
            inclusion_rate = image_metrics.get('inclusion_rate_percentage', 0)
            avg_decision_time = image_metrics.get('avg_decision_time_ms', 0)
            
            self.stdout.write(f'Total Decisions: {total_decisions}')
            self.stdout.write(f'Images Included: {images_included} ({inclusion_rate}%)')
            self.stdout.write(f'Images Excluded: {images_excluded} ({100 - inclusion_rate:.1f}%)')
            self.stdout.write(f'Average Decision Time: {avg_decision_time}ms')
            
            # Decision type breakdown
            if verbose:
                decision_types = image_metrics.get('decision_types', {})
                if decision_types:
                    self.stdout.write('\nDecision Types:')
                    for decision_type, count in decision_types.items():
                        percentage = (count / total_decisions * 100) if total_decisions > 0 else 0
                        self.stdout.write(f'  {decision_type.replace("_", " ").title()}: {count} ({percentage:.1f}%)')
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error displaying image posting metrics: {e}'))
    
    def _display_error_metrics(self, error_logger, hours, output_format, verbose):
        """Display error metrics and patterns."""
        self.stdout.write(self.style.HTTP_INFO('\n⚠️  Error Metrics'))
        self.stdout.write('=' * 50)
        
        try:
            error_summary = error_logger.get_error_summary(hours)
            
            total_errors = error_summary.get('total_errors', 0)
            critical_errors = error_summary.get('critical_errors', 0)
            categories = error_summary.get('categories', {})
            
            self.stdout.write(f'Total Errors: {total_errors}')
            self.stdout.write(f'Critical Errors: {critical_errors}')
            
            if total_errors == 0:
                self.stdout.write(self.style.SUCCESS('No errors recorded in the specified period'))
                return
            
            # Error breakdown by category
            if categories:
                self.stdout.write('\nError Categories:')
                for category, metrics in categories.items():
                    count = metrics.get('count', 0)
                    percentage = (count / total_errors * 100) if total_errors > 0 else 0
                    self.stdout.write(f'  {category.replace("_", " ").title()}: {count} ({percentage:.1f}%)')
                    
                    if verbose:
                        severity_counts = metrics.get('severity_counts', {})
                        if severity_counts:
                            for severity, sev_count in severity_counts.items():
                                self.stdout.write(f'    {severity.title()}: {sev_count}')
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error displaying error metrics: {e}'))
    
    def _display_quota_metrics(self, metrics_logger, output_format, verbose):
        """Display API quota utilization metrics."""
        self.stdout.write(self.style.HTTP_INFO('\n📈 API Quota Metrics'))
        self.stdout.write('=' * 50)
        
        try:
            quota_metrics = metrics_logger._get_quota_metrics_summary()
            
            if quota_metrics.get('status') == 'no_data':
                self.stdout.write(self.style.WARNING('No quota data available'))
                return
            
            daily_used = quota_metrics.get('daily_quota_used', 0)
            daily_limit = quota_metrics.get('daily_quota_limit', 100)
            usage_percentage = quota_metrics.get('usage_percentage', 0)
            remaining = quota_metrics.get('remaining_quota', 0)
            
            self.stdout.write(f'Daily Quota Used: {daily_used}/{daily_limit}')
            self.stdout.write(f'Usage Percentage: {usage_percentage:.1f}%')
            self.stdout.write(f'Remaining Quota: {remaining}')
            
            # Color-code based on usage
            if usage_percentage >= 90:
                self.stdout.write(self.style.ERROR('⚠️  CRITICAL: Quota usage very high'))
            elif usage_percentage >= 80:
                self.stdout.write(self.style.WARNING('⚠️  WARNING: Quota usage high'))
            elif usage_percentage >= 50:
                self.stdout.write(self.style.HTTP_INFO('ℹ️  INFO: Moderate quota usage'))
            else:
                self.stdout.write(self.style.SUCCESS('✅ Good: Low quota usage'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error displaying quota metrics: {e}'))
    
    def _display_fallback_metrics(self, metrics_logger, output_format, verbose):
        """Display fallback mechanism metrics."""
        self.stdout.write(self.style.HTTP_INFO('\n🔄 Fallback Mechanism Metrics'))
        self.stdout.write('=' * 50)
        
        try:
            fallback_metrics = metrics_logger._get_fallback_metrics_summary()
            
            if fallback_metrics.get('status') == 'no_data':
                self.stdout.write(self.style.WARNING('No fallback data available'))
                return
            
            if fallback_metrics.get('status') == 'no_fallbacks':
                self.stdout.write(self.style.SUCCESS('No fallback mechanisms triggered'))
                return
            
            total_fallbacks = fallback_metrics.get('total_fallbacks', 0)
            successful_fallbacks = fallback_metrics.get('successful_fallbacks', 0)
            failed_fallbacks = fallback_metrics.get('failed_fallbacks', 0)
            success_rate = fallback_metrics.get('success_rate_percentage', 0)
            
            self.stdout.write(f'Total Fallbacks: {total_fallbacks}')
            self.stdout.write(f'Successful: {successful_fallbacks} ({success_rate}%)')
            self.stdout.write(f'Failed: {failed_fallbacks}')
            
            if verbose:
                # Fallback types
                fallback_types = fallback_metrics.get('fallback_types', {})
                if fallback_types:
                    self.stdout.write('\nFallback Types:')
                    for fallback_type, count in fallback_types.items():
                        percentage = (count / total_fallbacks * 100) if total_fallbacks > 0 else 0
                        self.stdout.write(f'  {fallback_type.replace("_", " ").title()}: {count} ({percentage:.1f}%)')
                
                # Error triggers
                error_triggers = fallback_metrics.get('error_triggers', {})
                if error_triggers:
                    self.stdout.write('\nError Triggers:')
                    for error_type, count in error_triggers.items():
                        percentage = (count / total_fallbacks * 100) if total_fallbacks > 0 else 0
                        self.stdout.write(f'  {error_type}: {count} ({percentage:.1f}%)')
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error displaying fallback metrics: {e}'))