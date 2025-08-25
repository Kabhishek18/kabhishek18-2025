"""
Management command to generate comprehensive LinkedIn integration metrics reports.

This command provides detailed reporting on hashtag generation, image posting,
configuration changes, and overall system health.
"""

import json
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.core.cache import cache

from blog.services.linkedin_metrics_logger import linkedin_metrics_logger
from blog.services.linkedin_content_formatter import LinkedInContentFormatter
from blog.linkedin_models import LinkedInConfig


class Command(BaseCommand):
    help = 'Generate comprehensive LinkedIn integration metrics report'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            choices=['json', 'text', 'summary'],
            default='text',
            help='Output format for the report'
        )
        parser.add_argument(
            '--feature',
            choices=['hashtag', 'image', 'config', 'health', 'all'],
            default='all',
            help='Specific feature to report on'
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset metrics after generating report'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (optional)'
        )

    def handle(self, *args, **options):
        try:
            self.stdout.write(
                self.style.SUCCESS('Generating LinkedIn integration metrics report...')
            )
            
            # Generate comprehensive report
            report_data = self.generate_report(options['feature'])
            
            # Format output
            if options['format'] == 'json':
                output = json.dumps(report_data, indent=2, default=str)
            elif options['format'] == 'summary':
                output = self.format_summary_report(report_data)
            else:
                output = self.format_text_report(report_data)
            
            # Output to file or stdout
            if options['output']:
                with open(options['output'], 'w') as f:
                    f.write(output)
                self.stdout.write(
                    self.style.SUCCESS(f'Report saved to {options["output"]}')
                )
            else:
                self.stdout.write(output)
            
            # Reset metrics if requested
            if options['reset']:
                self.reset_metrics(options['feature'])
                self.stdout.write(
                    self.style.WARNING('Metrics have been reset')
                )
            
        except Exception as e:
            raise CommandError(f'Error generating report: {e}')

    def generate_report(self, feature_filter):
        """Generate comprehensive metrics report."""
        report = {
            'generated_at': timezone.now().isoformat(),
            'report_type': feature_filter,
            'linkedin_configs': self.get_config_summary(),
            'metrics': {}
        }
        
        if feature_filter in ['hashtag', 'all']:
            report['metrics']['hashtag_generation'] = self.get_hashtag_metrics()
        
        if feature_filter in ['image', 'all']:
            report['metrics']['image_posting'] = self.get_image_posting_metrics()
        
        if feature_filter in ['config', 'all']:
            report['metrics']['configuration_changes'] = self.get_config_change_metrics()
        
        if feature_filter in ['health', 'all']:
            report['metrics']['health_status'] = self.get_health_metrics()
        
        if feature_filter == 'all':
            report['comprehensive_summary'] = linkedin_metrics_logger.get_comprehensive_metrics_summary()
        
        return report

    def get_config_summary(self):
        """Get summary of LinkedIn configurations."""
        try:
            configs = LinkedInConfig.objects.all()
            active_config = LinkedInConfig.get_active_config()
            
            return {
                'total_configs': configs.count(),
                'active_config_id': active_config.id if active_config else None,
                'active_config_status': {
                    'hashtags_enabled': active_config.enable_hashtags if active_config else False,
                    'max_hashtags': active_config.max_hashtags if active_config else 0,
                    'image_posting_enabled': active_config.enable_image_posting if active_config else False,
                    'image_posting_strategy': active_config.image_posting_strategy if active_config else 'unknown'
                } if active_config else None
            }
        except Exception as e:
            return {'error': str(e)}

    def get_hashtag_metrics(self):
        """Get hashtag generation metrics."""
        try:
            formatter = LinkedInContentFormatter()
            return formatter.get_hashtag_metrics_summary()
        except Exception as e:
            return {'error': str(e)}

    def get_image_posting_metrics(self):
        """Get image posting decision metrics."""
        try:
            formatter = LinkedInContentFormatter()
            return formatter.get_image_posting_metrics_summary()
        except Exception as e:
            return {'error': str(e)}

    def get_config_change_metrics(self):
        """Get configuration change metrics."""
        try:
            cache_key = "linkedin_metrics_config_changes"
            return cache.get(cache_key, {'status': 'no_data'})
        except Exception as e:
            return {'error': str(e)}

    def get_health_metrics(self):
        """Get health check metrics."""
        try:
            cache_key = "linkedin_metrics_health_metrics"
            health_data = cache.get(cache_key, {'status': 'no_data'})
            
            # Add current configuration health check
            active_config = LinkedInConfig.get_active_config()
            if active_config:
                health_data['current_config_health'] = self.check_config_health(active_config)
            
            return health_data
        except Exception as e:
            return {'error': str(e)}

    def check_config_health(self, config):
        """Perform health check on LinkedIn configuration."""
        health_issues = []
        health_status = 'healthy'
        
        try:
            # Check credential status
            credential_status = config.get_credential_status()
            if not credential_status['is_valid']:
                health_issues.append('Invalid or expired credentials')
                health_status = 'critical'
            
            # Check hashtag configuration
            if config.enable_hashtags:
                if config.max_hashtags == 0:
                    health_issues.append('Hashtags enabled but max_hashtags is 0')
                    health_status = 'warning'
                elif config.max_hashtags > 10:
                    health_issues.append(f'max_hashtags very high: {config.max_hashtags}')
                    if health_status == 'healthy':
                        health_status = 'warning'
            
            # Check image posting configuration
            if config.enable_image_posting and config.image_posting_strategy == 'category_based':
                if not config.category_image_overrides:
                    health_issues.append('Category-based image posting enabled but no category overrides configured')
                    if health_status == 'healthy':
                        health_status = 'warning'
            
            return {
                'status': health_status,
                'issues': health_issues,
                'credential_status': credential_status,
                'checked_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'checked_at': timezone.now().isoformat()
            }

    def format_text_report(self, report_data):
        """Format report as human-readable text."""
        lines = []
        lines.append("=" * 60)
        lines.append("LinkedIn Integration Metrics Report")
        lines.append("=" * 60)
        lines.append(f"Generated: {report_data['generated_at']}")
        lines.append(f"Report Type: {report_data['report_type']}")
        lines.append("")
        
        # Configuration Summary
        config_summary = report_data.get('linkedin_configs', {})
        lines.append("Configuration Summary:")
        lines.append("-" * 20)
        lines.append(f"Total Configurations: {config_summary.get('total_configs', 'Unknown')}")
        lines.append(f"Active Configuration ID: {config_summary.get('active_config_id', 'None')}")
        
        if config_summary.get('active_config_status'):
            status = config_summary['active_config_status']
            lines.append(f"  - Hashtags Enabled: {status.get('hashtags_enabled', 'Unknown')}")
            lines.append(f"  - Max Hashtags: {status.get('max_hashtags', 'Unknown')}")
            lines.append(f"  - Image Posting Enabled: {status.get('image_posting_enabled', 'Unknown')}")
            lines.append(f"  - Image Strategy: {status.get('image_posting_strategy', 'Unknown')}")
        lines.append("")
        
        # Feature Metrics
        metrics = report_data.get('metrics', {})
        
        # Hashtag Generation Metrics
        if 'hashtag_generation' in metrics:
            hashtag_metrics = metrics['hashtag_generation']
            lines.append("Hashtag Generation Metrics:")
            lines.append("-" * 30)
            
            if hashtag_metrics.get('status') == 'active':
                lines.append(f"Total Attempts: {hashtag_metrics.get('total_attempts', 0)}")
                lines.append(f"Success Rate: {hashtag_metrics.get('success_rate_percent', 0)}%")
                lines.append(f"Average Hashtags per Post: {hashtag_metrics.get('avg_hashtags_per_post', 0)}")
                lines.append(f"Average Generation Time: {hashtag_metrics.get('avg_generation_time_seconds', 0)}s")
                lines.append(f"Health Status: {hashtag_metrics.get('health_status', 'Unknown')}")
            else:
                lines.append(f"Status: {hashtag_metrics.get('status', 'Unknown')}")
                lines.append(f"Message: {hashtag_metrics.get('message', 'No additional information')}")
            lines.append("")
        
        # Image Posting Metrics
        if 'image_posting' in metrics:
            image_metrics = metrics['image_posting']
            lines.append("Image Posting Decision Metrics:")
            lines.append("-" * 35)
            
            if image_metrics.get('status') == 'active':
                lines.append(f"Total Decisions: {image_metrics.get('total_decisions', 0)}")
                lines.append(f"Images Included Rate: {image_metrics.get('inclusion_rate_percent', 0)}%")
                lines.append(f"Error Rate: {image_metrics.get('error_rate_percent', 0)}%")
                lines.append(f"Average Decision Time: {image_metrics.get('avg_decision_time_seconds', 0)}s")
                lines.append(f"Health Status: {image_metrics.get('health_status', 'Unknown')}")
            else:
                lines.append(f"Status: {image_metrics.get('status', 'Unknown')}")
                lines.append(f"Message: {image_metrics.get('message', 'No additional information')}")
            lines.append("")
        
        # Health Status
        if 'health_status' in metrics:
            health_metrics = metrics['health_status']
            lines.append("Health Status:")
            lines.append("-" * 15)
            
            if 'current_config_health' in health_metrics:
                config_health = health_metrics['current_config_health']
                lines.append(f"Current Configuration Health: {config_health.get('status', 'Unknown')}")
                
                issues = config_health.get('issues', [])
                if issues:
                    lines.append("Issues Found:")
                    for issue in issues:
                        lines.append(f"  - {issue}")
                else:
                    lines.append("No issues found")
            lines.append("")
        
        return "\n".join(lines)

    def format_summary_report(self, report_data):
        """Format report as brief summary."""
        lines = []
        lines.append("LinkedIn Integration Summary")
        lines.append("=" * 30)
        
        # Overall status
        comprehensive = report_data.get('comprehensive_summary', {})
        overall_status = comprehensive.get('overall_status', 'unknown')
        lines.append(f"Overall Status: {overall_status.upper()}")
        lines.append("")
        
        # Quick stats
        metrics = report_data.get('metrics', {})
        
        if 'hashtag_generation' in metrics:
            hashtag = metrics['hashtag_generation']
            if hashtag.get('status') == 'active':
                lines.append(f"Hashtag Generation: {hashtag.get('success_rate_percent', 0)}% success rate")
        
        if 'image_posting' in metrics:
            image = metrics['image_posting']
            if image.get('status') == 'active':
                lines.append(f"Image Posting: {image.get('inclusion_rate_percent', 0)}% include images")
        
        config_summary = report_data.get('linkedin_configs', {})
        if config_summary.get('active_config_id'):
            lines.append(f"Active Configuration: ID {config_summary['active_config_id']}")
        
        return "\n".join(lines)

    def reset_metrics(self, feature_filter):
        """Reset metrics based on feature filter."""
        if feature_filter == 'hashtag':
            linkedin_metrics_logger.reset_metrics('hashtag_generation')
        elif feature_filter == 'image':
            linkedin_metrics_logger.reset_metrics('image_posting_decision')
        elif feature_filter == 'all':
            linkedin_metrics_logger.reset_metrics()
        else:
            # Reset specific feature metrics
            cache_keys_to_reset = []
            
            if feature_filter == 'config':
                cache_keys_to_reset.append('linkedin_metrics_config_changes')
            elif feature_filter == 'health':
                cache_keys_to_reset.append('linkedin_metrics_health_metrics')
            
            for key in cache_keys_to_reset:
                cache.delete(key)