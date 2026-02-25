"""
Admin configuration for roadmap app
"""
from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path
from django.shortcuts import render
from django.utils.html import format_html
import logging

from .models import ResumeParserConfig
from .admin_forms import ResumeParserConfigForm

logger = logging.getLogger(__name__)


@admin.register(ResumeParserConfig)
class ResumeParserConfigAdmin(admin.ModelAdmin):
    """
    Admin interface for Resume Parser Configuration management
    """
    form = ResumeParserConfigForm
    
    list_display = (
        'default_backend', 
        'max_file_size_mb', 
        'enable_fallback_processing',
        'backend_status_display',
        'updated_at'
    )
    
    readonly_fields = ('created_at', 'updated_at', 'backend_status_display')
    
    actions = ['test_all_backends', 'test_gemini_backend', 'test_spacy_backend', 'test_rule_based_backend']
    
    fieldsets = (
        ('API Configuration', {
            'fields': ('gemini_api_key',),
            'description': 'Configure external API keys for AI processing'
        }),
        ('File Processing Settings', {
            'fields': (
                'max_file_size_mb',
                'processing_timeout_seconds',
                'temp_file_cleanup_timeout'
            ),
            'description': 'Configure file upload and processing limits'
        }),
        ('AI Backend Configuration', {
            'fields': (
                'default_backend',
                'spacy_model',
                'enable_fallback_processing',
                'enable_confidence_scoring'
            ),
            'description': 'Configure AI processing backends and behavior'
        }),
        ('Backend Status', {
            'fields': ('backend_status_display',),
            'description': 'Current status of AI processing backends'
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'System timestamps'
        }),
    )
    
    def has_add_permission(self, request):
        """Only allow one configuration instance"""
        return not ResumeParserConfig.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Don't allow deletion of the configuration"""
        return False
    
    def changelist_view(self, request, extra_context=None):
        """Redirect to change view if config exists, otherwise show add form"""
        if ResumeParserConfig.objects.exists():
            config = ResumeParserConfig.objects.first()
            return self.change_view(request, str(config.pk), extra_context)
        return super().changelist_view(request, extra_context)
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form for better user experience"""
        form = super().get_form(request, obj, **kwargs)
        
        # The custom form handles most of the customization
        # Add any request-specific customizations here if needed
        
        return form
    
    def save_model(self, request, obj, form, change):
        """Custom save logic with user feedback"""
        super().save_model(request, obj, form, change)
        
        if change:
            messages.success(
                request, 
                "Resume Parser configuration updated successfully. "
                "Use the admin actions below to test your backends."
            )
        else:
            messages.success(
                request,
                "Resume Parser configuration created successfully. "
                "Use the admin actions below to test your backends."
            )
    
    def backend_status_display(self, obj):
        """Display current backend status with color coding"""
        try:
            from .services.ai_processor import AIProcessor
            processor = AIProcessor()
            status = processor.get_backend_status()
            
            html_parts = []
            for backend_name, backend_status in status.items():
                if backend_status['available']:
                    color = 'green'
                    icon = '✓'
                    status_text = 'Available'
                else:
                    color = 'red'
                    icon = '✗'
                    status_text = f"Unavailable: {backend_status.get('error', 'Unknown error')}"
                
                html_parts.append(
                    f'<div style="margin: 2px 0;"><span style="color: {color}; font-weight: bold;">'
                    f'{icon}</span> <strong>{backend_status["backend_name"]}:</strong> {status_text}</div>'
                )
            
            return format_html(''.join(html_parts))
            
        except Exception as e:
            return format_html(
                '<div style="color: red;">Error checking backend status: {}</div>',
                str(e)
            )
    
    backend_status_display.short_description = 'Backend Status'
    
    # Admin Actions for Testing Backends
    
    def test_all_backends(self, request, queryset):
        """Test all available AI backends"""
        try:
            from .services.ai_processor import AIProcessor
            processor = AIProcessor()
            
            # Sample resume text for testing
            test_text = """
            John Doe
            Software Engineer
            john.doe@email.com
            (555) 123-4567
            
            EXPERIENCE
            Senior Software Engineer at Tech Corp (2020-2023)
            - Developed web applications using Python and Django
            - Led a team of 5 developers
            
            EDUCATION
            Bachelor of Science in Computer Science
            University of Technology (2018)
            
            SKILLS
            Python, Django, JavaScript, React, SQL, AWS
            """
            
            status = processor.get_backend_status()
            results = []
            
            for backend_name, backend_status in status.items():
                if backend_status['available']:
                    try:
                        result = processor.process_resume_text(test_text, backend_name)
                        results.append(f"✓ {backend_status['backend_name']}: Successfully processed test resume")
                    except Exception as e:
                        results.append(f"✗ {backend_status['backend_name']}: Failed - {str(e)}")
                else:
                    results.append(f"✗ {backend_status['backend_name']}: Not available - {backend_status.get('error', 'Unknown error')}")
            
            if results:
                messages.success(request, f"Backend Test Results:\n" + "\n".join(results))
            else:
                messages.warning(request, "No backends available for testing")
                
        except Exception as e:
            messages.error(request, f"Error testing backends: {str(e)}")
    
    test_all_backends.short_description = "Test all AI backends"
    
    def test_gemini_backend(self, request, queryset):
        """Test Gemini AI backend specifically"""
        self._test_specific_backend(request, 'gemini', 'Gemini AI')
    
    test_gemini_backend.short_description = "Test Gemini AI backend"
    
    def test_spacy_backend(self, request, queryset):
        """Test spaCy backend specifically"""
        self._test_specific_backend(request, 'spacy', 'spaCy NLP')
    
    test_spacy_backend.short_description = "Test spaCy NLP backend"
    
    def test_rule_based_backend(self, request, queryset):
        """Test rule-based backend specifically"""
        self._test_specific_backend(request, 'rule_based', 'Rule-based')
    
    test_rule_based_backend.short_description = "Test rule-based backend"
    
    def _test_specific_backend(self, request, backend_name, backend_display_name):
        """Helper method to test a specific backend"""
        try:
            from .services.ai_processor import AIProcessor
            processor = AIProcessor()
            
            # Sample resume text for testing
            test_text = """
            Jane Smith
            Data Scientist
            jane.smith@example.com
            +1 (555) 987-6543
            
            PROFESSIONAL EXPERIENCE
            Senior Data Scientist at DataTech Inc. (2021-Present)
            - Built machine learning models using Python and scikit-learn
            - Analyzed large datasets to drive business insights
            - Collaborated with cross-functional teams
            
            Data Analyst at Analytics Co. (2019-2021)
            - Created dashboards and reports using Tableau
            - Performed statistical analysis on customer data
            
            EDUCATION
            Master of Science in Data Science
            State University (2019)
            
            Bachelor of Arts in Mathematics
            City College (2017)
            
            TECHNICAL SKILLS
            Python, R, SQL, Tableau, scikit-learn, pandas, numpy, TensorFlow, AWS, Git
            """
            
            # Check if backend is available
            status = processor.get_backend_status()
            if backend_name not in status:
                messages.error(request, f"{backend_display_name} backend not found")
                return
            
            backend_status = status[backend_name]
            if not backend_status['available']:
                messages.error(
                    request, 
                    f"{backend_display_name} backend is not available: {backend_status.get('error', 'Unknown error')}"
                )
                return
            
            # Test the backend
            result = processor.process_resume_text(test_text, backend_name)
            
            # Format the results for display
            success_msg = f"✓ {backend_display_name} backend test successful!\n\n"
            success_msg += f"Extracted Information:\n"
            success_msg += f"• Name: {result.get('name', 'Not found')}\n"
            success_msg += f"• Email: {result.get('email', 'Not found')}\n"
            success_msg += f"• Phone: {result.get('phone', 'Not found')}\n"
            success_msg += f"• Skills: {len(result.get('skills', []))} skills found\n"
            success_msg += f"• Experience: {len(result.get('experience', []))} jobs found\n"
            success_msg += f"• Education: {len(result.get('education', []))} entries found\n"
            success_msg += f"• Confidence Score: {result.get('confidence_score', 0):.2f}\n"
            success_msg += f"• Backend Used: {result.get('processing_backend_used', 'Unknown')}"
            
            messages.success(request, success_msg)
            
        except Exception as e:
            logger.error(f"Error testing {backend_name} backend: {e}")
            messages.error(request, f"Error testing {backend_display_name} backend: {str(e)}")
    
    def get_urls(self):
        """Add custom URLs for admin actions"""
        urls = super().get_urls()
        custom_urls = [
            path(
                'backend-test-results/',
                self.admin_site.admin_view(self.backend_test_results_view),
                name='roadmap_resumeparserconfig_backend_test_results',
            ),
        ]
        return custom_urls + urls
    
    def backend_test_results_view(self, request):
        """Custom view to display detailed backend test results"""
        try:
            from .services.ai_processor import AIProcessor
            processor = AIProcessor()
            
            context = {
                'title': 'AI Backend Test Results',
                'backend_status': processor.get_backend_status(),
                'available_backends': processor.get_available_backends(),
            }
            
            return render(request, 'admin/roadmap/backend_test_results.html', context)
            
        except Exception as e:
            messages.error(request, f"Error loading backend test results: {str(e)}")
            return HttpResponseRedirect('../')
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add extra context to change view"""
        extra_context = extra_context or {}
        
        try:
            from .services.ai_processor import AIProcessor
            processor = AIProcessor()
            extra_context['backend_status'] = processor.get_backend_status()
            extra_context['available_backends'] = processor.get_available_backends()
        except Exception as e:
            logger.warning(f"Could not load backend status: {e}")
        
        return super().change_view(request, object_id, form_url, extra_context)
