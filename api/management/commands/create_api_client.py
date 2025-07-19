# api/management/commands/create_api_client.py

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from api.models import APIClient, APIKey
from api.utils import get_api_config


class Command(BaseCommand):
    help = 'Create a new API client with optional API key generation'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Client name')
        parser.add_argument('--description', type=str, default='', help='Client description')
        parser.add_argument('--user', type=str, required=True, help='Username of the user creating the client')
        
        # Permission arguments
        parser.add_argument('--read-posts', action='store_true', help='Allow reading posts')
        parser.add_argument('--write-posts', action='store_true', help='Allow writing posts')
        parser.add_argument('--delete-posts', action='store_true', help='Allow deleting posts')
        parser.add_argument('--manage-categories', action='store_true', help='Allow managing categories')
        parser.add_argument('--access-users', action='store_true', help='Allow accessing user data')
        parser.add_argument('--access-pages', action='store_true', help='Allow accessing pages')
        
        # Rate limiting
        parser.add_argument('--rate-minute', type=int, default=60, help='Requests per minute limit')
        parser.add_argument('--rate-hour', type=int, default=1000, help='Requests per hour limit')
        
        # IP restrictions
        parser.add_argument('--allowed-ips', type=str, help='Comma-separated list of allowed IPs')
        
        # API key generation
        parser.add_argument('--generate-key', action='store_true', help='Generate API key immediately')
        parser.add_argument('--key-expiration', type=int, default=24, help='API key expiration in hours')

    def handle(self, *args, **options):
        try:
            # Get the user
            user = User.objects.get(username=options['user'])
        except User.DoesNotExist:
            raise CommandError(f'User "{options["user"]}" does not exist')

        # Check if client name already exists
        if APIClient.objects.filter(name=options['name']).exists():
            raise CommandError(f'Client with name "{options["name"]}" already exists')

        # Create the client
        client = APIClient.objects.create(
            name=options['name'],
            description=options['description'],
            created_by=user,
            can_read_posts=options['read_posts'],
            can_write_posts=options['write_posts'],
            can_delete_posts=options['delete_posts'],
            can_manage_categories=options['manage_categories'],
            can_access_users=options['access_users'],
            can_access_pages=options['access_pages'],
            requests_per_minute=options['rate_minute'],
            requests_per_hour=options['rate_hour'],
            allowed_ips=options['allowed_ips'] or ''
        )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created API client: {client.name}')
        )
        self.stdout.write(f'Client ID: {client.client_id}')
        
        # Display permissions
        permissions = []
        if client.can_read_posts: permissions.append('read-posts')
        if client.can_write_posts: permissions.append('write-posts')
        if client.can_delete_posts: permissions.append('delete-posts')
        if client.can_manage_categories: permissions.append('manage-categories')
        if client.can_access_users: permissions.append('access-users')
        if client.can_access_pages: permissions.append('access-pages')
        
        self.stdout.write(f'Permissions: {", ".join(permissions) if permissions else "None"}')
        self.stdout.write(f'Rate limits: {client.requests_per_minute}/min, {client.requests_per_hour}/hour')
        
        if client.allowed_ips:
            self.stdout.write(f'Allowed IPs: {client.allowed_ips}')

        # Generate API key if requested
        if options['generate_key']:
            try:
                key_data = APIKey.generate_key_pair(client, options['key_expiration'])
                
                self.stdout.write(self.style.SUCCESS('\n🔑 API Key Generated:'))
                self.stdout.write(f'API Key: {key_data["api_key"]}')
                self.stdout.write(f'Encryption Key: {key_data["api_key_instance"].encryption_key}')
                self.stdout.write(f'Expires: {key_data["expires_at"]}')
                self.stdout.write(
                    self.style.WARNING('\n⚠️  Save these keys securely! They cannot be retrieved again.')
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to generate API key: {str(e)}')
                )