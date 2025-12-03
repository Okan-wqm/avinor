# services/booking-service/src/tests/unit/test_models.py
"""
Unit Tests for Booking Models

Tests for model methods, properties, and business logic.
"""

import uuid
from datetime import datetime, date, time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from django.db import IntegrityError

from apps.core.models import Booking, RecurringPattern, Availability, BookingRule, WaitlistEntry


@pytest.mark.django_db
class TestBookingModel:
    """Tests for Booking model."""

    def test_create_booking(self, organization_id, location_id, aircraft_id, student_id):
        """Test booking creation with required fields."""
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=2)

        booking = Booking.objects.create(
            organization_id=organization_id,
            location_id=location_id,
            booking_type=Booking.BookingType.RENTAL,
            scheduled_start=start,
            scheduled_end=end,
            aircraft_id=aircraft_id,
            student_id=student_id,
        )

        assert booking.id is not None
        assert booking.booking_number is not None
        assert booking.status == Booking.Status.DRAFT
        assert booking.scheduled_duration == 120  # 2 hours in minutes

    def test_booking_number_generation(self, organization_id, location_id):
        """Test unique booking number generation."""
        start = timezone.now() + timedelta(days=1)

        booking1 = Booking.objects.create(
            organization_id=organization_id,
            location_id=location_id,
            booking_type=Booking.BookingType.TRAINING,
            scheduled_start=start,
            scheduled_end=start + timedelta(hours=1),
        )

        booking2 = Booking.objects.create(
            organization_id=organization_id,
            location_id=location_id,
            booking_type=Booking.BookingType.TRAINING,
            scheduled_start=start + timedelta(hours=2),
            scheduled_end=start + timedelta(hours=3),
        )

        assert booking1.booking_number != booking2.booking_number
        assert booking1.booking_number.startswith('BK')

    def test_block_time_calculation(self, organization_id, location_id):
        """Test block time calculation with pre/post flight."""
        start = timezone.now() + timedelta(days=1)
        start = start.replace(hour=10, minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=2)

        booking = Booking.objects.create(
            organization_id=organization_id,
            location_id=location_id,
            booking_type=Booking.BookingType.TRAINING,
            scheduled_start=start,
            scheduled_end=end,
            preflight_minutes=15,
            postflight_minutes=15,
        )

        # Block start should be 15 minutes before scheduled start
        assert booking.block_start == start - timedelta(minutes=15)
        # Block end should be 15 minutes after scheduled end
        assert booking.block_end == end + timedelta(minutes=15)

    def test_hours_until_start(self, organization_id, location_id):
        """Test hours until start calculation."""
        # Future booking
        start = timezone.now() + timedelta(hours=5)
        booking = Booking.objects.create(
            organization_id=organization_id,
            location_id=location_id,
            booking_type=Booking.BookingType.RENTAL,
            scheduled_start=start,
            scheduled_end=start + timedelta(hours=1),
        )

        hours_until = booking.hours_until_start
        assert 4.9 < hours_until < 5.1

    def test_can_cancel_property(self, organization_id, location_id):
        """Test can_cancel property for different statuses."""
        start = timezone.now() + timedelta(days=1)

        booking = Booking.objects.create(
            organization_id=organization_id,
            location_id=location_id,
            booking_type=Booking.BookingType.TRAINING,
            scheduled_start=start,
            scheduled_end=start + timedelta(hours=1),
            status=Booking.Status.SCHEDULED,
        )

        assert booking.can_cancel is True

        # Completed bookings cannot be cancelled
        booking.status = Booking.Status.COMPLETED
        booking.save()
        assert booking.can_cancel is False

        # Already cancelled bookings cannot be cancelled
        booking.status = Booking.Status.CANCELLED
        booking.save()
        assert booking.can_cancel is False

    def test_status_transitions(self, organization_id, location_id):
        """Test booking status workflow transitions."""
        start = timezone.now() + timedelta(hours=1)
        booking = Booking.objects.create(
            organization_id=organization_id,
            location_id=location_id,
            booking_type=Booking.BookingType.TRAINING,
            scheduled_start=start,
            scheduled_end=start + timedelta(hours=1),
            status=Booking.Status.SCHEDULED,
        )

        # Confirm
        booking.confirm()
        assert booking.status == Booking.Status.CONFIRMED

        # Check in
        booking.check_in()
        assert booking.status == Booking.Status.CHECKED_IN

    def test_cancel_booking(self, organization_id, location_id, user_id):
        """Test booking cancellation."""
        start = timezone.now() + timedelta(days=1)
        booking = Booking.objects.create(
            organization_id=organization_id,
            location_id=location_id,
            booking_type=Booking.BookingType.TRAINING,
            scheduled_start=start,
            scheduled_end=start + timedelta(hours=1),
            status=Booking.Status.SCHEDULED,
        )

        booking.cancel(reason='Test cancellation', cancelled_by=user_id)

        assert booking.status == Booking.Status.CANCELLED
        assert booking.cancellation_reason == 'Test cancellation'
        assert booking.cancelled_by == user_id
        assert booking.cancelled_at is not None

    def test_conflict_detection(self, organization_id, location_id, aircraft_id):
        """Test booking conflict detection."""
        start = timezone.now() + timedelta(days=1)
        start = start.replace(hour=10, minute=0, second=0, microsecond=0)

        # Create first booking
        booking1 = Booking.objects.create(
            organization_id=organization_id,
            location_id=location_id,
            booking_type=Booking.BookingType.RENTAL,
            aircraft_id=aircraft_id,
            scheduled_start=start,
            scheduled_end=start + timedelta(hours=2),
            status=Booking.Status.SCHEDULED,
        )

        # Check for conflicts in overlapping time
        conflicts = Booking.get_conflicts(
            organization_id=organization_id,
            start=start + timedelta(hours=1),
            end=start + timedelta(hours=3),
            aircraft_id=aircraft_id,
        )

        assert len(conflicts) == 1
        assert conflicts[0].id == booking1.id

        # Check for no conflicts outside the time range
        no_conflicts = Booking.get_conflicts(
            organization_id=organization_id,
            start=start + timedelta(hours=3),
            end=start + timedelta(hours=4),
            aircraft_id=aircraft_id,
        )

        assert len(no_conflicts) == 0


