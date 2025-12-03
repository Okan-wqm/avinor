# services/organization-service/src/apps/core/events/definitions.py
"""
Event Definitions

Defines all event types and schemas for the Organization Service.
Events follow CloudEvents specification.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict


# =============================================================================
# Event Type Enums
# =============================================================================

class OrganizationEventType(str, Enum):
    """Organization-related event types."""

    CREATED = 'organization.created'
    UPDATED = 'organization.updated'
    DELETED = 'organization.deleted'
    ACTIVATED = 'organization.activated'
    SUSPENDED = 'organization.suspended'
    BRANDING_UPDATED = 'organization.branding.updated'
    SETTINGS_UPDATED = 'organization.settings.updated'
    DOMAIN_SETUP = 'organization.domain.setup'
    DOMAIN_VERIFIED = 'organization.domain.verified'


class LocationEventType(str, Enum):
    """Location-related event types."""

    CREATED = 'location.created'
    UPDATED = 'location.updated'
    DELETED = 'location.deleted'
    PRIMARY_CHANGED = 'location.primary.changed'
    ACTIVATED = 'location.activated'
    DEACTIVATED = 'location.deactivated'


class SubscriptionEventType(str, Enum):
    """Subscription-related event types."""

    PLAN_CHANGED = 'subscription.plan.changed'
    TRIAL_STARTED = 'subscription.trial.started'
    TRIAL_EXTENDED = 'subscription.trial.extended'
    TRIAL_CONVERTED = 'subscription.trial.converted'
    TRIAL_EXPIRED = 'subscription.trial.expired'
    CANCELLED = 'subscription.cancelled'
    REACTIVATED = 'subscription.reactivated'
    LIMITS_UPDATED = 'subscription.limits.updated'
    PAYMENT_RECEIVED = 'subscription.payment.received'
    PAYMENT_FAILED = 'subscription.payment.failed'


class InvitationEventType(str, Enum):
    """Invitation-related event types."""

    CREATED = 'invitation.created'
    SENT = 'invitation.sent'
    RESENT = 'invitation.resent'
    ACCEPTED = 'invitation.accepted'
    CANCELLED = 'invitation.cancelled'
    REVOKED = 'invitation.revoked'
    EXPIRED = 'invitation.expired'
    BULK_CREATED = 'invitation.bulk.created'


# =============================================================================
# CloudEvents Base Structure
# =============================================================================

@dataclass
class CloudEvent:
    """
    CloudEvents specification compliant event structure.

    See: https://cloudevents.io/
    """

    # Required fields
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = 'organization-service'
    specversion: str = '1.0'
    type: str = ''
    time: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')

    # Optional fields
    datacontenttype: str = 'application/json'
    subject: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    # Extension fields
    organizationid: Optional[str] = None
    userid: Optional[str] = None
    correlationid: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}


# =============================================================================
# Event Builders
# =============================================================================

def build_organization_event(
    event_type: OrganizationEventType,
    organization_id: str,
    data: Dict[str, Any],
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> CloudEvent:
    """
    Build an organization event.

    Args:
        event_type: Type of organization event
        organization_id: Organization UUID
        data: Event payload data
        user_id: User who triggered the event
        correlation_id: Correlation ID for tracing

    Returns:
        CloudEvent instance
    """
    return CloudEvent(
        type=event_type.value,
        subject=f'organization/{organization_id}',
        data=data,
        organizationid=organization_id,
        userid=user_id,
        correlationid=correlation_id,
    )


def build_location_event(
    event_type: LocationEventType,
    organization_id: str,
    location_id: str,
    data: Dict[str, Any],
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> CloudEvent:
    """
    Build a location event.

    Args:
        event_type: Type of location event
        organization_id: Organization UUID
        location_id: Location UUID
        data: Event payload data
        user_id: User who triggered the event
        correlation_id: Correlation ID for tracing

    Returns:
        CloudEvent instance
    """
    return CloudEvent(
        type=event_type.value,
        subject=f'organization/{organization_id}/location/{location_id}',
        data=data,
        organizationid=organization_id,
        userid=user_id,
        correlationid=correlation_id,
    )


def build_subscription_event(
    event_type: SubscriptionEventType,
    organization_id: str,
    data: Dict[str, Any],
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> CloudEvent:
    """
    Build a subscription event.

    Args:
        event_type: Type of subscription event
        organization_id: Organization UUID
        data: Event payload data
        user_id: User who triggered the event
        correlation_id: Correlation ID for tracing

    Returns:
        CloudEvent instance
    """
    return CloudEvent(
        type=event_type.value,
        subject=f'organization/{organization_id}/subscription',
        data=data,
        organizationid=organization_id,
        userid=user_id,
        correlationid=correlation_id,
    )


def build_invitation_event(
    event_type: InvitationEventType,
    organization_id: str,
    invitation_id: str,
    data: Dict[str, Any],
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> CloudEvent:
    """
    Build an invitation event.

    Args:
        event_type: Type of invitation event
        organization_id: Organization UUID
        invitation_id: Invitation UUID
        data: Event payload data
        user_id: User who triggered the event
        correlation_id: Correlation ID for tracing

    Returns:
        CloudEvent instance
    """
    return CloudEvent(
        type=event_type.value,
        subject=f'organization/{organization_id}/invitation/{invitation_id}',
        data=data,
        organizationid=organization_id,
        userid=user_id,
        correlationid=correlation_id,
    )


# =============================================================================
# Event Data Schemas
# =============================================================================

def organization_created_data(
    organization_id: str,
    name: str,
    slug: str,
    organization_type: str,
    email: str,
    country_code: str,
    created_by: str,
) -> Dict[str, Any]:
    """Build data payload for organization.created event."""
    return {
        'organization_id': organization_id,
        'name': name,
        'slug': slug,
        'organization_type': organization_type,
        'email': email,
        'country_code': country_code,
        'created_by': created_by,
        'created_at': datetime.utcnow().isoformat() + 'Z',
    }


def organization_updated_data(
    organization_id: str,
    changes: Dict[str, Any],
    updated_by: str,
) -> Dict[str, Any]:
    """Build data payload for organization.updated event."""
    return {
        'organization_id': organization_id,
        'changes': changes,
        'updated_by': updated_by,
        'updated_at': datetime.utcnow().isoformat() + 'Z',
    }


def subscription_changed_data(
    organization_id: str,
    from_plan: Optional[str],
    to_plan: str,
    billing_cycle: str,
    changed_by: str,
    effective_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build data payload for subscription.plan.changed event."""
    return {
        'organization_id': organization_id,
        'from_plan': from_plan,
        'to_plan': to_plan,
        'billing_cycle': billing_cycle,
        'changed_by': changed_by,
        'effective_at': effective_at or datetime.utcnow().isoformat() + 'Z',
    }


def invitation_created_data(
    invitation_id: str,
    organization_id: str,
    email: str,
    role_code: Optional[str],
    invited_by: str,
    expires_at: str,
) -> Dict[str, Any]:
    """Build data payload for invitation.created event."""
    return {
        'invitation_id': invitation_id,
        'organization_id': organization_id,
        'email': email,
        'role_code': role_code,
        'invited_by': invited_by,
        'expires_at': expires_at,
        'created_at': datetime.utcnow().isoformat() + 'Z',
    }


def invitation_accepted_data(
    invitation_id: str,
    organization_id: str,
    email: str,
    accepted_by_user_id: str,
    role_code: Optional[str],
) -> Dict[str, Any]:
    """Build data payload for invitation.accepted event."""
    return {
        'invitation_id': invitation_id,
        'organization_id': organization_id,
        'email': email,
        'accepted_by_user_id': accepted_by_user_id,
        'role_code': role_code,
        'accepted_at': datetime.utcnow().isoformat() + 'Z',
    }
