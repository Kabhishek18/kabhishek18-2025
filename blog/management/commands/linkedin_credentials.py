"""
Django management command for LinkedIn credential management.
Provides utilities for validating, testing, and managing LinkedIn API credentials.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from blog.linkedin_models import LinkedInConfig
from blog.utils.encryption import credential_encryption
import json


class Command(BaseCommand):
    help = 'Manage LinkedIn API credentials'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['validate', 'status', 'clear', 'generate-key'],
            help='Action to perform'
        )
        parser.add_argument(
            '--config-id',
            type=int,
            help='Specific configuration ID to operate on'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Apply action to all configurations'
        )

    def handle(self, *args, **options):
        action = options['action']
        config_id = options.get('config_id')
        all_configs = options.get('all', False)

        if action == 'generate-key':
            self.generate_encryption_key()
        elif action == 'validate':
            self.validate_credentials(config_id, all_configs)
        elif action == 'status':
            self.show_status(config_id, all_configs)
        elif action == 'clear':
            self.clear_tokens(config_id, all_configs)

    def generate_encryption_key(self):
        """Generate a new encryption key for credentials"""
        key = credential_encryption.generate_key()
        self.stdout.write(
            self.style.SUCCESS(f'Generated encryption key: {key}')
        )
        self.stdout.write(
            'Add this to your settings.py or environment variables as LINKEDIN_ENCRYPTION_KEY'
        )

    def get_configurations(self, config_id, all_configs):
        """Get configurations based on parameters"""
        if config_id:
            try:
                return [LinkedInConfig.objects.get(id=config_id)]
            except LinkedInConfig.DoesNotExist:
                raise CommandError(f'Configuration with ID {config_id} not found')
        elif all_configs:
            return LinkedInConfig.objects.all()
        else:
            # Get active configuration
            active_config = LinkedInConfig.get_active_config()
            if not active_config:
                raise CommandError('No active LinkedIn configuration found')
            return [active_config]

    def validate_credentials(self, config_id, all_configs):
        """Validate LinkedIn credentials"""
        configs = self.get_configurations(config_id, all_configs)
        
        for config in configs:
            self.stdout.write(f'\nValidating configuration {config.id}:')
            self.stdout.write(f'  Client ID: {config.client_id}')
            
            # Validate credentials
            validation = config.validate_credentials()
            
            if validation['client_secret_valid']:
                self.stdout.write(
                    self.style.SUCCESS('  ✓ Client Secret: Valid')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('  ✗ Client Secret: Invalid or missing')
                )
            
            if validation['access_token_valid']:
                self.stdout.write(
                    self.style.SUCCESS('  ✓ Access Token: Valid')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('  ✗ Access Token: Invalid or missing')
                )
            
            if validation['refresh_token_valid']:
                self.stdout.write(
                    self.style.SUCCESS('  ✓ Refresh Token: Valid')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('  ⚠ Refresh Token: Invalid or missing')
                )
            
            # Show errors
            if validation['errors']:
                self.stdout.write(self.style.ERROR('  Errors:'))
                for error in validation['errors']:
                    self.stdout.write(f'    • {error}')
            
            # Overall status
            if config.has_valid_credentials():
                self.stdout.write(
                    self.style.SUCCESS('  Overall Status: Ready for API calls')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('  Overall Status: Not ready for API calls')
                )

    def show_status(self, config_id, all_configs):
        """Show detailed status of LinkedIn configurations"""
        configs = self.get_configurations(config_id, all_configs)
        
        for config in configs:
            status = config.get_credential_status()
            
            self.stdout.write(f'\nConfiguration {config.id} Status:')
            self.stdout.write(f'  Active: {config.is_active}')
            self.stdout.write(f'  Client ID: {config.client_id}')
            self.stdout.write(f'  Has Client Secret: {status["has_client_secret"]}')
            self.stdout.write(f'  Has Access Token: {status["has_access_token"]}')
            self.stdout.write(f'  Has Refresh Token: {status["has_refresh_token"]}')
            self.stdout.write(f'  Token Expired: {status["token_expired"]}')
            self.stdout.write(f'  Needs Refresh: {status["needs_refresh"]}')
            self.stdout.write(f'  Is Valid: {status["is_valid"]}')
            
            if status.get('expires_at'):
                self.stdout.write(f'  Token Expires: {status["expires_at"]}')
                if status.get('expires_in_hours'):
                    hours = status['expires_in_hours']
                    if hours > 0:
                        self.stdout.write(f'  Expires In: {hours:.1f} hours')
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'  Expired {abs(hours):.1f} hours ago')
                        )
            
            self.stdout.write(f'  Created: {config.created_at}')
            self.stdout.write(f'  Updated: {config.updated_at}')

    def clear_tokens(self, config_id, all_configs):
        """Clear tokens for configurations"""
        configs = self.get_configurations(config_id, all_configs)
        
        for config in configs:
            self.stdout.write(f'Clearing tokens for configuration {config.id}...')
            config.clear_tokens()
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Tokens cleared for configuration {config.id}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Cleared tokens for {len(configs)} configuration(s)')
        )