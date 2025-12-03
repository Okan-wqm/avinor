# services/booking-service/src/tests/unit/test_services.py
"""
Unit Tests for Booking Services

Tests for service layer business logic.
"""

import uuid
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.utils import timezone

from apps.core.models import Booking, RecurringPattern, Availability, BookingRule, WaitlistEntry
from apps.core.services import (
    BookingService,
    AvailabilityService,
    RuleService,
    WaitlistService,
    BookingNotFoundError,
    BookingConflictError,
    BookingValidationError,
    BookingStateError,
    RuleViolationError,
    WaitlistError,
)


@pytest.mark.django_db
class TestBookingService:
    """Tests for BookingService."""

    def setup_method(self):
        """Set up test dependencies."""
        self.service = BookingService()

    def test_create_booking_success(self, organization_id, location_id, aircraft_id, student_id):
        """Test successful booking creation."""
        start = timezone.now() + timedelta(days=1)
        start = start.replace(hour=10, minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=2)

        booking = self.service.create_booking(
            organization_id=organization_id,
            location_id=location_id,
            scheduled_start=start,
            scheduled_end=end,
            booking_type=Booking.BookingType.RENTAL,
            aircraft_id=aircraft_id,
            student_id=student_id,
        )

        assert booking.id is not None
        assert booking.booking_number is not None
        assert booking.status == Booking.Status.DRAFT

    def test_create_booking_with_conflict(
        self, organization_id, location_id, aircraft_id, student_id
    ):
        """Test booking creation fails with conflict."""
        start = timezone.now() + timedelta(days=1)
        start = start.replace(hour=10, minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=2)

        # Create first booking
        booking1 = self.service.create_booking(
            organization_id=organization_id,
            location_id=location_id,
            scheduled_start=start,
            scheduled_end=end,
            booking_type=Booking.BookingType.RENTAL,
            aircraft_id=aircraft_id,
            student_id=student_id,
        )
        booking1.status = Booking.Status.SCHEDULED
        booking1.save()

        # Try to create overlapping booking
        with pytest.raises(BookingConflictError):
            self.service.create_booking(
                organization_id=organization_id,
                location_id=location_id,
                scheduled_start=start + timedelta(hours=1),
                scheduled_end=end + timedelta(hours=1),
                booking_type=Booking.BookingType.RENTAL,
                aircraft_id=aircraft_id,
                student_id=uuid.uuid4(),
            )

    def test_create_booking_validate_only(self, organization_id, location_id, aircraft_id):
        """Test booking validation without creation."""
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=2)

        result = self.service.create_booking(
            organization_id=organization_id,
            location_id=location_id,
            scheduled_start=start,
            scheduled_end=end,
            booking_type=Booking.BookingType.RENTAL,
            aircraft_id=aircraft_id,
            validate_only=True,
        )

        # Should return validation result, not booking
        assert result is None or isinstance(result, dict)

    def test_update_booking(self, create_booking):
        """Test booking update."""
        booking = create_booking(status=Booking.Status.SCHEDULED)

        new_route = 'ENGM-ENBR-ENGM'
        updated = self.service.update_booking(
            booking_id=booking.id,
            route=new_route,
        )

        assert updated.route == new_route

    def test_update_booking_invalid_status(self, create_booking):
        """Test update fails for completed booking."""
        booking = create_booking(status=Booking.Status.COMPLETED)

        with pytest.raises(BookingStateError):
            self.service.update_booking(
                booking_id=booking.id,
                route='New Route',
            )

    def test_confirm_booking(self, create_booking):
        """Test booking confirmation."""
        booking = create_booking(status=Booking.Status.SCHEDULED)

        confirmed = self.service.confirm_booking(booking.id)

        assert confirmed.status == Booking.Status.CONFIRMED

    def test_check_in(self, create_booking):
        """Test booking check-in."""
        booking = create_booking(
            status=Booking.Status.CONFIRMED,
            scheduled_start=timezone.now() + timedelta(minutes=30),
            scheduled_end=timezone.now() + timedelta(hours=2),
        )

        checked_in = self.service.check_in(booking.id)

        assert checked_in.status == Booking.Status.CHECKED_IN

    def test_cancel_booking(self, create_booking, user_id):
        """Test booking cancellation."""
        booking = create_booking(status=Booking.Status.SCHEDULED)

        cancelled = self.service.cancel_booking(
            booking_id=booking.id,
            cancelled_by=user_id,
            reason='Test cancellation',
        )

        assert cancelled.status == Booking.Status.CANCELLED
        assert cancelled.cancellation_reason == 'Test cancellation'

    def test_mark_no_show(self, create_booking, user_id):
        """Test marking booking as no-show."""
        # Create booking scheduled for the past
        booking = create_booking(
            status=Booking.Status.CONFIRMED,
            scheduled_start=timezone.now() - timedelta(hours=2),
            scheduled_end=timezone.now() - timedelta(hours=1),
        )

        no_show = self.service.mark_no_show(booking.id, marked_by=user_id)

        assert no_show.status == Booking.Status.NO_SHOW
        assert no_show.no_show_at is not None

    def test_get_calendar(self, create_booking, organization_id):
        """Test calendar view generation."""
        today = timezone.now().date()

        # Create some bookings
        for i in range(3):
            create_booking(
                scheduled_start=timezone.now() + timedelta(days=i, hours=10),
                scheduled_end=timezone.now() + timedelta(days=i, hours=12),
                status=Booking.Status.SCHEDULED,
            )

        calendar = self.service.get_calendar(
            organization_id=organization_id,
            start_date=today,
            end_date=today + timedelta(days=7),
        )

        assert 'days' in calendar
        assert len(calendar['days']) <= 8


