# Resume Parser Configuration Guide

## Overview

The Resume Parser system supports multiple configuration options to customize its behavior, AI backends, and system limits. This guide covers all available configuration options and their usage.

## Environment Variables

### Required Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `GEMINI_API_KEY` | Google Gemini AI API key (required for Gemini backend) | - | `AIzaSyC...` |

### Optional Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `RESUME_PARSER_MAX_FILE_SIZE` | Maximum file size in MB | `10` | `15` |
| `RESUME_PARSER_DEFAULT_BACKEND` | Default processing backend | `auto` | `gemini` |
| `SPACY_MODEL` | spaCy model to use | `en_core_web_sm` | `en_core_web_lg` |
| `RESUME_PARSER_TEMP_DIR` | Temporary file directory | `/tmp` | `/var/tmp/resumes` |
| `RESUME_PARSER_CLEANUP_TIMEOUT` | File cleanup timeout in seconds | `300` | `600` |
| `RESUME_PARSER_DEBUG` | Enable debug logging | `False` | `True` |

### Setting Environment Variables

#### Development (.env file)
```bash
# .env file
GEMINI_API_KEY=your_gemini_api_key_here
RESUME_PARSER_MAX_FILE_SIZE=10
RESUME_PARSER_DEFAULT_BACKEND=auto
SPACY_MODEL=en_core_web_sm
RESUME_PARSER_DEBUG=True
```

#### Production (System Environment)
```bash
# Linux/macOS
export GEMINI_API_KEY="your_gemini_api_key_here"
export RESUME_PARSER_MAX_FILE_SIZE=10

# Windows
set GEMINI_API_KEY=your_gemini_api_key_here
set RESUME_PARSER_MAX_FILE_SIZE=10
```

#### Docker
```dockerfile
# Dockerfile
ENV GEMINI_API_KEY=your_gemini_api_key_here
ENV RESUME_PARSER_MAX_FILE_SIZE=10
ENV RESUME_PARSER_DEFAULT_BACKEND=auto
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    environment:
      - GEMINI_API_KEY=your_gemini_api_key_here
      - RESUME_PARSER_MAX_FILE_SIZE=10
      - RESUME_PARSER_DEFAULT_BACKEND=auto
```

## Django Settings Configuration

### Basic Configuration

Add to your Django `settings.py`:

```python
# settings.py

# Resume Parser Settings
RESUME_PARSER_SETTINGS = {
    # File handling
    'MAX_FILE_SIZE_MB': int(os.getenv('RESUME_PARSER_MAX_FILE_SIZE', 10)),
    'ALLOWED_FILE_TYPES': ['application/pdf'],
    'TEMP_FILE_CLEANUP_TIMEOUT': int(os.getenv('RESUME_PARSER_CLEANUP_TIMEOUT', 300)),
    
    # Processing
    'DEFAULT_BACKEND': os.getenv('RESUME_PARSER_DEFAULT_BACKEND', 'auto'),
    'PROCESSING_TIMEOUT': 60,  # seconds
    
    # AI Backends
    'AI_BACKENDS': {
        'gemini': {
            'enabled': bool(os.getenv('GEMINI_API_KEY')),
            'api_key': os.getenv('GEMINI_API_KEY'),
            'timeout': 30,
            'max_retries': 3,
            'model': 'gemini-pro',
        },
        'spacy': {
            'enabled': True,
            'model': os.getenv('SPACY_MODEL', 'en_core_web_sm'),
            'timeout': 15,
        },
        'rule_based': {
            'enabled': True,
            'timeout': 5,
        }
    },
    
    # Logging
    'DEBUG_MODE': os.getenv('RESUME_PARSER_DEBUG', 'False').lower() == 'true',
    'LOG_LEVEL': 'DEBUG' if os.getenv('RESUME_PARSER_DEBUG', 'False').lower() == 'true' else 'INFO',
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'resume_parser_file': {
            'level': RESUME_PARSER_SETTINGS['LOG_LEVEL'],
            'class': 'logging.FileHandler',
            'filename': 'resume_parser.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': RESUME_PARSER_SETTINGS['LOG_LEVEL'],
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'roadmap': {
            'handlers': ['resume_parser_file', 'console'],
            'level': RESUME_PARSER_SETTINGS['LOG_LEVEL'],
            'propagate': False,
        },
    },
}
```

### Advanced Configuration

