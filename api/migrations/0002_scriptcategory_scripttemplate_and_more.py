# Generated by Django 5.2.3 on 2025-06-30 07:11

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ScriptCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('icon', models.CharField(default='📝', max_length=50)),
            ],
            options={
                'verbose_name_plural': 'Script Categories',
            },
        ),
        migrations.CreateModel(
            name='ScriptTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('template_code', models.TextField()),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.AlterModelOptions(
            name='scriptrunner',
            options={'ordering': ['-executed_at', '-created_at'], 'verbose_name': 'Script Runner', 'verbose_name_plural': 'Script Runners'},
        ),
        migrations.AddField(
            model_name='scriptrunner',
            name='created_by',
            field=models.ForeignKey(blank=True, help_text='User who created this script', null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='scriptrunner',
            name='execution_count',
            field=models.IntegerField(default=0, help_text='Number of times this script has been executed'),
        ),
        migrations.AddField(
            model_name='scriptrunner',
            name='execution_status',
            field=models.CharField(choices=[('pending', '⏳ Pending'), ('running', '🔄 Running'), ('completed', '✅ Completed'), ('failed', '❌ Failed'), ('timeout', '⏰ Timeout')], default='pending', help_text='Current execution status', max_length=20),
        ),
        migrations.AddField(
            model_name='scriptrunner',
            name='execution_time',
            field=models.FloatField(blank=True, help_text='Execution time in seconds', null=True),
        ),
        migrations.AddField(
            model_name='scriptrunner',
            name='is_favorite',
            field=models.BooleanField(default=False, help_text='Mark as favorite script'),
        ),
        migrations.AddField(
            model_name='scriptrunner',
            name='timeout_seconds',
            field=models.IntegerField(default=30, help_text='Maximum execution time in seconds'),
        ),
    ]
