# services/aircraft-service/src/tests/test_views.py
"""
Tests for Aircraft Service API Views.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.core.models import Aircraft, AircraftSquawk, AircraftDocument


# =============================================================================
# Aircraft API Tests
# =============================================================================

@pytest.mark.django_db
class TestAircraftAPI:
    """Tests for Aircraft API endpoints."""

    def test_list_aircraft(self, authenticated_client, aircraft_c172, aircraft_pa28):
        """Test listing aircraft."""
        url = reverse('api:aircraft-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_list_aircraft_with_filter(
        self, authenticated_client, aircraft_c172, aircraft_grounded
    ):
        """Test filtering aircraft list."""
        url = reverse('api:aircraft-list')
        response = authenticated_client.get(url, {'status': 'active'})

        assert response.status_code == status.HTTP_200_OK
        registrations = [a['registration'] for a in response.data['results']]
        assert 'TC-AVI' in registrations
        assert 'TC-GND' not in registrations

    def test_create_aircraft(self, authenticated_client, aircraft_type_c172, test_location):
        """Test creating an aircraft."""
        url = reverse('api:aircraft-list')
        data = {
            'registration': 'TC-NEW',
            'serial_number': '17299999',
            'aircraft_type': str(aircraft_type_c172.id),
            'category': 'airplane',
            'year_manufactured': 2023,
            'engine_type': 'piston',
            'engine_count': 1,
            'home_base_id': str(test_location['id']),
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['registration'] == 'TC-NEW'

    def test_create_aircraft_invalid_registration(self, authenticated_client):
        """Test creating aircraft with invalid registration."""
        url = reverse('api:aircraft-list')
        data = {
            'registration': 'X',  # Too short
            'category': 'airplane',
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_aircraft(self, authenticated_client, aircraft_c172):
        """Test retrieving aircraft details."""
        url = reverse('api:aircraft-detail', kwargs={'pk': aircraft_c172.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['registration'] == 'TC-AVI'
        assert 'aircraft_type_data' in response.data

    def test_update_aircraft(self, authenticated_client, aircraft_c172):
        """Test updating an aircraft."""
        url = reverse('api:aircraft-detail', kwargs={'pk': aircraft_c172.id})
        data = {
            'notes': 'Updated via API',
            'cruise_speed_kts': 130,
        }

        response = authenticated_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['notes'] == 'Updated via API'

    def test_delete_aircraft(self, authenticated_client, aircraft_c172):
        """Test deleting an aircraft."""
        url = reverse('api:aircraft-detail', kwargs={'pk': aircraft_c172.id})
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify soft delete
        aircraft_c172.refresh_from_db()
        assert aircraft_c172.deleted_at is not None

    def test_aircraft_status(self, authenticated_client, aircraft_c172):
        """Test getting aircraft status."""
        url = reverse('api:aircraft-status', kwargs={'pk': aircraft_c172.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'status' in response.data
        assert 'warnings' in response.data
        assert 'blockers' in response.data

    def test_ground_aircraft(self, authenticated_client, aircraft_c172):
        """Test grounding an aircraft."""
        url = reverse('api:aircraft-ground', kwargs={'pk': aircraft_c172.id})
        data = {
            'reason': 'Annual inspection required - grounding aircraft',
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_grounded'] is True
        assert response.data['status'] == 'grounded'

    def test_unground_aircraft(self, authenticated_client, aircraft_grounded):
        """Test ungrounding an aircraft."""
        url = reverse('api:aircraft-unground', kwargs={'pk': aircraft_grounded.id})
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_grounded'] is False

    def test_aircraft_availability(self, authenticated_client, aircraft_c172):
        """Test checking aircraft availability."""
        url = reverse('api:aircraft-availability', kwargs={'pk': aircraft_c172.id})
        params = {
            'start': '2024-01-15T09:00:00Z',
            'end': '2024-01-15T12:00:00Z',
        }

        response = authenticated_client.get(url, params)

        assert response.status_code == status.HTTP_200_OK
        assert 'is_available' in response.data


# =============================================================================
# Squawk API Tests
# =============================================================================

@pytest.mark.django_db
class TestSquawkAPI:
    """Tests for Squawk API endpoints."""

    def test_list_squawks(self, authenticated_client, squawk_open, squawk_resolved):
        """Test listing squawks."""
        url = reverse('api:squawk-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_list_squawks_for_aircraft(self, authenticated_client, aircraft_c172, squawk_open):
        """Test listing squawks for specific aircraft."""
        url = reverse(
            'api:aircraft-squawk-list',
            kwargs={'aircraft_pk': aircraft_c172.id}
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_create_squawk(self, authenticated_client, aircraft_c172):
        """Test creating a squawk."""
        url = reverse(
            'api:aircraft-squawk-list',
            kwargs={'aircraft_pk': aircraft_c172.id}
        )
        data = {
            'title': 'Fuel gauge fluctuating',
            'description': 'Left fuel gauge shows erratic readings during flight',
            'category': 'fuel_system',
            'severity': 'minor',
            'priority': 'normal',
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'Fuel gauge fluctuating'
        assert response.data['squawk_number'] is not None

    def test_retrieve_squawk(self, authenticated_client, aircraft_c172, squawk_open):
        """Test retrieving squawk details."""
        url = reverse(
            'api:aircraft-squawk-detail',
            kwargs={'aircraft_pk': aircraft_c172.id, 'pk': squawk_open.id}
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(squawk_open.id)

    def test_resolve_squawk(self, authenticated_client, aircraft_c172, squawk_open):
        """Test resolving a squawk."""
        url = reverse(
            'api:aircraft-squawk-resolve',
            kwargs={'aircraft_pk': aircraft_c172.id, 'pk': squawk_open.id}
        )
        data = {
            'resolution': 'Compass compensated and deviation card updated',
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'resolved'

    def test_defer_squawk(self, authenticated_client, aircraft_c172, squawk_open):
        """Test deferring a squawk."""
        url = reverse(
            'api:aircraft-squawk-defer',
            kwargs={'aircraft_pk': aircraft_c172.id, 'pk': squawk_open.id}
        )
        data = {
            'mel_category': 'C',
            'reason': 'Deferring under MEL until parts available',
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'deferred'
        assert response.data['is_mel_item'] is True

    def test_squawk_statistics(self, authenticated_client, aircraft_c172, squawk_open):
        """Test getting squawk statistics."""
        url = reverse(
            'api:aircraft-squawk-statistics',
            kwargs={'aircraft_pk': aircraft_c172.id}
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'total' in response.data
        assert 'by_severity' in response.data


# =============================================================================
# Document API Tests
# =============================================================================

@pytest.mark.django_db
class TestDocumentAPI:
    """Tests for Document API endpoints."""

    def test_list_documents(self, authenticated_client, aircraft_c172, document_registration):
        """Test listing documents."""
        url = reverse(
            'api:aircraft-document-list',
            kwargs={'aircraft_pk': aircraft_c172.id}
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_create_document(self, authenticated_client, aircraft_c172):
        """Test creating a document."""
        url = reverse(
            'api:aircraft-document-list',
            kwargs={'aircraft_pk': aircraft_c172.id}
        )
        data = {
            'document_type': 'poh',
            'title': 'Pilots Operating Handbook',
            'file_url': 'https://storage.example.com/docs/poh.pdf',
            'file_name': 'poh.pdf',
            'file_type': 'pdf',
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['document_type'] == 'poh'

    def test_document_compliance(self, authenticated_client, aircraft_c172, document_registration):
        """Test getting document compliance."""
        url = reverse(
            'api:aircraft-document-compliance',
            kwargs={'aircraft_pk': aircraft_c172.id}
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'is_compliant' in response.data
        assert 'missing_documents' in response.data

    def test_expiring_documents(self, authenticated_client, aircraft_c172, document_insurance):
        """Test getting expiring documents."""
        # Set document to expire soon
        document_insurance.expiry_date = date.today() + timedelta(days=15)
        document_insurance.save()

        url = reverse(
            'api:aircraft-document-expiring',
            kwargs={'aircraft_pk': aircraft_c172.id}
        )
        response = authenticated_client.get(url, {'days': 30})

        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Counter API Tests
# =============================================================================

@pytest.mark.django_db
class TestCounterAPI:
    """Tests for Counter API endpoints."""

    def test_get_counters(self, authenticated_client, aircraft_c172):
        """Test getting counters."""
        url = reverse(
            'api:aircraft-counters-list',
            kwargs={'aircraft_pk': aircraft_c172.id}
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'hobbs_time' in response.data
        assert 'engines' in response.data

    def test_add_flight_time(self, authenticated_client, aircraft_c172):
        """Test adding flight time."""
        url = reverse(
            'api:aircraft-counters-flight',
            kwargs={'aircraft_pk': aircraft_c172.id}
        )
        data = {
            'flight_id': str(uuid.uuid4()),
            'hobbs_time': '1.5',
            'landings': 2,
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert 'time_log_id' in response.data

    def test_counter_adjustment(self, authenticated_client, aircraft_c172):
        """Test making counter adjustment."""
        url = reverse(
            'api:aircraft-counters-adjustment',
            kwargs={'aircraft_pk': aircraft_c172.id}
        )
        data = {
            'field': 'hobbs_time',
            'new_value': '1300.00',
            'reason': 'Hobbs meter replaced - adjusting to match new meter',
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['new_value'] == 1300.0

    def test_counter_logs(self, authenticated_client, aircraft_c172, time_log_flight):
        """Test getting counter logs."""
        url = reverse(
            'api:aircraft-counters-logs',
            kwargs={'aircraft_pk': aircraft_c172.id}
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'logs' in response.data

    def test_utilization_stats(self, authenticated_client, aircraft_c172):
        """Test getting utilization statistics."""
        url = reverse(
            'api:aircraft-counters-utilization',
            kwargs={'aircraft_pk': aircraft_c172.id}
        )
        response = authenticated_client.get(url, {'days': 30})

        assert response.status_code == status.HTTP_200_OK
        assert 'period' in response.data
        assert 'totals' in response.data


# =============================================================================
# Aircraft Type API Tests
# =============================================================================

@pytest.mark.django_db
class TestAircraftTypeAPI:
    """Tests for AircraftType API endpoints."""

    def test_list_aircraft_types(self, authenticated_client, aircraft_type_c172, aircraft_type_pa28):
        """Test listing aircraft types."""
        url = reverse('api:aircraft-type-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_retrieve_aircraft_type(self, authenticated_client, aircraft_type_c172):
        """Test retrieving aircraft type details."""
        url = reverse('api:aircraft-type-detail', kwargs={'pk': aircraft_type_c172.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['icao_code'] == 'C172'


# =============================================================================
# Engine API Tests
# =============================================================================

@pytest.mark.django_db
class TestEngineAPI:
    """Tests for Engine API endpoints."""

    def test_list_engines(self, authenticated_client, aircraft_c172, engine_single):
        """Test listing engines."""
        url = reverse(
            'api:aircraft-engines',
            kwargs={'pk': aircraft_c172.id}
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_add_engine(self, authenticated_client, aircraft_c172):
        """Test adding an engine."""
        url = reverse(
            'api:aircraft-engines',
            kwargs={'pk': aircraft_c172.id}
        )
        data = {
            'position': 1,
            'engine_type': 'piston',
            'manufacturer': 'Lycoming',
            'model': 'O-360',
            'serial_number': 'L-99999',
            'tsn': '500.0',
            'tso': '100.0',
            'tbo_hours': '2000',
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['manufacturer'] == 'Lycoming'
