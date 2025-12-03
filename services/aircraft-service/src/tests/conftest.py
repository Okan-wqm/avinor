# services/aircraft-service/src/tests/conftest.py
"""
Pytest Configuration and Fixtures for Aircraft Service Tests.
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import (
    Aircraft, AircraftType, AircraftEngine, AircraftPropeller,
    AircraftSquawk, AircraftDocument, AircraftTimeLog
)


# =============================================================================
# API Client Fixtures
# =============================================================================

@pytest.fixture
def api_client():
    """Return an API client instance."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, test_organization, test_user):
    """Return an authenticated API client with organization headers."""
    api_client.credentials(
        HTTP_X_ORGANIZATION_ID=str(test_organization['id']),
        HTTP_X_USER_ID=str(test_user['id']),
        HTTP_X_USER_NAME=test_user['name'],
        HTTP_AUTHORIZATION='Bearer test-token'
    )
    return api_client


# =============================================================================
# Identity Fixtures
# =============================================================================

@pytest.fixture
def test_organization():
    """Return a test organization."""
    return {
        'id': uuid.uuid4(),
        'name': 'Test Flight School',
        'code': 'TFS',
    }


@pytest.fixture
def test_user():
    """Return a test user."""
    return {
        'id': uuid.uuid4(),
        'name': 'John Pilot',
        'email': 'john@example.com',
    }


@pytest.fixture
def test_mechanic():
    """Return a test mechanic user."""
    return {
        'id': uuid.uuid4(),
        'name': 'Bob Mechanic',
        'email': 'bob@example.com',
    }


@pytest.fixture
def test_location():
    """Return a test location (airport)."""
    return {
        'id': uuid.uuid4(),
        'icao_code': 'LTBA',
        'name': 'Istanbul Airport',
    }


# =============================================================================
# Aircraft Type Fixtures
# =============================================================================

@pytest.fixture
def aircraft_type_c172(db):
    """Create a Cessna 172 aircraft type."""
    return AircraftType.objects.create(
        icao_code='C172',
        manufacturer='Cessna',
        model='172',
        variant='S',
        common_name='Cessna 172 Skyhawk',
        category=AircraftType.Category.AIRPLANE,
        class_type=AircraftType.ClassType.SEL,
        engine_count=1,
        engine_type='piston',
        default_cruise_speed_kts=122,
        default_fuel_consumption_gph=8.5,
        default_fuel_capacity_gal=56,
        default_useful_load_lbs=878,
        default_seat_count=4,
        is_complex=False,
        is_high_performance=False,
        is_tailwheel=False,
        is_pressurized=False,
        requires_type_rating=False,
    )


@pytest.fixture
def aircraft_type_pa28(db):
    """Create a Piper PA-28 aircraft type."""
    return AircraftType.objects.create(
        icao_code='PA28',
        manufacturer='Piper',
        model='PA-28',
        variant='161',
        common_name='Piper Warrior',
        category=AircraftType.Category.AIRPLANE,
        class_type=AircraftType.ClassType.SEL,
        engine_count=1,
        engine_type='piston',
        default_cruise_speed_kts=115,
        default_fuel_consumption_gph=9.0,
        default_fuel_capacity_gal=50,
        default_useful_load_lbs=820,
        default_seat_count=4,
        is_complex=False,
        is_high_performance=False,
    )


@pytest.fixture
def aircraft_type_da42(db):
    """Create a Diamond DA42 aircraft type (multi-engine)."""
    return AircraftType.objects.create(
        icao_code='DA42',
        manufacturer='Diamond',
        model='DA42',
        variant='VI',
        common_name='Diamond DA42 Twin Star',
        category=AircraftType.Category.AIRPLANE,
        class_type=AircraftType.ClassType.MEL,
        engine_count=2,
        engine_type='piston',
        default_cruise_speed_kts=170,
        default_fuel_consumption_gph=14.0,
        default_fuel_capacity_gal=50,
        default_useful_load_lbs=980,
        default_seat_count=4,
        is_complex=True,
        is_high_performance=True,
    )


# =============================================================================
# Aircraft Fixtures
# =============================================================================

