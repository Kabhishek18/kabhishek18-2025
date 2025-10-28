# LinkedIn Token Automation - Zero Manual Intervention

## Problem Statement

LinkedIn access tokens expire every 60 days, requiring manual OAuth flow to renew. This creates maintenance overhead and potential service interruptions.

## Solution: Automated Token Management

### Approach 1: Automated OAuth Flow (Recommended)

Create a web endpoint that handles the complete OAuth flow automatically when tokens are about to expire.

#### Implementation

```python
# blog/views.py
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import requests
import urllib.parse
from .linkedin_models import LinkedInConfig
from .services.linkedin_service import LinkedInAPIService

class LinkedInTokenRenewalView(View):
    """Automated LinkedIn token renewal endpoint"""
    
    def get(self, request):
        """Initiate OAuth flow for token renewal"""
        config = LinkedInConfig.get_active_config()
        if not config:
            return JsonResponse({'error': 'No active LinkedIn configuration'}, status=400)
        
        # Generate authorization URL
        params = {
            'response_type': 'code',
            'client_id': config.client_id,
            'redirect_uri': request.build_absolute_uri('/linkedin/callback/'),
            'scope': 'profile w_member_social openid email',
            'state': f'renewal_{config.id}'
        }
        
        auth_url = 'https://www.linkedin.com/oauth/v2/authorization?' + urllib.parse.urlencode(params)
        return HttpResponseRedirect(auth_url)

@method_decorator(csrf_exempt, name='dispatch')
class LinkedInCallbackView(View):
    """Handle OAuth callback and update tokens"""
    
    def get(self, request):
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        
        if error:
            return JsonResponse({'error': f'OAuth error: {error}'}, status=400)
        
        if not code or not state.startswith('renewal_'):
            return JsonResponse({'error': 'Invalid callback parameters'}, status=400)
        
        # Extract config ID from state
        config_id = state.replace('renewal_', '')
        
        try:
            config = LinkedInConfig.objects.get(id=config_id)
        except LinkedInConfig.DoesNotExist:
            return JsonResponse({'error': 'Configuration not found'}, status=404)
        
        # Exchange code for tokens
        success = self.exchange_code_for_tokens(config, code, request)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': 'LinkedIn tokens renewed successfully',
                'expires_at': config.token_expires_at.isoformat() if config.token_expires_at else None
            })
        else:
            return JsonResponse({'error': 'Failed to renew tokens'}, status=500)
    
    def exchange_code_for_tokens(self, config, code, request):
        """Exchange authorization code for access tokens"""
        token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': config.client_id,
            'client_secret': config.get_client_secret(),
            'redirect_uri': request.build_absolute_uri('/linkedin/callback/')
        }
        
        try:
            response = requests.post(token_url, data=data, headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            })
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Update configuration with new tokens
                config.update_tokens(
                    access_token=token_data.get('access_token'),
                    refresh_token=token_data.get('refresh_token'),
                    expires_in=token_data.get('expires_in')
                )
                
                logger.info(f"Successfully renewed LinkedIn tokens for config {config.id}")
                return True
            else:
                logger.error(f"Token renewal failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Token renewal error: {e}")
            return False
```

#### URL Configuration

```python
# blog/urls.py or main urls.py
from django.urls import path
from .views import LinkedInTokenRenewalView, LinkedInCallbackView

urlpatterns = [
    # ... existing patterns
    path('linkedin/renew/', LinkedInTokenRenewalView.as_view(), name='linkedin_renew'),
    path('linkedin/callback/', LinkedInCallbackView.as_view(), name='linkedin_callback'),
]
```

### Approach 2: Automated Monitoring & Renewal

Create a system that automatically triggers token renewal before expiration.

#### Celery Task for Automated Renewal

```python
# blog/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import requests
import logging

logger = logging.getLogger(__name__)

@shared_task
def check_and_renew_linkedin_tokens():
    """Check all LinkedIn configurations and renew tokens if needed"""
    from .linkedin_models import LinkedInConfig
    
    configs = LinkedInConfig.objects.filter(is_active=True)
    
    for config in configs:
        if config.needs_token_refresh(buffer_days=7):  # Renew 7 days before expiration
            logger.info(f"LinkedIn token for config {config.id} needs renewal")
            
            # Try automatic renewal first
            if config.get_refresh_token():
                success = renew_with_refresh_token(config)
                if success:
                    logger.info(f"Successfully renewed token for config {config.id} using refresh token")
                    continue
            
            # If refresh token method fails, trigger OAuth flow
            trigger_oauth_renewal(config)

def renew_with_refresh_token(config):
    """Attempt to renew token using refresh token"""
    if not config.get_refresh_token():
        return False
    
    token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
    
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': config.get_refresh_token(),
        'client_id': config.client_id,
        'client_secret': config.get_client_secret()
    }
    
    try:
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            
            config.update_tokens(
                access_token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                expires_in=token_data.get('expires_in')
            )
            
            return True
        else:
            logger.error(f"Refresh token renewal failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Refresh token renewal error: {e}")
        return False

def trigger_oauth_renewal(config):
    """Trigger OAuth renewal process"""
    from django.core.mail import send_mail
    from django.conf import settings
    
    # Generate renewal URL
    renewal_url = f"{settings.SITE_URL}/linkedin/renew/"
    
    # Send notification with auto-renewal link
    send_mail(
        subject='LinkedIn Token Renewal Required',
        message=f'''
        Your LinkedIn integration token will expire soon.
        
        Click this link to automatically renew: {renewal_url}
        
        This is an automated message from your blog system.
        ''',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_EMAIL],
        fail_silently=False,
    )
    
    logger.info(f"Sent token renewal notification for config {config.id}")
```

