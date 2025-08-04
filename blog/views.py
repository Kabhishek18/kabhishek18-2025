from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import F, Q, Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.core.cache import cache
from django.conf import settings
from django.utils.html import format_html
from django.db.models import Case, When, Value, IntegerField
from datetime import datetime, timedelta
import re
from .models import Post, Category, NewsletterSubscriber, Tag, Comment, SocialShare, AuthorProfile, MediaItem
from .forms import NewsletterSubscriptionForm, CommentForm  # MediaUploadForm, ImageGalleryForm, VideoEmbedForm
from .tasks import send_confirmation_email, send_comment_notification
from .services.social_share_service import SocialShareService
from .services.content_discovery_service import ContentDiscoveryService
from .services.table_of_contents_service import TableOfContentsService
# from .services.multimedia_service import multimedia_service
from .author_services.author_service import AuthorService
from .security_clean import RateLimiter, SecurityAuditLogger
from .performance import CacheManager, QueryOptimizer, ViewCountOptimizer, PerformanceMonitor
import time

def blog_list(request, category_slug=None, tag_slug=None):
    """
    Enhanced blog list view with advanced search, filtering, and navigation capabilities.
    Supports category hierarchy, tag filtering, date ranges, and improved search with highlighting.
    """
    category = None
    tag = None
    posts_list = Post.objects.filter(status='published').select_related('author').prefetch_related('categories', 'tags')
    
    # Filter by category (with hierarchy support)
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        # Include posts from subcategories as well
        category_ids = [category.id]
        subcategories = category.subcategories.all()
        category_ids.extend([sub.id for sub in subcategories])
        posts_list = posts_list.filter(categories__id__in=category_ids)
    
    # Filter by tag
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        posts_list = posts_list.filter(tags=tag)
    
    # Advanced search functionality
    query = request.GET.get('q', '').strip()
    search_highlighted_posts = []
    
    if query:
        # Enhanced search with weighted results
        search_query = Q()
        
        # Title search (highest weight)
        search_query |= Q(title__icontains=query)
        
        # Tag search (high weight)
        search_query |= Q(tags__name__icontains=query)
        
        # Category search (medium weight)
        search_query |= Q(categories__name__icontains=query)
        
        # Content search (lower weight)
        search_query |= Q(excerpt__icontains=query) | Q(content__icontains=query)
        
        # Apply search filter
        posts_list = posts_list.filter(search_query).distinct()
        
        # Add search result highlighting
        search_highlighted_posts = _highlight_search_results(posts_list, query)
    
    # Advanced filtering
    category_filter = request.GET.get('category')
    tag_filter = request.GET.get('tag')
    date_filter = request.GET.get('date_range')
    sort_by = request.GET.get('sort', 'newest')
    
    # Additional category filter (for advanced search form)
    if category_filter and category_filter != 'all':
        try:
            filter_category = Category.objects.get(slug=category_filter)
            posts_list = posts_list.filter(categories=filter_category)
        except Category.DoesNotExist:
            pass
    
    # Additional tag filter (for advanced search form)
    if tag_filter and tag_filter != 'all':
        try:
            filter_tag = Tag.objects.get(slug=tag_filter)
            posts_list = posts_list.filter(tags=filter_tag)
        except Tag.DoesNotExist:
            pass
    
    # Date range filtering
    if date_filter:
        now = timezone.now()
        if date_filter == 'week':
            start_date = now - timedelta(days=7)
            posts_list = posts_list.filter(created_at__gte=start_date)
        elif date_filter == 'month':
            start_date = now - timedelta(days=30)
            posts_list = posts_list.filter(created_at__gte=start_date)
        elif date_filter == 'year':
            start_date = now - timedelta(days=365)
            posts_list = posts_list.filter(created_at__gte=start_date)
    
    # Sorting options
    if sort_by == 'oldest':
        posts_list = posts_list.order_by('created_at')
    elif sort_by == 'popular':
        posts_list = posts_list.order_by('-view_count', '-created_at')
    elif sort_by == 'title':
        posts_list = posts_list.order_by('title')
    else:  # newest (default)
        posts_list = posts_list.order_by('-created_at')
    
    # Pagination with enhanced page size options
    page_size = int(request.GET.get('per_page', 10))
    if page_size not in [5, 10, 20, 50]:
        page_size = 10
    
    paginator = Paginator(posts_list, page_size)
    page_number = request.GET.get('page')
    
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    
    # Get navigation data with hierarchy
    category_hierarchy = _get_category_hierarchy()
    all_categories = Category.objects.annotate(
        post_count=Count('posts', filter=Q(posts__status='published'))
    ).filter(post_count__gt=0).order_by('name')
    
    # Enhanced tag cloud with weighted display
    tag_cloud = Tag.objects.annotate(
        post_count=Count('posts', filter=Q(posts__status='published'))
    ).filter(post_count__gt=0).order_by('-post_count', 'name')[:20]
    
    # Generate breadcrumbs
    breadcrumbs = _generate_breadcrumbs(category, tag, query)
    
    # Get filter options for advanced search
    filter_options = {
        'categories': Category.objects.annotate(
            post_count=Count('posts', filter=Q(posts__status='published'))
        ).filter(post_count__gt=0).order_by('name'),
        'tags': Tag.objects.annotate(
            post_count=Count('posts', filter=Q(posts__status='published'))
        ).filter(post_count__gt=0).order_by('name'),
        'date_ranges': [
            ('all', 'All Time'),
            ('week', 'Past Week'),
            ('month', 'Past Month'),
            ('year', 'Past Year'),
        ],
        'sort_options': [
            ('newest', 'Newest First'),
            ('oldest', 'Oldest First'),
            ('popular', 'Most Popular'),
            ('title', 'Alphabetical'),
        ]
    }
    
    newsletter_form = NewsletterSubscriptionForm()
    
    # Get content discovery data
    featured_posts = ContentDiscoveryService.get_featured_posts(limit=3)
    popular_posts = ContentDiscoveryService.get_popular_posts(timeframe='week', limit=5)
    trending_tags = ContentDiscoveryService.get_trending_tags(limit=10)
    
    # Build title and meta description
    title_parts = ['Blog']
    if category:
        title_parts.append(category.name)
    if tag:
        title_parts.append(tag.name)
    if query:
        title_parts.append(f'Search: {query}')
    
    title = ' - '.join(title_parts) + ' - Digital Codex'
    
    # Enhanced meta description
    meta_parts = []
    if query:
        meta_parts.append(f'Search results for "{query}"')
    if category:
        meta_parts.append(f'in {category.name}')
    if tag:
        meta_parts.append(f'tagged with {tag.name}')
    
    if meta_parts:
        meta_details = ' '.join(meta_parts) + f' - {posts.paginator.count} posts found'
    else:
        meta_details = 'Read the latest articles and insights from Digital Codex'
    
    context = {
        'posts': posts,
        'category_hierarchy': category_hierarchy,
        'all_categories': all_categories,
        'tag_cloud': tag_cloud,
        'current_category': category,
        'current_tag': tag,
        'newsletter_form': newsletter_form,
        'title': title,
        'meta_details': meta_details,
        'query': query,
        'breadcrumbs': breadcrumbs,
        'filter_options': filter_options,
        'current_filters': {
            'category': category_filter,
            'tag': tag_filter,
            'date_range': date_filter,
            'sort': sort_by,
            'per_page': page_size,
        },
        'search_highlighted_posts': search_highlighted_posts,
        'total_results': posts.paginator.count if posts else 0,
        'featured_posts': featured_posts,
        'popular_posts': popular_posts,
        'trending_tags': trending_tags,
    }
    return render(request, 'blog/blog_list.html', context)

