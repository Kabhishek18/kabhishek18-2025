# Generated by Django 5.2.3 on 2025-07-20 13:33

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SiteFilesConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('site_name', models.CharField(default='My Site', help_text='Name of the website', max_length=255)),
                ('site_url', models.URLField(default='https://example.com', help_text='Base URL of the website (e.g., https://example.com)')),
                ('sitemap_path', models.CharField(default='static/Sitemap.xml', help_text='Path to the sitemap file relative to the project root', max_length=255)),
                ('robots_path', models.CharField(default='static/robots.txt', help_text='Path to the robots.txt file relative to the project root', max_length=255)),
                ('security_path', models.CharField(default='static/security.txt', help_text='Path to the security.txt file relative to the project root', max_length=255)),
                ('llms_path', models.CharField(default='static/humans.txt', help_text='Path to the LLMs.txt file relative to the project root', max_length=255)),
                ('update_frequency', models.CharField(choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')], default='daily', help_text='How often the site files should be updated', max_length=20)),
                ('update_sitemap', models.BooleanField(default=True, help_text='Enable automatic sitemap updates')),
                ('update_robots', models.BooleanField(default=True, help_text='Enable automatic robots.txt updates')),
                ('update_security', models.BooleanField(default=True, help_text='Enable automatic security.txt updates')),
                ('update_llms', models.BooleanField(default=True, help_text='Enable automatic LLMs.txt updates')),
                ('last_update', models.DateTimeField(blank=True, help_text='When the site files were last updated', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='When this configuration was created')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='When this configuration was last modified')),
            ],
            options={
                'verbose_name': 'Site Files Configuration',
                'verbose_name_plural': 'Site Files Configuration',
            },
        ),
    ]
