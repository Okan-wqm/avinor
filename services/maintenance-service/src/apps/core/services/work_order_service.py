# services/maintenance-service/src/apps/core/services/work_order_service.py
"""
Work Order Service

Manages work order lifecycle and tasks.
"""

import uuid
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.core.models import WorkOrder, WorkOrderTask, MaintenanceItem

logger = logging.getLogger(__name__)


class WorkOrderService:
    """
    Service for managing work orders.

    Handles:
    - Work order CRUD
    - Workflow transitions
    - Task management
    - Cost tracking
    """

    # ==========================================================================
    # Work Order CRUD
    # ==========================================================================

    @transaction.atomic
    def create_work_order(
        self,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID,
        title: str,
        work_order_type: str,
        created_by: uuid.UUID,
        created_by_name: str = None,
        maintenance_item_ids: List[uuid.UUID] = None,
        squawk_ids: List[uuid.UUID] = None,
        **kwargs
    ) -> WorkOrder:
        """Create a new work order."""
        work_order = WorkOrder.objects.create(
            organization_id=organization_id,
            aircraft_id=aircraft_id,
            title=title,
            work_order_type=work_order_type,
            created_by=created_by,
            created_by_name=created_by_name,
            maintenance_items=maintenance_item_ids or [],
            squawk_ids=squawk_ids or [],
            **kwargs
        )

        # Create tasks from maintenance items
        if maintenance_item_ids:
            self._create_tasks_from_items(work_order, maintenance_item_ids)

        logger.info(f"Created work order: {work_order.work_order_number}")
        return work_order

    def get_work_order(self, work_order_id: uuid.UUID) -> WorkOrder:
        """Get a work order by ID."""
        try:
            return WorkOrder.objects.prefetch_related('tasks').get(id=work_order_id)
        except WorkOrder.DoesNotExist:
            from . import WorkOrderNotFoundError
            raise WorkOrderNotFoundError(f"Work order {work_order_id} not found")

    def get_by_number(self, work_order_number: str) -> WorkOrder:
        """Get a work order by number."""
        try:
            return WorkOrder.objects.prefetch_related('tasks').get(
                work_order_number=work_order_number
            )
        except WorkOrder.DoesNotExist:
            from . import WorkOrderNotFoundError
            raise WorkOrderNotFoundError(f"Work order {work_order_number} not found")

    def list_work_orders(
        self,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID = None,
        status: str = None,
        priority: str = None,
        work_order_type: str = None,
        assigned_to: uuid.UUID = None,
        is_open: bool = None
    ) -> List[WorkOrder]:
        """List work orders with filters."""
        queryset = WorkOrder.objects.filter(organization_id=organization_id)

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)
        if status:
            queryset = queryset.filter(status=status)
        if priority:
            queryset = queryset.filter(priority=priority)
        if work_order_type:
            queryset = queryset.filter(work_order_type=work_order_type)
        if assigned_to:
            queryset = queryset.filter(assigned_to=assigned_to)
        if is_open is True:
            queryset = queryset.filter(
                status__in=[
                    WorkOrder.Status.DRAFT,
                    WorkOrder.Status.PLANNED,
                    WorkOrder.Status.APPROVED,
                    WorkOrder.Status.IN_PROGRESS,
                    WorkOrder.Status.ON_HOLD
                ]
            )
        elif is_open is False:
            queryset = queryset.filter(
                status__in=[WorkOrder.Status.COMPLETED, WorkOrder.Status.CANCELLED]
            )

        return list(queryset.order_by('-created_at'))

    @transaction.atomic
    def update_work_order(self, work_order_id: uuid.UUID, **kwargs) -> WorkOrder:
        """Update a work order."""
        work_order = self.get_work_order(work_order_id)

        # Check if update is allowed
        if work_order.status in [WorkOrder.Status.COMPLETED, WorkOrder.Status.CANCELLED]:
            from . import WorkOrderStateError
            raise WorkOrderStateError("Cannot update completed or cancelled work order")

        allowed_fields = [
            'title', 'description', 'priority', 'scheduled_start',
            'scheduled_end', 'location_id', 'hangar', 'assigned_to',
            'assigned_to_name', 'assigned_team', 'estimated_hours',
            'estimated_cost', 'estimated_parts_cost', 'required_parts',
            'approval_notes', 'customer_approval_ref'
        ]

        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(work_order, field, value)

        work_order.save()
        return work_order

    # ==========================================================================
    # Workflow
    # ==========================================================================

    def plan(
        self,
        work_order_id: uuid.UUID,
        scheduled_start: datetime,
        scheduled_end: datetime = None
    ) -> WorkOrder:
        """Schedule the work order."""
        work_order = self.get_work_order(work_order_id)

        if work_order.status not in [WorkOrder.Status.DRAFT]:
            from . import WorkOrderStateError
            raise WorkOrderStateError(f"Cannot plan work order in {work_order.status} status")

        work_order.plan(scheduled_start, scheduled_end)
        logger.info(f"Planned work order {work_order.work_order_number}")
        return work_order

    def approve(
        self,
        work_order_id: uuid.UUID,
        approved_by: uuid.UUID,
        approved_by_name: str = None,
        notes: str = None
    ) -> WorkOrder:
        """Approve the work order."""
        work_order = self.get_work_order(work_order_id)

        if work_order.status not in [WorkOrder.Status.PLANNED]:
            from . import WorkOrderStateError
            raise WorkOrderStateError(f"Cannot approve work order in {work_order.status} status")

        work_order.approve(approved_by, approved_by_name, notes)
        logger.info(f"Approved work order {work_order.work_order_number}")
        return work_order

    def start(
        self,
        work_order_id: uuid.UUID,
        started_by: uuid.UUID = None,
        aircraft_hours: Decimal = None
    ) -> WorkOrder:
        """Start work on the work order."""
        work_order = self.get_work_order(work_order_id)

        if work_order.status not in [WorkOrder.Status.APPROVED, WorkOrder.Status.PLANNED]:
            from . import WorkOrderStateError
            raise WorkOrderStateError(f"Cannot start work order in {work_order.status} status")

        work_order.start(started_by, aircraft_hours)
        logger.info(f"Started work order {work_order.work_order_number}")
        return work_order

    def hold(self, work_order_id: uuid.UUID, reason: str) -> WorkOrder:
        """Put work order on hold."""
        work_order = self.get_work_order(work_order_id)

        if work_order.status != WorkOrder.Status.IN_PROGRESS:
            from . import WorkOrderStateError
            raise WorkOrderStateError(f"Cannot hold work order in {work_order.status} status")

        work_order.hold(reason)
        logger.info(f"Put work order {work_order.work_order_number} on hold: {reason}")
        return work_order

    def resume(self, work_order_id: uuid.UUID) -> WorkOrder:
        """Resume work order from hold."""
        work_order = self.get_work_order(work_order_id)

        if work_order.status != WorkOrder.Status.ON_HOLD:
            from . import WorkOrderStateError
            raise WorkOrderStateError(f"Cannot resume work order in {work_order.status} status")

        work_order.resume()
        logger.info(f"Resumed work order {work_order.work_order_number}")
        return work_order

    @transaction.atomic
    def complete(
        self,
        work_order_id: uuid.UUID,
        completed_by: uuid.UUID,
        completed_by_name: str = None,
        notes: str = None,
        findings: str = None,
        aircraft_hours: Decimal = None,
        actual_hours: Decimal = None,
        actual_cost: Decimal = None
    ) -> WorkOrder:
        """Complete the work order."""
        work_order = self.get_work_order(work_order_id)

        if work_order.status != WorkOrder.Status.IN_PROGRESS:
            from . import WorkOrderStateError
            raise WorkOrderStateError(f"Cannot complete work order in {work_order.status} status")

        # Verify all tasks are completed
        incomplete_tasks = work_order.tasks.exclude(
            status__in=[WorkOrderTask.Status.COMPLETED, WorkOrderTask.Status.SKIPPED]
        ).count()

        if incomplete_tasks > 0:
            from . import WorkOrderStateError
            raise WorkOrderStateError(f"{incomplete_tasks} tasks are not completed")

        if actual_hours:
            work_order.actual_hours = actual_hours
        if actual_cost:
            work_order.actual_cost = actual_cost

        work_order.complete(
            completed_by=completed_by,
            completed_by_name=completed_by_name,
            notes=notes,
            findings=findings,
            aircraft_hours=aircraft_hours
        )

        logger.info(f"Completed work order {work_order.work_order_number}")
        return work_order

    def cancel(
        self,
        work_order_id: uuid.UUID,
        reason: str,
        cancelled_by: uuid.UUID = None
    ) -> WorkOrder:
        """Cancel the work order."""
        work_order = self.get_work_order(work_order_id)

        if work_order.status == WorkOrder.Status.COMPLETED:
            from . import WorkOrderStateError
            raise WorkOrderStateError("Cannot cancel completed work order")

        work_order.cancel(reason, cancelled_by)
        logger.info(f"Cancelled work order {work_order.work_order_number}: {reason}")
        return work_order

    # ==========================================================================
    # Task Management
    # ==========================================================================

    def add_task(
        self,
        work_order_id: uuid.UUID,
        title: str,
        description: str = None,
        instructions: str = None,
        maintenance_item_id: uuid.UUID = None,
        estimated_hours: Decimal = None,
        sequence: int = None
    ) -> WorkOrderTask:
        """Add a task to a work order."""
        work_order = self.get_work_order(work_order_id)

        if sequence is None:
            sequence = work_order.tasks.count() + 1

        task = WorkOrderTask.objects.create(
            work_order=work_order,
            sequence=sequence,
            title=title,
            description=description,
            instructions=instructions,
            maintenance_item_id=maintenance_item_id,
            estimated_hours=estimated_hours,
        )

        return task

    def complete_task(
        self,
        task_id: uuid.UUID,
        completed_by: uuid.UUID,
        notes: str = None,
        hours: Decimal = None
    ) -> WorkOrderTask:
        """Complete a task."""
        try:
            task = WorkOrderTask.objects.select_related('work_order').get(id=task_id)
        except WorkOrderTask.DoesNotExist:
            from . import WorkOrderNotFoundError
            raise WorkOrderNotFoundError(f"Task {task_id} not found")

        task.complete(completed_by, notes, hours)
        return task

    def sign_off_task(self, task_id: uuid.UUID, signed_by: uuid.UUID) -> WorkOrderTask:
        """Sign off on a completed task."""
        try:
            task = WorkOrderTask.objects.get(id=task_id)
        except WorkOrderTask.DoesNotExist:
            from . import WorkOrderNotFoundError
            raise WorkOrderNotFoundError(f"Task {task_id} not found")

        if task.status != WorkOrderTask.Status.COMPLETED:
            from . import WorkOrderStateError
            raise WorkOrderStateError("Can only sign off completed tasks")

        task.sign_off(signed_by)
        return task

    def _create_tasks_from_items(
        self,
        work_order: WorkOrder,
        item_ids: List[uuid.UUID]
    ) -> List[WorkOrderTask]:
        """Create tasks from maintenance items."""
        tasks = []
        items = MaintenanceItem.objects.filter(id__in=item_ids)

        for i, item in enumerate(items, 1):
            task = WorkOrderTask.objects.create(
                work_order=work_order,
                sequence=i,
                title=item.name,
                description=item.description,
                maintenance_item_id=item.id,
                estimated_hours=item.estimated_labor_hours,
            )
            tasks.append(task)

        return tasks

    # ==========================================================================
    # Statistics
    # ==========================================================================

    def get_statistics(
        self,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID = None
    ) -> Dict[str, Any]:
        """Get work order statistics."""
        queryset = WorkOrder.objects.filter(organization_id=organization_id)
        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        # Count by status
        open_count = queryset.filter(
            status__in=[
                WorkOrder.Status.DRAFT,
                WorkOrder.Status.PLANNED,
                WorkOrder.Status.APPROVED,
                WorkOrder.Status.IN_PROGRESS,
                WorkOrder.Status.ON_HOLD
            ]
        ).count()

        in_progress = queryset.filter(status=WorkOrder.Status.IN_PROGRESS).count()
        on_hold = queryset.filter(status=WorkOrder.Status.ON_HOLD).count()

        # AOG count
        aog_count = queryset.filter(
            priority=WorkOrder.Priority.AOG,
            status__in=[
                WorkOrder.Status.DRAFT,
                WorkOrder.Status.PLANNED,
                WorkOrder.Status.IN_PROGRESS
            ]
        ).count()

        # Overdue
        overdue_count = queryset.filter(
            scheduled_end__lt=timezone.now(),
            status__in=[
                WorkOrder.Status.PLANNED,
                WorkOrder.Status.IN_PROGRESS
            ]
        ).count()

        # Cost totals
        cost_data = queryset.filter(
            status=WorkOrder.Status.COMPLETED
        ).aggregate(
            total_labor=Sum('actual_cost'),
            total_parts=Sum('actual_parts_cost'),
            total_hours=Sum('actual_hours'),
        )

        return {
            'open_count': open_count,
            'in_progress_count': in_progress,
            'on_hold_count': on_hold,
            'aog_count': aog_count,
            'overdue_count': overdue_count,
            'total_labor_cost': float(cost_data['total_labor'] or 0),
            'total_parts_cost': float(cost_data['total_parts'] or 0),
            'total_hours': float(cost_data['total_hours'] or 0),
        }
