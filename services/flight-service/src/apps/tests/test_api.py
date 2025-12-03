# services/flight-service/src/apps/tests/test_api.py
"""
API Tests

Tests for flight service REST API endpoints.
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status


# =============================================================================
# Flight API Tests
# =============================================================================

@pytest.mark.django_db
class TestFlightAPI:
    """Tests for Flight API endpoints."""

    def test_list_flights(self, authenticated_client, create_multiple_flights):
        """Test listing flights."""
        create_multiple_flights(count=5)

        response = authenticated_client.get('/api/v1/flights/flights/')

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert 'total' in response.data

    def test_list_flights_with_pagination(
        self, authenticated_client, create_multiple_flights
    ):
        """Test listing flights with pagination."""
        create_multiple_flights(count=15)

        response = authenticated_client.get(
            '/api/v1/flights/flights/',
            {'page': 1, 'page_size': 5}
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5
        assert response.data['total'] == 15

    def test_create_flight(
        self, authenticated_client, aircraft_id, pilot_id
    ):
        """Test creating a flight."""
        data = {
            'flight_date': date.today().isoformat(),
            'aircraft_id': str(aircraft_id),
            'aircraft_registration': 'LN-TST',
            'aircraft_type': 'C172',
            'departure_airport': 'ENGM',
            'arrival_airport': 'ENZV',
            'flight_type': 'training',
            'flight_rules': 'VFR',
            'pic_id': str(pilot_id),
        }

        response = authenticated_client.post(
            '/api/v1/flights/flights/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['aircraft_registration'] == 'LN-TST'

    def test_get_flight(self, authenticated_client, flight):
        """Test getting a flight."""
        response = authenticated_client.get(
            f'/api/v1/flights/flights/{flight.id}/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['flight']['id'] == str(flight.id)

    def test_update_flight(self, authenticated_client, flight):
        """Test updating a flight."""
        response = authenticated_client.patch(
            f'/api/v1/flights/flights/{flight.id}/',
            {'remarks': 'Updated via API'},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['remarks'] == 'Updated via API'

    def test_delete_flight(self, authenticated_client, flight):
        """Test deleting a flight."""
        response = authenticated_client.delete(
            f'/api/v1/flights/flights/{flight.id}/'
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_submit_flight(self, authenticated_client, flight):
        """Test submitting a flight."""
        # Ensure required fields
        from django.utils import timezone
        flight.block_off = timezone.now() - timedelta(hours=2)
        flight.block_on = timezone.now()
        flight.save()

        response = authenticated_client.post(
            f'/api/v1/flights/flights/{flight.id}/submit/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['flight_status'] == 'submitted'

    def test_approve_flight(self, authenticated_client, flight):
        """Test approving a flight."""
        from apps.core.models import Flight
        flight.flight_status = Flight.Status.SUBMITTED
        flight.save()

        response = authenticated_client.post(
            f'/api/v1/flights/flights/{flight.id}/approve/',
            {'remarks': 'Approved'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['flight_status'] == 'approved'

    def test_reject_flight(self, authenticated_client, flight):
        """Test rejecting a flight."""
        from apps.core.models import Flight
        flight.flight_status = Flight.Status.SUBMITTED
        flight.save()

        response = authenticated_client.post(
            f'/api/v1/flights/flights/{flight.id}/reject/',
            {'reason': 'Test rejection'},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['flight_status'] == 'rejected'

    def test_sign_flight(self, authenticated_client, flight):
        """Test signing a flight."""
        response = authenticated_client.post(
            f'/api/v1/flights/flights/{flight.id}/sign/',
            {
                'role': 'pic',
                'signature_data': {'type': 'svg', 'data': 'test'}
            },
            format='json'
        )

        # Should succeed if user is PIC
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_pending_approval(self, authenticated_client, flight):
        """Test getting pending approval flights."""
        from apps.core.models import Flight
        flight.flight_status = Flight.Status.SUBMITTED
        flight.save()

        response = authenticated_client.get(
            '/api/v1/flights/flights/pending_approval/'
        )

        assert response.status_code == status.HTTP_200_OK

    def test_by_pilot(self, authenticated_client, flight, pilot_id):
        """Test getting flights by pilot."""
        response = authenticated_client.get(
            '/api/v1/flights/flights/by_pilot/',
            {'pilot_id': str(pilot_id)}
        )

        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Approach API Tests
# =============================================================================

@pytest.mark.django_db
class TestApproachAPI:
    """Tests for Approach API endpoints."""

    def test_list_approaches(self, authenticated_client, approach):
        """Test listing approaches."""
        response = authenticated_client.get('/api/v1/flights/approaches/')

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_create_approach(self, authenticated_client, flight):
        """Test creating an approach."""
        data = {
            'flight_id': str(flight.id),
            'approach_type': 'ILS',
            'airport_icao': 'ENGM',
            'runway': '01L',
            'result': 'landed',
        }

        response = authenticated_client.post(
            '/api/v1/flights/approaches/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_get_approach(self, authenticated_client, approach):
        """Test getting an approach."""
        response = authenticated_client.get(
            f'/api/v1/flights/approaches/{approach.id}/'
        )

        assert response.status_code == status.HTTP_200_OK

    def test_by_flight(self, authenticated_client, flight, approach):
        """Test getting approaches by flight."""
        response = authenticated_client.get(
            '/api/v1/flights/approaches/by_flight/',
            {'flight_id': str(flight.id)}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_approach_statistics(self, authenticated_client, approach):
        """Test getting approach statistics."""
        response = authenticated_client.get(
            '/api/v1/flights/approaches/statistics/'
        )

        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Fuel Record API Tests
# =============================================================================

@pytest.mark.django_db
class TestFuelRecordAPI:
    """Tests for Fuel Record API endpoints."""

    def test_list_fuel_records(self, authenticated_client, fuel_record):
        """Test listing fuel records."""
        response = authenticated_client.get('/api/v1/flights/fuel-records/')

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_create_fuel_record(self, authenticated_client, flight):
        """Test creating a fuel record."""
        data = {
            'flight_id': str(flight.id),
            'record_type': 'uplift',
            'fuel_type': '100LL',
            'quantity_liters': '150.0',
            'price_per_liter': '25.50',
            'location_icao': 'ENGM',
        }

        response = authenticated_client.post(
            '/api/v1/flights/fuel-records/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_by_aircraft(self, authenticated_client, fuel_record, aircraft_id):
        """Test getting fuel records by aircraft."""
        response = authenticated_client.get(
            '/api/v1/flights/fuel-records/by_aircraft/',
            {'aircraft_id': str(aircraft_id)}
        )

        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Logbook API Tests
# =============================================================================

@pytest.mark.django_db
class TestLogbookAPI:
    """Tests for Logbook API endpoints."""

    def test_list_logbook_entries(
        self, authenticated_client, approved_flight, flight_crew_log
    ):
        """Test listing logbook entries."""
        response = authenticated_client.get('/api/v1/flights/logbook/')

        assert response.status_code == status.HTTP_200_OK
        assert 'entries' in response.data

    def test_get_summary(self, authenticated_client, pilot_logbook_summary):
        """Test getting logbook summary."""
        response = authenticated_client.get('/api/v1/flights/logbook/summary/')

        assert response.status_code == status.HTTP_200_OK

    def test_recalculate_summary(self, authenticated_client):
        """Test recalculating logbook summary."""
        response = authenticated_client.post(
            '/api/v1/flights/logbook/recalculate/'
        )

        assert response.status_code == status.HTTP_200_OK

    def test_export_logbook(
        self, authenticated_client, approved_flight, flight_crew_log
    ):
        """Test exporting logbook."""
        response = authenticated_client.get(
            '/api/v1/flights/logbook/export/',
            {'format': 'json'}
        )

        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Statistics API Tests
# =============================================================================

@pytest.mark.django_db
class TestStatisticsAPI:
    """Tests for Statistics API endpoints."""

    def test_dashboard(self, authenticated_client, create_approved_flights):
        """Test getting dashboard statistics."""
        create_approved_flights(count=3)

        response = authenticated_client.get(
            '/api/v1/flights/statistics/dashboard/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'last_30_days' in response.data

    def test_pilot_statistics(self, authenticated_client, create_approved_flights):
        """Test getting pilot statistics."""
        create_approved_flights(count=3)

        response = authenticated_client.get(
            '/api/v1/flights/statistics/pilot/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'summary' in response.data

    def test_organization_statistics(
        self, authenticated_client, create_approved_flights
    ):
        """Test getting organization statistics."""
        create_approved_flights(count=3)

        response = authenticated_client.get(
            '/api/v1/flights/statistics/organization/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'summary' in response.data


# =============================================================================
# Currency API Tests
# =============================================================================

@pytest.mark.django_db
class TestCurrencyAPI:
    """Tests for Currency API endpoints."""

    def test_currency_status(self, authenticated_client):
        """Test getting currency status."""
        response = authenticated_client.get('/api/v1/flights/currency/status/')

        assert response.status_code == status.HTTP_200_OK
        assert 'currencies' in response.data

    def test_currency_check(self, authenticated_client):
        """Test checking all currency."""
        response = authenticated_client.get('/api/v1/flights/currency/check/')

        assert response.status_code == status.HTTP_200_OK

    def test_validate_for_flight(self, authenticated_client):
        """Test validating currency for flight."""
        response = authenticated_client.post(
            '/api/v1/flights/currency/validate_for_flight/',
            {
                'flight_type': 'training',
                'flight_rules': 'VFR',
                'has_passengers': False,
                'is_night': False,
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'is_valid' in response.data

    def test_day_vfr_currency(self, authenticated_client):
        """Test getting day VFR currency details."""
        response = authenticated_client.get('/api/v1/flights/currency/day_vfr/')

        assert response.status_code == status.HTTP_200_OK

    def test_ifr_currency(self, authenticated_client):
        """Test getting IFR currency details."""
        response = authenticated_client.get('/api/v1/flights/currency/ifr/')

        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.django_db
class TestErrorHandling:
    """Tests for API error handling."""

    def test_missing_organization_id(self, api_client):
        """Test request without organization ID."""
        response = api_client.get('/api/v1/flights/flights/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_uuid(self, authenticated_client):
        """Test request with invalid UUID."""
        response = authenticated_client.get(
            '/api/v1/flights/flights/invalid-uuid/'
        )

        # Should return 400 or 404
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]

    def test_flight_not_found(self, authenticated_client):
        """Test getting non-existent flight."""
        response = authenticated_client.get(
            f'/api/v1/flights/flights/{uuid.uuid4()}/'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_validation_error(self, authenticated_client):
        """Test validation error response."""
        # Missing required fields
        response = authenticated_client.post(
            '/api/v1/flights/flights/',
            {},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