@PerformanceMonitor.time_function
@PerformanceMonitor.track_query_count
def blog_detail(request, slug):
    """
    Displays a single blog post with comments and increments its view count.
    Enhanced with performance optimizations and security measures.
    """
    post = get_object_or_404(Post, slug=slug, status='published')
    
    # Get author profile
    author_profile = AuthorService.get_author_profile(post.author)
    
    # Increment view count with optimized batching
    ViewCountOptimizer.increment_view_count(post.id)
    
    # Get related posts using optimized caching
    related_posts = QueryOptimizer.get_related_posts_optimized(post, limit=3)

    # Get approved comments for this post (only top-level comments, replies are handled in template)
    comments = Comment.objects.filter(
        post=post, 
        is_approved=True, 
        parent=None
    ).order_by('created_at').prefetch_related('replies')
    
    # Initialize comment form
    comment_form = CommentForm()
    
    # Get social sharing data
    share_urls = SocialShareService.generate_share_urls(post, request)
    share_counts = SocialShareService.get_share_counts(post)
    total_shares = SocialShareService.get_total_shares(post)
    
    # Generate table of contents data
    toc_data = TableOfContentsService.generate_toc_data_for_template(post)

    context = {
        'post': post,
        'author_profile': author_profile,
        'related_posts': related_posts,
        'comments': comments,
        'comment_form': comment_form,
        'share_urls': share_urls,
        'share_counts': share_counts,
        'total_shares': total_shares,
        'title': post.title,
        'meta_data': post.meta_data,
        'meta_details': post.excerpt or post.content[:160],
        'toc_data': toc_data,
    }
    return render(request, 'blog/blog_detail.html', context)


