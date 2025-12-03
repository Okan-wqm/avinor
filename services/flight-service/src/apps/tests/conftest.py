# services/flight-service/src/apps/tests/conftest.py
"""
Pytest Configuration and Fixtures

Shared fixtures for flight service tests.
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone


# =============================================================================
# UUID Fixtures
# =============================================================================

@pytest.fixture
def organization_id():
    """Generate organization ID."""
    return uuid.uuid4()


@pytest.fixture
def user_id():
    """Generate user ID."""
    return uuid.uuid4()


@pytest.fixture
def aircraft_id():
    """Generate aircraft ID."""
    return uuid.uuid4()


@pytest.fixture
def pilot_id():
    """Generate pilot ID."""
    return uuid.uuid4()


@pytest.fixture
def instructor_id():
    """Generate instructor ID."""
    return uuid.uuid4()


@pytest.fixture
def student_id():
    """Generate student ID."""
    return uuid.uuid4()


# =============================================================================
# Model Fixtures
# =============================================================================

@pytest.fixture
def flight_data(organization_id, user_id, aircraft_id, pilot_id):
    """Generate basic flight data."""
    return {
        'organization_id': organization_id,
        'created_by': user_id,
        'flight_date': date.today(),
        'aircraft_id': aircraft_id,
        'aircraft_registration': 'LN-ABC',
        'aircraft_type': 'C172',
        'departure_airport': 'ENGM',
        'arrival_airport': 'ENZV',
        'flight_type': 'training',
        'flight_rules': 'VFR',
        'pic_id': pilot_id,
        'block_off': timezone.now() - timedelta(hours=2),
        'takeoff_time': timezone.now() - timedelta(hours=2) + timedelta(minutes=10),
        'landing_time': timezone.now() - timedelta(minutes=20),
        'block_on': timezone.now() - timedelta(minutes=10),
        'hobbs_start': Decimal('1234.5'),
        'hobbs_end': Decimal('1236.5'),
        'landings_day': 2,
        'full_stop_day': 1,
    }


@pytest.fixture
def training_flight_data(flight_data, instructor_id, student_id):
    """Generate training flight data."""
    return {
        **flight_data,
        'flight_type': 'training',
        'training_type': 'dual',
        'instructor_id': instructor_id,
        'student_id': student_id,
        'time_dual_received': Decimal('1.5'),
    }


@pytest.fixture
def approach_data(organization_id):
    """Generate approach data."""
    return {
        'organization_id': organization_id,
        'approach_type': 'ILS',
        'airport_icao': 'ENGM',
        'runway': '01L',
        'result': 'landed',
        'in_imc': True,
        'to_minimums': True,
        'hand_flown': True,
    }


@pytest.fixture
def hold_data(organization_id):
    """Generate hold data."""
    return {
        'organization_id': organization_id,
        'fix_name': 'NETRO',
        'fix_type': 'VOR',
        'entry_type': 'direct',
        'turns': 2,
        'altitude': 5000,
        'in_imc': True,
    }


@pytest.fixture
def fuel_record_data(organization_id, aircraft_id, user_id):
    """Generate fuel record data."""
    return {
        'organization_id': organization_id,
        'aircraft_id': aircraft_id,
        'created_by': user_id,
        'record_type': 'uplift',
        'fuel_type': '100LL',
        'quantity_liters': Decimal('150.0'),
        'price_per_liter': Decimal('25.50'),
        'location_icao': 'ENGM',
        'fbo_name': 'Avinor FBO',
    }


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture
def flight(db, flight_data):
    """Create a flight in database."""
    from apps.core.models import Flight
    return Flight.objects.create(**flight_data)


@pytest.fixture
def approved_flight(db, flight_data, user_id):
    """Create an approved flight."""
    from apps.core.models import Flight
    flight_data['flight_status'] = Flight.Status.APPROVED
    flight_data['approved_at'] = timezone.now()
    flight_data['approved_by'] = user_id
    return Flight.objects.create(**flight_data)


@pytest.fixture
def training_flight(db, training_flight_data):
    """Create a training flight."""
    from apps.core.models import Flight
    return Flight.objects.create(**training_flight_data)


@pytest.fixture
def approach(db, flight, approach_data):
    """Create an approach record."""
    from apps.core.models import Approach
    approach_data['flight_id'] = flight.id
    return Approach.objects.create(**approach_data)


@pytest.fixture
def hold(db, flight, hold_data):
    """Create a hold record."""
    from apps.core.models import Hold
    hold_data['flight_id'] = flight.id
    return Hold.objects.create(**hold_data)


@pytest.fixture
def fuel_record(db, flight, fuel_record_data):
    """Create a fuel record."""
    from apps.core.models import FuelRecord
    fuel_record_data['flight_id'] = flight.id
    return FuelRecord.objects.create(**fuel_record_data)


@pytest.fixture
def pilot_logbook_summary(db, organization_id, pilot_id):
    """Create a pilot logbook summary."""
    from apps.core.models import PilotLogbookSummary
    return PilotLogbookSummary.objects.create(
        organization_id=organization_id,
        user_id=pilot_id,
        total_time=Decimal('150.5'),
        total_pic=Decimal('100.0'),
        total_flights=75,
        landings_last_90_days=10,
        night_landings_last_90_days=3,
        ifr_approaches_last_6_months=8,
    )


@pytest.fixture
def flight_crew_log(db, approved_flight, pilot_id):
    """Create a flight crew log entry."""
    from apps.core.models import FlightCrewLog
    return FlightCrewLog.objects.create(
        flight_id=approved_flight.id,
        organization_id=approved_flight.organization_id,
        user_id=pilot_id,
        role='pic',
        flight_time=approved_flight.flight_time or Decimal('1.5'),
        time_pic=Decimal('1.5'),
        landings_day=2,
        full_stop_day=1,
    )


# =============================================================================
# Service Fixtures
# =============================================================================

@pytest.fixture
def flight_service():
    """Get FlightService class."""
    from apps.core.services import FlightService
    return FlightService


@pytest.fixture
def logbook_service():
    """Get LogbookService class."""
    from apps.core.services import LogbookService
    return LogbookService


@pytest.fixture
def currency_service():
    """Get CurrencyService class."""
    from apps.core.services import CurrencyService
    return CurrencyService


@pytest.fixture
def statistics_service():
    """Get StatisticsService class."""
    from apps.core.services import StatisticsService
    return StatisticsService


# =============================================================================
# API Client Fixtures
# =============================================================================

@pytest.fixture
def api_client():
    """Get Django REST framework API client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, organization_id, user_id):
    """Get authenticated API client with headers."""
    api_client.credentials(
        HTTP_X_ORGANIZATION_ID=str(organization_id),
        HTTP_X_USER_ID=str(user_id)
    )
    return api_client


