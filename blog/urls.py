# blog/urls.py
from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.blog_list, name='list'),
    path('category/<slug:category_slug>/', views.blog_list, name='list_by_category'),
    path('subscribe/', views.subscribe_newsletter, name='subscribe_newsletter'),
    path('<slug:slug>/', views.blog_detail, name='detail'),
]
