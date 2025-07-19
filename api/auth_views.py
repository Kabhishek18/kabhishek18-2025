# api/auth_views.py - API Authentication Views

import uuid
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import APIClient, APIKey, APIUsageLog
from .serializers import (
    APIClientSerializer, APIClientRegistrationSerializer,
    APIKeySerializer, APIKeyGenerationSerializer, APIKeyResponseSerializer,
    APIUsageLogSerializer, ClientPermissionsSerializer,
    APIEndpointSerializer, ClientUsageStatsSerializer, ErrorResponseSerializer
)
from .authentication import get_authenticated_client, get_authenticated_api_key
from .utils import log_api_usage, get_api_config
import logging

logger = logging.getLogger(__name__)


class APIClientViewSet(ModelViewSet):
    """
    ViewSet for managing API clients
    Only accessible by authenticated Django users (admin interface)
    """
    queryset = APIClient.objects.all()
    serializer_class = APIClientSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return APIClientRegistrationSerializer
        return APIClientSerializer
    
    def perform_create(self, serializer):
        """Set the created_by field to the current user"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def generate_key(self, request, pk=None):
        """Generate a new API key for the client"""
        client = self.get_object()
        serializer = APIKeyGenerationSerializer(data=request.data)
        
        if serializer.is_valid():
            expiration_hours = serializer.validated_data.get('expiration_hours', 24)
            
            try:
                # Generate new API key
                key_data = APIKey.generate_key_pair(client, expiration_hours)
                
                response_data = {
                    'api_key': key_data['api_key'],
                    'client_id': str(client.client_id),
                    'encryption_key': key_data['api_key_instance'].encryption_key,
                    'expires_at': key_data['expires_at'],
                    'created_at': key_data['api_key_instance'].created_at
                }
                
                return Response(
                    APIKeyResponseSerializer(response_data).data,
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                logger.error(f"Failed to generate API key for client {client.name}: {str(e)}")
                return Response(
                    {'error': 'Failed to generate API key'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def usage_stats(self, request, pk=None):
        """Get usage statistics for the client"""
        client = self.get_object()
        
        # Calculate time ranges
        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        this_hour = now.replace(minute=0, second=0, microsecond=0)
        this_minute = now.replace(second=0, microsecond=0)
        
        # Get usage statistics
        logs = APIUsageLog.objects.filter(client=client)
        
        stats = {
            'total_requests': logs.count(),
            'requests_today': logs.filter(timestamp__gte=today).count(),
            'requests_this_hour': logs.filter(timestamp__gte=this_hour).count(),
            'requests_this_minute': logs.filter(timestamp__gte=this_minute).count(),
            'average_response_time': logs.aggregate(avg=Avg('response_time'))['avg'] or 0,
            'success_rate': self._calculate_success_rate(logs),
            'most_used_endpoints': self._get_most_used_endpoints(logs),
            'rate_limit_status': {
                'requests_per_minute_limit': client.requests_per_minute,
                'requests_per_hour_limit': client.requests_per_hour,
                'current_minute_usage': logs.filter(timestamp__gte=this_minute).count(),
                'current_hour_usage': logs.filter(timestamp__gte=this_hour).count(),
            }
        }
        
        return Response(ClientUsageStatsSerializer(stats).data)
    
    def _calculate_success_rate(self, logs):
        """Calculate success rate (2xx status codes)"""
        total = logs.count()
        if total == 0:
            return 100.0
        
        successful = logs.filter(status_code__gte=200, status_code__lt=300).count()
        return round((successful / total) * 100, 2)
    
    def _get_most_used_endpoints(self, logs, limit=5):
        """Get most frequently used endpoints"""
        endpoints = logs.values('endpoint', 'method').annotate(
            count=Count('id')
        ).order_by('-count')[:limit]
        
        return [
            {
                'endpoint': ep['endpoint'],
                'method': ep['method'],
                'count': ep['count']
            }
            for ep in endpoints
        ]


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_description="Register a new API client",
    request_body=APIClientRegistrationSerializer,
    responses={
        201: openapi.Response('Client created', APIClientSerializer),
        400: 'Bad Request'
    }
)
def register_client(request):
    """
    Register a new API client
    Only accessible by authenticated Django users
    """
    serializer = APIClientRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        client = serializer.save(created_by=request.user)
        
        # Return full client data
        response_serializer = APIClientSerializer(client)
        
        logger.info(f"New API client registered: {client.name} by {request.user.username}")
        
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_description="Generate API key for a client",
    request_body=APIKeyGenerationSerializer,
    responses={
        201: openapi.Response('API key generated', APIKeyResponseSerializer),
        400: 'Bad Request',
        404: 'Client not found'
    }
)
def generate_api_key(request, client_id):
    """
    Generate a new API key for a specific client
    """
    try:
        client = APIClient.objects.get(client_id=client_id)
    except APIClient.DoesNotExist:
        return Response(
            {'error': 'Client not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = APIKeyGenerationSerializer(data=request.data)
    
    if serializer.is_valid():
        expiration_hours = serializer.validated_data.get('expiration_hours', 24)
        
        try:
            # Generate new API key
            key_data = APIKey.generate_key_pair(client, expiration_hours)
            
            response_data = {
                'api_key': key_data['api_key'],
                'client_id': str(client.client_id),
                'encryption_key': key_data['api_key_instance'].encryption_key,
                'expires_at': key_data['expires_at'],
                'created_at': key_data['api_key_instance'].created_at
            }
            
            logger.info(f"API key generated for client: {client.name}")
            
            return Response(
                APIKeyResponseSerializer(response_data).data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Failed to generate API key for client {client.name}: {str(e)}")
            return Response(
                {'error': 'Failed to generate API key'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@csrf_exempt
@swagger_auto_schema(
    operation_description="Validate API authentication",
    manual_parameters=[
        openapi.Parameter('X-Client-ID', openapi.IN_HEADER, description="Client ID", type=openapi.TYPE_STRING),
        openapi.Parameter('X-API-Key', openapi.IN_HEADER, description="API Key", type=openapi.TYPE_STRING),
    ],
    responses={
        200: openapi.Response('Authentication valid', ClientPermissionsSerializer),
        401: 'Authentication failed'
    }
)
def validate_authentication(request):
    """
    Validate API authentication and return client permissions
    This endpoint uses the API authentication system
    """
    from .authentication import CombinedAPIAuthentication
    
    auth = CombinedAPIAuthentication()
    try:
        user, api_key = auth.authenticate(request)
        if user and api_key:
            client = user.client
            
            permissions = {
                'can_read_posts': client.can_read_posts,
                'can_write_posts': client.can_write_posts,
                'can_delete_posts': client.can_delete_posts,
                'can_manage_categories': client.can_manage_categories,
                'can_access_users': client.can_access_users,
                'can_access_pages': client.can_access_pages,
            }
            
            return Response({
                'valid': True,
                'client_name': client.name,
                'client_id': str(client.client_id),
                'permissions': permissions,
                'expires_at': api_key.expires_at,
                'rate_limits': {
                    'requests_per_minute': client.requests_per_minute,
                    'requests_per_hour': client.requests_per_hour
                }
            })
        else:
            return Response(
                {'valid': False, 'error': 'Authentication failed'},
                status=status.HTTP_401_UNAUTHORIZED
            )
    except Exception as e:
        return Response(
            {'valid': False, 'error': str(e)},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['GET'])
@swagger_auto_schema(
    operation_description="Get list of available API endpoints",
    responses={
        200: openapi.Response('Endpoint list', APIEndpointSerializer(many=True))
    }
)
def get_api_endpoints(request):
    """
    Return a list of all available API endpoints (excluding admin)
    """
    from django.urls import get_resolver
    from django.conf import settings
    
    endpoints = []
    
    # Define our API endpoints manually for better control
    api_endpoints = [
        {
            'name': 'Blog Posts',
            'url': '/api/v1/posts/',
            'methods': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'description': 'CRUD operations for blog posts',
            'permissions_required': ['can_read_posts', 'can_write_posts', 'can_delete_posts']
        },
        {
            'name': 'Blog Categories',
            'url': '/api/v1/categories/',
            'methods': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'description': 'CRUD operations for blog categories',
            'permissions_required': ['can_read_posts', 'can_manage_categories']
        },
        {
            'name': 'Pages',
            'url': '/api/v1/pages/',
            'methods': ['GET'],
            'description': 'Access to page content',
            'permissions_required': ['can_access_pages']
        },
        {
            'name': 'Components',
            'url': '/api/v1/components/',
            'methods': ['GET'],
            'description': 'Access to component data',
            'permissions_required': ['can_access_pages']
        },
        {
            'name': 'Templates',
            'url': '/api/v1/templates/',
            'methods': ['GET'],
            'description': 'Access to template information',
            'permissions_required': ['can_access_pages']
        },
        {
            'name': 'Users',
            'url': '/api/v1/users/',
            'methods': ['GET'],
            'description': 'Access to user information (limited)',
            'permissions_required': ['can_access_users']
        },
        {
            'name': 'Authentication Validation',
            'url': '/api/v1/auth/validate/',
            'methods': ['POST'],
            'description': 'Validate API authentication',
            'permissions_required': []
        },
        {
            'name': 'API Endpoints Discovery',
            'url': '/api/v1/endpoints/',
            'methods': ['GET'],
            'description': 'Get list of available endpoints',
            'permissions_required': []
        }
    ]
    
    return Response(APIEndpointSerializer(api_endpoints, many=True).data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_client_usage(request, client_id):
    """
    Get usage logs for a specific client
    """
    try:
        client = APIClient.objects.get(client_id=client_id)
    except APIClient.DoesNotExist:
        return Response(
            {'error': 'Client not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get query parameters for filtering
    limit = int(request.GET.get('limit', 100))
    offset = int(request.GET.get('offset', 0))
    
    logs = APIUsageLog.objects.filter(client=client).order_by('-timestamp')[offset:offset+limit]
    
    serializer = APIUsageLogSerializer(logs, many=True)
    
    return Response({
        'count': APIUsageLog.objects.filter(client=client).count(),
        'results': serializer.data
    })


class APIKeyViewSet(ModelViewSet):
    """
    ViewSet for managing API keys
    Only accessible by authenticated Django users
    """
    serializer_class = APIKeySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return APIKey.objects.select_related('client').all()
    
    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        """Refresh (regenerate) an API key"""
        api_key = self.get_object()
        client = api_key.client
        
        # Get expiration hours from request or use default
        expiration_hours = request.data.get('expiration_hours', 24)
        
        try:
            # Deactivate old key
            api_key.is_active = False
            api_key.save()
            
            # Generate new key
            key_data = APIKey.generate_key_pair(client, expiration_hours)
            
            response_data = {
                'api_key': key_data['api_key'],
                'client_id': str(client.client_id),
                'encryption_key': key_data['api_key_instance'].encryption_key,
                'expires_at': key_data['expires_at'],
                'created_at': key_data['api_key_instance'].created_at
            }
            
            logger.info(f"API key refreshed for client: {client.name}")
            
            return Response(
                APIKeyResponseSerializer(response_data).data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Failed to refresh API key for client {client.name}: {str(e)}")
            return Response(
                {'error': 'Failed to refresh API key'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )