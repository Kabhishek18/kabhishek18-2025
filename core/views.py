# core/views.py

from django.shortcuts import render, get_object_or_404
from django.views import View
from django.http import Http404
from .models import Page

def custom_404(request, exception=None):
    """Custom 404 error handler"""
    return render(request, '404.html', status=404)

def custom_500(request):
    """Custom 500 error handler"""
    return render(request, '404.html', status=500)  # Use 404 template for now

class PageRequest(View):
    """
    View to handle both homepage and custom page requests
    """
    
    def get(self, request, slug=None):
        try:
            if slug is None:
                # Homepage request
                page = Page.objects.filter(
                    is_homepage=True, 
                    is_published=True
                ).first()
            else:
                # Specific page request
                page = get_object_or_404(
                    Page, 
                    slug=slug, 
                    is_published=True
                )
            
            if not page:
                raise Http404("Page not found")
            
            # Build context
            context = {
                'title': page.title,
                'meta_details': page.meta_description or page.title,
                'home_navbar': page.navbar_type == 'HOME',
                'blog_navbar': page.navbar_type == 'BLOG',
                'generic_navbar': page.navbar_type == 'GENERIC',
                'page_content': None,
                'template_includes': [],
                'page': page,
            }

            # Handle template vs content rendering
            if page.template and page.template.files.exists():
                # Use template files
                template_files = page.template.files.all().order_by('id')
                context['template_includes'] = [
                    f.get_include_path() for f in template_files
                ]
            else:
                # Use manual content
                context['page_content'] = page.content

            return render(request, 'index.html', context)
            
        except Page.DoesNotExist:
            raise Http404("Page not found")
        except Exception as e:
            # In production, you'd log this error
            print(f"Error rendering page: {e}")
            raise Http404("Page not found")