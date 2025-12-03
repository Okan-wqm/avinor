# services/aircraft-service/src/tests/test_services.py
"""
Tests for Aircraft Service Business Logic.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.core.models import Aircraft, AircraftSquawk, AircraftDocument
from apps.core.services import (
    AircraftService,
    SquawkService,
    CounterService,
    DocumentService,
    AircraftNotFoundError,
    AircraftValidationError,
    AircraftConflictError,
    SquawkError,
    DocumentError,
    CounterError,
)


# =============================================================================
# AircraftService Tests
# =============================================================================

@pytest.mark.django_db
class TestAircraftService:
    """Tests for AircraftService."""

    @pytest.fixture
    def service(self):
        return AircraftService()

    def test_create_aircraft(self, service, test_organization, aircraft_type_c172):
        """Test creating an aircraft."""
        aircraft = service.create_aircraft(
            organization_id=test_organization['id'],
            registration='TC-NEW',
            aircraft_type=aircraft_type_c172,
            category=Aircraft.Category.AIRPLANE,
        )

        assert aircraft.registration == 'TC-NEW'
        assert aircraft.organization_id == test_organization['id']
        assert aircraft.status == Aircraft.Status.ACTIVE

    def test_create_aircraft_duplicate_registration(
        self, service, test_organization, aircraft_c172
    ):
        """Test creating aircraft with duplicate registration."""
        with pytest.raises(AircraftConflictError):
            service.create_aircraft(
                organization_id=test_organization['id'],
                registration='TC-AVI',  # Already exists
                category=Aircraft.Category.AIRPLANE,
            )

    def test_create_aircraft_invalid_registration(self, service, test_organization):
        """Test creating aircraft with invalid registration."""
        with pytest.raises(AircraftValidationError):
            service.create_aircraft(
                organization_id=test_organization['id'],
                registration='A',  # Too short
                category=Aircraft.Category.AIRPLANE,
            )

    def test_get_aircraft(self, service, aircraft_c172):
        """Test getting an aircraft."""
        aircraft = service.get_aircraft(aircraft_c172.id)
        assert aircraft.id == aircraft_c172.id
        assert aircraft.registration == 'TC-AVI'

    def test_get_aircraft_not_found(self, service):
        """Test getting non-existent aircraft."""
        with pytest.raises(AircraftNotFoundError):
            service.get_aircraft(uuid.uuid4())

    def test_get_aircraft_by_registration(self, service, aircraft_c172, test_organization):
        """Test getting aircraft by registration."""
        aircraft = service.get_aircraft_by_registration(
            organization_id=test_organization['id'],
            registration='TC-AVI'
        )
        assert aircraft.id == aircraft_c172.id

    def test_list_aircraft(self, service, test_organization, aircraft_c172, aircraft_pa28):
        """Test listing aircraft."""
        aircraft_list = service.list_aircraft(
            organization_id=test_organization['id']
        )
        assert len(aircraft_list) >= 2

    def test_list_aircraft_with_filters(
        self, service, test_organization, aircraft_c172, aircraft_grounded
    ):
        """Test listing aircraft with filters."""
        # Only active
        active = service.list_aircraft(
            organization_id=test_organization['id'],
            status=Aircraft.Status.ACTIVE
        )
        registrations = [a.registration for a in active]
        assert 'TC-AVI' in registrations
        assert 'TC-GND' not in registrations

    def test_update_aircraft(self, service, aircraft_c172):
        """Test updating an aircraft."""
        aircraft = service.update_aircraft(
            aircraft_id=aircraft_c172.id,
            notes='Updated notes',
            cruise_speed_kts=125,
        )
        assert aircraft.notes == 'Updated notes'
        assert aircraft.cruise_speed_kts == 125

    def test_delete_aircraft(self, service, aircraft_c172, test_user):
        """Test soft deleting an aircraft."""
        service.delete_aircraft(
            aircraft_id=aircraft_c172.id,
            deleted_by=test_user['id']
        )

        # Refresh from DB
        aircraft_c172.refresh_from_db()
        assert aircraft_c172.deleted_at is not None

    def test_get_aircraft_status(self, service, aircraft_c172):
        """Test getting aircraft status."""
        status = service.get_aircraft_status(aircraft_c172.id)

        assert 'status' in status
        assert 'is_airworthy' in status
        assert 'warnings' in status
        assert 'blockers' in status

    def test_ground_aircraft(self, service, aircraft_c172, test_user):
        """Test grounding an aircraft."""
        aircraft = service.ground_aircraft(
            aircraft_id=aircraft_c172.id,
            reason='Test grounding reason',
            grounded_by=test_user['id']
        )

        assert aircraft.is_grounded is True
        assert aircraft.status == Aircraft.Status.GROUNDED

    def test_unground_aircraft(self, service, aircraft_grounded):
        """Test ungrounding an aircraft."""
        aircraft = service.unground_aircraft(aircraft_grounded.id)

        assert aircraft.is_grounded is False
        assert aircraft.status == Aircraft.Status.ACTIVE

    def test_check_availability(self, service, aircraft_c172):
        """Test checking availability."""
        availability = service.check_availability(
            aircraft_id=aircraft_c172.id,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=2)
        )

        assert 'is_available' in availability
        assert availability['is_available'] is True


# =============================================================================
# SquawkService Tests
# =============================================================================

@pytest.mark.django_db
class TestSquawkService:
    """Tests for SquawkService."""

    @pytest.fixture
    def service(self):
        return SquawkService()

    def test_create_squawk(self, service, test_organization, aircraft_c172, test_user):
        """Test creating a squawk."""
        squawk = service.create_squawk(
            aircraft_id=aircraft_c172.id,
            organization_id=test_organization['id'],
            title='Test squawk',
            description='Test description for the squawk',
            category=AircraftSquawk.Category.INSTRUMENTS,
            severity=AircraftSquawk.Severity.MINOR,
            reported_by=test_user['id'],
            reported_by_name=test_user['name'],
        )

        assert squawk.title == 'Test squawk'
        assert squawk.status == AircraftSquawk.Status.OPEN
        assert squawk.squawk_number is not None

    def test_get_squawk(self, service, squawk_open):
        """Test getting a squawk."""
        squawk = service.get_squawk(squawk_open.id)
        assert squawk.id == squawk_open.id

    def test_list_squawks(self, service, test_organization, squawk_open, squawk_resolved):
        """Test listing squawks."""
        squawks = service.list_squawks(organization_id=test_organization['id'])
        assert len(squawks) >= 2

    def test_list_squawks_for_aircraft(
        self, service, test_organization, aircraft_c172, squawk_open
    ):
        """Test listing squawks for specific aircraft."""
        squawks = service.list_squawks(
            organization_id=test_organization['id'],
            aircraft_id=aircraft_c172.id
        )
        assert all(s.aircraft_id == aircraft_c172.id for s in squawks)

    def test_resolve_squawk(self, service, squawk_open, test_mechanic):
        """Test resolving a squawk."""
        squawk = service.resolve_squawk(
            squawk_id=squawk_open.id,
            resolution='Fixed the issue',
            resolved_by=test_mechanic['id'],
            resolved_by_name=test_mechanic['name'],
        )

        assert squawk.status == AircraftSquawk.Status.RESOLVED
        assert squawk.resolution == 'Fixed the issue'

    def test_close_squawk(self, service, squawk_resolved, test_user):
        """Test closing a squawk."""
        squawk = service.close_squawk(
            squawk_id=squawk_resolved.id,
            closed_by=test_user['id'],
            closed_by_name=test_user['name'],
        )

        assert squawk.status == AircraftSquawk.Status.CLOSED

    def test_cancel_squawk(self, service, squawk_open):
        """Test cancelling a squawk."""
        squawk = service.cancel_squawk(
            squawk_id=squawk_open.id,
            reason='Created in error - not a real issue',
        )

        assert squawk.status == AircraftSquawk.Status.CANCELLED

    def test_defer_squawk(self, service, squawk_open, test_user):
        """Test deferring a squawk."""
        squawk = service.defer_squawk(
            squawk_id=squawk_open.id,
            mel_category=AircraftSquawk.MELCategory.C,
            mel_reference='MEL 34-20',
            deferred_by=test_user['id'],
        )

        assert squawk.status == AircraftSquawk.Status.DEFERRED
        assert squawk.is_mel_item is True

    def test_get_statistics(self, service, test_organization, squawk_open, squawk_resolved):
        """Test getting squawk statistics."""
        stats = service.get_statistics(organization_id=test_organization['id'])

        assert 'total' in stats
        assert 'open' in stats
        assert 'by_severity' in stats


# =============================================================================
# CounterService Tests
# =============================================================================

@pytest.mark.django_db
class TestCounterService:
    """Tests for CounterService."""

    @pytest.fixture
    def service(self):
        return CounterService()

    def test_get_counters(self, service, aircraft_c172):
        """Test getting counters."""
        counters = service.get_counters(aircraft_c172.id)

        assert counters['aircraft_id'] == str(aircraft_c172.id)
        assert counters['hobbs_time'] == float(aircraft_c172.hobbs_time)
        assert 'engines' in counters

    def test_add_flight_time(self, service, aircraft_c172, test_user):
        """Test adding flight time."""
        initial_hobbs = float(aircraft_c172.hobbs_time)
        flight_id = uuid.uuid4()

        result = service.add_flight_time(
            aircraft_id=aircraft_c172.id,
            flight_id=flight_id,
            hobbs_time=Decimal('1.5'),
            landings=2,
            created_by=test_user['id'],
        )

        assert 'time_log_id' in result
        assert result['new_counters']['hobbs_time'] == initial_hobbs + 1.5

    def test_adjust_counter(self, service, aircraft_c172, test_mechanic):
        """Test adjusting a counter."""
        result = service.adjust_counter(
            aircraft_id=aircraft_c172.id,
            field='hobbs_time',
            new_value=Decimal('1300.0'),
            reason='Meter replaced - adjusting to match new meter reading',
            created_by=test_mechanic['id'],
            created_by_name=test_mechanic['name'],
        )

        assert 'time_log_id' in result
        assert result['new_value'] == 1300.0

    def test_adjust_counter_invalid_field(self, service, aircraft_c172, test_mechanic):
        """Test adjusting invalid counter field."""
        with pytest.raises(CounterError):
            service.adjust_counter(
                aircraft_id=aircraft_c172.id,
                field='invalid_field',
                new_value=Decimal('100'),
                reason='Test reason for adjustment',
                created_by=test_mechanic['id'],
            )

    def test_get_time_logs(self, service, aircraft_c172, time_log_flight):
        """Test getting time logs."""
        result = service.get_time_logs(aircraft_c172.id)

        assert 'logs' in result
        assert len(result['logs']) >= 1

    def test_get_utilization_stats(self, service, aircraft_c172):
        """Test getting utilization statistics."""
        stats = service.get_utilization_stats(
            aircraft_id=aircraft_c172.id,
            period_days=30
        )

        assert 'period' in stats
        assert 'totals' in stats
        assert 'averages' in stats


# =============================================================================
# DocumentService Tests
# =============================================================================

@pytest.mark.django_db
class TestDocumentService:
    """Tests for DocumentService."""

    @pytest.fixture
    def service(self):
        return DocumentService()

    def test_add_document(self, service, test_organization, aircraft_c172, test_user):
        """Test adding a document."""
        document = service.add_document(
            aircraft_id=aircraft_c172.id,
            organization_id=test_organization['id'],
            document_type=AircraftDocument.DocumentType.POH,
            title='Pilots Operating Handbook',
            file_url='https://storage.example.com/docs/poh.pdf',
            created_by=test_user['id'],
        )

        assert document.document_type == AircraftDocument.DocumentType.POH
        assert document.is_current is True

    def test_get_document(self, service, document_registration):
        """Test getting a document."""
        document = service.get_document(document_registration.id)
        assert document.id == document_registration.id

    def test_list_documents(self, service, aircraft_c172, document_registration, document_insurance):
        """Test listing documents."""
        documents = service.list_documents(aircraft_c172.id)
        assert len(documents) >= 2

    def test_update_document(self, service, document_registration, test_user):
        """Test updating a document."""
        document = service.update_document(
            document_id=document_registration.id,
            title='Updated Title',
            updated_by=test_user['id'],
        )

        assert document.title == 'Updated Title'

    def test_delete_document(self, service, document_registration):
        """Test deleting a document."""
        doc_id = document_registration.id
        service.delete_document(doc_id)

        with pytest.raises(DocumentError):
            service.get_document(doc_id)

    def test_check_compliance(self, service, aircraft_c172, document_registration):
        """Test checking compliance."""
        compliance = service.check_compliance(aircraft_c172.id)

        assert 'is_compliant' in compliance
        assert 'missing_documents' in compliance
        assert 'expired_documents' in compliance

    def test_get_expiring_documents(self, service, test_organization, document_insurance):
        """Test getting expiring documents."""
        # Set to expire soon
        document_insurance.expiry_date = date.today() + timedelta(days=15)
        document_insurance.save()

        documents = service.get_expiring_documents(
            organization_id=test_organization['id'],
            days_ahead=30
        )

        assert len(documents) >= 1

    def test_get_expired_documents(self, service, test_organization, document_expired):
        """Test getting expired documents."""
        documents = service.get_expired_documents(
            organization_id=test_organization['id']
        )

        assert len(documents) >= 1
