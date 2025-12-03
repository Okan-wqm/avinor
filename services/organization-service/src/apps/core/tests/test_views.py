# services/organization-service/src/apps/core/tests/test_views.py
"""
API View Tests

Integration tests for Organization Service API endpoints.
"""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import (
    Organization,
    Location,
    OrganizationInvitation,
)


# =============================================================================
# Organization API Tests
# =============================================================================

@pytest.mark.django_db
class TestOrganizationAPI:
    """Tests for Organization API endpoints."""

    def test_list_organizations(self, authenticated_client, test_organization):
        """Test listing organizations."""
        response = authenticated_client.get('/api/v1/organizations/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        assert response.data['count'] >= 1

    def test_create_organization(self, authenticated_client, starter_plan):
        """Test creating an organization."""
        data = {
            'name': 'New Flight School',
            'email': 'new@flightschool.com',
            'country_code': 'US',
            'organization_type': 'flight_school',
        }

        response = authenticated_client.post('/api/v1/organizations/', data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'success'
        assert response.data['data']['name'] == 'New Flight School'

    def test_get_organization(self, authenticated_client, test_organization):
        """Test retrieving an organization."""
        response = authenticated_client.get(f'/api/v1/organizations/{test_organization.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['id'] == str(test_organization.id)
        assert response.data['data']['name'] == test_organization.name

    def test_update_organization(self, authenticated_client, test_organization):
        """Test updating an organization."""
        data = {
            'name': 'Updated School Name',
            'city': 'Los Angeles',
        }

        response = authenticated_client.put(
            f'/api/v1/organizations/{test_organization.id}/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['name'] == 'Updated School Name'
        assert response.data['data']['city'] == 'Los Angeles'

    def test_delete_organization(self, authenticated_client, test_organization):
        """Test deleting an organization."""
        response = authenticated_client.delete(f'/api/v1/organizations/{test_organization.id}/')

        assert response.status_code == status.HTTP_200_OK

        # Verify soft deleted
        test_organization.refresh_from_db()
        assert test_organization.deleted_at is not None

    def test_update_branding(self, authenticated_client, test_organization):
        """Test updating organization branding."""
        data = {
            'primary_color': '#FF5733',
            'logo_url': 'https://example.com/logo.png',
        }

        response = authenticated_client.put(
            f'/api/v1/organizations/{test_organization.id}/branding/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['primary_color'] == '#FF5733'

    def test_get_usage(self, authenticated_client, test_organization, primary_location):
        """Test getting organization usage statistics."""
        response = authenticated_client.get(
            f'/api/v1/organizations/{test_organization.id}/usage/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'locations' in response.data['data']

    def test_activate_organization(self, authenticated_client, inactive_organization):
        """Test activating an organization."""
        response = authenticated_client.post(
            f'/api/v1/organizations/{inactive_organization.id}/activate/'
        )

        assert response.status_code == status.HTTP_200_OK
        inactive_organization.refresh_from_db()
        assert inactive_organization.status == Organization.Status.ACTIVE

    def test_suspend_organization(self, authenticated_client, test_organization):
        """Test suspending an organization."""
        data = {'reason': 'Payment overdue'}

        response = authenticated_client.post(
            f'/api/v1/organizations/{test_organization.id}/suspend/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        test_organization.refresh_from_db()
        assert test_organization.status == Organization.Status.SUSPENDED


# =============================================================================
# Location API Tests
# =============================================================================

@pytest.mark.django_db
class TestLocationAPI:
    """Tests for Location API endpoints."""

    def test_list_locations(self, authenticated_client, test_organization, primary_location):
        """Test listing locations."""
        response = authenticated_client.get(
            f'/api/v1/organizations/{test_organization.id}/locations/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 1

    def test_create_location(self, authenticated_client, test_organization):
        """Test creating a location."""
        data = {
            'name': 'New Training Base',
            'code': 'NTB',
            'location_type': 'training',
            'airport_icao': 'KJFK',
            'city': 'New York',
            'country_code': 'US',
        }

        response = authenticated_client.post(
            f'/api/v1/organizations/{test_organization.id}/locations/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['name'] == 'New Training Base'

    def test_get_location(self, authenticated_client, test_organization, primary_location):
        """Test retrieving a location."""
        response = authenticated_client.get(
            f'/api/v1/organizations/{test_organization.id}/locations/{primary_location.id}/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['id'] == str(primary_location.id)

    def test_update_location(self, authenticated_client, test_organization, primary_location):
        """Test updating a location."""
        data = {
            'name': 'Updated Base Name',
            'elevation_ft': 100,
        }

        response = authenticated_client.put(
            f'/api/v1/organizations/{test_organization.id}/locations/{primary_location.id}/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['name'] == 'Updated Base Name'

    def test_set_primary_location(
        self, authenticated_client, test_organization, primary_location, secondary_location
    ):
        """Test setting a new primary location."""
        response = authenticated_client.put(
            f'/api/v1/organizations/{test_organization.id}/locations/{secondary_location.id}/primary/'
        )

        assert response.status_code == status.HTTP_200_OK
        secondary_location.refresh_from_db()
        assert secondary_location.is_primary is True

    def test_update_operating_hours(self, authenticated_client, test_organization, primary_location):
        """Test updating operating hours."""
        data = {
            'monday': {'open': '09:00', 'close': '17:00'},
            'saturday': {'closed': True},
        }

        response = authenticated_client.put(
            f'/api/v1/organizations/{test_organization.id}/locations/{primary_location.id}/operating-hours/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

    def test_update_facilities(self, authenticated_client, test_organization, primary_location):
        """Test updating facilities."""
        data = {
            'facilities': ['hangar', 'briefing_room', 'simulator', 'cafe'],
        }

        response = authenticated_client.put(
            f'/api/v1/organizations/{test_organization.id}/locations/{primary_location.id}/facilities/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

    def test_delete_location(
        self, authenticated_client, test_organization, secondary_location
    ):
        """Test deleting a location."""
        response = authenticated_client.delete(
            f'/api/v1/organizations/{test_organization.id}/locations/{secondary_location.id}/'
        )

        assert response.status_code == status.HTTP_200_OK
        secondary_location.refresh_from_db()
        assert secondary_location.deleted_at is not None


# =============================================================================
# Subscription API Tests
# =============================================================================

@pytest.mark.django_db
class TestSubscriptionAPI:
    """Tests for Subscription API endpoints."""

    def test_list_plans(self, api_client, all_plans):
        """Test listing subscription plans (public endpoint)."""
        response = api_client.get('/api/v1/subscription-plans/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 1

    def test_get_plan(self, api_client, starter_plan):
        """Test getting a subscription plan."""
        response = api_client.get(f'/api/v1/subscription-plans/{starter_plan.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['code'] == 'starter'

    def test_compare_plans(self, api_client, all_plans):
        """Test comparing subscription plans."""
        response = api_client.get('/api/v1/subscription-plans/compare/')

        assert response.status_code == status.HTTP_200_OK
        assert 'plans' in response.data['data']
        assert 'features' in response.data['data']

    def test_get_subscription_status(self, authenticated_client, test_organization):
        """Test getting subscription status."""
        response = authenticated_client.get(
            f'/api/v1/organizations/{test_organization.id}/subscription/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['organization_id'] == str(test_organization.id)

    def test_change_plan(self, authenticated_client, test_organization, professional_plan):
        """Test changing subscription plan."""
        data = {
            'plan_code': 'professional',
            'billing_cycle': 'monthly',
        }

        response = authenticated_client.post(
            f'/api/v1/organizations/{test_organization.id}/subscription/change/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_subscription_history(self, authenticated_client, test_organization):
        """Test getting subscription history."""
        response = authenticated_client.get(
            f'/api/v1/organizations/{test_organization.id}/subscription/history/'
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_limits(self, authenticated_client, test_organization):
        """Test getting subscription limits."""
        response = authenticated_client.get(
            f'/api/v1/organizations/{test_organization.id}/subscription/limits/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'max_users' in response.data['data']


# =============================================================================
# Invitation API Tests
# =============================================================================

@pytest.mark.django_db
class TestInvitationAPI:
    """Tests for Invitation API endpoints."""

    def test_list_invitations(self, authenticated_client, test_organization, pending_invitation):
        """Test listing invitations."""
        response = authenticated_client.get(
            f'/api/v1/organizations/{test_organization.id}/invitations/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 1

    def test_create_invitation(self, authenticated_client, test_organization):
        """Test creating an invitation."""
        data = {
            'email': 'newinvite@example.com',
            'role_code': 'instructor',
            'message': 'Welcome to our flight school!',
            'expires_in_days': 7,
        }

        response = authenticated_client.post(
            f'/api/v1/organizations/{test_organization.id}/invitations/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['email'] == 'newinvite@example.com'

    def test_bulk_create_invitations(self, authenticated_client, test_organization):
        """Test bulk creating invitations."""
        data = {
            'emails': [
                'bulk1@example.com',
                'bulk2@example.com',
                'bulk3@example.com',
            ],
            'role_code': 'student',
        }

        response = authenticated_client.post(
            f'/api/v1/organizations/{test_organization.id}/invitations/bulk/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['created'] == 3

    def test_get_invitation(self, authenticated_client, test_organization, pending_invitation):
        """Test retrieving an invitation."""
        response = authenticated_client.get(
            f'/api/v1/organizations/{test_organization.id}/invitations/{pending_invitation.id}/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['id'] == str(pending_invitation.id)

    def test_cancel_invitation(self, authenticated_client, test_organization, pending_invitation):
        """Test cancelling an invitation."""
        response = authenticated_client.delete(
            f'/api/v1/organizations/{test_organization.id}/invitations/{pending_invitation.id}/'
        )

        assert response.status_code == status.HTTP_200_OK
        pending_invitation.refresh_from_db()
        assert pending_invitation.status == 'cancelled'

    def test_resend_invitation(self, authenticated_client, test_organization, pending_invitation):
        """Test resending an invitation."""
        response = authenticated_client.post(
            f'/api/v1/organizations/{test_organization.id}/invitations/{pending_invitation.id}/resend/'
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_statistics(self, authenticated_client, test_organization, pending_invitation):
        """Test getting invitation statistics."""
        response = authenticated_client.get(
            f'/api/v1/organizations/{test_organization.id}/invitations/statistics/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'pending' in response.data['data']
        assert 'total' in response.data['data']

    def test_validate_token_public(self, api_client, pending_invitation):
        """Test validating invitation token (public endpoint)."""
        response = api_client.get(
            f'/api/v1/invitations/validate/{pending_invitation.token}/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['valid'] is True
        assert response.data['data']['email'] == pending_invitation.email

    def test_validate_invalid_token(self, api_client):
        """Test validating invalid token."""
        response = api_client.get('/api/v1/invitations/validate/invalid_token_here/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_accept_invitation(self, api_client, pending_invitation):
        """Test accepting an invitation."""
        user_id = str(uuid.uuid4())
        data = {
            'token': pending_invitation.token,
            'user_id': user_id,
        }

        response = api_client.post('/api/v1/invitations/accept/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        pending_invitation.refresh_from_db()
        assert pending_invitation.status == 'accepted'

    def test_accept_expired_invitation(self, api_client, expired_invitation):
        """Test accepting expired invitation fails."""
        data = {
            'token': expired_invitation.token,
            'user_id': str(uuid.uuid4()),
        }

        response = api_client.post('/api/v1/invitations/accept/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Settings API Tests
# =============================================================================

@pytest.mark.django_db
class TestOrganizationSettingsAPI:
    """Tests for Organization Settings API endpoints."""

    def test_list_settings(self, authenticated_client, test_organization, organization_settings):
        """Test listing organization settings."""
        response = authenticated_client.get(
            f'/api/v1/organizations/{test_organization.id}/settings/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'notifications' in response.data['data'] or response.data['count'] >= 0

    def test_create_setting(self, authenticated_client, test_organization):
        """Test creating a setting."""
        data = {
            'category': 'billing',
            'key': 'auto_invoice',
            'value': True,
        }

        response = authenticated_client.post(
            f'/api/v1/organizations/{test_organization.id}/settings/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_filter_settings_by_category(
        self, authenticated_client, test_organization, organization_settings
    ):
        """Test filtering settings by category."""
        response = authenticated_client.get(
            f'/api/v1/organizations/{test_organization.id}/settings/?category=notifications'
        )

        assert response.status_code == status.HTTP_200_OK