```python
# Advanced settings.py configuration

RESUME_PARSER_SETTINGS = {
    # File handling
    'MAX_FILE_SIZE_MB': 10,
    'ALLOWED_FILE_TYPES': ['application/pdf'],
    'TEMP_FILE_CLEANUP_TIMEOUT': 300,
    'TEMP_DIR': os.getenv('RESUME_PARSER_TEMP_DIR', tempfile.gettempdir()),
    
    # Processing
    'DEFAULT_BACKEND': 'auto',
    'PROCESSING_TIMEOUT': 60,
    'CONCURRENT_UPLOADS_LIMIT': 5,
    
    # AI Backends with detailed configuration
    'AI_BACKENDS': {
        'gemini': {
            'enabled': bool(os.getenv('GEMINI_API_KEY')),
            'api_key': os.getenv('GEMINI_API_KEY'),
            'timeout': 30,
            'max_retries': 3,
            'retry_delay': 1,  # seconds
            'model': 'gemini-pro',
            'temperature': 0.1,
            'max_tokens': 4000,
            'rate_limit': {
                'requests_per_minute': 60,
                'tokens_per_minute': 32000,
            }
        },
        'spacy': {
            'enabled': True,
            'model': os.getenv('SPACY_MODEL', 'en_core_web_sm'),
            'timeout': 15,
            'batch_size': 1000,
            'n_process': 1,
            'custom_components': [],
        },
        'rule_based': {
            'enabled': True,
            'timeout': 5,
            'skill_keywords_file': 'skills_keywords.json',
            'patterns': {
                'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                'phone': r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                'linkedin': r'linkedin\.com/in/[\w-]+',
            }
        }
    },
    
    # Security
    'SECURITY': {
        'max_concurrent_uploads': 5,
        'rate_limiting': {
            'enabled': True,
            'requests_per_minute': 10,
            'burst_limit': 20,
        },
        'file_validation': {
            'check_magic_bytes': True,
            'scan_for_malware': False,  # Requires additional setup
        }
    },
    
    # Performance
    'PERFORMANCE': {
        'cache_ai_responses': False,  # Don't cache for privacy
        'async_processing': False,    # Future feature
        'memory_limit_mb': 512,
    },
    
    # Monitoring
    'MONITORING': {
        'metrics_enabled': True,
        'health_check_interval': 300,  # seconds
        'alert_thresholds': {
            'processing_time_seconds': 30,
            'error_rate_percent': 10,
            'temp_files_count': 100,
        }
    }
}
```

## Database Configuration

### Resume Parser Config Model

The system uses a database model for runtime configuration:

```python
# Admin interface configuration
from django.contrib import admin
from .models import ResumeParserConfig

@admin.register(ResumeParserConfig)
class ResumeParserConfigAdmin(admin.ModelAdmin):
    list_display = ['id', 'max_file_size_mb', 'default_backend', 'created_at', 'updated_at']
    fields = [
        'gemini_api_key',
        'max_file_size_mb',
        'default_backend',
        'spacy_model',
        'enable_debug_logging',
        'processing_timeout_seconds',
    ]
    
    def has_add_permission(self, request):
        # Only allow one configuration instance
        return not ResumeParserConfig.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of configuration
        return False
```

### Configuration Fields

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `gemini_api_key` | CharField | Google Gemini API key | Empty |
| `max_file_size_mb` | IntegerField | Maximum file size in MB | 10 |
| `default_backend` | CharField | Default processing backend | 'auto' |
| `spacy_model` | CharField | spaCy model name | 'en_core_web_sm' |
| `enable_debug_logging` | BooleanField | Enable debug logging | False |
| `processing_timeout_seconds` | IntegerField | Processing timeout | 60 |

## AI Backend Configuration

### Gemini AI Setup

1. **Get API Key:**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Copy the key to your environment variables

2. **Configure in Django:**
   ```python
   # settings.py
   RESUME_PARSER_SETTINGS['AI_BACKENDS']['gemini'] = {
       'enabled': True,
       'api_key': 'your_api_key_here',
       'timeout': 30,
       'max_retries': 3,
       'model': 'gemini-pro',
   }
   ```

3. **Test Configuration:**
   ```bash
   python manage.py shell
   >>> from roadmap.services.ai_processor import AIProcessor
   >>> processor = AIProcessor()
   >>> processor.test_gemini_connection()
   ```

### spaCy Setup

1. **Install spaCy Model:**
   ```bash
   # Install the model
   python -m spacy download en_core_web_sm
   
   # For better accuracy (larger model)
   python -m spacy download en_core_web_lg
   ```

2. **Configure Model:**
   ```python
   # settings.py
   RESUME_PARSER_SETTINGS['AI_BACKENDS']['spacy'] = {
       'enabled': True,
       'model': 'en_core_web_sm',  # or 'en_core_web_lg'
       'timeout': 15,
   }
   ```

3. **Test Configuration:**
   ```bash
   python manage.py shell
   >>> import spacy
   >>> nlp = spacy.load('en_core_web_sm')
   >>> doc = nlp("Test text")
   >>> print("spaCy model loaded successfully")
   ```

### Rule-based Backend

The rule-based backend requires no additional setup but can be customized:

```python
# Custom skill keywords file (optional)
# skills_keywords.json
{
    "programming_languages": [
        "Python", "JavaScript", "Java", "C++", "C#", "Ruby", "Go", "Rust"
    ],
    "frameworks": [
        "Django", "Flask", "React", "Angular", "Vue.js", "Spring", "Express"
    ],
    "databases": [
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch"
    ],
    "cloud_platforms": [
        "AWS", "Azure", "Google Cloud", "Heroku", "DigitalOcean"
    ]
}
```