def subscribe_newsletter(request):
    """
    Handles newsletter subscription form submission with enhanced security and rate limiting.
    """
    if request.method == 'POST':
        # Enhanced rate limiting for newsletter subscriptions
        client_ip = get_client_ip(request)
        rate_limiter = RateLimiter()
        
        if rate_limiter.is_rate_limited(f'newsletter_{client_ip}', 3, 60):
            SecurityAuditLogger.log_suspicious_activity(request, 'rate_limit_exceeded', f'newsletter_subscription from {client_ip}')
            messages.error(request, 'Too many subscription attempts. Please try again later.')
            return redirect(request.META.get('HTTP_REFERER', 'blog:list'))
        
        form = NewsletterSubscriptionForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            # Check if email already exists
            existing_subscriber = NewsletterSubscriber.objects.filter(email=email).first()
            
            if existing_subscriber:
                if existing_subscriber.is_confirmed:
                    messages.warning(request, 'This email address is already subscribed and confirmed.')
                else:
                    # Resend confirmation email
                    send_confirmation_email.delay(existing_subscriber.id)
                    messages.info(request, 'A confirmation email has been resent to your email address.')
            else:
                # Create new subscriber
                subscriber = NewsletterSubscriber.objects.create(email=email)
                send_confirmation_email.delay(subscriber.id)
                messages.success(request, 'Thank you for subscribing! Please check your email to confirm your subscription.')
        else:
            # Log potential spam attempt if validation failed
            SecurityAuditLogger.log_spam_attempt(
                request, 
                'newsletter_subscription', 
                request.POST.get('email', '')
            )
            
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field.replace("_", " ").title()}: {error}')
    
    # Redirect back to the previous page, or the blog list as a fallback
    return redirect(request.META.get('HTTP_REFERER', 'blog:list'))


def confirm_subscription(request, token):
    """
    Handles email subscription confirmation via token.
    """
    try:
        subscriber = NewsletterSubscriber.objects.get(confirmation_token=token)
        
        if subscriber.is_confirmed:
            messages.info(request, 'Your subscription is already confirmed.')
        else:
            subscriber.is_confirmed = True
            subscriber.confirmed_at = timezone.now()
            subscriber.save()
            messages.success(request, 'Your subscription has been confirmed successfully!')
        
        return redirect('blog:list')
        
    except NewsletterSubscriber.DoesNotExist:
        messages.error(request, 'Invalid confirmation link.')
        return redirect('blog:list')


def unsubscribe_newsletter(request, token):
    """
    Handles newsletter unsubscription via token.
    """
    try:
        subscriber = NewsletterSubscriber.objects.get(unsubscribe_token=token)
        
        if request.method == 'POST':
            subscriber.delete()
            messages.success(request, 'You have been successfully unsubscribed from our newsletter.')
            return redirect('blog:list')
        
        # Show confirmation page
        context = {
            'subscriber': subscriber,
            'title': 'Unsubscribe from Newsletter',
        }
        return render(request, 'blog/unsubscribe_confirm.html', context)
        
    except NewsletterSubscriber.DoesNotExist:
        messages.error(request, 'Invalid unsubscribe link.')
        return redirect('blog:list')


