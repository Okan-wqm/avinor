# services/user-service/src/apps/core/models/role.py
"""
Role and Permission models for comprehensive RBAC implementation.
Supports system roles, organization roles, and conditional permissions.
"""

import uuid
from django.db import models
from django.utils import timezone


class Permission(models.Model):
    """
    Granular permission model for RBAC.
    Permissions are assigned to roles, not directly to users.
    """

    class Action(models.TextChoices):
        CREATE = 'create', 'Create'
        READ = 'read', 'Read'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        MANAGE = 'manage', 'Manage'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Identification
    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text='Unique permission code (e.g., users.create, bookings.approve)'
    )
    name = models.CharField(max_length=255, help_text='Human readable name')
    description = models.TextField(blank=True, null=True)

    # Categorization
    module = models.CharField(
        max_length=50,
        db_index=True,
        help_text='Module/resource (e.g., users, bookings, flights)'
    )
    action = models.CharField(
        max_length=50,
        choices=Action.choices,
        help_text='Action type'
    )

    # Security flags
    is_sensitive = models.BooleanField(
        default=False,
        help_text='Requires additional audit logging'
    )
    requires_2fa = models.BooleanField(
        default=False,
        help_text='Requires 2FA for this action'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'permissions'
        ordering = ['module', 'action', 'code']
        indexes = [
            models.Index(fields=['module']),
            models.Index(fields=['code']),
        ]

    def __str__(self):
        return f"{self.module}.{self.action}: {self.name}"


class Role(models.Model):
    """
    Role model for grouping permissions.
    Supports both system-wide and organization-specific roles.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Organization scope (NULL = system role available to all orgs)
    organization_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text='NULL for system roles available to all organizations'
    )

    # Identification
    code = models.CharField(
        max_length=50,
        db_index=True,
        help_text='Unique role code within organization'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # Properties
    is_system_role = models.BooleanField(
        default=False,
        help_text='System roles cannot be modified or deleted'
    )
    is_default = models.BooleanField(
        default=False,
        help_text='Automatically assigned to new users'
    )
    priority = models.IntegerField(
        default=0,
        help_text='Higher priority roles override lower in conflicts'
    )

    # Visual
    color = models.CharField(max_length=7, blank=True, null=True, help_text='Hex color code')
    icon = models.CharField(max_length=50, blank=True, null=True)

    # Permissions relationship
    permissions = models.ManyToManyField(
        Permission,
        through='RolePermission',
        related_name='roles'
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'roles'
        ordering = ['-priority', 'name']
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['code']),
            models.Index(fields=['is_system_role']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'code'],
                name='unique_org_role_code'
            )
        ]

    def __str__(self):
        if self.is_system_role:
            return f"[System] {self.name}"
        return self.name

    def get_all_permissions(self):
        """Get all permission codes for this role"""
        return list(
            self.role_permissions.values_list('permission__code', flat=True)
        )

    def has_permission(self, permission_code):
        """Check if role has a specific permission"""
        return self.role_permissions.filter(
            permission__code=permission_code
        ).exists()


class RolePermission(models.Model):
    """
    Many-to-many relationship between Role and Permission.
    Supports conditional permissions for ABAC.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_permissions'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='role_permissions'
    )

    # Conditional permissions (ABAC)
    conditions = models.JSONField(
        blank=True,
        null=True,
        help_text='JSON conditions for attribute-based access control'
    )
    # Example conditions:
    # {"own_records_only": true}
    # {"same_location": true}
    # {"same_organization": true}

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'role_permissions'
        constraints = [
            models.UniqueConstraint(
                fields=['role', 'permission'],
                name='unique_role_permission'
            )
        ]
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['permission']),
        ]

    def __str__(self):
        return f"{self.role.name} -> {self.permission.code}"


class UserRole(models.Model):
    """
    Assignment of roles to users with optional time and location constraints.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='user_roles'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_roles'
    )

    # Time validity
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text='NULL = unlimited validity'
    )

    # Location constraint
    location_id = models.UUIDField(
        null=True,
        blank=True,
        help_text='Role only valid for this location'
    )

    # Additional conditions
    conditions = models.JSONField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'user_roles'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'role', 'location_id'],
                name='unique_user_role_location'
            )
        ]
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['role']),
            models.Index(fields=['valid_from', 'valid_until']),
            models.Index(fields=['location_id']),
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.role.name}"

    @property
    def is_valid(self):
        """Check if role assignment is currently valid"""
        now = timezone.now()

        if self.revoked_at:
            return False
        if self.valid_until and self.valid_until < now:
            return False
        if self.valid_from and self.valid_from > now:
            return False

        return True

    def revoke(self, revoked_by=None):
        """Revoke this role assignment"""
        self.revoked_at = timezone.now()
        self.revoked_by = revoked_by
        self.save(update_fields=['revoked_at', 'revoked_by'])


class AuditLog(models.Model):
    """
    Comprehensive audit log for security-sensitive operations.
    """

    class RiskLevel(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(null=True, blank=True, db_index=True)

    # Actor
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    user_email = models.CharField(max_length=255, blank=True, null=True)
    user_name = models.CharField(max_length=255, blank=True, null=True)
    impersonated_by = models.UUIDField(
        null=True,
        blank=True,
        help_text='Real user ID if impersonating'
    )

    # Action
    action = models.CharField(
        max_length=50,
        db_index=True,
        help_text='Action performed (login, logout, create, update, delete, etc.)'
    )

    # Target
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.UUIDField(null=True, blank=True)
    entity_name = models.CharField(max_length=255, blank=True, null=True)

    # Changes
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    changed_fields = models.JSONField(null=True, blank=True)

    # Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    request_id = models.UUIDField(null=True, blank=True)
    session_id = models.UUIDField(null=True, blank=True)

    # Risk assessment
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        default=RiskLevel.LOW
    )

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['user_id']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['action']),
            models.Index(fields=['created_at']),
            models.Index(fields=['risk_level']),
        ]

    def __str__(self):
        return f"{self.action} on {self.entity_type} by {self.user_email or 'system'}"

    @classmethod
    def log(
        cls,
        action,
        entity_type,
        entity_id=None,
        entity_name=None,
        user=None,
        organization_id=None,
        old_values=None,
        new_values=None,
        changed_fields=None,
        ip_address=None,
        user_agent=None,
        request_id=None,
        session_id=None,
        risk_level='low',
        metadata=None,
        impersonated_by=None
    ):
        """Create an audit log entry"""
        return cls.objects.create(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            user_name=user.full_name if user else None,
            organization_id=organization_id or (user.organization_id if user else None),
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            session_id=session_id,
            risk_level=risk_level,
            metadata=metadata or {},
            impersonated_by=impersonated_by
        )
