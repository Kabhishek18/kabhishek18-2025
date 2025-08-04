from django.db.models import Q, Count, F, Case, When, Value, IntegerField
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
from collections import Counter
import re
from .models import Post, Tag, Category, SocialShare
from django.contrib.auth.models import User


class ContentDiscoveryService:
    """
    Service class for content discovery and recommendation features.
    Handles featured posts, related posts, and popular content algorithms.
    """
    
    @staticmethod
    def get_featured_posts(limit=3):
        """
        Get featured posts for homepage display.
        Returns posts marked as featured, ordered by creation date.
        """
        cache_key = f'featured_posts_{limit}'
        featured_posts = cache.get(cache_key)
        
        if featured_posts is None:
            featured_posts = Post.objects.filter(
                status='published',
                is_featured=True
            ).select_related('author').prefetch_related(
                'categories', 'tags'
            ).order_by('-created_at')[:limit]
            
            # Cache for 30 minutes
            cache.set(cache_key, featured_posts, 1800)
        
        return featured_posts
    
    @staticmethod
    def get_related_posts(post, limit=3):
        """
        Get related posts using tags, categories, and content similarity.
        Uses a weighted scoring system to determine relevance.
        """
        cache_key = f'related_posts_{post.id}_{limit}'
        related_posts = cache.get(cache_key)
        
        if related_posts is None:
            # Get all published posts except the current one
            candidates = Post.objects.filter(
                status='published'
            ).exclude(pk=post.pk).select_related('author').prefetch_related(
                'categories', 'tags'
            )
            
            # Calculate relevance scores
            scored_posts = []
            
            for candidate in candidates:
                score = ContentDiscoveryService._calculate_relevance_score(post, candidate)
                if score > 0:
                    scored_posts.append((candidate, score))
            
            # Sort by score and get top results
            scored_posts.sort(key=lambda x: x[1], reverse=True)
            related_posts = [post_score[0] for post_score in scored_posts[:limit]]
            
            # Cache for 1 hour
            cache.set(cache_key, related_posts, 3600)
        
        return related_posts
    
    @staticmethod
    def _calculate_relevance_score(original_post, candidate_post):
        """
        Calculate relevance score between two posts based on:
        - Shared tags (highest weight)
        - Shared categories (medium weight)
        - Content similarity (lower weight)
        - Recency bonus
        """
        score = 0
        
        # Tag similarity (weight: 3)
        original_tags = set(original_post.tags.values_list('id', flat=True))
        candidate_tags = set(candidate_post.tags.values_list('id', flat=True))
        shared_tags = original_tags.intersection(candidate_tags)
        score += len(shared_tags) * 3
        
        # Category similarity (weight: 2)
        original_categories = set(original_post.categories.values_list('id', flat=True))
        candidate_categories = set(candidate_post.categories.values_list('id', flat=True))
        shared_categories = original_categories.intersection(candidate_categories)
        score += len(shared_categories) * 2
        
        # Content similarity (weight: 1)
        # Simple keyword matching in titles and excerpts
        original_words = ContentDiscoveryService._extract_keywords(
            f"{original_post.title} {original_post.excerpt or ''}"
        )
        candidate_words = ContentDiscoveryService._extract_keywords(
            f"{candidate_post.title} {candidate_post.excerpt or ''}"
        )
        shared_words = original_words.intersection(candidate_words)
        score += len(shared_words) * 1
        
        # Recency bonus (posts from last 30 days get small boost)
        days_old = (timezone.now() - candidate_post.created_at).days
        if days_old <= 30:
            score += 0.5
        
        return score
    
    @staticmethod
    def _extract_keywords(text):
        """
        Extract meaningful keywords from text for content similarity.
        Removes common stop words and short words.
        """
        if not text:
            return set()
        
        # Convert to lowercase and extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Common stop words to exclude
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
            'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his',
            'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy',
            'did', 'she', 'use', 'way', 'will', 'with', 'this', 'that', 'have',
            'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time',
            'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 'many',
            'over', 'such', 'take', 'than', 'them', 'well', 'were'
        }
        
        # Filter out stop words and return set
        return set(word for word in words if word not in stop_words)
    
    @staticmethod
    def get_popular_posts(timeframe='week', limit=5):
        """
        Get popular posts based on views and engagement within a timeframe.
        Timeframe options: 'week', 'month', 'year', 'all'
        """
        cache_key = f'popular_posts_{timeframe}_{limit}'
        popular_posts = cache.get(cache_key)
        
        if popular_posts is None:
            posts_query = Post.objects.filter(status='published')
            
            # Apply timeframe filter
            if timeframe != 'all':
                now = timezone.now()
                if timeframe == 'week':
                    start_date = now - timedelta(days=7)
                elif timeframe == 'month':
                    start_date = now - timedelta(days=30)
                elif timeframe == 'year':
                    start_date = now - timedelta(days=365)
                else:
                    start_date = now - timedelta(days=7)  # Default to week
                
                posts_query = posts_query.filter(created_at__gte=start_date)
            
            # Calculate popularity score based on views, comments, and social shares
            popular_posts = posts_query.annotate(
                comment_count=Count('comments', filter=Q(comments__is_approved=True)),
                share_count=Count('social_shares'),
                popularity_score=F('view_count') + F('comment_count') * 2 + F('share_count') * 3
            ).select_related('author').prefetch_related(
                'categories', 'tags'
            ).order_by('-popularity_score', '-created_at')[:limit]
            
            # Cache for 1 hour
            cache.set(cache_key, popular_posts, 3600)
        
        return popular_posts
    
    @staticmethod
    def update_view_count(post):
        """
        Increment view count for a post.
        Uses F() expression to avoid race conditions.
        """
        Post.objects.filter(pk=post.pk).update(view_count=F('view_count') + 1)
        
        # Clear related caches
        cache_keys_to_clear = [
            f'popular_posts_week_5',
            f'popular_posts_month_5',
            f'popular_posts_year_5',
            f'popular_posts_all_5',
        ]
        cache.delete_many(cache_keys_to_clear)
    
    @staticmethod
    def get_trending_tags(limit=10):
        """
        Get trending tags based on recent post activity and engagement.
        """
        cache_key = f'trending_tags_{limit}'
        trending_tags = cache.get(cache_key)
        
        if trending_tags is None:
            # Get tags from posts created in the last 30 days
            recent_date = timezone.now() - timedelta(days=30)
            
            trending_tags = Tag.objects.filter(
                posts__status='published',
                posts__created_at__gte=recent_date
            ).annotate(
                recent_post_count=Count('posts', filter=Q(posts__created_at__gte=recent_date)),
                total_views=Count('posts__view_count'),
                engagement_score=F('recent_post_count') * 2 + F('total_views')
            ).filter(
                recent_post_count__gt=0
            ).order_by('-engagement_score', 'name')[:limit]
            
            # Cache for 2 hours
            cache.set(cache_key, trending_tags, 7200)
        
        return trending_tags
    
    @staticmethod
    def get_content_recommendations_for_user(user, limit=5):
        """
        Get personalized content recommendations based on user's reading history.
        This is a placeholder for future user behavior tracking.
        """
        # For now, return popular posts as we don't have user behavior tracking yet
        return ContentDiscoveryService.get_popular_posts('month', limit)
    
    @staticmethod
    def clear_content_caches():
        """
        Clear all content discovery related caches.
        Useful when posts are updated or new content is published.
        """
        cache_patterns = [
            'featured_posts_*',
            'related_posts_*',
            'popular_posts_*',
            'trending_tags_*',
        ]
        
        # Note: This is a simplified cache clearing approach
        # In production, you might want to use cache versioning or more sophisticated cache invalidation
        for pattern in cache_patterns:
            # Clear common cache keys
            for i in range(1, 11):  # Clear up to 10 variations
                cache.delete(pattern.replace('*', str(i)))