def get_client_ip(request):
    """Get the client's IP address from the request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@csrf_protect
@require_POST
def submit_comment(request, slug):
    """
    Handle comment submission with enhanced spam prevention and rate limiting.
    """
    post = get_object_or_404(Post, slug=slug, status='published')
    
    # Check if comments are allowed for this post
    if not post.allow_comments:
        messages.error(request, 'Comments are not allowed for this post.')
        return redirect('blog:detail', slug=slug)
    
    # Enhanced rate limiting using security module
    client_ip = get_client_ip(request)
    rate_limiter = RateLimiter()
    
    if rate_limiter.is_rate_limited(f'comment_{client_ip}', 5, 5):
        SecurityAuditLogger.log_suspicious_activity(request, 'rate_limit_exceeded', f'comment_submission from {client_ip}')
        messages.error(request, 'Rate limit exceeded. Please wait before submitting another comment.')
        return redirect('blog:detail', slug=slug)
    
    form = CommentForm(request.POST)
    
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.ip_address = client_ip
        comment.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        # Handle parent comment for replies
        parent_id = request.POST.get('parent_id')
        if parent_id:
            try:
                parent_comment = Comment.objects.get(id=parent_id, post=post, is_approved=True)
                comment.parent = parent_comment
            except Comment.DoesNotExist:
                messages.error(request, 'Invalid reply target.')
                return redirect('blog:detail', slug=slug)
        
        comment.save()
        
        # Send notification to post author (async)
        send_comment_notification.delay(comment.id)
        
        messages.success(request, 'Your comment has been submitted and is awaiting moderation.')
        return redirect('blog:detail', slug=slug)
    
    else:
        # Log potential spam attempt if validation failed
        SecurityAuditLogger.log_spam_attempt(
            request, 
            'comment', 
            request.POST.get('content', '')[:100]
        )
        
        # If form is invalid, redirect back with errors
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field.replace("_", " ").title()}: {error}')
        
        return redirect('blog:detail', slug=slug)


@csrf_protect
@require_POST
def submit_reply(request, slug, comment_id):
    """
    Handle reply submission to a specific comment.
    """
    post = get_object_or_404(Post, slug=slug, status='published')
    parent_comment = get_object_or_404(Comment, id=comment_id, post=post, is_approved=True)
    
    # Check if comments are allowed for this post
    if not post.allow_comments:
        messages.error(request, 'Comments are not allowed for this post.')
        return redirect('blog:detail', slug=slug)
    
    # Rate limiting
    client_ip = get_client_ip(request)
    cache_key = f'comment_rate_limit_{client_ip}'
    last_comment_time = cache.get(cache_key)
    
    if last_comment_time:
        time_diff = time.time() - last_comment_time
        if time_diff < 60:  # 1 minute rate limit
            messages.error(request, 'Please wait before submitting another comment.')
            return redirect('blog:detail', slug=slug)
    
    form = CommentForm(request.POST)
    
    if form.is_valid():
        reply = form.save(commit=False)
        reply.post = post
        reply.parent = parent_comment
        reply.ip_address = client_ip
        reply.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        reply.save()
        
        # Set rate limiting cache
        cache.set(cache_key, time.time(), 300)  # 5 minutes cache
        
        # Send notification to post author (async)
        send_comment_notification.delay(reply.id)
        
        messages.success(request, 'Your reply has been submitted and is awaiting moderation.')
        return redirect('blog:detail', slug=slug)
    
    else:
        # If form is invalid, redirect back with errors
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field.replace("_", " ").title()}: {error}')
        
        return redirect('blog:detail', slug=slug)


@require_POST
def track_social_share(request, slug):
    """
    Track social media share events via AJAX.
    """
    post = get_object_or_404(Post, slug=slug, status='published')
    platform = request.POST.get('platform')
    
    if not platform:
        return JsonResponse({'error': 'Platform is required'}, status=400)
    
    try:
        social_share = SocialShareService.track_share(post, platform)
        return JsonResponse({
            'success': True,
            'platform': platform,
            'share_count': social_share.share_count,
            'total_shares': SocialShareService.get_total_shares(post)
        })
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Failed to track share'}, status=500)


def _highlight_search_results(posts_queryset, query):
    """
    Add search result highlighting to post titles and excerpts.
    Returns a dictionary mapping post IDs to highlighted content.
    """
    highlighted_posts = {}
    
    if not query:
        return highlighted_posts
    
    # Create regex pattern for case-insensitive highlighting
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    
    for post in posts_queryset:
        highlighted_data = {}
        
        # Highlight in title
        if pattern.search(post.title):
            highlighted_data['title'] = pattern.sub(
                lambda m: f'<mark class="search-highlight">{m.group()}</mark>',
                post.title
            )
        
        # Highlight in excerpt
        if post.excerpt and pattern.search(post.excerpt):
            highlighted_data['excerpt'] = pattern.sub(
                lambda m: f'<mark class="search-highlight">{m.group()}</mark>',
                post.excerpt
            )
        
        # Highlight in tag names
        highlighted_tags = []
        for tag in post.tags.all():
            if pattern.search(tag.name):
                highlighted_tag_name = pattern.sub(
                    lambda m: f'<mark class="search-highlight">{m.group()}</mark>',
                    tag.name
                )
                highlighted_tags.append({
                    'id': tag.id,
                    'name': highlighted_tag_name,
                    'slug': tag.slug,
                    'color': tag.color
                })
        
        if highlighted_tags:
            highlighted_data['tags'] = highlighted_tags
        
        if highlighted_data:
            highlighted_posts[post.id] = highlighted_data
    
    return highlighted_posts


def _get_category_hierarchy():
    """
    Build a hierarchical structure of categories with their subcategories.
    Returns a list of top-level categories with nested subcategories.
    """
    # Get all categories with post counts
    all_categories = Category.objects.annotate(
        post_count=Count('posts', filter=Q(posts__status='published'))
    ).filter(post_count__gt=0).select_related('parent').order_by('name')
    
    # Build hierarchy
    category_dict = {}
    root_categories = []
    
    # First pass: create category objects
    for category in all_categories:
        category_dict[category.id] = {
            'category': category,
            'subcategories': [],
            'post_count': category.post_count
        }
    
    # Second pass: build hierarchy
    for category in all_categories:
        if category.parent_id:
            # This is a subcategory
            if category.parent_id in category_dict:
                category_dict[category.parent_id]['subcategories'].append(
                    category_dict[category.id]
                )
        else:
            # This is a root category
            root_categories.append(category_dict[category.id])
    
    return root_categories


def _generate_breadcrumbs(category=None, tag=None, query=None):
    """
    Generate breadcrumb navigation for the current page.
    Returns a list of breadcrumb items.
    """
    breadcrumbs = [
        {'name': 'Home', 'url': '/', 'active': False},
        {'name': 'Blog', 'url': '/blog/', 'active': not any([category, tag, query])}
    ]
    
    if category:
        # Add parent categories if they exist
        parent_categories = []
        current_category = category
        
        while current_category.parent:
            parent_categories.insert(0, current_category.parent)
            current_category = current_category.parent
        
        # Add parent categories to breadcrumbs
        for parent in parent_categories:
            breadcrumbs.append({
                'name': parent.name,
                'url': f'/blog/category/{parent.slug}/',
                'active': False
            })
        
        # Add current category
        breadcrumbs.append({
            'name': category.name,
            'url': f'/blog/category/{category.slug}/',
            'active': not tag and not query
        })
    
    if tag:
        breadcrumbs.append({
            'name': f'Tag: {tag.name}',
            'url': f'/blog/tag/{tag.slug}/',
            'active': not query
        })
    
    if query:
        breadcrumbs.append({
            'name': f'Search: {query}',
            'url': f'/blog/?q={query}',
            'active': True
        })
    
    return breadcrumbs


def advanced_search(request):
    """
    Handle advanced search requests via AJAX.
    Returns JSON response with search results and filters.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Only GET requests allowed'}, status=405)
    
    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category')
    tag_slug = request.GET.get('tag')
    date_range = request.GET.get('date_range')
    sort_by = request.GET.get('sort', 'newest')
    
    # Start with published posts
    posts_list = Post.objects.filter(status='published').select_related('author').prefetch_related('categories', 'tags')
    
    # Apply filters
    if query:
        search_query = Q(title__icontains=query) | Q(excerpt__icontains=query) | Q(content__icontains=query) | Q(tags__name__icontains=query) | Q(categories__name__icontains=query)
        posts_list = posts_list.filter(search_query).distinct()
    
    if category_slug and category_slug != 'all':
        try:
            category = Category.objects.get(slug=category_slug)
            posts_list = posts_list.filter(categories=category)
        except Category.DoesNotExist:
            pass
    
    if tag_slug and tag_slug != 'all':
        try:
            tag = Tag.objects.get(slug=tag_slug)
            posts_list = posts_list.filter(tags=tag)
        except Tag.DoesNotExist:
            pass
    
    # Date range filtering
    if date_range and date_range != 'all':
        now = timezone.now()
        if date_range == 'week':
            start_date = now - timedelta(days=7)
            posts_list = posts_list.filter(created_at__gte=start_date)
        elif date_range == 'month':
            start_date = now - timedelta(days=30)
            posts_list = posts_list.filter(created_at__gte=start_date)
        elif date_range == 'year':
            start_date = now - timedelta(days=365)
            posts_list = posts_list.filter(created_at__gte=start_date)
    
    # Sorting
    if sort_by == 'oldest':
        posts_list = posts_list.order_by('created_at')
    elif sort_by == 'popular':
        posts_list = posts_list.order_by('-view_count', '-created_at')
    elif sort_by == 'title':
        posts_list = posts_list.order_by('title')
    else:  # newest
        posts_list = posts_list.order_by('-created_at')
    
    # Limit results for AJAX response
    posts_list = posts_list[:20]
    
    # Prepare response data
    results = []
    for post in posts_list:
        post_data = {
            'id': post.id,
            'title': post.title,
            'slug': post.slug,
            'excerpt': post.excerpt[:200] if post.excerpt else '',
            'created_at': post.created_at.strftime('%B %d, %Y'),
            'author': post.author.get_full_name() or post.author.username,
            'view_count': post.view_count,
            'categories': [{'name': cat.name, 'slug': cat.slug} for cat in post.categories.all()],
            'tags': [{'name': tag.name, 'slug': tag.slug, 'color': tag.color} for tag in post.tags.all()],
            'url': f'/blog/{post.slug}/',
            'featured_image': post.featured_image.url if post.featured_image else None,
        }
        results.append(post_data)
    
    return JsonResponse({
        'results': results,
        'total_count': len(results),
        'query': query,
        'filters': {
            'category': category_slug,
            'tag': tag_slug,
            'date_range': date_range,
            'sort': sort_by,
        }
    })


