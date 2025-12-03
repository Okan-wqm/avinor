# services/user-service/src/apps/core/serializers/__init__.py
"""
User Service Serializers

This module exports all serializers for the User Service API including:
- User serializers (CRUD, search, sessions)
- Authentication serializers (login, tokens, 2FA)
- Role and Permission serializers (RBAC)
- Audit log serializers
"""

from .user import (
    UserSerializer,
    UserListSerializer,
    UserSearchSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    UserStatusUpdateSerializer,
    UserBulkActionSerializer,
    UserSessionSerializer,
    UserInviteSerializer,
    EmailChangeSerializer,
)

from .auth import (
    LoginSerializer,
    TwoFactorVerifySerializer,
    TokenResponseSerializer,
    TwoFactorRequiredResponseSerializer,
    RefreshTokenSerializer,
    LogoutSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    EmailVerificationSerializer,
    ResendVerificationSerializer,
    TwoFactorSetupSerializer,
    TwoFactorSetupResponseSerializer,
    TwoFactorConfirmSerializer,
    TwoFactorConfirmResponseSerializer,
    TwoFactorDisableSerializer,
    BackupCodesRegenerateSerializer,
    BackupCodesResponseSerializer,
    SessionListSerializer,
    SessionTerminateSerializer,
    RegisterSerializer,
    RegisterResponseSerializer,
    TokenVerifySerializer,
    TokenVerifyResponseSerializer,
)

from .role import (
    PermissionSerializer,
    PermissionListSerializer,
    PermissionCreateSerializer,
    RoleSerializer,
    RoleListSerializer,
    RoleCreateSerializer,
    RoleUpdateSerializer,
    RolePermissionSerializer,
    RolePermissionAssignSerializer,
    RolePermissionBulkSerializer,
    UserRoleSerializer,
    UserRoleAssignSerializer,
    UserRoleBulkAssignSerializer,
    UserRoleRevokeSerializer,
    AuditLogSerializer,
    AuditLogListSerializer,
    AuditLogFilterSerializer,
)

__all__ = [
    # User serializers
    'UserSerializer',
    'UserListSerializer',
    'UserSearchSerializer',
    'UserCreateSerializer',
    'UserUpdateSerializer',
    'UserStatusUpdateSerializer',
    'UserBulkActionSerializer',
    'UserSessionSerializer',
    'UserInviteSerializer',
    'EmailChangeSerializer',

    # Auth serializers
    'LoginSerializer',
    'TwoFactorVerifySerializer',
    'TokenResponseSerializer',
    'TwoFactorRequiredResponseSerializer',
    'RefreshTokenSerializer',
    'LogoutSerializer',
    'PasswordChangeSerializer',
    'PasswordResetRequestSerializer',
    'PasswordResetConfirmSerializer',
    'EmailVerificationSerializer',
    'ResendVerificationSerializer',
    'TwoFactorSetupSerializer',
    'TwoFactorSetupResponseSerializer',
    'TwoFactorConfirmSerializer',
    'TwoFactorConfirmResponseSerializer',
    'TwoFactorDisableSerializer',
    'BackupCodesRegenerateSerializer',
    'BackupCodesResponseSerializer',
    'SessionListSerializer',
    'SessionTerminateSerializer',
    'RegisterSerializer',
    'RegisterResponseSerializer',
    'TokenVerifySerializer',
    'TokenVerifyResponseSerializer',

    # Role serializers
    'PermissionSerializer',
    'PermissionListSerializer',
    'PermissionCreateSerializer',
    'RoleSerializer',
    'RoleListSerializer',
    'RoleCreateSerializer',
    'RoleUpdateSerializer',
    'RolePermissionSerializer',
    'RolePermissionAssignSerializer',
    'RolePermissionBulkSerializer',
    'UserRoleSerializer',
    'UserRoleAssignSerializer',
    'UserRoleBulkAssignSerializer',
    'UserRoleRevokeSerializer',

    # Audit serializers
    'AuditLogSerializer',
    'AuditLogListSerializer',
    'AuditLogFilterSerializer',
]
