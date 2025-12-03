# services/maintenance-service/src/apps/core/tests/test_models.py
"""
Tests for Maintenance Service Models
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
    PartTransaction,
    ADSBTracking,
)


class MaintenanceItemModelTest(TestCase):
    """Tests for MaintenanceItem model."""

    def setUp(self):
        self.org_id = uuid.uuid4()
        self.aircraft_id = uuid.uuid4()

    def test_create_maintenance_item(self):
        """Test creating a basic maintenance item."""
        item = MaintenanceItem.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            name='100 Hour Inspection',
            category=MaintenanceItem.Category.INSPECTION,
            item_type=MaintenanceItem.ItemType.RECURRING,
            interval_hours=100,
            warning_hours=10,
            critical_hours=5,
        )

        self.assertEqual(item.name, '100 Hour Inspection')
        self.assertEqual(item.category, MaintenanceItem.Category.INSPECTION)
        self.assertEqual(item.interval_hours, 100)
        self.assertIsNotNone(item.id)

    def test_calculate_remaining_hours(self):
        """Test calculating remaining hours."""
        item = MaintenanceItem.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            name='Oil Change',
            category=MaintenanceItem.Category.PREVENTIVE,
            item_type=MaintenanceItem.ItemType.RECURRING,
            interval_hours=50,
            next_due_hours=Decimal('150.0'),
        )

        item.calculate_remaining(current_hours=Decimal('130.0'))

        self.assertEqual(item.remaining_hours, Decimal('20.0'))
        self.assertEqual(item.compliance_status, MaintenanceItem.ComplianceStatus.DUE_SOON)

    def test_calculate_remaining_overdue(self):
        """Test overdue status calculation."""
        item = MaintenanceItem.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            name='Annual Inspection',
            category=MaintenanceItem.Category.INSPECTION,
            item_type=MaintenanceItem.ItemType.RECURRING,
            next_due_hours=Decimal('100.0'),
        )

        item.calculate_remaining(current_hours=Decimal('110.0'))

        self.assertEqual(item.remaining_hours, Decimal('-10.0'))
        self.assertEqual(item.compliance_status, MaintenanceItem.ComplianceStatus.OVERDUE)

    def test_record_compliance(self):
        """Test recording compliance on an item."""
        item = MaintenanceItem.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            name='Engine Inspection',
            category=MaintenanceItem.Category.INSPECTION,
            item_type=MaintenanceItem.ItemType.RECURRING,
            interval_hours=100,
            next_due_hours=Decimal('200.0'),
        )

        item.record_compliance(
            done_date=date.today(),
            done_hours=Decimal('200.0'),
            done_by='John Mechanic'
        )

        self.assertEqual(item.last_done_date, date.today())
        self.assertEqual(item.last_done_hours, Decimal('200.0'))
        self.assertEqual(item.last_done_by, 'John Mechanic')
        self.assertEqual(item.next_due_hours, Decimal('300.0'))
        self.assertEqual(item.compliance_status, MaintenanceItem.ComplianceStatus.COMPLIANT)

    def test_defer_maintenance(self):
        """Test deferring maintenance."""
        item = MaintenanceItem.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            name='Non-Critical Check',
            category=MaintenanceItem.Category.PREVENTIVE,
            item_type=MaintenanceItem.ItemType.RECURRING,
            is_mandatory=False,
            next_due_hours=Decimal('100.0'),
        )

        new_date = date.today() + timedelta(days=30)
        item.defer(
            new_due_date=new_date,
            new_due_hours=Decimal('120.0'),
            reason='Deferred for scheduling',
            approved_by=uuid.uuid4()
        )

        self.assertEqual(item.next_due_date, new_date)
        self.assertEqual(item.next_due_hours, Decimal('120.0'))
        self.assertEqual(item.deferral_reason, 'Deferred for scheduling')
        self.assertEqual(item.compliance_status, MaintenanceItem.ComplianceStatus.DEFERRED)


class WorkOrderModelTest(TestCase):
    """Tests for WorkOrder model."""

    def setUp(self):
        self.org_id = uuid.uuid4()
        self.aircraft_id = uuid.uuid4()

    def test_create_work_order(self):
        """Test creating a work order."""
        wo = WorkOrder.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            title='100 Hour Inspection',
            work_order_type=WorkOrder.WorkOrderType.SCHEDULED,
            created_by=uuid.uuid4(),
        )

        self.assertIsNotNone(wo.work_order_number)
        self.assertEqual(wo.status, WorkOrder.Status.DRAFT)
        self.assertEqual(wo.priority, WorkOrder.Priority.NORMAL)

    def test_work_order_workflow(self):
        """Test complete work order workflow."""
        wo = WorkOrder.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            title='Scheduled Maintenance',
            work_order_type=WorkOrder.WorkOrderType.SCHEDULED,
            created_by=uuid.uuid4(),
        )

        # Plan
        from datetime import datetime
        from django.utils import timezone
        scheduled_start = timezone.now()
        wo.plan(scheduled_start)
        self.assertEqual(wo.status, WorkOrder.Status.PLANNED)

        # Approve
        approver_id = uuid.uuid4()
        wo.approve(approver_id, 'Approver Name')
        self.assertEqual(wo.status, WorkOrder.Status.APPROVED)
        self.assertEqual(wo.approved_by, approver_id)

        # Start
        wo.start(uuid.uuid4())
        self.assertEqual(wo.status, WorkOrder.Status.IN_PROGRESS)
        self.assertIsNotNone(wo.actual_start)

        # Hold
        wo.hold('Waiting for parts')
        self.assertEqual(wo.status, WorkOrder.Status.ON_HOLD)
        self.assertEqual(wo.hold_reason, 'Waiting for parts')

        # Resume
        wo.resume()
        self.assertEqual(wo.status, WorkOrder.Status.IN_PROGRESS)

        # Complete
        completer_id = uuid.uuid4()
        wo.complete(completer_id, 'Completer Name')
        self.assertEqual(wo.status, WorkOrder.Status.COMPLETED)
        self.assertIsNotNone(wo.actual_end)

    def test_work_order_cancel(self):
        """Test cancelling a work order."""
        wo = WorkOrder.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            title='To Be Cancelled',
            work_order_type=WorkOrder.WorkOrderType.UNSCHEDULED,
            created_by=uuid.uuid4(),
        )

        wo.cancel('No longer needed', uuid.uuid4())
        self.assertEqual(wo.status, WorkOrder.Status.CANCELLED)
        self.assertEqual(wo.cancellation_reason, 'No longer needed')


class WorkOrderTaskModelTest(TestCase):
    """Tests for WorkOrderTask model."""

    def setUp(self):
        self.org_id = uuid.uuid4()
        self.aircraft_id = uuid.uuid4()
        self.work_order = WorkOrder.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            title='Test Work Order',
            work_order_type=WorkOrder.WorkOrderType.SCHEDULED,
            created_by=uuid.uuid4(),
        )

    def test_create_task(self):
        """Test creating a task."""
        task = WorkOrderTask.objects.create(
            work_order=self.work_order,
            sequence=1,
            title='Remove cowling',
            estimated_hours=Decimal('0.5'),
        )

        self.assertEqual(task.status, WorkOrderTask.Status.PENDING)
        self.assertEqual(task.sequence, 1)

    def test_complete_task(self):
        """Test completing a task."""
        task = WorkOrderTask.objects.create(
            work_order=self.work_order,
            sequence=1,
            title='Check oil level',
        )

        completer_id = uuid.uuid4()
        task.complete(completer_id, 'Oil level OK', Decimal('0.25'))

        self.assertEqual(task.status, WorkOrderTask.Status.COMPLETED)
        self.assertEqual(task.completed_by, completer_id)
        self.assertEqual(task.actual_hours, Decimal('0.25'))
        self.assertIsNotNone(task.completed_at)


class PartsInventoryModelTest(TestCase):
    """Tests for PartsInventory model."""

    def setUp(self):
        self.org_id = uuid.uuid4()

    def test_create_part(self):
        """Test creating a part."""
        part = PartsInventory.objects.create(
            organization_id=self.org_id,
            part_number='MS20426AD3-4',
            description='Rivet, AD3-4',
            category='hardware',
            quantity_on_hand=500,
            minimum_quantity=100,
            unit_cost=Decimal('0.15'),
        )

        self.assertEqual(part.part_number, 'MS20426AD3-4')
        self.assertEqual(part.quantity_available, 500)

    def test_receive_parts(self):
        """Test receiving parts."""
        part = PartsInventory.objects.create(
            organization_id=self.org_id,
            part_number='P/N-12345',
            description='Test Part',
            quantity_on_hand=10,
            unit_cost=Decimal('50.00'),
        )

        transaction = part.receive(
            quantity=20,
            unit_cost=Decimal('55.00'),
            received_by=uuid.uuid4()
        )

        self.assertEqual(part.quantity_on_hand, 30)
        self.assertEqual(transaction.transaction_type, PartTransaction.TransactionType.RECEIVE)
        self.assertEqual(transaction.quantity, 20)

    def test_issue_parts(self):
        """Test issuing parts."""
        part = PartsInventory.objects.create(
            organization_id=self.org_id,
            part_number='P/N-67890',
            description='Test Part',
            quantity_on_hand=50,
            unit_cost=Decimal('25.00'),
        )

        transaction = part.issue(
            quantity=10,
            work_order_id=uuid.uuid4(),
            issued_by=uuid.uuid4()
        )

        self.assertEqual(part.quantity_on_hand, 40)
        self.assertEqual(transaction.transaction_type, PartTransaction.TransactionType.ISSUE)

    def test_reserve_parts(self):
        """Test reserving parts."""
        part = PartsInventory.objects.create(
            organization_id=self.org_id,
            part_number='P/N-RESERVE',
            description='Reservable Part',
            quantity_on_hand=100,
        )

        part.reserve(quantity=30, work_order_id=uuid.uuid4())

        self.assertEqual(part.quantity_reserved, 30)
        self.assertEqual(part.quantity_available, 70)


class ADSBTrackingModelTest(TestCase):
    """Tests for ADSBTracking model."""

    def setUp(self):
        self.org_id = uuid.uuid4()
        self.aircraft_id = uuid.uuid4()

    def test_create_directive(self):
        """Test creating an AD directive."""
        ad = ADSBTracking.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            directive_type=ADSBTracking.DirectiveType.AD,
            directive_number='2024-01-01',
            title='Engine Mount Inspection',
            effective_date=date.today(),
            compliance_required=True,
            is_recurring=True,
            recurring_interval_hours=100,
        )

        self.assertEqual(ad.directive_type, ADSBTracking.DirectiveType.AD)
        self.assertEqual(ad.compliance_status, ADSBTracking.ComplianceStatus.PENDING)

    def test_record_directive_compliance(self):
        """Test recording compliance with a directive."""
        ad = ADSBTracking.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            directive_type=ADSBTracking.DirectiveType.AD,
            directive_number='2024-02-15',
            title='Fuel Tank Inspection',
            compliance_required=True,
            is_recurring=True,
            recurring_interval_hours=500,
            initial_compliance_hours=Decimal('1000.0'),
        )

        ad.record_compliance(
            compliance_date=date.today(),
            compliance_hours=Decimal('1000.0')
        )

        self.assertEqual(ad.last_compliance_date, date.today())
        self.assertEqual(ad.last_compliance_hours, Decimal('1000.0'))
        self.assertEqual(ad.next_due_hours, Decimal('1500.0'))
        self.assertEqual(ad.compliance_status, ADSBTracking.ComplianceStatus.COMPLIANT)

    def test_mark_not_applicable(self):
        """Test marking a directive as not applicable."""
        sb = ADSBTracking.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            directive_type=ADSBTracking.DirectiveType.SB,
            directive_number='SB-2024-001',
            title='Optional Modification',
        )

        sb.mark_not_applicable('Not applicable to this serial number')

        self.assertFalse(sb.is_applicable)
        self.assertEqual(sb.not_applicable_reason, 'Not applicable to this serial number')
        self.assertEqual(sb.compliance_status, ADSBTracking.ComplianceStatus.NOT_APPLICABLE)


class MaintenanceLogModelTest(TestCase):
    """Tests for MaintenanceLog model."""

    def setUp(self):
        self.org_id = uuid.uuid4()
        self.aircraft_id = uuid.uuid4()

    def test_create_log(self):
        """Test creating a maintenance log."""
        log = MaintenanceLog.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            title='100 Hour Inspection',
            work_performed='Performed 100 hour inspection per manufacturer checklist',
            category=MaintenanceLog.Category.INSPECTION,
            performed_date=date.today(),
            aircraft_hours=Decimal('2500.50'),
            performed_by='John Mechanic',
            created_by=uuid.uuid4(),
        )

        self.assertIsNotNone(log.log_number)
        self.assertEqual(log.status, MaintenanceLog.Status.DRAFT)

    def test_log_with_costs(self):
        """Test log with cost calculations."""
        log = MaintenanceLog.objects.create(
            organization_id=self.org_id,
            aircraft_id=self.aircraft_id,
            title='Engine Repair',
            work_performed='Replaced cylinder',
            category=MaintenanceLog.Category.REPAIR,
            performed_date=date.today(),
            performed_by='Senior Mechanic',
            labor_hours=Decimal('8.0'),
            labor_cost=Decimal('800.00'),
            parts_cost=Decimal('1500.00'),
            other_cost=Decimal('50.00'),
            created_by=uuid.uuid4(),
        )

        self.assertEqual(log.total_cost, Decimal('2350.00'))
