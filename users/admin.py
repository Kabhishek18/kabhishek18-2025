
# admin.py - For Django Admin Interface
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile Information'
    fk_name = 'user'
    max_num = 1
    min_num = 1
    extra = 0
    
    # Fix for Django Unfold compatibility
    ordering_field = None
    sortable_field_name = None
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('about', 'phone_number', 'dob', 'gender'),
            'classes': ('wide',)
        }),
        ('Address Information', {
            'fields': ('address', 'city', 'state', 'country', 'postal_code'),
            'classes': ('collapse',)
        }),
        ('Professional Information', {
            'fields': ('occupation', 'company', 'website'),
            'classes': ('collapse',)
        }),
        ('Social Media', {
            'fields': ('twitter', 'linkedin', 'instagram'),
            'classes': ('collapse',)
        }),
        ('Privacy Settings', {
            'fields': ('is_profile_public', 'show_email', 'show_phone'),
            'classes': ('collapse',)
        }),
        ('Additional Details', {
            'fields': ('personal_detail', 'profile_picture'),
            'classes': ('collapse',)
        }),
    )

class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = BaseUserAdmin.list_display + ('get_phone', 'get_city', 'get_join_date')
    list_filter = BaseUserAdmin.list_filter + ('profile__gender', 'profile__country')
    
    def get_phone(self, obj):
        return obj.profile.phone_number if hasattr(obj, 'profile') else ''
    get_phone.short_description = 'Phone'
    get_phone.admin_order_field = 'profile__phone_number'
    
    def get_city(self, obj):
        return obj.profile.city if hasattr(obj, 'profile') else ''
    get_city.short_description = 'City'
    get_city.admin_order_field = 'profile__city'
    
    def get_join_date(self, obj):
        return obj.date_joined.strftime('%Y-%m-%d')
    get_join_date.short_description = 'Join Date'
    get_join_date.admin_order_field = 'date_joined'

# Safely unregister and register User with Profile inline
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, UserAdmin)

# Optional: Also register Profile separately for direct access
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'city', 'country', 'created_at']
    list_filter = ['gender', 'country', 'is_profile_public', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'phone_number', 'city']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Basic Information', {
            'fields': ('about', 'phone_number', 'dob', 'gender')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'country', 'postal_code')
        }),
        ('Professional', {
            'fields': ('occupation', 'company', 'website')
        }),
        ('Social Media', {
            'fields': ('twitter', 'linkedin', 'instagram')
        }),
        ('Privacy Settings', {
            'fields': ('is_profile_public', 'show_email', 'show_phone')
        }),
        ('Additional Details', {
            'fields': ('personal_detail', 'profile_picture')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ['user']
        return self.readonly_fields