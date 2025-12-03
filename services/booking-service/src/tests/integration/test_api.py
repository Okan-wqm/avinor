# services/booking-service/src/tests/integration/test_api.py
"""
Integration Tests for Booking API

Tests API endpoints with full request/response cycle.
"""

import uuid
from datetime import datetime, date, time, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import Booking, RecurringPattern, Availability, BookingRule, WaitlistEntry


@pytest.mark.django_db
class TestBookingAPI:
    """Integration tests for booking endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = APIClient()

    def test_list_bookings(self, auth_headers, create_booking):
        """Test listing bookings."""
        # Create some bookings
        for i in range(5):
            create_booking(status=Booking.Status.SCHEDULED)

        response = self.client.get(
            '/api/v1/bookings/bookings/',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert len(response.data['results']) >= 5

    def test_create_booking(self, auth_headers, sample_booking_data):
        """Test creating a new booking."""
        response = self.client.post(
            '/api/v1/bookings/bookings/',
            data=sample_booking_data,
            format='json',
            **auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert 'booking_number' in response.data
        assert response.data['booking_type'] == sample_booking_data['booking_type']

    def test_create_booking_validation_error(self, auth_headers, organization_id, location_id):
        """Test booking creation with validation errors."""
        # End time before start time
        start = timezone.now() + timedelta(days=1)
        data = {
            'organization_id': str(organization_id),
            'location_id': str(location_id),
            'booking_type': 'training',
            'scheduled_start': start.isoformat(),
            'scheduled_end': (start - timedelta(hours=1)).isoformat(),
        }

        response = self.client.post(
            '/api/v1/bookings/bookings/',
            data=data,
            format='json',
            **auth_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_booking_detail(self, auth_headers, create_booking):
        """Test retrieving booking details."""
        booking = create_booking(status=Booking.Status.SCHEDULED)

        response = self.client.get(
            f'/api/v1/bookings/bookings/{booking.id}/',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(booking.id)
        assert response.data['booking_number'] == booking.booking_number

    def test_update_booking(self, auth_headers, create_booking):
        """Test updating a booking."""
        booking = create_booking(status=Booking.Status.SCHEDULED)

        update_data = {
            'route': 'ENGM-ENBR-ENGM',
            'remarks': 'Updated remarks',
        }

        response = self.client.patch(
            f'/api/v1/bookings/bookings/{booking.id}/',
            data=update_data,
            format='json',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['route'] == 'ENGM-ENBR-ENGM'

    def test_confirm_booking(self, auth_headers, create_booking):
        """Test confirming a booking."""
        booking = create_booking(status=Booking.Status.SCHEDULED)

        response = self.client.post(
            f'/api/v1/bookings/bookings/{booking.id}/confirm/',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == Booking.Status.CONFIRMED

    def test_check_in_booking(self, auth_headers, create_booking):
        """Test checking in for a booking."""
        booking = create_booking(
            status=Booking.Status.CONFIRMED,
            scheduled_start=timezone.now() + timedelta(minutes=30),
            scheduled_end=timezone.now() + timedelta(hours=2),
        )

        response = self.client.post(
            f'/api/v1/bookings/bookings/{booking.id}/check_in/',
            data={'hobbs_reading': '1234.5'},
            format='json',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == Booking.Status.CHECKED_IN

    def test_cancel_booking(self, auth_headers, create_booking):
        """Test cancelling a booking."""
        booking = create_booking(status=Booking.Status.SCHEDULED)

        response = self.client.post(
            f'/api/v1/bookings/bookings/{booking.id}/cancel/',
            data={
                'cancellation_type': 'user',
                'reason': 'Changed plans',
            },
            format='json',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == Booking.Status.CANCELLED

    def test_my_bookings(self, auth_headers, create_booking, user_id):
        """Test getting current user's bookings."""
        # Create bookings for user
        for _ in range(3):
            create_booking(student_id=user_id, status=Booking.Status.SCHEDULED)

        response = self.client.get(
            '/api/v1/bookings/bookings/my_bookings/',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK

    def test_conflict_check(self, auth_headers, create_booking, organization_id, aircraft_id):
        """Test conflict checking endpoint."""
        # Create existing booking
        start = timezone.now() + timedelta(days=1)
        start = start.replace(hour=10, minute=0, second=0, microsecond=0)
        create_booking(
            aircraft_id=aircraft_id,
            scheduled_start=start,
            scheduled_end=start + timedelta(hours=2),
            status=Booking.Status.SCHEDULED,
        )

        # Check for conflict
        data = {
            'organization_id': str(organization_id),
            'scheduled_start': (start + timedelta(hours=1)).isoformat(),
            'scheduled_end': (start + timedelta(hours=3)).isoformat(),
            'aircraft_id': str(aircraft_id),
        }

        response = self.client.post(
            '/api/v1/bookings/conflicts/',
            data=data,
            format='json',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['has_conflicts'] is True
        assert len(response.data['conflicts']) > 0

    def test_calendar_view(self, auth_headers, organization_id, create_booking):
        """Test calendar view endpoint."""
        # Create bookings across several days
        for i in range(5):
            create_booking(
                scheduled_start=timezone.now() + timedelta(days=i, hours=10),
                scheduled_end=timezone.now() + timedelta(days=i, hours=12),
                status=Booking.Status.SCHEDULED,
            )

        today = timezone.now().date()
        response = self.client.get(
            '/api/v1/bookings/calendar/',
            {
                'start_date': today.isoformat(),
                'end_date': (today + timedelta(days=7)).isoformat(),
            },
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestRecurringPatternAPI:
    """Integration tests for recurring pattern endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = APIClient()

    def test_create_recurring_pattern(self, auth_headers, sample_recurring_pattern_data):
        """Test creating a recurring pattern."""
        response = self.client.post(
            '/api/v1/bookings/recurring/',
            data=sample_recurring_pattern_data,
            format='json',
            **auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == sample_recurring_pattern_data['name']
        assert response.data['frequency'] == sample_recurring_pattern_data['frequency']

    def test_list_recurring_patterns(self, auth_headers, create_recurring_pattern):
        """Test listing recurring patterns."""
        for i in range(3):
            create_recurring_pattern(name=f'Pattern {i}')

        response = self.client.get(
            '/api/v1/bookings/recurring/',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_pause_pattern(self, auth_headers, create_recurring_pattern):
        """Test pausing a recurring pattern."""
        pattern = create_recurring_pattern(status=RecurringPattern.Status.ACTIVE)

        response = self.client.post(
            f'/api/v1/bookings/recurring/{pattern.id}/pause/',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == RecurringPattern.Status.PAUSED

    def test_resume_pattern(self, auth_headers, create_recurring_pattern):
        """Test resuming a paused pattern."""
        pattern = create_recurring_pattern(status=RecurringPattern.Status.PAUSED)

        response = self.client.post(
            f'/api/v1/bookings/recurring/{pattern.id}/resume/',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == RecurringPattern.Status.ACTIVE

    def test_get_occurrences(self, auth_headers, create_recurring_pattern):
        """Test getting pattern occurrences."""
        pattern = create_recurring_pattern()

        response = self.client.get(
            f'/api/v1/bookings/recurring/{pattern.id}/occurrences/',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)


@pytest.mark.django_db
class TestAvailabilityAPI:
    """Integration tests for availability endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = APIClient()

    def test_create_availability(self, auth_headers, sample_availability_data):
        """Test creating availability entry."""
        response = self.client.post(
            '/api/v1/bookings/availability/',
            data=sample_availability_data,
            format='json',
            **auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['reason'] == sample_availability_data['reason']

    def test_list_availability(self, auth_headers, create_availability):
        """Test listing availability entries."""
        for _ in range(3):
            create_availability()

        response = self.client.get(
            '/api/v1/bookings/availability/',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK

    def test_check_resource_availability(self, auth_headers, organization_id, aircraft_id, create_availability):
        """Test checking resource availability."""
        # Create unavailability block
        start = timezone.now() + timedelta(days=1)
        create_availability(
            resource_type='aircraft',
            resource_id=aircraft_id,
            availability_type=Availability.AvailabilityType.UNAVAILABLE,
            start_datetime=start,
            end_datetime=start + timedelta(hours=4),
        )

        response = self.client.post(
            '/api/v1/bookings/availability/check/',
            data={
                'resource_type': 'aircraft',
                'resource_id': str(aircraft_id),
                'start': (start + timedelta(hours=1)).isoformat(),
                'end': (start + timedelta(hours=2)).isoformat(),
            },
            format='json',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['available'] is False

    def test_get_available_slots(self, auth_headers, organization_id, aircraft_id):
        """Test getting available slots."""
        target_date = (timezone.now() + timedelta(days=1)).date()

        response = self.client.get(
            '/api/v1/bookings/slots/',
            {
                'date': target_date.isoformat(),
                'duration': 60,
                'aircraft_id': str(aircraft_id),
            },
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'slots' in response.data


@pytest.mark.django_db
class TestBookingRuleAPI:
    """Integration tests for booking rule endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = APIClient()

    def test_create_rule(self, auth_headers, sample_rule_data):
        """Test creating a booking rule."""
        response = self.client.post(
            '/api/v1/bookings/rules/',
            data=sample_rule_data,
            format='json',
            **auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == sample_rule_data['name']

    def test_list_rules(self, auth_headers, create_rule):
        """Test listing booking rules."""
        for i in range(3):
            create_rule(name=f'Rule {i}')

        response = self.client.get(
            '/api/v1/bookings/rules/',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_validate_booking_against_rules(self, auth_headers, organization_id, create_rule, user_id):
        """Test validating booking against rules."""
        create_rule(
            min_booking_duration=60,
            max_booking_duration=240,
        )

        start = timezone.now() + timedelta(days=1)

        response = self.client.post(
            '/api/v1/bookings/validate/',
            data={
                'organization_id': str(organization_id),
                'scheduled_start': start.isoformat(),
                'scheduled_end': (start + timedelta(hours=2)).isoformat(),
                'user_id': str(user_id),
            },
            format='json',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'valid' in response.data
        assert 'rules_applied' in response.data

    def test_calculate_cancellation_fee(self, auth_headers, organization_id, create_rule):
        """Test cancellation fee calculation."""
        create_rule(
            free_cancellation_hours=24,
            late_cancellation_fee_percent=Decimal('50.00'),
        )

        response = self.client.post(
            '/api/v1/bookings/cancellation-fee/',
            data={
                'organization_id': str(organization_id),
                'hours_until_start': 12,
                'estimated_cost': '500.00',
            },
            format='json',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'fee' in response.data
        assert 'is_late' in response.data


@pytest.mark.django_db
class TestWaitlistAPI:
    """Integration tests for waitlist endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = APIClient()

    def test_add_to_waitlist(self, auth_headers, sample_waitlist_data):
        """Test adding to waitlist."""
        response = self.client.post(
            '/api/v1/bookings/waitlist/',
            data=sample_waitlist_data,
            format='json',
            **auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == WaitlistEntry.Status.WAITING

    def test_list_waitlist_entries(self, auth_headers, create_waitlist_entry):
        """Test listing waitlist entries."""
        for _ in range(3):
            create_waitlist_entry()

        response = self.client.get(
            '/api/v1/bookings/waitlist/',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK

    def test_send_offer(self, auth_headers, create_waitlist_entry):
        """Test sending offer to waitlist entry."""
        entry = create_waitlist_entry()
        booking_id = uuid.uuid4()

        response = self.client.post(
            f'/api/v1/bookings/waitlist/{entry.id}/send_offer/',
            data={
                'booking_id': str(booking_id),
                'message': 'Slot available!',
                'expires_in_hours': 4,
            },
            format='json',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == WaitlistEntry.Status.OFFERED

    def test_accept_offer(self, auth_headers, create_waitlist_entry):
        """Test accepting waitlist offer."""
        entry = create_waitlist_entry()
        entry.status = WaitlistEntry.Status.OFFERED
        entry.offered_booking_id = uuid.uuid4()
        entry.offer_expires_at = timezone.now() + timedelta(hours=4)
        entry.save()

        response = self.client.post(
            f'/api/v1/bookings/waitlist/{entry.id}/accept/',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == WaitlistEntry.Status.ACCEPTED

    def test_decline_offer(self, auth_headers, create_waitlist_entry):
        """Test declining waitlist offer."""
        entry = create_waitlist_entry()
        entry.status = WaitlistEntry.Status.OFFERED
        entry.offered_booking_id = uuid.uuid4()
        entry.offer_expires_at = timezone.now() + timedelta(hours=4)
        entry.save()

        response = self.client.post(
            f'/api/v1/bookings/waitlist/{entry.id}/decline/',
            data={'notes': 'Time does not work'},
            format='json',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == WaitlistEntry.Status.DECLINED

    def test_waitlist_statistics(self, auth_headers, create_waitlist_entry):
        """Test waitlist statistics endpoint."""
        for _ in range(5):
            create_waitlist_entry()

        response = self.client.get(
            '/api/v1/bookings/waitlist/statistics/',
            **auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'total' in response.data
        assert 'waiting' in response.data
        assert 'fulfillment_rate' in response.data
