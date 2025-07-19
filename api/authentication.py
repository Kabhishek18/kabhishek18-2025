# api/authentication.py - Custom Authentication Classes

import logging
from typing import Optional, Tuple
from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils.translation import gettext_lazy as _
from .models import APIClient, APIKey
from .utils import APIKeyValidator, IPValidator, APIKeyGenerator
import time

logger = logging.getLogger(__name__)


class APIClientUser:
    """
    Custom user class to represent an authenticated API client
    This allows us to use the client in place of a Django User for permissions
    """
    def __init__(self, client: APIClient, api_key: APIKey = None):
        self.client = client
        self.api_key = api_key
        self.is_authenticated = True
        self.is_anonymous = False
        self.is_active = client.is_active
        
    @property
    def pk(self):
        return self.client.pk
    
    @property
    def id(self):
        return self.client.id
    
    @property
    def username(self):
        return self.client.name
    
    def __str__(self):
        return f"APIClient: {self.client.name}"
    
    def has_perm(self, perm, obj=None):
        """Check if client has specific permission"""
        permission_map = {
            'blog.view_post': self.client.can_read_posts,
            'blog.add_post': self.client.can_write_posts,
            'blog.change_post': self.client.can_write_posts,
            'blog.delete_post': self.client.can_delete_posts,
            'blog.view_category': self.client.can_read_posts,
            'blog.add_category': self.client.can_manage_categories,
            'blog.change_category': self.client.can_manage_categories,
            'blog.delete_category': self.client.can_manage_categories,
            'auth.view_user': self.client.can_access_users,
            'core.view_page': self.client.can_access_pages,
            'core.view_component': self.client.can_access_pages,
            'core.view_template': self.client.can_access_pages,
        }
        return permission_map.get(perm, False)
    
    def has_perms(self, perm_list, obj=None):
        """Check if client has all permissions in list"""
        return all(self.has_perm(perm, obj) for perm in perm_list)


class ClientAPIKeyAuthentication(BaseAuthentication):
    """
    Custom authentication class for API clients using client_id and api_key
    
    Expected headers:
    - X-Client-ID: The client's UUID
    - X-API-Key: The client's API key
    """
    
    def authenticate(self, request) -> Optional[Tuple[APIClientUser, APIKey]]:
        """
        Authenticate the request using client ID and API key
        
        Returns:
            Tuple of (APIClientUser, APIKey) or None if not authenticated
        """
        client_id = self.get_client_id(request)
        api_key = self.get_api_key(request)
        
        if not client_id or not api_key:
            return None
        
        try:
            # Get the client
            client = self.get_client(client_id)
            
            # Validate client is active
            if not client.is_active:
                raise AuthenticationFailed(_('Client is inactive'))
            
            # Check IP restrictions
            self.check_ip_restrictions(request, client)
            
            # Validate API key
            api_key_obj = self.validate_api_key(api_key, client)
            
            # Update key usage
            api_key_obj.update_usage()
            
            # Create client user
            client_user = APIClientUser(client, api_key_obj)
            
            # Log successful authentication
            logger.info(f"Successful API authentication for client: {client.name}")
            
            return (client_user, api_key_obj)
            
        except APIClient.DoesNotExist:
            raise AuthenticationFailed(_('Invalid client ID'))
        except APIKey.DoesNotExist:
            raise AuthenticationFailed(_('Invalid API key'))
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise AuthenticationFailed(str(e))
    
    def get_client_id(self, request) -> Optional[str]:
        """Extract client ID from request headers"""
        return request.META.get('HTTP_X_CLIENT_ID')
    
    def get_api_key(self, request) -> Optional[str]:
        """Extract API key from request headers"""
        return request.META.get('HTTP_X_API_KEY')
    
    def get_client(self, client_id: str) -> APIClient:
        """Get client by ID"""
        try:
            return APIClient.objects.get(client_id=client_id, is_active=True)
        except APIClient.DoesNotExist:
            raise AuthenticationFailed(_('Client not found or inactive'))
    
    def validate_api_key(self, api_key: str, client: APIClient) -> APIKey:
        """Validate API key for the client"""
        # Hash the provided key
        key_hash = APIKeyGenerator.hash_api_key(api_key)
        
        try:
            # Find the API key
            api_key_obj = APIKey.objects.get(
                client=client,
                key_hash=key_hash,
                is_active=True
            )
            
            # Check if key is expired
            if api_key_obj.is_expired():
                raise AuthenticationFailed(_('API key has expired'))
            
            return api_key_obj
            
        except APIKey.DoesNotExist:
            raise AuthenticationFailed(_('Invalid API key for this client'))
    
    def check_ip_restrictions(self, request, client: APIClient):
        """Check if client IP is allowed"""
        if not client.allowed_ips:
            return  # No IP restrictions
        
        client_ip = IPValidator.get_client_ip(request)
        allowed_ips = client.get_allowed_ip_list()
        
        if not IPValidator.is_ip_allowed(client_ip, allowed_ips):
            logger.warning(f"IP {client_ip} not allowed for client {client.name}")
            raise AuthenticationFailed(_('IP address not allowed'))
    
    def authenticate_header(self, request):
        """Return authentication header for 401 responses"""
        return 'ClientAPIKey realm="API"'


