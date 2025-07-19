# api/serializers.py
from django.contrib.auth.models import User
from users.models import Profile
from .models import APIClient, APIKey, APIUsageLog
from django.contrib.auth.models import User
from rest_framework import serializers
from blog.models import Post, Category
from core.models import Page, Component, Template

class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for the Category model.
    """
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent']

class PostSerializer(serializers.ModelSerializer):
    """
    Serializer for the Post model, including nested category details.
    """
    # Use CategorySerializer to display full category details instead of just IDs
    categories = CategorySerializer(many=True, read_only=True)
    # Display the author's username for better context
    author = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'author', 'content', 'excerpt', 
            'featured_image', 'categories', 'read_time', 'view_count', 
            'is_featured', 'status', 'created_at', 'updated_at'
        ]
        # Make certain fields read-only as they are auto-generated
        read_only_fields = ['read_time', 'view_count', 'author']



class APIClientSerializer(serializers.ModelSerializer):
    """
    Serializer for APIClient model
    """
    created_by = serializers.ReadOnlyField(source='created_by.username')
    client_id = serializers.ReadOnlyField()
    
    class Meta:
        model = APIClient
        fields = [
            'id', 'client_id', 'name', 'description', 'is_active',
            'created_by', 'created_at', 'updated_at',
            'can_read_posts', 'can_write_posts', 'can_delete_posts',
            'can_manage_categories', 'can_access_users', 'can_access_pages',
            'requests_per_minute', 'requests_per_hour', 'allowed_ips'
        ]
        read_only_fields = ['client_id', 'created_by', 'created_at', 'updated_at']


class APIClientRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for client registration (limited fields)
    """
    class Meta:
        model = APIClient
        fields = [
            'name', 'description',
            'can_read_posts', 'can_write_posts', 'can_delete_posts',
            'can_manage_categories', 'can_access_users', 'can_access_pages'
        ]
    
    def validate_name(self, value):
        """Ensure client name is unique"""
        if APIClient.objects.filter(name=value).exists():
            raise serializers.ValidationError("A client with this name already exists.")
        return value


class APIKeySerializer(serializers.ModelSerializer):
    """
    Serializer for APIKey model (without sensitive data)
    """
    client_name = serializers.ReadOnlyField(source='client.name')
    is_expired = serializers.SerializerMethodField()
    expires_in_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = APIKey
        fields = [
            'id', 'client_name', 'is_active', 'created_at', 'expires_at',
            'last_used_at', 'usage_count', 'is_expired', 'expires_in_hours'
        ]
        read_only_fields = ['created_at', 'last_used_at', 'usage_count']
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_expires_in_hours(self, obj):
        from django.utils import timezone
        if obj.is_expired():
            return 0
        time_diff = obj.expires_at - timezone.now()
        return round(time_diff.total_seconds() / 3600, 2)


class APIKeyGenerationSerializer(serializers.Serializer):
    """
    Serializer for API key generation requests
    """
    expiration_hours = serializers.IntegerField(
        default=24, 
        min_value=1, 
        max_value=8760,  # 1 year max
        help_text="Hours until the key expires (1-8760)"
    )


class APIKeyResponseSerializer(serializers.Serializer):
    """
    Serializer for API key generation response
    """
    api_key = serializers.CharField(help_text="The generated API key (store securely!)")
    client_id = serializers.UUIDField(help_text="Client ID to use with the API key")
    encryption_key = serializers.CharField(help_text="Encryption key for secure communications")
    expires_at = serializers.DateTimeField(help_text="When the key expires")
    created_at = serializers.DateTimeField(help_text="When the key was created")


class APIUsageLogSerializer(serializers.ModelSerializer):
    """
    Serializer for API usage logs
    """
    client_name = serializers.ReadOnlyField(source='client.name')
    
    class Meta:
        model = APIUsageLog
        fields = [
            'id', 'client_name', 'endpoint', 'method', 'status_code',
            'response_time', 'timestamp', 'ip_address', 'user_agent',
            'request_size', 'response_size', 'error_message'
        ]


