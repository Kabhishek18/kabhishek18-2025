# Fixed admin.py - Copy this to replace your admin.py

from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from unfold.admin import ModelAdmin
from .models import ScriptRunner
import sys
from io import StringIO
import traceback

def execute_script_action(modeladmin, request, queryset):
    """Execute the script and capture output"""
    for script_obj in queryset:
        # Initialize variables BEFORE try block to avoid UnboundLocalError
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        stdout_buffer = StringIO()
        stderr_buffer = StringIO()
        
        try:
            # Redirect stdout and stderr to capture output
            sys.stdout = stdout_buffer
            sys.stderr = stderr_buffer
            
            # Create a safe execution environment with common modules
            try:
                import urllib.parse
                import urllib.request
                import json
                import datetime
                import math
                import random
                import os
                import time
                import re
                import base64
                import hashlib
                import uuid
                
                safe_globals = {
                    '__builtins__': {
                        'print': print,
                        'len': len,
                        'str': str,
                        'int': int,
                        'float': float,
                        'list': list,
                        'dict': dict,
                        'tuple': tuple,
                        'set': set,
                        'range': range,
                        'enumerate': enumerate,
                        'zip': zip,
                        'map': map,
                        'filter': filter,
                        'sum': sum,
                        'max': max,
                        'min': min,
                        'abs': abs,
                        'round': round,
                        'sorted': sorted,
                        'reversed': reversed,
                        'any': any,
                        'all': all,
                        'type': type,
                        'isinstance': isinstance,
                        'hasattr': hasattr,
                        'getattr': getattr,
                        'setattr': setattr,
                        'dir': dir,
                        'help': help,
                        'open': open,
                        'exec': exec,
                        'eval': eval,
                        '__import__': __import__,
                    },
                    # Common modules
                    'urllib': urllib,
                    'json': json,
                    'datetime': datetime,
                    'math': math,
                    'random': random,
                    'os': os,
                    'sys': sys,
                    'time': time,
                    're': re,
                    'base64': base64,
                    'hashlib': hashlib,
                    'uuid': uuid,
                }
                
                # Try to import requests if available
                try:
                    import requests
                    safe_globals['requests'] = requests
                except ImportError:
                    pass
                    
            except ImportError:
                # Fallback to basic builtins if imports fail
                safe_globals = {
                    '__builtins__': {
                        'print': print,
                        'len': len,
                        'str': str,
                        'int': int,
                        'float': float,
                        'list': list,
                        'dict': dict,
                        'tuple': tuple,
                        'set': set,
                        'range': range,
                        'enumerate': enumerate,
                        'zip': zip,
                        'map': map,
                        'filter': filter,
                        'sum': sum,
                        'max': max,
                        'min': min,
                        'abs': abs,
                        'round': round,
                        'sorted': sorted,
                        'reversed': reversed,
                        'any': any,
                        'all': all,
                        'type': type,
                        'isinstance': isinstance,
                        'hasattr': hasattr,
                        'getattr': getattr,
                        'setattr': setattr,
                        'dir': dir,
                        'help': help,
                    }
                }
            
            # Add Django models for database operations (optional)
            try:
                from django.apps import apps
                safe_globals['models'] = apps.get_models()
            except:
                pass
            
            # Execute the script
            exec(script_obj.script_code, safe_globals)
            
            # Get the output
            stdout_content = stdout_buffer.getvalue()
            stderr_content = stderr_buffer.getvalue()
            
            # Combine output
            output = ""
            if stdout_content:
                output += f"OUTPUT:\n{stdout_content}\n"
            if stderr_content:
                output += f"ERRORS:\n{stderr_content}\n"
            
            if not output:
                output = "Script executed successfully (no output)"
            
            # Save output to model
            script_obj.output = output
            script_obj.executed_at = timezone.now()
            script_obj.save()
            
            messages.success(request, f"Script '{script_obj.name}' executed successfully!")
            
        except Exception as e:
            # Capture any execution errors
            error_output = f"EXECUTION ERROR:\n{str(e)}\n\nTRACEBACK:\n{traceback.format_exc()}"
            script_obj.output = error_output
            script_obj.executed_at = timezone.now()
            script_obj.save()
            
            messages.error(request, f"Script '{script_obj.name}' failed: {str(e)}")
        
        finally:
            # Always restore stdout and stderr (they're now always defined)
            sys.stdout = old_stdout
            sys.stderr = old_stderr

execute_script_action.short_description = "Execute Selected Scripts"

@admin.register(ScriptRunner)
class ScriptRunnerAdmin(ModelAdmin):
    list_display = ['name', 'created_at', 'executed_at', 'has_output']
    list_filter = ['created_at', 'executed_at']
    search_fields = ['name', 'script_code']
    actions = [execute_script_action]
    
    # Unfold specific configurations
    list_display_links = ['name']
    list_per_page = 25
    
    fieldsets = (
        ("Script Information", {
            'fields': ('name', 'script_code'),
            'description': 'Write your Python script in the code field below'
        }),
        ("Execution Results", {
            'fields': ('output',),
            'classes': ('collapse',),
            'description': 'Output will appear here after execution'
        }),
        ("Timestamps", {
            'fields': ('created_at', 'executed_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['created_at', 'executed_at', 'output']
    
    def has_output(self, obj):
        return bool(obj.output)
    has_output.boolean = True
    has_output.short_description = 'Has Output'
    
    # Override the form to add syntax highlighting (optional)
    class Media:
        css = {
            'all': ('admin/css/script_runner.css',)
        }
        js = ('admin/js/script_runner.js',)