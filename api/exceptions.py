# api/exceptions.py - Custom Exception Handling

import uuid
import logging
from django.utils import timezone
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for API responses
    Provides consistent error response format
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        # Generate unique request ID for tracking
        request_id = str(uuid.uuid4())
        
        # Get request information
        request = context.get('request')
        view = context.get('view')
        
        # Log the error
        logger.error(
            f"API Error [{request_id}]: {exc.__class__.__name__}: {str(exc)} "
            f"- Path: {request.path if request else 'Unknown'} "
            f"- Method: {request.method if request else 'Unknown'} "
            f"- View: {view.__class__.__name__ if view else 'Unknown'}"
        )
        
        # Create standardized error response
        error_response = {
            'error': {
                'code': get_error_code(exc),
                'message': get_error_message(exc, response.data),
                'details': get_error_details(exc, response.data)
            },
            'timestamp': timezone.now().isoformat(),
            'request_id': request_id
        }
        
        # Add path and method for debugging
        if request:
            error_response['path'] = request.path
            error_response['method'] = request.method
        
        response.data = error_response
    
    return response


def get_error_code(exc):
    """
    Get standardized error code based on exception type
    """
    error_codes = {
        'AuthenticationFailed': 'AUTHENTICATION_FAILED',
        'PermissionDenied': 'PERMISSION_DENIED',
        'ValidationError': 'VALIDATION_ERROR',
        'NotFound': 'NOT_FOUND',
        'MethodNotAllowed': 'METHOD_NOT_ALLOWED',
        'Throttled': 'RATE_LIMIT_EXCEEDED',
        'ParseError': 'PARSE_ERROR',
        'UnsupportedMediaType': 'UNSUPPORTED_MEDIA_TYPE',
    }
    
    return error_codes.get(exc.__class__.__name__, 'API_ERROR')


def get_error_message(exc, response_data):
    """
    Get user-friendly error message
    """
    # Handle different exception types
    if isinstance(exc, AuthenticationFailed):
        return str(exc) or 'Authentication failed'
    elif isinstance(exc, PermissionDenied):
        return str(exc) or 'Permission denied'
    elif isinstance(exc, ValidationError):
        return 'Validation failed'
    else:
        # Try to get message from response data
        if isinstance(response_data, dict):
            if 'detail' in response_data:
                return response_data['detail']
            elif 'message' in response_data:
                return response_data['message']
        elif isinstance(response_data, list) and response_data:
            return str(response_data[0])
        
        return str(exc) or 'An error occurred'


def get_error_details(exc, response_data):
    """
    Get detailed error information
    """
    details = {}
    
    # Add validation errors
    if isinstance(exc, ValidationError) and isinstance(response_data, dict):
        details['validation_errors'] = response_data
    
    # Add authentication details
    elif isinstance(exc, AuthenticationFailed):
        details['authentication_required'] = True
        if hasattr(exc, 'auth_header'):
            details['auth_header'] = exc.auth_header
    
    # Add permission details
    elif isinstance(exc, PermissionDenied):
        details['required_permissions'] = getattr(exc, 'required_permissions', [])
    
    # Add throttling details
    elif exc.__class__.__name__ == 'Throttled':
        if hasattr(exc, 'wait'):
            details['retry_after'] = exc.wait
        if hasattr(exc, 'detail'):
            details['throttle_scope'] = getattr(exc, 'scope', 'unknown')
    
    return details


class APIException(Exception):
    """
    Base exception class for API-specific errors
    """
    def __init__(self, message, code='API_ERROR', status_code=status.HTTP_400_BAD_REQUEST, details=None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ClientNotFoundError(APIException):
    """Exception raised when API client is not found"""
    def __init__(self, client_id=None):
        message = f"API client not found: {client_id}" if client_id else "API client not found"
        super().__init__(
            message=message,
            code='CLIENT_NOT_FOUND',
            status_code=status.HTTP_404_NOT_FOUND
        )


class APIKeyExpiredError(APIException):
    """Exception raised when API key has expired"""
    def __init__(self, expires_at=None):
        message = "API key has expired"
        details = {}
        if expires_at:
            details['expired_at'] = expires_at.isoformat()
        
        super().__init__(
            message=message,
            code='API_KEY_EXPIRED',
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class RateLimitExceededError(APIException):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, limit_type='requests', retry_after=None):
        message = f"Rate limit exceeded for {limit_type}"
        details = {}
        if retry_after:
            details['retry_after'] = retry_after
        
        super().__init__(
            message=message,
            code='RATE_LIMIT_EXCEEDED',
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )


class IPNotAllowedError(APIException):
    """Exception raised when client IP is not in allowed list"""
    def __init__(self, ip_address=None):
        message = f"IP address not allowed: {ip_address}" if ip_address else "IP address not allowed"
        super().__init__(
            message=message,
            code='IP_NOT_ALLOWED',
            status_code=status.HTTP_403_FORBIDDEN
        )


class InvalidAPIKeyError(APIException):
    """Exception raised when API key is invalid"""
    def __init__(self, message="Invalid API key"):
        super().__init__(
            message=message,
            code='INVALID_API_KEY',
            status_code=status.HTTP_401_UNAUTHORIZED
        )