@pytest.fixture
def aircraft_c172(db, test_organization, aircraft_type_c172, test_location):
    """Create a Cessna 172 aircraft."""
    return Aircraft.objects.create(
        organization_id=test_organization['id'],
        registration='TC-AVI',
        serial_number='17280001',
        aircraft_type=aircraft_type_c172,
        category=Aircraft.Category.AIRPLANE,
        class_type='SEL',
        year_manufactured=2020,
        engine_type=Aircraft.EngineType.PISTON,
        engine_count=1,
        fuel_type=Aircraft.FuelType.AVGAS_100LL,
        max_gross_weight_lbs=2550,
        empty_weight_lbs=1672,
        useful_load_lbs=878,
        fuel_capacity_gal=56,
        usable_fuel_gal=53,
        oil_capacity_qts=8,
        max_passengers=3,
        cruise_speed_kts=122,
        fuel_burn_gph=8.5,
        hobbs_time=Decimal('1234.5'),
        tach_time=Decimal('1180.2'),
        total_time_hours=Decimal('1234.5'),
        total_landings=5432,
        total_cycles=2716,
        billing_time_source=Aircraft.BillingTimeSource.HOBBS,
        status=Aircraft.Status.ACTIVE,
        is_airworthy=True,
        arc_expiry_date=date.today() + timedelta(days=180),
        insurance_expiry_date=date.today() + timedelta(days=90),
        home_base_id=test_location['id'],
        current_location_id=test_location['id'],
        hourly_rate=Decimal('150.00'),
    )


@pytest.fixture
def aircraft_pa28(db, test_organization, aircraft_type_pa28, test_location):
    """Create a Piper PA-28 aircraft."""
    return Aircraft.objects.create(
        organization_id=test_organization['id'],
        registration='TC-FLY',
        serial_number='28-7916001',
        aircraft_type=aircraft_type_pa28,
        category=Aircraft.Category.AIRPLANE,
        class_type='SEL',
        year_manufactured=2018,
        engine_type=Aircraft.EngineType.PISTON,
        engine_count=1,
        fuel_type=Aircraft.FuelType.AVGAS_100LL,
        hobbs_time=Decimal('2500.0'),
        total_time_hours=Decimal('2500.0'),
        total_landings=8000,
        status=Aircraft.Status.ACTIVE,
        is_airworthy=True,
        arc_expiry_date=date.today() + timedelta(days=365),
        home_base_id=test_location['id'],
        hourly_rate=Decimal('140.00'),
    )


@pytest.fixture
def aircraft_grounded(db, test_organization, aircraft_type_c172, test_user):
    """Create a grounded aircraft."""
    return Aircraft.objects.create(
        organization_id=test_organization['id'],
        registration='TC-GND',
        serial_number='17280002',
        aircraft_type=aircraft_type_c172,
        category=Aircraft.Category.AIRPLANE,
        status=Aircraft.Status.GROUNDED,
        is_airworthy=False,
        is_grounded=True,
        grounded_at=timezone.now(),
        grounded_by=test_user['id'],
        grounded_reason='Annual inspection required',
    )


@pytest.fixture
def aircraft_multi_engine(db, test_organization, aircraft_type_da42, test_location):
    """Create a multi-engine aircraft."""
    return Aircraft.objects.create(
        organization_id=test_organization['id'],
        registration='TC-MEL',
        serial_number='42.123',
        aircraft_type=aircraft_type_da42,
        category=Aircraft.Category.AIRPLANE,
        class_type='MEL',
        year_manufactured=2019,
        engine_type=Aircraft.EngineType.PISTON,
        engine_count=2,
        is_complex=True,
        is_high_performance=True,
        is_ifr_certified=True,
        hobbs_time=Decimal('500.0'),
        total_time_hours=Decimal('500.0'),
        status=Aircraft.Status.ACTIVE,
        is_airworthy=True,
        home_base_id=test_location['id'],
        hourly_rate=Decimal('350.00'),
    )


# =============================================================================
# Engine Fixtures
# =============================================================================

@pytest.fixture
def engine_single(db, aircraft_c172):
    """Create an engine for single-engine aircraft."""
    return AircraftEngine.objects.create(
        aircraft=aircraft_c172,
        position=1,
        engine_type=AircraftEngine.EngineType.PISTON,
        manufacturer='Lycoming',
        model='IO-360-L2A',
        serial_number='L-12345-51A',
        tsn=Decimal('1234.5'),
        tso=Decimal('234.5'),
        tbo_hours=Decimal('2000'),
        tbo_years=12,
        last_overhaul_date=date.today() - timedelta(days=365),
        horsepower=180,
    )


