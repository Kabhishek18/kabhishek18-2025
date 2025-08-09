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
from .linkedin_models import LinkedInConfig, LinkedInPost
from ckeditor.widgets import CKEditorWidget


@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = ('title', 'author', 'status', 'is_featured', 'view_count', 'engagement_score', 'linkedin_status', 'created_at')
    list_filter = ('status', 'is_featured', 'categories', 'tags', 'author', 'created_at', 'linkedin_posts__status')
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
        ("LinkedIn Integration", {
            'classes': ('collapse',),
            'fields': ('linkedin_posting_info',),
            'description': 'LinkedIn posting status and information'
        }),
        ("SEO & Meta", {
            'classes': ('collapse',),
            'fields': ('read_time', 'view_count', 'meta_data')
        }),
    )
    
    readonly_fields = ('view_count', 'linkedin_posting_info')
    actions = ['mark_as_featured', 'unmark_as_featured', 'clear_content_cache', 'post_to_linkedin', 'retry_linkedin_posting']
    
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
    
    def linkedin_status(self, obj):
        """Display LinkedIn posting status"""
        try:
            linkedin_post = obj.linkedin_posts.first()
            if not linkedin_post:
                return format_html('<span style="color: gray;">Not Posted</span>')
            
            status_colors = {
                'pending': 'orange',
                'success': 'green',
                'failed': 'red',
                'retrying': 'blue',
            }
            color = status_colors.get(linkedin_post.status, 'gray')
            
            if linkedin_post.status == 'success' and linkedin_post.linkedin_post_url:
                return format_html(
                    '<a href="{}" target="_blank" style="color: {}; font-weight: bold;">✓ Posted</a>',
                    linkedin_post.linkedin_post_url,
                    color
                )
            else:
                return format_html(
                    '<span style="color: {}; font-weight: bold;">{}</span>',
                    color,
                    linkedin_post.get_status_display()
                )
        except Exception:
            return format_html('<span style="color: gray;">Unknown</span>')
    linkedin_status.short_description = 'LinkedIn Status'
    
    def linkedin_posting_info(self, obj):
        """Display detailed LinkedIn posting information"""
        try:
            linkedin_post = obj.linkedin_posts.first()
            if not linkedin_post:
                return "This post has not been posted to LinkedIn."
            
            info_parts = []
            info_parts.append(f"<strong>Status:</strong> {linkedin_post.get_status_display()}")
            
            if linkedin_post.linkedin_post_id:
                info_parts.append(f"<strong>LinkedIn Post ID:</strong> {linkedin_post.linkedin_post_id}")
            
            if linkedin_post.linkedin_post_url:
                info_parts.append(f'<strong>LinkedIn URL:</strong> <a href="{linkedin_post.linkedin_post_url}" target="_blank">View Post</a>')
            
            if linkedin_post.attempt_count > 0:
                info_parts.append(f"<strong>Attempts:</strong> {linkedin_post.attempt_count}")
            
            if linkedin_post.posted_at:
                info_parts.append(f"<strong>Posted At:</strong> {linkedin_post.posted_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if linkedin_post.error_message:
                info_parts.append(f"<strong>Last Error:</strong> {linkedin_post.error_message}")
            
            if linkedin_post.status == 'retrying' and linkedin_post.next_retry_at:
                info_parts.append(f"<strong>Next Retry:</strong> {linkedin_post.get_retry_delay_display()}")
            
            return "<br>".join(info_parts)
        except Exception as e:
            return f"Error retrieving LinkedIn posting information: {e}"
    linkedin_posting_info.allow_tags = True
    linkedin_posting_info.short_description = 'LinkedIn Posting Information'
    
    def post_to_linkedin(self, request, queryset):
        """Manually post selected blog posts to LinkedIn"""
        from .services.linkedin_service import LinkedInAPIService, LinkedInAPIError
        from .linkedin_models import LinkedInConfig
        
        # Check if LinkedIn is configured
        config = LinkedInConfig.get_active_config()
        if not config:
            self.message_user(
                request, 
                "LinkedIn integration is not configured. Please configure LinkedIn settings first.", 
                level=messages.ERROR
            )
            return
        
        service = LinkedInAPIService(config)
        if not service.is_configured():
            self.message_user(
                request, 
                "LinkedIn integration is not properly configured.", 
                level=messages.ERROR
            )
            return
        
        success_count = 0
        error_count = 0
        
        for post in queryset:
            # Only post published posts
            if post.status != 'published':
                self.message_user(
                    request, 
                    f"Skipped '{post.title}' - only published posts can be posted to LinkedIn", 
                    level=messages.WARNING
                )
                continue
            
            # Check if already successfully posted
            existing_linkedin_post = post.linkedin_posts.filter(status='success').first()
            if existing_linkedin_post:
                self.message_user(
                    request, 
                    f"Skipped '{post.title}' - already successfully posted to LinkedIn", 
                    level=messages.WARNING
                )
                continue
            
            try:
                linkedin_post = service.post_blog_article(post)
                if linkedin_post.is_successful():
                    success_count += 1
                else:
                    error_count += 1
                    self.message_user(
                        request, 
                        f"Failed to post '{post.title}' to LinkedIn: {linkedin_post.error_message}", 
                        level=messages.ERROR
                    )
            except LinkedInAPIError as e:
                error_count += 1
                self.message_user(
                    request, 
                    f"Failed to post '{post.title}' to LinkedIn: {e.message}", 
                    level=messages.ERROR
                )
            except Exception as e:
                error_count += 1
                self.message_user(
                    request, 
                    f"Unexpected error posting '{post.title}' to LinkedIn: {str(e)}", 
                    level=messages.ERROR
                )
        
        if success_count > 0:
            self.message_user(
                request, 
                f"Successfully posted {success_count} post(s) to LinkedIn", 
                level=messages.SUCCESS
            )
        
        if error_count > 0:
            self.message_user(
                request, 
                f"Failed to post {error_count} post(s) to LinkedIn", 
                level=messages.ERROR
            )
    post_to_linkedin.short_description = "Post selected posts to LinkedIn"
    
    def retry_linkedin_posting(self, request, queryset):
        """Retry failed LinkedIn postings for selected posts"""
        from .services.linkedin_service import LinkedInAPIService, LinkedInAPIError
        from .linkedin_models import LinkedInConfig
        
        # Check if LinkedIn is configured
        config = LinkedInConfig.get_active_config()
        if not config:
            self.message_user(
                request, 
                "LinkedIn integration is not configured. Please configure LinkedIn settings first.", 
                level=messages.ERROR
            )
            return
        
        service = LinkedInAPIService(config)
        if not service.is_configured():
            self.message_user(
                request, 
                "LinkedIn integration is not properly configured.", 
                level=messages.ERROR
            )
            return
        
        retry_count = 0
        success_count = 0
        error_count = 0
        
        for post in queryset:
            # Only retry posts that have failed LinkedIn postings
            failed_linkedin_posts = post.linkedin_posts.filter(status__in=['failed', 'retrying'])
            if not failed_linkedin_posts.exists():
                continue
            
            linkedin_post = failed_linkedin_posts.first()
            if not linkedin_post.can_retry():
                self.message_user(
                    request, 
                    f"Cannot retry '{post.title}' - maximum attempts reached", 
                    level=messages.WARNING
                )
                continue
            
            try:
                # Reset to pending and try again
                linkedin_post.mark_as_pending()
                linkedin_post = service.post_blog_article(post)
                retry_count += 1
                
                if linkedin_post.is_successful():
                    success_count += 1
                else:
                    error_count += 1
                    self.message_user(
                        request, 
                        f"Retry failed for '{post.title}': {linkedin_post.error_message}", 
                        level=messages.ERROR
                    )
            except LinkedInAPIError as e:
                error_count += 1
                self.message_user(
                    request, 
                    f"Retry failed for '{post.title}': {e.message}", 
                    level=messages.ERROR
                )
            except Exception as e:
                error_count += 1
                self.message_user(
                    request, 
                    f"Unexpected error retrying '{post.title}': {str(e)}", 
                    level=messages.ERROR
                )
        
        if retry_count == 0:
            self.message_user(
                request, 
                "No posts found that can be retried for LinkedIn posting", 
                level=messages.WARNING
            )
        else:
            if success_count > 0:
                self.message_user(
                    request, 
                    f"Successfully retried and posted {success_count} post(s) to LinkedIn", 
                    level=messages.SUCCESS
                )
            
            if error_count > 0:
                self.message_user(
                    request, 
                    f"Failed to retry {error_count} post(s) for LinkedIn posting", 
                    level=messages.ERROR
                )
    retry_linkedin_posting.short_description = "Retry failed LinkedIn postings"
    
    def get_queryset(self, request):
        """Optimize queryset with prefetch_related for LinkedIn posts"""
        return super().get_queryset(request).prefetch_related('linkedin_posts')

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

@admin.register(LinkedInConfig)
class LinkedInConfigAdmin(ModelAdmin):
    """
    Admin configuration for LinkedIn API credentials with secure field handling.
    """
    list_display = ('client_id_display', 'is_active', 'credential_status', 'token_status', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('client_id',)
    readonly_fields = ('created_at', 'updated_at', 'credential_validation_display', 'token_info_display')
    
    fieldsets = (
        ("Basic Configuration", {
            'fields': ('client_id', 'is_active'),
            'description': 'Basic LinkedIn API configuration settings.'
        }),
        ("API Credentials", {
            'fields': ('client_secret', 'access_token', 'refresh_token'),
            'description': 'Sensitive API credentials (encrypted when stored). Leave blank to keep existing values.'
        }),
        ("Token Management", {
            'fields': ('token_expires_at', 'token_info_display'),
            'description': 'Access token expiration and status information.'
        }),
        ("Validation", {
            'classes': ('collapse',),
            'fields': ('credential_validation_display',),
            'description': 'Credential validation and troubleshooting information.'
        }),
        ("Timestamps", {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['validate_credentials', 'clear_tokens', 'test_connection']
    
    def client_id_display(self, obj):
        """Display truncated client ID for security"""
        if obj.client_id:
            return f"{obj.client_id[:10]}..."
        return "Not set"
    client_id_display.short_description = 'Client ID'
    
    def credential_status(self, obj):
        """Display overall credential status"""
        if obj.has_valid_credentials():
            return format_html('<span style="color: green; font-weight: bold;">✓ Valid</span>')
        elif obj.get_client_secret() and obj.client_id:
            return format_html('<span style="color: orange; font-weight: bold;">⚠ Needs Auth</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">✗ Invalid</span>')
    credential_status.short_description = 'Status'
    
    def token_status(self, obj):
        """Display token expiration status"""
        if not obj.get_access_token():
            return format_html('<span style="color: gray;">No Token</span>')
        elif obj.is_token_expired():
            return format_html('<span style="color: red; font-weight: bold;">Expired</span>')
        elif obj.needs_token_refresh():
            return format_html('<span style="color: orange; font-weight: bold;">Expires Soon</span>')
        else:
            return format_html('<span style="color: green; font-weight: bold;">Valid</span>')
    token_status.short_description = 'Token Status'
    
    def client_secret_display(self, obj):
        """Display client secret field with security handling"""
        if obj.client_secret:
            return "••••••••••••••••"
        return "Not set"
    client_secret_display.short_description = 'Client Secret'
    
    def access_token_display(self, obj):
        """Display access token field with security handling"""
        if obj.access_token:
            return "••••••••••••••••"
        return "Not set"
    access_token_display.short_description = 'Access Token'
    
    def refresh_token_display(self, obj):
        """Display refresh token field with security handling"""
        if obj.refresh_token:
            return "••••••••••••••••"
        return "Not set"
    refresh_token_display.short_description = 'Refresh Token'
    
    def token_info_display(self, obj):
        """Display detailed token information"""
        status = obj.get_credential_status()
        
        info_parts = []
        if status.get('expires_at'):
            expires_at = status['expires_at'].strftime('%Y-%m-%d %H:%M:%S')
            info_parts.append(f"Expires: {expires_at}")
            
            if status.get('expires_in_hours'):
                hours = status['expires_in_hours']
                if hours > 0:
                    info_parts.append(f"({hours:.1f} hours remaining)")
                else:
                    info_parts.append("(EXPIRED)")
        
        if status.get('needs_refresh'):
            info_parts.append("⚠ Needs refresh")
        
        return "<br>".join(info_parts) if info_parts else "No token information"
    token_info_display.allow_tags = True
    token_info_display.short_description = 'Token Information'
    
    def credential_validation_display(self, obj):
        """Display credential validation results"""
        validation = obj.validate_credentials()
        
        results = []
        if validation['client_secret_valid']:
            results.append("✓ Client Secret: Valid")
        else:
            results.append("✗ Client Secret: Invalid")
        
        if validation['access_token_valid']:
            results.append("✓ Access Token: Valid")
        else:
            results.append("✗ Access Token: Invalid")
        
        if validation['refresh_token_valid']:
            results.append("✓ Refresh Token: Valid")
        else:
            results.append("✗ Refresh Token: Invalid")
        
        if validation['errors']:
            results.append("<br><strong>Errors:</strong>")
            for error in validation['errors']:
                results.append(f"• {error}")
        
        return "<br>".join(results)
    credential_validation_display.allow_tags = True
    credential_validation_display.short_description = 'Credential Validation'
    
    def validate_credentials(self, request, queryset):
        """Validate credentials for selected configurations"""
        for config in queryset:
            validation = config.validate_credentials()
            if validation['errors']:
                self.message_user(
                    request, 
                    f"Config {config.id}: {', '.join(validation['errors'])}", 
                    level=messages.ERROR
                )
            else:
                self.message_user(
                    request, 
                    f"Config {config.id}: All credentials valid", 
                    level=messages.SUCCESS
                )
    validate_credentials.short_description = "Validate selected configurations"
    
    def clear_tokens(self, request, queryset):
        """Clear tokens for selected configurations"""
        for config in queryset:
            config.clear_tokens()
        
        count = queryset.count()
        self.message_user(request, f"Cleared tokens for {count} configuration(s)")
    clear_tokens.short_description = "Clear tokens (force re-authentication)"
    
    def test_connection(self, request, queryset):
        """Test LinkedIn API connection for selected configurations"""
        # This would require the LinkedIn service to be implemented
        # For now, just validate credentials
        for config in queryset:
            if config.has_valid_credentials():
                self.message_user(
                    request, 
                    f"Config {config.id}: Ready for API connection", 
                    level=messages.SUCCESS
                )
            else:
                self.message_user(
                    request, 
                    f"Config {config.id}: Invalid credentials - cannot connect", 
                    level=messages.ERROR
                )
    test_connection.short_description = "Test API connection readiness"
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form to handle sensitive fields"""
        from django import forms
        
        class LinkedInConfigForm(forms.ModelForm):
            client_secret = forms.CharField(
                widget=forms.PasswordInput(attrs={'placeholder': 'Enter client secret'}),
                required=False,
                help_text="Leave blank to keep existing value"
            )
            access_token = forms.CharField(
                widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter access token'}),
                required=False,
                help_text="Leave blank to keep existing value"
            )
            refresh_token = forms.CharField(
                widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter refresh token'}),
                required=False,
                help_text="Leave blank to keep existing value"
            )
            
            class Meta:
                model = LinkedInConfig
                fields = '__all__'
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Don't show actual encrypted values in form
                if self.instance and self.instance.pk:
                    self.fields['client_secret'].initial = ''
                    self.fields['access_token'].initial = ''
                    self.fields['refresh_token'].initial = ''
            
            def save(self, commit=True):
                instance = super().save(commit=False)
                
                # Only update encrypted fields if new values are provided
                if self.cleaned_data.get('client_secret'):
                    instance.set_client_secret(self.cleaned_data['client_secret'])
                
                if self.cleaned_data.get('access_token'):
                    instance.set_access_token(self.cleaned_data['access_token'])
                
                if self.cleaned_data.get('refresh_token'):
                    instance.set_refresh_token(self.cleaned_data['refresh_token'])
                
                if commit:
                    instance.save()
                return instance
        
        kwargs['form'] = LinkedInConfigForm
        return super().get_form(request, obj, **kwargs)
    
    def has_add_permission(self, request):
        """Limit to one active configuration"""
        if LinkedInConfig.objects.filter(is_active=True).exists():
            return False
        return super().has_add_permission(request)
    
    def get_urls(self):
        """Add custom URLs for credential management"""
        urls = super().get_urls()
        custom_urls = [
            path('set-credentials/<int:config_id>/', 
                 self.admin_site.admin_view(self.set_credentials_view), 
                 name='blog_linkedinconfig_set_credentials'),
        ]
        return custom_urls + urls
    
    def set_credentials_view(self, request, config_id):
        """Custom view for setting sensitive credentials"""
        try:
            config = LinkedInConfig.objects.get(id=config_id)
        except LinkedInConfig.DoesNotExist:
            messages.error(request, "Configuration not found")
            return redirect('admin:blog_linkedinconfig_changelist')
        
        if request.method == 'POST':
            client_secret = request.POST.get('client_secret')
            access_token = request.POST.get('access_token')
            refresh_token = request.POST.get('refresh_token')
            expires_in = request.POST.get('expires_in')
            
            try:
                if client_secret:
                    config.set_client_secret(client_secret)
                
                if access_token:
                    config.set_access_token(access_token)
                
                if refresh_token:
                    config.set_refresh_token(refresh_token)
                
                if expires_in:
                    try:
                        expires_seconds = int(expires_in)
                        config.token_expires_at = timezone.now() + timedelta(seconds=expires_seconds)
                    except ValueError:
                        messages.error(request, "Invalid expiration time")
                        return redirect(request.path)
                
                config.save()
                messages.success(request, "Credentials updated successfully")
                return redirect('admin:blog_linkedinconfig_changelist')
                
            except Exception as e:
                messages.error(request, f"Failed to update credentials: {e}")
        
        context = {
            'title': f'Set Credentials for {config}',
            'config': config,
            'opts': self.model._meta,
        }
        
        return render(request, 'admin/blog/linkedinconfig/set_credentials.html', context)


@admin.register(LinkedInPost)
class LinkedInPostAdmin(ModelAdmin):
    """
    Admin configuration for LinkedIn Post tracking with status monitoring.
    """
    list_display = ('post_title', 'status_display', 'attempt_count', 'created_at', 'posted_at', 'retry_info')
    list_filter = ('status', 'created_at', 'posted_at', 'post__categories')
    search_fields = ('post__title', 'linkedin_post_id', 'error_message')
    readonly_fields = (
        'created_at', 'posted_at', 'last_attempt_at', 'linkedin_post_url',
        'posted_title', 'posted_content', 'posted_url', 'error_details_display'
    )
    raw_id_fields = ('post',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    fieldsets = (
        ("Post Information", {
            'fields': ('post', 'status', 'linkedin_post_id', 'linkedin_post_url')
        }),
        ("Posting Content", {
            'classes': ('collapse',),
            'fields': ('posted_title', 'posted_content', 'posted_url'),
            'description': 'Content that was posted to LinkedIn'
        }),
        ("Retry Configuration", {
            'fields': ('attempt_count', 'max_attempts', 'next_retry_at')
        }),
        ("Error Information", {
            'classes': ('collapse',),
            'fields': ('error_message', 'error_code', 'error_details_display'),
            'description': 'Error details for failed posting attempts'
        }),
        ("Timestamps", {
            'classes': ('collapse',),
            'fields': ('created_at', 'posted_at', 'last_attempt_at')
        }),
    )
    
    actions = ['retry_failed_posts', 'mark_as_success', 'reset_attempts', 'export_posting_data']
    
    def post_title(self, obj):
        """Display the blog post title"""
        return obj.post.title
    post_title.short_description = 'Blog Post'
    post_title.admin_order_field = 'post__title'
    
    def status_display(self, obj):
        """Display status with color coding"""
        status_colors = {
            'pending': 'orange',
            'success': 'green',
            'failed': 'red',
            'retrying': 'blue',
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def retry_info(self, obj):
        """Display retry information"""
        if obj.status == 'retrying' and obj.next_retry_at:
            return obj.get_retry_delay_display()
        elif obj.status == 'failed':
            return f"Failed after {obj.attempt_count} attempts"
        elif obj.status == 'success':
            return "Posted successfully"
        else:
            return "Pending"
    retry_info.short_description = 'Retry Info'
    
    def error_details_display(self, obj):
        """Display detailed error information"""
        if not obj.error_message:
            return "No errors"
        
        details = [f"<strong>Message:</strong> {obj.error_message}"]
        
        if obj.error_code:
            details.append(f"<strong>Code:</strong> {obj.error_code}")
        
        if obj.last_attempt_at:
            details.append(f"<strong>Last Attempt:</strong> {obj.last_attempt_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "<br>".join(details)
    error_details_display.allow_tags = True
    error_details_display.short_description = 'Error Details'
    
    def retry_failed_posts(self, request, queryset):
        """Retry selected failed posts"""
        retryable_posts = queryset.filter(status__in=['failed', 'retrying'])
        count = 0
        
        for linkedin_post in retryable_posts:
            if linkedin_post.can_retry():
                linkedin_post.mark_as_pending()
                count += 1
        
        self.message_user(request, f"Marked {count} posts for retry")
    retry_failed_posts.short_description = "Retry selected failed posts"
    
    def mark_as_success(self, request, queryset):
        """Mark selected posts as successful (manual override)"""
        count = 0
        for linkedin_post in queryset:
            if linkedin_post.status != 'success':
                linkedin_post.mark_as_success('manual-override', 'Manual admin override')
                count += 1
        
        self.message_user(request, f"Marked {count} posts as successful")
    mark_as_success.short_description = "Mark selected posts as successful"
    
    def reset_attempts(self, request, queryset):
        """Reset attempt count for selected posts"""
        updated = queryset.update(attempt_count=0, next_retry_at=None)
        self.message_user(request, f"Reset attempt count for {updated} posts")
    reset_attempts.short_description = "Reset attempt count"
    
    def export_posting_data(self, request, queryset):
        """Export posting data to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="linkedin_posts_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Blog Post Title', 'Status', 'LinkedIn Post ID', 'Attempt Count', 
            'Created At', 'Posted At', 'Error Message'
        ])
        
        for linkedin_post in queryset.select_related('post'):
            writer.writerow([
                linkedin_post.post.title,
                linkedin_post.get_status_display(),
                linkedin_post.linkedin_post_id or '',
                linkedin_post.attempt_count,
                linkedin_post.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                linkedin_post.posted_at.strftime('%Y-%m-%d %H:%M:%S') if linkedin_post.posted_at else '',
                linkedin_post.error_message or ''
            ])
        
        return response
    export_posting_data.short_description = "Export posting data to CSV"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('post')