"""
Management command to fix LinkedIn credential decryption issues.
"""
from django.core.management.base import BaseCommand, CommandError
from blog.linkedin_models import LinkedInConfig
from blog.utils.encryption import credential_encryption
import getpass


class Command(BaseCommand):
    help = 'Fix LinkedIn credential decryption issues by re-encrypting credentials'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config-id',
            type=int,
            help='Specific LinkedIn config ID to fix (default: all configs)',
        )
        parser.add_argument(
            '--clear-credentials',
            action='store_true',
            help='Clear all encrypted credentials (will require re-entering them)',
        )
        parser.add_argument(
            '--set-credentials',
            action='store_true',
            help='Set new credentials interactively',
        )

    def handle(self, *args, **options):
        config_id = options.get('config_id')
        clear_credentials = options.get('clear_credentials')
        set_credentials = options.get('set_credentials')

        # Get configs to work with
        if config_id:
            try:
                configs = [LinkedInConfig.objects.get(id=config_id)]
            except LinkedInConfig.DoesNotExist:
                raise CommandError(f'LinkedIn config with ID {config_id} does not exist')
        else:
            configs = LinkedInConfig.objects.all()

        if not configs:
            self.stdout.write(self.style.WARNING('No LinkedIn configurations found'))
            return

        for config in configs:
            self.stdout.write(f'\nProcessing LinkedIn config {config.id}:')
            self.stdout.write(f'  Client ID: {config.client_id}')
            self.stdout.write(f'  Active: {config.is_active}')

            # Check current credential status
            status = config.get_credential_status()
            self.stdout.write(f'  Current status:')
            self.stdout.write(f'    Has client secret: {status["has_client_secret"]}')
            self.stdout.write(f'    Has access token: {status["has_access_token"]}')
            self.stdout.write(f'    Has refresh token: {status["has_refresh_token"]}')

            if clear_credentials:
                self.stdout.write('  Clearing credentials...')
                # Use update to bypass model validation
                was_active = config.is_active
                LinkedInConfig.objects.filter(id=config.id).update(
                    is_active=False,
                    client_secret='',
                    access_token='',
                    refresh_token='',
                    token_expires_at=None
                )
                
                # Reactivate if it was active before
                if was_active:
                    self.stdout.write('  Note: Configuration was deactivated due to missing credentials')
                    self.stdout.write('  Use --set-credentials to add new credentials and reactivate')
                
                self.stdout.write(self.style.SUCCESS('  ✓ Credentials cleared'))

            elif set_credentials:
                self.stdout.write('  Setting new credentials...')
                
                # Get client secret
                if not status["has_client_secret"] or self.confirm('Replace client secret?'):
                    client_secret = getpass.getpass('Enter LinkedIn client secret: ')
                    if client_secret.strip():
                        config.set_client_secret(client_secret.strip())
                        self.stdout.write('  ✓ Client secret set')
                
                # Get access token
                if not status["has_access_token"] or self.confirm('Replace access token?'):
                    access_token = getpass.getpass('Enter LinkedIn access token: ')
                    if access_token.strip():
                        config.set_access_token(access_token.strip())
                        self.stdout.write('  ✓ Access token set')
                
                # Get refresh token (optional)
                if not status["has_refresh_token"] or self.confirm('Replace refresh token?'):
                    refresh_token = getpass.getpass('Enter LinkedIn refresh token (optional): ')
                    if refresh_token.strip():
                        config.set_refresh_token(refresh_token.strip())
                        self.stdout.write('  ✓ Refresh token set')
                
                config.save()
                self.stdout.write(self.style.SUCCESS('  ✓ New credentials saved'))

            else:
                # Just try to validate current credentials
                try:
                    validation_result = config.validate_credentials()
                    if validation_result['errors']:
                        self.stdout.write(self.style.ERROR(f'  ✗ Validation errors: {validation_result["errors"]}'))
                        self.stdout.write('  Run with --clear-credentials or --set-credentials to fix')
                    else:
                        self.stdout.write(self.style.SUCCESS('  ✓ Credentials are valid'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Validation failed: {e}'))

        self.stdout.write(self.style.SUCCESS('\nDone!'))

    def confirm(self, message):
        """Ask for user confirmation."""
        response = input(f'{message} (y/N): ').lower().strip()
        return response in ('y', 'yes')