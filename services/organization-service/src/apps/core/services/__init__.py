# services/organization-service/src/apps/core/services/__init__.py
"""
Organization Service Business Logic

This module exports all services and exceptions.
"""

from .organization_service import (
    OrganizationService,
    OrganizationError,
    OrganizationNotFoundError,
    OrganizationValidationError,
    OrganizationLimitExceededError,
    SlugAlreadyExistsError,
    DomainAlreadyExistsError,
)

from .location_service import (
    LocationService,
    LocationError,
    LocationNotFoundError,
    LocationValidationError,
)

from .subscription_service import (
    SubscriptionService,
    SubscriptionError,
    PlanNotFoundError,
    SubscriptionLimitError,
    DowngradeNotAllowedError,
)

from .invitation_service import (
    InvitationService,
    InvitationError,
    InvitationNotFoundError,
    InvitationExpiredError,
    InvitationAlreadyAcceptedError,
)

__all__ = [
    # Organization Service
    'OrganizationService',
    'OrganizationError',
    'OrganizationNotFoundError',
    'OrganizationValidationError',
    'OrganizationLimitExceededError',
    'SlugAlreadyExistsError',
    'DomainAlreadyExistsError',

    # Location Service
    'LocationService',
    'LocationError',
    'LocationNotFoundError',
    'LocationValidationError',

    # Subscription Service
    'SubscriptionService',
    'SubscriptionError',
    'PlanNotFoundError',
    'SubscriptionLimitError',
    'DowngradeNotAllowedError',

    # Invitation Service
    'InvitationService',
    'InvitationError',
    'InvitationNotFoundError',
    'InvitationExpiredError',
    'InvitationAlreadyAcceptedError',
]
