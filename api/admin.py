# admin.py 

from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from unfold.admin import ModelAdmin
from .models import ScriptRunner
import sys
from io import StringIO
import traceback
import time
import threading

def execute_script_action(modeladmin, request, queryset):
    """Execute the script and capture output with timeout protection"""
    for script_obj in queryset:
        # Initialize variables BEFORE try block to avoid UnboundLocalError
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        stdout_buffer = StringIO()
        stderr_buffer = StringIO()
        start_time = time.time()
        
        # Update status to running
        script_obj.execution_status = 'running'
        script_obj.save()
        
        try:
            # Redirect stdout and stderr to capture output
            sys.stdout = stdout_buffer
            sys.stderr = stderr_buffer
            
            # Create enhanced execution environment
            safe_globals = create_safe_environment()
            
            # Execute with timeout using threading
            execution_successful = False
            execution_error = None
            
            def execute_code():
                nonlocal execution_successful, execution_error
                try:
                    exec(script_obj.script_code, safe_globals)
                    execution_successful = True
                except Exception as e:
                    execution_error = e
            
            # Run in thread with timeout
            thread = threading.Thread(target=execute_code)
            thread.daemon = True
            thread.start()
            thread.join(timeout=getattr(script_obj, 'timeout_seconds', 30))
            
            if thread.is_alive():
                # Timeout occurred
                raise TimeoutError(f"Script timed out after {getattr(script_obj, 'timeout_seconds', 30)} seconds")
            
            if execution_error:
                raise execution_error
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Get output
            stdout_content = stdout_buffer.getvalue()
            stderr_content = stderr_buffer.getvalue()
            
            # Format output
            output = f"⏱️  Execution Time: {execution_time:.3f}s\n"
            output += "=" * 50 + "\n"
            
            if stdout_content:
                output += "📤 OUTPUT:\n" + stdout_content + "\n"
            
            if stderr_content:
                output += "⚠️  ERRORS:\n" + stderr_content + "\n"
            
            if not stdout_content and not stderr_content:
                output += "✅ Script executed successfully (no output)\n"
            
            # Save results
            script_obj.output = output
            script_obj.execution_status = 'completed'
            if hasattr(script_obj, 'execution_time'):
                script_obj.execution_time = execution_time
            if hasattr(script_obj, 'execution_count'):
                script_obj.execution_count = getattr(script_obj, 'execution_count', 0) + 1
            script_obj.executed_at = timezone.now()
            script_obj.save()
            
            messages.success(request, f"✅ '{script_obj.name}' executed successfully in {execution_time:.2f}s!")
            
        except Exception as e:
            # Handle errors
            execution_time = time.time() - start_time
            error_output = f"❌ EXECUTION ERROR:\n{str(e)}\n\n📋 TRACEBACK:\n{traceback.format_exc()}"
            
            script_obj.output = error_output
            script_obj.execution_status = 'failed'
            if hasattr(script_obj, 'execution_time'):
                script_obj.execution_time = execution_time
            script_obj.executed_at = timezone.now()
            script_obj.save()
            
            messages.error(request, f"❌ '{script_obj.name}' failed: {str(e)}")
        
        finally:
            # Always restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr

def create_safe_environment():
    """Create a safe execution environment with common modules"""
    # Import safe modules
    modules = {}
    safe_module_names = [
        'urllib', 'json', 'datetime', 'math', 'random', 'os', 'time', 're', 
        'base64', 'hashlib', 'uuid', 'csv', 'itertools', 'collections'
    ]
    
    for module_name in safe_module_names:
        try:
            modules[module_name] = __import__(module_name)
        except ImportError:
            pass
    
    # Try to add requests
    try:
        import requests
        modules['requests'] = requests
    except ImportError:
        pass
    
    # Enhanced builtins
    safe_builtins = {
        'print': print, 'len': len, 'str': str, 'int': int, 'float': float,
        'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
        'range': range, 'enumerate': enumerate, 'zip': zip, 'map': map, 'filter': filter,
        'sum': sum, 'max': max, 'min': min, 'abs': abs, 'round': round,
        'sorted': sorted, 'reversed': reversed, 'any': any, 'all': all,
        'type': type, 'isinstance': isinstance, 'hasattr': hasattr,
        'getattr': getattr, 'setattr': setattr, 'dir': dir, 'help': help,
        '__import__': __import__
    }
    
    # Helper functions
    def api_test(url, method='GET', **kwargs):
        """Quick API testing"""
        try:
            import requests
            response = requests.request(method, url, timeout=10, **kwargs)
            return {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content': response.text[:500] + '...' if len(response.text) > 500 else response.text
            }
        except Exception as e:
            return {'error': str(e)}
    
    def db_query(query, params=None):
        """Database query helper"""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(query, params or [])
                if query.strip().upper().startswith('SELECT'):
                    return cursor.fetchall()
                return cursor.rowcount
        except Exception as e:
            return f"Error: {str(e)}"
    
    # Add helpers to builtins
    safe_builtins.update({
        'api_test': api_test,
        'db_query': db_query,
    })
    
    return {
        '__builtins__': safe_builtins,
        **modules
    }

# Additional admin actions
def clone_script_action(modeladmin, request, queryset):
    """Clone selected scripts"""
    for script in queryset:
        cloned = ScriptRunner.objects.create(
            name=f"{script.name} (Copy)",
            script_code=script.script_code,
            created_by=getattr(request, 'user', None) if hasattr(script, 'created_by') else None
        )
        messages.success(request, f"📋 Cloned '{script.name}' as '{cloned.name}'")

# Set action descriptions
execute_script_action.short_description = "🚀 Execute Selected Scripts"
clone_script_action.short_description = "📋 Clone Selected Scripts"

@admin.register(ScriptRunner)
class ScriptRunnerAdmin(ModelAdmin):
    list_display = ['name', 'created_at', 'executed_at', 'get_status', 'get_execution_time']
    list_filter = ['created_at', 'executed_at']
    search_fields = ['name', 'script_code']
    actions = [execute_script_action, clone_script_action]
    
    fieldsets = (
        ("📝 Script Information", {
            'fields': ('name', 'script_code'),
            'description': 'Write your Python script in the code field below'
        }),
        ("📊 Execution Results", {
            'fields': ('output',),
            'classes': ('collapse',),
            'description': 'Output will appear here after execution'
        }),
        ("🕒 Timestamps", {
            'fields': ('created_at', 'executed_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['created_at', 'executed_at', 'output']
    
    def get_status(self, obj):
        """Get execution status with icons"""
        status = getattr(obj, 'execution_status', 'pending')
        status_icons = {
            'pending': '⏳ Pending',
            'running': '🔄 Running',
            'completed': '✅ Completed',
            'failed': '❌ Failed',
            'timeout': '⏰ Timeout'
        }
        return status_icons.get(status, '❓ Unknown')
    get_status.short_description = 'Status'
    
    def get_execution_time(self, obj):
        """Get formatted execution time"""
        if hasattr(obj, 'execution_time') and obj.execution_time:
            return f"{obj.execution_time:.3f}s"
        return "-"
    get_execution_time.short_description = 'Exec Time'
    
    def save_model(self, request, obj, form, change):
        if not change and hasattr(obj, 'created_by'):  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    class Media:
        css = {
            'all': ('admin/css/script_runner.css',)
        }
        js = ('admin/js/script_runner.js',)