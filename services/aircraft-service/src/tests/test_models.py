# services/aircraft-service/src/tests/test_models.py
"""
Tests for Aircraft Service Models.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.core.models import (
    Aircraft, AircraftType, AircraftEngine, AircraftPropeller,
    AircraftSquawk, AircraftDocument, AircraftTimeLog
)


# =============================================================================
# AircraftType Model Tests
# =============================================================================

@pytest.mark.django_db
class TestAircraftTypeModel:
    """Tests for AircraftType model."""

    def test_create_aircraft_type(self, aircraft_type_c172):
        """Test creating an aircraft type."""
        assert aircraft_type_c172.icao_code == 'C172'
        assert aircraft_type_c172.manufacturer == 'Cessna'
        assert aircraft_type_c172.is_active is True

    def test_display_name(self, aircraft_type_c172):
        """Test display name property."""
        assert 'Cessna' in aircraft_type_c172.display_name
        assert '172' in aircraft_type_c172.display_name

    def test_aircraft_type_unique_icao(self, db, aircraft_type_c172):
        """Test unique ICAO code constraint."""
        with pytest.raises(Exception):
            AircraftType.objects.create(
                icao_code='C172',  # Duplicate
                manufacturer='Another',
                model='Model',
            )


# =============================================================================
# Aircraft Model Tests
# =============================================================================

@pytest.mark.django_db
class TestAircraftModel:
    """Tests for Aircraft model."""

    def test_create_aircraft(self, aircraft_c172):
        """Test creating an aircraft."""
        assert aircraft_c172.registration == 'TC-AVI'
        assert aircraft_c172.status == Aircraft.Status.ACTIVE
        assert aircraft_c172.is_airworthy is True

    def test_display_name(self, aircraft_c172):
        """Test display name property."""
        display = aircraft_c172.display_name
        assert 'TC-AVI' in display

    def test_is_available(self, aircraft_c172, aircraft_grounded):
        """Test is_available property."""
        assert aircraft_c172.is_available is True
        assert aircraft_grounded.is_available is False

    def test_is_multi_engine(self, aircraft_c172, aircraft_multi_engine):
        """Test is_multi_engine property."""
        assert aircraft_c172.is_multi_engine is False
        assert aircraft_multi_engine.is_multi_engine is True

    def test_arc_days_remaining(self, aircraft_c172):
        """Test ARC days remaining calculation."""
        days = aircraft_c172.arc_days_remaining
        assert days is not None
        assert days > 0

    def test_insurance_days_remaining(self, aircraft_c172):
        """Test insurance days remaining calculation."""
        days = aircraft_c172.insurance_days_remaining
        assert days is not None
        assert days > 0

    def test_ground_aircraft(self, aircraft_c172, test_user):
        """Test grounding an aircraft."""
        aircraft_c172.ground(
            reason='Test grounding',
            grounded_by=test_user['id']
        )

        assert aircraft_c172.is_grounded is True
        assert aircraft_c172.is_airworthy is False
        assert aircraft_c172.status == Aircraft.Status.GROUNDED
        assert aircraft_c172.grounded_reason == 'Test grounding'

    def test_unground_aircraft(self, aircraft_grounded):
        """Test ungrounding an aircraft."""
        aircraft_grounded.unground()

        assert aircraft_grounded.is_grounded is False
        assert aircraft_grounded.status == Aircraft.Status.ACTIVE

    def test_update_counters(self, aircraft_c172):
        """Test updating aircraft counters."""
        initial_hobbs = aircraft_c172.hobbs_time
        initial_landings = aircraft_c172.total_landings

        aircraft_c172.update_counters(
            hobbs_time=Decimal('1.5'),
            tach_time=Decimal('1.4'),
            landings=2,
            cycles=1
        )

        assert aircraft_c172.hobbs_time == initial_hobbs + Decimal('1.5')
        assert aircraft_c172.total_landings == initial_landings + 2

    def test_soft_delete(self, aircraft_c172, test_user):
        """Test soft delete."""
        aircraft_c172.soft_delete(deleted_by=test_user['id'])

        assert aircraft_c172.deleted_at is not None
        assert aircraft_c172.status == Aircraft.Status.DECOMMISSIONED

    def test_get_billing_rate_hourly(self, aircraft_c172):
        """Test getting billing rate."""
        rate = aircraft_c172.get_billing_rate()
        assert rate == aircraft_c172.hourly_rate


# =============================================================================
# AircraftEngine Model Tests
# =============================================================================

@pytest.mark.django_db
class TestAircraftEngineModel:
    """Tests for AircraftEngine model."""

    def test_create_engine(self, engine_single):
        """Test creating an engine."""
        assert engine_single.manufacturer == 'Lycoming'
        assert engine_single.position == 1
        assert engine_single.is_active is True

    def test_hours_until_tbo(self, engine_single):
        """Test hours until TBO calculation."""
        hours = engine_single.hours_until_tbo
        expected = engine_single.tbo_hours - engine_single.tso
        assert hours == expected

    def test_tbo_percentage(self, engine_single):
        """Test TBO percentage calculation."""
        percentage = engine_single.tbo_percentage
        expected = (engine_single.tso / engine_single.tbo_hours) * 100
        assert percentage == expected

    def test_is_tbo_exceeded(self, engine_single):
        """Test TBO exceeded check."""
        assert engine_single.is_tbo_exceeded is False

        # Manually exceed TBO
        engine_single.tso = engine_single.tbo_hours + Decimal('100')
        assert engine_single.is_tbo_exceeded is True

    def test_add_hours(self, engine_single):
        """Test adding hours to engine."""
        initial_tsn = engine_single.tsn
        initial_tso = engine_single.tso

        engine_single.add_hours(Decimal('2.5'))

        assert engine_single.tsn == initial_tsn + Decimal('2.5')
        assert engine_single.tso == initial_tso + Decimal('2.5')

    def test_record_overhaul(self, engine_single):
        """Test recording an engine overhaul."""
        engine_single.record_overhaul(
            overhaul_date=date.today(),
            overhaul_type='major'
        )

        assert engine_single.tso == Decimal('0')
        assert engine_single.last_overhaul_date == date.today()

    def test_get_status(self, engine_single):
        """Test engine status."""
        status = engine_single.get_status()
        assert 'status' in status
        assert 'hours_until_tbo' in status


# =============================================================================
# AircraftSquawk Model Tests
# =============================================================================

@pytest.mark.django_db
class TestAircraftSquawkModel:
    """Tests for AircraftSquawk model."""

    def test_create_squawk(self, squawk_open):
        """Test creating a squawk."""
        assert squawk_open.title == 'Compass inaccurate'
        assert squawk_open.status == AircraftSquawk.Status.OPEN

    def test_squawk_number_auto_generation(self, squawk_open):
        """Test automatic squawk number generation."""
        assert squawk_open.squawk_number is not None
        assert squawk_open.squawk_number.startswith('SQ-')

    def test_is_open_property(self, squawk_open, squawk_resolved):
        """Test is_open property."""
        assert squawk_open.is_open is True
        assert squawk_resolved.is_open is False

    def test_days_open(self, squawk_open):
        """Test days open calculation."""
        days = squawk_open.days_open
        assert days >= 0

    def test_resolve_squawk(self, squawk_open, test_mechanic):
        """Test resolving a squawk."""
        squawk_open.resolve(
            resolution='Compass compensated and swung',
            resolved_by=test_mechanic['id'],
            resolved_by_name=test_mechanic['name']
        )

        assert squawk_open.status == AircraftSquawk.Status.RESOLVED
        assert squawk_open.resolution is not None
        assert squawk_open.resolved_at is not None

    def test_close_squawk(self, squawk_resolved, test_user):
        """Test closing a squawk."""
        squawk_resolved.close(
            closed_by=test_user['id'],
            closed_by_name=test_user['name']
        )

        assert squawk_resolved.status == AircraftSquawk.Status.CLOSED
        assert squawk_resolved.closed_at is not None

    def test_defer_squawk(self, squawk_open, test_user):
        """Test deferring a squawk."""
        squawk_open.defer(
            mel_category=AircraftSquawk.MELCategory.C,
            mel_reference='MEL 34-10',
            deferred_by=test_user['id']
        )

        assert squawk_open.status == AircraftSquawk.Status.DEFERRED
        assert squawk_open.is_mel_item is True
        assert squawk_open.mel_category == AircraftSquawk.MELCategory.C

    def test_mel_time_limit(self, squawk_deferred):
        """Test MEL time limit calculation."""
        assert squawk_deferred.mel_time_limit_days == 10  # Category C = 10 days

    def test_grounding_squawk_sets_flag(self, test_organization, aircraft_c172, test_user):
        """Test that grounding severity sets is_grounding flag."""
        squawk = AircraftSquawk.objects.create(
            organization_id=test_organization['id'],
            aircraft=aircraft_c172,
            title='Critical issue',
            description='Test',
            category=AircraftSquawk.Category.POWERPLANT,
            severity=AircraftSquawk.Severity.GROUNDING,
            reported_by=test_user['id'],
        )

        assert squawk.is_grounding is True


# =============================================================================
# AircraftDocument Model Tests
# =============================================================================

@pytest.mark.django_db
class TestAircraftDocumentModel:
    """Tests for AircraftDocument model."""

    def test_create_document(self, document_registration):
        """Test creating a document."""
        assert document_registration.document_type == AircraftDocument.DocumentType.REGISTRATION
        assert document_registration.is_current is True

    def test_is_expired(self, document_expired):
        """Test is_expired property."""
        assert document_expired.is_expired is True

    def test_days_until_expiry(self, document_registration):
        """Test days until expiry calculation."""
        days = document_registration.days_until_expiry
        assert days is not None
        assert days > 0

    def test_is_expiring_soon(self, document_insurance, document_registration):
        """Test expiring soon check."""
        # Insurance expires in 90 days with 30 day reminder
        assert document_insurance.is_expiring_soon is False

        # Modify to expire soon
        document_insurance.expiry_date = date.today() + timedelta(days=15)
        document_insurance.save()
        assert document_insurance.is_expiring_soon is True

    def test_needs_reminder(self, document_insurance):
        """Test needs reminder check."""
        document_insurance.expiry_date = date.today() + timedelta(days=15)
        document_insurance.reminder_sent = False
        document_insurance.save()

        assert document_insurance.needs_reminder is True

    def test_file_size_display(self, document_registration):
        """Test file size display formatting."""
        size = document_registration.file_size_display
        assert 'KB' in size or 'MB' in size

    def test_get_expiring_documents(self, db, document_registration, document_insurance):
        """Test get_expiring_documents class method."""
        # Set one to expire soon
        document_insurance.expiry_date = date.today() + timedelta(days=15)
        document_insurance.save()

        expiring = AircraftDocument.get_expiring_documents(days_ahead=30)
        assert expiring.count() >= 1


# =============================================================================
# AircraftTimeLog Model Tests
# =============================================================================

@pytest.mark.django_db
class TestAircraftTimeLogModel:
    """Tests for AircraftTimeLog model."""

    def test_create_time_log(self, time_log_flight):
        """Test creating a time log."""
        assert time_log_flight.source_type == AircraftTimeLog.SourceType.FLIGHT
        assert time_log_flight.hobbs_change == Decimal('2.5')

    def test_create_from_flight(self, aircraft_c172, test_user):
        """Test creating time log from flight."""
        flight_id = uuid.uuid4()

        log = AircraftTimeLog.create_from_flight(
            aircraft=aircraft_c172,
            flight_id=flight_id,
            hobbs_change=Decimal('1.5'),
            landings=2,
            flight_date=date.today(),
            created_by=test_user['id'],
        )

        assert log.source_type == AircraftTimeLog.SourceType.FLIGHT
        assert log.source_id == flight_id
        assert log.hobbs_change == Decimal('1.5')
        assert log.landings_change == 2

    def test_create_adjustment(self, aircraft_c172, test_mechanic):
        """Test creating adjustment log."""
        log = AircraftTimeLog.create_adjustment(
            aircraft=aircraft_c172,
            field='hobbs_time',
            new_value=Decimal('1250.0'),
            reason='Meter correction after replacement',
            created_by=test_mechanic['id'],
            created_by_name=test_mechanic['name'],
        )

        assert log.source_type == AircraftTimeLog.SourceType.ADJUSTMENT
        assert log.adjustment_reason is not None

    def test_get_history(self, aircraft_c172, time_log_flight, time_log_adjustment):
        """Test getting time log history."""
        history = AircraftTimeLog.get_history(aircraft_c172.id, limit=10)
        assert len(history) >= 2

    def test_get_totals_for_period(self, aircraft_c172, time_log_flight):
        """Test getting totals for period."""
        totals = AircraftTimeLog.get_totals_for_period(
            aircraft_id=aircraft_c172.id,
            start_date=date.today() - timedelta(days=30),
            end_date=date.today(),
        )

        assert 'hobbs' in totals
        assert 'landings' in totals
