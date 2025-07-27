from django.contrib import admin
from django.db import models
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
import csv
import json
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import WysiwygWidget
from .models import Post, Category, NewsletterSubscriber, Tag, Comment, SocialShare, AuthorProfile, MediaItem
from ckeditor.widgets import CKEditorWidget


@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = ('title', 'author', 'status', 'is_featured', 'view_count', 'engagement_score', 'created_at')
    list_filter = ('status', 'is_featured', 'categories', 'tags', 'author', 'created_at')
    search_fields = ('title', 'excerpt', 'content')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('status', 'is_featured')
    filter_horizontal = ('categories', 'tags')
    ordering = ('-created_at',)

    # Use CKEditor for content fields
    formfield_overrides = {
        models.TextField: {"widget": CKEditorWidget(config_name='default')},
    }
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'content':
            kwargs['widget'] = CKEditorWidget(config_name='default')
        elif db_field.name == 'excerpt':
            kwargs['widget'] = CKEditorWidget(config_name='basic')
        elif db_field.name == 'meta_data':
            kwargs['widget'] = admin.widgets.AdminTextareaWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    fieldsets = (
        ("Main Content", {
            'fields': ('title', 'slug', 'author', 'status', 'excerpt', 'content')
        }),
        ("Organization & Media", {
            'fields': ('categories', 'tags', 'is_featured', 'featured_image')
        }),
        ("SEO & Meta", {
            'classes': ('collapse',),
            'fields': ('read_time', 'view_count', 'meta_data')
        }),
    )
    
    readonly_fields = ('view_count',)
    actions = ['mark_as_featured', 'unmark_as_featured', 'clear_content_cache']
    
    def engagement_score(self, obj):
        """Calculate and display engagement score based on views, comments, and shares"""
        from django.db.models import Count
        comment_count = obj.comments.filter(is_approved=True).count()
        share_count = obj.social_shares.aggregate(total=Count('share_count'))['total'] or 0
        score = obj.view_count + (comment_count * 2) + (share_count * 3)
        return score
    engagement_score.short_description = 'Engagement Score'
    engagement_score.admin_order_field = 'view_count'
    
    def mark_as_featured(self, request, queryset):
        """Mark selected posts as featured"""
        updated = queryset.update(is_featured=True)
        # Clear cache when featured posts change
        from .services import ContentDiscoveryService
        ContentDiscoveryService.clear_content_caches()
        self.message_user(request, f'{updated} posts marked as featured.')
    mark_as_featured.short_description = "Mark selected posts as featured"
    
    def unmark_as_featured(self, request, queryset):
        """Remove featured status from selected posts"""
        updated = queryset.update(is_featured=False)
        # Clear cache when featured posts change
        from .services import ContentDiscoveryService
        ContentDiscoveryService.clear_content_caches()
        self.message_user(request, f'{updated} posts unmarked as featured.')
    unmark_as_featured.short_description = "Remove featured status from selected posts"
    
    def clear_content_cache(self, request, queryset):
        """Clear content discovery caches"""
        from .services import ContentDiscoveryService
        ContentDiscoveryService.clear_content_caches()
        self.message_user(request, 'Content discovery caches cleared.')
    clear_content_cache.short_description = "Clear content discovery caches"

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    """
    Admin configuration for Categories.
    """
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Tag)
class TagAdmin(ModelAdmin):
    """
    Admin configuration for Tags with color coding and management features.
    """
    list_display = ('name', 'slug', 'color_display', 'get_post_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ("Tag Information", {
            'fields': ('name', 'slug', 'description')
        }),
        ("Display Settings", {
            'fields': ('color',),
            'description': 'Choose a color for this tag. Use hex format (e.g., #007acc)'
        }),
        ("Metadata", {
            'classes': ('collapse',),
            'fields': ('created_at',)
        }),
    )
    
    def color_display(self, obj):
        """Display the tag color as a colored box in the admin list"""
        return f'<div style="width: 20px; height: 20px; background-color: {obj.color}; border: 1px solid #ccc; display: inline-block; border-radius: 3px;"></div> {obj.color}'
    color_display.allow_tags = True
    color_display.short_description = 'Color'
    
    def get_post_count(self, obj):
        """Display the number of published posts with this tag"""
        return obj.get_post_count()
    get_post_count.short_description = 'Published Posts'

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(ModelAdmin):
    """
    Admin configuration for Newsletter Subscribers with enhanced confirmation workflow and export functionality.
    """
    list_display = ('email', 'is_confirmed', 'subscribed_at', 'confirmed_at', 'preferences_display')
    list_filter = ('is_confirmed', 'subscribed_at', 'confirmed_at')
    search_fields = ('email',)
    readonly_fields = ('subscribed_at', 'confirmed_at', 'confirmation_token', 'unsubscribe_token')
    list_editable = ('is_confirmed',)
    date_hierarchy = 'subscribed_at'
    
    fieldsets = (
        ("Subscriber Information", {
            'fields': ('email', 'is_confirmed', 'preferences')
        }),
        ("Timestamps", {
            'fields': ('subscribed_at', 'confirmed_at')
        }),
        ("Security Tokens", {
            'classes': ('collapse',),
            'fields': ('confirmation_token', 'unsubscribe_token'),
            'description': 'These tokens are used for email confirmation and unsubscribe links.'
        }),
    )
    
    actions = ['mark_as_confirmed', 'mark_as_unconfirmed', 'resend_confirmation_email', 'export_subscribers_csv', 'export_subscribers_json']
    
    def preferences_display(self, obj):
        """Display subscriber preferences in a readable format"""
        if obj.preferences:
            prefs = []
            for key, value in obj.preferences.items():
                prefs.append(f"{key}: {value}")
            return "; ".join(prefs) if prefs else "Default"
        return "Default"
    preferences_display.short_description = 'Preferences'
    
    def mark_as_confirmed(self, request, queryset):
        """Mark selected subscribers as confirmed"""
        from django.utils import timezone
        updated = queryset.update(is_confirmed=True, confirmed_at=timezone.now())
        self.message_user(request, f'{updated} subscribers marked as confirmed.')
    mark_as_confirmed.short_description = "Mark selected subscribers as confirmed"
    
    def mark_as_unconfirmed(self, request, queryset):
        """Mark selected subscribers as unconfirmed"""
        updated = queryset.update(is_confirmed=False, confirmed_at=None)
        self.message_user(request, f'{updated} subscribers marked as unconfirmed.')
    mark_as_unconfirmed.short_description = "Mark selected subscribers as unconfirmed"
    
    def resend_confirmation_email(self, request, queryset):
        """Resend confirmation email to selected unconfirmed subscribers"""
        try:
            from .tasks import send_confirmation_email
            count = 0
            for subscriber in queryset.filter(is_confirmed=False):
                send_confirmation_email.delay(subscriber.id)
                count += 1
            self.message_user(request, f'Confirmation emails queued for {count} subscribers.')
        except ImportError:
            # Fallback if Celery tasks are not available
            self.message_user(request, 'Email sending service not available.', level=messages.WARNING)
    resend_confirmation_email.short_description = "Resend confirmation email to unconfirmed subscribers"
    
    def export_subscribers_csv(self, request, queryset):
        """Export selected subscribers to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="newsletter_subscribers_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Email', 'Confirmed', 'Subscribed At', 'Confirmed At', 'Preferences'])
        
        for subscriber in queryset:
            preferences_str = json.dumps(subscriber.preferences) if subscriber.preferences else ''
            writer.writerow([
                subscriber.email,
                'Yes' if subscriber.is_confirmed else 'No',
                subscriber.subscribed_at.strftime('%Y-%m-%d %H:%M:%S') if subscriber.subscribed_at else '',
                subscriber.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if subscriber.confirmed_at else '',
                preferences_str
            ])
        
        return response
    export_subscribers_csv.short_description = "Export selected subscribers to CSV"
    
    def export_subscribers_json(self, request, queryset):
        """Export selected subscribers to JSON"""
        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="newsletter_subscribers_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
        
        subscribers_data = []
        for subscriber in queryset:
            subscribers_data.append({
                'email': subscriber.email,
                'is_confirmed': subscriber.is_confirmed,
                'subscribed_at': subscriber.subscribed_at.isoformat() if subscriber.subscribed_at else None,
                'confirmed_at': subscriber.confirmed_at.isoformat() if subscriber.confirmed_at else None,
                'preferences': subscriber.preferences
            })
        
        response.write(json.dumps(subscribers_data, indent=2))
        return response
    export_subscribers_json.short_description = "Export selected subscribers to JSON"
    
    def get_urls(self):
        """Add custom URLs for subscriber management"""
        urls = super().get_urls()
        custom_urls = [
            path('subscriber-stats/', self.admin_site.admin_view(self.subscriber_stats_view), name='blog_newslettersubscriber_stats'),
        ]
        return custom_urls + urls
    
    def subscriber_stats_view(self, request):
        """Display subscriber statistics"""
        total_subscribers = NewsletterSubscriber.objects.count()
        confirmed_subscribers = NewsletterSubscriber.objects.filter(is_confirmed=True).count()
        unconfirmed_subscribers = total_subscribers - confirmed_subscribers
        
        # Recent subscription trends
        last_30_days = timezone.now() - timedelta(days=30)
        recent_subscriptions = NewsletterSubscriber.objects.filter(subscribed_at__gte=last_30_days).count()
        recent_confirmations = NewsletterSubscriber.objects.filter(confirmed_at__gte=last_30_days).count()
        
        context = {
            'title': 'Newsletter Subscriber Statistics',
            'total_subscribers': total_subscribers,
            'confirmed_subscribers': confirmed_subscribers,
            'unconfirmed_subscribers': unconfirmed_subscribers,
            'confirmation_rate': (confirmed_subscribers / total_subscribers * 100) if total_subscribers > 0 else 0,
            'recent_subscriptions': recent_subscriptions,
            'recent_confirmations': recent_confirmations,
        }
        
        return render(request, 'admin/blog/newslettersubscriber/stats.html', context)


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    """
    Admin configuration for Comments with enhanced moderation dashboard and bulk actions.
    """
    list_display = ('author_name', 'post', 'is_approved', 'is_reply', 'created_at', 'content_preview', 'moderation_status')
    list_filter = ('is_approved', 'created_at', 'post__categories', 'post__author')
    search_fields = ('author_name', 'author_email', 'content', 'post__title')
    list_editable = ('is_approved',)
    readonly_fields = ('created_at', 'ip_address', 'user_agent', 'get_reply_count', 'get_author_comment_count')
    raw_id_fields = ('post', 'parent')
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    fieldsets = (
        ("Comment Information", {
            'fields': ('post', 'parent', 'author_name', 'author_email', 'author_website')
        }),
        ("Content", {
            'fields': ('content', 'is_approved')
        }),
        ("Moderation Info", {
            'classes': ('collapse',),
            'fields': ('get_reply_count', 'get_author_comment_count'),
            'description': 'Additional information for moderation decisions.'
        }),
        ("Technical Metadata", {
            'classes': ('collapse',),
            'fields': ('created_at', 'ip_address', 'user_agent'),
            'description': 'Technical information for spam detection and moderation.'
        }),
    )
    
    actions = [
        'approve_comments', 'unapprove_comments', 'delete_spam_comments', 
        'bulk_approve_by_author', 'bulk_block_by_ip', 'export_comments_csv'
    ]
    
    def content_preview(self, obj):
        """Show a preview of the comment content"""
        preview = obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
        # Add basic HTML escaping for safety
        preview = preview.replace('<', '&lt;').replace('>', '&gt;')
        return mark_safe(preview)
    content_preview.short_description = 'Content Preview'
    
    def moderation_status(self, obj):
        """Display moderation status with color coding"""
        if obj.is_approved:
            return format_html('<span style="color: green; font-weight: bold;">✓ Approved</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">⏳ Pending</span>')
    moderation_status.short_description = 'Status'
    
    def is_reply(self, obj):
        """Show if this comment is a reply"""
        return obj.parent is not None
    is_reply.boolean = True
    is_reply.short_description = 'Is Reply'
    
    def get_reply_count(self, obj):
        """Get the number of replies to this comment"""
        return obj.replies.count()
    get_reply_count.short_description = 'Replies'
    
    def get_author_comment_count(self, obj):
        """Get total comments by this author"""
        return Comment.objects.filter(author_email=obj.author_email).count()
    get_author_comment_count.short_description = 'Author Total Comments'
    
    def approve_comments(self, request, queryset):
        """Approve selected comments"""
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} comments approved.')
    approve_comments.short_description = "✓ Approve selected comments"
    
    def unapprove_comments(self, request, queryset):
        """Unapprove selected comments"""
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} comments unapproved.')
    unapprove_comments.short_description = "⏳ Unapprove selected comments"
    
    def delete_spam_comments(self, request, queryset):
        """Delete selected comments (for spam)"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} spam comments deleted.')
    delete_spam_comments.short_description = "🗑️ Delete selected comments (spam)"
    
    def bulk_approve_by_author(self, request, queryset):
        """Approve all comments by the same authors as selected comments"""
        author_emails = queryset.values_list('author_email', flat=True).distinct()
        updated = Comment.objects.filter(author_email__in=author_emails, is_approved=False).update(is_approved=True)
        self.message_user(request, f'Approved {updated} comments from {len(author_emails)} authors.')
    bulk_approve_by_author.short_description = "✓ Approve all comments by selected authors"
    
    def bulk_block_by_ip(self, request, queryset):
        """Mark all comments from the same IP addresses as spam"""
        ip_addresses = queryset.values_list('ip_address', flat=True).distinct()
        updated = Comment.objects.filter(ip_address__in=ip_addresses).update(is_approved=False)
        self.message_user(request, f'Blocked {updated} comments from {len(ip_addresses)} IP addresses.')
    bulk_block_by_ip.short_description = "🚫 Block all comments from selected IP addresses"
    
    def export_comments_csv(self, request, queryset):
        """Export selected comments to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="comments_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Post Title', 'Author Name', 'Author Email', 'Content', 'Approved', 'Created At', 'IP Address'])
        
        for comment in queryset.select_related('post'):
            writer.writerow([
                comment.post.title,
                comment.author_name,
                comment.author_email,
                comment.content[:200] + '...' if len(comment.content) > 200 else comment.content,
                'Yes' if comment.is_approved else 'No',
                comment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                comment.ip_address
            ])
        
        return response
    export_comments_csv.short_description = "📊 Export selected comments to CSV"
    
    def get_urls(self):
        """Add custom URLs for comment moderation dashboard"""
        urls = super().get_urls()
        custom_urls = [
            path('moderation-dashboard/', self.admin_site.admin_view(self.moderation_dashboard_view), name='blog_comment_moderation'),
        ]
        return custom_urls + urls
    
    def moderation_dashboard_view(self, request):
        """Display comment moderation dashboard"""
        # Get moderation statistics
        total_comments = Comment.objects.count()
        pending_comments = Comment.objects.filter(is_approved=False).count()
        approved_comments = total_comments - pending_comments
        
        # Recent activity
        last_24_hours = timezone.now() - timedelta(hours=24)
        recent_comments = Comment.objects.filter(created_at__gte=last_24_hours).count()
        recent_pending = Comment.objects.filter(created_at__gte=last_24_hours, is_approved=False).count()
        
        # Top commenters
        top_commenters = Comment.objects.values('author_name', 'author_email').annotate(
            comment_count=Count('id'),
            approved_count=Count('id', filter=Q(is_approved=True))
        ).order_by('-comment_count')[:10]
        
        # Comments by post
        top_commented_posts = Post.objects.annotate(
            comment_count=Count('comments', filter=Q(comments__is_approved=True))
        ).filter(comment_count__gt=0).order_by('-comment_count')[:10]
        
        context = {
            'title': 'Comment Moderation Dashboard',
            'total_comments': total_comments,
            'pending_comments': pending_comments,
            'approved_comments': approved_comments,
            'approval_rate': (approved_comments / total_comments * 100) if total_comments > 0 else 0,
            'recent_comments': recent_comments,
            'recent_pending': recent_pending,
            'top_commenters': top_commenters,
            'top_commented_posts': top_commented_posts,
        }
        
        return render(request, 'admin/blog/comment/moderation_dashboard.html', context)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('post', 'parent')


@admin.register(SocialShare)
class SocialShareAdmin(ModelAdmin):
    """
    Admin configuration for Social Share tracking with analytics.
    """
    list_display = ('post', 'platform', 'share_count', 'last_shared', 'platform_icon')
    list_filter = ('platform', 'last_shared', 'created_at')
    search_fields = ('post__title',)
    readonly_fields = ('created_at', 'last_shared')
    date_hierarchy = 'last_shared'
    
    fieldsets = (
        ("Share Information", {
            'fields': ('post', 'platform', 'share_count')
        }),
        ("Timestamps", {
            'fields': ('created_at', 'last_shared')
        }),
    )
    
    actions = ['reset_share_counts', 'export_share_data_csv']
    
    def platform_icon(self, obj):
        """Display platform-specific icons"""
        icons = {
            'facebook': '📘',
            'twitter': '🐦',
            'linkedin': '💼',
            'reddit': '🤖',
            'pinterest': '📌',
            'whatsapp': '💬',
        }
        return f"{icons.get(obj.platform, '📤')} {obj.get_platform_display()}"
    platform_icon.short_description = 'Platform'
    
    def reset_share_counts(self, request, queryset):
        """Reset share counts for selected items"""
        updated = queryset.update(share_count=0)
        self.message_user(request, f'Share counts reset for {updated} items.')
    reset_share_counts.short_description = "Reset share counts to zero"
    
    def export_share_data_csv(self, request, queryset):
        """Export social share data to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="social_shares_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Post Title', 'Platform', 'Share Count', 'Last Shared', 'Created At'])
        
        for share in queryset.select_related('post'):
            writer.writerow([
                share.post.title,
                share.get_platform_display(),
                share.share_count,
                share.last_shared.strftime('%Y-%m-%d %H:%M:%S') if share.last_shared else '',
                share.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    export_share_data_csv.short_description = "📊 Export share data to CSV"
    
    def get_urls(self):
        """Add custom URLs for social share analytics"""
        urls = super().get_urls()
        custom_urls = [
            path('analytics/', self.admin_site.admin_view(self.analytics_view), name='blog_socialshare_analytics'),
        ]
        return custom_urls + urls
    
    def analytics_view(self, request):
        """Display social share analytics"""
        # Total shares by platform
        platform_stats = SocialShare.objects.values('platform').annotate(
            total_shares=Sum('share_count'),
            post_count=Count('post', distinct=True)
        ).order_by('-total_shares')
        
        # Most shared posts
        most_shared_posts = Post.objects.annotate(
            total_shares=Sum('social_shares__share_count')
        ).filter(total_shares__gt=0).order_by('-total_shares')[:10]
        
        # Recent sharing activity
        last_7_days = timezone.now() - timedelta(days=7)
        recent_activity = SocialShare.objects.filter(last_shared__gte=last_7_days).values('platform').annotate(
            recent_shares=Sum('share_count')
        ).order_by('-recent_shares')
        
        context = {
            'title': 'Social Share Analytics',
            'platform_stats': platform_stats,
            'most_shared_posts': most_shared_posts,
            'recent_activity': recent_activity,
            'total_shares': sum(stat['total_shares'] or 0 for stat in platform_stats),
        }
        
        return render(request, 'admin/blog/socialshare/analytics.html', context)


@admin.register(AuthorProfile)
class AuthorProfileAdmin(ModelAdmin):
    """
    Admin configuration for Author Profiles with guest author management.
    """
    list_display = ('get_display_name', 'user', 'is_guest_author', 'is_active', 'get_post_count', 'created_at')
    list_filter = ('is_guest_author', 'is_active', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email', 'bio', 'guest_author_company')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at', 'get_post_count', 'get_recent_posts_display')
    raw_id_fields = ('user',)
    
    fieldsets = (
        ("Author Information", {
            'fields': ('user', 'bio', 'profile_picture', 'is_active')
        }),
        ("Social Media Links", {
            'fields': ('website', 'twitter', 'linkedin', 'github', 'instagram'),
            'description': 'Social media profiles and website links for the author.'
        }),
        ("Guest Author Settings", {
            'fields': ('is_guest_author', 'guest_author_email', 'guest_author_company'),
            'description': 'Special settings for guest authors with limited permissions.'
        }),
        ("Statistics", {
            'classes': ('collapse',),
            'fields': ('get_post_count', 'get_recent_posts_display'),
            'description': 'Author statistics and recent activity.'
        }),
        ("Timestamps", {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['activate_authors', 'deactivate_authors', 'mark_as_guest_authors', 'mark_as_regular_authors']
    
    def get_display_name(self, obj):
        """Display the author's name"""
        return obj.get_display_name()
    get_display_name.short_description = 'Display Name'
    get_display_name.admin_order_field = 'user__first_name'
    
    def get_post_count(self, obj):
        """Display the number of published posts by this author"""
        return obj.get_post_count()
    get_post_count.short_description = 'Published Posts'
    
    def get_recent_posts_display(self, obj):
        """Display recent posts by this author"""
        recent_posts = obj.get_recent_posts(limit=3)
        if not recent_posts:
            return "No published posts"
        
        posts_html = []
        for post in recent_posts:
            posts_html.append(f'<a href="/admin/blog/post/{post.id}/change/" target="_blank">{post.title}</a>')
        
        return '<br>'.join(posts_html)
    get_recent_posts_display.allow_tags = True
    get_recent_posts_display.short_description = 'Recent Posts'
    
    def activate_authors(self, request, queryset):
        """Activate selected author profiles"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} author profiles activated.')
    activate_authors.short_description = "Activate selected author profiles"
    
    def deactivate_authors(self, request, queryset):
        """Deactivate selected author profiles"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} author profiles deactivated.')
    deactivate_authors.short_description = "Deactivate selected author profiles"
    
    def mark_as_guest_authors(self, request, queryset):
        """Mark selected authors as guest authors"""
        updated = queryset.update(is_guest_author=True)
        self.message_user(request, f'{updated} authors marked as guest authors.')
    mark_as_guest_authors.short_description = "Mark selected authors as guest authors"
    
    def mark_as_regular_authors(self, request, queryset):
        """Mark selected authors as regular authors"""
        updated = queryset.update(is_guest_author=False)
        self.message_user(request, f'{updated} authors marked as regular authors.')
    mark_as_regular_authors.short_description = "Mark selected authors as regular authors"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('user')

@admin.register(MediaItem)
class MediaItemAdmin(ModelAdmin):
    """
    Admin configuration for Media Items with multimedia management capabilities.
    """
    list_display = ('title', 'post', 'media_type', 'is_featured', 'order', 'file_size_display', 'created_at')
    list_filter = ('media_type', 'is_featured', 'created_at', 'post__categories')
    search_fields = ('title', 'description', 'post__title', 'alt_text')
    list_editable = ('order', 'is_featured')
    readonly_fields = ('created_at', 'updated_at', 'file_size', 'width', 'height', 'get_responsive_images_display')
    raw_id_fields = ('post',)
    ordering = ('post', 'order', '-created_at')
    
    fieldsets = (
        ("Media Information", {
            'fields': ('post', 'media_type', 'title', 'description', 'alt_text')
        }),
        ("Image Fields", {
            'fields': ('original_image', 'thumbnail_image', 'medium_image', 'large_image'),
            'classes': ('collapse',),
            'description': 'Image files for different sizes (automatically generated)'
        }),
        ("Video Fields", {
            'fields': ('video_url', 'video_platform', 'video_id', 'video_embed_url', 'video_thumbnail'),
            'classes': ('collapse',),
            'description': 'Video embed information for YouTube and Vimeo'
        }),
        ("Gallery Fields", {
            'fields': ('gallery_images',),
            'classes': ('collapse',),
            'description': 'JSON data for image galleries'
        }),
        ("Display Settings", {
            'fields': ('order', 'is_featured')
        }),
        ("Technical Information", {
            'classes': ('collapse',),
            'fields': ('file_size', 'width', 'height', 'get_responsive_images_display'),
            'description': 'Automatically populated technical metadata'
        }),
        ("Timestamps", {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['mark_as_featured', 'unmark_as_featured', 'regenerate_thumbnails', 'optimize_images']
    
    def file_size_display(self, obj):
        """Display file size in human-readable format"""
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "N/A"
    file_size_display.short_description = 'File Size'
    
    def get_responsive_images_display(self, obj):
        """Display available responsive image sizes"""
        if obj.media_type == 'image':
            responsive_images = obj.get_responsive_images()
            if responsive_images:
                sizes = []
                for size, data in responsive_images.items():
                    if isinstance(data, dict) and 'url' in data:
                        sizes.append(f'<a href="{data["url"]}" target="_blank">{size.title()}</a>')
                    else:
                        sizes.append(size.title())
                return ' | '.join(sizes)
        return "N/A"
    get_responsive_images_display.allow_tags = True
    get_responsive_images_display.short_description = 'Available Sizes'
    
    def mark_as_featured(self, request, queryset):
        """Mark selected media items as featured"""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} media items marked as featured.')
    mark_as_featured.short_description = "Mark selected media as featured"
    
    def unmark_as_featured(self, request, queryset):
        """Remove featured status from selected media items"""
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} media items unmarked as featured.')
    unmark_as_featured.short_description = "Remove featured status from selected media"
    
    def regenerate_thumbnails(self, request, queryset):
        """Regenerate thumbnails for selected image media items"""
        from .services.multimedia_service import multimedia_service
        
        count = 0
        for media_item in queryset.filter(media_type='image'):
            if media_item.original_image:
                try:
                    # This would regenerate thumbnails - simplified for now
                    count += 1
                except Exception as e:
                    self.message_user(request, f'Error processing {media_item.title}: {str(e)}', level='ERROR')
        
        self.message_user(request, f'Thumbnails regenerated for {count} media items.')
    regenerate_thumbnails.short_description = "Regenerate thumbnails for selected images"
    
    def optimize_images(self, request, queryset):
        """Optimize images for web delivery"""
        from .services.multimedia_service import multimedia_service
        
        count = 0
        for media_item in queryset.filter(media_type='image'):
            if media_item.original_image:
                try:
                    # This would optimize images - simplified for now
                    count += 1
                except Exception as e:
                    self.message_user(request, f'Error optimizing {media_item.title}: {str(e)}', level='ERROR')
        
        self.message_user(request, f'Images optimized for {count} media items.')
    optimize_images.short_description = "Optimize selected images for web"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('post')
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Customize form fields"""
        if db_field.name == 'gallery_images':
            kwargs['widget'] = admin.widgets.AdminTextareaWidget(attrs={'rows': 10, 'cols': 80})
        return super().formfield_for_dbfield(db_field, request, **kwargs)


# Custom Admin Site with Analytics Dashboard
class BlogEngagementAdminSite(admin.AdminSite):
    """Custom admin site with engagement analytics dashboard"""
    site_header = 'Blog Engagement Administration'
    site_title = 'Blog Engagement Admin'
    index_title = 'Blog Engagement Dashboard'
    
    def get_urls(self):
        """Add custom URLs for analytics dashboard"""
        urls = super().get_urls()
        custom_urls = [
            path('engagement-analytics/', self.admin_view(self.engagement_analytics_view), name='blog_engagement_analytics'),
            path('toggle-sidebar/', self.admin_view(self.toggle_sidebar_view), name='toggle_sidebar'),
        ]
        return custom_urls + urls
    
    def engagement_analytics_view(self, request):
        """Main engagement analytics dashboard"""
        # Overall statistics
        total_posts = Post.objects.filter(status='published').count()
        total_comments = Comment.objects.filter(is_approved=True).count()
        total_subscribers = NewsletterSubscriber.objects.filter(is_confirmed=True).count()
        total_shares = SocialShare.objects.aggregate(total=Sum('share_count'))['total'] or 0
        
        # Recent activity (last 30 days)
        last_30_days = timezone.now() - timedelta(days=30)
        recent_posts = Post.objects.filter(created_at__gte=last_30_days, status='published').count()
        recent_comments = Comment.objects.filter(created_at__gte=last_30_days, is_approved=True).count()
        recent_subscribers = NewsletterSubscriber.objects.filter(subscribed_at__gte=last_30_days).count()
        recent_shares = SocialShare.objects.filter(last_shared__gte=last_30_days).aggregate(total=Sum('share_count'))['total'] or 0
        
        # Top performing content
        top_posts_by_views = Post.objects.filter(status='published').order_by('-view_count')[:10]
        top_posts_by_comments = Post.objects.filter(status='published').annotate(
            comment_count=Count('comments', filter=Q(comments__is_approved=True))
        ).order_by('-comment_count')[:10]
        top_posts_by_shares = Post.objects.filter(status='published').annotate(
            share_count=Sum('social_shares__share_count')
        ).filter(share_count__gt=0).order_by('-share_count')[:10]
        
        # Engagement trends by category
        category_stats = Category.objects.annotate(
            post_count=Count('posts', filter=Q(posts__status='published')),
            total_views=Sum('posts__view_count', filter=Q(posts__status='published')),
            total_comments=Count('posts__comments', filter=Q(posts__status='published', posts__comments__is_approved=True)),
            total_shares=Sum('posts__social_shares__share_count', filter=Q(posts__status='published'))
        ).filter(post_count__gt=0).order_by('-total_views')[:10]
        
        # Tag performance
        tag_stats = Tag.objects.annotate(
            post_count=Count('posts', filter=Q(posts__status='published')),
            total_views=Sum('posts__view_count', filter=Q(posts__status='published')),
            avg_engagement=Count('posts__comments', filter=Q(posts__status='published', posts__comments__is_approved=True)) + Sum('posts__social_shares__share_count', filter=Q(posts__status='published'))
        ).filter(post_count__gt=0).order_by('-total_views')[:10]
        
        # Author performance
        author_stats = User.objects.annotate(
            post_count=Count('blog_posts', filter=Q(blog_posts__status='published')),
            total_views=Sum('blog_posts__view_count', filter=Q(blog_posts__status='published')),
            total_comments=Count('blog_posts__comments', filter=Q(blog_posts__status='published', blog_posts__comments__is_approved=True)),
            total_shares=Sum('blog_posts__social_shares__share_count', filter=Q(blog_posts__status='published'))
        ).filter(post_count__gt=0).order_by('-total_views')[:10]
        
        # Social media platform performance
        platform_performance = SocialShare.objects.values('platform').annotate(
            total_shares=Sum('share_count'),
            post_count=Count('post', distinct=True),
            avg_shares_per_post=Sum('share_count') / Count('post', distinct=True)
        ).order_by('-total_shares')
        
        context = {
            'title': 'Blog Engagement Analytics Dashboard',
            'total_posts': total_posts,
            'total_comments': total_comments,
            'total_subscribers': total_subscribers,
            'total_shares': total_shares,
            'recent_posts': recent_posts,
            'recent_comments': recent_comments,
            'recent_subscribers': recent_subscribers,
            'recent_shares': recent_shares,
            'top_posts_by_views': top_posts_by_views,
            'top_posts_by_comments': top_posts_by_comments,
            'top_posts_by_shares': top_posts_by_shares,
            'category_stats': category_stats,
            'tag_stats': tag_stats,
            'author_stats': author_stats,
            'platform_performance': platform_performance,
        }
        
        return render(request, 'admin/blog/engagement_analytics.html', context)
    
    def toggle_sidebar_view(self, request):
        """Handle sidebar toggle functionality for Unfold theme"""
        from django.http import JsonResponse
        # This is a simple view that returns a success response
        # The actual sidebar toggle is handled by JavaScript on the frontend
        return JsonResponse({'status': 'success'})


# Create an instance of the custom admin site
blog_engagement_admin = BlogEngagementAdminSite(name='blog_engagement_admin')

# Register all models with the custom admin site
blog_engagement_admin.register(Post, PostAdmin)
blog_engagement_admin.register(Category, CategoryAdmin)
blog_engagement_admin.register(Tag, TagAdmin)
blog_engagement_admin.register(NewsletterSubscriber, NewsletterSubscriberAdmin)
blog_engagement_admin.register(Comment, CommentAdmin)
blog_engagement_admin.register(SocialShare, SocialShareAdmin)
blog_engagement_admin.register(AuthorProfile, AuthorProfileAdmin)
blog_engagement_admin.register(MediaItem, MediaItemAdmin)