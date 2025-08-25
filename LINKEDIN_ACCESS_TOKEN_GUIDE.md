# LinkedIn Access Token Creation Guide

## Overview

To integrate your blog with LinkedIn, you need to create a LinkedIn app and obtain API credentials. This guide walks you through the entire process.

## Step 1: Create a LinkedIn App

### 1.1 Go to LinkedIn Developer Portal
1. Visit [LinkedIn Developer Portal](https://developer.linkedin.com/)
2. Sign in with your LinkedIn account
3. Click "Create App"

### 1.2 Fill Out App Information
- **App name**: Your blog name (e.g., "My Tech Blog")
- **LinkedIn Page**: Select your company/personal page (required)
- **Privacy policy URL**: Your blog's privacy policy URL
- **App logo**: Upload a logo (optional but recommended)
- **Legal agreement**: Check the box to agree

### 1.3 Submit for Review
- Click "Create app"
- Your app will be created and you'll be redirected to the app dashboard

## Step 2: Configure App Permissions

### 2.1 Products Tab
1. Go to the "Products" tab in your app dashboard
2. Request access to:
   - **Share on LinkedIn** (for posting content)
   - **Sign In with LinkedIn using OpenID Connect** (for authentication)

### 2.2 Wait for Approval
- LinkedIn will review your request (usually takes 1-2 business days)
- You'll receive an email when approved

## Step 3: Get Your Credentials

### 3.1 Auth Tab
1. Go to the "Auth" tab in your app dashboard
2. Note down:
   - **Client ID**: This is your app's public identifier
   - **Client Secret**: This is your app's private key (keep it secure!)

### 3.2 Configure Redirect URLs
1. In the "Auth" tab, scroll to "Authorized redirect URLs for your app"
2. Add your callback URL:
   ```
   https://yourdomain.com/admin/linkedin/callback/
   ```
   Replace `yourdomain.com` with your actual domain

## Step 4: Generate Access Token

### 4.1 Authorization URL
Create an authorization URL with these parameters:

```
https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&scope=profile%20w_member_social%20openid%20email
```

Replace:
- `YOUR_CLIENT_ID`: Your app's Client ID
- `YOUR_REDIRECT_URI`: Your encoded redirect URI

### 4.2 Get Authorization Code
1. Visit the authorization URL in your browser
2. LinkedIn will ask you to authorize your app
3. After authorization, you'll be redirected to your callback URL with a `code` parameter
4. Copy this authorization code (it expires in 10 minutes)

### 4.3 Exchange Code for Access Token
Make a POST request to exchange the code for an access token:

```bash
curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=YOUR_AUTHORIZATION_CODE" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=YOUR_REDIRECT_URI"
```

### 4.4 Response
You'll receive a JSON response like:
```json
{
  "access_token": "AQV...",
  "expires_in": 5184000,
  "refresh_token": "AQW...",
  "refresh_token_expires_in": 31536000,
  "scope": "profile,w_member_social"
}
```

## Step 5: Configure Your Django App

### 5.1 Using Management Command
```bash
python manage.py fix_linkedin_credentials --set-credentials
```

Enter when prompted:
- **Client Secret**: From Step 3.1
- **Access Token**: From Step 4.4
- **Refresh Token**: From Step 4.4 (optional but recommended)

### 5.2 Using Django Admin
1. Go to `/admin/blog/linkedinconfig/`
2. Edit the existing configuration
3. Fill in:
   - Client Secret
   - Access Token
   - Refresh Token (optional)
4. Set `is_active` to `True`
5. Save

## Step 6: Test Your Integration

### 6.1 Verify Credentials
```bash
python manage.py fix_linkedin_credentials
```

Should show: `✓ Credentials are valid`

### 6.2 Test Posting
1. Go to Django admin
2. Create or edit a blog post
3. Use the "Post to LinkedIn" action
4. Check your LinkedIn profile for the post

## Troubleshooting

### Common Issues

#### 1. "Invalid redirect_uri"
- Ensure the redirect URI in your authorization URL exactly matches what's configured in your LinkedIn app
- URLs are case-sensitive and must include protocol (https://)

#### 2. "Invalid client_id"
- Double-check your Client ID from the LinkedIn app dashboard
- Ensure there are no extra spaces or characters

#### 3. "Access token expired"
- Access tokens expire (usually after 60 days)
- Use the refresh token to get a new access token
- Or repeat the authorization process

#### 4. "Insufficient permissions"
- Ensure your LinkedIn app has been approved for the required products
- Check that you requested the correct scopes in the authorization URL

### Required Scopes

For full functionality, request these scopes:
- `profile`: Basic profile information
- `w_member_social`: Post to LinkedIn
- `openid`: OpenID Connect
- `email`: Email address (optional)

## Security Best Practices

1. **Keep credentials secure**: Never commit credentials to version control
2. **Use environment variables**: Store credentials in environment variables or secure settings
3. **Rotate tokens regularly**: Refresh access tokens periodically
4. **Monitor usage**: Keep track of API usage and rate limits
5. **Use HTTPS**: Always use HTTPS for redirect URIs and API calls

## API Rate Limits

LinkedIn has rate limits:
- **Share API**: 100 posts per day per person
- **Profile API**: 500 requests per day per app
- **Throttling**: 100 requests per 10-second window

Plan your posting frequency accordingly.

## Useful Links

- [LinkedIn Developer Documentation](https://docs.microsoft.com/en-us/linkedin/)
- [LinkedIn API Reference](https://docs.microsoft.com/en-us/linkedin/shared/api-guide)
- [OAuth 2.0 Authorization](https://docs.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow)
- [Share API Documentation](https://docs.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin)

## Need Help?

If you encounter issues:
1. Check the troubleshooting section above
2. Review LinkedIn's developer documentation
3. Check your app's status in the LinkedIn Developer Portal
4. Ensure all required permissions are approved