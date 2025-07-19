# api/management/commands/api_stats.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Avg, Q
from api.models import APIClient, APIKey, APIUsageLog
from datetime import timedelta


class Command(BaseCommand):
    help = 'Display API usage statistics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--client',
            type=str,
            help='Show stats for specific client (by name or client_id)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to analyze (default: 7)'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed statistics'
        )

    def handle(self, *args, **options):
        days = options['days']
        since_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(
            self.style.SUCCESS(f'📊 API Statistics (Last {days} days)')
        )
        self.stdout.write('=' * 50)
        
        if options['client']:
            self.show_client_stats(options['client'], since_date, options['detailed'])
        else:
            self.show_overall_stats(since_date, options['detailed'])

    def show_overall_stats(self, since_date, detailed=False):
        # Client statistics
        total_clients = APIClient.objects.count()
        active_clients = APIClient.objects.filter(is_active=True).count()
        
        self.stdout.write(f'\n🏢 Clients:')
        self.stdout.write(f'  Total: {total_clients}')
        self.stdout.write(f'  Active: {active_clients}')
        self.stdout.write(f'  Inactive: {total_clients - active_clients}')
        
        # API Key statistics
        total_keys = APIKey.objects.count()
        active_keys = APIKey.objects.filter(
            is_active=True,
            expires_at__gt=timezone.now()
        ).count()
        expired_keys = APIKey.objects.filter(
            expires_at__lt=timezone.now()
        ).count()
        
        self.stdout.write(f'\n🔑 API Keys:')
        self.stdout.write(f'  Total: {total_keys}')
        self.stdout.write(f'  Active: {active_keys}')
        self.stdout.write(f'  Expired: {expired_keys}')
        
        # Usage statistics
        logs = APIUsageLog.objects.filter(timestamp__gte=since_date)
        total_requests = logs.count()
        
        if total_requests > 0:
            successful_requests = logs.filter(
                status_code__gte=200, 
                status_code__lt=300
            ).count()
            
            avg_response_time = logs.aggregate(avg=Avg('response_time'))['avg']
            
            self.stdout.write(f'\n📈 Usage (Last {(timezone.now() - since_date).days} days):')
            self.stdout.write(f'  Total requests: {total_requests:,}')
            self.stdout.write(f'  Successful: {successful_requests:,} ({(successful_requests/total_requests*100):.1f}%)')
            self.stdout.write(f'  Average response time: {avg_response_time:.3f}s')
            
            # Top endpoints
            top_endpoints = logs.values('endpoint', 'method').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
            
            self.stdout.write(f'\n🔥 Top Endpoints:')
            for i, endpoint in enumerate(top_endpoints, 1):
                self.stdout.write(
                    f'  {i}. {endpoint["method"]} {endpoint["endpoint"]} '
                    f'({endpoint["count"]:,} requests)'
                )
            
            if detailed:
                self.show_detailed_stats(logs)
        else:
            self.stdout.write(f'\n📈 No usage data found for the last {(timezone.now() - since_date).days} days')

    def show_client_stats(self, client_identifier, since_date, detailed=False):
        try:
            # Try to find client by name first, then by client_id
            try:
                client = APIClient.objects.get(name=client_identifier)
            except APIClient.DoesNotExist:
                # Only try UUID lookup if the identifier looks like a UUID
                import uuid
                try:
                    uuid.UUID(client_identifier)
                    client = APIClient.objects.get(client_id=client_identifier)
                except (ValueError, APIClient.DoesNotExist):
                    raise APIClient.DoesNotExist()
        except APIClient.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Client "{client_identifier}" not found')
            )
            return
        
        self.stdout.write(f'\n🏢 Client: {client.name}')
        self.stdout.write(f'  Client ID: {client.client_id}')
        self.stdout.write(f'  Status: {"🟢 Active" if client.is_active else "🔴 Inactive"}')
        self.stdout.write(f'  Created: {client.created_at.strftime("%Y-%m-%d")}')
        
        # Permissions
        permissions = []
        if client.can_read_posts: permissions.append('read-posts')
        if client.can_write_posts: permissions.append('write-posts')
        if client.can_delete_posts: permissions.append('delete-posts')
        if client.can_manage_categories: permissions.append('manage-categories')
        if client.can_access_users: permissions.append('access-users')
        if client.can_access_pages: permissions.append('access-pages')
        
        self.stdout.write(f'  Permissions: {", ".join(permissions) if permissions else "None"}')
        self.stdout.write(f'  Rate limits: {client.requests_per_minute}/min, {client.requests_per_hour}/hour')
        
        # API Keys
        keys = client.api_keys.all()
        active_keys = keys.filter(is_active=True, expires_at__gt=timezone.now())
        
        self.stdout.write(f'\n🔑 API Keys:')
        self.stdout.write(f'  Total: {keys.count()}')
        self.stdout.write(f'  Active: {active_keys.count()}')
        
        # Usage statistics
        logs = APIUsageLog.objects.filter(client=client, timestamp__gte=since_date)
        total_requests = logs.count()
        
        if total_requests > 0:
            successful_requests = logs.filter(
                status_code__gte=200, 
                status_code__lt=300
            ).count()
            
            avg_response_time = logs.aggregate(avg=Avg('response_time'))['avg']
            
            self.stdout.write(f'\n📈 Usage (Last {(timezone.now() - since_date).days} days):')
            self.stdout.write(f'  Total requests: {total_requests:,}')
            self.stdout.write(f'  Successful: {successful_requests:,} ({(successful_requests/total_requests*100):.1f}%)')
            self.stdout.write(f'  Average response time: {avg_response_time:.3f}s')
            
            # Endpoints used
            endpoints = logs.values('endpoint', 'method').annotate(
                count=Count('id')
            ).order_by('-count')
            
            self.stdout.write(f'\n🎯 Endpoints Used:')
            for endpoint in endpoints:
                self.stdout.write(
                    f'  {endpoint["method"]} {endpoint["endpoint"]} '
                    f'({endpoint["count"]:,} requests)'
                )
        else:
            self.stdout.write(f'\n📈 No usage data found for the last {(timezone.now() - since_date).days} days')

    def show_detailed_stats(self, logs):
        # Status code breakdown
        status_codes = logs.values('status_code').annotate(
            count=Count('id')
        ).order_by('status_code')
        
        self.stdout.write(f'\n📊 Status Code Breakdown:')
        for status in status_codes:
            code = status['status_code']
            count = status['count']
            if 200 <= code < 300:
                icon = '✅'
            elif 400 <= code < 500:
                icon = '⚠️'
            else:
                icon = '❌'
            
            self.stdout.write(f'  {icon} {code}: {count:,} requests')
        
        # Daily breakdown
        from django.db.models import TruncDate
        daily_stats = logs.annotate(
            date=TruncDate('timestamp')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        if daily_stats:
            self.stdout.write(f'\n📅 Daily Breakdown:')
            for day in daily_stats:
                self.stdout.write(
                    f'  {day["date"].strftime("%Y-%m-%d")}: {day["count"]:,} requests'
                )