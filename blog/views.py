from django.shortcuts import render, get_object_or_404
from django.db.models import F, Q
from .models import Post, Category

def blog_list(request, category_slug=None):
    """
    Displays a list of published blog posts.
    Can be filtered by a category slug and handles search queries.
    """
    category = None
    posts = Post.objects.filter(status='published')
    
    # Filter by category if a category_slug is provided in the URL
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        posts = posts.filter(categories=category)
        
    # Handle search query from the search input in the template
    query = request.GET.get('q')
    if query:
        posts = posts.filter(
            Q(title__icontains=query) | 
            Q(excerpt__icontains=query) |
            Q(content__icontains=query)
        ).distinct()

    all_categories = Category.objects.all()

    context = {
        'posts': posts,
        'all_categories': all_categories,
        'current_category': category,
        'title': f'Blog - {category.name}' if category else 'Blog - Digital Codex',
        'meta_details': f'Posts in the category {category.name}' if category else 'Read the latest articles and insights from The Digital Architect.',
    }
    return render(request, 'blog/blog_list.html', context)

def blog_detail(request, slug):
    """
    Displays a single blog post and increments its view count.
    """
    post = get_object_or_404(Post, slug=slug, status='published')
    
    # Increment the view count efficiently
    Post.objects.filter(pk=post.pk).update(view_count=F('view_count') + 1)
    post.refresh_from_db() # Get the updated count
    
    # Get up to 3 related posts from the same categories
    related_posts = Post.objects.filter(
        status='published', 
        categories__in=post.categories.all()
    ).exclude(pk=post.pk).distinct()[:3]

    context = {
        'post': post,
        'related_posts': related_posts,
        'title': post.title,
        'meta_details': post.excerpt or post.content[:160],
    }
    return render(request, 'blog/blog_detail.html', context)

