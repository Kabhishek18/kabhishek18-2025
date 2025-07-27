"""
Social Share Service for Blog Posts

This service provides functionality for social media sharing including
URL generation, share tracking, and analytics.
"""

from django.urls import reverse
from urllib.parse import urlencode, quote_plus
from typing import Dict, Optional
from ..models import Post, SocialShare


class SocialShareService:
    """Service class for social media sharing functionality"""
    
    # Social media platform configurations
    PLATFORMS = {
        'facebook': {
            'name': 'Facebook',
            'icon': 'fab fa-facebook-f',
            'color': '#1877f2',
            'url_template': 'https://www.facebook.com/sharer/sharer.php?u={url}'
        },
        'twitter': {
            'name': 'Twitter',
            'icon': 'fab fa-twitter',
            'color': '#1da1f2',
            'url_template': 'https://twitter.com/intent/tweet?text={title}&url={url}'
        },
        'linkedin': {
            'name': 'LinkedIn',
            'icon': 'fab fa-linkedin-in',
            'color': '#0077b5',
            'url_template': 'https://www.linkedin.com/sharing/share-offsite/?url={url}'
        },
        'reddit': {
            'name': 'Reddit',
            'icon': 'fab fa-reddit-alien',
            'color': '#ff4500',
            'url_template': 'https://reddit.com/submit?url={url}&title={title}'
        },
        'pinterest': {
            'name': 'Pinterest',
            'icon': 'fab fa-pinterest-p',
            'color': '#bd081c',
            'url_template': 'https://pinterest.com/pin/create/button/?url={url}&description={title}'
        },
        'whatsapp': {
            'name': 'WhatsApp',
            'icon': 'fab fa-whatsapp',
            'color': '#25d366',
            'url_template': 'https://wa.me/?text={title} {url}'
        }
    }
    
    @classmethod
    def generate_share_urls(cls, post: Post, request) -> Dict[str, Dict]:
        """
        Generate social media share URLs for a blog post.
        
        Args:
            post: Blog post to generate share URLs for
            request: Django request object for building absolute URLs
            
        Returns:
            Dictionary mapping platform names to share data
        """
        # Build absolute URL for the post
        post_url = request.build_absolute_uri(
            reverse('blog:detail', kwargs={'slug': post.slug})
        )
        
        # Prepare title and description
        title = post.title
        description = post.excerpt or post.content[:160]
        
        share_urls = {}
        
        for platform_key, platform_config in cls.PLATFORMS.items():
            # Generate platform-specific share URL
            if platform_key == 'twitter':
                share_url = platform_config['url_template'].format(
                    title=quote_plus(f"{title} - Digital Codex"),
                    url=quote_plus(post_url)
                )
            elif platform_key == 'whatsapp':
                share_url = platform_config['url_template'].format(
                    title=quote_plus(title),
                    url=quote_plus(post_url)
                )
            else:
                share_url = platform_config['url_template'].format(
                    title=quote_plus(title),
                    url=quote_plus(post_url),
                    description=quote_plus(description)
                )
            
            share_urls[platform_key] = {
                'name': platform_config['name'],
                'url': share_url,
                'icon': platform_config['icon'],
                'color': platform_config['color']
            }
        
        return share_urls
    
    @classmethod
    def track_share(cls, post: Post, platform: str) -> SocialShare:
        """
        Track a social media share event.
        
        Args:
            post: Blog post that was shared
            platform: Social media platform name
            
        Returns:
            SocialShare object
            
        Raises:
            ValueError: If platform is not supported
        """
        if platform not in cls.PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform}")
        
        # Get or create social share record
        social_share, created = SocialShare.objects.get_or_create(
            post=post,
            platform=platform,
            defaults={'share_count': 0}
        )
        
        # Increment share count
        social_share.increment_share_count()
        
        return social_share
    
    @classmethod
    def get_share_counts(cls, post: Post) -> Dict[str, int]:
        """
        Get share counts for all platforms for a post.
        
        Args:
            post: Blog post to get share counts for
            
        Returns:
            Dictionary mapping platform names to share counts
        """
        share_counts = {}
        
        # Get all social shares for this post
        social_shares = SocialShare.objects.filter(post=post)
        
        # Initialize all platforms with 0
        for platform_key in cls.PLATFORMS.keys():
            share_counts[platform_key] = 0
        
        # Update with actual counts
        for share in social_shares:
            share_counts[share.platform] = share.share_count
        
        return share_counts
    
    @classmethod
    def get_total_shares(cls, post: Post) -> int:
        """
        Get total share count across all platforms for a post.
        
        Args:
            post: Blog post to get total shares for
            
        Returns:
            Total number of shares
        """
        return sum(cls.get_share_counts(post).values())
    
    @classmethod
    def get_popular_shared_posts(cls, limit: int = 10) -> list:
        """
        Get posts with the highest share counts.
        
        Args:
            limit: Maximum number of posts to return
            
        Returns:
            List of Post objects ordered by total shares
        """
        from django.db.models import Sum
        
        return list(Post.objects.filter(
            status='published'
        ).annotate(
            total_shares=Sum('social_shares__share_count')
        ).filter(
            total_shares__gt=0
        ).order_by('-total_shares')[:limit])
    
    @classmethod
    def get_platform_analytics(cls, post: Optional[Post] = None) -> Dict:
        """
        Get analytics data for social sharing.
        
        Args:
            post: Optional specific post to get analytics for
            
        Returns:
            Dictionary with analytics data
        """
        if post:
            # Analytics for specific post
            shares = SocialShare.objects.filter(post=post)
        else:
            # Analytics for all posts
            shares = SocialShare.objects.all()
        
        analytics = {
            'total_shares': sum(share.share_count for share in shares),
            'platform_breakdown': {},
            'top_platforms': []
        }
        
        # Calculate platform breakdown
        for platform_key, platform_config in cls.PLATFORMS.items():
            platform_shares = shares.filter(platform=platform_key)
            total_count = sum(share.share_count for share in platform_shares)
            
            analytics['platform_breakdown'][platform_key] = {
                'name': platform_config['name'],
                'count': total_count,
                'percentage': (total_count / analytics['total_shares'] * 100) if analytics['total_shares'] > 0 else 0
            }
        
        # Get top platforms
        analytics['top_platforms'] = sorted(
            analytics['platform_breakdown'].items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:5]
        
        return analytics