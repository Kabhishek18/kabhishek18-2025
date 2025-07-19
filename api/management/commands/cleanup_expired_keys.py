# api/management/commands/cleanup_expired_keys.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import APIKey


class Command(BaseCommand):
    help = 'Clean up expired API keys'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--days-old',
            type=int,
            default=7,
            help='Delete keys expired for more than X days (default: 7)'
        )

    def handle(self, *args, **options):
        # Calculate cutoff date
        cutoff_date = timezone.now() - timezone.timedelta(days=options['days_old'])
        
        # Find expired keys
        expired_keys = APIKey.objects.filter(
            expires_at__lt=cutoff_date
        )
        
        count = expired_keys.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No expired keys found to clean up.')
            )
            return
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would delete {count} expired API keys:')
            )
            
            for key in expired_keys:
                self.stdout.write(
                    f'  - {key.client.name} (expired: {key.expires_at})'
                )
        else:
            # Show what will be deleted
            self.stdout.write(f'Found {count} expired API keys to delete:')
            for key in expired_keys:
                self.stdout.write(
                    f'  - {key.client.name} (expired: {key.expires_at})'
                )
            
            # Confirm deletion
            confirm = input('\nAre you sure you want to delete these keys? (yes/no): ')
            
            if confirm.lower() in ['yes', 'y']:
                deleted_count = expired_keys.delete()[0]
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully deleted {deleted_count} expired API keys.')
                )
            else:
                self.stdout.write('Deletion cancelled.')
        
        # Show statistics
        total_keys = APIKey.objects.count()
        active_keys = APIKey.objects.filter(
            is_active=True,
            expires_at__gt=timezone.now()
        ).count()
        
        self.stdout.write(f'\nAPI Key Statistics:')
        self.stdout.write(f'  Total keys: {total_keys}')
        self.stdout.write(f'  Active keys: {active_keys}')
        self.stdout.write(f'  Expired keys: {total_keys - active_keys}')