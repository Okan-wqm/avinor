# services/flight-service/src/apps/tests/test_models.py
"""
Model Tests

Tests for flight service database models.
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone


# =============================================================================
# Flight Model Tests
# =============================================================================

@pytest.mark.django_db
class TestFlightModel:
    """Tests for Flight model."""

    def test_create_flight(self, flight_data):
        """Test creating a basic flight."""
        from apps.core.models import Flight

        flight = Flight.objects.create(**flight_data)

        assert flight.id is not None
        assert flight.flight_date == flight_data['flight_date']
        assert flight.aircraft_registration == 'LN-ABC'
        assert flight.departure_airport == 'ENGM'
        assert flight.flight_status == Flight.Status.DRAFT

    def test_flight_calculate_times(self, flight):
        """Test flight time calculations."""
        flight.calculate_times()

        assert flight.flight_time is not None
        assert flight.block_time is not None
        assert flight.flight_time > Decimal('0')

    def test_flight_total_landings(self, flight):
        """Test total landings property."""
        flight.landings_day = 3
        flight.landings_night = 2

        assert flight.total_landings == 5

    def test_flight_total_full_stops(self, flight):
        """Test total full stops property."""
        flight.full_stop_day = 2
        flight.full_stop_night = 1

        assert flight.total_full_stops == 3

    def test_flight_is_training_flight(self, training_flight):
        """Test is_training_flight property."""
        assert training_flight.is_training_flight is True

    def test_flight_submit_workflow(self, flight, user_id):
        """Test flight submission workflow."""
        from apps.core.models import Flight

        # Ensure required fields
        flight.block_off = timezone.now() - timedelta(hours=2)
        flight.block_on = timezone.now()
        flight.save()

        flight.submit(user_id)

        assert flight.flight_status == Flight.Status.SUBMITTED
        assert flight.submitted_at is not None
        assert flight.submitted_by == user_id

    def test_flight_approve_workflow(self, flight, user_id):
        """Test flight approval workflow."""
        from apps.core.models import Flight

        # Submit first
        flight.block_off = timezone.now() - timedelta(hours=2)
        flight.block_on = timezone.now()
        flight.flight_status = Flight.Status.SUBMITTED
        flight.save()

        flight.approve(user_id)

        assert flight.flight_status == Flight.Status.APPROVED
        assert flight.approved_at is not None
        assert flight.approved_by == user_id

    def test_flight_reject_workflow(self, flight, user_id):
        """Test flight rejection workflow."""
        from apps.core.models import Flight

        flight.flight_status = Flight.Status.SUBMITTED
        flight.save()

        flight.reject(user_id, "Test rejection reason")

        assert flight.flight_status == Flight.Status.REJECTED
        assert flight.rejected_at is not None
        assert flight.rejected_by == user_id
        assert flight.rejection_reason == "Test rejection reason"

    def test_flight_display_route(self, flight):
        """Test display_route property."""
        flight.via_airports = ['ENTO', 'ENBO']

        route = flight.display_route
        assert 'ENGM' in route
        assert 'ENTO' in route
        assert 'ENBO' in route

    def test_flight_add_squawk(self, flight):
        """Test adding squawk to flight."""
        squawk_id = uuid.uuid4()

        flight.add_squawk(squawk_id)

        assert squawk_id in flight.squawk_ids


# =============================================================================
# Approach Model Tests
# =============================================================================

@pytest.mark.django_db
class TestApproachModel:
    """Tests for Approach model."""

    def test_create_approach(self, flight, approach_data):
        """Test creating an approach."""
        from apps.core.models import Approach

        approach_data['flight_id'] = flight.id
        approach = Approach.objects.create(**approach_data)

        assert approach.id is not None
        assert approach.approach_type == 'ILS'
        assert approach.airport_icao == 'ENGM'
        assert approach.runway == '01L'

    def test_approach_display_name(self, approach):
        """Test approach display_name property."""
        display = approach.display_name

        assert 'ILS' in display
        assert '01L' in display
        assert 'ENGM' in display

    def test_approach_counts_for_currency(self, approach):
        """Test counts_for_currency property."""
        # ILS counts for currency
        assert approach.counts_for_currency is True

        # Visual doesn't count
        approach.approach_type = 'VISUAL'
        assert approach.counts_for_currency is False

    def test_approach_statistics(self, db, organization_id, flight, approach):
        """Test approach statistics classmethod."""
        from apps.core.models import Approach, Flight

        # Approve the flight first
        flight.flight_status = Flight.Status.APPROVED
        flight.save()

        stats = Approach.get_approach_statistics(
            organization_id=organization_id
        )

        assert stats['total_approaches'] >= 1


# =============================================================================
# Hold Model Tests
# =============================================================================

@pytest.mark.django_db
class TestHoldModel:
    """Tests for Hold model."""

    def test_create_hold(self, flight, hold_data):
        """Test creating a hold."""
        from apps.core.models import Hold

        hold_data['flight_id'] = flight.id
        hold = Hold.objects.create(**hold_data)

        assert hold.id is not None
        assert hold.fix_name == 'NETRO'
        assert hold.turns == 2

    def test_hold_str(self, hold):
        """Test hold __str__ method."""
        assert 'NETRO' in str(hold)


# =============================================================================
# FuelRecord Model Tests
# =============================================================================

@pytest.mark.django_db
class TestFuelRecordModel:
    """Tests for FuelRecord model."""

    def test_create_fuel_record(self, flight, fuel_record_data):
        """Test creating a fuel record."""
        from apps.core.models import FuelRecord

        fuel_record_data['flight_id'] = flight.id
        record = FuelRecord.objects.create(**fuel_record_data)

        assert record.id is not None
        assert record.quantity_liters == Decimal('150.0')
        assert record.record_type == 'uplift'

    def test_fuel_record_auto_calculations(self, fuel_record):
        """Test automatic calculations on save."""
        # Gallons should be calculated
        assert fuel_record.quantity_gallons is not None
        assert fuel_record.quantity_gallons > Decimal('0')

        # Total cost should be calculated
        assert fuel_record.total_cost is not None
        assert fuel_record.total_cost > Decimal('0')

    def test_fuel_record_total_tank_reading(self, flight, fuel_record_data):
        """Test total_tank_reading property."""
        from apps.core.models import FuelRecord

        fuel_record_data['flight_id'] = flight.id
        fuel_record_data['left_tank_liters'] = Decimal('50.0')
        fuel_record_data['right_tank_liters'] = Decimal('50.0')
        fuel_record_data['aux_tank_liters'] = Decimal('25.0')

        record = FuelRecord.objects.create(**fuel_record_data)

        assert record.total_tank_reading == Decimal('125.0')


# =============================================================================
# FlightCrewLog Model Tests
# =============================================================================

@pytest.mark.django_db
class TestFlightCrewLogModel:
    """Tests for FlightCrewLog model."""

    def test_create_crew_log(self, approved_flight, pilot_id):
        """Test creating a crew log entry."""
        from apps.core.models import FlightCrewLog

        log = FlightCrewLog.objects.create(
            flight_id=approved_flight.id,
            organization_id=approved_flight.organization_id,
            user_id=pilot_id,
            role='pic',
            flight_time=Decimal('1.5'),
            time_pic=Decimal('1.5'),
            landings_day=2,
        )

        assert log.id is not None
        assert log.role == 'pic'
        assert log.flight_time == Decimal('1.5')

    def test_crew_log_total_landings(self, flight_crew_log):
        """Test total_landings property."""
        flight_crew_log.landings_day = 3
        flight_crew_log.landings_night = 2

        assert flight_crew_log.total_landings == 5

    def test_crew_log_total_instrument_time(self, flight_crew_log):
        """Test total_instrument_time property."""
        flight_crew_log.time_actual_instrument = Decimal('0.5')
        flight_crew_log.time_simulated_instrument = Decimal('0.3')

        assert flight_crew_log.total_instrument_time == Decimal('0.8')

    def test_crew_log_sign(self, flight_crew_log):
        """Test signing a crew log entry."""
        signature_data = {'type': 'svg', 'data': 'test_signature'}

        flight_crew_log.sign(signature_data)

        assert flight_crew_log.is_signed is True
        assert flight_crew_log.signed_at is not None
        assert flight_crew_log.signature is not None

    def test_crew_log_to_logbook_entry(self, flight_crew_log, approved_flight):
        """Test to_logbook_entry method."""
        flight_data = {
            'flight_date': approved_flight.flight_date.isoformat(),
            'aircraft_registration': approved_flight.aircraft_registration,
            'aircraft_type': approved_flight.aircraft_type,
            'departure_airport': approved_flight.departure_airport,
            'arrival_airport': approved_flight.arrival_airport,
            'route': approved_flight.route,
        }

        entry = flight_crew_log.to_logbook_entry(flight_data)

        assert 'flight_id' in entry
        assert 'date' in entry
        assert 'aircraft' in entry
        assert 'role' in entry

    def test_crew_log_create_from_flight(self, approved_flight, pilot_id):
        """Test create_from_flight classmethod."""
        from apps.core.models import FlightCrewLog

        log = FlightCrewLog.create_from_flight(
            flight=approved_flight,
            user_id=pilot_id,
            role='pic',
            time_pic=Decimal('1.5'),
        )

        assert log.flight_id == approved_flight.id
        assert log.user_id == pilot_id
        assert log.role == 'pic'


# =============================================================================
# PilotLogbookSummary Model Tests
# =============================================================================

@pytest.mark.django_db
class TestPilotLogbookSummaryModel:
    """Tests for PilotLogbookSummary model."""

    def test_create_summary(self, organization_id, pilot_id):
        """Test creating a logbook summary."""
        from apps.core.models import PilotLogbookSummary

        summary = PilotLogbookSummary.objects.create(
            organization_id=organization_id,
            user_id=pilot_id,
            total_time=Decimal('100.0'),
            total_pic=Decimal('80.0'),
            total_flights=50,
        )

        assert summary.id is not None
        assert summary.total_time == Decimal('100.0')

    def test_summary_total_landings(self, pilot_logbook_summary):
        """Test total_landings property."""
        pilot_logbook_summary.total_landings_day = 100
        pilot_logbook_summary.total_landings_night = 30

        assert pilot_logbook_summary.total_landings == 130

    def test_summary_is_day_current(self, pilot_logbook_summary):
        """Test is_day_current property."""
        pilot_logbook_summary.landings_last_90_days = 5

        assert pilot_logbook_summary.is_day_current is True

        pilot_logbook_summary.landings_last_90_days = 2
        assert pilot_logbook_summary.is_day_current is False

    def test_summary_is_night_current(self, pilot_logbook_summary):
        """Test is_night_current property."""
        pilot_logbook_summary.night_landings_last_90_days = 4

        assert pilot_logbook_summary.is_night_current is True

        pilot_logbook_summary.night_landings_last_90_days = 2
        assert pilot_logbook_summary.is_night_current is False

    def test_summary_is_ifr_current(self, pilot_logbook_summary):
        """Test is_ifr_current property."""
        pilot_logbook_summary.ifr_approaches_last_6_months = 8
        pilot_logbook_summary.holds_last_6_months = 1

        assert pilot_logbook_summary.is_ifr_current is True

        pilot_logbook_summary.ifr_approaches_last_6_months = 4
        assert pilot_logbook_summary.is_ifr_current is False

    def test_summary_get_currency_status(self, pilot_logbook_summary):
        """Test get_currency_status method."""
        status = pilot_logbook_summary.get_currency_status()

        assert 'day_vfr' in status
        assert 'night_vfr' in status
        assert 'ifr' in status