# =============================================================================
# Helper Fixtures
# =============================================================================

@pytest.fixture
def create_multiple_flights(db, organization_id, user_id, aircraft_id, pilot_id):
    """Factory fixture for creating multiple flights."""
    from apps.core.models import Flight

    def _create_flights(count=5, **overrides):
        flights = []
        for i in range(count):
            data = {
                'organization_id': organization_id,
                'created_by': user_id,
                'flight_date': date.today() - timedelta(days=i),
                'aircraft_id': aircraft_id,
                'aircraft_registration': f'LN-AB{chr(65 + i % 26)}',
                'aircraft_type': 'C172',
                'departure_airport': 'ENGM',
                'arrival_airport': 'ENZV',
                'flight_type': 'training',
                'flight_rules': 'VFR',
                'pic_id': pilot_id,
                'flight_time': Decimal('1.5'),
                'landings_day': 1,
                'full_stop_day': 1,
                **overrides,
            }
            flights.append(Flight.objects.create(**data))
        return flights

    return _create_flights


@pytest.fixture
def create_approved_flights(db, organization_id, user_id, aircraft_id, pilot_id):
    """Factory fixture for creating approved flights."""
    from apps.core.models import Flight

    def _create_flights(count=5, **overrides):
        flights = []
        for i in range(count):
            data = {
                'organization_id': organization_id,
                'created_by': user_id,
                'flight_date': date.today() - timedelta(days=i),
                'aircraft_id': aircraft_id,
                'aircraft_registration': f'LN-AB{chr(65 + i % 26)}',
                'aircraft_type': 'C172',
                'departure_airport': 'ENGM',
                'arrival_airport': 'ENZV',
                'flight_type': 'training',
                'flight_rules': 'VFR',
                'pic_id': pilot_id,
                'flight_time': Decimal('1.5'),
                'landings_day': 1,
                'full_stop_day': 1,
                'flight_status': Flight.Status.APPROVED,
                'approved_at': timezone.now(),
                'approved_by': user_id,
                **overrides,
            }
            flights.append(Flight.objects.create(**data))
        return flights

    return _create_flights
