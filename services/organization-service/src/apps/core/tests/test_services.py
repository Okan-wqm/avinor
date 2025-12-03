# services/organization-service/src/apps/core/tests/test_services.py
"""
Service Layer Tests

Unit tests for Organization Service business logic.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.utils import timezone

from apps.core.models import (
    Organization,
    Location,
    SubscriptionPlan,
    OrganizationInvitation,
)
from apps.core.services import (
    OrganizationService,
    LocationService,
    SubscriptionService,
    InvitationService,
    OrganizationError,
    LocationError,
    SubscriptionError,
    InvitationError,
)


# =============================================================================
# Organization Service Tests
# =============================================================================

@pytest.mark.django_db
class TestOrganizationService:
    """Tests for OrganizationService."""

    @pytest.fixture
    def service(self):
        return OrganizationService()

    def test_create_organization(self, service, starter_plan, test_user):
        """Test creating an organization."""
        org = service.create_organization(
            name='New Flight School',
            email='new@flight.com',
            country_code='US',
            organization_type='flight_school',
            created_by_user_id=test_user.id,
        )

        assert org.name == 'New Flight School'
        assert org.email == 'new@flight.com'
        assert org.slug is not None
        assert 'new-flight-school' in org.slug

    def test_create_organization_generates_unique_slug(self, service, test_organization, starter_plan, test_user):
        """Test that duplicate names generate unique slugs."""
        org = service.create_organization(
            name=test_organization.name,  # Same name
            email='different@flight.com',
            country_code='US',
            created_by_user_id=test_user.id,
        )

        assert org.slug != test_organization.slug
        assert test_organization.name.lower().replace(' ', '-') in org.slug

    def test_get_organization(self, service, test_organization):
        """Test retrieving an organization."""
        org = service.get_organization(str(test_organization.id))
        assert org.id == test_organization.id

    def test_get_organization_not_found(self, service):
        """Test retrieving non-existent organization."""
        org = service.get_organization(str(uuid.uuid4()))
        assert org is None

    def test_get_organization_by_slug(self, service, test_organization):
        """Test retrieving organization by slug."""
        org = service.get_organization_by_slug(test_organization.slug)
        assert org.id == test_organization.id

    def test_update_organization(self, service, test_organization, test_user):
        """Test updating an organization."""
        org = service.update_organization(
            organization_id=str(test_organization.id),
            updated_by_user_id=test_user.id,
            name='Updated Name',
            city='Los Angeles',
        )

        assert org.name == 'Updated Name'
        assert org.city == 'Los Angeles'

    def test_update_branding(self, service, test_organization, test_user):
        """Test updating organization branding."""
        org = service.update_branding(
            organization_id=str(test_organization.id),
            updated_by_user_id=test_user.id,
            primary_color='#FF5733',
            logo_url='https://example.com/logo.png',
        )

        assert org.primary_color == '#FF5733'
        assert org.logo_url == 'https://example.com/logo.png'

    def test_delete_organization(self, service, test_organization, test_user):
        """Test soft deleting an organization."""
        service.delete_organization(
            organization_id=str(test_organization.id),
            deleted_by_user_id=test_user.id,
        )

        # Should be soft deleted
        org = Organization.objects.get(id=test_organization.id)
        assert org.deleted_at is not None
        assert org.status == Organization.Status.DELETED

    def test_get_usage_statistics(self, service, test_organization, primary_location):
        """Test getting usage statistics."""
        usage = service.get_usage_statistics(str(test_organization.id))

        assert 'users' in usage
        assert 'locations' in usage
        assert usage['locations']['current'] >= 1  # At least one location

    def test_setup_custom_domain(self, service, test_organization):
        """Test setting up custom domain."""
        result = service.setup_custom_domain(
            organization_id=str(test_organization.id),
            domain='custom.flightschool.com'
        )

        assert 'dns_records' in result
        test_organization.refresh_from_db()
        assert test_organization.custom_domain == 'custom.flightschool.com'


# =============================================================================
# Location Service Tests
# =============================================================================

@pytest.mark.django_db
class TestLocationService:
    """Tests for LocationService."""

    @pytest.fixture
    def service(self):
        return LocationService()

    def test_create_location(self, service, test_organization, test_user):
        """Test creating a location."""
        location = service.create_location(
            organization_id=str(test_organization.id),
            name='New Base',
            code='NB01',
            location_type='base',
            created_by_user_id=test_user.id,
        )

        assert location.name == 'New Base'
        assert location.code == 'NB01'
        assert location.organization == test_organization

    def test_create_location_exceeds_limit(self, service, test_organization, test_user, create_location):
        """Test location limit enforcement."""
        test_organization.max_locations = 2
        test_organization.save()

        # Create locations up to limit
        create_location(test_organization, name='Location 1')
        create_location(test_organization, name='Location 2')

        # Should fail on third
        with pytest.raises(LocationError, match='limit'):
            service.create_location(
                organization_id=str(test_organization.id),
                name='Location 3',
                created_by_user_id=test_user.id,
            )

    def test_get_location(self, service, primary_location, test_organization):
        """Test retrieving a location."""
        location = service.get_location(
            str(primary_location.id),
            str(test_organization.id)
        )
        assert location.id == primary_location.id

    def test_update_location(self, service, primary_location, test_organization, test_user):
        """Test updating a location."""
        location = service.update_location(
            location_id=str(primary_location.id),
            organization_id=str(test_organization.id),
            updated_by_user_id=test_user.id,
            name='Updated Base Name',
        )

        assert location.name == 'Updated Base Name'

    def test_set_primary_location(self, service, primary_location, secondary_location, test_organization):
        """Test setting a new primary location."""
        # Secondary becomes primary
        location = service.set_primary_location(
            location_id=str(secondary_location.id),
            organization_id=str(test_organization.id)
        )

        assert location.is_primary is True

        # Old primary should no longer be primary
        primary_location.refresh_from_db()
        assert primary_location.is_primary is False

    def test_update_operating_hours(self, service, primary_location, test_organization):
        """Test updating operating hours."""
        hours = {
            'monday': {'open': '09:00', 'close': '17:00'},
            'saturday': {'closed': True},
        }

        location = service.update_operating_hours(
            location_id=str(primary_location.id),
            organization_id=str(test_organization.id),
            operating_hours=hours
        )

        assert location.operating_hours['monday']['open'] == '09:00'
        assert location.operating_hours['saturday']['closed'] is True

    def test_delete_location(self, service, secondary_location, test_organization, test_user):
        """Test deleting a location."""
        service.delete_location(
            location_id=str(secondary_location.id),
            organization_id=str(test_organization.id),
            deleted_by_user_id=test_user.id
        )

        secondary_location.refresh_from_db()
        assert secondary_location.deleted_at is not None

    def test_cannot_delete_primary_location(self, service, primary_location, test_organization, test_user):
        """Test that primary location cannot be deleted."""
        with pytest.raises(LocationError, match='primary'):
            service.delete_location(
                location_id=str(primary_location.id),
                organization_id=str(test_organization.id),
                deleted_by_user_id=test_user.id
            )


# =============================================================================
# Subscription Service Tests
# =============================================================================

@pytest.mark.django_db
class TestSubscriptionService:
    """Tests for SubscriptionService."""

    @pytest.fixture
    def service(self):
        return SubscriptionService()

    def test_get_subscription_status(self, service, test_organization):
        """Test getting subscription status."""
        status = service.get_subscription_status(str(test_organization.id))

        assert status['organization_id'] == str(test_organization.id)
        assert 'plan' in status
        assert 'limits' in status
        assert 'is_active' in status

    def test_change_plan_upgrade(self, service, test_organization, professional_plan, test_user):
        """Test upgrading subscription plan."""
        result = service.change_plan(
            organization_id=str(test_organization.id),
            plan_code='professional',
            billing_cycle='monthly',
            changed_by_user_id=test_user.id,
        )

        assert result['new_plan'] == 'professional'
        test_organization.refresh_from_db()
        assert test_organization.subscription_plan == professional_plan

    def test_change_plan_downgrade_with_limit_check(
        self, service, test_organization, free_plan, test_user, create_location
    ):
        """Test downgrade fails if exceeds new plan limits."""
        # Create locations that exceed free plan limit
        test_organization.max_locations = 10
        test_organization.save()

        create_location(test_organization, name='Loc 1')
        create_location(test_organization, name='Loc 2')
        create_location(test_organization, name='Loc 3')

        # Free plan only allows 1 location
        with pytest.raises(SubscriptionError, match='exceeds'):
            service.change_plan(
                organization_id=str(test_organization.id),
                plan_code='free',
                changed_by_user_id=test_user.id,
            )

    def test_start_trial(self, service, test_organization, professional_plan, all_plans):
        """Test starting a trial."""
        # Reset to no plan
        test_organization.subscription_plan = None
        test_organization.subscription_status = 'inactive'
        test_organization.save()

        result = service.start_trial(
            organization_id=str(test_organization.id),
            plan_code='professional',
            trial_days=14
        )

        test_organization.refresh_from_db()
        assert test_organization.subscription_status == 'trialing'
        assert test_organization.trial_ends_at is not None

    def test_extend_trial(self, service, trial_organization):
        """Test extending trial period."""
        original_end = trial_organization.trial_ends_at

        result = service.extend_trial(
            organization_id=str(trial_organization.id),
            days=7
        )

        trial_organization.refresh_from_db()
        expected = original_end + timedelta(days=7)
        diff = abs((trial_organization.trial_ends_at - expected).total_seconds())
        assert diff < 1

    def test_cancel_subscription(self, service, test_organization, test_user):
        """Test cancelling subscription."""
        result = service.cancel_subscription(
            organization_id=str(test_organization.id),
            reason='Too expensive',
            cancelled_by_user_id=test_user.id,
        )

        test_organization.refresh_from_db()
        assert test_organization.subscription_status == 'cancelled'

    def test_get_subscription_limits(self, service, test_organization):
        """Test getting subscription limits."""
        limits = service.get_subscription_limits(str(test_organization.id))

        assert 'max_users' in limits
        assert 'max_aircraft' in limits
        assert 'max_locations' in limits


# =============================================================================
# Invitation Service Tests
# =============================================================================

@pytest.mark.django_db
class TestInvitationService:
    """Tests for InvitationService."""

    @pytest.fixture
    def service(self):
        return InvitationService()

    def test_create_invitation(self, service, test_organization, test_user):
        """Test creating an invitation."""
        invitation = service.create_invitation(
            organization_id=str(test_organization.id),
            email='newmember@example.com',
            role_code='instructor',
            invited_by_user_id=test_user.id,
            invited_by_email=test_user.email,
        )

        assert invitation.email == 'newmember@example.com'
        assert invitation.role_code == 'instructor'
        assert invitation.status == 'pending'
        assert len(invitation.token) == 64

    def test_create_invitation_duplicate_email(self, service, pending_invitation, test_organization, test_user):
        """Test creating duplicate invitation fails."""
        with pytest.raises(InvitationError, match='already'):
            service.create_invitation(
                organization_id=str(test_organization.id),
                email=pending_invitation.email,
                invited_by_user_id=test_user.id,
            )

    def test_bulk_create_invitations(self, service, test_organization, test_user):
        """Test bulk creating invitations."""
        emails = [
            'user1@example.com',
            'user2@example.com',
            'user3@example.com',
        ]

        result = service.bulk_create_invitations(
            organization_id=str(test_organization.id),
            emails=emails,
            role_code='student',
            invited_by_user_id=test_user.id,
        )

        assert result['created'] == 3
        assert len(result['invitations']) == 3

    def test_accept_invitation(self, service, pending_invitation):
        """Test accepting an invitation."""
        user_id = str(uuid.uuid4())

        result = service.accept_invitation(
            token=pending_invitation.token,
            accepted_by_user_id=user_id
        )

        pending_invitation.refresh_from_db()
        assert pending_invitation.status == 'accepted'
        assert pending_invitation.accepted_by_user_id == user_id

    def test_accept_expired_invitation(self, service, expired_invitation):
        """Test accepting expired invitation fails."""
        user_id = str(uuid.uuid4())

        with pytest.raises(InvitationError, match='expired'):
            service.accept_invitation(
                token=expired_invitation.token,
                accepted_by_user_id=user_id
            )

    def test_cancel_invitation(self, service, pending_invitation, test_organization, test_user):
        """Test cancelling an invitation."""
        service.cancel_invitation(
            invitation_id=str(pending_invitation.id),
            organization_id=str(test_organization.id),
            cancelled_by_user_id=test_user.id,
        )

        pending_invitation.refresh_from_db()
        assert pending_invitation.status == 'cancelled'

    def test_resend_invitation(self, service, pending_invitation, test_organization):
        """Test resending an invitation."""
        original_sent_count = pending_invitation.sent_count or 0

        invitation = service.resend_invitation(
            invitation_id=str(pending_invitation.id),
            organization_id=str(test_organization.id),
        )

        assert invitation.sent_count == original_sent_count + 1

    def test_get_invitation_statistics(self, service, test_organization, pending_invitation, create_invitation):
        """Test getting invitation statistics."""
        # Create additional invitations
        accepted = create_invitation(test_organization, email='accepted@test.com')
        accepted.status = 'accepted'
        accepted.save()

        stats = service.get_invitation_statistics(str(test_organization.id))

        assert stats['pending'] >= 1
        assert stats['accepted'] >= 1
        assert stats['total'] >= 2

    def test_cleanup_expired_invitations(self, service, expired_invitation, test_organization):
        """Test cleaning up expired invitations."""
        count = service.cleanup_expired_invitations(str(test_organization.id))

        assert count >= 1
        expired_invitation.refresh_from_db()
        assert expired_invitation.status == 'expired'
