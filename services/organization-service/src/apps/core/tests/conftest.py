# services/organization-service/src/apps/core/tests/conftest.py
"""
Pytest Configuration and Fixtures

Provides common fixtures for Organization Service tests.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any

import pytest
from django.test import Client
from rest_framework.test import APIClient

from apps.core.models import (
    Organization,
    OrganizationSetting,
    Location,
    SubscriptionPlan,
    SubscriptionHistory,
    OrganizationInvitation,
)


# =============================================================================
# API Client Fixtures
# =============================================================================

@pytest.fixture
def api_client():
    """Return DRF API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, test_user):
    """Return authenticated API client."""
    api_client.force_authenticate(user=test_user)
    return api_client


# =============================================================================
# User Fixtures
# =============================================================================

class MockUser:
    """Mock user object for testing."""

    def __init__(self, user_id: str = None, email: str = None, is_authenticated: bool = True):
        self.id = user_id or str(uuid.uuid4())
        self.email = email or f"user-{self.id[:8]}@test.com"
        self.is_authenticated = is_authenticated


@pytest.fixture
def test_user():
    """Create mock test user."""
    return MockUser(
        user_id=str(uuid.uuid4()),
        email='testuser@example.com'
    )


@pytest.fixture
def admin_user():
    """Create mock admin user."""
    return MockUser(
        user_id=str(uuid.uuid4()),
        email='admin@example.com'
    )


# =============================================================================
# Subscription Plan Fixtures
# =============================================================================

@pytest.fixture
def free_plan(db):
    """Create free subscription plan."""
    return SubscriptionPlan.objects.create(
        code='free',
        name='Free Plan',
        description='Basic free tier',
        price_monthly=Decimal('0.00'),
        price_yearly=Decimal('0.00'),
        max_users=3,
        max_aircraft=1,
        max_students=5,
        max_locations=1,
        storage_limit_gb=1,
        features={'basic_scheduling': True},
        trial_days=0,
        is_active=True,
        is_public=True,
        display_order=1,
    )


@pytest.fixture
def starter_plan(db):
    """Create starter subscription plan."""
    return SubscriptionPlan.objects.create(
        code='starter',
        name='Starter Plan',
        description='For small flight schools',
        price_monthly=Decimal('49.00'),
        price_yearly=Decimal('490.00'),
        max_users=10,
        max_aircraft=5,
        max_students=25,
        max_locations=2,
        storage_limit_gb=10,
        features={
            'basic_scheduling': True,
            'student_management': True,
            'aircraft_management': True,
        },
        trial_days=14,
        badge_text='Popular',
        badge_color='#3B82F6',
        is_active=True,
        is_public=True,
        display_order=2,
    )


@pytest.fixture
def professional_plan(db):
    """Create professional subscription plan."""
    return SubscriptionPlan.objects.create(
        code='professional',
        name='Professional Plan',
        description='For growing organizations',
        price_monthly=Decimal('149.00'),
        price_yearly=Decimal('1490.00'),
        max_users=50,
        max_aircraft=20,
        max_students=100,
        max_locations=5,
        storage_limit_gb=50,
        features={
            'basic_scheduling': True,
            'student_management': True,
            'aircraft_management': True,
            'advanced_reporting': True,
            'api_access': True,
        },
        trial_days=14,
        is_active=True,
        is_public=True,
        display_order=3,
    )


@pytest.fixture
def enterprise_plan(db):
    """Create enterprise subscription plan."""
    return SubscriptionPlan.objects.create(
        code='enterprise',
        name='Enterprise Plan',
        description='For large organizations',
        price_monthly=Decimal('499.00'),
        price_yearly=Decimal('4990.00'),
        max_users=None,  # Unlimited
        max_aircraft=None,
        max_students=None,
        max_locations=None,
        storage_limit_gb=500,
        features={
            'basic_scheduling': True,
            'student_management': True,
            'aircraft_management': True,
            'advanced_reporting': True,
            'api_access': True,
            'white_label': True,
            'custom_integrations': True,
            'priority_support': True,
        },
        trial_days=30,
        badge_text='Best Value',
        badge_color='#10B981',
        is_active=True,
        is_public=True,
        display_order=4,
    )


@pytest.fixture
def all_plans(free_plan, starter_plan, professional_plan, enterprise_plan):
    """Return all subscription plans."""
    return {
        'free': free_plan,
        'starter': starter_plan,
        'professional': professional_plan,
        'enterprise': enterprise_plan,
    }


# =============================================================================
# Organization Fixtures
# =============================================================================

@pytest.fixture
def test_organization(db, starter_plan, test_user):
    """Create test organization."""
    org = Organization.objects.create(
        name='Test Flight School',
        slug='test-flight-school',
        email='info@testflight.com',
        organization_type='flight_school',
        country_code='US',
        timezone='America/New_York',
        currency_code='USD',
        language='en',
        subscription_plan=starter_plan,
        subscription_status='active',
        max_users=starter_plan.max_users,
        max_aircraft=starter_plan.max_aircraft,
        max_students=starter_plan.max_students,
        max_locations=starter_plan.max_locations,
        storage_limit_gb=starter_plan.storage_limit_gb,
        features=starter_plan.features,
        status='active',
        created_by=test_user.id,
    )
    return org


@pytest.fixture
def trial_organization(db, professional_plan, test_user):
    """Create organization on trial."""
    org = Organization.objects.create(
        name='Trial Flight School',
        slug='trial-flight-school',
        email='info@trialflight.com',
        organization_type='flight_school',
        country_code='NO',
        timezone='Europe/Oslo',
        currency_code='NOK',
        language='no',
        subscription_plan=professional_plan,
        subscription_status='trialing',
        trial_ends_at=datetime.utcnow() + timedelta(days=14),
        max_users=professional_plan.max_users,
        max_aircraft=professional_plan.max_aircraft,
        max_students=professional_plan.max_students,
        max_locations=professional_plan.max_locations,
        storage_limit_gb=professional_plan.storage_limit_gb,
        features=professional_plan.features,
        status='active',
        created_by=test_user.id,
    )
    return org


@pytest.fixture
def inactive_organization(db, free_plan, test_user):
    """Create inactive organization."""
    org = Organization.objects.create(
        name='Inactive School',
        slug='inactive-school',
        email='info@inactive.com',
        organization_type='flight_school',
        country_code='US',
        subscription_plan=free_plan,
        subscription_status='cancelled',
        status='suspended',
        created_by=test_user.id,
    )
    return org


# =============================================================================
# Location Fixtures
# =============================================================================

@pytest.fixture
def primary_location(db, test_organization, test_user):
    """Create primary location for organization."""
    return Location.objects.create(
        organization=test_organization,
        name='Main Base',
        code='MAIN',
        location_type='base',
        airport_icao='KJFK',
        airport_iata='JFK',
        airport_name='John F. Kennedy International Airport',
        city='New York',
        state_province='NY',
        country_code='US',
        latitude=Decimal('40.64131'),
        longitude=Decimal('-73.77814'),
        elevation_ft=13,
        timezone='America/New_York',
        is_primary=True,
        is_active=True,
        operating_hours={
            'monday': {'open': '08:00', 'close': '18:00'},
            'tuesday': {'open': '08:00', 'close': '18:00'},
            'wednesday': {'open': '08:00', 'close': '18:00'},
            'thursday': {'open': '08:00', 'close': '18:00'},
            'friday': {'open': '08:00', 'close': '18:00'},
            'saturday': {'open': '09:00', 'close': '14:00'},
            'sunday': {'closed': True},
        },
        facilities=['hangar', 'briefing_room', 'fuel'],
        created_by=test_user.id,
        display_order=1,
    )


@pytest.fixture
def secondary_location(db, test_organization, test_user):
    """Create secondary location for organization."""
    return Location.objects.create(
        organization=test_organization,
        name='Training Field',
        code='TRN',
        location_type='training',
        airport_icao='KEWR',
        airport_iata='EWR',
        airport_name='Newark Liberty International Airport',
        city='Newark',
        state_province='NJ',
        country_code='US',
        latitude=Decimal('40.68925'),
        longitude=Decimal('-74.17446'),
        elevation_ft=18,
        timezone='America/New_York',
        is_primary=False,
        is_active=True,
        facilities=['training_area'],
        created_by=test_user.id,
        display_order=2,
    )


