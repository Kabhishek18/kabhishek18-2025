# Design Document

## Overview

This design enhances the existing LinkedIn posting functionality by adding hashtag support and configurable image posting options. The solution builds upon the current LinkedIn integration architecture, extending the `LinkedInConfig` model with new configuration fields and enhancing the `LinkedInContentFormatter` service to handle hashtag generation and image posting preferences.

## Architecture

The enhancement follows the existing service-oriented architecture pattern used in the LinkedIn integration:

- **Model Layer**: Extend `LinkedInConfig` with hashtag and image posting configuration fields
- **Service Layer**: Enhance `LinkedInContentFormatter` with hashtag generation logic and image posting controls
- **Admin Layer**: Add admin interface controls for managing hashtag rules and image posting settings

## Components and Interfaces

### 1. Enhanced LinkedInConfig Model

**Location**: `blog/linkedin_models.py`

**New Fields**:
```python
# Hashtag Configuration
enable_hashtags = models.BooleanField(default=True, help_text="Enable automatic hashtag generation")
max_hashtags = models.PositiveIntegerField(default=5, help_text="Maximum number of hashtags per post")
custom_hashtag_rules = models.JSONField(default=dict, help_text="Custom hashtag rules per category")
hashtag_blacklist = models.JSONField(default=list, help_text="Words to exclude from hashtag generation")

# Image Posting Configuration  
enable_image_posting = models.BooleanField(default=True, help_text="Include images in LinkedIn posts")
image_posting_strategy = models.CharField(max_length=20, choices=[
    ('always', 'Always include images when available'),
    ('never', 'Never include images (text-only posts)'),
    ('category_based', 'Based on post category settings')
], default='always', help_text="Strategy for including images in posts")
```

**Methods**:
- `get_hashtag_config()`: Returns hashtag configuration as dictionary
- `get_image_posting_config()`: Returns image posting configuration
- `should_include_images(blog_post)`: Determines if images should be included for a specific post
- `get_hashtags_for_category(category)`: Gets custom hashtags for a category

### 2. Enhanced LinkedInContentFormatter Service

**Location**: `blog/services/linkedin_content_formatter.py`

**New Methods**:
- `generate_hashtags_with_config(blog_post, config)`: Generate hashtags based on configuration
- `apply_hashtag_rules(hashtags, rules)`: Apply custom hashtag rules
- `filter_blacklisted_hashtags(hashtags, blacklist)`: Remove blacklisted terms
- `format_post_with_config(blog_post, config)`: Format post content with configuration options

**Enhanced Methods**:
- `_generate_hashtags(blog_post)`: Enhanced to use configuration settings
- `format_post_content(blog_post, include_excerpt, optimize_for_images)`: Enhanced to respect image posting configuration

### 3. Hashtag Generation Engine

**Location**: `blog/services/linkedin_content_formatter.py` (new class)

**Class**: `HashtagGenerator`

**Methods**:
- `generate_from_tags(blog_post, max_count)`: Generate hashtags from post tags
- `generate_from_categories(blog_post, max_count)`: Generate hashtags from post categories
- `generate_from_content(blog_post, max_count)`: Extract hashtags from post content
- `apply_custom_rules(hashtags, category_rules)`: Apply category-specific hashtag rules
- `validate_hashtag(hashtag)`: Validate hashtag format for LinkedIn
- `prioritize_hashtags(hashtags, priority_rules)`: Sort hashtags by priority

### 4. Image Posting Controller

**Location**: `blog/services/linkedin_content_formatter.py` (enhanced)

**Methods**:
- `should_include_image(blog_post, config)`: Determine if image should be included
- `get_image_posting_strategy(blog_post, config)`: Get strategy for specific post
- `format_content_for_strategy(blog_post, strategy)`: Format content based on strategy

## Data Models

### LinkedInConfig Extensions

```python
# Hashtag configuration structure
hashtag_config = {
    "enable_hashtags": True,
    "max_hashtags": 5,
    "custom_rules": {
        "technology": ["#TechTips", "#Programming", "#Development"],
        "tutorial": ["#Tutorial", "#HowTo", "#Learning"]
    },
    "blacklist": ["spam", "clickbait", "urgent"],
    "priority_tags": ["featured", "important"]
}

# Image posting configuration structure  
image_config = {
    "enable_image_posting": True,
    "strategy": "always",  # always, never, category_based
    "category_overrides": {
        "news": False,  # Never include images for news posts
        "tutorial": True  # Always include images for tutorials
    }
}
```

### Hashtag Generation Rules

```python
# Category-based hashtag rules
category_hashtag_rules = {
    "category_slug": {
        "required_hashtags": ["#CategoryTag"],  # Always include these
        "suggested_hashtags": ["#Related1", "#Related2"],  # Include if space allows
        "max_hashtags": 3,  # Override global max for this category
        "priority": 1  # Higher priority categories get preference
    }
}
```

## Error Handling

### Hashtag Generation Errors
- **Invalid hashtag format**: Log warning and skip invalid hashtags
- **No hashtags generated**: Continue with post without hashtags
- **Configuration errors**: Fall back to default hashtag generation

### Image Posting Errors
- **Image unavailable**: Fall back to text-only posting
- **Configuration conflicts**: Use global default settings
- **Image processing failures**: Continue with text-only post and log error

### Fallback Strategies
1. **Hashtag fallback**: Use post tags as hashtags if custom rules fail
2. **Image fallback**: Gracefully degrade to text-only posts if image posting fails
3. **Configuration fallback**: Use system defaults if user configuration is invalid

## Testing Strategy

### Unit Tests
- **HashtagGenerator**: Test hashtag generation from various sources
- **LinkedInConfig**: Test configuration validation and retrieval methods
- **LinkedInContentFormatter**: Test enhanced formatting with new options

### Integration Tests
- **End-to-end posting**: Test complete posting flow with hashtags and images
- **Configuration scenarios**: Test different configuration combinations
- **Fallback scenarios**: Test error handling and fallback mechanisms

### Test Cases
1. **Hashtag generation from tags**: Verify hashtags are correctly generated from post tags
2. **Custom hashtag rules**: Test category-specific hashtag rules
3. **Hashtag blacklist**: Verify blacklisted terms are excluded
4. **Image posting configuration**: Test different image posting strategies
5. **Mixed configuration**: Test posts with both hashtags and image settings
6. **Error scenarios**: Test behavior when hashtag generation or image processing fails

### Performance Tests
- **Hashtag generation performance**: Ensure hashtag generation doesn't slow down posting
- **Image processing impact**: Verify image posting configuration doesn't affect performance
- **Configuration lookup**: Test configuration retrieval performance

## Implementation Notes

### Backward Compatibility
- All new fields have sensible defaults to maintain existing functionality
- Existing posts will continue to work without modification
- New features are opt-in through configuration

### Security Considerations
- Hashtag blacklist prevents injection of inappropriate terms
- Configuration validation prevents malformed rules
- Image posting respects existing image security measures

### Performance Considerations
- Hashtag generation is cached per post to avoid repeated processing
- Configuration is loaded once per posting session
- Image posting decisions are made early to avoid unnecessary processing

### Migration Strategy
- Database migration adds new fields with defaults
- Existing configurations are automatically updated with default values
- Admin interface is enhanced to support new configuration options