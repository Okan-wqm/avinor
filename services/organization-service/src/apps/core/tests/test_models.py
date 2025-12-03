# services/organization-service/src/apps/core/tests/test_models.py
"""
Model Tests

Unit tests for Organization Service models.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.core.models import (
    Organization,
    OrganizationSetting,
    Location,
    SubscriptionPlan,
    SubscriptionHistory,
    OrganizationInvitation,
)


# =============================================================================
# Organization Model Tests
# =============================================================================

@pytest.mark.django_db
class TestOrganizationModel:
    """Tests for Organization model."""

    def test_create_organization(self, starter_plan, test_user):
        """Test creating a basic organization."""
        org = Organization.objects.create(
            name='Test Flight School',
            slug='test-flight-school',
            email='test@example.com',
            country_code='US',
            subscription_plan=starter_plan,
            created_by=test_user.id,
        )

        assert org.id is not None
        assert org.name == 'Test Flight School'
        assert org.slug == 'test-flight-school'
        assert org.status == Organization.Status.PENDING
        assert org.subscription_status == Organization.SubscriptionStatus.INACTIVE

    def test_organization_slug_unique(self, test_organization, starter_plan, test_user):
        """Test that organization slug must be unique."""
        with pytest.raises(IntegrityError):
            Organization.objects.create(
                name='Another School',
                slug=test_organization.slug,  # Duplicate slug
                email='another@example.com',
                country_code='US',
                subscription_plan=starter_plan,
                created_by=test_user.id,
            )

    def test_full_address_property(self, test_organization):
        """Test full_address computed property."""
        test_organization.address_line1 = '123 Aviation Way'
        test_organization.city = 'New York'
        test_organization.state_province = 'NY'
        test_organization.postal_code = '10001'
        test_organization.country_code = 'US'
        test_organization.save()

        expected = '123 Aviation Way, New York, NY 10001, US'
        assert test_organization.full_address == expected

    def test_is_trial_expired(self, trial_organization):
        """Test is_trial_expired property."""
        # Trial not expired
        trial_organization.trial_ends_at = timezone.now() + timedelta(days=7)
        trial_organization.save()
        assert not trial_organization.is_trial_expired

        # Trial expired
        trial_organization.trial_ends_at = timezone.now() - timedelta(days=1)
        trial_organization.save()
        assert trial_organization.is_trial_expired

    def test_days_until_trial_end(self, trial_organization):
        """Test days_until_trial_end property."""
        trial_organization.trial_ends_at = timezone.now() + timedelta(days=10)
        trial_organization.save()

        # Should be approximately 10 days
        days = trial_organization.days_until_trial_end
        assert days >= 9 and days <= 10

    def test_has_feature(self, test_organization):
        """Test has_feature method."""
        test_organization.features = {
            'scheduling': True,
            'reporting': False,
        }
        test_organization.save()

        assert test_organization.has_feature('scheduling') is True
        assert test_organization.has_feature('reporting') is False
        assert test_organization.has_feature('nonexistent') is False

    def test_can_add_user(self, test_organization):
        """Test can_add_user limit checking."""
        test_organization.max_users = 5
        test_organization.save()

        # Should be able to add (assuming 0 current users)
        assert test_organization.can_add_user(current_count=4) is True
        assert test_organization.can_add_user(current_count=5) is False
        assert test_organization.can_add_user(current_count=10) is False

        # Unlimited users
        test_organization.max_users = None
        test_organization.save()
        assert test_organization.can_add_user(current_count=1000) is True

    def test_soft_delete(self, test_organization):
        """Test soft delete functionality."""
        org_id = test_organization.id
        test_organization.soft_delete()

        # Should not appear in default queryset
        assert Organization.objects.filter(id=org_id, deleted_at__isnull=True).count() == 0

        # Should still exist in database
        assert Organization.objects.filter(id=org_id).count() == 1


# =============================================================================
# Location Model Tests
# =============================================================================

@pytest.mark.django_db
class TestLocationModel:
    """Tests for Location model."""

    def test_create_location(self, test_organization, test_user):
        """Test creating a location."""
        location = Location.objects.create(
            organization=test_organization,
            name='Main Base',
            code='MAIN',
            location_type='base',
            is_primary=True,
            created_by=test_user.id,
        )

        assert location.id is not None
        assert location.organization == test_organization
        assert location.is_primary is True

    def test_coordinates_property(self, primary_location):
        """Test coordinates computed property."""
        coords = primary_location.coordinates
        assert 'latitude' in coords
        assert 'longitude' in coords
        assert coords['latitude'] == float(primary_location.latitude)

    def test_effective_timezone(self, primary_location, test_organization):
        """Test effective_timezone property."""
        # Location has timezone
        primary_location.timezone = 'America/Chicago'
        primary_location.save()
        assert primary_location.effective_timezone == 'America/Chicago'

        # Location inherits from organization
        primary_location.timezone = None
        primary_location.save()
        assert primary_location.effective_timezone == test_organization.timezone

    def test_has_facility(self, primary_location):
        """Test has_facility method."""
        primary_location.facilities = ['hangar', 'briefing_room', 'fuel']
        primary_location.save()

        assert primary_location.has_facility('hangar') is True
        assert primary_location.has_facility('restaurant') is False

    def test_unique_code_per_organization(self, test_organization, primary_location, test_user):
        """Test that location code is unique per organization."""
        with pytest.raises(IntegrityError):
            Location.objects.create(
                organization=test_organization,
                name='Another Location',
                code=primary_location.code,  # Duplicate code
                created_by=test_user.id,
            )


# =============================================================================
# Subscription Plan Model Tests
# =============================================================================

@pytest.mark.django_db
class TestSubscriptionPlanModel:
    """Tests for SubscriptionPlan model."""

    def test_yearly_savings(self, starter_plan):
        """Test yearly_savings computed property."""
        # Monthly price * 12 - yearly price
        expected = (starter_plan.price_monthly * 12) - starter_plan.price_yearly
        assert starter_plan.yearly_savings == expected

    def test_yearly_discount_percent(self, starter_plan):
        """Test yearly_discount_percent computed property."""
        monthly_annual = starter_plan.price_monthly * 12
        if monthly_annual > 0:
            expected = ((monthly_annual - starter_plan.price_yearly) / monthly_annual) * 100
            assert abs(starter_plan.yearly_discount_percent - expected) < 0.01

    def test_get_limit(self, starter_plan):
        """Test get_limit method."""
        assert starter_plan.get_limit('max_users') == starter_plan.max_users
        assert starter_plan.get_limit('max_aircraft') == starter_plan.max_aircraft
        assert starter_plan.get_limit('nonexistent') is None

    def test_unique_code(self, starter_plan):
        """Test that plan code must be unique."""
        with pytest.raises(IntegrityError):
            SubscriptionPlan.objects.create(
                code=starter_plan.code,  # Duplicate code
                name='Duplicate Plan',
                price_monthly=Decimal('99.00'),
                price_yearly=Decimal('990.00'),
            )


# =============================================================================
# Organization Invitation Model Tests
# =============================================================================

@pytest.mark.django_db
class TestOrganizationInvitationModel:
    """Tests for OrganizationInvitation model."""

    def test_create_invitation(self, test_organization, test_user):
        """Test creating an invitation."""
        invitation = OrganizationInvitation.objects.create(
            organization=test_organization,
            email='newuser@example.com',
            role_code='instructor',
            token=OrganizationInvitation.generate_token(),
            expires_at=timezone.now() + timedelta(days=7),
            invited_by=test_user.id,
        )

        assert invitation.id is not None
        assert invitation.status == OrganizationInvitation.Status.PENDING
        assert len(invitation.token) == 64

    def test_is_expired_property(self, pending_invitation):
        """Test is_expired computed property."""
        # Not expired
        pending_invitation.expires_at = timezone.now() + timedelta(days=7)
        pending_invitation.save()
        assert pending_invitation.is_expired is False

        # Expired
        pending_invitation.expires_at = timezone.now() - timedelta(days=1)
        pending_invitation.save()
        assert pending_invitation.is_expired is True

    def test_is_pending_property(self, pending_invitation):
        """Test is_pending computed property."""
        # Pending and not expired
        pending_invitation.status = OrganizationInvitation.Status.PENDING
        pending_invitation.expires_at = timezone.now() + timedelta(days=7)
        pending_invitation.save()
        assert pending_invitation.is_pending is True

        # Accepted
        pending_invitation.status = OrganizationInvitation.Status.ACCEPTED
        pending_invitation.save()
        assert pending_invitation.is_pending is False

    def test_days_until_expiry(self, pending_invitation):
        """Test days_until_expiry property."""
        pending_invitation.expires_at = timezone.now() + timedelta(days=5)
        pending_invitation.save()

        days = pending_invitation.days_until_expiry
        assert days >= 4 and days <= 5

    def test_accept_invitation(self, pending_invitation, test_user):
        """Test accepting an invitation."""
        user_id = str(uuid.uuid4())
        pending_invitation.accept(user_id)

        assert pending_invitation.status == OrganizationInvitation.Status.ACCEPTED
        assert pending_invitation.accepted_by_user_id == user_id
        assert pending_invitation.accepted_at is not None

    def test_cancel_invitation(self, pending_invitation):
        """Test cancelling an invitation."""
        pending_invitation.cancel()

        assert pending_invitation.status == OrganizationInvitation.Status.CANCELLED

    def test_revoke_invitation(self, pending_invitation):
        """Test revoking an invitation."""
        pending_invitation.revoke()

        assert pending_invitation.status == OrganizationInvitation.Status.REVOKED

    def test_extend_expiry(self, pending_invitation):
        """Test extending invitation expiry."""
        original_expiry = pending_invitation.expires_at
        pending_invitation.extend_expiry(days=7)

        assert pending_invitation.expires_at > original_expiry
        expected = original_expiry + timedelta(days=7)
        diff = abs((pending_invitation.expires_at - expected).total_seconds())
        assert diff < 1  # Within 1 second

    def test_generate_token(self):
        """Test token generation."""
        token1 = OrganizationInvitation.generate_token()
        token2 = OrganizationInvitation.generate_token()

        assert len(token1) == 64
        assert len(token2) == 64
        assert token1 != token2  # Should be unique

    def test_unique_pending_email(self, pending_invitation, test_organization, test_user):
        """Test that pending invitations have unique email per organization."""
        # Should raise error for duplicate pending invitation
        with pytest.raises(IntegrityError):
            OrganizationInvitation.objects.create(
                organization=test_organization,
                email=pending_invitation.email,  # Same email
                status=OrganizationInvitation.Status.PENDING,
                token=OrganizationInvitation.generate_token(),
                expires_at=timezone.now() + timedelta(days=7),
                invited_by=test_user.id,
            )


# =============================================================================
# Organization Setting Model Tests
# =============================================================================

@pytest.mark.django_db
class TestOrganizationSettingModel:
    """Tests for OrganizationSetting model."""

    def test_create_setting(self, test_organization):
        """Test creating a setting."""
        setting = OrganizationSetting.objects.create(
            organization=test_organization,
            category='notifications',
            key='email_enabled',
            value=True,
        )

        assert setting.id is not None
        assert setting.value is True

    def test_get_display_value(self, test_organization):
        """Test get_display_value method."""
        # Non-secret value
        setting = OrganizationSetting.objects.create(
            organization=test_organization,
            category='test',
            key='public_key',
            value='visible_value',
            is_secret=False,
        )
        assert setting.get_display_value() == 'visible_value'

        # Secret value
        secret_setting = OrganizationSetting.objects.create(
            organization=test_organization,
            category='test',
            key='api_key',
            value='secret_api_key_123',
            is_secret=True,
        )
        assert secret_setting.get_display_value() == '***'

    def test_unique_category_key_per_organization(self, test_organization):
        """Test unique constraint on category/key per organization."""
        OrganizationSetting.objects.create(
            organization=test_organization,
            category='billing',
            key='auto_charge',
            value=True,
        )

        with pytest.raises(IntegrityError):
            OrganizationSetting.objects.create(
                organization=test_organization,
                category='billing',
                key='auto_charge',  # Duplicate category/key
                value=False,
            )


# =============================================================================
# Subscription History Model Tests
# =============================================================================

@pytest.mark.django_db
class TestSubscriptionHistoryModel:
    """Tests for SubscriptionHistory model."""

    def test_log_change(self, test_organization, starter_plan, professional_plan, test_user):
        """Test logging subscription change."""
        history = SubscriptionHistory.log_change(
            organization=test_organization,
            change_type='upgrade',
            from_plan=starter_plan,
            to_plan=professional_plan,
            reason='Upgrading to professional',
            amount=professional_plan.price_monthly,
            currency='USD',
            created_by=test_user.id,
        )

        assert history.id is not None
        assert history.change_type == 'upgrade'
        assert history.from_plan == starter_plan
        assert history.to_plan == professional_plan
        assert history.amount == professional_plan.price_monthly
