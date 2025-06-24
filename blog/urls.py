from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    # URL for the list of all blog posts, e.g., /blog/
    path('', views.blog_list, name='list'),
    
    # NEW: URL for filtering posts by a category, e.g., /blog/category/ai-ml/
    path('category/<slug:category_slug>/', views.blog_list, name='list_by_category'),
    
    # URL for a single blog post, e.g., /blog/neural-networks-guide/
    path('<slug:slug>/', views.blog_detail, name='detail'),
]
