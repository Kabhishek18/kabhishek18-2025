import os
from dotenv import load_dotenv
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

# Load environment variables from .env file
load_dotenv()
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Application definition

INSTALLED_APPS = [
    "unfold",  # before django.contrib.admin
    "unfold.contrib.filters",  # optional, if special filters are needed
    "unfold.contrib.forms",  # optional, if special form elements are needed
    "unfold.contrib.inlines",  # optional, if special inlines are needed
    "unfold.contrib.import_export",  # optional, if django-import-export package is used
    "unfold.contrib.guardian",  # optional, if django-guardian package is used
    "unfold.contrib.simple_history",  # optional, if django-simple-history package is used

    'ckeditor',
    'ckeditor_uploader',     
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #celery
    'django_celery_beat',
    'django_celery_results',
    # Drf
    'rest_framework',
    'drf_yasg',
    #Custom Modules
    'users',
    'core',
    'blog',
    'api',
    'site_files'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'blog.middleware.SecurityHeadersMiddleware',
    'blog.middleware.RateLimitMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'blog.middleware.CacheControlMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'blog.middleware.CSRFEnhancementMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'blog.middleware.ContentSecurityMiddleware',
    'blog.middleware.CommentSpamProtectionMiddleware',
    'blog.middleware.PerformanceMonitoringMiddleware',
    'blog.middleware.RequestLoggingMiddleware',
]

ROOT_URLCONF = 'kabhishek18.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.debug',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'kabhishek18.wsgi.application'
APPEND_SLASH = True


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
# In your project's settings.py file
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('MYSQL_DATABASE'),
        'USER': os.getenv('MYSQL_USER'),
        'PASSWORD': os.getenv('MYSQL_PASSWORD'),  # your MySQL root password
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
        },
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Add logging for URL debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'django_debug.log',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'core.views': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Custom error handling
USE_L10N = True
USE_I18N = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# settings.py

