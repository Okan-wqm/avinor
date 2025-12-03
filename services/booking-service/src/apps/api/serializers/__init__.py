# services/booking-service/src/apps/api/serializers/__init__.py
"""
Booking API Serializers
"""

from .booking_serializers import (
    BookingSerializer,
    BookingListSerializer,
    BookingDetailSerializer,
    BookingCreateSerializer,
    BookingUpdateSerializer,
    BookingStatusUpdateSerializer,
    BookingCancelSerializer,
    BookingCheckInSerializer,
    BookingDispatchSerializer,
    BookingCompleteSerializer,
    BookingConflictSerializer,
    BookingCalendarSerializer,
    BookingCostEstimateSerializer,
)

from .recurring_serializers import (
    RecurringPatternSerializer,
    RecurringPatternListSerializer,
    RecurringPatternDetailSerializer,
    RecurringPatternCreateSerializer,
    RecurringPatternUpdateSerializer,
    RecurringPatternOccurrenceSerializer,
)

from .availability_serializers import (
    AvailabilitySerializer,
    AvailabilityListSerializer,
    AvailabilityDetailSerializer,
    AvailabilityCreateSerializer,
    AvailabilityUpdateSerializer,
    OperatingHoursSerializer,
    OperatingHoursCreateSerializer,
    AvailableSlotSerializer,
    ResourceScheduleSerializer,
)

from .rule_serializers import (
    BookingRuleSerializer,
    BookingRuleListSerializer,
    BookingRuleDetailSerializer,
    BookingRuleCreateSerializer,
    BookingRuleUpdateSerializer,
    RuleValidationResultSerializer,
    CancellationFeeSerializer,
)

from .waitlist_serializers import (
    WaitlistEntrySerializer,
    WaitlistEntryListSerializer,
    WaitlistEntryDetailSerializer,
    WaitlistEntryCreateSerializer,
    WaitlistEntryUpdateSerializer,
    WaitlistOfferSerializer,
    WaitlistStatisticsSerializer,
)


__all__ = [
    # Booking
    'BookingSerializer',
    'BookingListSerializer',
    'BookingDetailSerializer',
    'BookingCreateSerializer',
    'BookingUpdateSerializer',
    'BookingStatusUpdateSerializer',
    'BookingCancelSerializer',
    'BookingCheckInSerializer',
    'BookingDispatchSerializer',
    'BookingCompleteSerializer',
    'BookingConflictSerializer',
    'BookingCalendarSerializer',
    'BookingCostEstimateSerializer',

    # Recurring
    'RecurringPatternSerializer',
    'RecurringPatternListSerializer',
    'RecurringPatternDetailSerializer',
    'RecurringPatternCreateSerializer',
    'RecurringPatternUpdateSerializer',
    'RecurringPatternOccurrenceSerializer',

    # Availability
    'AvailabilitySerializer',
    'AvailabilityListSerializer',
    'AvailabilityDetailSerializer',
    'AvailabilityCreateSerializer',
    'AvailabilityUpdateSerializer',
    'OperatingHoursSerializer',
    'OperatingHoursCreateSerializer',
    'AvailableSlotSerializer',
    'ResourceScheduleSerializer',

    # Rules
    'BookingRuleSerializer',
    'BookingRuleListSerializer',
    'BookingRuleDetailSerializer',
    'BookingRuleCreateSerializer',
    'BookingRuleUpdateSerializer',
    'RuleValidationResultSerializer',
    'CancellationFeeSerializer',

    # Waitlist
    'WaitlistEntrySerializer',
    'WaitlistEntryListSerializer',
    'WaitlistEntryDetailSerializer',
    'WaitlistEntryCreateSerializer',
    'WaitlistEntryUpdateSerializer',
    'WaitlistOfferSerializer',
    'WaitlistStatisticsSerializer',
]