def get_search_suggestions(request):
    """
    Provide search suggestions for autocomplete functionality.
    """
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    suggestions = []
    
    # Get matching post titles
    posts = Post.objects.filter(
        status='published',
        title__icontains=query
    ).values_list('title', flat=True)[:5]
    
    for title in posts:
        suggestions.append({
            'type': 'post',
            'text': title,
            'category': 'Posts'
        })
    
    # Get matching tags
    tags = Tag.objects.filter(
        name__icontains=query
    ).annotate(
        post_count=Count('posts', filter=Q(posts__status='published'))
    ).filter(post_count__gt=0).values_list('name', flat=True)[:3]
    
    for tag_name in tags:
        suggestions.append({
            'type': 'tag',
            'text': tag_name,
            'category': 'Tags'
        })
    
    # Get matching categories
    categories = Category.objects.filter(
        name__icontains=query
    ).annotate(
        post_count=Count('posts', filter=Q(posts__status='published'))
    ).filter(post_count__gt=0).values_list('name', flat=True)[:3]
    
    for cat_name in categories:
        suggestions.append({
            'type': 'category',
            'text': cat_name,
            'category': 'Categories'
        })
    
    return JsonResponse({'suggestions': suggestions[:10]})


def author_detail(request, username):
    """
    Display author profile page with their posts and bio information.
    """
    author = get_object_or_404(User, username=username)
    author_profile = AuthorService.get_author_profile(author)
    
    # Check if author profile is active
    if not author_profile.is_active:
        messages.error(request, 'Author profile not found.')
        return redirect('blog:list')
    
    # Get author's published posts
    posts_list = AuthorService.get_author_posts(author, status='published')
    
    # Pagination
    page_size = int(request.GET.get('per_page', 10))
    if page_size not in [5, 10, 20, 50]:
        page_size = 10
    
    paginator = Paginator(posts_list, page_size)
    page_number = request.GET.get('page')
    
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    
    # Get author statistics
    author_stats = AuthorService.get_author_stats(author)
    
    # Get social links
    social_links = AuthorService.get_author_social_links(author)
    
    # Generate breadcrumbs
    breadcrumbs = [
        {'name': 'Home', 'url': '/', 'active': False},
        {'name': 'Blog', 'url': '/blog/', 'active': False},
        {'name': 'Authors', 'url': '/blog/authors/', 'active': False},
        {'name': author_profile.get_display_name(), 'url': f'/blog/author/{username}/', 'active': True}
    ]
    
    context = {
        'author': author,
        'author_profile': author_profile,
        'posts': posts,
        'author_stats': author_stats,
        'social_links': social_links,
        'breadcrumbs': breadcrumbs,
        'title': f'{author_profile.get_display_name()} - Author Profile',
        'meta_details': author_profile.get_short_bio() or f'Posts by {author_profile.get_display_name()}',
    }
    
    return render(request, 'blog/author_detail.html', context)


