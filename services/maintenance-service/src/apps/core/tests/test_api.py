# services/maintenance-service/src/apps/core/tests/test_api.py
"""
Tests for Maintenance Service API Endpoints
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import (
    MaintenanceItem,
    WorkOrder,
    WorkOrderTask,
    MaintenanceLog,
    PartsInventory,
    ADSBTracking,
)


class MaintenanceItemAPITest(TestCase):
    """Tests for Maintenance Item API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.org_id = uuid.uuid4()
        self.aircraft_id = uuid.uuid4()

        # Create test item
        self.item = MaintenanceItem.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            name='Test Inspection',
            category=MaintenanceItem.Category.INSPECTION,
            item_type=MaintenanceItem.ItemType.RECURRING,
            interval_hours=100,
        )

    def test_list_items(self):
        """Test listing maintenance items."""
        url = reverse('api:maintenance-item-list')
        response = self.client.get(url, {'organization_id': str(self.org_id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_retrieve_item(self):
        """Test retrieving a single item."""
        url = reverse('api:maintenance-item-detail', kwargs={'pk': self.item.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Inspection')

    def test_create_item(self):
        """Test creating an item."""
        url = reverse('api:maintenance-item-list')
        data = {
            'organization_id': str(self.org_id),
            'aircraft_id': str(self.aircraft_id),
            'name': 'New Inspection',
            'category': MaintenanceItem.Category.INSPECTION,
            'item_type': MaintenanceItem.ItemType.RECURRING,
            'interval_hours': 50,
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Inspection')

    def test_update_item(self):
        """Test updating an item."""
        url = reverse('api:maintenance-item-detail', kwargs={'pk': self.item.id})
        data = {'name': 'Updated Inspection'}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Inspection')

    def test_record_compliance(self):
        """Test recording compliance."""
        url = reverse('api:maintenance-item-record-compliance', kwargs={'pk': self.item.id})
        data = {
            'performed_date': date.today().isoformat(),
            'aircraft_hours': '100.0',
            'performed_by': 'Test Mechanic',
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('log_id', response.data)

    def test_aircraft_status(self):
        """Test getting aircraft maintenance status."""
        url = reverse('api:maintenance-item-aircraft-status')
        response = self.client.get(url, {
            'aircraft_id': str(self.aircraft_id),
            'current_hours': '50.0',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('overdue_count', response.data)
        self.assertIn('due_count', response.data)

    def test_dashboard(self):
        """Test getting dashboard statistics."""
        url = reverse('api:maintenance-item-dashboard')
        response = self.client.get(url, {'organization_id': str(self.org_id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_items', response.data)


class WorkOrderAPITest(TestCase):
    """Tests for Work Order API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.org_id = uuid.uuid4()
        self.aircraft_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

        # Create test work order
        self.work_order = WorkOrder.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            title='Test Work Order',
            work_order_type=WorkOrder.WorkOrderType.SCHEDULED,
            created_by=self.user_id,
        )

    def test_list_work_orders(self):
        """Test listing work orders."""
        url = reverse('api:work-order-list')
        response = self.client.get(url, {'organization_id': str(self.org_id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_work_order(self):
        """Test creating a work order."""
        url = reverse('api:work-order-list')
        data = {
            'organization_id': str(self.org_id),
            'aircraft_id': str(self.aircraft_id),
            'title': 'New Work Order',
            'work_order_type': WorkOrder.WorkOrderType.SCHEDULED,
            'created_by': str(self.user_id),
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['work_order_number'])

    def test_plan_work_order(self):
        """Test planning a work order."""
        url = reverse('api:work-order-plan', kwargs={'pk': self.work_order.id})
        from django.utils import timezone
        data = {
            'scheduled_start': (timezone.now() + timedelta(days=1)).isoformat(),
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], WorkOrder.Status.PLANNED)

    def test_add_task(self):
        """Test adding a task to work order."""
        url = reverse('api:work-order-add-task', kwargs={'pk': self.work_order.id})
        data = {
            'title': 'New Task',
            'estimated_hours': '2.0',
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Task')

    def test_statistics(self):
        """Test getting work order statistics."""
        url = reverse('api:work-order-statistics')
        response = self.client.get(url, {'organization_id': str(self.org_id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('open_count', response.data)


class PartsInventoryAPITest(TestCase):
    """Tests for Parts Inventory API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.org_id = uuid.uuid4()

        # Create test part
        self.part = PartsInventory.objects.create(
            organization_id=self.org_id,
            part_number='PN-API-TEST',
            description='API Test Part',
            quantity_on_hand=100,
            minimum_quantity=20,
            unit_cost=Decimal('25.00'),
        )

    def test_list_parts(self):
        """Test listing parts."""
        url = reverse('api:parts-inventory-list')
        response = self.client.get(url, {'organization_id': str(self.org_id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_part(self):
        """Test creating a part."""
        url = reverse('api:parts-inventory-list')
        data = {
            'organization_id': str(self.org_id),
            'part_number': 'PN-NEW-001',
            'description': 'New Part',
            'quantity_on_hand': 50,
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['part_number'], 'PN-NEW-001')

    def test_receive_parts(self):
        """Test receiving parts."""
        url = reverse('api:parts-inventory-receive', kwargs={'pk': self.part.id})
        data = {
            'quantity': 25,
            'unit_cost': '30.00',
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('transaction', response.data)

    def test_issue_parts(self):
        """Test issuing parts."""
        url = reverse('api:parts-inventory-issue', kwargs={'pk': self.part.id})
        data = {
            'quantity': 10,
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_issue_insufficient(self):
        """Test issuing more than available."""
        url = reverse('api:parts-inventory-issue', kwargs={'pk': self.part.id})
        data = {
            'quantity': 500,
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_low_stock(self):
        """Test getting low stock parts."""
        # Create a low stock part
        PartsInventory.objects.create(
            organization_id=self.org_id,
            part_number='PN-LOW-STOCK',
            description='Low Stock Part',
            quantity_on_hand=5,
            minimum_quantity=20,
        )

        url = reverse('api:parts-inventory-low-stock')
        response = self.client.get(url, {'organization_id': str(self.org_id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_search_parts(self):
        """Test searching parts."""
        url = reverse('api:parts-inventory-search')
        response = self.client.get(url, {
            'organization_id': str(self.org_id),
            'q': 'API',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class ADSBTrackingAPITest(TestCase):
    """Tests for AD/SB Tracking API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.org_id = uuid.uuid4()
        self.aircraft_id = uuid.uuid4()

        # Create test directive
        self.directive = ADSBTracking.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            directive_type=ADSBTracking.DirectiveType.AD,
            directive_number='2024-01-01',
            title='Test AD',
            compliance_required=True,
        )

    def test_list_directives(self):
        """Test listing directives."""
        url = reverse('api:adsb-tracking-list')
        response = self.client.get(url, {'organization_id': str(self.org_id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_directive(self):
        """Test creating a directive."""
        url = reverse('api:adsb-tracking-list')
        data = {
            'organization_id': str(self.org_id),
            'aircraft_id': str(self.aircraft_id),
            'directive_type': 'SB',
            'directive_number': 'SB-2024-001',
            'title': 'New Service Bulletin',
            'compliance_method': 'Inspection',
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['directive_number'], 'SB-2024-001')

    def test_record_compliance(self):
        """Test recording compliance."""
        url = reverse('api:adsb-tracking-record-compliance', kwargs={'pk': self.directive.id})
        data = {
            'compliance_date': date.today().isoformat(),
            'compliance_hours': '1000.0',
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('directive', response.data)

    def test_mark_not_applicable(self):
        """Test marking as not applicable."""
        url = reverse('api:adsb-tracking-mark-not-applicable', kwargs={'pk': self.directive.id})
        data = {
            'reason': 'Not applicable to this serial number',
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_aircraft_status(self):
        """Test getting aircraft compliance status."""
        url = reverse('api:adsb-tracking-aircraft-status')
        response = self.client.get(url, {'aircraft_id': str(self.aircraft_id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('is_compliant', response.data)

    def test_statistics(self):
        """Test getting compliance statistics."""
        url = reverse('api:adsb-tracking-statistics')
        response = self.client.get(url, {'organization_id': str(self.org_id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('compliance_rate', response.data)


class MaintenanceLogAPITest(TestCase):
    """Tests for Maintenance Log API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.org_id = uuid.uuid4()
        self.aircraft_id = uuid.uuid4()

        # Create test log
        self.log = MaintenanceLog.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            title='Test Maintenance',
            work_performed='Test work performed',
            category=MaintenanceLog.Category.INSPECTION,
            performed_date=date.today(),
            performed_by='Test Mechanic',
            created_by=uuid.uuid4(),
        )

    def test_list_logs(self):
        """Test listing logs."""
        url = reverse('api:maintenance-log-list')
        response = self.client.get(url, {'organization_id': str(self.org_id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_log(self):
        """Test creating a log."""
        url = reverse('api:maintenance-log-list')
        data = {
            'organization_id': str(self.org_id),
            'aircraft_id': str(self.aircraft_id),
            'title': 'New Maintenance Log',
            'work_performed': 'Work performed description',
            'category': MaintenanceLog.Category.REPAIR,
            'performed_date': date.today().isoformat(),
            'performed_by': 'Mechanic Name',
            'created_by': str(uuid.uuid4()),
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['log_number'])

    def test_aircraft_history(self):
        """Test getting aircraft history."""
        url = reverse('api:maintenance-log-aircraft-history')
        response = self.client.get(url, {'aircraft_id': str(self.aircraft_id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_summary(self):
        """Test getting summary statistics."""
        url = reverse('api:maintenance-log-summary')
        response = self.client.get(url, {'organization_id': str(self.org_id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_logs', response.data)
