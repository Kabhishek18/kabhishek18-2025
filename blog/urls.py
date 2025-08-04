# blog/urls.py
from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.blog_list, name='list'),
    path('search/', views.advanced_search, name='advanced_search'),
    path('search/suggestions/', views.get_search_suggestions, name='search_suggestions'),
    path('authors/', views.author_list, name='author_list'),
    path('author/<str:username>/', views.author_detail, name='author_detail'),
    path('author/<str:username>/category/<slug:category_slug>/', views.author_posts_by_category, name='author_posts_by_category'),
    path('category/<slug:category_slug>/', views.blog_list, name='list_by_category'),
    path('tag/<slug:tag_slug>/', views.blog_list, name='list_by_tag'),
    path('category/<slug:category_slug>/tag/<slug:tag_slug>/', views.blog_list, name='list_by_category_and_tag'),
    path('subscribe/', views.subscribe_newsletter, name='subscribe_newsletter'),
    path('confirm/<str:token>/', views.confirm_subscription, name='confirm_subscription'),
    path('unsubscribe/<str:token>/', views.unsubscribe_newsletter, name='unsubscribe'),
    path('<slug:slug>/comment/', views.submit_comment, name='submit_comment'),
    path('<slug:slug>/reply/<int:comment_id>/', views.submit_reply, name='submit_reply'),
    path('<slug:slug>/share/', views.track_social_share, name='track_social_share'),
    
    # Multimedia URLs
    path('post/<int:post_id>/upload-media/', views.upload_media, name='upload_media'),
    path('post/<int:post_id>/create-gallery/', views.create_image_gallery, name='create_gallery'),
    path('post/<int:post_id>/embed-video/', views.embed_video, name='embed_video'),
    path('post/<int:post_id>/manage-media/', views.manage_media, name='manage_media'),
    path('post/<int:post_id>/optimize-images/', views.optimize_images, name='optimize_images'),
    path('post/<int:post_id>/update-media-order/', views.update_media_order, name='update_media_order'),
    path('media/<int:media_id>/delete/', views.delete_media, name='delete_media'),
    path('media/<int:media_id>/image/<str:size>/', views.get_responsive_image, name='responsive_image'),
    path('media/<int:media_id>/gallery/', views.gallery_lightbox, name='gallery_lightbox'),
    
    path('<slug:slug>/', views.blog_detail, name='detail'),
]
