# services/booking-service/src/apps/api/views/filters.py
"""
API Filters

Django Filter classes for booking API.
"""

import django_filters
from django.db.models import Q

from apps.core.models import Booking, RecurringPattern, WaitlistEntry


class BookingFilter(django_filters.FilterSet):
    """Filter for booking queries."""

    # Date filters
    date = django_filters.DateFilter(
        field_name='scheduled_start',
        lookup_expr='date'
    )
    date_from = django_filters.DateFilter(
        field_name='scheduled_start',
        lookup_expr='date__gte'
    )
    date_to = django_filters.DateFilter(
        field_name='scheduled_start',
        lookup_expr='date__lte'
    )

    # Time range
    start_after = django_filters.DateTimeFilter(
        field_name='scheduled_start',
        lookup_expr='gte'
    )
    start_before = django_filters.DateTimeFilter(
        field_name='scheduled_start',
        lookup_expr='lte'
    )

    # Status filters
    status = django_filters.ChoiceFilter(
        choices=Booking.Status.choices
    )
    status_in = django_filters.BaseInFilter(
        field_name='status'
    )
    active = django_filters.BooleanFilter(
        method='filter_active'
    )

    # Resource filters
    aircraft_id = django_filters.UUIDFilter()
    instructor_id = django_filters.UUIDFilter()
    student_id = django_filters.UUIDFilter()
    pilot_id = django_filters.UUIDFilter()
    location_id = django_filters.UUIDFilter()

    # Type filters
    booking_type = django_filters.ChoiceFilter(
        choices=Booking.BookingType.choices
    )
    training_type = django_filters.ChoiceFilter(
        choices=Booking.TrainingType.choices
    )

    # User involvement (any role)
    user_involved = django_filters.UUIDFilter(
        method='filter_user_involved'
    )

    # Booking number search
    booking_number = django_filters.CharFilter(
        lookup_expr='icontains'
    )

    # Created by
    created_by = django_filters.UUIDFilter()

    # Recurring pattern
    recurring_pattern_id = django_filters.UUIDFilter()
    is_recurring = django_filters.BooleanFilter(
        method='filter_is_recurring'
    )

    # Payment status
    payment_status = django_filters.ChoiceFilter(
        choices=Booking.PaymentStatus.choices
    )

    class Meta:
        model = Booking
        fields = [
            'status', 'booking_type', 'training_type',
            'aircraft_id', 'instructor_id', 'student_id', 'pilot_id',
            'location_id', 'created_by', 'recurring_pattern_id',
            'payment_status',
        ]

    def filter_active(self, queryset, name, value):
        """Filter for active (non-cancelled, non-completed) bookings."""
        if value:
            return queryset.filter(
                status__in=Booking.get_active_statuses()
            )
        return queryset.exclude(
            status__in=Booking.get_active_statuses()
        )

    def filter_user_involved(self, queryset, name, value):
        """Filter bookings where user is involved in any role."""
        return queryset.filter(
            Q(student_id=value) |
            Q(pilot_id=value) |
            Q(instructor_id=value) |
            Q(created_by=value)
        )

    def filter_is_recurring(self, queryset, name, value):
        """Filter for recurring vs one-time bookings."""
        if value:
            return queryset.filter(recurring_pattern_id__isnull=False)
        return queryset.filter(recurring_pattern_id__isnull=True)


class RecurringPatternFilter(django_filters.FilterSet):
    """Filter for recurring pattern queries."""

    status = django_filters.ChoiceFilter(
        choices=RecurringPattern.Status.choices
    )
    frequency = django_filters.ChoiceFilter(
        choices=RecurringPattern.Frequency.choices
    )

    # Date filters
    start_date_from = django_filters.DateFilter(
        field_name='start_date',
        lookup_expr='gte'
    )
    start_date_to = django_filters.DateFilter(
        field_name='start_date',
        lookup_expr='lte'
    )
    end_date_before = django_filters.DateFilter(
        field_name='end_date',
        lookup_expr='lte'
    )

    # Resource filters
    aircraft_id = django_filters.UUIDFilter()
    instructor_id = django_filters.UUIDFilter()
    student_id = django_filters.UUIDFilter()
    location_id = django_filters.UUIDFilter()

    # Active filter
    is_active = django_filters.BooleanFilter(
        method='filter_is_active'
    )

    class Meta:
        model = RecurringPattern
        fields = [
            'status', 'frequency',
            'aircraft_id', 'instructor_id', 'student_id', 'location_id',
        ]

    def filter_is_active(self, queryset, name, value):
        """Filter for active patterns."""
        if value:
            return queryset.filter(status=RecurringPattern.Status.ACTIVE)
        return queryset.exclude(status=RecurringPattern.Status.ACTIVE)


class WaitlistFilter(django_filters.FilterSet):
    """Filter for waitlist queries."""

    status = django_filters.ChoiceFilter(
        choices=WaitlistEntry.Status.choices
    )

    # Date filters
    requested_date = django_filters.DateFilter()
    requested_date_from = django_filters.DateFilter(
        field_name='requested_date',
        lookup_expr='gte'
    )
    requested_date_to = django_filters.DateFilter(
        field_name='requested_date',
        lookup_expr='lte'
    )

    # Resource filters
    user_id = django_filters.UUIDFilter()
    aircraft_id = django_filters.UUIDFilter()
    instructor_id = django_filters.UUIDFilter()
    location_id = django_filters.UUIDFilter()

    # Priority filter
    priority_min = django_filters.NumberFilter(
        field_name='priority',
        lookup_expr='gte'
    )

    # Active filter
    is_active = django_filters.BooleanFilter(
        method='filter_is_active'
    )

    # Has offer
    has_offer = django_filters.BooleanFilter(
        method='filter_has_offer'
    )

    class Meta:
        model = WaitlistEntry
        fields = [
            'status', 'user_id', 'aircraft_id', 'instructor_id', 'location_id',
        ]

    def filter_is_active(self, queryset, name, value):
        """Filter for active waitlist entries."""
        active_statuses = [
            WaitlistEntry.Status.WAITING,
            WaitlistEntry.Status.OFFERED
        ]
        if value:
            return queryset.filter(status__in=active_statuses)
        return queryset.exclude(status__in=active_statuses)

    def filter_has_offer(self, queryset, name, value):
        """Filter for entries with pending offers."""
        if value:
            return queryset.filter(status=WaitlistEntry.Status.OFFERED)
        return queryset.exclude(status=WaitlistEntry.Status.OFFERED)
