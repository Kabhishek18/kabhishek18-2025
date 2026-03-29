# kabhishek18/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.views.generic.base import TemplateView
from core.views import sitemap_view

schema_view = get_schema_view(
   openapi.Info(
      title="KAbhishek18 API",
      default_version='v1',
      description="API documentation for the KAbhishek18 project",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="developer@kabhishek18.com"),
      license=openapi.License(name="MIT License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

# Define the primary URL patterns with specific prefixes FIRST

import os
from django.http import Http404
from django.views.static import serve
from core.theme import get_active_theme

import os
from django.http import Http404, FileResponse, HttpResponse
from core.theme import get_active_theme
import mimetypes

def serve_theme_static(request, path, prefix=''):
    active_theme = get_active_theme()
    
    if active_theme == 'others_3d':
        document_root = os.path.join(settings.BASE_DIR, 'Others-3d', 'dist')
    elif active_theme == 'portfolio_3d':
        document_root = os.path.join(settings.BASE_DIR, 'portfolio-3d', 'dist')
    elif active_theme == 'portfolio':
        document_root = os.path.join(settings.BASE_DIR, 'portfolio', 'out')
    else:
        document_root = os.path.join(settings.BASE_DIR, 'Others-3d', 'dist')
        
    serve_path = f"{prefix}/{path}" if prefix else path
    full_path = os.path.join(document_root, serve_path)
    
    if os.path.exists(full_path) and os.path.isfile(full_path):
        content_type, encoding = mimetypes.guess_type(full_path)
        content_type = content_type or 'application/octet-stream'
        return FileResponse(open(full_path, 'rb'), content_type=content_type)
    
    raise Http404(f"File not found: {serve_path}")

urlpatterns = [
    # Add these lines
    path(
        "sitemap.xml",
        sitemap_view,
        name="sitemap",
    ),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots",
    ),
    path(
        "security.txt",
        TemplateView.as_view(template_name="security.txt", content_type="text/plain"),
        name="security",
    ),
    path(
        "humans.txt",
        TemplateView.as_view(template_name="humans.txt", content_type="text/plain"),
        name="humans",
    ),
    path(
        "ads.txt",
        TemplateView.as_view(template_name="ads.txt", content_type="text/plain"),
        name="ads",
    ),

    # Static App Assets mappings based on Active Theme
    # Automatically match directories explicitly known from SPAs (Vite and Next.js)
    re_path(r'^(?P<prefix>(assets|_next|models|images|draco|fonts))/(?P<path>.*)$', serve_theme_static),
    re_path(r'^(?P<path>.*\.webmanifest|.*\.png|.*\.ico|.*\.svg|.*\.json|.*\.pdf|.*\.glb|.*\.gltf)$', serve_theme_static, {'prefix': ''}),
    
    # Admin URLs
    path('open/admin/', admin.site.urls),
    
    # API URLs - specific prefix with versioning
    path('api/v1/', include('api.urls')),
    
    # Roadmap/Resume Parser API URLs
    path('api/roadmap/', include('roadmap.urls')),
    
    # Blog URLs - specific prefix
    path('blog/', include('blog.urls', namespace='blog')),
]

# Add Swagger URLs only when in DEBUG mode
if settings.DEBUG:
    urlpatterns += [
        path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
        path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
        # API schema
        path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    ]
    # Add media file serving for development (static files are served automatically when DEBUG=True)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# IMPORTANT: The "catch-all" pattern for the core app MUST be the LAST one
urlpatterns += [
    path('', include('core.urls')),
]

# Custom error handlers
handler404 = 'core.views.custom_404'
handler500 = 'core.views.custom_500'  # Add this if you have a 500 handler
