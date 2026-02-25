from django.core.management.base import BaseCommand
from blog.models import Post, Category, Tag
from django.contrib.auth.models import User
from django.utils.text import slugify
import re

class Command(BaseCommand):
    help = 'Improve site structure for better SEO and user experience'

    def add_arguments(self, parser):
        parser.add_argument('--categories', action='store_true', help='Organize content into categories')
        parser.add_argument('--tags', action='store_true', help='Add relevant tags to posts')
        parser.add_argument('--internal-links', action='store_true', help='Add internal links between posts')
        parser.add_argument('--meta', action='store_true', help='Optimize meta descriptions and titles')

    def handle(self, *args, **options):
        if options.get('categories'):
            self.organize_categories()
        
        if options.get('tags'):
            self.add_relevant_tags()
        
        if options.get('internal_links'):
            self.add_internal_links()
        
        if options.get('meta'):
            self.optimize_meta_data()
        
        self.stdout.write(
            self.style.SUCCESS('Site structure improvements completed successfully')
        )

    def organize_categories(self):
        """Organize posts into relevant categories"""
        self.stdout.write("Organizing content into categories...")
        
        # Create comprehensive category structure
        categories = [
            {'name': 'Web Development', 'slug': 'web-development'},
            {'name': 'Django Tutorials', 'slug': 'django-tutorials'},
            {'name': 'Python Programming', 'slug': 'python-programming'},
            {'name': 'Database Management', 'slug': 'database-management'},
            {'name': 'Security', 'slug': 'security'},
            {'name': 'Performance Optimization', 'slug': 'performance-optimization'},
            {'name': 'JavaScript', 'slug': 'javascript'},
            {'name': 'Best Practices', 'slug': 'best-practices'},
            {'name': 'Case Studies', 'slug': 'case-studies'},
            {'name': 'Blockchain & Fintech', 'slug': 'blockchain-fintech'}
        ]
        
        created_categories = {}
        for cat_data in categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'slug': cat_data['slug']}
            )
            created_categories[cat_data['name']] = category
            if created:
                self.stdout.write(f'Created category: {category.name}')
        
        # Categorize existing posts
        posts = Post.objects.filter(status='published')
        for post in posts:
            categories_to_add = self.determine_post_categories(post, created_categories)
            if categories_to_add:
                post.categories.set(categories_to_add)
                self.stdout.write(f'Categorized post: {post.title}')

    def determine_post_categories(self, post, categories):
        """Determine appropriate categories for a post based on content"""
        content_lower = (post.title + ' ' + post.content).lower()
        post_categories = []
        
        # Django-related content
        if any(keyword in content_lower for keyword in ['django', 'rest framework', 'orm']):
            post_categories.append(categories['Django Tutorials'])
            post_categories.append(categories['Web Development'])
        
        # Python-related content
        if any(keyword in content_lower for keyword in ['python', 'pip', 'virtualenv']):
            post_categories.append(categories['Python Programming'])
        
        # Database-related content
        if any(keyword in content_lower for keyword in ['database', 'sql', 'postgresql', 'mysql', 'query']):
            post_categories.append(categories['Database Management'])
        
        # Security-related content
        if any(keyword in content_lower for keyword in ['security', 'authentication', 'csrf', 'xss', 'encryption']):
            post_categories.append(categories['Security'])
        
        # Performance-related content
        if any(keyword in content_lower for keyword in ['performance', 'optimization', 'caching', 'scalability']):
            post_categories.append(categories['Performance Optimization'])
        
        # JavaScript-related content
        if any(keyword in content_lower for keyword in ['javascript', 'es6', 'async', 'promise']):
            post_categories.append(categories['JavaScript'])
        
        # Blockchain/Fintech content
        if any(keyword in content_lower for keyword in ['blockchain', 'tokenization', 'rwa', 'fintech']):
            post_categories.append(categories['Blockchain & Fintech'])
        
        # Case studies
        if any(keyword in content_lower for keyword in ['case study', 'lessons learned', 'architecture']):
            post_categories.append(categories['Case Studies'])
        
        # Best practices
        if any(keyword in content_lower for keyword in ['best practices', 'guidelines', 'recommendations']):
            post_categories.append(categories['Best Practices'])
        
        # Default to Web Development if no specific category found
        if not post_categories:
            post_categories.append(categories['Web Development'])
        
        return post_categories

    def add_relevant_tags(self):
        """Add relevant tags to posts"""
        self.stdout.write("Adding relevant tags to posts...")
        
        # Create comprehensive tag set
        tag_data = [
            {'name': 'Django', 'color': '#092e20'},
            {'name': 'Python', 'color': '#3776ab'},
            {'name': 'JavaScript', 'color': '#f7df1e'},
            {'name': 'Database', 'color': '#336791'},
            {'name': 'Security', 'color': '#dc3545'},
            {'name': 'Performance', 'color': '#28a745'},
            {'name': 'REST API', 'color': '#17a2b8'},
            {'name': 'Web Development', 'color': '#6f42c1'},
            {'name': 'Best Practices', 'color': '#fd7e14'},
            {'name': 'Tutorial', 'color': '#20c997'},
            {'name': 'Guide', 'color': '#6610f2'},
            {'name': 'Optimization', 'color': '#e83e8c'},
            {'name': 'Authentication', 'color': '#dc3545'},
            {'name': 'Caching', 'color': '#28a745'},
            {'name': 'Scalability', 'color': '#17a2b8'},
            {'name': 'PostgreSQL', 'color': '#336791'},
            {'name': 'MySQL', 'color': '#4479a1'},
            {'name': 'Blockchain', 'color': '#f7931a'},
            {'name': 'Fintech', 'color': '#00d4aa'},
            {'name': 'Case Study', 'color': '#6c757d'}
        ]
        
        created_tags = {}
        for tag_info in tag_data:
            tag, created = Tag.objects.get_or_create(
                name=tag_info['name'],
                defaults={
                    'slug': slugify(tag_info['name']),
                    'color': tag_info['color']
                }
            )
            created_tags[tag_info['name']] = tag
            if created:
                self.stdout.write(f'Created tag: {tag.name}')
        
        # Add tags to posts
        posts = Post.objects.filter(status='published')
        for post in posts:
            relevant_tags = self.determine_post_tags(post, created_tags)
            if relevant_tags:
                post.tags.set(relevant_tags)
                self.stdout.write(f'Tagged post: {post.title}')

    def determine_post_tags(self, post, tags):
        """Determine relevant tags for a post"""
        content_lower = (post.title + ' ' + post.content).lower()
        post_tags = []
        
        # Technology tags
        if 'django' in content_lower:
            post_tags.append(tags['Django'])
        if 'python' in content_lower:
            post_tags.append(tags['Python'])
        if 'javascript' in content_lower:
            post_tags.append(tags['JavaScript'])
        if any(db in content_lower for db in ['database', 'sql', 'postgresql', 'mysql']):
            post_tags.append(tags['Database'])
        if 'postgresql' in content_lower:
            post_tags.append(tags['PostgreSQL'])
        if 'mysql' in content_lower:
            post_tags.append(tags['MySQL'])
        
        # Concept tags
        if any(sec in content_lower for sec in ['security', 'authentication', 'authorization']):
            post_tags.append(tags['Security'])
        if 'authentication' in content_lower:
            post_tags.append(tags['Authentication'])
        if any(perf in content_lower for perf in ['performance', 'optimization']):
            post_tags.append(tags['Performance'])
        if 'optimization' in content_lower:
            post_tags.append(tags['Optimization'])
        if 'caching' in content_lower:
            post_tags.append(tags['Caching'])
        if 'scalability' in content_lower:
            post_tags.append(tags['Scalability'])
        if any(api in content_lower for api in ['rest api', 'api', 'rest framework']):
            post_tags.append(tags['REST API'])
        
        # Content type tags
        if any(tutorial in content_lower for tutorial in ['tutorial', 'guide', 'how to']):
            post_tags.append(tags['Tutorial'])
        if 'guide' in content_lower:
            post_tags.append(tags['Guide'])
        if 'best practices' in content_lower:
            post_tags.append(tags['Best Practices'])
        if 'case study' in content_lower:
            post_tags.append(tags['Case Study'])
        
        # Industry tags
        if any(blockchain in content_lower for blockchain in ['blockchain', 'tokenization', 'rwa']):
            post_tags.append(tags['Blockchain'])
        if 'fintech' in content_lower:
            post_tags.append(tags['Fintech'])
        
        # General web development tag
        post_tags.append(tags['Web Development'])
        
        return post_tags

    def add_internal_links(self):
        """Add internal links between related posts"""
        self.stdout.write("Adding internal links between posts...")
        
        posts = Post.objects.filter(status='published')
        updated_count = 0
        
        for post in posts:
            # Find related posts
            related_posts = self.find_related_posts(post)
            
            if related_posts and not self.has_sufficient_internal_links(post):
                # Add related posts section
                related_section = self.create_related_posts_section(related_posts)
                post.content += related_section
                post.save()
                updated_count += 1
                self.stdout.write(f'Added internal links to: {post.title}')
        
        self.stdout.write(f'Added internal links to {updated_count} posts')

    def find_related_posts(self, post):
        """Find posts related to the current post"""
        # Find posts with shared categories
        related_by_category = Post.objects.filter(
            categories__in=post.categories.all(),
            status='published'
        ).exclude(id=post.id).distinct()[:3]
        
        # Find posts with shared tags
        related_by_tags = Post.objects.filter(
            tags__in=post.tags.all(),
            status='published'
        ).exclude(id=post.id).distinct()[:3]
        
        # Combine and deduplicate
        related_posts = list(related_by_category) + list(related_by_tags)
        seen_ids = set()
        unique_related = []
        
        for related_post in related_posts:
            if related_post.id not in seen_ids:
                unique_related.append(related_post)
                seen_ids.add(related_post.id)
                if len(unique_related) >= 3:
                    break
        
        return unique_related

    def has_sufficient_internal_links(self, post):
        """Check if post already has sufficient internal links"""
        internal_link_count = post.content.count('/blog/')
        return internal_link_count >= 2

    def create_related_posts_section(self, related_posts):
        """Create HTML section for related posts"""
        section = "\n\n<h2>Related Articles</h2>\n"
        section += "<p>Explore these related topics to deepen your understanding:</p>\n<ul>\n"
        
        for related_post in related_posts:
            section += f'<li><a href="/blog/{related_post.slug}/">{related_post.title}</a></li>\n'
        
        section += "</ul>\n"
        return section

    def optimize_meta_data(self):
        """Optimize meta descriptions and titles"""
        self.stdout.write("Optimizing meta descriptions and titles...")
        
        posts = Post.objects.filter(status='published')
        updated_count = 0
        
        for post in posts:
            updated = False
            
            # Optimize meta description (excerpt)
            if not post.excerpt or len(post.excerpt) < 120:
                post.excerpt = self.generate_meta_description(post)
                updated = True
            
            # Ensure title is SEO-friendly
            if len(post.title) > 60:
                # Title is too long for SEO
                self.stdout.write(f'Warning: Title too long for SEO: {post.title}')
            
            if updated:
                post.save()
                updated_count += 1
                self.stdout.write(f'Optimized meta data for: {post.title}')
        
        self.stdout.write(f'Optimized meta data for {updated_count} posts')

    def generate_meta_description(self, post):
        """Generate SEO-friendly meta description"""
        # Extract meaningful content from the post
        content_text = re.sub(r'<[^>]+>', '', post.content)
        
        # Get first few sentences
        sentences = content_text.split('.')[:3]
        description = '. '.join(sentences).strip()
        
        # Ensure proper length
        if len(description) > 155:
            description = description[:152] + "..."
        elif len(description) < 120:
            # Add call-to-action or additional context
            description += f" Learn more about {post.title.lower()} with practical examples and expert insights."
        
        return description