def author_list(request):
    """
    Display a list of all active authors with their profiles.
    """
    # Get all active authors
    authors = AuthorService.get_all_active_authors()
    
    # Search functionality
    query = request.GET.get('q', '').strip()
    if query:
        authors = AuthorService.search_authors(query)
    
    # Filter by author type
    author_type = request.GET.get('type', 'all')
    if author_type == 'guest':
        authors = authors.filter(author_profile__is_guest_author=True)
    elif author_type == 'staff':
        authors = authors.filter(author_profile__is_guest_author=False)
    
    # Pagination
    page_size = int(request.GET.get('per_page', 12))
    if page_size not in [6, 12, 24, 48]:
        page_size = 12
    
    paginator = Paginator(authors, page_size)
    page_number = request.GET.get('page')
    
    try:
        authors_page = paginator.page(page_number)
    except PageNotAnInteger:
        authors_page = paginator.page(1)
    except EmptyPage:
        authors_page = paginator.page(paginator.num_pages)
    
    # Generate breadcrumbs
    breadcrumbs = [
        {'name': 'Home', 'url': '/', 'active': False},
        {'name': 'Blog', 'url': '/blog/', 'active': False},
        {'name': 'Authors', 'url': '/blog/authors/', 'active': True}
    ]
    
    # Filter options
    filter_options = {
        'author_types': [
            ('all', 'All Authors'),
            ('staff', 'Staff Authors'),
            ('guest', 'Guest Authors'),
        ]
    }
    
    context = {
        'authors': authors_page,
        'query': query,
        'breadcrumbs': breadcrumbs,
        'filter_options': filter_options,
        'current_filters': {
            'type': author_type,
            'per_page': page_size,
        },
        'total_results': authors_page.paginator.count if authors_page else 0,
        'title': 'Authors - Digital Codex',
        'meta_details': 'Meet our talented authors and contributors',
    }
    
    return render(request, 'blog/author_list.html', context)


def author_posts_by_category(request, username, category_slug):
    """
    Display author's posts filtered by category.
    """
    author = get_object_or_404(User, username=username)
    category = get_object_or_404(Category, slug=category_slug)
    author_profile = AuthorService.get_author_profile(author)
    
    # Check if author profile is active
    if not author_profile.is_active:
        messages.error(request, 'Author profile not found.')
        return redirect('blog:list')
    
    # Get author's posts in this category
    posts_list = author.blog_posts.filter(
        status='published',
        categories=category
    ).order_by('-created_at')
    
    # Pagination
    page_size = int(request.GET.get('per_page', 10))
    if page_size not in [5, 10, 20, 50]:
        page_size = 10
    
    paginator = Paginator(posts_list, page_size)
    page_number = request.GET.get('page')
    
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    
    # Generate breadcrumbs
    breadcrumbs = [
        {'name': 'Home', 'url': '/', 'active': False},
        {'name': 'Blog', 'url': '/blog/', 'active': False},
        {'name': 'Authors', 'url': '/blog/authors/', 'active': False},
        {'name': author_profile.get_display_name(), 'url': f'/blog/author/{username}/', 'active': False},
        {'name': category.name, 'url': f'/blog/author/{username}/category/{category_slug}/', 'active': True}
    ]
    
    context = {
        'author': author,
        'author_profile': author_profile,
        'category': category,
        'posts': posts,
        'breadcrumbs': breadcrumbs,
        'title': f'{author_profile.get_display_name()} - {category.name} Posts',
        'meta_details': f'Posts by {author_profile.get_display_name()} in {category.name}',
    }
    
    return render(request, 'blog/author_posts_by_category.html', context)

# Multimedia Views

