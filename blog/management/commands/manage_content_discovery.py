from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q
from blog.models import Post, Tag, Category
from blog.services import ContentDiscoveryService
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Manage content discovery features: featured posts, cache clearing, and analytics'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['clear-cache', 'auto-feature', 'analytics', 'trending-tags'],
            help='Action to perform'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=3,
            help='Number of posts to auto-feature (default: 3)'
        )
        
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to look back for analytics (default: 7)'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'clear-cache':
            self.clear_content_caches()
        elif action == 'auto-feature':
            self.auto_feature_posts(options['limit'])
        elif action == 'analytics':
            self.show_analytics(options['days'])
        elif action == 'trending-tags':
            self.show_trending_tags()

    def clear_content_caches(self):
        """Clear all content discovery related caches"""
        self.stdout.write('Clearing content discovery caches...')
        ContentDiscoveryService.clear_content_caches()
        self.stdout.write(
            self.style.SUCCESS('Successfully cleared content discovery caches')
        )

    def auto_feature_posts(self, limit):
        """Automatically feature top-performing posts"""
        self.stdout.write(f'Auto-featuring top {limit} posts...')
        
        # Get posts from the last 30 days with high engagement
        recent_date = timezone.now() - timedelta(days=30)
        
        top_posts = Post.objects.filter(
            status='published',
            created_at__gte=recent_date
        ).annotate(
            comment_count=Count('comments', filter=Q(comments__is_approved=True)),
            share_count=Count('social_shares'),
            engagement_score=Count('view_count') + Count('comment_count') * 2 + Count('share_count') * 3
        ).order_by('-engagement_score', '-view_count')[:limit]
        
        if not top_posts:
            self.stdout.write(
                self.style.WARNING('No posts found to feature from the last 30 days')
            )
            return
        
        # Unfeature all current featured posts
        Post.objects.filter(is_featured=True).update(is_featured=False)
        
        # Feature the top posts
        featured_count = 0
        for post in top_posts:
            post.is_featured = True
            post.save()
            featured_count += 1
            self.stdout.write(f'Featured: {post.title}')
        
        # Clear cache after updating featured posts
        ContentDiscoveryService.clear_content_caches()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully featured {featured_count} posts')
        )

    def show_analytics(self, days):
        """Show content discovery analytics"""
        self.stdout.write(f'Content Discovery Analytics (Last {days} days)')
        self.stdout.write('=' * 50)
        
        recent_date = timezone.now() - timedelta(days=days)
        
        # Featured posts performance
        featured_posts = Post.objects.filter(
            is_featured=True,
            status='published'
        ).annotate(
            comment_count=Count('comments', filter=Q(comments__is_approved=True)),
            share_count=Count('social_shares')
        )
        
        self.stdout.write('\nFeatured Posts Performance:')
        self.stdout.write('-' * 30)
        for post in featured_posts:
            self.stdout.write(
                f'• {post.title[:50]}...\n'
                f'  Views: {post.view_count} | Comments: {post.comment_count} | Shares: {post.share_count}'
            )
        
        # Popular posts in timeframe
        popular_posts = ContentDiscoveryService.get_popular_posts(
            timeframe='week' if days <= 7 else 'month',
            limit=5
        )
        
        self.stdout.write(f'\nTop 5 Popular Posts (Last {days} days):')
        self.stdout.write('-' * 30)
        for i, post in enumerate(popular_posts, 1):
            self.stdout.write(
                f'{i}. {post.title[:50]}...\n'
                f'   Views: {post.view_count} | Engagement Score: {post.popularity_score}'
            )
        
        # Category performance
        category_stats = Category.objects.annotate(
            post_count=Count('posts', filter=Q(posts__status='published')),
            total_views=Count('posts__view_count', filter=Q(posts__status='published'))
        ).filter(post_count__gt=0).order_by('-total_views')[:5]
        
        self.stdout.write('\nTop 5 Categories by Views:')
        self.stdout.write('-' * 30)
        for category in category_stats:
            self.stdout.write(
                f'• {category.name}: {category.post_count} posts, {category.total_views} total views'
            )
        
        # Tag performance
        trending_tags = ContentDiscoveryService.get_trending_tags(limit=10)
        
        self.stdout.write('\nTrending Tags:')
        self.stdout.write('-' * 30)
        for tag in trending_tags:
            self.stdout.write(
                f'• {tag.name}: {tag.recent_post_count} recent posts, Score: {tag.engagement_score}'
            )

    def show_trending_tags(self):
        """Show detailed trending tags information"""
        self.stdout.write('Trending Tags Analysis')
        self.stdout.write('=' * 30)
        
        trending_tags = ContentDiscoveryService.get_trending_tags(limit=20)
        
        if not trending_tags:
            self.stdout.write(
                self.style.WARNING('No trending tags found')
            )
            return
        
        for i, tag in enumerate(trending_tags, 1):
            total_posts = tag.posts.filter(status='published').count()
            self.stdout.write(
                f'{i:2d}. {tag.name}\n'
                f'    Recent Posts: {tag.recent_post_count}\n'
                f'    Total Posts: {total_posts}\n'
                f'    Engagement Score: {tag.engagement_score}\n'
                f'    Color: {tag.color}\n'
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Found {len(trending_tags)} trending tags')
        )