from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from blog.models import Post, MediaItem

class Command(BaseCommand):
    help = 'Create sample media items for testing'

    def handle(self, *args, **options):
        # Get or create a sample post
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR('No users found. Please create a user first.'))
            return

        post, created = Post.objects.get_or_create(
            title='Sample Post with Media',
            defaults={
                'author': user,
                'content': '''
                This is a sample blog post that demonstrates how to use MediaItem.
                
                You can embed media using shortcodes:
                
                [image id="1"]
                
                [video id="2"]
                
                [gallery id="3"]
                
                Or just let them display automatically in the media gallery at the end.
                ''',
                'excerpt': 'A sample post showing MediaItem usage',
                'status': 'published'
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created sample post: {post.title}'))
        else:
            self.stdout.write(self.style.WARNING(f'Post already exists: {post.title}'))

        # Create sample media items
        sample_media = [
            {
                'media_type': 'image',
                'title': 'Sample Image',
                'description': 'This is a sample image for demonstration',
                'alt_text': 'Sample image alt text',
                'is_featured': True
            },
            {
                'media_type': 'video',
                'title': 'Sample Video',
                'description': 'This is a sample embedded video',
                'video_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'video_platform': 'youtube',
                'video_id': 'dQw4w9WgXcQ',
                'video_embed_url': 'https://www.youtube.com/embed/dQw4w9WgXcQ',
                'video_thumbnail': 'https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg'
            },
            {
                'media_type': 'gallery',
                'title': 'Sample Gallery',
                'description': 'This is a sample image gallery',
                'gallery_images': [
                    {
                        'title': 'Gallery Image 1',
                        'alt_text': 'First gallery image',
                        'processed': {
                            'thumbnail': 'https://via.placeholder.com/150x150',
                            'medium': 'https://via.placeholder.com/400x300',
                            'large': 'https://via.placeholder.com/800x600',
                            'original': 'https://via.placeholder.com/1200x900'
                        }
                    },
                    {
                        'title': 'Gallery Image 2',
                        'alt_text': 'Second gallery image',
                        'processed': {
                            'thumbnail': 'https://via.placeholder.com/150x150/ff0000',
                            'medium': 'https://via.placeholder.com/400x300/ff0000',
                            'large': 'https://via.placeholder.com/800x600/ff0000',
                            'original': 'https://via.placeholder.com/1200x900/ff0000'
                        }
                    }
                ]
            }
        ]

        for i, media_data in enumerate(sample_media, 1):
            media_item, created = MediaItem.objects.get_or_create(
                post=post,
                media_type=media_data['media_type'],
                title=media_data['title'],
                defaults={
                    **media_data,
                    'order': i
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created {media_data["media_type"]}: {media_data["title"]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'{media_data["media_type"]} already exists: {media_data["title"]}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSample data created! Visit your blog post to see the media items in action.\n'
                f'Post URL: /blog/{post.slug}/'
            )
        )