#### Periodic Task Setup

```python
# settings.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'check-linkedin-tokens': {
        'task': 'blog.tasks.check_and_renew_linkedin_tokens',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
}
```

### Approach 3: Webhook-Based Renewal

Set up a webhook that can be triggered externally for token renewal.

#### Webhook Endpoint

```python
# blog/views.py
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import hmac
import hashlib
import json

@csrf_exempt
@require_http_methods(["POST"])
def linkedin_token_webhook(request):
    """Webhook endpoint for external token renewal triggers"""
    
    # Verify webhook signature (optional but recommended)
    if not verify_webhook_signature(request):
        return JsonResponse({'error': 'Invalid signature'}, status=403)
    
    try:
        data = json.loads(request.body)
        action = data.get('action')
        
        if action == 'renew_tokens':
            # Trigger token renewal process
            from .tasks import check_and_renew_linkedin_tokens
            check_and_renew_linkedin_tokens.delay()
            
            return JsonResponse({
                'success': True,
                'message': 'Token renewal process initiated'
            })
        else:
            return JsonResponse({'error': 'Unknown action'}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def verify_webhook_signature(request):
    """Verify webhook signature for security"""
    signature = request.headers.get('X-Webhook-Signature')
    if not signature:
        return False
    
    expected_signature = hmac.new(
        settings.WEBHOOK_SECRET.encode(),
        request.body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)
```

### Management Command for Manual Trigger

```python
# blog/management/commands/renew_linkedin_tokens.py
from django.core.management.base import BaseCommand
from blog.tasks import check_and_renew_linkedin_tokens

class Command(BaseCommand):
    help = 'Manually trigger LinkedIn token renewal check'
    
    def handle(self, *args, **options):
        self.stdout.write('Checking LinkedIn tokens for renewal...')
        check_and_renew_linkedin_tokens()
        self.stdout.write(self.style.SUCCESS('Token renewal check completed'))
```

## Deployment Configuration

### Environment Variables

```bash
# .env
SITE_URL=https://yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com
WEBHOOK_SECRET=your-secure-webhook-secret
```

### Cron Job Alternative (if not using Celery)

```bash
# Add to crontab
0 9 * * * cd /path/to/project && python manage.py renew_linkedin_tokens
```

### Monitoring Setup

```python
# blog/management/commands/linkedin_token_status.py
from django.core.management.base import BaseCommand
from blog.linkedin_models import LinkedInConfig
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Check LinkedIn token status and expiration'
    
    def handle(self, *args, **options):
        configs = LinkedInConfig.objects.filter(is_active=True)
        
        for config in configs:
            if config.token_expires_at:
                days_left = (config.token_expires_at - timezone.now()).days
                
                if days_left <= 7:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Config {config.id}: Token expires in {days_left} days'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Config {config.id}: Token valid for {days_left} days'
                        )
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Config {config.id}: No expiration date set')
                )
```

## Usage

### Setup
1. Add the views and URLs to your Django project
2. Configure Celery with the periodic task
3. Set up environment variables
4. Test the renewal endpoint

### Automatic Operation
- System checks tokens daily at 9 AM
- Sends email notification when renewal needed
- Provides one-click renewal link
- Automatically updates tokens after OAuth flow

### Manual Trigger
```bash
# Check token status
python manage.py linkedin_token_status

# Manually trigger renewal check
python manage.py renew_linkedin_tokens

# Or via webhook
curl -X POST https://yourdomain.com/webhook/linkedin-tokens/ \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: your-signature" \
  -d '{"action": "renew_tokens"}'
```

This solution eliminates manual intervention by:
1. **Proactive monitoring**: Checks tokens daily
2. **Automated notifications**: Emails when renewal needed
3. **One-click renewal**: Simple URL to complete OAuth flow
4. **Fallback mechanisms**: Multiple renewal methods
5. **Zero downtime**: Renews before expiration

The system ensures your LinkedIn integration never goes down due to expired tokens.