@pytest.mark.django_db
class TestAvailabilityService:
    """Tests for AvailabilityService."""

    def setup_method(self):
        """Set up test dependencies."""
        self.service = AvailabilityService()

    def test_create_availability(self, organization_id, aircraft_id):
        """Test availability creation."""
        start = timezone.now()
        end = start + timedelta(days=1)

        availability = self.service.create_availability(
            organization_id=organization_id,
            resource_type='aircraft',
            resource_id=aircraft_id,
            availability_type='unavailable',
            start_datetime=start,
            end_datetime=end,
            reason='Scheduled maintenance',
        )

        assert availability.id is not None
        assert availability.reason == 'Scheduled maintenance'

    def test_is_resource_available(self, organization_id, aircraft_id):
        """Test resource availability check."""
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=4)

        # Create unavailability
        self.service.create_availability(
            organization_id=organization_id,
            resource_type='aircraft',
            resource_id=aircraft_id,
            availability_type='unavailable',
            start_datetime=start,
            end_datetime=end,
        )

        # Check during unavailable period
        result = self.service.is_resource_available(
            organization_id=organization_id,
            resource_type='aircraft',
            resource_id=aircraft_id,
            start=start + timedelta(hours=1),
            end=start + timedelta(hours=2),
        )

        assert result['available'] is False
        assert len(result['conflicts']) > 0

    def test_get_available_slots(self, organization_id, location_id, aircraft_id):
        """Test available slots calculation."""
        target_date = timezone.now().date() + timedelta(days=1)

        slots = self.service.get_available_slots(
            organization_id=organization_id,
            target_date=target_date,
            duration_minutes=60,
            aircraft_id=aircraft_id,
            location_id=location_id,
            slot_interval=30,
        )

        assert isinstance(slots, list)
        # Should have slots based on operating hours
        for slot in slots:
            assert 'start' in slot
            assert 'end' in slot
            assert slot['available'] is True

    def test_get_resource_schedule(self, organization_id, aircraft_id, create_booking):
        """Test resource schedule retrieval."""
        target_date = timezone.now().date() + timedelta(days=1)

        # Create a booking for the aircraft
        create_booking(
            aircraft_id=aircraft_id,
            scheduled_start=timezone.make_aware(datetime.combine(target_date, time(10, 0))),
            scheduled_end=timezone.make_aware(datetime.combine(target_date, time(12, 0))),
            status=Booking.Status.SCHEDULED,
        )

        schedule = self.service.get_resource_schedule(
            organization_id=organization_id,
            resource_type='aircraft',
            resource_id=aircraft_id,
            target_date=target_date,
        )

        assert schedule['date'] == target_date.isoformat()
        assert len(schedule['bookings']) >= 1


