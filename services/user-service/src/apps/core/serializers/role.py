# services/user-service/src/apps/core/serializers/role.py
"""
Role and Permission Serializers - RBAC management

Includes:
- PermissionSerializer: Permission details
- RoleSerializer: Role with permissions
- UserRoleSerializer: User-role assignments
- AuditLogSerializer: Audit trail
"""

from rest_framework import serializers
from apps.core.models import Role, Permission, UserRole, RolePermission, AuditLog


class PermissionSerializer(serializers.ModelSerializer):
    """
    Serializer for Permission model.
    """

    class Meta:
        model = Permission
        fields = [
            'id',
            'code',
            'name',
            'description',
            'module',
            'action',
            'is_sensitive',
            'requires_2fa',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class PermissionListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for permission lists.
    """

    class Meta:
        model = Permission
        fields = [
            'id',
            'code',
            'name',
            'module',
            'action',
        ]


class PermissionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating permissions.
    """

    class Meta:
        model = Permission
        fields = [
            'code',
            'name',
            'description',
            'module',
            'action',
            'is_sensitive',
            'requires_2fa',
        ]

    def validate_code(self, value):
        """Ensure permission code is unique."""
        if Permission.objects.filter(code=value).exists():
            raise serializers.ValidationError(
                f"Permission with code '{value}' already exists."
            )
        return value


class RolePermissionSerializer(serializers.ModelSerializer):
    """
    Serializer for role-permission relationship with conditions.
    """

    permission = PermissionListSerializer(read_only=True)
    permission_code = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = RolePermission
        fields = [
            'id',
            'permission',
            'permission_code',
            'conditions',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class RoleSerializer(serializers.ModelSerializer):
    """
    Full Role serializer with permissions.
    """

    permissions = serializers.SerializerMethodField()
    permission_count = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            'id',
            'code',
            'name',
            'description',
            'organization_id',
            'is_system_role',
            'is_default',
            'priority',
            'color',
            'icon',
            'permissions',
            'permission_count',
            'user_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_permissions(self, obj) -> list:
        """Get role's permissions with conditions."""
        role_permissions = RolePermission.objects.filter(
            role=obj
        ).select_related('permission')

        return [
            {
                'code': rp.permission.code,
                'name': rp.permission.name,
                'module': rp.permission.module,
                'action': rp.permission.action,
                'conditions': rp.conditions,
            }
            for rp in role_permissions
        ]

    def get_permission_count(self, obj) -> int:
        """Get count of permissions."""
        return RolePermission.objects.filter(role=obj).count()

    def get_user_count(self, obj) -> int:
        """Get count of users with this role."""
        from django.utils import timezone
        from django.db.models import Q

        now = timezone.now()
        return UserRole.objects.filter(
            role=obj,
            valid_from__lte=now,
            revoked_at__isnull=True
        ).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gt=now)
        ).values('user').distinct().count()


class RoleListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for role lists.
    """

    permission_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            'id',
            'code',
            'name',
            'description',
            'is_system_role',
            'is_default',
            'priority',
            'color',
            'permission_count',
        ]

    def get_permission_count(self, obj) -> int:
        return RolePermission.objects.filter(role=obj).count()


class RoleCreateSerializer(serializers.Serializer):
    """
    Serializer for creating roles.
    """

    code = serializers.CharField(required=True, max_length=50)
    name = serializers.CharField(required=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    organization_id = serializers.UUIDField(required=False, allow_null=True)
    is_default = serializers.BooleanField(default=False)
    priority = serializers.IntegerField(default=0)
    color = serializers.CharField(required=False, max_length=7, allow_blank=True)
    icon = serializers.CharField(required=False, max_length=50, allow_blank=True)
    permissions = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list
    )

    def validate(self, attrs):
        """Validate role code uniqueness within organization."""
        code = attrs.get('code')
        org_id = attrs.get('organization_id')

        if Role.objects.filter(code=code, organization_id=org_id).exists():
            raise serializers.ValidationError({
                'code': f"Role with code '{code}' already exists in this organization."
            })

        return attrs


class RoleUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating roles.
    """

    name = serializers.CharField(required=False, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    is_default = serializers.BooleanField(required=False)
    priority = serializers.IntegerField(required=False)
    color = serializers.CharField(required=False, max_length=7, allow_blank=True)
    icon = serializers.CharField(required=False, max_length=50, allow_blank=True)


class RolePermissionAssignSerializer(serializers.Serializer):
    """
    Serializer for assigning permissions to a role.
    """

    permission_code = serializers.CharField(required=True, max_length=100)
    conditions = serializers.DictField(required=False, allow_null=True)


class RolePermissionBulkSerializer(serializers.Serializer):
    """
    Serializer for bulk permission operations on a role.
    """

    permissions = serializers.ListField(
        child=serializers.CharField(max_length=100),
        min_length=1
    )
    action = serializers.ChoiceField(
        choices=[('add', 'Add'), ('remove', 'Remove'), ('set', 'Set')],
        default='add'
    )


class UserRoleSerializer(serializers.ModelSerializer):
    """
    Serializer for user-role assignment.
    """

    role_details = RoleListSerializer(source='role', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserRole
        fields = [
            'id',
            'user',
            'user_email',
            'user_name',
            'role',
            'role_details',
            'valid_from',
            'valid_until',
            'location_id',
            'conditions',
            'is_valid',
            'created_at',
            'revoked_at',
        ]
        read_only_fields = ['id', 'created_at', 'revoked_at', 'is_valid']


class UserRoleAssignSerializer(serializers.Serializer):
    """
    Serializer for assigning a role to a user.
    """

    user_id = serializers.UUIDField(required=True)
    role_id = serializers.UUIDField(required=False)
    role_code = serializers.CharField(required=False, max_length=50)
    valid_from = serializers.DateTimeField(required=False)
    valid_until = serializers.DateTimeField(required=False, allow_null=True)
    location_id = serializers.UUIDField(required=False, allow_null=True)
    conditions = serializers.DictField(required=False, allow_null=True)

    def validate(self, attrs):
        """Ensure either role_id or role_code is provided."""
        if not attrs.get('role_id') and not attrs.get('role_code'):
            raise serializers.ValidationError(
                "Either 'role_id' or 'role_code' must be provided."
            )
        return attrs


class UserRoleBulkAssignSerializer(serializers.Serializer):
    """
    Serializer for bulk role assignment.
    """

    user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100
    )
    role_id = serializers.UUIDField(required=False)
    role_code = serializers.CharField(required=False, max_length=50)
    valid_until = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs.get('role_id') and not attrs.get('role_code'):
            raise serializers.ValidationError(
                "Either 'role_id' or 'role_code' must be provided."
            )
        return attrs


class UserRoleRevokeSerializer(serializers.Serializer):
    """
    Serializer for revoking a role from a user.
    """

    user_id = serializers.UUIDField(required=True)
    role_id = serializers.UUIDField(required=False)
    role_code = serializers.CharField(required=False, max_length=50)
    location_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs.get('role_id') and not attrs.get('role_code'):
            raise serializers.ValidationError(
                "Either 'role_id' or 'role_code' must be provided."
            )
        return attrs


# ==================== AUDIT LOG SERIALIZERS ====================

class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for audit log entries.
    """

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'organization_id',
            'user_id',
            'user_email',
            'user_name',
            'impersonated_by',
            'action',
            'entity_type',
            'entity_id',
            'entity_name',
            'old_values',
            'new_values',
            'changed_fields',
            'ip_address',
            'user_agent',
            'request_id',
            'session_id',
            'risk_level',
            'metadata',
            'created_at',
        ]
        read_only_fields = fields  # All fields are read-only


class AuditLogListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for audit log lists.
    """

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'user_email',
            'action',
            'entity_type',
            'entity_name',
            'risk_level',
            'ip_address',
            'created_at',
        ]


class AuditLogFilterSerializer(serializers.Serializer):
    """
    Serializer for audit log filtering.
    """

    user_id = serializers.UUIDField(required=False)
    entity_type = serializers.CharField(required=False, max_length=100)
    entity_id = serializers.UUIDField(required=False)
    action = serializers.CharField(required=False, max_length=50)
    risk_level = serializers.ChoiceField(
        choices=AuditLog.RiskLevel.choices,
        required=False
    )
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    ip_address = serializers.IPAddressField(required=False)
