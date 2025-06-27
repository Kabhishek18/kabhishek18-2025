from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import F, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from .models import Post, Category, NewsletterSubscriber
from .forms import NewsletterSubscriptionForm

def blog_list(request, category_slug=None):
    """
    Displays a list of published blog posts with search, filtering, and pagination.
    """
    category = None
    posts_list = Post.objects.filter(status='published').order_by('-created_at')
    
    # Filter by category
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        posts_list = posts_list.filter(categories=category)
        
    # Handle search query
    query = request.GET.get('q')
    if query:
        posts_list = posts_list.filter(
            Q(title__icontains=query) | 
            Q(excerpt__icontains=query) |
            Q(content__icontains=query)
        ).distinct()

    # Pagination - Show 6 posts per page
    paginator = Paginator(posts_list, 9)
    page_number = request.GET.get('page')
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        posts = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        posts = paginator.page(paginator.num_pages)

    all_categories = Category.objects.all()
    newsletter_form = NewsletterSubscriptionForm() # Add form to context

    context = {
        'posts': posts,
        'all_categories': all_categories,
        'current_category': category,
        'newsletter_form': newsletter_form,
        'title': f'Blog - {category.name}' if category else 'Blog - Digital Codex',
        'meta_details': f'Posts in category {category.name}' if category else 'Read the latest articles and insights.',
    }
    return render(request, 'blog/blog_list.html', context)

def blog_detail(request, slug):
    """
    Displays a single blog post and increments its view count.
    """
    post = get_object_or_404(Post, slug=slug, status='published')
    
    # Increment the view count
    Post.objects.filter(pk=post.pk).update(view_count=F('view_count') + 1)
    post.refresh_from_db() 
    
    related_posts = Post.objects.filter(
        status='published', 
        categories__in=post.categories.all()
    ).exclude(pk=post.pk).distinct()[:3]

    context = {
        'post': post,
        'related_posts': related_posts,
        'title': post.title,
        'meta_data': post.meta_data,
        'meta_details': post.excerpt or post.content[:160],
    }
    return render(request, 'blog/blog_detail.html', context)


def subscribe_newsletter(request):
    """
    Handles newsletter subscription form submission.
    """
    if request.method == 'POST':
        form = NewsletterSubscriptionForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            # Prevent duplicate subscriptions
            if not NewsletterSubscriber.objects.filter(email=email).exists():
                NewsletterSubscriber.objects.create(email=email)
                messages.success(request, 'Thank you for subscribing to the newsletter!')
            else:
                messages.warning(request, 'This email address is already subscribed.')
    
    # Redirect back to the previous page, or the blog list as a fallback
    return redirect(request.META.get('HTTP_REFERER', 'blog:list'))
