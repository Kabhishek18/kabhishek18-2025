# Generated manually for multimedia models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0006_add_author_profile_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='MediaItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('media_type', models.CharField(choices=[('image', 'Image'), ('video', 'Video'), ('gallery', 'Image Gallery')], help_text='Type of media content', max_length=10)),
                ('title', models.CharField(blank=True, help_text='Optional title for the media item', max_length=200)),
                ('description', models.TextField(blank=True, help_text='Optional description or caption')),
                ('original_image', models.ImageField(blank=True, help_text='Original uploaded image', null=True, upload_to='blog_images/originals/')),
                ('thumbnail_image', models.ImageField(blank=True, help_text='Thumbnail version', null=True, upload_to='blog_images/thumbnails/')),
                ('medium_image', models.ImageField(blank=True, help_text='Medium size version', null=True, upload_to='blog_images/medium/')),
                ('large_image', models.ImageField(blank=True, help_text='Large size version', null=True, upload_to='blog_images/large/')),
                ('video_url', models.URLField(blank=True, help_text='URL for embedded video (YouTube, Vimeo)')),
                ('video_platform', models.CharField(blank=True, help_text='Video platform (youtube, vimeo)', max_length=20)),
                ('video_id', models.CharField(blank=True, help_text='Platform-specific video ID', max_length=50)),
                ('video_embed_url', models.URLField(blank=True, help_text='Embed URL for the video')),
                ('video_thumbnail', models.URLField(blank=True, help_text='Thumbnail URL for the video')),
                ('gallery_images', models.JSONField(blank=True, default=list, help_text='JSON array of gallery image data')),
                ('alt_text', models.CharField(blank=True, help_text='Alt text for accessibility', max_length=255)),
                ('order', models.PositiveIntegerField(default=0, help_text='Display order within the post')),
                ('is_featured', models.BooleanField(default=False, help_text='Use as featured media for the post')),
                ('file_size', models.PositiveIntegerField(default=0, help_text='File size in bytes')),
                ('width', models.PositiveIntegerField(default=0, help_text='Image/video width in pixels')),
                ('height', models.PositiveIntegerField(default=0, help_text='Image/video height in pixels')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('post', models.ForeignKey(help_text='The blog post this media belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='media_items', to='blog.post')),
            ],
            options={
                'ordering': ['order', 'created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='mediaitem',
            index=models.Index(fields=['post', 'media_type'], name='blog_mediai_post_id_b8e7a5_idx'),
        ),
        migrations.AddIndex(
            model_name='mediaitem',
            index=models.Index(fields=['is_featured'], name='blog_mediai_is_feat_b69323_idx'),
        ),
        migrations.AddIndex(
            model_name='mediaitem',
            index=models.Index(fields=['order'], name='blog_mediai_order_a1b2c3_idx'),
        ),
    ]