@pytest.mark.django_db
class TestRecurringPatternModel:
    """Tests for RecurringPattern model."""

    def test_create_recurring_pattern(self, organization_id, location_id):
        """Test recurring pattern creation."""
        start_date = timezone.now().date() + timedelta(days=7)

        pattern = RecurringPattern.objects.create(
            organization_id=organization_id,
            location_id=location_id,
            name='Weekly Training',
            frequency=RecurringPattern.Frequency.WEEKLY,
            interval=1,
            days_of_week=[1, 3],  # Monday and Wednesday
            start_date=start_date,
            start_time=time(10, 0),
            end_time=time(12, 0),
            booking_type='training',
        )

        assert pattern.id is not None
        assert pattern.status == RecurringPattern.Status.ACTIVE
        assert pattern.is_active is True

    def test_get_next_occurrences_weekly(self, organization_id, location_id):
        """Test getting next occurrences for weekly pattern."""
        # Start on next Monday
        today = timezone.now().date()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        start_date = today + timedelta(days=days_until_monday)

        pattern = RecurringPattern.objects.create(
            organization_id=organization_id,
            location_id=location_id,
            name='Weekly Monday',
            frequency=RecurringPattern.Frequency.WEEKLY,
            interval=1,
            days_of_week=[1],  # Monday
            start_date=start_date,
            start_time=time(10, 0),
            end_time=time(12, 0),
        )

        occurrences = pattern.get_next_occurrences(4)

        assert len(occurrences) == 4
        # All occurrences should be on Mondays
        for occ in occurrences:
            assert occ.weekday() == 0  # Monday is 0

    def test_exception_dates(self, organization_id, location_id):
        """Test exception dates in recurring patterns."""
        start_date = timezone.now().date() + timedelta(days=7)
        exception_date = start_date + timedelta(days=7)

        pattern = RecurringPattern.objects.create(
            organization_id=organization_id,
            location_id=location_id,
            name='Daily with Exception',
            frequency=RecurringPattern.Frequency.DAILY,
            interval=1,
            start_date=start_date,
            start_time=time(10, 0),
            end_time=time(12, 0),
            exception_dates=[exception_date],
        )

        occurrences = pattern.get_next_occurrences(10)

        # Exception date should not be in occurrences
        assert exception_date not in occurrences

    def test_max_occurrences(self, organization_id, location_id):
        """Test max occurrences limit."""
        start_date = timezone.now().date() + timedelta(days=1)

        pattern = RecurringPattern.objects.create(
            organization_id=organization_id,
            location_id=location_id,
            name='Limited Pattern',
            frequency=RecurringPattern.Frequency.DAILY,
            interval=1,
            start_date=start_date,
            start_time=time(10, 0),
            end_time=time(12, 0),
            max_occurrences=5,
        )

        occurrences = pattern.get_next_occurrences(10)

        assert len(occurrences) <= 5