@pytest.mark.django_db
class TestRuleService:
    """Tests for RuleService."""

    def setup_method(self):
        """Set up test dependencies."""
        self.service = RuleService()

    def test_create_rule(self, organization_id):
        """Test rule creation."""
        rule = self.service.create_rule(
            organization_id=organization_id,
            rule_type=BookingRule.RuleType.GENERAL,
            name='Test Rule',
            min_booking_duration=30,
            max_booking_duration=480,
        )

        assert rule.id is not None
        assert rule.name == 'Test Rule'

    def test_validate_booking_duration(self, organization_id, create_rule):
        """Test booking validation against duration rules."""
        # Create rule with duration limits
        create_rule(
            min_booking_duration=60,  # 1 hour minimum
            max_booking_duration=240,  # 4 hours maximum
        )

        start = timezone.now() + timedelta(days=1)

        # Valid duration (2 hours)
        valid_result = self.service.validate_booking(
            organization_id=organization_id,
            scheduled_start=start,
            scheduled_end=start + timedelta(hours=2),
            user_id=uuid.uuid4(),
        )
        assert valid_result['valid'] is True

        # Too short (30 minutes)
        short_result = self.service.validate_booking(
            organization_id=organization_id,
            scheduled_start=start,
            scheduled_end=start + timedelta(minutes=30),
            user_id=uuid.uuid4(),
        )
        assert short_result['valid'] is False
        assert 'min' in str(short_result['errors']).lower()

        # Too long (5 hours)
        long_result = self.service.validate_booking(
            organization_id=organization_id,
            scheduled_start=start,
            scheduled_end=start + timedelta(hours=5),
            user_id=uuid.uuid4(),
        )
        assert long_result['valid'] is False
        assert 'max' in str(long_result['errors']).lower()

    def test_validate_booking_notice(self, organization_id, create_rule):
        """Test booking validation against notice period rules."""
        create_rule(min_notice_hours=24)

        # Booking with sufficient notice
        future_result = self.service.validate_booking(
            organization_id=organization_id,
            scheduled_start=timezone.now() + timedelta(days=2),
            scheduled_end=timezone.now() + timedelta(days=2, hours=1),
            user_id=uuid.uuid4(),
        )
        assert future_result['valid'] is True

        # Booking with insufficient notice
        soon_result = self.service.validate_booking(
            organization_id=organization_id,
            scheduled_start=timezone.now() + timedelta(hours=2),
            scheduled_end=timezone.now() + timedelta(hours=3),
            user_id=uuid.uuid4(),
        )
        assert soon_result['valid'] is False
        assert 'notice' in str(soon_result['errors']).lower()

    def test_calculate_cancellation_fee(self, organization_id, create_rule):
        """Test cancellation fee calculation."""
        create_rule(
            free_cancellation_hours=24,
            late_cancellation_fee_percent=Decimal('50.00'),
            no_show_fee_percent=Decimal('100.00'),
        )

        estimated_cost = Decimal('500.00')

        # Free cancellation (more than 24 hours ahead)
        free_result = self.service.calculate_cancellation_fee(
            organization_id=organization_id,
            hours_until_start=48,
            estimated_cost=estimated_cost,
        )
        assert free_result['is_free'] is True
        assert free_result['fee'] == Decimal('0.00')

        # Late cancellation
        late_result = self.service.calculate_cancellation_fee(
            organization_id=organization_id,
            hours_until_start=12,
            estimated_cost=estimated_cost,
        )
        assert late_result['is_free'] is False
        assert late_result['is_late'] is True
        assert late_result['fee'] == Decimal('250.00')  # 50% of 500

        # No show
        noshow_result = self.service.calculate_cancellation_fee(
            organization_id=organization_id,
            hours_until_start=-1,  # Past start time
            estimated_cost=estimated_cost,
        )
        assert noshow_result['fee'] == Decimal('500.00')  # 100% of 500