@csrf_protect
def upload_media(request, post_id):
    """
    Handle multimedia upload for blog posts with drag-and-drop support.
    """
    post = get_object_or_404(Post, id=post_id)
    
    # Check permissions (only post author or superuser can upload media)
    if not (request.user == post.author or request.user.is_superuser):
        messages.error(request, 'You do not have permission to upload media for this post.')
        return redirect('blog:detail', slug=post.slug)
    
    if request.method == 'POST':
        form = MediaUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            media_type = form.cleaned_data['media_type']
            title = form.cleaned_data['title']
            description = form.cleaned_data['description']
            alt_text = form.cleaned_data['alt_text']
            
            try:
                if media_type == 'image':
                    # Handle single image upload
                    image_file = form.cleaned_data['image_file']
                    processed_images = multimedia_service.process_image_upload(image_file)
                    
                    # Create MediaItem
                    media_item = MediaItem.objects.create(
                        post=post,
                        media_type='image',
                        title=title,
                        description=description,
                        alt_text=alt_text,
                        original_image=image_file,
                        file_size=image_file.size,
                    )
                    
                    # Save processed images
                    if 'thumbnail' in processed_images:
                        media_item.thumbnail_image.name = processed_images['thumbnail']
                    if 'medium' in processed_images:
                        media_item.medium_image.name = processed_images['medium']
                    if 'large' in processed_images:
                        media_item.large_image.name = processed_images['large']
                    
                    media_item.save()
                    messages.success(request, 'Image uploaded and processed successfully!')
                
                elif media_type == 'gallery':
                    # Handle gallery upload
                    gallery_files = request.FILES.getlist('gallery_files')
                    gallery_data = []
                    
                    for i, image_file in enumerate(gallery_files):
                        processed_images = multimedia_service.process_image_upload(image_file)
                        gallery_data.append({
                            'id': i,
                            'original': image_file.name,
                            'processed': processed_images,
                            'alt': f'{title} - Image {i + 1}' if title else f'Gallery Image {i + 1}'
                        })
                    
                    # Create MediaItem for gallery
                    media_item = MediaItem.objects.create(
                        post=post,
                        media_type='gallery',
                        title=title,
                        description=description,
                        alt_text=alt_text,
                        gallery_images=gallery_data,
                    )
                    
                    messages.success(request, f'Gallery with {len(gallery_files)} images uploaded successfully!')
                
                elif media_type == 'video':
                    # Handle video embed
                    video_url = form.cleaned_data['video_url']
                    video_info = multimedia_service.extract_video_embed(video_url)
                    
                    if video_info:
                        media_item = MediaItem.objects.create(
                            post=post,
                            media_type='video',
                            title=title or video_info.get('title', ''),
                            description=description,
                            video_url=video_url,
                            video_platform=video_info['platform'],
                            video_id=video_info['video_id'],
                            video_embed_url=video_info['embed_url'],
                            video_thumbnail=video_info['thumbnail_url'],
                        )
                        
                        messages.success(request, 'Video embedded successfully!')
                    else:
                        messages.error(request, 'Failed to process video URL.')
                
                return redirect('blog:detail', slug=post.slug)
                
            except Exception as e:
                messages.error(request, f'Error uploading media: {str(e)}')
        
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field.replace("_", " ").title()}: {error}')
    
    else:
        form = MediaUploadForm()
    
    context = {
        'form': form,
        'post': post,
        'title': f'Upload Media - {post.title}',
    }
    return render(request, 'blog/upload_media.html', context)


def create_image_gallery(request, post_id):
    """
    Create an image gallery for a blog post.
    """
    post = get_object_or_404(Post, id=post_id)
    
    # Check permissions
    if not (request.user == post.author or request.user.is_superuser):
        messages.error(request, 'You do not have permission to create galleries for this post.')
        return redirect('blog:detail', slug=post.slug)
    
    if request.method == 'POST':
        form = ImageGalleryForm(request.POST, request.FILES)
        
        if form.is_valid():
            title = form.cleaned_data['title']
            description = form.cleaned_data['description']
            images = request.FILES.getlist('images')
            
            try:
                # Process all images
                gallery_data = []
                for i, image_file in enumerate(images):
                    processed_images = multimedia_service.process_image_upload(image_file)
                    
                    gallery_item = {
                        'id': i,
                        'title': f'{title} - Image {i + 1}',
                        'original': image_file.name,
                        'processed': processed_images,
                        'alt': f'{title} - Image {i + 1}',
                        'order': i,
                    }
                    gallery_data.append(gallery_item)
                
                # Create MediaItem for gallery
                media_item = MediaItem.objects.create(
                    post=post,
                    media_type='gallery',
                    title=title,
                    description=description,
                    gallery_images=gallery_data,
                )
                
                messages.success(request, f'Gallery "{title}" created with {len(images)} images!')
                return redirect('blog:detail', slug=post.slug)
                
            except Exception as e:
                messages.error(request, f'Error creating gallery: {str(e)}')
        
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field.replace("_", " ").title()}: {error}')
    
    else:
        form = ImageGalleryForm()
    
    context = {
        'form': form,
        'post': post,
        'title': f'Create Gallery - {post.title}',
    }
    return render(request, 'blog/create_gallery.html', context)


