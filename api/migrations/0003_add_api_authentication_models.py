# Generated migration for API authentication models

import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models
import api.models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_scriptcategory_scripttemplate_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='APIClient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('client_id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='Unique identifier for this client', unique=True)),
                ('name', models.CharField(help_text='Friendly name for this API client', max_length=200)),
                ('description', models.TextField(blank=True, help_text='Description of the client application')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this client can access the API')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('can_read_posts', models.BooleanField(default=True, help_text='Can read blog posts')),
                ('can_write_posts', models.BooleanField(default=False, help_text='Can create and update blog posts')),
                ('can_delete_posts', models.BooleanField(default=False, help_text='Can delete blog posts')),
                ('can_manage_categories', models.BooleanField(default=False, help_text='Can manage blog categories')),
                ('can_access_users', models.BooleanField(default=False, help_text='Can access user information')),
                ('can_access_pages', models.BooleanField(default=True, help_text='Can access page content')),
                ('requests_per_minute', models.IntegerField(default=60, help_text='Maximum requests per minute')),
                ('requests_per_hour', models.IntegerField(default=1000, help_text='Maximum requests per hour')),
                ('allowed_ips', models.TextField(blank=True, help_text='Comma-separated list of allowed IP addresses (leave blank for no restriction)', validators=[api.models.validate_ip_list])),
                ('created_by', models.ForeignKey(help_text='User who created this client', on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'API Client',
                'verbose_name_plural': 'API Clients',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='APIKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key_hash', models.CharField(help_text='Hashed version of the API key', max_length=128, unique=True)),
                ('encryption_key', models.CharField(help_text='Encryption key for secure communications', max_length=256)),
                ('expires_at', models.DateTimeField(help_text='When this key expires')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this key is currently active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_used_at', models.DateTimeField(blank=True, help_text='Last time this key was used', null=True)),
                ('usage_count', models.IntegerField(default=0, help_text='Number of times this key has been used')),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='api_keys', to='api.apiclient')),
            ],
            options={
                'verbose_name': 'API Key',
                'verbose_name_plural': 'API Keys',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='APIUsageLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('endpoint', models.CharField(help_text='API endpoint that was accessed', max_length=200)),
                ('method', models.CharField(help_text='HTTP method used', max_length=10)),
                ('status_code', models.IntegerField(help_text='HTTP response status code')),
                ('response_time', models.FloatField(help_text='Response time in seconds')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(help_text='Client IP address')),
                ('user_agent', models.TextField(blank=True, help_text='Client user agent string')),
                ('request_size', models.IntegerField(default=0, help_text='Request size in bytes')),
                ('response_size', models.IntegerField(default=0, help_text='Response size in bytes')),
                ('error_message', models.TextField(blank=True, help_text='Error message if request failed')),
                ('api_key', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.apikey')),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usage_logs', to='api.apiclient')),
            ],
            options={
                'verbose_name': 'API Usage Log',
                'verbose_name_plural': 'API Usage Logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='apiusagelog',
            index=models.Index(fields=['client', '-timestamp'], name='api_apiusag_client__b8e7a5_idx'),
        ),
        migrations.AddIndex(
            model_name='apiusagelog',
            index=models.Index(fields=['endpoint', '-timestamp'], name='api_apiusag_endpoin_8b4c8a_idx'),
        ),
        migrations.AddIndex(
            model_name='apiusagelog',
            index=models.Index(fields=['status_code', '-timestamp'], name='api_apiusag_status__c8f9d2_idx'),
        ),
    ]