class SocialShareService:
    """
    Service class for handling social media sharing functionality.
    """
    
    PLATFORM_CONFIGS = {
        'facebook': {
            'name': 'Facebook',
            'url_template': 'https://www.facebook.com/sharer/sharer.php?u={url}',
            'icon': 'fab fa-facebook-f',
            'color': '#1877f2'
        },
        'twitter': {
            'name': 'Twitter',
            'url_template': 'https://twitter.com/intent/tweet?url={url}&text={title}',
            'icon': 'fab fa-twitter',
            'color': '#1da1f2'
        },
        'linkedin': {
            'name': 'LinkedIn',
            'url_template': 'https://www.linkedin.com/sharing/share-offsite/?url={url}',
            'icon': 'fab fa-linkedin-in',
            'color': '#0077b5'
        },
        'reddit': {
            'name': 'Reddit',
            'url_template': 'https://reddit.com/submit?url={url}&title={title}',
            'icon': 'fab fa-reddit-alien',
            'color': '#ff4500'
        },
        'pinterest': {
            'name': 'Pinterest',
            'url_template': 'https://pinterest.com/pin/create/button/?url={url}&description={title}',
            'icon': 'fab fa-pinterest-p',
            'color': '#bd081c'
        },
        'whatsapp': {
            'name': 'WhatsApp',
            'url_template': 'https://wa.me/?text={title} {url}',
            'icon': 'fab fa-whatsapp',
            'color': '#25d366'
        }
    }
    
    @staticmethod
    def generate_share_urls(post, request):
        """
        Generate social sharing URLs for all platforms.
        """
        from django.urls import reverse
        from urllib.parse import quote
        
        # Build absolute URL
        post_url = request.build_absolute_uri(reverse('blog:detail', args=[post.slug]))
        encoded_url = quote(post_url)
        encoded_title = quote(post.title)
        
        share_urls = {}
        
        for platform, config in SocialShareService.PLATFORM_CONFIGS.items():
            share_urls[platform] = {
                'url': config['url_template'].format(
                    url=encoded_url,
                    title=encoded_title
                ),
                'name': config['name'],
                'icon': config['icon'],
                'color': config['color']
            }
        
        return share_urls
    
    @staticmethod
    def track_share(post, platform):
        """
        Track a social media share event.
        """
        if platform not in SocialShareService.PLATFORM_CONFIGS:
            raise ValueError(f"Unsupported platform: {platform}")
        
        social_share, created = SocialShare.objects.get_or_create(
            post=post,
            platform=platform,
            defaults={'share_count': 0}
        )
        
        social_share.increment_share_count()
        
        # Clear popular posts cache as share counts affect popularity
        ContentDiscoveryService.clear_content_caches()
        
        return social_share
    
    @staticmethod
    def get_share_counts(post):
        """
        Get share counts for all platforms for a specific post.
        """
        shares = SocialShare.objects.filter(post=post)
        share_counts = {}
        
        for share in shares:
            share_counts[share.platform] = share.share_count
        
        # Ensure all platforms are represented
        for platform in SocialShareService.PLATFORM_CONFIGS:
            if platform not in share_counts:
                share_counts[platform] = 0
        
        return share_counts
    
    @staticmethod
    def get_total_shares(post):
        """
        Get total share count across all platforms for a post.
        """
        return SocialShare.objects.filter(post=post).aggregate(
            total=Count('share_count')
        )['total'] or 0
    
    @staticmethod
    def get_most_shared_posts(limit=10, timeframe='month'):
        """
        Get posts with the highest share counts within a timeframe.
        """
        posts_query = Post.objects.filter(status='published')
        
        if timeframe != 'all':
            now = timezone.now()
            if timeframe == 'week':
                start_date = now - timedelta(days=7)
            elif timeframe == 'month':
                start_date = now - timedelta(days=30)
            elif timeframe == 'year':
                start_date = now - timedelta(days=365)
            else:
                start_date = now - timedelta(days=30)  # Default to month
            
            posts_query = posts_query.filter(created_at__gte=start_date)
        
        return posts_query.annotate(
            total_shares=Count('social_shares__share_count')
        ).order_by('-total_shares', '-created_at')[:limit]