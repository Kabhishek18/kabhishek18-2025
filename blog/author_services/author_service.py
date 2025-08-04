"""
Author service for managing author profiles and related functionality.
"""
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.core.exceptions import ObjectDoesNotExist
from ..models import AuthorProfile, Post
import logging

logger = logging.getLogger(__name__)


class AuthorService:
    """Service class for author-related operations."""
    
    @staticmethod
    def get_author_profile(user):
        """
        Get or create an AuthorProfile for the given user.
        
        Args:
            user: User instance
            
        Returns:
            AuthorProfile instance
        """
        try:
            return user.author_profile
        except ObjectDoesNotExist:
            # Create profile if it doesn't exist
            profile = AuthorProfile.objects.create(user=user)
            logger.info(f"Created AuthorProfile for user: {user.username}")
            return profile
    
    @staticmethod
    def get_author_posts(user, status='published', limit=None):
        """
        Get posts by a specific author.
        
        Args:
            user: User instance
            status: Post status filter (default: 'published')
            limit: Maximum number of posts to return
            
        Returns:
            QuerySet of Post objects
        """
        posts = user.blog_posts.filter(status=status).order_by('-created_at')
        
        if limit:
            posts = posts[:limit]
            
        return posts
    
    @staticmethod
    def get_author_social_links(user):
        """
        Get social media links for an author.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary of social media links
        """
        try:
            profile = user.author_profile
            return profile.get_social_links()
        except ObjectDoesNotExist:
            return {}
    
    @staticmethod
    def get_all_active_authors():
        """
        Get all active authors who have published posts.
        
        Returns:
            QuerySet of User objects with author profiles
        """
        return User.objects.filter(
            author_profile__is_active=True,
            blog_posts__status='published'
        ).annotate(
            post_count=Count('blog_posts', filter=Q(blog_posts__status='published'))
        ).filter(post_count__gt=0).distinct().order_by('first_name', 'last_name', 'username')
    
    @staticmethod
    def get_guest_authors():
        """
        Get all guest authors.
        
        Returns:
            QuerySet of AuthorProfile objects for guest authors
        """
        return AuthorProfile.objects.filter(
            is_guest_author=True,
            is_active=True
        ).select_related('user').order_by('user__first_name', 'user__last_name', 'user__username')
    
    @staticmethod
    def create_guest_author(username, email, first_name='', last_name='', bio='', **profile_data):
        """
        Create a new guest author with limited permissions.
        
        Args:
            username: Username for the guest author
            email: Email address
            first_name: First name (optional)
            last_name: Last name (optional)
            bio: Author biography
            **profile_data: Additional profile data
            
        Returns:
            Tuple of (User, AuthorProfile) instances
        """
        # Create user account with limited permissions
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            is_staff=False,  # Guest authors are not staff
            is_superuser=False
        )
        
        # Create or update author profile
        profile, created = AuthorProfile.objects.get_or_create(
            user=user,
            defaults={
                'bio': bio,
                'is_guest_author': True,
                'guest_author_email': email,
                **profile_data
            }
        )
        
        if not created:
            # Update existing profile
            profile.bio = bio
            profile.is_guest_author = True
            profile.guest_author_email = email
            for key, value in profile_data.items():
                setattr(profile, key, value)
            profile.save()
        
        logger.info(f"Created guest author: {username} ({email})")
        return user, profile
    
    @staticmethod
    def update_author_profile(user, **profile_data):
        """
        Update an author's profile information.
        
        Args:
            user: User instance
            **profile_data: Profile data to update
            
        Returns:
            Updated AuthorProfile instance
        """
        profile = AuthorService.get_author_profile(user)
        
        for key, value in profile_data.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.save()
        logger.info(f"Updated AuthorProfile for user: {user.username}")
        return profile
    
    @staticmethod
    def deactivate_author(user):
        """
        Deactivate an author profile.
        
        Args:
            user: User instance
        """
        try:
            profile = user.author_profile
            profile.is_active = False
            profile.save()
            logger.info(f"Deactivated AuthorProfile for user: {user.username}")
        except ObjectDoesNotExist:
            logger.warning(f"No AuthorProfile found for user: {user.username}")
    
    @staticmethod
    def get_author_stats(user):
        """
        Get statistics for an author.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary with author statistics
        """
        posts = user.blog_posts.filter(status='published')
        
        stats = {
            'total_posts': posts.count(),
            'total_views': sum(post.view_count for post in posts),
            'total_comments': sum(post.comments.filter(is_approved=True).count() for post in posts),
            'most_viewed_post': posts.order_by('-view_count').first(),
            'latest_post': posts.order_by('-created_at').first(),
        }
        
        return stats
    
    @staticmethod
    def search_authors(query):
        """
        Search for authors by name or username.
        
        Args:
            query: Search query string
            
        Returns:
            QuerySet of User objects matching the search
        """
        return User.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query) |
            Q(author_profile__bio__icontains=query),
            author_profile__is_active=True,
            blog_posts__status='published'
        ).annotate(
            post_count=Count('blog_posts', filter=Q(blog_posts__status='published'))
        ).filter(post_count__gt=0).distinct().order_by('first_name', 'last_name', 'username')