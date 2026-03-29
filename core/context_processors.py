from urllib.parse import urlencode

from django.conf import settings as django_settings

from .theme import get_active_theme, get_active_theme_label, get_theme_settings


def _get_site_url():
    site_url = getattr(django_settings, "SITE_URL", "https://kabhishek18.com") or "https://kabhishek18.com"
    return site_url.rstrip("/")


def _build_canonical_url(request):
    site_url = _get_site_url()
    path = request.path if request.path else "/"
    query_params = request.GET.copy()

    # Keep only SEO-meaningful params in canonicals.
    allowed_keys = ["page", "q"]
    filtered_params = [(key, value) for key, value in query_params.items() if key in allowed_keys and value]
    query_string = urlencode(filtered_params)

    canonical_url = f"{site_url}{path}"
    if query_string:
        canonical_url = f"{canonical_url}?{query_string}"
    return canonical_url


def active_theme(request):
    settings = get_theme_settings()
    site_url = _get_site_url()
    return {
        'theme_settings': settings,
        'active_theme': get_active_theme(),
        'active_theme_label': get_active_theme_label(),
        'site_url': site_url,
        'canonical_url': _build_canonical_url(request),
        'publisher_name': getattr(settings, 'site_name', '') or getattr(django_settings, 'SITE_NAME', 'Kumar Abhishek'),
        'publisher_logo_url': f"{site_url}/static/web-app-manifest-512x512.png",
        'default_meta_keywords': 'Kumar Abhishek, Kabhishek18, AI Engineer, Senior Software Engineer, Django, Python, React, Portfolio, Blog, Technical Articles',
    }
