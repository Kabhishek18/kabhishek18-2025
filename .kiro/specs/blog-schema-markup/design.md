# Design Document

## Overview

This design implements JSON-LD schema markup for blog posts to enhance SEO and enable rich results in search engines. The solution will automatically generate structured data for each blog post using Django template tags and context processors, ensuring compliance with Schema.org specifications while maintaining performance and maintainability.

## Architecture

### Component Structure
```
blog/
├── templatetags/
│   └── schema_tags.py          # Custom template tags for schema generation
├── services/
│   └── schema_service.py       # Core schema generation logic
├── context_processors.py       # Global schema context (if needed)
└── templates/
    └── blog/
        └── partials/
            └── schema_markup.html  # Schema markup template
```

### Integration Points
- **Template Integration**: Schema markup will be included in the `<head>` section of blog detail pages
- **Model Integration**: Leverages existing Post, AuthorProfile, Category, and Tag models
- **URL Integration**: Uses Django's `build_absolute_uri()` for generating absolute URLs
- **Media Integration**: Incorporates featured images and media items from existing MediaItem model

## Components and Interfaces

### 1. Schema Service (`blog/services/schema_service.py`)

**Purpose**: Core business logic for generating schema markup data

**Key Methods**:
```python
class SchemaService:
    @staticmethod
    def generate_article_schema(post, request) -> dict
    
    @staticmethod
    def generate_author_schema(author_profile) -> dict
    
    @staticmethod
    def generate_publisher_schema() -> dict
    
    @staticmethod
    def generate_breadcrumb_schema(post, request) -> dict
    
    @staticmethod
    def validate_schema(schema_data) -> bool
```

**Dependencies**: 
- Django models (Post, AuthorProfile, Category, Tag, MediaItem)
- Django request object for absolute URL generation
- Settings for publisher information

### 2. Template Tags (`blog/templatetags/schema_tags.py`)

**Purpose**: Provide template-level interface for schema generation

**Key Template Tags**:
```python
@register.inclusion_tag('blog/partials/schema_markup.html', takes_context=True)
def render_article_schema(context, post)

@register.simple_tag(takes_context=True)
def get_article_schema_json(context, post)

@register.filter
def to_schema_date(date_value)
```

### 3. Schema Markup Template (`templates/blog/partials/schema_markup.html`)

**Purpose**: Render JSON-LD markup in HTML

**Structure**:
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{{ schema.headline }}",
  "author": {{ schema.author|safe }},
  "publisher": {{ schema.publisher|safe }},
  "datePublished": "{{ schema.datePublished }}",
  "dateModified": "{{ schema.dateModified }}",
  "image": {{ schema.image|safe }},
  "articleSection": {{ schema.articleSection|safe }},
  "keywords": {{ schema.keywords|safe }},
  "url": "{{ schema.url }}"
}
</script>
```

## Data Models

### Schema Data Structure

**Article Schema**:
```python
{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": str,           # Post title (max 110 chars for SEO)
    "author": {
        "@type": "Person",
        "name": str,
        "url": str,           # Author profile URL if available
        "sameAs": [str]       # Social media profiles
    },
    "publisher": {
        "@type": "Organization",
        "name": str,
        "logo": {
            "@type": "ImageObject",
            "url": str
        }
    },
    "datePublished": str,     # ISO 8601 format
    "dateModified": str,      # ISO 8601 format
    "image": [str],          # Array of image URLs
    "articleSection": [str],  # Categories
    "keywords": [str],       # Tags
    "url": str,              # Canonical URL
    "wordCount": int,        # Calculated from content
    "timeRequired": str,     # Reading time in ISO 8601 duration format
    "description": str       # Post excerpt or meta description
}
```

**Publisher Schema**:
```python
{
    "@type": "Organization",
    "name": "Digital Codex",
    "logo": {
        "@type": "ImageObject",
        "url": "https://kabhishek18.com/static/web-app-manifest-512x512.png",
        "width": 512,
        "height": 512
    },
    "url": "https://kabhishek18.com",
    "sameAs": [
        "https://twitter.com/kabhishek18",
        "https://linkedin.com/in/kabhishek18"
    ]
}
```

## Error Handling

### Schema Generation Errors
- **Missing Required Fields**: Graceful fallbacks for missing post data
- **Invalid URLs**: Validation and fallback to site root
- **Image Processing**: Handle missing or invalid images
- **Date Formatting**: Ensure ISO 8601 compliance

### Template Integration Errors
- **Template Tag Failures**: Silent failures with logging
- **JSON Serialization**: Handle special characters and encoding
- **Context Missing**: Fallback to minimal schema

### Validation Strategy
- **Schema.org Compliance**: Validate against required properties
- **Google Rich Results**: Test compatibility with Google's requirements
- **Performance Impact**: Monitor template rendering time

## Testing Strategy

### Unit Tests
- **Schema Generation**: Test all schema generation methods
- **Template Tags**: Test template tag functionality
- **Data Validation**: Test schema validation logic
- **Edge Cases**: Test with missing or invalid data

### Integration Tests
- **Template Rendering**: Test schema markup in actual templates
- **URL Generation**: Test absolute URL generation
- **Media Integration**: Test image and media inclusion

### Validation Tests
- **Schema.org Validator**: Automated validation against Schema.org
- **Google Rich Results Test**: Integration with Google's testing tool
- **JSON-LD Validation**: Ensure valid JSON-LD format

### Performance Tests
- **Template Rendering Time**: Measure impact on page load
- **Database Queries**: Ensure no N+1 query problems
- **Caching Strategy**: Test caching effectiveness

## Implementation Considerations

### Performance Optimizations
- **Template Fragment Caching**: Cache generated schema markup
- **Database Query Optimization**: Use select_related and prefetch_related
- **Lazy Loading**: Generate schema only when needed

### SEO Best Practices
- **Headline Length**: Truncate titles to 110 characters for optimal display
- **Image Requirements**: Ensure images meet Google's size requirements
- **Required vs Optional Fields**: Prioritize required schema properties

### Maintenance and Monitoring
- **Schema Updates**: Handle Schema.org specification changes
- **Error Logging**: Log schema generation failures
- **Performance Monitoring**: Track template rendering performance
- **Validation Monitoring**: Regular validation checks

### Security Considerations
- **XSS Prevention**: Proper escaping of user-generated content
- **URL Validation**: Validate and sanitize URLs
- **Content Sanitization**: Clean HTML content for schema inclusion