class EncryptionKeyAuthentication(BaseAuthentication):
    """
    Alternative authentication using only encryption key
    This is for simpler authentication scenarios
    
    Expected headers:
    - X-Encryption-Key: The client's encryption key
    """
    
    def authenticate(self, request) -> Optional[Tuple[APIClientUser, APIKey]]:
        """
        Authenticate using encryption key only
        
        Returns:
            Tuple of (APIClientUser, APIKey) or None if not authenticated
        """
        encryption_key = self.get_encryption_key(request)
        
        if not encryption_key:
            return None
        
        try:
            # Find API key by encryption key
            api_key_obj = APIKey.objects.select_related('client').get(
                encryption_key=encryption_key,
                is_active=True
            )
            
            # Check if key is expired
            if api_key_obj.is_expired():
                raise AuthenticationFailed(_('Encryption key has expired'))
            
            # Check if client is active
            if not api_key_obj.client.is_active:
                raise AuthenticationFailed(_('Client is inactive'))
            
            # Check IP restrictions
            self.check_ip_restrictions(request, api_key_obj.client)
            
            # Update key usage
            api_key_obj.update_usage()
            
            # Create client user
            client_user = APIClientUser(api_key_obj.client, api_key_obj)
            
            # Log successful authentication
            logger.info(f"Successful encryption key authentication for client: {api_key_obj.client.name}")
            
            return (client_user, api_key_obj)
            
        except APIKey.DoesNotExist:
            raise AuthenticationFailed(_('Invalid or expired encryption key'))
        except Exception as e:
            logger.error(f"Encryption key authentication error: {str(e)}")
            raise AuthenticationFailed(str(e))
    
    def get_encryption_key(self, request) -> Optional[str]:
        """Extract encryption key from request headers"""
        return request.META.get('HTTP_X_ENCRYPTION_KEY')
    
    def check_ip_restrictions(self, request, client: APIClient):
        """Check if client IP is allowed"""
        if not client.allowed_ips:
            return  # No IP restrictions
        
        client_ip = IPValidator.get_client_ip(request)
        allowed_ips = client.get_allowed_ip_list()
        
        if not IPValidator.is_ip_allowed(client_ip, allowed_ips):
            logger.warning(f"IP {client_ip} not allowed for client {client.name}")
            raise AuthenticationFailed(_('IP address not allowed'))
    
    def authenticate_header(self, request):
        """Return authentication header for 401 responses"""
        return 'EncryptionKey realm="API"'


class CombinedAPIAuthentication(BaseAuthentication):
    """
    Combined authentication that tries both methods:
    1. Client ID + API Key
    2. Encryption Key only
    
    This provides flexibility for different client implementations
    """
    
    def __init__(self):
        self.client_auth = ClientAPIKeyAuthentication()
        self.encryption_auth = EncryptionKeyAuthentication()
    
    def authenticate(self, request) -> Optional[Tuple[APIClientUser, APIKey]]:
        """
        Try both authentication methods
        
        Returns:
            Tuple of (APIClientUser, APIKey) or None if not authenticated
        """
        # Try client ID + API key first
        result = self.client_auth.authenticate(request)
        if result:
            return result
        
        # Try encryption key authentication
        result = self.encryption_auth.authenticate(request)
        if result:
            return result
        
        return None
    
    def authenticate_header(self, request):
        """Return authentication header for 401 responses"""
        return 'ClientAPIKey, EncryptionKey realm="API"'


# Utility functions for authentication

def get_authenticated_client(request) -> Optional[APIClient]:
    """
    Get the authenticated API client from the request
    
    Args:
        request: Django request object
        
    Returns:
        APIClient instance or None
    """
    if hasattr(request, 'user') and isinstance(request.user, APIClientUser):
        return request.user.client
    return None


def get_authenticated_api_key(request) -> Optional[APIKey]:
    """
    Get the authenticated API key from the request
    
    Args:
        request: Django request object
        
    Returns:
        APIKey instance or None
    """
    if hasattr(request, 'user') and isinstance(request.user, APIClientUser):
        return request.user.api_key
    return None


def require_client_permission(permission: str):
    """
    Decorator to require specific client permission
    
    Args:
        permission: Permission string (e.g., 'read_posts', 'write_posts')
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            client = get_authenticated_client(request)
            if not client:
                raise AuthenticationFailed(_('Authentication required'))
            
            is_allowed, error_msg = APIKeyValidator.validate_client_permissions(client, permission)
            if not is_allowed:
                raise AuthenticationFailed(error_msg)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator