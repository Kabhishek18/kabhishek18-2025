"""
Custom admin widgets for roadmap app
"""
from django import forms
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class BackendStatusWidget(forms.Widget):
    """
    Custom widget to display backend status information in admin
    """
    
    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.template_name = 'admin/roadmap/widgets/backend_status.html'
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render the backend status widget"""
        try:
            from ..services.ai_processor import AIProcessor
            processor = AIProcessor()
            status = processor.get_backend_status()
            available_backends = processor.get_available_backends()
            
            html_parts = ['<div class="backend-status-widget">']
            
            # Add a header
            html_parts.append('<h4 style="margin: 0 0 10px 0; color: #333;">AI Backend Status</h4>')
            
            # Add status for each backend
            for backend_name, backend_status in status.items():
                if backend_status['available']:
                    color = '#28a745'  # Green
                    icon = '✓'
                    status_text = 'Available'
                    status_class = 'available'
                else:
                    color = '#dc3545'  # Red
                    icon = '✗'
                    status_text = 'Unavailable'
                    status_class = 'unavailable'
                
                html_parts.append(f'''
                    <div class="backend-item {status_class}" style="
                        margin: 5px 0; 
                        padding: 8px 12px; 
                        border-left: 4px solid {color}; 
                        background: #f8f9fa;
                        border-radius: 0 4px 4px 0;
                    ">
                        <span style="color: {color}; font-weight: bold; margin-right: 8px;">{icon}</span>
                        <strong>{backend_status["backend_name"]}:</strong> 
                        <span style="color: {color};">{status_text}</span>
                        {f'<br><small style="color: #6c757d; margin-left: 20px;">Error: {backend_status.get("error", "")}</small>' if backend_status.get("error") else ''}
                    </div>
                ''')
            
            # Add summary
            available_count = len(available_backends)
            total_count = len(status)
            
            if available_count == total_count:
                summary_color = '#28a745'
                summary_text = f'All {total_count} backends are available'
            elif available_count > 0:
                summary_color = '#ffc107'
                summary_text = f'{available_count} of {total_count} backends available'
            else:
                summary_color = '#dc3545'
                summary_text = 'No backends available'
            
            html_parts.append(f'''
                <div style="
                    margin-top: 10px; 
                    padding: 8px 12px; 
                    background: {summary_color}15; 
                    border: 1px solid {summary_color}40;
                    border-radius: 4px;
                    text-align: center;
                ">
                    <strong style="color: {summary_color};">{summary_text}</strong>
                </div>
            ''')
            
            # Add refresh note
            html_parts.append('''
                <div style="
                    margin-top: 8px; 
                    font-size: 11px; 
                    color: #6c757d; 
                    text-align: center;
                ">
                    Status updates when page is refreshed
                </div>
            ''')
            
            html_parts.append('</div>')
            
            return mark_safe(''.join(html_parts))
            
        except Exception as e:
            return format_html(
                '<div style="color: #dc3545; padding: 10px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px;">'
                'Error loading backend status: {}'
                '</div>',
                str(e)
            )
    
    def value_from_datadict(self, data, files, name):
        """This widget is read-only, so return None"""
        return None


class APIKeyWidget(forms.PasswordInput):
    """
    Custom widget for API key fields with show/hide functionality
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'vTextField api-key-field',
            'style': 'width: 400px;',
            'autocomplete': 'off',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render API key field with show/hide toggle"""
        widget_html = super().render(name, value, attrs, renderer)
        
        # Add JavaScript for show/hide functionality
        toggle_html = f'''
        <div class="api-key-container">
            {widget_html}
            <button type="button" class="api-key-toggle" onclick="toggleAPIKey('{attrs.get('id', name) if attrs else name}')" 
                    style="margin-left: 8px; padding: 4px 8px; font-size: 11px; cursor: pointer;">
                Show
            </button>
        </div>
        <script>
        function toggleAPIKey(fieldId) {{
            const field = document.getElementById(fieldId);
            const button = field.nextElementSibling;
            
            if (field.type === 'password') {{
                field.type = 'text';
                button.textContent = 'Hide';
            }} else {{
                field.type = 'password';
                button.textContent = 'Show';
            }}
        }}
        </script>
        <style>
        .api-key-container {{
            display: inline-block;
        }}
        .api-key-toggle {{
            background: #007cba;
            color: white;
            border: none;
            border-radius: 3px;
            font-size: 11px;
            padding: 4px 8px;
            cursor: pointer;
        }}
        .api-key-toggle:hover {{
            background: #005a87;
        }}
        </style>
        '''
        
        return mark_safe(toggle_html)