## Performance Tuning

### File Processing Optimization

```python
# settings.py
RESUME_PARSER_SETTINGS.update({
    'PERFORMANCE': {
        # Memory management
        'memory_limit_mb': 512,
        'max_concurrent_uploads': 3,
        
        # Processing optimization
        'pdf_extraction_method': 'pdfplumber',  # or 'pypdf2'
        'text_preprocessing': {
            'remove_extra_whitespace': True,
            'normalize_unicode': True,
            'max_text_length': 50000,  # characters
        },
        
        # AI backend optimization
        'gemini_batch_size': 1,
        'spacy_batch_size': 100,
        'enable_caching': False,  # Privacy consideration
    }
})
```

### Resource Limits

```python
# Celery configuration for async processing (future feature)
CELERY_TASK_ROUTES = {
    'roadmap.tasks.process_resume': {'queue': 'resume_processing'},
}

CELERY_TASK_ANNOTATIONS = {
    'roadmap.tasks.process_resume': {
        'rate_limit': '10/m',
        'time_limit': 120,
        'soft_time_limit': 90,
    }
}
```

## Security Configuration

### File Upload Security

```python
# settings.py
RESUME_PARSER_SETTINGS.update({
    'SECURITY': {
        # File validation
        'allowed_mime_types': ['application/pdf'],
        'check_file_headers': True,
        'max_file_size_mb': 10,
        
        # Content security
        'scan_for_malicious_content': True,
        'sanitize_extracted_text': True,
        
        # Rate limiting
        'rate_limiting': {
            'enabled': True,
            'requests_per_minute': 10,
            'burst_limit': 20,
            'block_duration_minutes': 15,
        },
        
        # Temporary file security
        'temp_file_permissions': 0o600,
        'secure_temp_directory': True,
        'immediate_cleanup': True,
    }
})
```

### API Security

```python
# Future authentication configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10/min',
        'user': '60/min'
    }
}
```

## Monitoring and Logging

### Logging Configuration

```python
# Detailed logging setup
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '{levelname} {asctime} {name} {module} {funcName} {lineno} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'resume_parser_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/resume_parser.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'detailed',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/resume_parser_errors.log',
            'maxBytes': 10485760,
            'backupCount': 5,
            'formatter': 'detailed',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'roadmap': {
            'handlers': ['resume_parser_file', 'error_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'roadmap.services': {
            'handlers': ['resume_parser_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### Metrics Collection

```python
# Custom metrics (requires additional setup)
RESUME_PARSER_SETTINGS.update({
    'METRICS': {
        'enabled': True,
        'backend': 'prometheus',  # or 'statsd', 'cloudwatch'
        'metrics': [
            'processing_time',
            'file_size',
            'backend_usage',
            'error_rates',
            'confidence_scores',
        ],
        'export_interval': 60,  # seconds
    }
})
```

## Troubleshooting

### Common Configuration Issues

1. **Gemini API Key Issues:**
   ```bash
   # Test API key
   curl -H "Content-Type: application/json" \
        -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_API_KEY"
   ```

2. **spaCy Model Issues:**
   ```bash
   # Check installed models
   python -m spacy info
   
   # Reinstall model
   python -m spacy download en_core_web_sm --force
   ```

3. **File Permission Issues:**
   ```bash
   # Check temp directory permissions
   ls -la /tmp/
   
   # Fix permissions
   chmod 755 /tmp/resume_parser/
   ```

### Configuration Validation

```python
# Management command to validate configuration
# management/commands/validate_resume_parser_config.py

from django.core.management.base import BaseCommand
from roadmap.services.ai_processor import AIProcessor

class Command(BaseCommand):
    help = 'Validate Resume Parser configuration'
    
    def handle(self, *args, **options):
        processor = AIProcessor()
        
        # Test all backends
        for backend in ['gemini', 'spacy', 'rule_based']:
            try:
                status = processor.test_backend(backend)
                self.stdout.write(
                    self.style.SUCCESS(f'{backend}: {status}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'{backend}: {e}')
                )
```

Run validation:
```bash
python manage.py validate_resume_parser_config
```

## Best Practices

1. **Environment Variables:**
   - Use `.env` files for development
   - Use system environment variables for production
   - Never commit API keys to version control

2. **Performance:**
   - Start with smaller spaCy models for development
   - Use larger models in production for better accuracy
   - Monitor memory usage with large files

3. **Security:**
   - Regularly rotate API keys
   - Monitor file upload patterns
   - Implement rate limiting
   - Use HTTPS in production

4. **Monitoring:**
   - Set up log rotation
   - Monitor processing times
   - Track error rates
   - Alert on backend failures

5. **Backup:**
   - Backup configuration settings
   - Document custom configurations
   - Test configuration changes in staging first