@pytest.fixture
def engines_multi(db, aircraft_multi_engine):
    """Create engines for multi-engine aircraft."""
    engine1 = AircraftEngine.objects.create(
        aircraft=aircraft_multi_engine,
        position=1,
        engine_type=AircraftEngine.EngineType.PISTON,
        manufacturer='Austro Engine',
        model='AE300',
        serial_number='AE-001',
        tsn=Decimal('500.0'),
        tso=Decimal('500.0'),
        tbo_hours=Decimal('1800'),
        horsepower=170,
    )
    engine2 = AircraftEngine.objects.create(
        aircraft=aircraft_multi_engine,
        position=2,
        engine_type=AircraftEngine.EngineType.PISTON,
        manufacturer='Austro Engine',
        model='AE300',
        serial_number='AE-002',
        tsn=Decimal('500.0'),
        tso=Decimal('500.0'),
        tbo_hours=Decimal('1800'),
        horsepower=170,
    )
    return [engine1, engine2]


# =============================================================================
# Propeller Fixtures
# =============================================================================

@pytest.fixture
def propeller_single(db, aircraft_c172):
    """Create a propeller for single-engine aircraft."""
    return AircraftPropeller.objects.create(
        aircraft=aircraft_c172,
        position=1,
        propeller_type=AircraftPropeller.PropellerType.FIXED_PITCH,
        manufacturer='McCauley',
        model='1C172MDC/M7695',
        serial_number='P-12345',
        blade_count=2,
        tsn=Decimal('1234.5'),
        tso=Decimal('234.5'),
        tbo_hours=Decimal('2400'),
    )


# =============================================================================
# Squawk Fixtures
# =============================================================================

@pytest.fixture
def squawk_open(db, test_organization, aircraft_c172, test_user):
    """Create an open squawk."""
    return AircraftSquawk.objects.create(
        organization_id=test_organization['id'],
        aircraft=aircraft_c172,
        title='Compass inaccurate',
        description='Compass shows 5 degree deviation at all headings',
        category=AircraftSquawk.Category.INSTRUMENTS,
        severity=AircraftSquawk.Severity.MINOR,
        priority=AircraftSquawk.Priority.NORMAL,
        status=AircraftSquawk.Status.OPEN,
        reported_by=test_user['id'],
        reported_by_name=test_user['name'],
        reported_at=timezone.now(),
        aircraft_hours_at=aircraft_c172.hobbs_time,
    )


@pytest.fixture
def squawk_grounding(db, test_organization, aircraft_c172, test_user):
    """Create a grounding squawk."""
    return AircraftSquawk.objects.create(
        organization_id=test_organization['id'],
        aircraft=aircraft_c172,
        title='Engine oil leak',
        description='Significant oil leak observed from engine compartment',
        category=AircraftSquawk.Category.POWERPLANT,
        severity=AircraftSquawk.Severity.GROUNDING,
        priority=AircraftSquawk.Priority.URGENT,
        status=AircraftSquawk.Status.OPEN,
        is_grounding=True,
        affects_dispatch=True,
        reported_by=test_user['id'],
        reported_by_name=test_user['name'],
        reported_at=timezone.now(),
    )


@pytest.fixture
def squawk_deferred(db, test_organization, aircraft_c172, test_user):
    """Create a deferred (MEL) squawk."""
    return AircraftSquawk.objects.create(
        organization_id=test_organization['id'],
        aircraft=aircraft_c172,
        title='Landing light inoperative',
        description='Left landing light not functioning',
        category=AircraftSquawk.Category.LIGHTS,
        severity=AircraftSquawk.Severity.MINOR,
        priority=AircraftSquawk.Priority.LOW,
        status=AircraftSquawk.Status.DEFERRED,
        is_mel_item=True,
        mel_category=AircraftSquawk.MELCategory.C,
        mel_reference='MEL 33-10',
        operational_restrictions='Day VFR only',
        reported_by=test_user['id'],
        reported_at=timezone.now() - timedelta(days=5),
        deferred_at=timezone.now() - timedelta(days=4),
        deferred_by=test_user['id'],
    )


