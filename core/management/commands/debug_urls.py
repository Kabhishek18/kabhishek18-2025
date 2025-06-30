# core/management/commands/debug_urls.py
# Usage: python manage.py debug_urls

import sys
from django.core.management.base import BaseCommand
from django.urls import get_resolver
from django.conf import settings
from core.models import Page

class Command(BaseCommand):
    help = 'Debug URL patterns and page routing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-url',
            type=str,
            help='Test a specific URL path',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('=== URL DEBUGGING INFORMATION ===\n')
        )
        
        # 1. Show all URL patterns
        self.show_url_patterns()
        
        # 2. Show all pages
        self.show_pages()
        
        # 3. Test specific URL if provided
        if options['test_url']:
            self.test_url(options['test_url'])
    
    def show_url_patterns(self):
        """Display all registered URL patterns"""
        self.stdout.write(self.style.HTTP_INFO('📍 REGISTERED URL PATTERNS:'))
        
        resolver = get_resolver()
        for pattern in resolver.url_patterns:
            pattern_str = str(pattern.pattern)
            self.stdout.write(f"  • {pattern_str}")
            
            # If it's an include, show sub-patterns
            if hasattr(pattern, 'url_patterns'):
                for sub_pattern in pattern.url_patterns:
                    self.stdout.write(f"    ↳ {sub_pattern.pattern}")
        
        self.stdout.write("")  # Empty line
    
    def show_pages(self):
        """Display all pages in the database"""
        self.stdout.write(self.style.HTTP_INFO('📄 PAGES IN DATABASE:'))
        
        pages = Page.objects.all()
        if not pages:
            self.stdout.write("  No pages found!")
            return
        
        for page in pages:
            status = "✅ Published" if page.is_published else "❌ Draft"
            homepage = "🏠 Homepage" if page.is_homepage else ""
            self.stdout.write(
                f"  • {page.slug or '(no slug)'} → {page.title} {status} {homepage}"
            )
        
        self.stdout.write("")  # Empty line
    
    def test_url(self, url_path):
        """Test a specific URL path"""
        self.stdout.write(
            self.style.HTTP_INFO(f'🧪 TESTING URL: {url_path}')
        )
        
        try:
            from django.test import RequestFactory
            from core.views import PageRequest
            
            factory = RequestFactory()
            request = factory.get(url_path)
            
            # Extract slug from URL
            slug = url_path.strip('/') if url_path != '/' else None
            
            view = PageRequest()
            response = view.get(request, slug=slug)
            
            self.stdout.write(
                self.style.SUCCESS(f"✅ URL resolves successfully (Status: {response.status_code})")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ URL failed: {str(e)}")
            )
    
    def show_settings_info(self):
        """Show relevant settings"""
        self.stdout.write(self.style.HTTP_INFO('⚙️  RELEVANT SETTINGS:'))
        self.stdout.write(f"  • DEBUG: {settings.DEBUG}")
        self.stdout.write(f"  • APPEND_SLASH: {settings.APPEND_SLASH}")
        self.stdout.write(f"  • ROOT_URLCONF: {settings.ROOT_URLCONF}")
        self.stdout.write("")