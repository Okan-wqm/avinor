# services/booking-service/src/apps/api/views/__init__.py
"""
Booking API Views
"""

from .booking_views import (
    BookingViewSet,
    BookingCalendarView,
    BookingConflictCheckView,
    BookingCostEstimateView,
)

from .recurring_views import (
    RecurringPatternViewSet,
)

from .availability_views import (
    AvailabilityViewSet,
    OperatingHoursViewSet,
    AvailableSlotsView,
    ResourceScheduleView,
)

from .rule_views import (
    BookingRuleViewSet,
    RuleValidationView,
    CancellationFeeView,
)

from .waitlist_views import (
    WaitlistEntryViewSet,
    WaitlistStatisticsView,
)


__all__ = [
    # Booking
    'BookingViewSet',
    'BookingCalendarView',
    'BookingConflictCheckView',
    'BookingCostEstimateView',

    # Recurring
    'RecurringPatternViewSet',

    # Availability
    'AvailabilityViewSet',
    'OperatingHoursViewSet',
    'AvailableSlotsView',
    'ResourceScheduleView',

    # Rules
    'BookingRuleViewSet',
    'RuleValidationView',
    'CancellationFeeView',

    # Waitlist
    'WaitlistEntryViewSet',
    'WaitlistStatisticsView',
]
