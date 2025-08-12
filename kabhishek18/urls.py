# kabhishek18/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.views.generic.base import TemplateView

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
urlpatterns = [
    # Admin URLs
    path('open/admin/', admin.site.urls),
    
    # API URLs - specific prefix with versioning
    path('api/v1/', include('api.urls')),
    
    # Blog URLs - specific prefix
    path('blog/', include('blog.urls', namespace='blog')),

    # Add these lines
    path(
        "sitemap.xml",
        TemplateView.as_view(template_name="sitemap.xml", content_type="application/xml"),
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
]

# Add Swagger URLs only when in DEBUG mode
if settings.DEBUG:
    urlpatterns += [
        path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
        path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
        # API schema
        path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    ]
    # Add media file serving for development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# IMPORTANT: The "catch-all" pattern for the core app MUST be the LAST one
urlpatterns += [
    path('', include('core.urls')),
]

# Custom error handlers
handler404 = 'core.views.custom_404'
handler500 = 'core.views.custom_500'  # Add this if you have a 500 handler