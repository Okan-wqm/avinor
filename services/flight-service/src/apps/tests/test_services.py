# services/flight-service/src/apps/tests/test_services.py
"""
Service Tests

Tests for flight service business logic layer.
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone


# =============================================================================
# FlightService Tests
# =============================================================================

@pytest.mark.django_db
class TestFlightService:
    """Tests for FlightService."""

    def test_create_flight(self, flight_service, organization_id, user_id, flight_data):
        """Test creating a flight via service."""
        # Remove organization_id and created_by as service adds them
        del flight_data['organization_id']
        del flight_data['created_by']

        flight = flight_service.create_flight(
            organization_id=organization_id,
            created_by=user_id,
            flight_data=flight_data
        )

        assert flight.id is not None
        assert flight.organization_id == organization_id
        assert flight.created_by == user_id

    def test_create_flight_with_approaches(
        self, flight_service, organization_id, user_id, flight_data, approach_data
    ):
        """Test creating a flight with approaches."""
        del flight_data['organization_id']
        del flight_data['created_by']
        del approach_data['organization_id']

        flight = flight_service.create_flight(
            organization_id=organization_id,
            created_by=user_id,
            flight_data=flight_data,
            approaches=[approach_data],
        )

        assert flight.approach_count == 1

    def test_get_flight(self, flight_service, flight):
        """Test getting a flight."""
        retrieved = flight_service.get_flight(
            flight_id=flight.id,
            organization_id=flight.organization_id
        )

        assert retrieved.id == flight.id

    def test_get_flight_not_found(self, flight_service, organization_id):
        """Test getting non-existent flight."""
        from apps.core.services.exceptions import FlightNotFoundError

        with pytest.raises(FlightNotFoundError):
            flight_service.get_flight(
                flight_id=uuid.uuid4(),
                organization_id=organization_id
            )

    def test_get_flight_with_details(self, flight_service, flight, approach):
        """Test getting flight with all details."""
        result = flight_service.get_flight_with_details(
            flight_id=flight.id,
            organization_id=flight.organization_id
        )

        assert result['flight'].id == flight.id
        assert len(result['approaches']) >= 1

    def test_update_flight(self, flight_service, flight, user_id):
        """Test updating a flight."""
        updated = flight_service.update_flight(
            flight_id=flight.id,
            organization_id=flight.organization_id,
            updated_by=user_id,
            flight_data={'remarks': 'Updated remarks'}
        )

        assert updated.remarks == 'Updated remarks'

    def test_update_approved_flight_fails(self, flight_service, approved_flight, user_id):
        """Test that approved flights cannot be updated."""
        from apps.core.services.exceptions import FlightStateError

        with pytest.raises(FlightStateError):
            flight_service.update_flight(
                flight_id=approved_flight.id,
                organization_id=approved_flight.organization_id,
                updated_by=user_id,
                flight_data={'remarks': 'Should fail'}
            )

    def test_submit_flight(self, flight_service, flight, user_id):
        """Test submitting a flight."""
        from apps.core.models import Flight

        # Ensure required fields
        flight.block_off = timezone.now() - timedelta(hours=2)
        flight.block_on = timezone.now()
        flight.save()

        submitted = flight_service.submit_flight(
            flight_id=flight.id,
            organization_id=flight.organization_id,
            submitted_by=user_id
        )

        assert submitted.flight_status == Flight.Status.SUBMITTED

    def test_approve_flight(self, flight_service, flight, user_id):
        """Test approving a flight."""
        from apps.core.models import Flight

        flight.flight_status = Flight.Status.SUBMITTED
        flight.save()

        approved = flight_service.approve_flight(
            flight_id=flight.id,
            organization_id=flight.organization_id,
            approved_by=user_id
        )

        assert approved.flight_status == Flight.Status.APPROVED

    def test_reject_flight(self, flight_service, flight, user_id):
        """Test rejecting a flight."""
        from apps.core.models import Flight

        flight.flight_status = Flight.Status.SUBMITTED
        flight.save()

        rejected = flight_service.reject_flight(
            flight_id=flight.id,
            organization_id=flight.organization_id,
            rejected_by=user_id,
            reason='Test rejection'
        )

        assert rejected.flight_status == Flight.Status.REJECTED
        assert rejected.rejection_reason == 'Test rejection'

    def test_cancel_flight(self, flight_service, flight, user_id):
        """Test cancelling a flight."""
        from apps.core.models import Flight

        cancelled = flight_service.cancel_flight(
            flight_id=flight.id,
            organization_id=flight.organization_id,
            cancelled_by=user_id,
            reason='Test cancellation'
        )

        assert cancelled.flight_status == Flight.Status.CANCELLED

    def test_list_flights(self, flight_service, create_multiple_flights, organization_id):
        """Test listing flights with pagination."""
        create_multiple_flights(count=10)

        result = flight_service.list_flights(
            organization_id=organization_id,
            page=1,
            page_size=5
        )

        assert len(result['flights']) == 5
        assert result['total'] == 10
        assert result['total_pages'] == 2

    def test_list_flights_with_filters(
        self, flight_service, create_multiple_flights, organization_id
    ):
        """Test listing flights with filters."""
        flights = create_multiple_flights(count=5)

        # Filter by aircraft
        result = flight_service.list_flights(
            organization_id=organization_id,
            filters={'aircraft_id': flights[0].aircraft_id}
        )

        assert len(result['flights']) > 0

    def test_sign_as_pic(self, flight_service, flight, pilot_id):
        """Test PIC signature."""
        signature_data = {'type': 'svg', 'data': 'test'}

        signed = flight_service.sign_as_pic(
            flight_id=flight.id,
            organization_id=flight.organization_id,
            signer_id=flight.pic_id,
            signature_data=signature_data
        )

        assert signed.pic_signed_at is not None

    def test_add_approach(self, flight_service, flight, approach_data):
        """Test adding an approach."""
        del approach_data['organization_id']

        approach = flight_service.add_approach(
            flight_id=flight.id,
            organization_id=flight.organization_id,
            approach_data=approach_data
        )

        assert approach.flight_id == flight.id

    def test_add_hold(self, flight_service, flight, hold_data):
        """Test adding a hold."""
        del hold_data['organization_id']

        hold = flight_service.add_hold(
            flight_id=flight.id,
            organization_id=flight.organization_id,
            hold_data=hold_data
        )

        assert hold.flight_id == flight.id


# =============================================================================
# LogbookService Tests
# =============================================================================

@pytest.mark.django_db
class TestLogbookService:
    """Tests for LogbookService."""

    def test_get_or_create_summary(self, logbook_service, organization_id, pilot_id):
        """Test getting or creating logbook summary."""
        summary = logbook_service.get_or_create_summary(
            organization_id=organization_id,
            user_id=pilot_id
        )

        assert summary.user_id == pilot_id

        # Get again should return same
        summary2 = logbook_service.get_or_create_summary(
            organization_id=organization_id,
            user_id=pilot_id
        )

        assert summary.id == summary2.id

    def test_get_logbook_entries(
        self, logbook_service, organization_id, pilot_id,
        approved_flight, flight_crew_log
    ):
        """Test getting logbook entries."""
        result = logbook_service.get_logbook_entries(
            organization_id=organization_id,
            user_id=pilot_id
        )

        assert 'entries' in result
        assert 'total' in result

    def test_update_logbook_remarks(
        self, logbook_service, organization_id, pilot_id, flight_crew_log
    ):
        """Test updating logbook remarks."""
        updated = logbook_service.update_logbook_remarks(
            organization_id=organization_id,
            user_id=pilot_id,
            flight_id=flight_crew_log.flight_id,
            remarks='New remarks'
        )

        assert updated.remarks == 'New remarks'

    def test_sign_logbook_entry(
        self, logbook_service, organization_id, pilot_id, flight_crew_log
    ):
        """Test signing a logbook entry."""
        signature_data = {'type': 'svg', 'data': 'test'}

        signed = logbook_service.sign_logbook_entry(
            organization_id=organization_id,
            user_id=pilot_id,
            flight_id=flight_crew_log.flight_id,
            signature_data=signature_data
        )

        assert signed.is_signed is True

    def test_export_logbook(
        self, logbook_service, organization_id, pilot_id,
        approved_flight, flight_crew_log
    ):
        """Test exporting logbook."""
        export = logbook_service.export_logbook(
            organization_id=organization_id,
            user_id=pilot_id,
            format='json'
        )

        assert 'pilot_id' in export
        assert 'summary' in export
        assert 'entries' in export


# =============================================================================
# CurrencyService Tests
# =============================================================================

@pytest.mark.django_db
class TestCurrencyService:
    """Tests for CurrencyService."""

    def test_check_all_currency(self, currency_service, organization_id, pilot_id):
        """Test checking all currency requirements."""
        results = currency_service.check_all_currency(
            organization_id=organization_id,
            user_id=pilot_id
        )

        assert len(results) > 0
        assert all(hasattr(r, 'currency_type') for r in results)

    def test_get_currency_summary(self, currency_service, organization_id, pilot_id):
        """Test getting currency summary."""
        summary = currency_service.get_currency_summary(
            organization_id=organization_id,
            user_id=pilot_id
        )

        assert 'user_id' in summary
        assert 'overall_status' in summary
        assert 'currencies' in summary

    def test_validate_for_flight(self, currency_service, organization_id, pilot_id):
        """Test validating currency for a flight."""
        validation = currency_service.validate_for_flight(
            organization_id=organization_id,
            user_id=pilot_id,
            flight_type='training',
            flight_rules='VFR',
            has_passengers=False,
            is_night=False
        )

        assert 'is_valid' in validation
        assert 'warnings' in validation
        assert 'errors' in validation

    def test_validate_for_flight_with_passengers(
        self, currency_service, organization_id, pilot_id,
        create_approved_flights
    ):
        """Test validating currency for passenger flight."""
        # Create some recent flights with landings
        create_approved_flights(
            count=3,
            full_stop_day=1,
        )

        validation = currency_service.validate_for_flight(
            organization_id=organization_id,
            user_id=pilot_id,
            flight_type='private',
            flight_rules='VFR',
            has_passengers=True,
            is_night=False
        )

        # Should have some result
        assert 'is_valid' in validation


# =============================================================================
# StatisticsService Tests
# =============================================================================

@pytest.mark.django_db
class TestStatisticsService:
    """Tests for StatisticsService."""

    def test_get_pilot_statistics(
        self, statistics_service, organization_id, pilot_id,
        create_approved_flights
    ):
        """Test getting pilot statistics."""
        create_approved_flights(count=5)

        stats = statistics_service.get_pilot_statistics(
            organization_id=organization_id,
            user_id=pilot_id
        )

        assert 'user_id' in stats
        assert 'summary' in stats
        assert stats['summary']['total_flights'] >= 5

    def test_get_aircraft_statistics(
        self, statistics_service, organization_id, aircraft_id,
        create_approved_flights
    ):
        """Test getting aircraft statistics."""
        create_approved_flights(count=3)

        stats = statistics_service.get_aircraft_statistics(
            organization_id=organization_id,
            aircraft_id=aircraft_id
        )

        assert 'aircraft_id' in stats
        assert 'summary' in stats

    def test_get_organization_statistics(
        self, statistics_service, organization_id, create_approved_flights
    ):
        """Test getting organization statistics."""
        create_approved_flights(count=5)

        stats = statistics_service.get_organization_statistics(
            organization_id=organization_id
        )

        assert 'organization_id' in stats
        assert 'summary' in stats

    def test_get_dashboard_statistics(
        self, statistics_service, organization_id, pilot_id,
        create_approved_flights
    ):
        """Test getting dashboard statistics."""
        create_approved_flights(count=3)

        stats = statistics_service.get_dashboard_statistics(
            organization_id=organization_id,
            user_id=pilot_id
        )

        assert 'last_30_days' in stats
        assert 'pending' in stats
        assert 'recent_flights' in stats

    def test_get_period_comparison(
        self, statistics_service, organization_id,
        create_approved_flights
    ):
        """Test getting period comparison."""
        create_approved_flights(count=5)

        today = date.today()
        comparison = statistics_service.get_period_comparison(
            organization_id=organization_id,
            period_1_start=today - timedelta(days=30),
            period_1_end=today - timedelta(days=15),
            period_2_start=today - timedelta(days=14),
            period_2_end=today
        )

        assert 'period_1' in comparison
        assert 'period_2' in comparison
        assert 'changes' in comparison
