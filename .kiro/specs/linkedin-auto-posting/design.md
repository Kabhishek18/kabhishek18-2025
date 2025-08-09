# Design Document

## Overview

The LinkedIn auto-posting feature will integrate with the existing Django blog system to automatically post content to LinkedIn when blog posts are published. The system will use LinkedIn's API v2 for authentication and posting, following OAuth 2.0 flow for secure access.

The integration will be implemented as a Django service that hooks into the existing post publishing workflow through Django signals, ensuring minimal disruption to the current blog functionality.

## Architecture

### High-Level Components

1. **LinkedIn API Service** - Handles authentication and API communication
2. **LinkedIn Post Model** - Tracks posting attempts and results
3. **Signal Handler** - Triggers LinkedIn posting when posts are published
4. **Configuration Management** - Securely stores API credentials
5. **Admin Interface** - Provides visibility into posting status and configuration

### Integration Points

- **Django Signals**: Extends existing `post_save` signal handler in `blog/signals.py`
- **Blog Post Model**: Integrates with existing `Post` model without modification
- **Admin Interface**: Extends Django admin for configuration and monitoring
- **Celery Tasks**: Uses existing task infrastructure for asynchronous processing

## Components and Interfaces

### LinkedIn API Service

```python
class LinkedInAPIService:
    def authenticate(self) -> bool
    def create_post(self, title: str, content: str, url: str, image_url: str = None) -> dict
    def refresh_token(self) -> bool
    def get_user_profile(self) -> dict
```

**Responsibilities:**
- Handle OAuth 2.0 authentication flow
- Manage access token refresh
- Create LinkedIn posts via API
- Handle API rate limiting and errors

### LinkedIn Post Tracking Model

```python
class LinkedInPost(models.Model):
    post = ForeignKey(Post)
    linkedin_post_id = CharField()
    status = CharField(choices=['pending', 'success', 'failed'])
    error_message = TextField()
    attempt_count = IntegerField()
    created_at = DateTimeField()
    posted_at = DateTimeField()
```

**Responsibilities:**
- Track posting attempts for each blog post
- Store LinkedIn post IDs for reference
- Log errors and retry attempts
- Provide audit trail for admin interface

### LinkedIn Configuration Model

```python
class LinkedInConfig(models.Model):
    client_id = CharField()
    client_secret = CharField()  # Encrypted
    access_token = TextField()   # Encrypted
    refresh_token = TextField()  # Encrypted
    token_expires_at = DateTimeField()
    is_active = BooleanField()
```

**Responsibilities:**
- Store API credentials securely
- Manage token expiration
- Enable/disable LinkedIn integration

## Data Models

### LinkedIn Post Content Format

The system will format LinkedIn posts using this structure:

```
{title}

{excerpt}

Read more: {full_url}

#hashtags (derived from post tags)
```

### API Request Structure

LinkedIn API v2 posts will use this format:

```json
{
  "author": "urn:li:person:{person_id}",
  "lifecycleState": "PUBLISHED",
  "specificContent": {
    "com.linkedin.ugc.ShareContent": {
      "shareCommentary": {
        "text": "{formatted_content}"
      },
      "shareMediaCategory": "ARTICLE",
      "media": [
        {
          "status": "READY",
          "description": {
            "text": "{excerpt}"
          },
          "originalUrl": "{blog_post_url}",
          "title": {
            "text": "{title}"
          }
        }
      ]
    }
  },
  "visibility": {
    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
  }
}
```

## Error Handling

### Authentication Errors
- **Token Expired**: Attempt automatic refresh, fallback to admin notification
- **Invalid Credentials**: Log error, disable auto-posting, notify admin
- **OAuth Revoked**: Require re-authentication through admin interface

### API Errors
- **Rate Limiting**: Implement exponential backoff with jitter
- **Content Violations**: Log specific error, skip post, notify admin
- **Network Errors**: Retry up to 3 times with increasing delays
- **Server Errors**: Retry with exponential backoff

### Content Formatting Errors
- **Character Limits**: Truncate content intelligently at word boundaries
- **Invalid URLs**: Skip posting, log error with post details
- **Missing Required Fields**: Use fallback values or skip posting

## Testing Strategy

### Unit Tests
- LinkedIn API service methods
- Content formatting functions
- Error handling scenarios
- Token refresh logic
- Configuration validation

### Integration Tests
- End-to-end posting workflow
- Signal handler integration
- Admin interface functionality
- Database model relationships
- Celery task execution

### Mock Testing
- LinkedIn API responses (success/failure scenarios)
- Network timeout conditions
- Authentication flow simulation
- Rate limiting scenarios

### Test Data Requirements
- Sample blog posts with various content types
- Mock LinkedIn API responses
- Test credentials for development environment
- Edge case content (very long titles, special characters)

## Security Considerations

### Credential Storage
- Encrypt sensitive tokens using Django's `cryptography` library
- Store encryption keys in environment variables
- Rotate tokens according to LinkedIn's recommendations
- Implement secure key management practices

### API Security
- Validate all API responses before processing
- Sanitize content before sending to LinkedIn
- Implement request signing where required
- Use HTTPS for all API communications

### Access Control
- Restrict LinkedIn configuration to superuser access
- Log all configuration changes
- Implement audit trail for posting activities
- Secure admin interface with proper permissions

## Performance Considerations

### Asynchronous Processing
- Use Celery for non-blocking LinkedIn posting
- Implement proper task queuing and retry logic
- Monitor task execution and failure rates
- Set appropriate task timeouts

### Rate Limiting
- Respect LinkedIn's API rate limits (100 posts per day per user)
- Implement intelligent queuing for high-volume scenarios
- Cache authentication tokens to reduce API calls
- Monitor API usage and implement alerts

### Database Optimization
- Index frequently queried fields
- Implement proper foreign key relationships
- Use database-level constraints for data integrity
- Regular cleanup of old posting records

## Monitoring and Logging

### Logging Strategy
- Log all API interactions with appropriate detail levels
- Track posting success/failure rates
- Monitor authentication token refresh cycles
- Log configuration changes and admin actions

### Metrics Collection
- Track posting success rates
- Monitor API response times
- Count authentication failures
- Measure content formatting errors

### Alerting
- Notify admins of authentication failures
- Alert on high error rates
- Monitor token expiration approaching
- Track unusual API response patterns