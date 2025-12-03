# services/user-service/src/apps/core/events/handlers.py
"""
Event Handlers

Helper functions to publish events from various parts of the application.
These provide a clean interface between the business logic and event publishing.
"""

import logging
from typing import Optional, Dict, Any, List

from apps.core.models import User, Role, Permission, UserRole

from .publisher import get_publisher
from .types import (
    UserCreatedEvent,
    UserUpdatedEvent,
    UserDeletedEvent,
    UserStatusChangedEvent,
    UserLoginEvent,
    UserLogoutEvent,
    UserPasswordChangedEvent,
    User2FAEnabledEvent,
    User2FADisabledEvent,
    RoleCreatedEvent,
    RoleUpdatedEvent,
    RoleDeletedEvent,
    UserRoleAssignedEvent,
    UserRoleRevokedEvent,
    PermissionCreatedEvent,
    PermissionUpdatedEvent,
)

logger = logging.getLogger(__name__)


# ==================== USER EVENT HANDLERS ====================

def publish_user_created(
    user: User,
    created_by: str = 'self',
    actor: Optional[User] = None,
    roles: Optional[List[str]] = None,
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish user created event.

    Args:
        user: The created user
        created_by: How the user was created ('self', 'admin', 'invitation')
        actor: The user who created this user (if admin)
        roles: Initial roles assigned to the user
        correlation_id: Optional correlation ID for tracing
    """
    event = UserCreatedEvent(
        user_id=str(user.id),
        organization_id=str(user.organization_id) if user.organization_id else None,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        status=user.status,
        roles=roles or [],
        created_by=created_by,
        actor_id=str(actor.id) if actor else None,
        actor_email=actor.email if actor else None,
        correlation_id=correlation_id,
    )

    return get_publisher().publish(event)


def publish_user_updated(
    user: User,
    changed_fields: List[str],
    old_values: Dict[str, Any],
    new_values: Dict[str, Any],
    actor: Optional[User] = None,
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish user updated event.

    Args:
        user: The updated user
        changed_fields: List of fields that were changed
        old_values: Previous field values
        new_values: New field values
        actor: The user who made the update
        correlation_id: Optional correlation ID for tracing
    """
    event = UserUpdatedEvent(
        user_id=str(user.id),
        organization_id=str(user.organization_id) if user.organization_id else None,
        changed_fields=changed_fields,
        old_values=old_values,
        new_values=new_values,
        actor_id=str(actor.id) if actor else str(user.id),
        actor_email=actor.email if actor else user.email,
        correlation_id=correlation_id,
    )

    return get_publisher().publish(event)


def publish_user_deleted(
    user: User,
    deleted_by: Optional[User] = None,
    reason: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish user deleted event.

    Args:
        user: The deleted user
        deleted_by: The user who deleted this user
        reason: Reason for deletion
        correlation_id: Optional correlation ID for tracing
    """
    event = UserDeletedEvent(
        user_id=str(user.id),
        organization_id=str(user.organization_id) if user.organization_id else None,
        email=user.email,
        deleted_by=str(deleted_by.id) if deleted_by else None,
        reason=reason,
        actor_id=str(deleted_by.id) if deleted_by else str(user.id),
        actor_email=deleted_by.email if deleted_by else user.email,
        correlation_id=correlation_id,
    )

    return get_publisher().publish(event)


def publish_user_status_changed(
    user: User,
    old_status: str,
    new_status: str,
    reason: Optional[str] = None,
    actor: Optional[User] = None,
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish user status changed event.

    Args:
        user: The user whose status changed
        old_status: Previous status
        new_status: New status
        reason: Reason for the status change
        actor: The user who changed the status
        correlation_id: Optional correlation ID for tracing
    """
    event = UserStatusChangedEvent(
        user_id=str(user.id),
        organization_id=str(user.organization_id) if user.organization_id else None,
        old_status=old_status,
        new_status=new_status,
        reason=reason,
        actor_id=str(actor.id) if actor else str(user.id),
        actor_email=actor.email if actor else user.email,
        correlation_id=correlation_id,
    )

    return get_publisher().publish(event)


def publish_user_login(
    user: User,
    session_id: str,
    ip_address: str,
    user_agent: str,
    device_type: Optional[str] = None,
    location: Optional[str] = None,
    two_factor_used: bool = False,
    login_method: str = 'password',
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish user login event.

    Args:
        user: The user who logged in
        session_id: The session ID
        ip_address: Client IP address
        user_agent: Client user agent
        device_type: Type of device
        location: Geographic location
        two_factor_used: Whether 2FA was used
        login_method: Method of login
        correlation_id: Optional correlation ID for tracing
    """
    event = UserLoginEvent(
        user_id=str(user.id),
        organization_id=str(user.organization_id) if user.organization_id else None,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
        device_type=device_type,
        location=location,
        two_factor_used=two_factor_used,
        login_method=login_method,
        actor_id=str(user.id),
        actor_email=user.email,
        correlation_id=correlation_id,
    )

    return get_publisher().publish(event)


def publish_user_logout(
    user: User,
    session_id: str,
    logout_type: str = 'manual',
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish user logout event.

    Args:
        user: The user who logged out
        session_id: The session ID
        logout_type: Type of logout ('manual', 'timeout', 'forced')
        correlation_id: Optional correlation ID for tracing
    """
    event = UserLogoutEvent(
        user_id=str(user.id),
        organization_id=str(user.organization_id) if user.organization_id else None,
        session_id=session_id,
        logout_type=logout_type,
        actor_id=str(user.id),
        actor_email=user.email,
        correlation_id=correlation_id,
    )

    return get_publisher().publish(event)


def publish_password_changed(
    user: User,
    change_type: str = 'change',
    ip_address: Optional[str] = None,
    actor: Optional[User] = None,
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish password changed event.

    Args:
        user: The user whose password changed
        change_type: Type of change ('change', 'reset', 'forced')
        ip_address: Client IP address
        actor: The user who changed the password
        correlation_id: Optional correlation ID for tracing
    """
    event = UserPasswordChangedEvent(
        user_id=str(user.id),
        organization_id=str(user.organization_id) if user.organization_id else None,
        change_type=change_type,
        ip_address=ip_address,
        actor_id=str(actor.id) if actor else str(user.id),
        actor_email=actor.email if actor else user.email,
        correlation_id=correlation_id,
    )

    return get_publisher().publish(event)


def publish_2fa_enabled(
    user: User,
    method: str = 'totp',
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish 2FA enabled event.

    Args:
        user: The user who enabled 2FA
        method: 2FA method ('totp', 'sms', 'email')
        correlation_id: Optional correlation ID for tracing
    """
    event = User2FAEnabledEvent(
        user_id=str(user.id),
        organization_id=str(user.organization_id) if user.organization_id else None,
        method=method,
        actor_id=str(user.id),
        actor_email=user.email,
        correlation_id=correlation_id,
    )

    return get_publisher().publish(event)


def publish_2fa_disabled(
    user: User,
    disabled_by: str = 'user',
    actor: Optional[User] = None,
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish 2FA disabled event.

    Args:
        user: The user whose 2FA was disabled
        disabled_by: Who disabled it ('user', 'admin')
        actor: The user who disabled 2FA
        correlation_id: Optional correlation ID for tracing
    """
    event = User2FADisabledEvent(
        user_id=str(user.id),
        organization_id=str(user.organization_id) if user.organization_id else None,
        disabled_by=disabled_by,
        actor_id=str(actor.id) if actor else str(user.id),
        actor_email=actor.email if actor else user.email,
        correlation_id=correlation_id,
    )

    return get_publisher().publish(event)


# ==================== ROLE EVENT HANDLERS ====================

def publish_role_created(
    role: Role,
    permissions: Optional[List[str]] = None,
    actor: Optional[User] = None,
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish role created event.

    Args:
        role: The created role
        permissions: List of permission codes assigned to the role
        actor: The user who created the role
        correlation_id: Optional correlation ID for tracing
    """
    event = RoleCreatedEvent(
        role_id=str(role.id),
        role_code=role.code,
        organization_id=str(role.organization_id) if role.organization_id else None,
        name=role.name,
        description=role.description or '',
        is_system_role=role.is_system_role,
        permissions=permissions or [],
        actor_id=str(actor.id) if actor else None,
        actor_email=actor.email if actor else None,
        correlation_id=correlation_id,
    )

    return get_publisher().publish(event)


def publish_role_updated(
    role: Role,
    changed_fields: List[str],
    old_values: Dict[str, Any],
    new_values: Dict[str, Any],
    actor: Optional[User] = None,
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish role updated event.

    Args:
        role: The updated role
        changed_fields: List of fields that were changed
        old_values: Previous field values
        new_values: New field values
        actor: The user who updated the role
        correlation_id: Optional correlation ID for tracing
    """
    event = RoleUpdatedEvent(
        role_id=str(role.id),
        role_code=role.code,
        organization_id=str(role.organization_id) if role.organization_id else None,
        changed_fields=changed_fields,
        old_values=old_values,
        new_values=new_values,
        actor_id=str(actor.id) if actor else None,
        actor_email=actor.email if actor else None,
        correlation_id=correlation_id,
    )

    return get_publisher().publish(event)


def publish_role_deleted(
    role: Role,
    affected_users_count: int = 0,
    actor: Optional[User] = None,
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish role deleted event.

    Args:
        role: The deleted role
        affected_users_count: Number of users affected by the deletion
        actor: The user who deleted the role
        correlation_id: Optional correlation ID for tracing
    """
    event = RoleDeletedEvent(
        role_id=str(role.id),
        role_code=role.code,
        organization_id=str(role.organization_id) if role.organization_id else None,
        name=role.name,
        affected_users_count=affected_users_count,
        actor_id=str(actor.id) if actor else None,
        actor_email=actor.email if actor else None,
        correlation_id=correlation_id,
    )

    return get_publisher().publish(event)


def publish_user_role_assigned(
    user_role: UserRole,
    actor: Optional[User] = None,
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish user role assigned event.

    Args:
        user_role: The user role assignment
        actor: The user who made the assignment
        correlation_id: Optional correlation ID for tracing
    """
    event = UserRoleAssignedEvent(
        user_id=str(user_role.user.id),
        user_email=user_role.user.email,
        role_id=str(user_role.role.id),
        role_code=user_role.role.code,
        role_name=user_role.role.name,
        organization_id=str(user_role.user.organization_id) if user_role.user.organization_id else None,
        location_id=str(user_role.location_id) if user_role.location_id else None,
        valid_from=user_role.valid_from.isoformat() if user_role.valid_from else None,
        valid_until=user_role.valid_until.isoformat() if user_role.valid_until else None,
        assigned_by=str(actor.id) if actor else None,
        conditions=user_role.conditions or {},
        correlation_id=correlation_id,
    )

    return get_publisher().publish(event)


def publish_user_role_revoked(
    user: User,
    role: Role,
    reason: Optional[str] = None,
    actor: Optional[User] = None,
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish user role revoked event.

    Args:
        user: The user whose role was revoked
        role: The role that was revoked
        reason: Reason for revocation
        actor: The user who revoked the role
        correlation_id: Optional correlation ID for tracing
    """
    event = UserRoleRevokedEvent(
        user_id=str(user.id),
        user_email=user.email,
        role_id=str(role.id),
        role_code=role.code,
        role_name=role.name,
        organization_id=str(user.organization_id) if user.organization_id else None,
        revoked_by=str(actor.id) if actor else None,
        reason=reason,
        correlation_id=correlation_id,
    )

    return get_publisher().publish(event)


# ==================== PERMISSION EVENT HANDLERS ====================

def publish_permission_created(
    permission: Permission,
    actor: Optional[User] = None,
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish permission created event.

    Args:
        permission: The created permission
        actor: The user who created the permission
        correlation_id: Optional correlation ID for tracing
    """
    event = PermissionCreatedEvent(
        permission_id=str(permission.id),
        permission_code=permission.code,
        name=permission.name,
        module=permission.module,
        action=permission.action,
        actor_id=str(actor.id) if actor else None,
        actor_email=actor.email if actor else None,
        correlation_id=correlation_id,
    )

    return get_publisher().publish(event)


def publish_permission_updated(
    permission: Permission,
    changed_fields: List[str],
    old_values: Dict[str, Any],
    new_values: Dict[str, Any],
    actor: Optional[User] = None,
    correlation_id: Optional[str] = None
) -> bool:
    """
    Publish permission updated event.

    Args:
        permission: The updated permission
        changed_fields: List of fields that were changed
        old_values: Previous field values
        new_values: New field values
        actor: The user who updated the permission
        correlation_id: Optional correlation ID for tracing
    """
    event = PermissionUpdatedEvent(
        permission_id=str(permission.id),
        permission_code=permission.code,
        changed_fields=changed_fields,
        old_values=old_values,
        new_values=new_values,
        actor_id=str(actor.id) if actor else None,
        actor_email=actor.email if actor else None,
        correlation_id=correlation_id,
    )

    return get_publisher().publish(event)