@pytest.fixture
def squawk_resolved(db, test_organization, aircraft_c172, test_user, test_mechanic):
    """Create a resolved squawk."""
    return AircraftSquawk.objects.create(
        organization_id=test_organization['id'],
        aircraft=aircraft_c172,
        title='Flat tire',
        description='Left main tire flat',
        category=AircraftSquawk.Category.LANDING_GEAR,
        severity=AircraftSquawk.Severity.MINOR,
        status=AircraftSquawk.Status.RESOLVED,
        reported_by=test_user['id'],
        reported_at=timezone.now() - timedelta(days=2),
        resolution='Replaced tire and tube, inspected for damage',
        resolved_by=test_mechanic['id'],
        resolved_by_name=test_mechanic['name'],
        resolved_at=timezone.now() - timedelta(days=1),
    )


# =============================================================================
# Document Fixtures
# =============================================================================

@pytest.fixture
def document_registration(db, test_organization, aircraft_c172, test_user):
    """Create a registration document."""
    return AircraftDocument.objects.create(
        organization_id=test_organization['id'],
        aircraft=aircraft_c172,
        document_type=AircraftDocument.DocumentType.REGISTRATION,
        title='Aircraft Registration Certificate',
        file_url='https://storage.example.com/docs/tc-avi-reg.pdf',
        file_name='tc-avi-registration.pdf',
        file_size_bytes=245000,
        file_type=AircraftDocument.FileType.PDF,
        document_number='TC-AVI-2020',
        issuing_authority='SHGM',
        expiry_date=date.today() + timedelta(days=365),
        is_required=True,
        reminder_days=30,
        created_by=test_user['id'],
    )


@pytest.fixture
def document_insurance(db, test_organization, aircraft_c172, test_user):
    """Create an insurance document."""
    return AircraftDocument.objects.create(
        organization_id=test_organization['id'],
        aircraft=aircraft_c172,
        document_type=AircraftDocument.DocumentType.INSURANCE,
        title='Aviation Insurance Policy',
        file_url='https://storage.example.com/docs/tc-avi-insurance.pdf',
        file_name='tc-avi-insurance.pdf',
        file_size_bytes=512000,
        expiry_date=date.today() + timedelta(days=90),
        is_required=True,
        reminder_days=30,
        created_by=test_user['id'],
    )


@pytest.fixture
def document_expired(db, test_organization, aircraft_c172, test_user):
    """Create an expired document."""
    return AircraftDocument.objects.create(
        organization_id=test_organization['id'],
        aircraft=aircraft_c172,
        document_type=AircraftDocument.DocumentType.AIRWORTHINESS,
        title='Airworthiness Certificate',
        file_url='https://storage.example.com/docs/tc-avi-aw.pdf',
        expiry_date=date.today() - timedelta(days=30),
        is_required=True,
        created_by=test_user['id'],
    )


# =============================================================================
# Time Log Fixtures
# =============================================================================

@pytest.fixture
def time_log_flight(db, aircraft_c172, test_user):
    """Create a flight time log entry."""
    return AircraftTimeLog.objects.create(
        aircraft=aircraft_c172,
        source_type=AircraftTimeLog.SourceType.FLIGHT,
        source_id=uuid.uuid4(),
        log_date=date.today(),
        hobbs_before=Decimal('1232.0'),
        hobbs_after=Decimal('1234.5'),
        hobbs_change=Decimal('2.5'),
        total_time_before=Decimal('1232.0'),
        total_time_after=Decimal('1234.5'),
        total_time_change=Decimal('2.5'),
        landings_before=5430,
        landings_after=5432,
        landings_change=2,
        created_by=test_user['id'],
    )


@pytest.fixture
def time_log_adjustment(db, aircraft_c172, test_mechanic):
    """Create an adjustment time log entry."""
    return AircraftTimeLog.objects.create(
        aircraft=aircraft_c172,
        source_type=AircraftTimeLog.SourceType.ADJUSTMENT,
        log_date=date.today(),
        hobbs_before=Decimal('1230.0'),
        hobbs_after=Decimal('1232.0'),
        hobbs_change=Decimal('2.0'),
        adjustment_reason='Correction after maintenance meter swap',
        created_by=test_mechanic['id'],
        created_by_name=test_mechanic['name'],
    )
