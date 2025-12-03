# services/maintenance-service/src/conftest.py
"""
Pytest configuration for Maintenance Service
"""

import os
import django
from django.conf import settings

# Set up Django settings before importing any Django modules
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


def pytest_configure():
    """Configure Django settings for tests."""
    settings.DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
    settings.DEBUG = False
    settings.PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]
    django.setup()


import pytest
import uuid
from decimal import Decimal
from datetime import date


@pytest.fixture
def org_id():
    """Generate a test organization ID."""
    return uuid.uuid4()


@pytest.fixture
def aircraft_id():
    """Generate a test aircraft ID."""
    return uuid.uuid4()


@pytest.fixture
def user_id():
    """Generate a test user ID."""
    return uuid.uuid4()


@pytest.fixture
def maintenance_item(org_id, aircraft_id):
    """Create a test maintenance item."""
    from apps.core.models import MaintenanceItem

    return MaintenanceItem.objects.create(
        organization_id=org_id,
        aircraft_id=aircraft_id,
        name='Test Maintenance Item',
        category=MaintenanceItem.Category.INSPECTION,
        item_type=MaintenanceItem.ItemType.RECURRING,
        interval_hours=100,
        next_due_hours=Decimal('100.0'),
    )


@pytest.fixture
def work_order(org_id, aircraft_id, user_id):
    """Create a test work order."""
    from apps.core.models import WorkOrder

    return WorkOrder.objects.create(
        organization_id=org_id,
        aircraft_id=aircraft_id,
        title='Test Work Order',
        work_order_type=WorkOrder.WorkOrderType.SCHEDULED,
        created_by=user_id,
    )


@pytest.fixture
def parts_inventory(org_id):
    """Create a test parts inventory item."""
    from apps.core.models import PartsInventory

    return PartsInventory.objects.create(
        organization_id=org_id,
        part_number='PN-TEST-001',
        description='Test Part',
        quantity_on_hand=100,
        minimum_quantity=20,
        unit_cost=Decimal('25.00'),
    )


@pytest.fixture
def ad_tracking(org_id, aircraft_id):
    """Create a test AD tracking record."""
    from apps.core.models import ADSBTracking

    return ADSBTracking.objects.create(
        organization_id=org_id,
        aircraft_id=aircraft_id,
        directive_type=ADSBTracking.DirectiveType.AD,
        directive_number='2024-TEST-001',
        title='Test AD',
        compliance_required=True,
    )


@pytest.fixture
def maintenance_log(org_id, aircraft_id, user_id):
    """Create a test maintenance log."""
    from apps.core.models import MaintenanceLog

    return MaintenanceLog.objects.create(
        organization_id=org_id,
        aircraft_id=aircraft_id,
        title='Test Maintenance Log',
        work_performed='Test work performed',
        category=MaintenanceLog.Category.INSPECTION,
        performed_date=date.today(),
        performed_by='Test Mechanic',
        created_by=user_id,
    )


@pytest.fixture
def maintenance_service():
    """Create MaintenanceService instance."""
    from apps.core.services import MaintenanceService
    return MaintenanceService()


@pytest.fixture
def work_order_service():
    """Create WorkOrderService instance."""
    from apps.core.services import WorkOrderService
    return WorkOrderService()


@pytest.fixture
def parts_service():
    """Create PartsService instance."""
    from apps.core.services import PartsService
    return PartsService()


@pytest.fixture
def compliance_service():
    """Create ComplianceService instance."""
    from apps.core.services import ComplianceService
    return ComplianceService()


@pytest.fixture
def api_client():
    """Create API test client."""
    from rest_framework.test import APIClient
    return APIClient()