# =============================================================================
# Invitation Fixtures
# =============================================================================

@pytest.fixture
def pending_invitation(db, test_organization, test_user):
    """Create pending invitation."""
    return OrganizationInvitation.objects.create(
        organization=test_organization,
        email='newuser@example.com',
        role_code='instructor',
        status='pending',
        token=OrganizationInvitation.generate_token(),
        expires_at=datetime.utcnow() + timedelta(days=7),
        invited_by=test_user.id,
        invited_by_email=test_user.email,
        message='Welcome to our flight school!',
    )


@pytest.fixture
def expired_invitation(db, test_organization, test_user):
    """Create expired invitation."""
    return OrganizationInvitation.objects.create(
        organization=test_organization,
        email='expired@example.com',
        role_code='student',
        status='pending',
        token=OrganizationInvitation.generate_token(),
        expires_at=datetime.utcnow() - timedelta(days=1),
        invited_by=test_user.id,
        invited_by_email=test_user.email,
    )


# =============================================================================
# Organization Setting Fixtures
# =============================================================================

@pytest.fixture
def organization_settings(db, test_organization):
    """Create organization settings."""
    settings_data = [
        ('notifications', 'email_enabled', True),
        ('notifications', 'sms_enabled', False),
        ('scheduling', 'default_duration', 60),
        ('scheduling', 'buffer_minutes', 15),
        ('billing', 'auto_invoice', True),
    ]

    settings = []
    for category, key, value in settings_data:
        setting = OrganizationSetting.objects.create(
            organization=test_organization,
            category=category,
            key=key,
            value=value,
        )
        settings.append(setting)

    return settings


# =============================================================================
# Helper Functions
# =============================================================================

@pytest.fixture
def create_organization(db, starter_plan):
    """Factory fixture to create organizations."""

    def _create_organization(
        name: str = None,
        **kwargs
    ) -> Organization:
        name = name or f"Test Org {uuid.uuid4().hex[:8]}"
        slug = kwargs.pop('slug', name.lower().replace(' ', '-'))

        defaults = {
            'name': name,
            'slug': slug,
            'email': f'{slug}@test.com',
            'organization_type': 'flight_school',
            'country_code': 'US',
            'subscription_plan': starter_plan,
            'subscription_status': 'active',
            'status': 'active',
            'created_by': str(uuid.uuid4()),
        }
        defaults.update(kwargs)

        return Organization.objects.create(**defaults)

    return _create_organization


@pytest.fixture
def create_location(db):
    """Factory fixture to create locations."""

    def _create_location(
        organization: Organization,
        name: str = None,
        **kwargs
    ) -> Location:
        name = name or f"Location {uuid.uuid4().hex[:8]}"
        code = kwargs.pop('code', name[:3].upper())

        defaults = {
            'organization': organization,
            'name': name,
            'code': code,
            'location_type': 'base',
            'is_active': True,
            'created_by': str(uuid.uuid4()),
        }
        defaults.update(kwargs)

        return Location.objects.create(**defaults)

    return _create_location


@pytest.fixture
def create_invitation(db):
    """Factory fixture to create invitations."""

    def _create_invitation(
        organization: Organization,
        email: str = None,
        **kwargs
    ) -> OrganizationInvitation:
        email = email or f"invite-{uuid.uuid4().hex[:8]}@test.com"

        defaults = {
            'organization': organization,
            'email': email,
            'role_code': 'member',
            'status': 'pending',
            'token': OrganizationInvitation.generate_token(),
            'expires_at': datetime.utcnow() + timedelta(days=7),
            'invited_by': str(uuid.uuid4()),
        }
        defaults.update(kwargs)

        return OrganizationInvitation.objects.create(**defaults)

    return _create_invitation