@pytest.mark.django_db
class TestAvailabilityModel:
    """Tests for Availability model."""

    def test_create_availability(self, organization_id, aircraft_id):
        """Test availability creation."""
        start = timezone.now()
        end = start + timedelta(days=1)

        availability = Availability.objects.create(
            organization_id=organization_id,
            resource_type='aircraft',
            resource_id=aircraft_id,
            availability_type=Availability.AvailabilityType.UNAVAILABLE,
            start_datetime=start,
            end_datetime=end,
            reason='Maintenance',
        )

        assert availability.id is not None
        assert availability.reason == 'Maintenance'

    def test_is_resource_available(self, organization_id, aircraft_id):
        """Test resource availability check."""
        start = timezone.now()
        end = start + timedelta(days=1)

        # Create unavailability block
        Availability.objects.create(
            organization_id=organization_id,
            resource_type='aircraft',
            resource_id=aircraft_id,
            availability_type=Availability.AvailabilityType.UNAVAILABLE,
            start_datetime=start,
            end_datetime=end,
        )

        # Check availability during blocked time
        is_available = Availability.is_resource_available(
            organization_id=organization_id,
            resource_type='aircraft',
            resource_id=aircraft_id,
            start=start + timedelta(hours=6),
            end=start + timedelta(hours=8),
        )

        assert is_available is False

        # Check availability outside blocked time
        is_available_outside = Availability.is_resource_available(
            organization_id=organization_id,
            resource_type='aircraft',
            resource_id=aircraft_id,
            start=start + timedelta(days=2),
            end=start + timedelta(days=2, hours=2),
        )

        assert is_available_outside is True


@pytest.mark.django_db
class TestBookingRuleModel:
    """Tests for BookingRule model."""

    def test_create_rule(self, organization_id):
        """Test booking rule creation."""
        rule = BookingRule.objects.create(
            organization_id=organization_id,
            rule_type=BookingRule.RuleType.GENERAL,
            name='Test Rule',
            priority=10,
            min_booking_duration=30,
            max_booking_duration=480,
            min_notice_hours=2,
        )

        assert rule.id is not None
        assert rule.is_active is True

    def test_rule_effectiveness(self, organization_id):
        """Test rule effective date checking."""
        today = timezone.now().date()

        # Currently effective rule
        active_rule = BookingRule.objects.create(
            organization_id=organization_id,
            rule_type=BookingRule.RuleType.GENERAL,
            name='Active Rule',
            priority=10,
            effective_from=today - timedelta(days=7),
            effective_to=today + timedelta(days=7),
        )

        assert active_rule.is_effective is True

        # Expired rule
        expired_rule = BookingRule.objects.create(
            organization_id=organization_id,
            rule_type=BookingRule.RuleType.GENERAL,
            name='Expired Rule',
            priority=10,
            effective_from=today - timedelta(days=30),
            effective_to=today - timedelta(days=1),
        )

        assert expired_rule.is_effective is False

        # Future rule
        future_rule = BookingRule.objects.create(
            organization_id=organization_id,
            rule_type=BookingRule.RuleType.GENERAL,
            name='Future Rule',
            priority=10,
            effective_from=today + timedelta(days=7),
        )

        assert future_rule.is_effective is False

    def test_merged_rules(self, organization_id, aircraft_id):
        """Test rule merging with priorities."""
        # Create organization-level rule
        org_rule = BookingRule.objects.create(
            organization_id=organization_id,
            rule_type=BookingRule.RuleType.GENERAL,
            name='Org Rule',
            priority=5,
            min_booking_duration=30,
            max_booking_duration=480,
            free_cancellation_hours=24,
        )

        # Create aircraft-specific rule with higher priority
        aircraft_rule = BookingRule.objects.create(
            organization_id=organization_id,
            rule_type=BookingRule.RuleType.AIRCRAFT,
            target_id=aircraft_id,
            name='Aircraft Rule',
            priority=10,
            max_booking_duration=240,  # Override
            free_cancellation_hours=48,  # Override
        )

        merged = BookingRule.get_merged_rules(
            organization_id=organization_id,
            aircraft_id=aircraft_id,
        )

        # Higher priority aircraft rule should override
        assert merged['max_booking_duration'] == 240
        assert merged['free_cancellation_hours'] == 48
        # Lower priority org rule should apply where not overridden
        assert merged['min_booking_duration'] == 30


