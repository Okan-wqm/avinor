# services/user-service/src/apps/core/events/types.py
"""
Event Type Definitions

Defines the structure of events published by the User Service.
All events follow a standard format for inter-service communication.
"""

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class EventType(str, Enum):
    """Event type enumeration."""
    # User events
    USER_CREATED = 'user.created'
    USER_UPDATED = 'user.updated'
    USER_DELETED = 'user.deleted'
    USER_STATUS_CHANGED = 'user.status_changed'
    USER_LOGIN = 'user.login'
    USER_LOGOUT = 'user.logout'
    USER_PASSWORD_CHANGED = 'user.password_changed'
    USER_2FA_ENABLED = 'user.2fa_enabled'
    USER_2FA_DISABLED = 'user.2fa_disabled'
    USER_EMAIL_VERIFIED = 'user.email_verified'
    USER_EMAIL_CHANGED = 'user.email_changed'
    USER_LOCKED = 'user.locked'
    USER_UNLOCKED = 'user.unlocked'

    # Role events
    ROLE_CREATED = 'role.created'
    ROLE_UPDATED = 'role.updated'
    ROLE_DELETED = 'role.deleted'
    USER_ROLE_ASSIGNED = 'user.role_assigned'
    USER_ROLE_REVOKED = 'user.role_revoked'

    # Permission events
    PERMISSION_CREATED = 'permission.created'
    PERMISSION_UPDATED = 'permission.updated'
    PERMISSION_DELETED = 'permission.deleted'
    ROLE_PERMISSION_ADDED = 'role.permission_added'
    ROLE_PERMISSION_REMOVED = 'role.permission_removed'

    # Session events
    SESSION_CREATED = 'session.created'
    SESSION_TERMINATED = 'session.terminated'
    SESSION_EXPIRED = 'session.expired'


@dataclass
class BaseEvent:
    """Base class for all events."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ''
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str = '1.0'
    source: str = 'user-service'
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return asdict(self)

    def to_json_serializable(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        data = self.to_dict()
        # Convert any UUID or datetime objects
        return self._make_serializable(data)

    def _make_serializable(self, obj: Any) -> Any:
        """Recursively make objects JSON serializable."""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, (uuid.UUID, datetime)):
            return str(obj)
        elif isinstance(obj, Enum):
            return obj.value
        return obj


# ==================== USER EVENTS ====================

@dataclass
class UserEvent(BaseEvent):
    """Base class for user-related events."""

    user_id: str = ''
    organization_id: Optional[str] = None
    actor_id: Optional[str] = None  # User who triggered the event
    actor_email: Optional[str] = None


@dataclass
class UserCreatedEvent(UserEvent):
    """Event published when a new user is created."""

    event_type: str = EventType.USER_CREATED.value
    email: str = ''
    first_name: str = ''
    last_name: str = ''
    status: str = 'pending_verification'
    roles: List[str] = field(default_factory=list)
    created_by: Optional[str] = None  # 'self', 'admin', 'invitation'


@dataclass
class UserUpdatedEvent(UserEvent):
    """Event published when a user is updated."""

    event_type: str = EventType.USER_UPDATED.value
    changed_fields: List[str] = field(default_factory=list)
    old_values: Dict[str, Any] = field(default_factory=dict)
    new_values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserDeletedEvent(UserEvent):
    """Event published when a user is deleted (soft delete)."""

    event_type: str = EventType.USER_DELETED.value
    email: str = ''
    deleted_by: Optional[str] = None
    reason: Optional[str] = None


@dataclass
class UserStatusChangedEvent(UserEvent):
    """Event published when user status changes."""

    event_type: str = EventType.USER_STATUS_CHANGED.value
    old_status: str = ''
    new_status: str = ''
    reason: Optional[str] = None


@dataclass
class UserLoginEvent(UserEvent):
    """Event published when a user logs in."""

    event_type: str = EventType.USER_LOGIN.value
    session_id: str = ''
    ip_address: str = ''
    user_agent: str = ''
    device_type: Optional[str] = None
    location: Optional[str] = None
    two_factor_used: bool = False
    login_method: str = 'password'  # password, 2fa, sso, etc.


@dataclass
class UserLogoutEvent(UserEvent):
    """Event published when a user logs out."""

    event_type: str = EventType.USER_LOGOUT.value
    session_id: str = ''
    logout_type: str = 'manual'  # manual, timeout, forced


@dataclass
class UserPasswordChangedEvent(UserEvent):
    """Event published when a user's password is changed."""

    event_type: str = EventType.USER_PASSWORD_CHANGED.value
    change_type: str = 'change'  # change, reset, forced
    ip_address: Optional[str] = None


