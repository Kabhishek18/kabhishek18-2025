from django.shortcuts import render, get_object_or_404
from django.views import View
from .models import Page

# Ensure your custom 404 handler is defined or imported if you use it.
def custom_404(request, exception):
    return render(request, '404.html', status=404)

class PageRequest(View):
    def get(self, request, slug=None):
        page = None
        if slug is None:
            page = Page.objects.filter(is_homepage=True, is_published=True).first()
        else:
            page = get_object_or_404(Page, slug=slug, is_published=True)

        if not page:
            return custom_404(request, None)

        # Prepare the context dictionary
        context = {
            'title': page.title,
            'meta_details': page.meta_description,
            'home_navbar': page.navbar_type == 'HOME',
            'blog_navbar': page.navbar_type == 'BLOG',
            'generic_navbar': page.navbar_type == 'GENERIC',
            'page_content': None,
            'template_includes': []
        }

        # Check if a template set is associated with the page
        if page.template:
            # Get all associated TemplateFile objects and extract their include paths
            template_files = page.template.files.all()
            context['template_includes'] = [f.get_include_path() for f in template_files]
        else:
            # If no template set is selected, use the manual content from the Page model
            context['page_content'] = page.content

        return render(request, 'index.html', context)