def embed_video(request, post_id):
    """
    Embed a video from YouTube or Vimeo into a blog post.
    """
    post = get_object_or_404(Post, id=post_id)
    
    # Check permissions
    if not (request.user == post.author or request.user.is_superuser):
        messages.error(request, 'You do not have permission to embed videos for this post.')
        return redirect('blog:detail', slug=post.slug)
    
    if request.method == 'POST':
        form = VideoEmbedForm(request.POST)
        
        if form.is_valid():
            video_url = form.cleaned_data['video_url']
            title = form.cleaned_data['title']
            description = form.cleaned_data['description']
            
            try:
                video_info = multimedia_service.extract_video_embed(video_url)
                
                if video_info:
                    media_item = MediaItem.objects.create(
                        post=post,
                        media_type='video',
                        title=title or f'{video_info["platform"].title()} Video',
                        description=description,
                        video_url=video_url,
                        video_platform=video_info['platform'],
                        video_id=video_info['video_id'],
                        video_embed_url=video_info['embed_url'],
                        video_thumbnail=video_info['thumbnail_url'],
                    )
                    
                    messages.success(request, f'{video_info["platform"].title()} video embedded successfully!')
                    return redirect('blog:detail', slug=post.slug)
                else:
                    messages.error(request, 'Failed to extract video information from URL.')
                    
            except Exception as e:
                messages.error(request, f'Error embedding video: {str(e)}')
        
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field.replace("_", " ").title()}: {error}')
    
    else:
        form = VideoEmbedForm()
    
    context = {
        'form': form,
        'post': post,
        'title': f'Embed Video - {post.title}',
    }
    return render(request, 'blog/embed_video.html', context)


def manage_media(request, post_id):
    """
    Manage all media items for a blog post.
    """
    post = get_object_or_404(Post, id=post_id)
    
    # Check permissions
    if not (request.user == post.author or request.user.is_superuser):
        messages.error(request, 'You do not have permission to manage media for this post.')
        return redirect('blog:detail', slug=post.slug)
    
    # Get all media items for this post
    media_items = MediaItem.objects.filter(post=post).order_by('order', 'created_at')
    
    context = {
        'post': post,
        'media_items': media_items,
        'title': f'Manage Media - {post.title}',
    }
    return render(request, 'blog/manage_media.html', context)


@require_POST
def delete_media(request, media_id):
    """
    Delete a media item.
    """
    media_item = get_object_or_404(MediaItem, id=media_id)
    post = media_item.post
    
    # Check permissions
    if not (request.user == post.author or request.user.is_superuser):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        # Delete associated files
        if media_item.original_image:
            media_item.original_image.delete(save=False)
        if media_item.thumbnail_image:
            media_item.thumbnail_image.delete(save=False)
        if media_item.medium_image:
            media_item.medium_image.delete(save=False)
        if media_item.large_image:
            media_item.large_image.delete(save=False)
        
        media_item.delete()
        
        return JsonResponse({'success': True, 'message': 'Media item deleted successfully'})
        
    except Exception as e:
        return JsonResponse({'error': f'Failed to delete media: {str(e)}'}, status=500)


@require_POST
def update_media_order(request, post_id):
    """
    Update the display order of media items via AJAX.
    """
    post = get_object_or_404(Post, id=post_id)
    
    # Check permissions
    if not (request.user == post.author or request.user.is_superuser):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        import json
        media_order = json.loads(request.body)
        
        for item in media_order:
            media_id = item.get('id')
            order = item.get('order')
            
            if media_id and order is not None:
                MediaItem.objects.filter(id=media_id, post=post).update(order=order)
        
        return JsonResponse({'success': True, 'message': 'Media order updated successfully'})
        
    except Exception as e:
        return JsonResponse({'error': f'Failed to update order: {str(e)}'}, status=500)


def get_responsive_image(request, media_id, size):
    """
    Get responsive image URL for a specific size.
    """
    media_item = get_object_or_404(MediaItem, id=media_id, media_type='image')
    
    size_mapping = {
        'thumbnail': media_item.thumbnail_image,
        'medium': media_item.medium_image,
        'large': media_item.large_image,
        'original': media_item.original_image,
    }
    
    image_field = size_mapping.get(size)
    
    if image_field and image_field.name:
        return JsonResponse({
            'url': image_field.url,
            'width': media_item.width if size == 'original' else None,
            'height': media_item.height if size == 'original' else None,
        })
    else:
        return JsonResponse({'error': 'Image size not available'}, status=404)


def gallery_lightbox(request, media_id):
    """
    Get gallery data for lightbox display.
    """
    media_item = get_object_or_404(MediaItem, id=media_id, media_type='gallery')
    
    try:
        gallery_data = multimedia_service.create_image_gallery(media_item.gallery_images)
        
        return JsonResponse({
            'title': media_item.title,
            'description': media_item.description,
            'images': gallery_data,
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Failed to load gallery: {str(e)}'}, status=500)


@require_POST
def optimize_images(request, post_id):
    """
    Optimize all images for a blog post.
    """
    post = get_object_or_404(Post, id=post_id)
    
    # Check permissions
    if not (request.user == post.author or request.user.is_superuser):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        media_items = MediaItem.objects.filter(post=post, media_type='image')
        optimized_count = 0
        
        for media_item in media_items:
            if media_item.original_image:
                try:
                    optimized_path = multimedia_service.optimize_image_for_web(
                        media_item.original_image.name
                    )
                    optimized_count += 1
                except Exception as e:
                    continue
        
        return JsonResponse({
            'success': True,
            'message': f'Optimized {optimized_count} images',
            'optimized_count': optimized_count
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Failed to optimize images: {str(e)}'}, status=500)