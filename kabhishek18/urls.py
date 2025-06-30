# kabhishek18/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

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

# Define the primary URL patterns first
urlpatterns = [
    path('open/admin/', admin.site.urls),
    path('blog/', include('blog.urls', namespace='blog')),
    path('api/', include('api.urls')),
]

# Add Swagger URLs only when in DEBUG mode
if settings.DEBUG:
    urlpatterns += [
        path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
        path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    ]
    # Also add media file serving for development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# IMPORTANT: The "catch-all" pattern for the core app must be the last one added.
urlpatterns += [
    path('', include('core.urls')),
]