# services/user-service/src/apps/core/admin.py
"""
Django Admin configuration for User Service
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.core.models import User, UserProfile
from apps.core.models.role import Role, Permission, UserRole, RolePermission
from apps.core.models.token import RefreshToken, PasswordResetToken, EmailVerificationToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'full_name', 'organization_id', 'status', 'is_active', 'is_verified', 'created_at']
    list_filter = ['status', 'is_active', 'is_verified', 'is_staff', 'created_at']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'middle_name', 'phone')}),
        ('Organization', {'fields': ('organization_id',)}),
        ('Status', {'fields': ('status', 'is_active', 'is_verified', 'is_deleted')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser')}),
        ('Security', {'fields': ('failed_login_attempts', 'locked_until', 'must_change_password')}),
        ('Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    readonly_fields = ['created_at', 'updated_at', 'last_login']

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'first_name', 'last_name'),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'date_of_birth', 'nationality', 'city', 'country']
    search_fields = ['user__email', 'user__username']
    raw_id_fields = ['user']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'codename', 'role_type', 'organization_id', 'level', 'is_active', 'is_default']
    list_filter = ['role_type', 'is_active', 'is_default']
    search_fields = ['name', 'codename']


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'codename', 'category']
    list_filter = ['category']
    search_fields = ['name', 'codename']


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'organization_id', 'is_active', 'assigned_at']
    list_filter = ['is_active', 'role']
    search_fields = ['user__email', 'role__name']
    raw_id_fields = ['user']


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ['role', 'permission', 'granted_at']
    list_filter = ['role']
    search_fields = ['role__name', 'permission__codename']


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_revoked', 'created_at', 'expires_at', 'last_used_at']
    list_filter = ['is_revoked']
    search_fields = ['user__email']
    raw_id_fields = ['user']
    readonly_fields = ['token', 'jti', 'created_at']


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_used', 'created_at', 'expires_at']
    list_filter = ['is_used']
    search_fields = ['user__email']
    raw_id_fields = ['user']


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'is_used', 'created_at', 'expires_at']
    list_filter = ['is_used']
    search_fields = ['user__email', 'email']
    raw_id_fields = ['user']
