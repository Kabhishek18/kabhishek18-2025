# Design Document

## Overview

This design enhances the existing LinkedIn auto-posting system to include image support for both direct LinkedIn posts and link preview optimization. The solution extends the current LinkedInAPIService and LinkedInContentFormatter to handle image upload, processing, and integration while maintaining backward compatibility with the existing text-only posting functionality.

## Architecture

### Component Structure
```
blog/
├── services/
│   ├── linkedin_service.py           # Enhanced with image upload methods
│   ├── linkedin_content_formatter.py # Enhanced with image processing
│   └── linkedin_image_service.py     # New service for image handling
├── utils/
│   └── image_processor.py            # New utility for image processing
└── templates/
    └── blog/
        └── partials/
            └── social_meta_tags.html # Enhanced Open Graph tags
```

### Integration Points
- **LinkedIn API v2**: Uses the media upload and UGC posts endpoints
- **Existing Models**: Leverages Post, MediaItem, and LinkedInPost models
- **Image Processing**: Integrates with Django's ImageField and PIL for image manipulation
- **Open Graph Tags**: Enhances existing meta tags for better link previews

## Components and Interfaces

### 1. LinkedIn Image Service (`blog/services/linkedin_image_service.py`)

**Purpose**: Handle image processing and upload for LinkedIn posts

**Key Methods**:
```python
class LinkedInImageService:
    @staticmethod
    def get_post_image(blog_post) -> Optional[str]
    
    @staticmethod
    def validate_image_for_linkedin(image_url: str) -> Tuple[bool, List[str]]
    
    @staticmethod
    def upload_image_to_linkedin(image_url: str, config: LinkedInConfig) -> str
    
    @staticmethod
    def process_image_for_linkedin(image_path: str) -> str
    
    @staticmethod
    def get_image_metadata(image_url: str) -> Dict[str, Any]
```

### 2. Enhanced LinkedIn API Service

**New Methods**:
```python
class LinkedInAPIService:
    def upload_media(self, image_url: str) -> str
    def create_post_with_media(self, title: str, content: str, url: str, media_id: str) -> Dict
    def create_image_carousel_post(self, title: str, content: str, url: str, media_ids: List[str]) -> Dict
```

### 3. Image Processor Utility (`blog/utils/image_processor.py`)

**Purpose**: Handle image validation, resizing, and format conversion

**Key Methods**:
```python
class ImageProcessor:
    @staticmethod
    def validate_image_dimensions(image_path: str) -> Tuple[bool, Dict[str, int]]
    
    @staticmethod
    def resize_image_for_linkedin(image_path: str, output_path: str) -> str
    
    @staticmethod
    def convert_image_format(image_path: str, target_format: str) -> str
    
    @staticmethod
    def optimize_image_for_web(image_path: str) -> str
```

### 4. Enhanced Content Formatter

**New Methods**:
```python
class LinkedInContentFormatter:
    def get_post_images(self, blog_post) -> List[str]
    def select_best_image_for_linkedin(self, blog_post) -> Optional[str]
    def validate_image_compatibility(self, image_url: str) -> bool
```

## Data Models

### Enhanced LinkedInPost Model

**New Fields**:
```python
class LinkedInPost(models.Model):
    # Existing fields...
    
    # New image-related fields
    media_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="LinkedIn media IDs for uploaded images"
    )
    image_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="Original image URLs that were processed"
    )
    image_upload_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('skipped', 'Skipped'),
        ],
        default='pending',
        help_text="Status of image upload process"
    )
    image_error_message = models.TextField(
        blank=True,
        help_text="Error message if image upload failed"
    )
```

### LinkedIn Image Requirements

**Supported Formats**: JPEG, PNG, GIF
**Dimensions**: 
- Minimum: 200x200 pixels
- Maximum: 7680x4320 pixels
- Recommended: 1200x627 pixels for optimal display
**File Size**: Maximum 20MB per image
**Aspect Ratios**: 1.91:1 to 1:1.91 (landscape to portrait)

## Error Handling

### Image Processing Errors
- **Invalid Format**: Convert to supported format or skip with warning
- **Size Limits**: Resize images that exceed LinkedIn limits
- **Network Errors**: Retry image download with exponential backoff
- **Processing Failures**: Fall back to text-only posting

### LinkedIn API Errors
- **Media Upload Failures**: Log detailed error and continue with text post
- **Quota Limits**: Track image upload quota separately from post quota
- **Authentication Issues**: Handle media-specific permission errors

### Fallback Strategies
- **Primary Image Fails**: Try alternative images from MediaItem
- **All Images Fail**: Post text-only content with detailed logging
- **Partial Success**: Post with available images, log failed ones

## Testing Strategy

### Unit Tests
- **Image Selection Logic**: Test image prioritization and selection
- **Image Processing**: Test resizing, format conversion, and optimization
- **LinkedIn API Integration**: Mock API calls for image upload testing
- **Error Handling**: Test all failure scenarios and fallbacks

### Integration Tests
- **End-to-End Posting**: Test complete flow from blog post to LinkedIn with images
- **Image Processing Pipeline**: Test image download, processing, and upload
- **Open Graph Integration**: Test meta tag generation and LinkedIn preview

### Performance Tests
- **Image Processing Time**: Measure image processing performance
- **Memory Usage**: Monitor memory usage during image processing
- **API Rate Limits**: Test image upload quota management

## Implementation Considerations

### Performance Optimizations
- **Async Image Processing**: Process images asynchronously to avoid blocking
- **Image Caching**: Cache processed images to avoid reprocessing
- **Lazy Loading**: Only process images when LinkedIn posting is triggered
- **Batch Processing**: Handle multiple images efficiently

### Security Considerations
- **Image Validation**: Validate image content and metadata
- **URL Sanitization**: Ensure image URLs are safe and accessible
- **File Size Limits**: Enforce reasonable file size limits
- **Content Filtering**: Basic validation for inappropriate content

### LinkedIn API Compliance
- **Rate Limiting**: Respect LinkedIn's image upload rate limits
- **Content Policies**: Ensure images comply with LinkedIn's content policies
- **Media Retention**: Handle LinkedIn's media retention policies
- **API Versioning**: Use stable LinkedIn API endpoints for media

### Open Graph Enhancement

**Meta Tags Structure**:
```html
<meta property="og:image" content="{{ image_url }}" />
<meta property="og:image:width" content="{{ image_width }}" />
<meta property="og:image:height" content="{{ image_height }}" />
<meta property="og:image:type" content="{{ image_type }}" />
<meta property="og:image:alt" content="{{ image_alt }}" />
```

### Monitoring and Logging

**Image Processing Metrics**:
- Image processing success/failure rates
- Average processing time per image
- Image format distribution
- Size optimization statistics

**LinkedIn Integration Metrics**:
- Image upload success rates
- Media ID tracking
- Post engagement with vs without images
- Error categorization and frequency

### Configuration Options

**Settings Integration**:
```python
LINKEDIN_IMAGE_SETTINGS = {
    'ENABLE_IMAGE_UPLOAD': True,
    'MAX_IMAGES_PER_POST': 1,  # LinkedIn supports 1 image per post
    'IMAGE_QUALITY': 85,
    'RESIZE_LARGE_IMAGES': True,
    'FALLBACK_TO_TEXT_ONLY': True,
    'CACHE_PROCESSED_IMAGES': True,
}
```

### Backward Compatibility

- Existing text-only posting continues to work unchanged
- New image functionality is opt-in via configuration
- Graceful degradation when image processing fails
- No breaking changes to existing LinkedInPost model structure