UNFOLD = {
    # Site title
    "SITE_TITLE": "Kumar Abhishek",
    # Header title
    "SITE_HEADER": "Kabhishek18",
    "SITE_SUBHEADER": "THE DIGITAL ARCHITECT",

    # URL to a logo image, must be in your static files
    "SITE_LOGO": {
        "url": "web-app-manifest-512x512.png",  # Example: "path/to/your/logo.svg"
        "alt": "Kabhishek18 Logo",
    },
    
    # A link to a favicon file, must be in your static files
    "SITE_FAVICON": {
        "url": "apple-touch-icon.png", # Example: "path/to/your/favicon.ico"
        "alt": "Kabhishek18 Icon",
    },

    "SITE_DROPDOWN": [
        {
            "icon": "home",
            "title": _("Home Page"),
            "link": "https://kabhishek18.com",
        },
    ],
    "SITE_URL": "/",
    "SITE_SYMBOL": "home",  # symbol from icon set

    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/png",
            "href": lambda request: static("favicon-32x32.png"),
        },
    ],
    "SHOW_HISTORY": True, # show/hide "History" button, default: True
    "SHOW_VIEW_ON_SITE": True, # show/hide "View on site" button, default: True
    "SHOW_BACK_BUTTON": True,
    "LOGIN": {
        "image": lambda request: static("login-bg.jpg"),
        "redirect_after": lambda request: reverse_lazy("admin:APP_MODEL_changelist"),
    },
    "EXTENSIONS": {
        "modeltranslation": {
            "flags": {
                "en": "🇬🇧",
                "fr": "🇫🇷",
                "nl": "🇧🇪",
            },
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True, # We will define our own navigation
        "navigation": [
            {
                "title": _("Navigation"),
                "separator": True,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                        # No permission needed, visible to all staff
                    },

                    {
                        "title": _("Users"),
                        "icon": "people",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                     {
                        "title": _("Groups"),
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
            {
                "title": _("Content Management"),
                "separator": True,
                "items": [
                    {
                        "title": _("Pages"),
                        "icon": "article",
                        "link": reverse_lazy("admin:core_page_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Templates"),
                        "icon": "layers",
                        "link": reverse_lazy("admin:core_template_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Components"),
                        "icon": "html",
                        "link": reverse_lazy("admin:core_component_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
            {
                "title": _("Blog Management"),
                "separator": True,
                "items": [
                    {
                        "title": _("Posts"),
                        "icon": "edit_document",
                        "link": reverse_lazy("admin:blog_post_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Categories"),
                        "icon": "folder",
                        "link": reverse_lazy("admin:blog_category_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Tags"),
                        "icon": "tag",
                        "link": reverse_lazy("admin:blog_tag_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Comments"),
                        "icon": "comment",
                        "link": reverse_lazy("admin:blog_comment_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Author Profiles"),
                        "icon": "person",
                        "link": reverse_lazy("admin:blog_authorprofile_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Media Items"),
                        "icon": "image",
                        "link": reverse_lazy("admin:blog_mediaitem_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Newsletter Subscribers"),
                        "icon": "email",
                        "link": reverse_lazy("admin:blog_newslettersubscriber_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Social Shares"),
                        "icon": "share",
                        "link": reverse_lazy("admin:blog_socialshare_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
            {
                "title": _("API Management"),
                "separator": True,
                "items": [
                    {
                        "title": _("API Clients"),
                        "icon": "key",
                        "link": reverse_lazy("admin:api_apiclient_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("API Keys"),
                        "icon": "vpn_key",
                        "link": reverse_lazy("admin:api_apikey_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Usage Logs"),
                        "icon": "analytics",
                        "link": reverse_lazy("admin:api_apiusagelog_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Script Runner"),
                        "icon": "code",
                        "link": reverse_lazy("admin:api_scriptrunner_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
            {
                "title": _("System Monitoring"),
                "separator": True,
                "items": [
                    {
                        "title": _("System Health"),
                        "icon": "health_and_safety",
                        "link": reverse_lazy("core:health_dashboard"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Health Metrics"),
                        "icon": "monitoring",
                        "link": reverse_lazy("admin:core_healthmetric_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("System Alerts"),
                        "icon": "warning",
                        "link": reverse_lazy("admin:core_systemalert_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
        ],
    },
    
    "DASHBOARD_CALLBACK": "core.views.dashboard_callback",

}
CKEDITOR_UPLOAD_PATH = "uploads/"

CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'height': 400,
        'width': '100%',
        'removePlugins': 'stylesheetparser',
        'allowedContent': True,
        'extraAllowedContent': 'iframe[*]',
    },
    'basic': {
        'width': '100%',
        'allowedContent': True,
    },
    'source_only': {
        'toolbar': [['Source']],
        'height': 400,
        'width': '100%',
        'removePlugins': 'stylesheetparser',
        'allowedContent': True,
        'extraPlugins': 'sourcearea',
    }
}

# --- CELERY & CELERY BEAT CONFIGURATION ---
# This section ensures Celery connects to Redis, not RabbitMQ.
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# API Authentication Settings
API_KEY_EXPIRATION_HOURS = int(os.getenv('API_KEY_EXPIRATION_HOURS', 24))
API_RATE_LIMIT_PER_MINUTE = int(os.getenv('API_RATE_LIMIT_PER_MINUTE', 60))
API_RATE_LIMIT_PER_HOUR = int(os.getenv('API_RATE_LIMIT_PER_HOUR', 1000))
API_ENABLE_IP_WHITELIST = os.getenv('API_ENABLE_IP_WHITELIST', 'False').lower() == 'true'
API_REQUIRE_HTTPS = os.getenv('API_REQUIRE_HTTPS', 'True').lower() == 'true'
API_KEY_EXPIRATION_WARNING_HOURS = int(os.getenv('API_KEY_EXPIRATION_WARNING_HOURS', 2))

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'api.authentication.CombinedAPIAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    },
    'EXCEPTION_HANDLER': 'api.exceptions.custom_exception_handler',
}

# Swagger/OpenAPI Documentation Settings
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'ClientAPIKey': {
            'type': 'apiKey',
            'name': 'X-Client-ID',
            'in': 'header'
        },
        'APIKey': {
            'type': 'apiKey',
            'name': 'X-API-Key',
            'in': 'header'
        },
        'EncryptionKey': {
            'type': 'apiKey',
            'name': 'X-Encryption-Key',
            'in': 'header'
        }
    },
    'USE_SESSION_AUTH': False,
    'JSON_EDITOR': True,
    'SUPPORTED_SUBMIT_METHODS': [
        'get',
        'post',
        'put',
        'delete',
        'patch'
    ],
    'OPERATIONS_SORTER': 'alpha',
    'TAGS_SORTER': 'alpha',
    'DOC_EXPANSION': 'none',
    'DEEP_LINKING': True,
    'SHOW_EXTENSIONS': True,
    'SHOW_COMMON_EXTENSIONS': True,
}

REDOC_SETTINGS = {
    'LAZY_RENDERING': False,
    'HIDE_HOSTNAME': False,
    'EXPAND_RESPONSES': 'all',
}

# Cache Configuration for API Rate Limiting
# Use Redis if available, otherwise fall back to database cache
REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1')

try:
    import redis
    # Test Redis connection
    r = redis.from_url(REDIS_URL)
    r.ping()
    # If Redis is available, use it
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'KEY_PREFIX': 'kabhishek18_api',
            'TIMEOUT': 300,
        }
    }
except (ImportError, redis.ConnectionError, redis.RedisError):
    # Fall back to database cache if Redis is not available
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'cache_table',
        }
    }

# API Logging Configuration
LOGGING['loggers'].update({
    'api.authentication': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
        'propagate': False,
    },
    'api.views': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
        'propagate': False,
    },
    'api.utils': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
        'propagate': False,
    },
    'blog.security': {
        'handlers': ['console', 'file'],
        'level': 'WARNING',
        'propagate': False,
    },
    'blog.performance': {
        'handlers': ['console', 'file'],
        'level': 'WARNING',
        'propagate': False,
    },
})

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Session Security
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600  # 1 hour

# CSRF Security
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_USE_SESSIONS = True

# Blog Security Settings
BLOG_RATE_LIMIT_COMMENT_SUBMISSIONS = 5  # per 5 minutes
BLOG_RATE_LIMIT_NEWSLETTER_SUBSCRIPTIONS = 3  # per hour
BLOG_RATE_LIMIT_SEARCH_REQUESTS = 30  # per 5 minutes
BLOG_COMMENT_MAX_LENGTH = 2000
BLOG_COMMENT_MIN_LENGTH = 10
BLOG_ENABLE_SPAM_DETECTION = True
BLOG_SPAM_THRESHOLD = 0.7

# Performance Settings
BLOG_CACHE_TIMEOUT_POPULAR_POSTS = 3600  # 1 hour
BLOG_CACHE_TIMEOUT_FEATURED_POSTS = 1800  # 30 minutes
BLOG_CACHE_TIMEOUT_TAG_CLOUD = 7200  # 2 hours
BLOG_CACHE_TIMEOUT_SEARCH_RESULTS = 900  # 15 minutes
BLOG_VIEW_COUNT_BATCH_SIZE = 10
BLOG_VIEW_COUNT_FLUSH_INTERVAL = 300  # 5 minutes

# CORS Settings (if needed for frontend integration)
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if origin.strip()
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-client-id',
    'x-api-key',
    'x-encryption-key',
]

# Email Configuration
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@kabhishek18.com')

# Site Configuration
SITE_NAME = os.getenv('SITE_NAME', 'Digital Codex')
SITE_URL = os.getenv('SITE_URL', 'http://127.0.0.1:8000')

# LinkedIn
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID","")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET","")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI",SITE_URL)
LINKEDIN_ENCRYPTION_KEY = os.getenv("LINKEDIN_ENCRYPTION_KEY")