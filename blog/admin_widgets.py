"""
Custom admin widgets for LinkedIn configuration management.
"""
from django import forms
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.contrib.admin.widgets import AdminTextareaWidget
import json


class HashtagRulesWidget(forms.Widget):
    """
    Custom widget for managing hashtag rules per category.
    Provides a user-friendly interface for JSON hashtag rules.
    """
    template_name = 'admin/blog/widgets/hashtag_rules_widget.html'
    
    def __init__(self, attrs=None):
        default_attrs = {'class': 'hashtag-rules-widget'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def format_value(self, value):
        """Format the JSON value for display"""
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return value
        if isinstance(value, dict):
            return json.dumps(value, indent=2)
        return str(value)
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget"""
        if attrs is None:
            attrs = {}
        
        formatted_value = self.format_value(value)
        
        # Create the textarea for JSON input
        textarea_attrs = {
            'rows': 10,
            'cols': 80,
            'class': 'vLargeTextField hashtag-rules-json',
            'placeholder': self.get_placeholder_text()
        }
        textarea_attrs.update(attrs)
        
        textarea_html = f'<textarea name="{name}" id="id_{name}" {self.build_attrs_string(textarea_attrs)}>{formatted_value}</textarea>'
        
        # Add help text and example
        help_html = f'''
        <div class="hashtag-rules-help">
            <p><strong>Hashtag Rules Configuration:</strong></p>
            <p>Define custom hashtag rules for different categories. Use JSON format.</p>
            <details>
                <summary>Click to see example format</summary>
                <pre>{self.get_example_json()}</pre>
            </details>
            <div class="hashtag-rules-actions">
                <button type="button" class="button" onclick="validateHashtagRules('{name}')">Validate JSON</button>
                <button type="button" class="button" onclick="formatHashtagRules('{name}')">Format JSON</button>
            </div>
        </div>
        '''
        
        # Add JavaScript for validation and formatting
        js_html = f'''
        <script>
        function validateHashtagRules(fieldName) {{
            const textarea = document.getElementById('id_' + fieldName);
            try {{
                const parsed = JSON.parse(textarea.value || '{{}}');
                alert('JSON is valid!');
                return true;
            }} catch (e) {{
                alert('Invalid JSON: ' + e.message);
                return false;
            }}
        }}
        
        function formatHashtagRules(fieldName) {{
            const textarea = document.getElementById('id_' + fieldName);
            try {{
                const parsed = JSON.parse(textarea.value || '{{}}');
                textarea.value = JSON.stringify(parsed, null, 2);
            }} catch (e) {{
                alert('Cannot format invalid JSON: ' + e.message);
            }}
        }}
        </script>
        '''
        
        return mark_safe(textarea_html + help_html + js_html)
    
    def build_attrs_string(self, attrs):
        """Build HTML attributes string"""
        return ' '.join([f'{k}="{v}"' for k, v in attrs.items()])
    
    def get_placeholder_text(self):
        """Get placeholder text for the textarea"""
        return '''Enter hashtag rules in JSON format. Example:
{
  "technology": {
    "required_hashtags": ["#Tech", "#Programming"],
    "suggested_hashtags": ["#Development", "#Coding"],
    "max_hashtags": 3
  }
}'''
    
    def get_example_json(self):
        """Get example JSON for help text"""
        return json.dumps({
            "technology": {
                "required_hashtags": ["#Tech", "#Programming"],
                "suggested_hashtags": ["#Development", "#Coding", "#Software"],
                "max_hashtags": 3,
                "priority": 1
            },
            "tutorial": {
                "required_hashtags": ["#Tutorial", "#HowTo"],
                "suggested_hashtags": ["#Learning", "#Guide", "#Tips"],
                "max_hashtags": 4,
                "priority": 2
            }
        }, indent=2)
    
    def value_from_datadict(self, data, files, name):
        """Extract value from form data"""
        value = data.get(name)
        if value:
            try:
                # Validate JSON
                parsed = json.loads(value)
                return parsed
            except json.JSONDecodeError:
                return value
        return {}


class HashtagBlacklistWidget(forms.Widget):
    """
    Custom widget for managing hashtag blacklist.
    Provides a user-friendly interface for managing blacklisted terms.
    """
    template_name = 'admin/blog/widgets/hashtag_blacklist_widget.html'
    
    def __init__(self, attrs=None):
        default_attrs = {'class': 'hashtag-blacklist-widget'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def format_value(self, value):
        """Format the list value for display"""
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return value
        if isinstance(value, list):
            return '\n'.join(value)
        return str(value)
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget"""
        if attrs is None:
            attrs = {}
        
        formatted_value = self.format_value(value)
        
        # Create the textarea for blacklist input
        textarea_attrs = {
            'rows': 8,
            'cols': 40,
            'class': 'vLargeTextField hashtag-blacklist-textarea',
            'placeholder': 'Enter blacklisted terms, one per line\nExample:\nspam\nclickbait\nurgent'
        }
        textarea_attrs.update(attrs)
        
        textarea_html = f'<textarea name="{name}" id="id_{name}" {self.build_attrs_string(textarea_attrs)}>{formatted_value}</textarea>'
        
        # Add help text and actions
        help_html = f'''
        <div class="hashtag-blacklist-help">
            <p><strong>Hashtag Blacklist:</strong></p>
            <p>Enter words or phrases that should never be used as hashtags, one per line.</p>
            <div class="hashtag-blacklist-actions">
                <button type="button" class="button" onclick="sortBlacklist('{name}')">Sort Alphabetically</button>
                <button type="button" class="button" onclick="removeDuplicates('{name}')">Remove Duplicates</button>
            </div>
        </div>
        '''
        
        # Add JavaScript for list management
        js_html = f'''
        <script>
        function sortBlacklist(fieldName) {{
            const textarea = document.getElementById('id_' + fieldName);
            const lines = textarea.value.split('\\n').filter(line => line.trim());
            const sorted = lines.sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
            textarea.value = sorted.join('\\n');
        }}
        
        function removeDuplicates(fieldName) {{
            const textarea = document.getElementById('id_' + fieldName);
            const lines = textarea.value.split('\\n').filter(line => line.trim());
            const unique = [...new Set(lines.map(line => line.toLowerCase()))];
            textarea.value = unique.join('\\n');
        }}
        </script>
        '''
        
        return mark_safe(textarea_html + help_html + js_html)
    
    def build_attrs_string(self, attrs):
        """Build HTML attributes string"""
        return ' '.join([f'{k}="{v}"' for k, v in attrs.items()])
    
    def value_from_datadict(self, data, files, name):
        """Extract value from form data"""
        value = data.get(name)
        if value:
            # Split by lines and clean up
            lines = [line.strip().lower() for line in value.split('\n') if line.strip()]
            return list(set(lines))  # Remove duplicates
        return []


class HashtagPreviewWidget(forms.Widget):
    """
    Widget for previewing hashtag generation for a specific post.
    """
    def __init__(self, attrs=None):
        default_attrs = {'class': 'hashtag-preview-widget'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render the preview widget"""
        preview_html = f'''
        <div class="hashtag-preview-container">
            <div class="hashtag-preview-controls">
                <label for="preview-post-select">Test hashtag generation for post:</label>
                <select id="preview-post-select" class="hashtag-preview-select">
                    <option value="">Select a post...</option>
                </select>
                <button type="button" class="button" onclick="generateHashtagPreview()">Generate Preview</button>
            </div>
            <div id="hashtag-preview-results" class="hashtag-preview-results" style="display: none;">
                <h4>Generated Hashtags:</h4>
                <div id="hashtag-preview-content"></div>
            </div>
        </div>
        '''
        
        # Add JavaScript for preview functionality
        js_html = '''
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            loadPostsForPreview();
        });
        
        function loadPostsForPreview() {
            // This would be populated via AJAX in a real implementation
            // For now, we'll add a placeholder
            const select = document.getElementById('preview-post-select');
            const option = document.createElement('option');
            option.value = 'sample';
            option.textContent = 'Sample Post (Preview functionality)';
            select.appendChild(option);
        }
        
        function generateHashtagPreview() {
            const select = document.getElementById('preview-post-select');
            const resultsDiv = document.getElementById('hashtag-preview-results');
            const contentDiv = document.getElementById('hashtag-preview-content');
            
            if (!select.value) {
                alert('Please select a post first');
                return;
            }
            
            // Simulate hashtag generation
            const sampleHashtags = ['#Technology', '#Programming', '#Development', '#Tutorial', '#Learning'];
            contentDiv.innerHTML = sampleHashtags.map(tag => 
                `<span class="hashtag-preview-tag" style="background: #e1f5fe; padding: 2px 6px; margin: 2px; border-radius: 3px; display: inline-block;">${tag}</span>`
            ).join('');
            
            resultsDiv.style.display = 'block';
        }
        </script>
        '''
        
        return mark_safe(preview_html + js_html)


class CategoryImageOverridesWidget(forms.Widget):
    """
    Custom widget for managing category-based image posting overrides.
    Provides a user-friendly interface for JSON category overrides.
    """
    template_name = 'admin/blog/widgets/category_image_overrides_widget.html'
    
    def __init__(self, attrs=None):
        default_attrs = {'class': 'category-image-overrides-widget'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def format_value(self, value):
        """Format the JSON value for display"""
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return value
        if isinstance(value, dict):
            return json.dumps(value, indent=2)
        return str(value)
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget"""
        if attrs is None:
            attrs = {}
        
        formatted_value = self.format_value(value)
        
        # Create the textarea for JSON input
        textarea_attrs = {
            'rows': 8,
            'cols': 80,
            'class': 'vLargeTextField category-image-overrides-json',
            'placeholder': self.get_placeholder_text()
        }
        textarea_attrs.update(attrs)
        
        textarea_html = f'<textarea name="{name}" id="id_{name}" {self.build_attrs_string(textarea_attrs)}>{formatted_value}</textarea>'
        
        # Add help text and example
        help_html = f'''
        <div class="category-image-overrides-help">
            <p><strong>Category Image Posting Overrides:</strong></p>
            <p>Define image posting behavior for specific categories. Use JSON format.</p>
            <details>
                <summary>Click to see example format</summary>
                <pre>{self.get_example_json()}</pre>
            </details>
            <div class="category-image-overrides-actions">
                <button type="button" class="button" onclick="validateCategoryOverrides('{name}')">Validate JSON</button>
                <button type="button" class="button" onclick="formatCategoryOverrides('{name}')">Format JSON</button>
                <button type="button" class="button" onclick="loadAvailableCategories('{name}')">Load Categories</button>
            </div>
        </div>
        '''
        
        # Add JavaScript for validation and formatting
        js_html = f'''
        <script>
        function validateCategoryOverrides(fieldName) {{
            const textarea = document.getElementById('id_' + fieldName);
            try {{
                const parsed = JSON.parse(textarea.value || '{{}}');
                alert('JSON is valid!');
                return true;
            }} catch (e) {{
                alert('Invalid JSON: ' + e.message);
                return false;
            }}
        }}
        
        function formatCategoryOverrides(fieldName) {{
            const textarea = document.getElementById('id_' + fieldName);
            try {{
                const parsed = JSON.parse(textarea.value || '{{}}');
                textarea.value = JSON.stringify(parsed, null, 2);
            }} catch (e) {{
                alert('Cannot format invalid JSON: ' + e.message);
            }}
        }}
        
        function loadAvailableCategories(fieldName) {{
            // This would load available categories via AJAX in a real implementation
            const exampleCategories = {{
                "technology": {{"enable_images": true, "description": "Always include images for tech posts"}},
                "news": {{"enable_images": false, "description": "Never include images for news posts"}},
                "tutorial": {{"enable_images": true, "description": "Always include images for tutorials"}}
            }};
            
            const textarea = document.getElementById('id_' + fieldName);
            if (confirm('This will replace current content with example categories. Continue?')) {{
                textarea.value = JSON.stringify(exampleCategories, null, 2);
            }}
        }}
        </script>
        '''
        
        return mark_safe(textarea_html + help_html + js_html)
    
    def build_attrs_string(self, attrs):
        """Build HTML attributes string"""
        return ' '.join([f'{k}="{v}"' for k, v in attrs.items()])
    
    def get_placeholder_text(self):
        """Get placeholder text for the textarea"""
        return '''Enter category image overrides in JSON format. Example:
{
  "technology": {"enable_images": true},
  "news": {"enable_images": false}
}'''
    
    def get_example_json(self):
        """Get example JSON for help text"""
        return json.dumps({
            "technology": {
                "enable_images": True,
                "description": "Always include images for technology posts"
            },
            "news": {
                "enable_images": False,
                "description": "Never include images for news posts"
            },
            "tutorial": {
                "enable_images": True,
                "description": "Always include images for tutorial posts"
            },
            "opinion": {
                "enable_images": False,
                "description": "Text-only for opinion pieces"
            }
        }, indent=2)
    
    def value_from_datadict(self, data, files, name):
        """Extract value from form data"""
        value = data.get(name)
        if value:
            try:
                # Validate JSON
                parsed = json.loads(value)
                return parsed
            except json.JSONDecodeError:
                return value
        return {}


class ImagePostingPreviewWidget(forms.Widget):
    """
    Widget for previewing image posting decisions for specific posts.
    """
    template_name = 'admin/blog/widgets/image_posting_preview.html'
    
    def __init__(self, attrs=None):
        default_attrs = {'class': 'image-posting-preview-widget'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render the preview widget using template"""
        from django.template.loader import render_to_string
        
        context = {
            'widget_name': name,
            'widget_value': value,
            'widget_attrs': attrs or {}
        }
        
        return render_to_string(self.template_name, context)
        
