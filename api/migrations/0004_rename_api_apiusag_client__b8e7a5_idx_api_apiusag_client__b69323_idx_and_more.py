# Generated by Django 5.2.3 on 2025-07-19 06:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_add_api_authentication_models'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='apiusagelog',
            new_name='api_apiusag_client__b69323_idx',
            old_name='api_apiusag_client__b8e7a5_idx',
        ),
        migrations.RenameIndex(
            model_name='apiusagelog',
            new_name='api_apiusag_endpoin_423f00_idx',
            old_name='api_apiusag_endpoin_8b4c8a_idx',
        ),
        migrations.RenameIndex(
            model_name='apiusagelog',
            new_name='api_apiusag_status__9bfbaa_idx',
            old_name='api_apiusag_status__c8f9d2_idx',
        ),
    ]
