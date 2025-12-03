# services/booking-service/src/apps/core/services/__init__.py
"""
Booking Service Business Logic
"""

from .booking_service import BookingService
from .availability_service import AvailabilityService
from .rule_service import RuleService
from .waitlist_service import WaitlistService


# Custom Exceptions
class BookingServiceError(Exception):
    """Base exception for booking service errors."""
    pass


class BookingNotFoundError(BookingServiceError):
    """Booking not found."""
    pass


class BookingConflictError(BookingServiceError):
    """Booking conflicts with existing reservation."""
    pass


class BookingValidationError(BookingServiceError):
    """Booking validation failed."""
    pass


class BookingStateError(BookingServiceError):
    """Invalid booking state transition."""
    pass


class RuleViolationError(BookingServiceError):
    """Booking rule violation."""
    pass


class AvailabilityError(BookingServiceError):
    """Resource not available."""
    pass


class PrerequisiteError(BookingServiceError):
    """Prerequisites not met."""
    pass


class InsufficientBalanceError(BookingServiceError):
    """Insufficient account balance."""
    pass


class WaitlistError(BookingServiceError):
    """Waitlist operation error."""
    pass


__all__ = [
    # Services
    'BookingService',
    'AvailabilityService',
    'RuleService',
    'WaitlistService',

    # Exceptions
    'BookingServiceError',
    'BookingNotFoundError',
    'BookingConflictError',
    'BookingValidationError',
    'BookingStateError',
    'RuleViolationError',
    'AvailabilityError',
    'PrerequisiteError',
    'InsufficientBalanceError',
    'WaitlistError',
]
