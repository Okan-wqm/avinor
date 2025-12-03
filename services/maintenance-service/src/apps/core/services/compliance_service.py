# services/maintenance-service/src/apps/core/services/compliance_service.py
"""
Compliance Service

Manages AD/SB tracking and compliance.
"""

import uuid
import logging
from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any, List

from django.db import transaction
from django.db.models import Q, Count

from apps.core.models import ADSBTracking, MaintenanceItem

logger = logging.getLogger(__name__)


class ComplianceService:
    """
    Service for managing AD/SB compliance.

    Handles:
    - AD/SB tracking CRUD
    - Compliance recording
    - Status updates
    - Compliance reporting
    """

    # ==========================================================================
    # AD/SB CRUD
    # ==========================================================================

    @transaction.atomic
    def create_directive(
        self,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID,
        directive_type: str,
        directive_number: str,
        title: str,
        **kwargs
    ) -> ADSBTracking:
        """Create a new AD/SB tracking record."""
        directive = ADSBTracking.objects.create(
            organization_id=organization_id,
            aircraft_id=aircraft_id,
            directive_type=directive_type,
            directive_number=directive_number.upper(),
            title=title,
            **kwargs
        )

        # Create linked maintenance item if recurring
        if directive.is_recurring or directive.compliance_required:
            self._create_linked_maintenance_item(directive)

        logger.info(f"Created {directive_type} {directive_number} for aircraft {aircraft_id}")
        return directive

    def get_directive(self, directive_id: uuid.UUID) -> ADSBTracking:
        """Get a directive by ID."""
        try:
            return ADSBTracking.objects.get(id=directive_id)
        except ADSBTracking.DoesNotExist:
            from . import ComplianceError
            raise ComplianceError(f"Directive {directive_id} not found")

    def list_directives(
        self,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID = None,
        directive_type: str = None,
        compliance_status: str = None,
        is_applicable: bool = None
    ) -> List[ADSBTracking]:
        """List directives with filters."""
        queryset = ADSBTracking.objects.filter(organization_id=organization_id)

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)
        if directive_type:
            queryset = queryset.filter(directive_type=directive_type)
        if compliance_status:
            queryset = queryset.filter(compliance_status=compliance_status)
        if is_applicable is not None:
            queryset = queryset.filter(is_applicable=is_applicable)

        return list(queryset.order_by('-effective_date'))

    @transaction.atomic
    def update_directive(self, directive_id: uuid.UUID, **kwargs) -> ADSBTracking:
        """Update a directive."""
        directive = self.get_directive(directive_id)

        allowed_fields = [
            'revision', 'title', 'description', 'applicability',
            'affected_serial_numbers', 'is_applicable', 'not_applicable_reason',
            'compliance_method', 'compliance_instructions', 'is_terminating',
            'terminating_action', 'initial_compliance_date', 'initial_compliance_hours',
            'is_recurring', 'recurring_interval_days', 'recurring_interval_hours',
            'directive_document_url', 'compliance_document_url', 'notes'
        ]

        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(directive, field, value)

        directive.save()
        return directive

    # ==========================================================================
    # Compliance Recording
    # ==========================================================================

    @transaction.atomic
    def record_compliance(
        self,
        directive_id: uuid.UUID,
        compliance_date: date,
        compliance_hours: Decimal = None,
        compliance_cycles: int = None,
        notes: str = None,
        work_order_id: uuid.UUID = None,
        performed_by: str = None
    ) -> ADSBTracking:
        """Record compliance with a directive."""
        directive = self.get_directive(directive_id)

        directive.record_compliance(
            compliance_date=compliance_date,
            compliance_hours=compliance_hours,
            compliance_cycles=compliance_cycles,
            notes=notes,
            work_order_id=work_order_id
        )

        # Update linked maintenance item
        if directive.maintenance_item_id:
            try:
                item = MaintenanceItem.objects.get(id=directive.maintenance_item_id)
                item.record_compliance(
                    done_date=compliance_date,
                    done_hours=compliance_hours,
                    done_cycles=compliance_cycles,
                    done_by=performed_by,
                    notes=notes,
                    work_order_id=work_order_id
                )
            except MaintenanceItem.DoesNotExist:
                pass

        logger.info(
            f"Recorded compliance for {directive.directive_type} "
            f"{directive.directive_number}"
        )

        return directive

    def mark_not_applicable(
        self,
        directive_id: uuid.UUID,
        reason: str
    ) -> ADSBTracking:
        """Mark a directive as not applicable."""
        directive = self.get_directive(directive_id)
        directive.mark_not_applicable(reason)

        logger.info(
            f"Marked {directive.directive_type} {directive.directive_number} "
            f"as N/A: {reason}"
        )

        return directive

    # ==========================================================================
    # Status Updates
    # ==========================================================================

    def update_compliance_status(
        self,
        aircraft_id: uuid.UUID,
        current_hours: Decimal,
        current_cycles: int = None
    ) -> Dict[str, int]:
        """Update compliance status for all directives on an aircraft."""
        directives = ADSBTracking.objects.filter(
            aircraft_id=aircraft_id,
            is_applicable=True,
            compliance_required=True
        ).exclude(
            compliance_status=ADSBTracking.ComplianceStatus.TERMINATED
        )

        counts = {
            'updated': 0,
            'pending': 0,
            'compliant': 0,
            'non_compliant': 0
        }

        for directive in directives:
            directive.calculate_remaining(current_hours, current_cycles)
            counts['updated'] += 1

            if directive.is_overdue:
                counts['non_compliant'] += 1
            elif directive.compliance_status == ADSBTracking.ComplianceStatus.PENDING:
                counts['pending'] += 1
            else:
                counts['compliant'] += 1

        logger.info(
            f"Updated compliance status for aircraft {aircraft_id}: "
            f"{counts['updated']} directives"
        )

        return counts

    # ==========================================================================
    # Queries
    # ==========================================================================

    def get_pending_directives(
        self,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID = None
    ) -> List[ADSBTracking]:
        """Get all pending directives."""
        return list(ADSBTracking.get_pending_directives(
            organization_id=organization_id,
            aircraft_id=aircraft_id
        ))

    def get_upcoming_compliance(
        self,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID = None,
        days_ahead: int = 30,
        hours_ahead: int = 50
    ) -> List[ADSBTracking]:
        """Get directives coming due."""
        return list(ADSBTracking.get_recurring_due(
            organization_id=organization_id,
            aircraft_id=aircraft_id,
            days_ahead=days_ahead,
            hours_ahead=hours_ahead
        ))

    def get_aircraft_compliance_status(
        self,
        aircraft_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get comprehensive compliance status for an aircraft."""
        directives = ADSBTracking.objects.filter(
            aircraft_id=aircraft_id,
            is_applicable=True
        )

        # Count by status
        status_counts = directives.values('compliance_status').annotate(
            count=Count('id')
        )

        # Get non-compliant
        non_compliant = list(directives.filter(
            compliance_status__in=[
                ADSBTracking.ComplianceStatus.PENDING,
                ADSBTracking.ComplianceStatus.NON_COMPLIANT
            ]
        ))

        # Get upcoming
        upcoming = list(directives.filter(
            compliance_status=ADSBTracking.ComplianceStatus.COMPLIANT,
            is_recurring=True
        ).filter(
            Q(remaining_hours__lte=50) | Q(remaining_days__lte=30)
        ))

        # Count by type
        by_type = directives.values('directive_type').annotate(
            count=Count('id')
        )

        return {
            'aircraft_id': str(aircraft_id),
            'total_directives': directives.count(),
            'status_summary': {item['compliance_status']: item['count'] for item in status_counts},
            'by_type': {item['directive_type']: item['count'] for item in by_type},
            'non_compliant': [
                {
                    'id': str(d.id),
                    'type': d.directive_type,
                    'number': d.directive_number,
                    'title': d.title,
                    'status': d.compliance_status,
                }
                for d in non_compliant
            ],
            'upcoming': [
                {
                    'id': str(d.id),
                    'type': d.directive_type,
                    'number': d.directive_number,
                    'remaining_hours': float(d.remaining_hours) if d.remaining_hours else None,
                    'remaining_days': d.remaining_days,
                }
                for d in upcoming
            ],
            'is_compliant': len(non_compliant) == 0,
        }

    # ==========================================================================
    # Statistics
    # ==========================================================================

    def get_compliance_statistics(
        self,
        organization_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get compliance statistics for an organization."""
        directives = ADSBTracking.objects.filter(
            organization_id=organization_id,
            is_applicable=True
        )

        total = directives.count()

        status_counts = directives.values('compliance_status').annotate(
            count=Count('id')
        )

        type_counts = directives.values('directive_type').annotate(
            count=Count('id')
        )

        # Non-compliant count
        non_compliant = directives.filter(
            compliance_status__in=[
                ADSBTracking.ComplianceStatus.PENDING,
                ADSBTracking.ComplianceStatus.NON_COMPLIANT
            ]
        ).count()

        return {
            'total_directives': total,
            'compliant': total - non_compliant,
            'non_compliant': non_compliant,
            'compliance_rate': round((total - non_compliant) / total * 100, 1) if total > 0 else 100,
            'by_status': {item['compliance_status']: item['count'] for item in status_counts},
            'by_type': {item['directive_type']: item['count'] for item in type_counts},
        }

    # ==========================================================================
    # Helpers
    # ==========================================================================

    def _create_linked_maintenance_item(self, directive: ADSBTracking) -> MaintenanceItem:
        """Create a linked maintenance item for a directive."""
        category = (
            MaintenanceItem.Category.AD
            if directive.directive_type == 'AD'
            else MaintenanceItem.Category.SB
        )

        item_type = (
            MaintenanceItem.ItemType.RECURRING
            if directive.is_recurring
            else MaintenanceItem.ItemType.ONE_TIME
        )

        item = MaintenanceItem.objects.create(
            organization_id=directive.organization_id,
            aircraft_id=directive.aircraft_id,
            name=f"{directive.directive_type} {directive.directive_number}",
            code=directive.directive_number,
            description=directive.title,
            category=category,
            item_type=item_type,
            is_mandatory=True,
            regulatory_reference=directive.directive_number,
            ad_number=directive.directive_number if directive.directive_type == 'AD' else None,
            sb_number=directive.directive_number if directive.directive_type == 'SB' else None,
            interval_hours=directive.recurring_interval_hours,
            interval_days=directive.recurring_interval_days,
            next_due_date=directive.initial_compliance_date,
            next_due_hours=directive.initial_compliance_hours,
            documentation_url=directive.directive_document_url,
        )

        # Link back
        directive.maintenance_item_id = item.id
        directive.save(update_fields=['maintenance_item_id'])

        return item
