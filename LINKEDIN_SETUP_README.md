# LinkedIn Integration Setup Guide

## Overview

This guide walks you through setting up LinkedIn integration for automated blog post sharing. The system supports automatic posting, image handling, hashtag generation, and comprehensive error handling.

## Prerequisites

- Django project with LinkedIn integration models
- LinkedIn Developer Account
- Active LinkedIn Company/Personal Page
- SSL-enabled domain (required for production)

## Quick Start

### 1. LinkedIn App Setup

1. **Create LinkedIn App**
   - Go to [LinkedIn Developer Portal](https://developer.linkedin.com/)
   - Click "Create App"
   - Fill required information:
     - App name: Your blog/company name
     - LinkedIn Page: Select your page
     - Privacy policy URL: Your privacy policy
     - App logo: Upload your logo
   - Submit for review (1-2 business days)

2. **Configure App Permissions**
   - Go to "Products" tab
   - Request access to:
     - ✅ "Share on LinkedIn" 
     - ✅ "Sign In with LinkedIn using OpenID Connect"
   - Wait for approval (usually instant for basic permissions)

3. **Set Redirect URIs**
   - Go to "Auth" tab
   - Add redirect URI: `https://yourdomain.com/admin/linkedin/callback/`
   - For development: `http://localhost:8000/admin/linkedin/callback/`

### 2. Get Your Credentials

From the "Auth" tab in your LinkedIn app:
- **Client ID**: Copy this value
- **Client Secret**: Copy this value (keep secure!)

### 3. Django Integration Setup

#### Option A: Interactive Setup (Recommended)
```bash
python manage.py linkedin_setup
```
Follow the prompts to enter your credentials.

#### Option B: OAuth Flow Setup
```bash
# Step 1: Generate authorization URL
python manage.py linkedin_setup --create-auth-url \
  --client-id YOUR_CLIENT_ID \
  --redirect-uri https://yourdomain.com/admin/linkedin/callback/

# Step 2: Visit the URL, authorize, and copy the code from callback
# Step 3: Exchange code for tokens
python manage.py linkedin_setup --exchange-token \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET \
  --redirect-uri https://yourdomain.com/admin/linkedin/callback/ \
  --auth-code YOUR_AUTHORIZATION_CODE
```

### 4. Verify Setup

```bash
# Test API connectivity
python manage.py linkedin_operations test --verbose

# Check credential status
python manage.py linkedin_operations credentials status
```

## Configuration Options

### Hashtag Settings
- **Enable hashtags**: Automatic hashtag generation
- **Max hashtags**: Limit per post (recommended: 3-5)
- **Custom rules**: Category-specific hashtag rules
- **Blacklist**: Words to exclude from hashtags

### Image Posting Settings
- **Enable images**: Include featured images in posts
- **Strategy options**:
  - `always`: Include images when available
  - `never`: Text-only posts
  - `category_based`: Per-category rules

### Example Configuration
```python
# In Django admin or via management command
config = LinkedInConfig.objects.get(is_active=True)
config.enable_hashtags = True
config.max_hashtags = 5
config.enable_image_posting = True
config.image_posting_strategy = 'always'
config.save()
```

## Usage Commands

### Manual Posting
```bash
# Post single blog post
python manage.py linkedin_operations post 123

# Dry run (preview without posting)
python manage.py linkedin_operations post 123 --dry-run

# Force repost (even if already posted)
python manage.py linkedin_operations post 123 --force
```

### Bulk Posting
```bash
# Post last 10 published posts
python manage.py linkedin_operations bulk --limit 10 --delay 30

# Post from last 7 days
python manage.py linkedin_operations bulk --days 7 --delay 60

# Post specific category
python manage.py linkedin_operations bulk --category "technology" --limit 5

# Dry run bulk operation
python manage.py linkedin_operations bulk --dry-run --limit 5
```

### Monitoring
```bash
# Show recent posting activity
python manage.py linkedin_operations status --recent 20

# Show posting statistics
python manage.py linkedin_operations status --stats

# Show failed posts
python manage.py linkedin_operations status --failed

# Show pending retries
python manage.py linkedin_operations status --pending
```

### Credential Management
```bash
# Validate credentials
python manage.py linkedin_operations credentials validate

# Check credential status
python manage.py linkedin_operations credentials status

# Refresh access token (if refresh token available)
python manage.py linkedin_operations credentials refresh
```

## Production Deployment

### Environment Variables
```bash
# Optional: Set in your environment
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
```

### Rate Limiting
- LinkedIn allows 100 posts per day per user
- Use `--delay` parameter for bulk operations (recommended: 30-60 seconds)
- Monitor quota with `test` command

### Error Handling
- Failed posts automatically retry with exponential backoff
- Maximum 3 retry attempts per post
- Check retry status with `status --pending`

### Monitoring Setup
```bash
# Daily credential check (cron job)
0 9 * * * cd /path/to/project && python manage.py linkedin_operations credentials validate

# Weekly bulk posting
0 10 * * 1 cd /path/to/project && python manage.py linkedin_operations bulk --days 7 --delay 60

# Daily status check
0 18 * * * cd /path/to/project && python manage.py linkedin_operations status --stats
```

## Token Management

### Access Token Lifecycle
- **Duration**: 60 days for most LinkedIn apps
- **Renewal**: Re-run OAuth flow before expiration
- **Monitoring**: Check expiration with `credentials status`

### Renewal Process
1. **Set reminder** 1 week before expiration
2. **Run OAuth flow** again:
   ```bash
   python manage.py linkedin_setup --create-auth-url --client-id YOUR_CLIENT_ID --redirect-uri YOUR_REDIRECT_URI
   ```
3. **Update credentials** with new tokens

### Refresh Tokens
- Not all LinkedIn apps receive refresh tokens
- If available, automatic refresh is handled by the system
- Manual renewal required for apps without refresh tokens

## Troubleshooting

### Common Issues

**"redirect_uri_mismatch" Error**
- Ensure redirect URI in command matches LinkedIn app configuration exactly
- Check for trailing slashes and protocol (http vs https)

**"insufficient_permissions" Error**
- Verify app has "Share on LinkedIn" permission
- Check if app is approved for production use

**"token_expired" Error**
- Run credential validation: `python manage.py linkedin_operations credentials validate`
- Renew tokens if expired

**"quota_exceeded" Error**
- Check daily quota: `python manage.py linkedin_operations test`
- Wait 24 hours or reduce posting frequency

### Debug Mode
```bash
# Enable verbose logging
python manage.py linkedin_operations test --verbose

# Check specific post formatting
python manage.py linkedin_operations post 123 --dry-run
```

### Support Channels
- Check Django logs for detailed error messages
- Use `--verbose` flag for detailed output
- Monitor LinkedIn Developer Console for app status

## Security Best Practices

### Credential Protection
- Store credentials encrypted (handled automatically)
- Use environment variables for sensitive data
- Rotate tokens regularly
- Monitor access logs

### Access Control
- Limit LinkedIn app permissions to minimum required
- Use separate apps for development/production
- Regular security audits of app permissions

### Network Security
- Use HTTPS for all redirect URIs
- Validate SSL certificates
- Monitor for suspicious API activity

## Advanced Configuration

### Custom Hashtag Rules
```json
{
  "technology": {
    "required_hashtags": ["#Tech", "#Programming"],
    "suggested_hashtags": ["#Development", "#Coding"],
    "max_hashtags": 4
  },
  "business": {
    "required_hashtags": ["#Business"],
    "max_hashtags": 3
  }
}
```

### Category Image Overrides
```json
{
  "tutorials": {"enable_images": true},
  "news": {"enable_images": false},
  "reviews": {"enable_images": true, "strategy": "always"}
}
```

### Performance Optimization
- Use `--delay` for bulk operations
- Monitor API response times
- Cache configuration settings
- Batch similar operations

## Integration Examples

### With CI/CD Pipeline
```yaml
# .github/workflows/linkedin-posting.yml
name: LinkedIn Auto-Post
on:
  schedule:
    - cron: '0 10 * * 1'  # Weekly on Monday
jobs:
  post-to-linkedin:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
      - name: Post to LinkedIn
        run: |
          python manage.py linkedin_operations bulk --days 7 --delay 60
```

### With Django Signals
```python
# In your models.py or signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Post

@receiver(post_save, sender=Post)
def auto_post_to_linkedin(sender, instance, created, **kwargs):
    if instance.status == 'published' and instance.auto_share_linkedin:
        # Queue for LinkedIn posting
        from django_rq import get_queue
        queue = get_queue('default')
        queue.enqueue('blog.tasks.post_to_linkedin', instance.id)
```

## FAQ

**Q: How often can I post to LinkedIn?**
A: LinkedIn allows 100 posts per day per user. For best engagement, limit to 1-3 posts per day.

**Q: What image formats are supported?**
A: LinkedIn supports JPEG, PNG, and GIF. Images are automatically optimized for LinkedIn's requirements.

**Q: Can I schedule posts for later?**
A: The current system posts immediately. For scheduling, integrate with a task queue like Celery or Django-RQ.

**Q: How do I handle multiple LinkedIn accounts?**
A: Create separate LinkedIn apps and configurations for each account. Only one can be active at a time per Django instance.

**Q: What happens if posting fails?**
A: Failed posts automatically retry up to 3 times with exponential backoff. Check status with `linkedin_operations status --failed`.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Django logs for error details
3. Use `--verbose` flag for detailed debugging
4. Check LinkedIn Developer Console for app status

---

*Last updated: October 2025*