@pytest.mark.django_db
class TestWaitlistService:
    """Tests for WaitlistService."""

    def setup_method(self):
        """Set up test dependencies."""
        self.service = WaitlistService()

    def test_add_to_waitlist(self, organization_id, user_id):
        """Test adding to waitlist."""
        entry = self.service.add_to_waitlist(
            organization_id=organization_id,
            user_id=user_id,
            requested_date=timezone.now().date() + timedelta(days=7),
            duration_minutes=120,
            user_name='Test User',
            user_email='test@example.com',
        )

        assert entry.id is not None
        assert entry.status == WaitlistEntry.Status.WAITING

    def test_send_offer(self, organization_id, user_id):
        """Test sending offer to waitlist entry."""
        entry = self.service.add_to_waitlist(
            organization_id=organization_id,
            user_id=user_id,
            requested_date=timezone.now().date() + timedelta(days=7),
        )

        booking_id = uuid.uuid4()

        offered = self.service.send_offer(
            entry_id=entry.id,
            booking_id=booking_id,
            message='Slot available!',
            expires_in_hours=4,
        )

        assert offered.status == WaitlistEntry.Status.OFFERED
        assert offered.offered_booking_id == booking_id

    def test_accept_offer(self, create_waitlist_entry):
        """Test accepting waitlist offer."""
        entry = create_waitlist_entry()
        booking_id = uuid.uuid4()

        # Send offer first
        entry.send_offer(booking_id, 'Available!', 4)
        entry.save()

        accepted = self.service.accept_offer(entry.id)

        assert accepted.status == WaitlistEntry.Status.ACCEPTED

    def test_accept_expired_offer(self, create_waitlist_entry):
        """Test accepting expired offer fails."""
        entry = create_waitlist_entry()

        # Create expired offer
        entry.status = WaitlistEntry.Status.OFFERED
        entry.offered_booking_id = uuid.uuid4()
        entry.offer_expires_at = timezone.now() - timedelta(hours=1)
        entry.save()

        with pytest.raises(WaitlistError):
            self.service.accept_offer(entry.id)

    def test_decline_offer(self, create_waitlist_entry):
        """Test declining waitlist offer."""
        entry = create_waitlist_entry()
        booking_id = uuid.uuid4()

        # Send offer first
        entry.send_offer(booking_id, 'Available!', 4)
        entry.save()

        declined = self.service.decline_offer(entry.id, notes='Time does not work')

        assert declined.status == WaitlistEntry.Status.DECLINED

    def test_cancel_entry(self, create_waitlist_entry):
        """Test cancelling waitlist entry."""
        entry = create_waitlist_entry()

        cancelled = self.service.cancel_entry(entry.id, reason='No longer needed')

        assert cancelled.status == WaitlistEntry.Status.CANCELLED

    def test_list_entries(self, organization_id, user_id):
        """Test listing waitlist entries."""
        # Create multiple entries
        for i in range(5):
            self.service.add_to_waitlist(
                organization_id=organization_id,
                user_id=user_id,
                requested_date=timezone.now().date() + timedelta(days=7 + i),
            )

        entries = self.service.list_entries(
            organization_id=organization_id,
            user_id=user_id,
            active_only=True,
        )

        assert len(entries) == 5

    def test_get_statistics(self, organization_id, user_id):
        """Test waitlist statistics."""
        # Create entries with various statuses
        for _ in range(3):
            self.service.add_to_waitlist(
                organization_id=organization_id,
                user_id=user_id,
                requested_date=timezone.now().date() + timedelta(days=7),
            )

        stats = self.service.get_statistics(organization_id=organization_id)

        assert stats['total'] >= 3
        assert 'waiting' in stats
        assert 'fulfillment_rate' in stats
