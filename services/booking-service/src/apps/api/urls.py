# services/booking-service/src/apps/api/urls.py
"""
Booking API URL Configuration

Defines all API routes for the booking service.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    # Booking
    BookingViewSet,
    BookingCalendarView,
    BookingConflictCheckView,
    BookingCostEstimateView,
    # Recurring
    RecurringPatternViewSet,
    # Availability
    AvailabilityViewSet,
    OperatingHoursViewSet,
    AvailableSlotsView,
    ResourceScheduleView,
    # Rules
    BookingRuleViewSet,
    RuleValidationView,
    CancellationFeeView,
    # Waitlist
    WaitlistEntryViewSet,
    WaitlistStatisticsView,
)

app_name = 'api'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'recurring', RecurringPatternViewSet, basename='recurring')
router.register(r'availability', AvailabilityViewSet, basename='availability')
router.register(r'operating-hours', OperatingHoursViewSet, basename='operating-hours')
router.register(r'rules', BookingRuleViewSet, basename='rule')
router.register(r'waitlist', WaitlistEntryViewSet, basename='waitlist')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),

    # Calendar and scheduling
    path('calendar/', BookingCalendarView.as_view(), name='calendar'),
    path('conflicts/', BookingConflictCheckView.as_view(), name='conflict-check'),
    path('cost-estimate/', BookingCostEstimateView.as_view(), name='cost-estimate'),

    # Availability
    path('slots/', AvailableSlotsView.as_view(), name='available-slots'),
    path('schedule/', ResourceScheduleView.as_view(), name='resource-schedule'),

    # Rules
    path('validate/', RuleValidationView.as_view(), name='rule-validation'),
    path('cancellation-fee/', CancellationFeeView.as_view(), name='cancellation-fee'),

    # Waitlist
    path('waitlist/statistics/', WaitlistStatisticsView.as_view(), name='waitlist-statistics'),
]
