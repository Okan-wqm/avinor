# services/aircraft-service/src/apps/core/services/squawk_service.py
"""
Squawk Service

Business logic for aircraft squawk/discrepancy management.
"""

import logging
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone

from apps.core.models import Aircraft, AircraftSquawk

logger = logging.getLogger(__name__)


class SquawkService:
    """
    Service class for squawk management operations.

    Handles:
    - Squawk creation and updates
    - Resolution workflow
    - Deferral management
    - Statistics and reporting
    """

    # ==========================================================================
    # CRUD Operations
    # ==========================================================================

    def create_squawk(
        self,
        aircraft_id: UUID,
        organization_id: UUID,
        reported_by_user_id: UUID,
        title: str,
        description: str,
        category: str,
        severity: str = 'minor',
        reported_by_name: str = None,
        flight_id: UUID = None,
        photos: List[str] = None,
        **kwargs
    ) -> AircraftSquawk:
        """
        Create a new squawk.

        Args:
            aircraft_id: Aircraft UUID
            organization_id: Organization UUID
            reported_by_user_id: User reporting the squawk
            title: Short title
            description: Detailed description
            category: Squawk category
            severity: Severity level
            reported_by_name: Reporter's name for display
            flight_id: Associated flight ID if any
            photos: List of photo URLs
            **kwargs: Additional squawk fields

        Returns:
            Created AircraftSquawk

        Raises:
            SquawkError: If creation fails
        """
        from apps.core.services import SquawkError, AircraftNotFoundError

        # Verify aircraft exists
        try:
            aircraft = Aircraft.objects.get(
                id=aircraft_id,
                organization_id=organization_id,
                deleted_at__isnull=True
            )
        except Aircraft.DoesNotExist:
            raise AircraftNotFoundError(f"Aircraft {aircraft_id} not found")

        # Validate severity
        valid_severities = [s[0] for s in AircraftSquawk.Severity.choices]
        if severity not in valid_severities:
            raise SquawkError(f"Invalid severity: {severity}")

        # Validate category
        valid_categories = [c[0] for c in AircraftSquawk.Category.choices]
        if category not in valid_categories:
            raise SquawkError(f"Invalid category: {category}")

        with transaction.atomic():
            squawk = AircraftSquawk.objects.create(
                organization_id=organization_id,
                aircraft=aircraft,
                reported_by=reported_by_user_id,
                reported_by_name=reported_by_name,
                flight_id=flight_id,
                title=title,
                description=description,
                category=category,
                severity=severity,
                aircraft_hours_at=aircraft.total_time_hours,
                aircraft_cycles_at=aircraft.total_cycles,
                photos=photos or [],
                **kwargs
            )

            logger.info(
                f"Squawk created: {squawk.squawk_number} for {aircraft.registration} "
                f"(severity: {severity})"
            )

        return squawk

    def get_squawk(
        self,
        squawk_id: UUID,
        organization_id: UUID = None
    ) -> Optional[AircraftSquawk]:
        """Get squawk by ID."""
        try:
            queryset = AircraftSquawk.objects.select_related('aircraft')

            if organization_id:
                queryset = queryset.filter(organization_id=organization_id)

            return queryset.get(id=squawk_id)
        except AircraftSquawk.DoesNotExist:
            return None

    def list_squawks(
        self,
        aircraft_id: UUID = None,
        organization_id: UUID = None,
        status: str = None,
        severity: str = None,
        category: str = None,
        is_grounding: bool = None,
        is_open: bool = None,
        reported_by: UUID = None,
        start_date: date = None,
        end_date: date = None,
        search: str = None,
        limit: int = 100
    ) -> List[AircraftSquawk]:
        """
        List squawks with filters.

        Args:
            aircraft_id: Filter by aircraft
            organization_id: Filter by organization
            status: Filter by status
            severity: Filter by severity
            category: Filter by category
            is_grounding: Filter grounding squawks
            is_open: Filter open squawks
            reported_by: Filter by reporter
            start_date: Filter from date
            end_date: Filter to date
            search: Search in title/description
            limit: Maximum results

        Returns:
            List of AircraftSquawk
        """
        queryset = AircraftSquawk.objects.select_related('aircraft')

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        if status:
            queryset = queryset.filter(status=status)

        if severity:
            queryset = queryset.filter(severity=severity)

        if category:
            queryset = queryset.filter(category=category)

        if is_grounding is not None:
            queryset = queryset.filter(is_grounding=is_grounding)

        if is_open is True:
            queryset = queryset.filter(
                status__in=[
                    AircraftSquawk.Status.OPEN,
                    AircraftSquawk.Status.IN_PROGRESS,
                    AircraftSquawk.Status.DEFERRED
                ]
            )
        elif is_open is False:
            queryset = queryset.filter(
                status__in=[
                    AircraftSquawk.Status.RESOLVED,
                    AircraftSquawk.Status.CLOSED,
                    AircraftSquawk.Status.CANCELLED
                ]
            )

        if reported_by:
            queryset = queryset.filter(reported_by=reported_by)

        if start_date:
            queryset = queryset.filter(reported_at__date__gte=start_date)

        if end_date:
            queryset = queryset.filter(reported_at__date__lte=end_date)

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(squawk_number__icontains=search)
            )

        return list(queryset.order_by('-reported_at')[:limit])

    def update_squawk(
        self,
        squawk_id: UUID,
        organization_id: UUID,
        **kwargs
    ) -> AircraftSquawk:
        """Update squawk details."""
        from apps.core.services import SquawkError

        squawk = self.get_squawk(squawk_id, organization_id)
        if not squawk:
            raise SquawkError(f"Squawk {squawk_id} not found")

        # Prevent updating closed/cancelled squawks
        if squawk.status in [
            AircraftSquawk.Status.CLOSED,
            AircraftSquawk.Status.CANCELLED
        ]:
            raise SquawkError("Cannot update closed or cancelled squawks")

        for field, value in kwargs.items():
            if hasattr(squawk, field) and field not in [
                'id', 'organization_id', 'aircraft', 'squawk_number',
                'reported_by', 'reported_at', 'created_at'
            ]:
                setattr(squawk, field, value)

        squawk.save()

        logger.info(f"Squawk updated: {squawk.squawk_number}")

        return squawk

    # ==========================================================================
    # Workflow Operations
    # ==========================================================================

    def resolve_squawk(
        self,
        squawk_id: UUID,
        organization_id: UUID,
        resolution: str,
        resolved_by_user_id: UUID,
        resolved_by_name: str = None,
        resolution_action: str = None,
        parts_used: List[dict] = None,
        actual_hours: Decimal = None,
        actual_cost: Decimal = None
    ) -> AircraftSquawk:
        """
        Resolve a squawk.

        Args:
            squawk_id: Squawk UUID
            organization_id: Organization UUID
            resolution: Resolution description
            resolved_by_user_id: User resolving
            resolved_by_name: Resolver's name
            resolution_action: Action taken (repair, replace, adjust, etc.)
            parts_used: List of parts used
            actual_hours: Actual labor hours
            actual_cost: Actual cost

        Returns:
            Updated AircraftSquawk
        """
        from apps.core.services import SquawkError

        squawk = self.get_squawk(squawk_id, organization_id)
        if not squawk:
            raise SquawkError(f"Squawk {squawk_id} not found")

        if squawk.status in [
            AircraftSquawk.Status.RESOLVED,
            AircraftSquawk.Status.CLOSED,
            AircraftSquawk.Status.CANCELLED
        ]:
            raise SquawkError(f"Squawk is already {squawk.status}")

        with transaction.atomic():
            squawk.status = AircraftSquawk.Status.RESOLVED
            squawk.resolution = resolution
            squawk.resolution_action = resolution_action
            squawk.resolved_by = resolved_by_user_id
            squawk.resolved_by_name = resolved_by_name
            squawk.resolved_at = timezone.now()

            if parts_used:
                squawk.parts_used = parts_used
            if actual_hours:
                squawk.actual_hours = actual_hours
            if actual_cost:
                squawk.actual_cost = actual_cost

            squawk.save()

            # Update aircraft squawk status
            squawk.aircraft.update_squawk_status()

            logger.info(f"Squawk resolved: {squawk.squawk_number}")

        return squawk

    def close_squawk(
        self,
        squawk_id: UUID,
        organization_id: UUID
    ) -> AircraftSquawk:
        """Close a resolved squawk."""
        from apps.core.services import SquawkError

        squawk = self.get_squawk(squawk_id, organization_id)
        if not squawk:
            raise SquawkError(f"Squawk {squawk_id} not found")

        if squawk.status != AircraftSquawk.Status.RESOLVED:
            raise SquawkError("Only resolved squawks can be closed")

        squawk.close()

        logger.info(f"Squawk closed: {squawk.squawk_number}")

        return squawk

    def cancel_squawk(
        self,
        squawk_id: UUID,
        organization_id: UUID,
        reason: str = None
    ) -> AircraftSquawk:
        """Cancel a squawk."""
        from apps.core.services import SquawkError

        squawk = self.get_squawk(squawk_id, organization_id)
        if not squawk:
            raise SquawkError(f"Squawk {squawk_id} not found")

        if squawk.status in [
            AircraftSquawk.Status.RESOLVED,
            AircraftSquawk.Status.CLOSED
        ]:
            raise SquawkError(f"Cannot cancel a {squawk.status} squawk")

        with transaction.atomic():
            squawk.cancel(reason)

            # Update aircraft squawk status
            squawk.aircraft.update_squawk_status()

            logger.info(f"Squawk cancelled: {squawk.squawk_number}")

        return squawk

    def start_work(
        self,
        squawk_id: UUID,
        organization_id: UUID
    ) -> AircraftSquawk:
        """Mark squawk as in progress."""
        from apps.core.services import SquawkError

        squawk = self.get_squawk(squawk_id, organization_id)
        if not squawk:
            raise SquawkError(f"Squawk {squawk_id} not found")

        if squawk.status not in [
            AircraftSquawk.Status.OPEN,
            AircraftSquawk.Status.DEFERRED
        ]:
            raise SquawkError(f"Cannot start work on {squawk.status} squawk")

        squawk.start_work()

        logger.info(f"Work started on squawk: {squawk.squawk_number}")

        return squawk

    # ==========================================================================
    # Deferral Management
    # ==========================================================================

    def defer_squawk(
        self,
        squawk_id: UUID,
        organization_id: UUID,
        reason: str,
        approved_by_user_id: UUID,
        until_date: date = None,
        until_hours: Decimal = None,
        until_cycles: int = None,
        mel_category: str = None,
        mel_reference: str = None
    ) -> AircraftSquawk:
        """
        Defer a squawk.

        Args:
            squawk_id: Squawk UUID
            organization_id: Organization UUID
            reason: Deferral reason
            approved_by_user_id: User approving deferral
            until_date: Defer until date
            until_hours: Defer until aircraft hours
            until_cycles: Defer until cycles
            mel_category: MEL category (A, B, C, D)
            mel_reference: MEL reference number

        Returns:
            Updated AircraftSquawk
        """
        from apps.core.services import SquawkError

        squawk = self.get_squawk(squawk_id, organization_id)
        if not squawk:
            raise SquawkError(f"Squawk {squawk_id} not found")

        if squawk.is_grounding:
            raise SquawkError("Grounding squawks cannot be deferred")

        if squawk.status not in [
            AircraftSquawk.Status.OPEN,
            AircraftSquawk.Status.IN_PROGRESS
        ]:
            raise SquawkError(f"Cannot defer {squawk.status} squawk")

        # At least one deferral limit must be specified
        if not any([until_date, until_hours, until_cycles]):
            raise SquawkError("At least one deferral limit must be specified")

        # MEL item setup
        if mel_category:
            squawk.is_mel_item = True
            squawk.mel_category = mel_category
            squawk.mel_reference = mel_reference

            # Calculate MEL expiry if not specified
            if not until_date and mel_category in ['B', 'C', 'D']:
                mel_days = {'B': 3, 'C': 10, 'D': 120}.get(mel_category)
                until_date = date.today() + timedelta(days=mel_days)

        squawk.defer(
            reason=reason,
            approved_by=approved_by_user_id,
            until_date=until_date,
            until_hours=until_hours,
            until_cycles=until_cycles
        )

        logger.info(f"Squawk deferred: {squawk.squawk_number}")

        return squawk

    def get_overdue_deferrals(
        self,
        organization_id: UUID = None,
        aircraft_id: UUID = None
    ) -> List[AircraftSquawk]:
        """Get all overdue deferred squawks."""
        queryset = AircraftSquawk.objects.filter(
            status=AircraftSquawk.Status.DEFERRED,
            is_deferred=True
        ).select_related('aircraft')

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        overdue = []
        for squawk in queryset:
            if squawk.is_overdue:
                overdue.append(squawk)

        return overdue

    # ==========================================================================
    # Statistics
    # ==========================================================================

    def get_statistics(
        self,
        organization_id: UUID = None,
        aircraft_id: UUID = None,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """
        Get squawk statistics.

        Returns statistics including:
        - Total counts by status
        - Counts by category
        - Counts by severity
        - Average resolution time
        """
        queryset = AircraftSquawk.objects.all()

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        if start_date:
            queryset = queryset.filter(reported_at__date__gte=start_date)

        if end_date:
            queryset = queryset.filter(reported_at__date__lte=end_date)

        # Status counts
        status_counts = dict(
            queryset.values('status').annotate(count=Count('id')).values_list('status', 'count')
        )

        # Category counts
        category_counts = dict(
            queryset.values('category').annotate(count=Count('id')).values_list('category', 'count')
        )

        # Severity counts
        severity_counts = dict(
            queryset.values('severity').annotate(count=Count('id')).values_list('severity', 'count')
        )

        # Open counts
        open_statuses = [
            AircraftSquawk.Status.OPEN,
            AircraftSquawk.Status.IN_PROGRESS,
            AircraftSquawk.Status.DEFERRED
        ]
        open_count = queryset.filter(status__in=open_statuses).count()
        grounding_count = queryset.filter(
            status__in=open_statuses,
            is_grounding=True
        ).count()

        # Average resolution time (for resolved squawks)
        resolved = queryset.filter(
            status__in=[AircraftSquawk.Status.RESOLVED, AircraftSquawk.Status.CLOSED],
            resolved_at__isnull=False
        )

        avg_resolution_hours = None
        if resolved.exists():
            total_hours = 0
            count = 0
            for sq in resolved:
                delta = sq.resolved_at - sq.reported_at
                total_hours += delta.total_seconds() / 3600
                count += 1
            if count > 0:
                avg_resolution_hours = total_hours / count

        return {
            'total': queryset.count(),
            'open': open_count,
            'grounding': grounding_count,
            'by_status': status_counts,
            'by_category': category_counts,
            'by_severity': severity_counts,
            'avg_resolution_hours': round(avg_resolution_hours, 1) if avg_resolution_hours else None,
        }

    # ==========================================================================
    # Photo Management
    # ==========================================================================

    def add_photo(
        self,
        squawk_id: UUID,
        organization_id: UUID,
        photo_url: str
    ) -> AircraftSquawk:
        """Add photo to squawk."""
        from apps.core.services import SquawkError

        squawk = self.get_squawk(squawk_id, organization_id)
        if not squawk:
            raise SquawkError(f"Squawk {squawk_id} not found")

        squawk.add_photo(photo_url)

        return squawk

    def add_document(
        self,
        squawk_id: UUID,
        organization_id: UUID,
        document_url: str,
        title: str = None
    ) -> AircraftSquawk:
        """Add document to squawk."""
        from apps.core.services import SquawkError

        squawk = self.get_squawk(squawk_id, organization_id)
        if not squawk:
            raise SquawkError(f"Squawk {squawk_id} not found")

        squawk.add_document(document_url, title)

        return squawk