@pytest.mark.django_db
class TestWaitlistEntryModel:
    """Tests for WaitlistEntry model."""

    def test_create_waitlist_entry(self, organization_id, user_id):
        """Test waitlist entry creation."""
        requested_date = timezone.now().date() + timedelta(days=7)

        entry = WaitlistEntry.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            requested_date=requested_date,
            preferred_start_time=time(10, 0),
            preferred_end_time=time(12, 0),
            duration_minutes=120,
        )

        assert entry.id is not None
        assert entry.status == WaitlistEntry.Status.WAITING

    def test_send_offer(self, organization_id, user_id):
        """Test sending offer to waitlist entry."""
        entry = WaitlistEntry.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            requested_date=timezone.now().date() + timedelta(days=7),
        )

        booking_id = uuid.uuid4()
        entry.send_offer(booking_id, 'Available slot', expires_in_hours=4)

        assert entry.status == WaitlistEntry.Status.OFFERED
        assert entry.offered_booking_id == booking_id
        assert entry.offer_expires_at is not None
        assert entry.offer_message == 'Available slot'

    def test_accept_offer(self, organization_id, user_id):
        """Test accepting waitlist offer."""
        entry = WaitlistEntry.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            requested_date=timezone.now().date() + timedelta(days=7),
            status=WaitlistEntry.Status.OFFERED,
            offered_booking_id=uuid.uuid4(),
            offer_expires_at=timezone.now() + timedelta(hours=4),
        )

        entry.accept_offer('Thanks!')

        assert entry.status == WaitlistEntry.Status.ACCEPTED
        assert entry.accepted_booking_id == entry.offered_booking_id

    def test_decline_offer(self, organization_id, user_id):
        """Test declining waitlist offer."""
        entry = WaitlistEntry.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            requested_date=timezone.now().date() + timedelta(days=7),
            status=WaitlistEntry.Status.OFFERED,
            offered_booking_id=uuid.uuid4(),
            offer_expires_at=timezone.now() + timedelta(hours=4),
        )

        entry.decline_offer('Time does not work')

        assert entry.status == WaitlistEntry.Status.DECLINED

    def test_offer_expired_property(self, organization_id, user_id):
        """Test offer expired check."""
        # Non-expired offer
        active_entry = WaitlistEntry.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            requested_date=timezone.now().date() + timedelta(days=7),
            status=WaitlistEntry.Status.OFFERED,
            offered_booking_id=uuid.uuid4(),
            offer_expires_at=timezone.now() + timedelta(hours=4),
        )

        assert active_entry.offer_expired is False

        # Expired offer
        expired_entry = WaitlistEntry.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            requested_date=timezone.now().date() + timedelta(days=7),
            status=WaitlistEntry.Status.OFFERED,
            offered_booking_id=uuid.uuid4(),
            offer_expires_at=timezone.now() - timedelta(hours=1),
        )

        assert expired_entry.offer_expired is True

    def test_matches_slot(self, organization_id, user_id, aircraft_id, instructor_id):
        """Test slot matching logic."""
        entry = WaitlistEntry.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            requested_date=timezone.now().date() + timedelta(days=7),
            preferred_start_time=time(10, 0),
            preferred_end_time=time(12, 0),
            aircraft_id=aircraft_id,
            instructor_id=instructor_id,
            any_aircraft=False,
            any_instructor=False,
        )

        slot_date = timezone.now().date() + timedelta(days=7)
        slot_start = timezone.make_aware(datetime.combine(slot_date, time(10, 30)))
        slot_end = timezone.make_aware(datetime.combine(slot_date, time(11, 30)))

        # Should match with correct aircraft and instructor
        assert entry.matches_slot(slot_start, slot_end, aircraft_id, instructor_id) is True

        # Should not match with different aircraft
        different_aircraft = uuid.uuid4()
        assert entry.matches_slot(slot_start, slot_end, different_aircraft, instructor_id) is False
