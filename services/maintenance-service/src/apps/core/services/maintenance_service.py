# services/maintenance-service/src/apps/core/services/maintenance_service.py
"""
Maintenance Service

Core service for maintenance item management.
"""

import uuid
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

from django.db import transaction
from django.db.models import Q, Count
from django.core.cache import cache

from apps.core.models import MaintenanceItem, MaintenanceLog

logger = logging.getLogger(__name__)


class MaintenanceService:
    """
    Service for managing maintenance items and logs.

    Handles:
    - Maintenance item CRUD
    - Compliance tracking
    - Status calculations
    - Maintenance logging
    """

    CACHE_TTL = 300  # 5 minutes

    # ==========================================================================
    # Maintenance Item CRUD
    # ==========================================================================

    @transaction.atomic
    def create_item(
        self,
        organization_id: uuid.UUID,
        name: str,
        category: str,
        aircraft_id: uuid.UUID = None,
        **kwargs
    ) -> MaintenanceItem:
        """Create a new maintenance item."""
        item = MaintenanceItem.objects.create(
            organization_id=organization_id,
            aircraft_id=aircraft_id,
            name=name,
            category=category,
            **kwargs
        )

        logger.info(f"Created maintenance item: {item.name} ({item.id})")
        return item

    def get_item(self, item_id: uuid.UUID) -> MaintenanceItem:
        """Get a maintenance item by ID."""
        try:
            return MaintenanceItem.objects.get(id=item_id)
        except MaintenanceItem.DoesNotExist:
            from . import MaintenanceItemNotFoundError
            raise MaintenanceItemNotFoundError(f"Maintenance item {item_id} not found")

    def list_items(
        self,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID = None,
        category: str = None,
        compliance_status: str = None,
        status: str = None,
        is_mandatory: bool = None,
        search: str = None
    ) -> List[MaintenanceItem]:
        """List maintenance items with filters."""
        queryset = MaintenanceItem.objects.filter(organization_id=organization_id)

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)
        if category:
            queryset = queryset.filter(category=category)
        if compliance_status:
            queryset = queryset.filter(compliance_status=compliance_status)
        if status:
            queryset = queryset.filter(status=status)
        if is_mandatory is not None:
            queryset = queryset.filter(is_mandatory=is_mandatory)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )

        return list(queryset.order_by('next_due_hours', 'next_due_date'))

    @transaction.atomic
    def update_item(self, item_id: uuid.UUID, **kwargs) -> MaintenanceItem:
        """Update a maintenance item."""
        item = self.get_item(item_id)

        allowed_fields = [
            'name', 'code', 'description', 'category', 'item_type',
            'ata_chapter', 'component_type', 'is_mandatory',
            'regulatory_reference', 'interval_hours', 'interval_days',
            'interval_months', 'warning_hours', 'warning_days',
            'critical_hours', 'critical_days', 'estimated_labor_hours',
            'estimated_cost', 'documentation_url', 'notes', 'status'
        ]

        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(item, field, value)

        item.save()
        return item

    def delete_item(self, item_id: uuid.UUID) -> None:
        """Delete a maintenance item."""
        item = self.get_item(item_id)
        item.status = MaintenanceItem.Status.INACTIVE
        item.save(update_fields=['status', 'updated_at'])

    # ==========================================================================
    # Compliance Management
    # ==========================================================================

    @transaction.atomic
    def record_compliance(
        self,
        item_id: uuid.UUID,
        performed_date: date,
        aircraft_hours: Decimal = None,
        aircraft_cycles: int = None,
        performed_by: str = None,
        performed_by_id: uuid.UUID = None,
        work_performed: str = None,
        work_order_id: uuid.UUID = None,
        parts_used: List[Dict] = None,
        labor_hours: Decimal = None,
        notes: str = None,
        **kwargs
    ) -> MaintenanceLog:
        """Record maintenance compliance and create log entry."""
        item = self.get_item(item_id)

        # Create maintenance log
        log = MaintenanceLog.objects.create(
            organization_id=item.organization_id,
            aircraft_id=item.aircraft_id,
            maintenance_item_id=item.id,
            work_order_id=work_order_id,
            title=item.name,
            work_performed=work_performed or f"Completed {item.name}",
            category=item.category,
            performed_date=performed_date,
            aircraft_hours=aircraft_hours,
            aircraft_cycles=aircraft_cycles,
            performed_by=performed_by or 'Unknown',
            performed_by_id=performed_by_id,
            parts_used=parts_used or [],
            labor_hours=labor_hours,
            notes=notes,
            created_by=performed_by_id or uuid.uuid4(),
            **kwargs
        )

        # Update maintenance item
        item.record_compliance(
            done_date=performed_date,
            done_hours=aircraft_hours,
            done_cycles=aircraft_cycles,
            done_by=performed_by,
            notes=notes,
            work_order_id=work_order_id
        )

        # Set next due on log
        log.next_due_date = item.next_due_date
        log.next_due_hours = item.next_due_hours
        log.next_due_cycles = item.next_due_cycles
        log.save(update_fields=['next_due_date', 'next_due_hours', 'next_due_cycles'])

        logger.info(
            f"Recorded compliance for {item.name}: "
            f"hours={aircraft_hours}, date={performed_date}"
        )

        return log

    def update_compliance_status(
        self,
        aircraft_id: uuid.UUID,
        current_hours: Decimal,
        current_cycles: int = None
    ) -> Dict[str, int]:
        """Update compliance status for all items on an aircraft."""
        items = MaintenanceItem.objects.filter(
            aircraft_id=aircraft_id,
            status=MaintenanceItem.Status.ACTIVE
        )

        counts = {
            'updated': 0,
            'overdue': 0,
            'due': 0,
            'due_soon': 0
        }

        for item in items:
            old_status = item.compliance_status
            item.calculate_remaining(current_hours, current_cycles)
            counts['updated'] += 1

            if item.compliance_status == MaintenanceItem.ComplianceStatus.OVERDUE:
                counts['overdue'] += 1
            elif item.compliance_status == MaintenanceItem.ComplianceStatus.DUE:
                counts['due'] += 1
            elif item.compliance_status == MaintenanceItem.ComplianceStatus.DUE_SOON:
                counts['due_soon'] += 1

        logger.info(
            f"Updated compliance for aircraft {aircraft_id}: "
            f"{counts['updated']} items, {counts['overdue']} overdue"
        )

        return counts

    # ==========================================================================
    # Aircraft Status
    # ==========================================================================

    def get_aircraft_maintenance_status(
        self,
        aircraft_id: uuid.UUID,
        current_hours: Decimal = None
    ) -> Dict[str, Any]:
        """Get comprehensive maintenance status for an aircraft."""
        cache_key = f"maintenance_status:{aircraft_id}"
        cached = cache.get(cache_key)
        if cached and current_hours is None:
            return cached

        items = MaintenanceItem.objects.filter(
            aircraft_id=aircraft_id,
            status=MaintenanceItem.Status.ACTIVE
        )

        # Update remaining if hours provided
        if current_hours is not None:
            for item in items:
                item.calculate_remaining(current_hours)

        overdue = []
        due = []
        due_soon = []

        for item in items:
            item_data = self._serialize_item(item)

            if item.compliance_status == MaintenanceItem.ComplianceStatus.OVERDUE:
                overdue.append(item_data)
            elif item.compliance_status == MaintenanceItem.ComplianceStatus.DUE:
                due.append(item_data)
            elif item.compliance_status == MaintenanceItem.ComplianceStatus.DUE_SOON:
                due_soon.append(item_data)

        result = {
            'aircraft_id': str(aircraft_id),
            'current_hours': float(current_hours) if current_hours else None,
            'overdue': overdue,
            'overdue_count': len(overdue),
            'due': due,
            'due_count': len(due),
            'due_soon': due_soon,
            'due_soon_count': len(due_soon),
            'total_items': items.count(),
            'is_maintenance_required': len(overdue) > 0 or len(due) > 0,
            'is_grounding_maintenance': any(
                item.is_mandatory and item.compliance_status == MaintenanceItem.ComplianceStatus.OVERDUE
                for item in items
            ),
        }

        cache.set(cache_key, result, self.CACHE_TTL)
        return result

    def get_upcoming_maintenance(
        self,
        aircraft_id: uuid.UUID,
        hours_ahead: int = 50,
        days_ahead: int = 90
    ) -> List[Dict[str, Any]]:
        """Get upcoming maintenance items."""
        items = MaintenanceItem.get_upcoming(
            organization_id=None,  # Will be filtered by aircraft
            aircraft_id=aircraft_id,
            hours_ahead=hours_ahead,
            days_ahead=days_ahead
        )

        return [self._serialize_item(item) for item in items]

    # ==========================================================================
    # Dashboard / Statistics
    # ==========================================================================

    def get_dashboard_stats(
        self,
        organization_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get maintenance dashboard statistics."""
        items = MaintenanceItem.objects.filter(
            organization_id=organization_id,
            status=MaintenanceItem.Status.ACTIVE
        )

        stats = items.aggregate(
            total=Count('id'),
            overdue=Count('id', filter=Q(compliance_status=MaintenanceItem.ComplianceStatus.OVERDUE)),
            due=Count('id', filter=Q(compliance_status=MaintenanceItem.ComplianceStatus.DUE)),
            due_soon=Count('id', filter=Q(compliance_status=MaintenanceItem.ComplianceStatus.DUE_SOON)),
        )

        # Get by category
        by_category = items.values('category').annotate(
            count=Count('id')
        ).order_by('category')

        # Get recent logs
        recent_logs = MaintenanceLog.objects.filter(
            organization_id=organization_id
        ).order_by('-performed_date')[:10]

        return {
            'total_items': stats['total'],
            'overdue_count': stats['overdue'],
            'due_count': stats['due'],
            'due_soon_count': stats['due_soon'],
            'compliant_count': stats['total'] - stats['overdue'] - stats['due'] - stats['due_soon'],
            'by_category': {item['category']: item['count'] for item in by_category},
            'recent_maintenance': [
                {
                    'id': str(log.id),
                    'title': log.title,
                    'aircraft_id': str(log.aircraft_id),
                    'performed_date': log.performed_date.isoformat(),
                }
                for log in recent_logs
            ]
        }

    # ==========================================================================
    # Maintenance Log
    # ==========================================================================

    def get_log(self, log_id: uuid.UUID) -> MaintenanceLog:
        """Get a maintenance log by ID."""
        try:
            return MaintenanceLog.objects.get(id=log_id)
        except MaintenanceLog.DoesNotExist:
            from . import MaintenanceServiceError
            raise MaintenanceServiceError(f"Maintenance log {log_id} not found")

    def list_logs(
        self,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID = None,
        category: str = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100
    ) -> List[MaintenanceLog]:
        """List maintenance logs."""
        queryset = MaintenanceLog.objects.filter(organization_id=organization_id)

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)
        if category:
            queryset = queryset.filter(category=category)
        if start_date:
            queryset = queryset.filter(performed_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(performed_date__lte=end_date)

        return list(queryset.order_by('-performed_date')[:limit])

    def get_aircraft_history(
        self,
        aircraft_id: uuid.UUID,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get maintenance history for an aircraft."""
        logs = MaintenanceLog.get_aircraft_history(aircraft_id, limit=limit)

        return [
            {
                'id': str(log.id),
                'log_number': log.log_number,
                'title': log.title,
                'category': log.category,
                'performed_date': log.performed_date.isoformat(),
                'aircraft_hours': float(log.aircraft_hours) if log.aircraft_hours else None,
                'performed_by': log.performed_by,
                'total_cost': float(log.total_cost) if log.total_cost else None,
            }
            for log in logs
        ]

    # ==========================================================================
    # Template Management
    # ==========================================================================

    def create_from_template(
        self,
        template_id: uuid.UUID,
        aircraft_id: uuid.UUID,
        initial_hours: Decimal = None,
        initial_date: date = None
    ) -> MaintenanceItem:
        """Create a maintenance item for an aircraft from a template."""
        template = self.get_item(template_id)

        if not template.is_template:
            from . import MaintenanceServiceError
            raise MaintenanceServiceError("Item is not a template")

        return MaintenanceItem.create_from_template(
            template=template,
            aircraft_id=aircraft_id,
            initial_hours=initial_hours,
            initial_date=initial_date
        )

    def apply_templates_to_aircraft(
        self,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID,
        template_ids: List[uuid.UUID],
        initial_hours: Decimal = None,
        initial_date: date = None
    ) -> List[MaintenanceItem]:
        """Apply multiple templates to an aircraft."""
        created = []
        for template_id in template_ids:
            item = self.create_from_template(
                template_id=template_id,
                aircraft_id=aircraft_id,
                initial_hours=initial_hours,
                initial_date=initial_date or date.today()
            )
            created.append(item)

        logger.info(f"Applied {len(created)} templates to aircraft {aircraft_id}")
        return created

    # ==========================================================================
    # Helpers
    # ==========================================================================

    def _serialize_item(self, item: MaintenanceItem) -> Dict[str, Any]:
        """Serialize maintenance item to dict."""
        return {
            'id': str(item.id),
            'name': item.name,
            'code': item.code,
            'category': item.category,
            'item_type': item.item_type,
            'compliance_status': item.compliance_status,
            'is_mandatory': item.is_mandatory,
            'next_due_date': item.next_due_date.isoformat() if item.next_due_date else None,
            'next_due_hours': float(item.next_due_hours) if item.next_due_hours else None,
            'next_due_cycles': item.next_due_cycles,
            'remaining_hours': float(item.remaining_hours) if item.remaining_hours else None,
            'remaining_days': item.remaining_days,
            'remaining_cycles': item.remaining_cycles,
            'estimated_cost': float(item.estimated_cost) if item.estimated_cost else None,
        }
