from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from blog.models import Post, Category, Tag
from django.utils.text import slugify


class Command(BaseCommand):
    help = 'Test the enhanced search and navigation functionality'

    def handle(self, *args, **options):
        self.stdout.write('Testing enhanced search and navigation functionality...')
        
        # Get or create a test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        # Create test categories with hierarchy
        parent_category, created = Category.objects.get_or_create(
            name='Technology',
            defaults={'slug': 'technology'}
        )
        
        child_category, created = Category.objects.get_or_create(
            name='Web Development',
            defaults={'slug': 'web-development', 'parent': parent_category}
        )
        
        # Create test tags
        tags_data = [
            ('Python', '#3776ab'),
            ('Django', '#092e20'),
            ('JavaScript', '#f7df1e'),
            ('React', '#61dafb'),
            ('CSS', '#1572b6'),
        ]
        
        tags = []
        for tag_name, color in tags_data:
            tag, created = Tag.objects.get_or_create(
                name=tag_name,
                defaults={'slug': slugify(tag_name), 'color': color}
            )
            tags.append(tag)
        
        # Create test posts
        posts_data = [
            {
                'title': 'Getting Started with Django Web Development',
                'content': 'Django is a powerful Python web framework that makes it easy to build web applications. In this comprehensive guide, we will explore the fundamentals of Django development.',
                'excerpt': 'Learn the basics of Django web development with Python.',
                'categories': [parent_category, child_category],
                'tags': [tags[0], tags[1]]  # Python, Django
            },
            {
                'title': 'Modern JavaScript and React Best Practices',
                'content': 'JavaScript has evolved significantly over the years. React has become one of the most popular frontend frameworks. This post covers modern JavaScript features and React best practices.',
                'excerpt': 'Explore modern JavaScript features and React development patterns.',
                'categories': [child_category],
                'tags': [tags[2], tags[3]]  # JavaScript, React
            },
            {
                'title': 'CSS Grid and Flexbox Layout Techniques',
                'content': 'CSS Grid and Flexbox are powerful layout systems that have revolutionized web design. Learn how to create responsive layouts using these modern CSS features.',
                'excerpt': 'Master CSS Grid and Flexbox for responsive web layouts.',
                'categories': [child_category],
                'tags': [tags[4]]  # CSS
            },
            {
                'title': 'Full Stack Development with Python and JavaScript',
                'content': 'Combining Python backend development with JavaScript frontend creates powerful full-stack applications. This guide covers the complete development process.',
                'excerpt': 'Build full-stack applications using Python and JavaScript.',
                'categories': [parent_category, child_category],
                'tags': [tags[0], tags[2]]  # Python, JavaScript
            }
        ]
        
        for post_data in posts_data:
            post, created = Post.objects.get_or_create(
                title=post_data['title'],
                defaults={
                    'slug': slugify(post_data['title']),
                    'author': user,
                    'content': post_data['content'],
                    'excerpt': post_data['excerpt'],
                    'status': 'published'
                }
            )
            
            if created:
                post.categories.set(post_data['categories'])
                post.tags.set(post_data['tags'])
                self.stdout.write(f'Created post: {post.title}')
            else:
                self.stdout.write(f'Post already exists: {post.title}')
        
        self.stdout.write(self.style.SUCCESS('Test data created successfully!'))
        
        # Test search functionality
        self.stdout.write('\nTesting search functionality:')
        
        # Test basic search
        search_results = Post.objects.filter(
            status='published',
            title__icontains='Django'
        )
        self.stdout.write(f'Search for "Django": {search_results.count()} results')
        
        # Test tag search
        tag_results = Post.objects.filter(
            status='published',
            tags__name__icontains='Python'
        )
        self.stdout.write(f'Tag search for "Python": {tag_results.count()} results')
        
        # Test category hierarchy
        category_results = Post.objects.filter(
            status='published',
            categories=parent_category
        )
        self.stdout.write(f'Category "Technology": {category_results.count()} results')
        
        subcategory_results = Post.objects.filter(
            status='published',
            categories=child_category
        )
        self.stdout.write(f'Subcategory "Web Development": {subcategory_results.count()} results')
        
        self.stdout.write(self.style.SUCCESS('\nAll tests completed successfully!'))