class ClientPermissionsSerializer(serializers.Serializer):
    """
    Serializer for checking client permissions
    """
    can_read_posts = serializers.BooleanField()
    can_write_posts = serializers.BooleanField()
    can_delete_posts = serializers.BooleanField()
    can_manage_categories = serializers.BooleanField()
    can_access_users = serializers.BooleanField()
    can_access_pages = serializers.BooleanField()


class APIEndpointSerializer(serializers.Serializer):
    """
    Serializer for API endpoint discovery
    """
    name = serializers.CharField(help_text="Endpoint name")
    url = serializers.CharField(help_text="Endpoint URL pattern")
    methods = serializers.ListField(
        child=serializers.CharField(),
        help_text="Allowed HTTP methods"
    )
    description = serializers.CharField(help_text="Endpoint description")
    permissions_required = serializers.ListField(
        child=serializers.CharField(),
        help_text="Required permissions"
    )


class ClientUsageStatsSerializer(serializers.Serializer):
    """
    Serializer for client usage statistics
    """
    total_requests = serializers.IntegerField()
    requests_today = serializers.IntegerField()
    requests_this_hour = serializers.IntegerField()
    requests_this_minute = serializers.IntegerField()
    average_response_time = serializers.FloatField()
    success_rate = serializers.FloatField()
    most_used_endpoints = serializers.ListField(
        child=serializers.DictField()
    )
    rate_limit_status = serializers.DictField()


class ErrorResponseSerializer(serializers.Serializer):
    """
    Serializer for standardized error responses
    """
    error = serializers.DictField()
    timestamp = serializers.DateTimeField()
    request_id = serializers.CharField(required=False)


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model with privacy controls
    """
    profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'date_joined', 'profile']
        read_only_fields = ['id', 'username', 'date_joined']
    
    def get_profile(self, obj):
        """Get profile data with privacy controls"""
        try:
            profile = obj.profile
            if not profile.is_profile_public:
                return {'public': False}
            
            data = {
                'about': profile.about,
                'website': profile.website,
                'occupation': profile.occupation,
                'company': profile.company,
                'city': profile.city,
                'country': profile.country,
            }
            
            # Add social media links if public
            if profile.is_profile_public:
                data.update({
                    'twitter': profile.twitter,
                    'linkedin': profile.linkedin,
                    'instagram': profile.instagram,
                })
            
            # Add email and phone only if user allows it
            if profile.show_email:
                data['email'] = obj.email
            
            if profile.show_phone:
                data['phone_number'] = profile.phone_number
            
            return data
        except Profile.DoesNotExist:
            return None


class PublicUserSerializer(serializers.ModelSerializer):
    """
    Minimal user serializer for public access
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'date_joined']
        read_only_fields = ['id', 'username', 'first_name', 'last_name', 'date_joined']
        
# Core API Serializers


class ComponentSerializer(serializers.ModelSerializer):
    """
    Serializer for Component model
    """
    class Meta:
        model = Component
        fields = ['id', 'name', 'slug', 'content', 'created_at', 'updated_at']
        read_only_fields = ['slug', 'created_at', 'updated_at']


class TemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for Template model
    """
    files = ComponentSerializer(many=True, read_only=True)
    file_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Template
        fields = ['id', 'name', 'files', 'file_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_file_count(self, obj):
        return obj.files.count()


class PageSerializer(serializers.ModelSerializer):
    """
    Serializer for Page model
    """
    template_name = serializers.ReadOnlyField(source='template.name')
    
    class Meta:
        model = Page
        fields = [
            'id', 'title', 'slug', 'content', 'meta_description',
            'template', 'template_name', 'is_published', 'is_homepage',
            'navbar_type', 'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']


class PublicPageSerializer(serializers.ModelSerializer):
    """
    Serializer for public page access (limited fields)
    """
    template_name = serializers.ReadOnlyField(source='template.name')
    
    class Meta:
        model = Page
        fields = [
            'id', 'title', 'slug', 'content', 'meta_description',
            'template_name', 'navbar_type', 'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']