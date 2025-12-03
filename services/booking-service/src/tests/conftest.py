# services/booking-service/src/tests/conftest.py
"""
Pytest Configuration and Fixtures

Provides common fixtures for booking service tests.
"""

import uuid
from datetime import datetime, date, time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Provide API client for testing."""
    return APIClient()


@pytest.fixture
def organization_id():
    """Provide a test organization ID."""
    return uuid.uuid4()


@pytest.fixture
def user_id():
    """Provide a test user ID."""
    return uuid.uuid4()


@pytest.fixture
def location_id():
    """Provide a test location ID."""
    return uuid.uuid4()


@pytest.fixture
def aircraft_id():
    """Provide a test aircraft ID."""
    return uuid.uuid4()


@pytest.fixture
def instructor_id():
    """Provide a test instructor ID."""
    return uuid.uuid4()


@pytest.fixture
def student_id():
    """Provide a test student ID."""
    return uuid.uuid4()


@pytest.fixture
def auth_headers(organization_id, user_id):
    """Provide authentication headers for API requests."""
    return {
        'HTTP_X_ORGANIZATION_ID': str(organization_id),
        'HTTP_X_USER_ID': str(user_id),
    }


@pytest.fixture
def sample_booking_data(organization_id, location_id, aircraft_id, instructor_id, student_id):
    """Provide sample booking creation data."""
    start = timezone.now() + timedelta(days=1)
    start = start.replace(hour=10, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=2)

    return {
        'organization_id': organization_id,
        'location_id': location_id,
        'booking_type': 'training',
        'training_type': 'dual',
        'aircraft_id': aircraft_id,
        'instructor_id': instructor_id,
        'student_id': student_id,
        'scheduled_start': start.isoformat(),
        'scheduled_end': end.isoformat(),
        'preflight_minutes': 15,
        'postflight_minutes': 15,
        'route': 'ENGM-Local-ENGM',
    }


@pytest.fixture
def sample_recurring_pattern_data(organization_id, location_id, aircraft_id, instructor_id, student_id):
    """Provide sample recurring pattern data."""
    start_date = timezone.now().date() + timedelta(days=7)
    end_date = start_date + timedelta(days=30)

    return {
        'organization_id': organization_id,
        'location_id': location_id,
        'name': 'Weekly Training',
        'frequency': 'weekly',
        'interval': 1,
        'days_of_week': [1, 3],  # Monday and Wednesday
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'start_time': '10:00',
        'end_time': '12:00',
        'booking_type': 'training',
        'aircraft_id': aircraft_id,
        'instructor_id': instructor_id,
        'student_id': student_id,
    }


@pytest.fixture
def sample_availability_data(organization_id, aircraft_id):
    """Provide sample availability data."""
    start = timezone.now() + timedelta(days=1)
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)

    return {
        'organization_id': organization_id,
        'resource_type': 'aircraft',
        'resource_id': aircraft_id,
        'availability_type': 'unavailable',
        'start_datetime': start.isoformat(),
        'end_datetime': end.isoformat(),
        'reason': 'Scheduled maintenance',
    }


@pytest.fixture
def sample_rule_data(organization_id):
    """Provide sample booking rule data."""
    return {
        'organization_id': organization_id,
        'rule_type': 'general',
        'name': 'Default Booking Rules',
        'priority': 10,
        'min_booking_duration': 30,
        'max_booking_duration': 480,
        'min_notice_hours': 2,
        'max_advance_days': 30,
        'free_cancellation_hours': 24,
        'late_cancellation_fee_percent': '50.00',
    }


@pytest.fixture
def sample_waitlist_data(organization_id, user_id, aircraft_id, instructor_id, location_id):
    """Provide sample waitlist entry data."""
    requested_date = timezone.now().date() + timedelta(days=7)

    return {
        'organization_id': organization_id,
        'user_id': user_id,
        'user_name': 'Test User',
        'user_email': 'test@example.com',
        'requested_date': requested_date.isoformat(),
        'preferred_start_time': '10:00',
        'preferred_end_time': '12:00',
        'duration_minutes': 120,
        'booking_type': 'training',
        'aircraft_id': aircraft_id,
        'instructor_id': instructor_id,
        'location_id': location_id,
        'flexibility_days': 3,
    }


@pytest.fixture
def create_booking(organization_id, location_id):
    """Factory fixture for creating bookings."""
    from apps.core.models import Booking

    def _create_booking(**kwargs):
        defaults = {
            'organization_id': organization_id,
            'location_id': location_id,
            'booking_type': Booking.BookingType.TRAINING,
            'status': Booking.Status.SCHEDULED,
            'scheduled_start': timezone.now() + timedelta(days=1),
            'scheduled_end': timezone.now() + timedelta(days=1, hours=2),
        }
        defaults.update(kwargs)

        return Booking.objects.create(**defaults)

    return _create_booking


@pytest.fixture
def create_recurring_pattern(organization_id, location_id):
    """Factory fixture for creating recurring patterns."""
    from apps.core.models import RecurringPattern

    def _create_pattern(**kwargs):
        defaults = {
            'organization_id': organization_id,
            'location_id': location_id,
            'name': 'Test Pattern',
            'frequency': RecurringPattern.Frequency.WEEKLY,
            'interval': 1,
            'days_of_week': [1],
            'start_date': timezone.now().date() + timedelta(days=7),
            'start_time': time(10, 0),
            'end_time': time(12, 0),
            'booking_type': 'training',
        }
        defaults.update(kwargs)

        return RecurringPattern.objects.create(**defaults)

    return _create_pattern


@pytest.fixture
def create_availability(organization_id):
    """Factory fixture for creating availability entries."""
    from apps.core.models import Availability

    def _create_availability(**kwargs):
        defaults = {
            'organization_id': organization_id,
            'resource_type': 'aircraft',
            'resource_id': uuid.uuid4(),
            'availability_type': Availability.AvailabilityType.AVAILABLE,
            'start_datetime': timezone.now(),
            'end_datetime': timezone.now() + timedelta(days=1),
        }
        defaults.update(kwargs)

        return Availability.objects.create(**defaults)

    return _create_availability


@pytest.fixture
def create_rule(organization_id):
    """Factory fixture for creating booking rules."""
    from apps.core.models import BookingRule

    def _create_rule(**kwargs):
        defaults = {
            'organization_id': organization_id,
            'rule_type': BookingRule.RuleType.GENERAL,
            'name': 'Test Rule',
            'priority': 10,
            'is_active': True,
        }
        defaults.update(kwargs)

        return BookingRule.objects.create(**defaults)

    return _create_rule


@pytest.fixture
def create_waitlist_entry(organization_id, user_id):
    """Factory fixture for creating waitlist entries."""
    from apps.core.models import WaitlistEntry

    def _create_entry(**kwargs):
        defaults = {
            'organization_id': organization_id,
            'user_id': user_id,
            'requested_date': timezone.now().date() + timedelta(days=7),
            'status': WaitlistEntry.Status.WAITING,
        }
        defaults.update(kwargs)

        return WaitlistEntry.objects.create(**defaults)

    return _create_entry