@dataclass
class User2FAEnabledEvent(UserEvent):
    """Event published when 2FA is enabled for a user."""

    event_type: str = EventType.USER_2FA_ENABLED.value
    method: str = 'totp'  # totp, sms, email


@dataclass
class User2FADisabledEvent(UserEvent):
    """Event published when 2FA is disabled for a user."""

    event_type: str = EventType.USER_2FA_DISABLED.value
    disabled_by: str = 'user'  # user, admin


# ==================== ROLE EVENTS ====================

@dataclass
class RoleEvent(BaseEvent):
    """Base class for role-related events."""

    role_id: str = ''
    role_code: str = ''
    organization_id: Optional[str] = None
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None


@dataclass
class RoleCreatedEvent(RoleEvent):
    """Event published when a new role is created."""

    event_type: str = EventType.ROLE_CREATED.value
    name: str = ''
    description: str = ''
    is_system_role: bool = False
    permissions: List[str] = field(default_factory=list)


@dataclass
class RoleUpdatedEvent(RoleEvent):
    """Event published when a role is updated."""

    event_type: str = EventType.ROLE_UPDATED.value
    changed_fields: List[str] = field(default_factory=list)
    old_values: Dict[str, Any] = field(default_factory=dict)
    new_values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoleDeletedEvent(RoleEvent):
    """Event published when a role is deleted."""

    event_type: str = EventType.ROLE_DELETED.value
    name: str = ''
    affected_users_count: int = 0


@dataclass
class UserRoleAssignedEvent(BaseEvent):
    """Event published when a role is assigned to a user."""

    event_type: str = EventType.USER_ROLE_ASSIGNED.value
    user_id: str = ''
    user_email: str = ''
    role_id: str = ''
    role_code: str = ''
    role_name: str = ''
    organization_id: Optional[str] = None
    location_id: Optional[str] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    assigned_by: Optional[str] = None
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserRoleRevokedEvent(BaseEvent):
    """Event published when a role is revoked from a user."""

    event_type: str = EventType.USER_ROLE_REVOKED.value
    user_id: str = ''
    user_email: str = ''
    role_id: str = ''
    role_code: str = ''
    role_name: str = ''
    organization_id: Optional[str] = None
    revoked_by: Optional[str] = None
    reason: Optional[str] = None


# ==================== PERMISSION EVENTS ====================

@dataclass
class PermissionEvent(BaseEvent):
    """Base class for permission-related events."""

    permission_id: str = ''
    permission_code: str = ''
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None


@dataclass
class PermissionCreatedEvent(PermissionEvent):
    """Event published when a new permission is created."""

    event_type: str = EventType.PERMISSION_CREATED.value
    name: str = ''
    module: str = ''
    action: str = ''


@dataclass
class PermissionUpdatedEvent(PermissionEvent):
    """Event published when a permission is updated."""

    event_type: str = EventType.PERMISSION_UPDATED.value
    changed_fields: List[str] = field(default_factory=list)
    old_values: Dict[str, Any] = field(default_factory=dict)
    new_values: Dict[str, Any] = field(default_factory=dict)
