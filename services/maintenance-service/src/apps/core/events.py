# services/maintenance-service/src/apps/core/events.py
"""
Maintenance Service Events

Event definitions for inter-service communication.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal types."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class MaintenanceEventTypes:
    """Event type constants for maintenance service."""

    # Maintenance Item Events
    ITEM_CREATED = 'maintenance.item.created'
    ITEM_UPDATED = 'maintenance.item.updated'
    ITEM_COMPLIANCE_RECORDED = 'maintenance.item.compliance_recorded'
    ITEM_DEFERRED = 'maintenance.item.deferred'
    ITEM_STATUS_CHANGED = 'maintenance.item.status_changed'

    # Work Order Events
    WORK_ORDER_CREATED = 'maintenance.work_order.created'
    WORK_ORDER_PLANNED = 'maintenance.work_order.planned'
    WORK_ORDER_APPROVED = 'maintenance.work_order.approved'
    WORK_ORDER_STARTED = 'maintenance.work_order.started'
    WORK_ORDER_ON_HOLD = 'maintenance.work_order.on_hold'
    WORK_ORDER_RESUMED = 'maintenance.work_order.resumed'
    WORK_ORDER_COMPLETED = 'maintenance.work_order.completed'
    WORK_ORDER_CANCELLED = 'maintenance.work_order.cancelled'

    # Task Events
    TASK_CREATED = 'maintenance.task.created'
    TASK_COMPLETED = 'maintenance.task.completed'
    TASK_SIGNED_OFF = 'maintenance.task.signed_off'

    # Parts Events
    PART_RECEIVED = 'maintenance.part.received'
    PART_ISSUED = 'maintenance.part.issued'
    PART_ADJUSTED = 'maintenance.part.adjusted'
    PART_LOW_STOCK = 'maintenance.part.low_stock'

    # Compliance Events
    DIRECTIVE_CREATED = 'maintenance.directive.created'
    DIRECTIVE_COMPLIANCE_RECORDED = 'maintenance.directive.compliance_recorded'
    DIRECTIVE_OVERDUE = 'maintenance.directive.overdue'
    DIRECTIVE_DUE_SOON = 'maintenance.directive.due_soon'

    # Aircraft Status Events
    AIRCRAFT_MAINTENANCE_DUE = 'maintenance.aircraft.maintenance_due'
    AIRCRAFT_GROUNDED = 'maintenance.aircraft.grounded'
    AIRCRAFT_CLEARED = 'maintenance.aircraft.cleared'


class MaintenanceEventPublisher:
    """
    Publisher for maintenance service events.

    Supports multiple message brokers (Redis, RabbitMQ, etc.)
    """

    def __init__(self, broker_url: str = None):
        self.broker_url = broker_url
        self._connection = None

    def _get_connection(self):
        """Get or create broker connection."""
        if self._connection is None:
            # Placeholder for actual broker connection
            # In production, this would connect to Redis/RabbitMQ
            pass
        return self._connection

    def _serialize_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """Serialize event to JSON."""
        event = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'maintenance-service',
            'data': data,
        }
        return json.dumps(event, cls=DecimalEncoder)

    def publish(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Publish an event to the message broker."""
        try:
            message = self._serialize_event(event_type, data)
            logger.info(f"Publishing event: {event_type}")
            logger.debug(f"Event data: {message}")

            # Placeholder for actual publishing
            # In production: self._get_connection().publish(channel, message)

            return True
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            return False

    # ==========================================================================
    # Maintenance Item Events
    # ==========================================================================

    def item_created(self, item) -> bool:
        """Publish maintenance item created event."""
        return self.publish(MaintenanceEventTypes.ITEM_CREATED, {
            'item_id': str(item.id),
            'organization_id': str(item.organization_id),
            'aircraft_id': str(item.aircraft_id) if item.aircraft_id else None,
            'name': item.name,
            'code': item.code,
            'category': item.category,
            'is_mandatory': item.is_mandatory,
            'next_due_date': item.next_due_date.isoformat() if item.next_due_date else None,
            'next_due_hours': item.next_due_hours,
        })

    def item_compliance_recorded(self, item, log) -> bool:
        """Publish compliance recorded event."""
        return self.publish(MaintenanceEventTypes.ITEM_COMPLIANCE_RECORDED, {
            'item_id': str(item.id),
            'log_id': str(log.id),
            'organization_id': str(item.organization_id),
            'aircraft_id': str(item.aircraft_id) if item.aircraft_id else None,
            'name': item.name,
            'performed_date': log.performed_date.isoformat(),
            'aircraft_hours': log.aircraft_hours,
            'next_due_date': item.next_due_date.isoformat() if item.next_due_date else None,
            'next_due_hours': item.next_due_hours,
        })

    def item_status_changed(
        self,
        item,
        old_status: str,
        new_status: str
    ) -> bool:
        """Publish item status changed event."""
        return self.publish(MaintenanceEventTypes.ITEM_STATUS_CHANGED, {
            'item_id': str(item.id),
            'organization_id': str(item.organization_id),
            'aircraft_id': str(item.aircraft_id) if item.aircraft_id else None,
            'name': item.name,
            'old_status': old_status,
            'new_status': new_status,
            'is_mandatory': item.is_mandatory,
        })

    # ==========================================================================
    # Work Order Events
    # ==========================================================================

    def work_order_created(self, work_order) -> bool:
        """Publish work order created event."""
        return self.publish(MaintenanceEventTypes.WORK_ORDER_CREATED, {
            'work_order_id': str(work_order.id),
            'work_order_number': work_order.work_order_number,
            'organization_id': str(work_order.organization_id),
            'aircraft_id': str(work_order.aircraft_id),
            'title': work_order.title,
            'work_order_type': work_order.work_order_type,
            'priority': work_order.priority,
            'created_by': str(work_order.created_by) if work_order.created_by else None,
        })

    def work_order_status_changed(
        self,
        work_order,
        old_status: str,
        new_status: str,
        changed_by: Optional[UUID] = None
    ) -> bool:
        """Publish work order status changed event."""
        event_map = {
            'planned': MaintenanceEventTypes.WORK_ORDER_PLANNED,
            'approved': MaintenanceEventTypes.WORK_ORDER_APPROVED,
            'in_progress': MaintenanceEventTypes.WORK_ORDER_STARTED,
            'on_hold': MaintenanceEventTypes.WORK_ORDER_ON_HOLD,
            'completed': MaintenanceEventTypes.WORK_ORDER_COMPLETED,
            'cancelled': MaintenanceEventTypes.WORK_ORDER_CANCELLED,
        }

        event_type = event_map.get(new_status, f'maintenance.work_order.{new_status}')

        return self.publish(event_type, {
            'work_order_id': str(work_order.id),
            'work_order_number': work_order.work_order_number,
            'organization_id': str(work_order.organization_id),
            'aircraft_id': str(work_order.aircraft_id),
            'old_status': old_status,
            'new_status': new_status,
            'changed_by': str(changed_by) if changed_by else None,
            'priority': work_order.priority,
        })

    def work_order_completed(self, work_order) -> bool:
        """Publish work order completed event."""
        return self.publish(MaintenanceEventTypes.WORK_ORDER_COMPLETED, {
            'work_order_id': str(work_order.id),
            'work_order_number': work_order.work_order_number,
            'organization_id': str(work_order.organization_id),
            'aircraft_id': str(work_order.aircraft_id),
            'title': work_order.title,
            'completed_at': work_order.actual_end.isoformat() if work_order.actual_end else None,
            'actual_hours': work_order.actual_hours,
            'actual_cost': work_order.actual_cost,
            'completed_by': str(work_order.completed_by) if work_order.completed_by else None,
        })

    # ==========================================================================
    # Parts Events
    # ==========================================================================

    def part_received(self, part, transaction) -> bool:
        """Publish part received event."""
        return self.publish(MaintenanceEventTypes.PART_RECEIVED, {
            'part_id': str(part.id),
            'transaction_id': str(transaction.id),
            'organization_id': str(part.organization_id),
            'part_number': part.part_number,
            'quantity': transaction.quantity,
            'new_quantity': part.quantity_on_hand,
        })

    def part_issued(self, part, transaction) -> bool:
        """Publish part issued event."""
        return self.publish(MaintenanceEventTypes.PART_ISSUED, {
            'part_id': str(part.id),
            'transaction_id': str(transaction.id),
            'organization_id': str(part.organization_id),
            'part_number': part.part_number,
            'quantity': transaction.quantity,
            'remaining_quantity': part.quantity_on_hand,
            'work_order_id': str(transaction.work_order_id) if transaction.work_order_id else None,
            'aircraft_id': str(transaction.aircraft_id) if transaction.aircraft_id else None,
        })

    def part_low_stock(self, part) -> bool:
        """Publish low stock alert event."""
        return self.publish(MaintenanceEventTypes.PART_LOW_STOCK, {
            'part_id': str(part.id),
            'organization_id': str(part.organization_id),
            'part_number': part.part_number,
            'description': part.description,
            'quantity_available': part.quantity_available,
            'minimum_quantity': part.minimum_quantity,
            'reorder_quantity': part.reorder_quantity,
        })

    # ==========================================================================
    # Compliance Events
    # ==========================================================================

    def directive_created(self, directive) -> bool:
        """Publish directive created event."""
        return self.publish(MaintenanceEventTypes.DIRECTIVE_CREATED, {
            'directive_id': str(directive.id),
            'organization_id': str(directive.organization_id),
            'aircraft_id': str(directive.aircraft_id),
            'directive_type': directive.directive_type,
            'directive_number': directive.directive_number,
            'title': directive.title,
            'effective_date': directive.effective_date.isoformat() if directive.effective_date else None,
            'compliance_required': directive.compliance_required,
        })

    def directive_compliance_recorded(self, directive) -> bool:
        """Publish directive compliance recorded event."""
        return self.publish(MaintenanceEventTypes.DIRECTIVE_COMPLIANCE_RECORDED, {
            'directive_id': str(directive.id),
            'organization_id': str(directive.organization_id),
            'aircraft_id': str(directive.aircraft_id),
            'directive_type': directive.directive_type,
            'directive_number': directive.directive_number,
            'compliance_date': directive.last_compliance_date.isoformat() if directive.last_compliance_date else None,
            'compliance_hours': directive.last_compliance_hours,
            'next_due_date': directive.next_due_date.isoformat() if directive.next_due_date else None,
            'next_due_hours': directive.next_due_hours,
        })

    def directive_overdue(self, directive) -> bool:
        """Publish directive overdue alert event."""
        return self.publish(MaintenanceEventTypes.DIRECTIVE_OVERDUE, {
            'directive_id': str(directive.id),
            'organization_id': str(directive.organization_id),
            'aircraft_id': str(directive.aircraft_id),
            'directive_type': directive.directive_type,
            'directive_number': directive.directive_number,
            'title': directive.title,
            'due_date': directive.next_due_date.isoformat() if directive.next_due_date else None,
            'due_hours': directive.next_due_hours,
        })

    # ==========================================================================
    # Aircraft Status Events
    # ==========================================================================

    def aircraft_maintenance_due(
        self,
        aircraft_id: UUID,
        organization_id: UUID,
        overdue_items: list,
        due_items: list
    ) -> bool:
        """Publish aircraft maintenance due event."""
        return self.publish(MaintenanceEventTypes.AIRCRAFT_MAINTENANCE_DUE, {
            'aircraft_id': str(aircraft_id),
            'organization_id': str(organization_id),
            'overdue_count': len(overdue_items),
            'due_count': len(due_items),
            'overdue_items': [
                {'id': str(item.id), 'name': item.name, 'is_mandatory': item.is_mandatory}
                for item in overdue_items
            ],
            'due_items': [
                {'id': str(item.id), 'name': item.name, 'is_mandatory': item.is_mandatory}
                for item in due_items
            ],
        })

    def aircraft_grounded(
        self,
        aircraft_id: UUID,
        organization_id: UUID,
        reason: str,
        grounding_items: list
    ) -> bool:
        """Publish aircraft grounded event."""
        return self.publish(MaintenanceEventTypes.AIRCRAFT_GROUNDED, {
            'aircraft_id': str(aircraft_id),
            'organization_id': str(organization_id),
            'reason': reason,
            'grounding_items': [
                {'id': str(item.id), 'name': item.name, 'type': getattr(item, 'directive_type', item.category)}
                for item in grounding_items
            ],
        })

    def aircraft_cleared(
        self,
        aircraft_id: UUID,
        organization_id: UUID
    ) -> bool:
        """Publish aircraft cleared for flight event."""
        return self.publish(MaintenanceEventTypes.AIRCRAFT_CLEARED, {
            'aircraft_id': str(aircraft_id),
            'organization_id': str(organization_id),
            'cleared_at': datetime.utcnow().isoformat(),
        })


# Singleton instance
event_publisher = MaintenanceEventPublisher()
