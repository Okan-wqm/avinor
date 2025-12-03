# services/user-service/src/apps/core/events/__init__.py
"""
User Service Events

This module exports event classes and the event publisher for
inter-service communication.
"""

from .publisher import EventPublisher
from .types import (
    UserEvent,
    UserCreatedEvent,
    UserUpdatedEvent,
    UserDeletedEvent,
    UserStatusChangedEvent,
    UserLoginEvent,
    UserLogoutEvent,
    UserPasswordChangedEvent,
    User2FAEnabledEvent,
    User2FADisabledEvent,
    RoleEvent,
    RoleCreatedEvent,
    RoleUpdatedEvent,
    RoleDeletedEvent,
    UserRoleAssignedEvent,
    UserRoleRevokedEvent,
    PermissionEvent,
    PermissionCreatedEvent,
    PermissionUpdatedEvent,
)

__all__ = [
    # Publisher
    'EventPublisher',

    # User events
    'UserEvent',
    'UserCreatedEvent',
    'UserUpdatedEvent',
    'UserDeletedEvent',
    'UserStatusChangedEvent',
    'UserLoginEvent',
    'UserLogoutEvent',
    'UserPasswordChangedEvent',
    'User2FAEnabledEvent',
    'User2FADisabledEvent',

    # Role events
    'RoleEvent',
    'RoleCreatedEvent',
    'RoleUpdatedEvent',
    'RoleDeletedEvent',
    'UserRoleAssignedEvent',
    'UserRoleRevokedEvent',

    # Permission events
    'PermissionEvent',
    'PermissionCreatedEvent',
    'PermissionUpdatedEvent',
]
