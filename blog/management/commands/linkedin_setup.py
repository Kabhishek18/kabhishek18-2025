"""
Management command to help set up LinkedIn integration with guided token creation.
"""
from django.core.management.base import BaseCommand, CommandError
from blog.linkedin_models import LinkedInConfig
from blog.utils.encryption import credential_encryption
import getpass
import requests
import urllib.parse
import json


class Command(BaseCommand):
    help = 'Set up LinkedIn integration with guided token creation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--guide',
            action='store_true',
            help='Show step-by-step guide for creating LinkedIn app and tokens',
        )
        parser.add_argument(
            '--create-auth-url',
            action='store_true',
            help='Generate LinkedIn authorization URL',
        )
        parser.add_argument(
            '--exchange-token',
            action='store_true',
            help='Exchange authorization code for access token',
        )
        parser.add_argument(
            '--client-id',
            type=str,
            help='LinkedIn app Client ID',
        )
        parser.add_argument(
            '--client-secret',
            type=str,
            help='LinkedIn app Client Secret',
        )
        parser.add_argument(
            '--redirect-uri',
            type=str,
            help='Redirect URI configured in LinkedIn app',
        )
        parser.add_argument(
            '--auth-code',
            type=str,
            help='Authorization code from LinkedIn callback',
        )

    def handle(self, *args, **options):
        if options.get('guide'):
            self.show_guide()
        elif options.get('create_auth_url'):
            self.create_auth_url(options)
        elif options.get('exchange_token'):
            self.exchange_token(options)
        else:
            self.interactive_setup()

    def show_guide(self):
        """Show step-by-step guide for LinkedIn setup."""
        guide = """
🔗 LinkedIn Integration Setup Guide
=====================================

Step 1: Create LinkedIn App
---------------------------
1. Go to https://developer.linkedin.com/
2. Sign in and click "Create App"
3. Fill out app information:
   - App name: Your blog name
   - LinkedIn Page: Select your page
   - Privacy policy URL: Your privacy policy
4. Submit and wait for approval (1-2 days)

Step 2: Configure App Permissions
---------------------------------
1. Go to "Products" tab in your app
2. Request access to:
   - "Share on LinkedIn"
   - "Sign In with LinkedIn using OpenID Connect"
3. Wait for approval

Step 3: Get Credentials
----------------------
1. Go to "Auth" tab in your app
2. Note your Client ID and Client Secret
3. Add redirect URI: https://yourdomain.com/admin/linkedin/callback/

Step 4: Generate Access Token
----------------------------
Use this command to generate authorization URL:
  python manage.py linkedin_setup --create-auth-url --client-id YOUR_CLIENT_ID --redirect-uri YOUR_REDIRECT_URI

Then use this command to exchange code for token:
  python manage.py linkedin_setup --exchange-token --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET --redirect-uri YOUR_REDIRECT_URI --auth-code YOUR_CODE

Step 5: Configure Django
------------------------
Run: python manage.py linkedin_setup
Follow the prompts to enter your credentials.

For detailed instructions, see: LINKEDIN_ACCESS_TOKEN_GUIDE.md
        """
        self.stdout.write(guide)

    def create_auth_url(self, options):
        """Generate LinkedIn authorization URL."""
        client_id = options.get('client_id')
        redirect_uri = options.get('redirect_uri')

        if not client_id:
            client_id = input('Enter your LinkedIn Client ID: ').strip()
        
        if not redirect_uri:
            redirect_uri = input('Enter your redirect URI: ').strip()

        if not client_id or not redirect_uri:
            self.stdout.write(self.style.ERROR('Client ID and redirect URI are required'))
            return

        # LinkedIn OAuth scopes for posting and profile access
        scopes = [
            'profile',
            'w_member_social',
            'openid',
            'email'
        ]

        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': ' '.join(scopes),
            'state': 'linkedin_setup'  # CSRF protection
        }

        auth_url = 'https://www.linkedin.com/oauth/v2/authorization?' + urllib.parse.urlencode(params)

        self.stdout.write(self.style.SUCCESS('\n🔗 LinkedIn Authorization URL:'))
        self.stdout.write(f'\n{auth_url}\n')
        self.stdout.write('📋 Instructions:')
        self.stdout.write('1. Copy the URL above and open it in your browser')
        self.stdout.write('2. Sign in to LinkedIn and authorize your app')
        self.stdout.write('3. After authorization, copy the "code" parameter from the callback URL')
        self.stdout.write('4. Use the code with --exchange-token to get your access token\n')

    def exchange_token(self, options):
        """Exchange authorization code for access token."""
        client_id = options.get('client_id')
        client_secret = options.get('client_secret')
        redirect_uri = options.get('redirect_uri')
        auth_code = options.get('auth_code')

        # Get missing parameters interactively
        if not client_id:
            client_id = input('Enter your LinkedIn Client ID: ').strip()
        
        if not client_secret:
            client_secret = getpass.getpass('Enter your LinkedIn Client Secret: ').strip()
        
        if not redirect_uri:
            redirect_uri = input('Enter your redirect URI: ').strip()
        
        if not auth_code:
            auth_code = input('Enter the authorization code from LinkedIn callback: ').strip()

        if not all([client_id, client_secret, redirect_uri, auth_code]):
            self.stdout.write(self.style.ERROR('All parameters are required'))
            return

        # Exchange code for token
        self.stdout.write('🔄 Exchanging authorization code for access token...')
        
        token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
        data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri
        }

        try:
            response = requests.post(token_url, data=data, headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            })
            
            if response.status_code == 200:
                token_data = response.json()
                
                self.stdout.write(self.style.SUCCESS('✅ Successfully obtained access token!'))
                self.stdout.write('\n📋 Token Information:')
                self.stdout.write(f'Access Token: {token_data.get("access_token", "N/A")[:20]}...')
                self.stdout.write(f'Expires in: {token_data.get("expires_in", "N/A")} seconds')
                self.stdout.write(f'Refresh Token: {token_data.get("refresh_token", "N/A")[:20] if token_data.get("refresh_token") else "N/A"}...')
                
                # Ask if user wants to save to Django config
                save_config = input('\n💾 Save these credentials to Django configuration? (y/N): ').lower().strip()
                
                if save_config in ('y', 'yes'):
                    self.save_credentials(
                        client_id,
                        client_secret,
                        token_data.get('access_token'),
                        token_data.get('refresh_token'),
                        token_data.get('expires_in')
                    )
                else:
                    self.stdout.write('\n📝 Manual Configuration:')
                    self.stdout.write('Run: python manage.py linkedin_setup')
                    self.stdout.write('Or use Django admin to enter these credentials.')
                    
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                self.stdout.write(self.style.ERROR(f'❌ Token exchange failed: {response.status_code}'))
                self.stdout.write(f'Error: {error_data.get("error_description", response.text)}')
                
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f'❌ Network error: {e}'))
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR('❌ Invalid response from LinkedIn'))

    def save_credentials(self, client_id, client_secret, access_token, refresh_token=None, expires_in=None):
        """Save credentials to Django configuration."""
        try:
            # Get or create LinkedIn config
            config, created = LinkedInConfig.objects.get_or_create(
                defaults={
                    'client_id': client_id,
                    'is_active': False,  # Start inactive until user confirms
                    'enable_hashtags': True,
                    'max_hashtags': 5,
                    'enable_image_posting': True,
                    'image_posting_strategy': 'always'
                }
            )
            
            if not created:
                config.client_id = client_id
            
            # Set encrypted credentials
            config.set_client_secret(client_secret)
            config.set_access_token(access_token)
            
            if refresh_token:
                config.set_refresh_token(refresh_token)
            
            # Set token expiration
            if expires_in:
                from django.utils import timezone
                from datetime import timedelta
                config.token_expires_at = timezone.now() + timedelta(seconds=int(expires_in) - 300)  # 5 min buffer
            
            config.save()
            
            self.stdout.write(self.style.SUCCESS('✅ Credentials saved to Django configuration!'))
            self.stdout.write(f'Configuration ID: {config.id}')
            self.stdout.write('⚠️  Configuration is currently inactive.')
            
            activate = input('🔄 Activate LinkedIn integration now? (y/N): ').lower().strip()
            if activate in ('y', 'yes'):
                config.is_active = True
                config.save()
                self.stdout.write(self.style.SUCCESS('✅ LinkedIn integration activated!'))
                
                # Test the configuration
                self.stdout.write('🧪 Testing configuration...')
                validation = config.validate_credentials()
                if validation['errors']:
                    self.stdout.write(self.style.ERROR(f'❌ Validation errors: {validation["errors"]}'))
                else:
                    self.stdout.write(self.style.SUCCESS('✅ Configuration is valid and ready to use!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to save credentials: {e}'))

    def interactive_setup(self):
        """Interactive setup process."""
        self.stdout.write(self.style.SUCCESS('🔗 LinkedIn Integration Setup'))
        self.stdout.write('=' * 40)
        
        # Check if config exists
        configs = LinkedInConfig.objects.all()
        if configs.exists():
            self.stdout.write(f'Found {configs.count()} existing LinkedIn configuration(s)')
            for config in configs:
                self.stdout.write(f'  Config {config.id}: {config.client_id} (Active: {config.is_active})')
            
            update_existing = input('\nUpdate existing configuration? (y/N): ').lower().strip()
            if update_existing in ('y', 'yes'):
                config = configs.first()
            else:
                self.stdout.write('Creating new configuration...')
                config = LinkedInConfig()
        else:
            self.stdout.write('No existing configuration found. Creating new one...')
            config = LinkedInConfig()

        # Get credentials
        self.stdout.write('\n📋 Enter LinkedIn App Credentials:')
        
        client_id = input('Client ID: ').strip()
        if client_id:
            config.client_id = client_id
        
        client_secret = getpass.getpass('Client Secret: ').strip()
        if client_secret:
            config.set_client_secret(client_secret)
        
        access_token = getpass.getpass('Access Token: ').strip()
        if access_token:
            config.set_access_token(access_token)
        
        refresh_token = getpass.getpass('Refresh Token (optional): ').strip()
        if refresh_token:
            config.set_refresh_token(refresh_token)
        
        # Configuration options
        self.stdout.write('\n⚙️  Configuration Options:')
        
        enable_hashtags = input('Enable hashtag generation? (Y/n): ').lower().strip()
        config.enable_hashtags = enable_hashtags not in ('n', 'no')
        
        if config.enable_hashtags:
            max_hashtags = input('Maximum hashtags per post (default: 5): ').strip()
            config.max_hashtags = int(max_hashtags) if max_hashtags.isdigit() else 5
        
        enable_images = input('Enable image posting? (Y/n): ').lower().strip()
        config.enable_image_posting = enable_images not in ('n', 'no')
        
        # Save configuration
        try:
            config.save()
            self.stdout.write(self.style.SUCCESS('✅ Configuration saved!'))
            
            # Activate
            activate = input('🔄 Activate LinkedIn integration? (Y/n): ').lower().strip()
            if activate not in ('n', 'no'):
                config.is_active = True
                config.save()
                self.stdout.write(self.style.SUCCESS('✅ LinkedIn integration activated!'))
            
            # Test
            self.stdout.write('🧪 Testing configuration...')
            validation = config.validate_credentials()
            if validation['errors']:
                self.stdout.write(self.style.ERROR(f'❌ Validation errors: {validation["errors"]}'))
                self.stdout.write('💡 Tip: Use --guide to see setup instructions')
            else:
                self.stdout.write(self.style.SUCCESS('✅ Configuration is valid and ready to use!'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to save configuration: {e}'))

        self.stdout.write('\n🎉 Setup complete!')
        self.stdout.write('You can now post blog articles to LinkedIn from the Django admin.')