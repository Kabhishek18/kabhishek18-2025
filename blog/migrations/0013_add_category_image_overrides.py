# Generated migration for adding category_image_overrides field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0012_add_hashtag_image_config_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='linkedinconfig',
            name='category_image_overrides',
            field=models.JSONField(blank=True, default=dict, help_text='Category-specific image posting overrides (JSON format)'),
        ),
    ]