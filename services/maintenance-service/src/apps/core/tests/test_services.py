# services/maintenance-service/src/apps/core/tests/test_services.py
"""
Tests for Maintenance Service Business Logic
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from apps.core.models import (
    MaintenanceItem,
    WorkOrder,
    WorkOrderTask,
    MaintenanceLog,
    PartsInventory,
    ADSBTracking,
)
from apps.core.services import (
    MaintenanceService,
    WorkOrderService,
    PartsService,
    ComplianceService,
    MaintenanceItemNotFoundError,
    WorkOrderNotFoundError,
    WorkOrderStateError,
    PartNotFoundError,
    InsufficientInventoryError,
    ComplianceError,
)


class MaintenanceServiceTest(TestCase):
    """Tests for MaintenanceService."""

    def setUp(self):
        self.service = MaintenanceService()
        self.org_id = uuid.uuid4()
        self.aircraft_id = uuid.uuid4()

    def test_create_item(self):
        """Test creating a maintenance item through service."""
        item = self.service.create_item(
            organization_id=self.org_id,
            name='Oil Change',
            category=MaintenanceItem.Category.PREVENTIVE,
            aircraft_id=self.aircraft_id,
            item_type=MaintenanceItem.ItemType.RECURRING,
            interval_hours=50,
        )

        self.assertIsNotNone(item.id)
        self.assertEqual(item.name, 'Oil Change')
        self.assertEqual(item.interval_hours, 50)

    def test_get_item(self):
        """Test getting an item by ID."""
        created = self.service.create_item(
            organization_id=self.org_id,
            name='Test Item',
            category=MaintenanceItem.Category.INSPECTION,
        )

        retrieved = self.service.get_item(created.id)
        self.assertEqual(retrieved.id, created.id)

    def test_get_item_not_found(self):
        """Test getting non-existent item raises error."""
        with self.assertRaises(MaintenanceItemNotFoundError):
            self.service.get_item(uuid.uuid4())

    def test_list_items_with_filters(self):
        """Test listing items with various filters."""
        # Create multiple items
        self.service.create_item(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            name='Inspection 1',
            category=MaintenanceItem.Category.INSPECTION,
            is_mandatory=True,
        )
        self.service.create_item(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            name='Preventive 1',
            category=MaintenanceItem.Category.PREVENTIVE,
            is_mandatory=False,
        )

        # Filter by category
        inspections = self.service.list_items(
            organization_id=self.org_id,
            category=MaintenanceItem.Category.INSPECTION,
        )
        self.assertEqual(len(inspections), 1)
        self.assertEqual(inspections[0].category, MaintenanceItem.Category.INSPECTION)

        # Filter by mandatory
        mandatory = self.service.list_items(
            organization_id=self.org_id,
            is_mandatory=True,
        )
        self.assertEqual(len(mandatory), 1)

    def test_record_compliance(self):
        """Test recording compliance creates log and updates item."""
        item = self.service.create_item(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            name='Compliance Test',
            category=MaintenanceItem.Category.INSPECTION,
            item_type=MaintenanceItem.ItemType.RECURRING,
            interval_hours=100,
            next_due_hours=Decimal('100.0'),
        )

        log = self.service.record_compliance(
            item_id=item.id,
            performed_date=date.today(),
            aircraft_hours=Decimal('100.0'),
            performed_by='Test Mechanic',
        )

        self.assertIsNotNone(log.id)
        self.assertEqual(log.title, item.name)

        # Verify item was updated
        updated_item = self.service.get_item(item.id)
        self.assertEqual(updated_item.last_done_date, date.today())
        self.assertEqual(updated_item.next_due_hours, Decimal('200.0'))

    def test_update_compliance_status(self):
        """Test updating compliance status for aircraft items."""
        # Create items with different due hours
        self.service.create_item(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            name='Due Item',
            category=MaintenanceItem.Category.INSPECTION,
            next_due_hours=Decimal('100.0'),
            critical_hours=5,
        )
        self.service.create_item(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            name='Overdue Item',
            category=MaintenanceItem.Category.PREVENTIVE,
            next_due_hours=Decimal('80.0'),
        )

        counts = self.service.update_compliance_status(
            aircraft_id=self.aircraft_id,
            current_hours=Decimal('95.0'),
        )

        self.assertEqual(counts['updated'], 2)
        self.assertGreaterEqual(counts['overdue'], 1)

    def test_get_aircraft_maintenance_status(self):
        """Test getting comprehensive maintenance status."""
        # Create items in different states
        self.service.create_item(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            name='Current Item',
            category=MaintenanceItem.Category.INSPECTION,
            next_due_hours=Decimal('200.0'),
        )

        status = self.service.get_aircraft_maintenance_status(
            aircraft_id=self.aircraft_id,
            current_hours=Decimal('100.0'),
        )

        self.assertEqual(status['aircraft_id'], str(self.aircraft_id))
        self.assertIn('overdue', status)
        self.assertIn('due', status)
        self.assertIn('due_soon', status)


class WorkOrderServiceTest(TestCase):
    """Tests for WorkOrderService."""

    def setUp(self):
        self.service = WorkOrderService()
        self.org_id = uuid.uuid4()
        self.aircraft_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

    def test_create_work_order(self):
        """Test creating a work order."""
        wo = self.service.create_work_order(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            title='Test Work Order',
            work_order_type=WorkOrder.WorkOrderType.SCHEDULED,
            created_by=self.user_id,
        )

        self.assertIsNotNone(wo.id)
        self.assertIsNotNone(wo.work_order_number)
        self.assertEqual(wo.status, WorkOrder.Status.DRAFT)

    def test_create_work_order_with_tasks(self):
        """Test creating work order with maintenance items creates tasks."""
        # Create maintenance items first
        item1 = MaintenanceItem.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            name='Task 1',
            category=MaintenanceItem.Category.INSPECTION,
        )
        item2 = MaintenanceItem.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            name='Task 2',
            category=MaintenanceItem.Category.PREVENTIVE,
        )

        wo = self.service.create_work_order(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            title='Multi-Task WO',
            work_order_type=WorkOrder.WorkOrderType.SCHEDULED,
            created_by=self.user_id,
            maintenance_item_ids=[item1.id, item2.id],
        )

        self.assertEqual(wo.tasks.count(), 2)

    def test_workflow_plan_and_approve(self):
        """Test planning and approving a work order."""
        wo = self.service.create_work_order(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            title='Workflow Test',
            work_order_type=WorkOrder.WorkOrderType.SCHEDULED,
            created_by=self.user_id,
        )

        # Plan
        from django.utils import timezone
        scheduled_start = timezone.now() + timedelta(days=1)
        wo = self.service.plan(wo.id, scheduled_start)
        self.assertEqual(wo.status, WorkOrder.Status.PLANNED)

        # Approve
        wo = self.service.approve(wo.id, self.user_id, 'Approver')
        self.assertEqual(wo.status, WorkOrder.Status.APPROVED)

    def test_complete_work_order_with_incomplete_tasks(self):
        """Test that completing WO with incomplete tasks fails."""
        wo = self.service.create_work_order(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            title='Incomplete Tasks WO',
            work_order_type=WorkOrder.WorkOrderType.SCHEDULED,
            created_by=self.user_id,
        )

        # Add a task
        self.service.add_task(wo.id, 'Pending Task')

        # Move to in_progress
        from django.utils import timezone
        wo.status = WorkOrder.Status.IN_PROGRESS
        wo.actual_start = timezone.now()
        wo.save()

        # Try to complete - should fail
        with self.assertRaises(WorkOrderStateError):
            self.service.complete(wo.id, self.user_id)

    def test_add_and_complete_task(self):
        """Test adding and completing tasks."""
        wo = self.service.create_work_order(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            title='Task Test WO',
            work_order_type=WorkOrder.WorkOrderType.SCHEDULED,
            created_by=self.user_id,
        )

        # Add task
        task = self.service.add_task(
            work_order_id=wo.id,
            title='Test Task',
            estimated_hours=Decimal('2.0'),
        )
        self.assertEqual(task.status, WorkOrderTask.Status.PENDING)

        # Complete task
        task = self.service.complete_task(
            task_id=task.id,
            completed_by=self.user_id,
            notes='Completed successfully',
            hours=Decimal('1.5'),
        )
        self.assertEqual(task.status, WorkOrderTask.Status.COMPLETED)
        self.assertEqual(task.actual_hours, Decimal('1.5'))

    def test_get_statistics(self):
        """Test getting work order statistics."""
        # Create some work orders
        self.service.create_work_order(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            title='WO 1',
            work_order_type=WorkOrder.WorkOrderType.SCHEDULED,
            created_by=self.user_id,
        )

        stats = self.service.get_statistics(organization_id=self.org_id)

        self.assertIn('open_count', stats)
        self.assertIn('in_progress_count', stats)
        self.assertEqual(stats['open_count'], 1)


class PartsServiceTest(TestCase):
    """Tests for PartsService."""

    def setUp(self):
        self.service = PartsService()
        self.org_id = uuid.uuid4()

    def test_create_part(self):
        """Test creating a part."""
        part = self.service.create_part(
            organization_id=self.org_id,
            part_number='PN-TEST-001',
            description='Test Part',
            quantity_on_hand=100,
        )

        self.assertIsNotNone(part.id)
        self.assertEqual(part.part_number, 'PN-TEST-001')

    def test_receive_parts(self):
        """Test receiving parts."""
        part = self.service.create_part(
            organization_id=self.org_id,
            part_number='PN-RECEIVE',
            description='Receivable Part',
            quantity_on_hand=50,
            unit_cost=Decimal('10.00'),
        )

        transaction = self.service.receive_parts(
            part_id=part.id,
            quantity=25,
            unit_cost=Decimal('12.00'),
        )

        part.refresh_from_db()
        self.assertEqual(part.quantity_on_hand, 75)
        self.assertEqual(transaction.quantity, 25)

    def test_issue_parts(self):
        """Test issuing parts."""
        part = self.service.create_part(
            organization_id=self.org_id,
            part_number='PN-ISSUE',
            description='Issuable Part',
            quantity_on_hand=100,
        )

        transaction = self.service.issue_parts(
            part_id=part.id,
            quantity=30,
            work_order_id=uuid.uuid4(),
        )

        part.refresh_from_db()
        self.assertEqual(part.quantity_on_hand, 70)

    def test_issue_insufficient_inventory(self):
        """Test issuing more than available raises error."""
        part = self.service.create_part(
            organization_id=self.org_id,
            part_number='PN-INSUFFICIENT',
            description='Limited Part',
            quantity_on_hand=10,
        )

        with self.assertRaises(InsufficientInventoryError):
            self.service.issue_parts(part_id=part.id, quantity=50)

    def test_reserve_and_release(self):
        """Test reserving and releasing parts."""
        part = self.service.create_part(
            organization_id=self.org_id,
            part_number='PN-RESERVE',
            description='Reservable Part',
            quantity_on_hand=100,
        )

        # Reserve
        part = self.service.reserve_parts(
            part_id=part.id,
            quantity=30,
            work_order_id=uuid.uuid4(),
        )
        self.assertEqual(part.quantity_reserved, 30)
        self.assertEqual(part.quantity_available, 70)

        # Release
        part = self.service.release_reservation(part_id=part.id, quantity=30)
        self.assertEqual(part.quantity_reserved, 0)
        self.assertEqual(part.quantity_available, 100)

    def test_get_low_stock_parts(self):
        """Test getting low stock parts."""
        # Create parts with different stock levels
        self.service.create_part(
            organization_id=self.org_id,
            part_number='PN-LOW',
            description='Low Stock Part',
            quantity_on_hand=5,
            minimum_quantity=10,
        )
        self.service.create_part(
            organization_id=self.org_id,
            part_number='PN-OK',
            description='OK Stock Part',
            quantity_on_hand=50,
            minimum_quantity=10,
        )

        low_stock = self.service.get_low_stock_parts(organization_id=self.org_id)
        self.assertEqual(len(low_stock), 1)
        self.assertEqual(low_stock[0].part_number, 'PN-LOW')


class ComplianceServiceTest(TestCase):
    """Tests for ComplianceService."""

    def setUp(self):
        self.service = ComplianceService()
        self.org_id = uuid.uuid4()
        self.aircraft_id = uuid.uuid4()

    def test_create_directive(self):
        """Test creating an AD directive."""
        directive = self.service.create_directive(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            directive_type='AD',
            directive_number='2024-01-01',
            title='Test AD',
            compliance_required=True,
        )

        self.assertIsNotNone(directive.id)
        self.assertEqual(directive.directive_type, ADSBTracking.DirectiveType.AD)

    def test_record_compliance(self):
        """Test recording compliance with a directive."""
        directive = self.service.create_directive(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            directive_type='AD',
            directive_number='2024-02-01',
            title='Compliance Test AD',
            compliance_required=True,
            is_recurring=True,
            recurring_interval_hours=500,
        )

        directive = self.service.record_compliance(
            directive_id=directive.id,
            compliance_date=date.today(),
            compliance_hours=Decimal('1000.0'),
        )

        self.assertEqual(directive.last_compliance_date, date.today())
        self.assertEqual(directive.compliance_status, ADSBTracking.ComplianceStatus.COMPLIANT)

    def test_mark_not_applicable(self):
        """Test marking directive as not applicable."""
        directive = self.service.create_directive(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            directive_type='SB',
            directive_number='SB-2024-001',
            title='Optional SB',
        )

        directive = self.service.mark_not_applicable(
            directive_id=directive.id,
            reason='Not applicable to this configuration',
        )

        self.assertFalse(directive.is_applicable)
        self.assertEqual(directive.compliance_status, ADSBTracking.ComplianceStatus.NOT_APPLICABLE)

    def test_get_aircraft_compliance_status(self):
        """Test getting aircraft compliance status."""
        # Create some directives
        self.service.create_directive(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            directive_type='AD',
            directive_number='AD-001',
            title='AD 1',
        )
        self.service.create_directive(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            directive_type='SB',
            directive_number='SB-001',
            title='SB 1',
        )

        status = self.service.get_aircraft_compliance_status(
            aircraft_id=self.aircraft_id
        )

        self.assertEqual(status['aircraft_id'], str(self.aircraft_id))
        self.assertIn('total_directives', status)
        self.assertIn('is_compliant', status)

    def test_get_compliance_statistics(self):
        """Test getting compliance statistics."""
        # Create directives
        self.service.create_directive(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            directive_type='AD',
            directive_number='AD-STAT-001',
            title='Stats AD',
        )

        stats = self.service.get_compliance_statistics(
            organization_id=self.org_id
        )

        self.assertIn('total_directives', stats)
        self.assertIn('compliance_rate', stats)
        self.assertIn('by_type', stats)
