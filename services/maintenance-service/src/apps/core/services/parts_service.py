# services/maintenance-service/src/apps/core/services/parts_service.py
"""
Parts Service

Manages parts inventory and transactions.
"""

import uuid
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List

from django.db import transaction
from django.db.models import Q, Sum, F

from apps.core.models import PartsInventory, PartTransaction

logger = logging.getLogger(__name__)


class PartsService:
    """
    Service for managing parts inventory.

    Handles:
    - Inventory CRUD
    - Stock operations (receive, issue, adjust)
    - Reservations
    - Low stock alerts
    """

    # ==========================================================================
    # Inventory CRUD
    # ==========================================================================

    @transaction.atomic
    def create_part(
        self,
        organization_id: uuid.UUID,
        part_number: str,
        description: str,
        **kwargs
    ) -> PartsInventory:
        """Create a new part in inventory."""
        part = PartsInventory.objects.create(
            organization_id=organization_id,
            part_number=part_number.upper(),
            description=description,
            **kwargs
        )

        logger.info(f"Created part: {part.part_number}")
        return part

    def get_part(self, part_id: uuid.UUID) -> PartsInventory:
        """Get a part by ID."""
        try:
            return PartsInventory.objects.get(id=part_id)
        except PartsInventory.DoesNotExist:
            from . import PartNotFoundError
            raise PartNotFoundError(f"Part {part_id} not found")

    def get_by_part_number(
        self,
        organization_id: uuid.UUID,
        part_number: str,
        location_id: uuid.UUID = None
    ) -> PartsInventory:
        """Get a part by part number."""
        queryset = PartsInventory.objects.filter(
            organization_id=organization_id,
            part_number=part_number.upper()
        )
        if location_id:
            queryset = queryset.filter(location_id=location_id)

        part = queryset.first()
        if not part:
            from . import PartNotFoundError
            raise PartNotFoundError(f"Part {part_number} not found")

        return part

    def list_parts(
        self,
        organization_id: uuid.UUID,
        location_id: uuid.UUID = None,
        category: str = None,
        low_stock_only: bool = False,
        search: str = None,
        status: str = None
    ) -> List[PartsInventory]:
        """List parts with filters."""
        queryset = PartsInventory.objects.filter(organization_id=organization_id)

        if location_id:
            queryset = queryset.filter(location_id=location_id)
        if category:
            queryset = queryset.filter(category=category)
        if low_stock_only:
            queryset = queryset.filter(quantity_available__lte=F('minimum_quantity'))
        if status:
            queryset = queryset.filter(status=status)
        if search:
            queryset = queryset.filter(
                Q(part_number__icontains=search) |
                Q(description__icontains=search) |
                Q(manufacturer__icontains=search)
            )

        return list(queryset.order_by('part_number'))

    @transaction.atomic
    def update_part(self, part_id: uuid.UUID, **kwargs) -> PartsInventory:
        """Update a part."""
        part = self.get_part(part_id)

        allowed_fields = [
            'description', 'category', 'ata_chapter', 'manufacturer',
            'manufacturer_code', 'minimum_quantity', 'reorder_quantity',
            'unit_of_measure', 'bin_location', 'shelf', 'unit_cost',
            'preferred_vendor_id', 'preferred_vendor_name', 'vendor_part_number',
            'lead_time_days', 'specification_url', 'notes', 'status'
        ]

        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(part, field, value)

        part.save()
        return part

    # ==========================================================================
    # Stock Operations
    # ==========================================================================

    @transaction.atomic
    def receive_parts(
        self,
        part_id: uuid.UUID,
        quantity: int,
        unit_cost: Decimal = None,
        received_by: uuid.UUID = None,
        reference: str = None,
        notes: str = None
    ) -> PartTransaction:
        """Receive parts into inventory."""
        part = self.get_part(part_id)

        transaction = part.receive(
            quantity=quantity,
            unit_cost=unit_cost,
            received_by=received_by,
            reference=reference,
            notes=notes
        )

        logger.info(
            f"Received {quantity} x {part.part_number}, "
            f"new qty: {part.quantity_on_hand}"
        )

        return transaction

    @transaction.atomic
    def issue_parts(
        self,
        part_id: uuid.UUID,
        quantity: int,
        work_order_id: uuid.UUID = None,
        aircraft_id: uuid.UUID = None,
        issued_by: uuid.UUID = None,
        reference: str = None,
        notes: str = None
    ) -> PartTransaction:
        """Issue parts from inventory."""
        part = self.get_part(part_id)

        if quantity > part.quantity_available:
            from . import InsufficientInventoryError
            raise InsufficientInventoryError(
                f"Insufficient quantity. Requested: {quantity}, Available: {part.quantity_available}"
            )

        transaction = part.issue(
            quantity=quantity,
            work_order_id=work_order_id,
            aircraft_id=aircraft_id,
            issued_by=issued_by,
            reference=reference,
            notes=notes
        )

        logger.info(
            f"Issued {quantity} x {part.part_number}, "
            f"remaining: {part.quantity_on_hand}"
        )

        return transaction

    @transaction.atomic
    def adjust_inventory(
        self,
        part_id: uuid.UUID,
        new_quantity: int,
        reason: str,
        adjusted_by: uuid.UUID = None
    ) -> PartTransaction:
        """Adjust inventory count."""
        part = self.get_part(part_id)
        old_quantity = part.quantity_on_hand

        transaction = part.adjust(
            new_quantity=new_quantity,
            reason=reason,
            adjusted_by=adjusted_by
        )

        logger.info(
            f"Adjusted {part.part_number}: {old_quantity} -> {new_quantity}. "
            f"Reason: {reason}"
        )

        return transaction

    @transaction.atomic
    def return_parts(
        self,
        part_id: uuid.UUID,
        quantity: int,
        work_order_id: uuid.UUID = None,
        returned_by: uuid.UUID = None,
        reason: str = None
    ) -> PartTransaction:
        """Return parts to inventory."""
        part = self.get_part(part_id)

        # Increase stock
        part.quantity_on_hand += quantity
        part.save()

        transaction = PartTransaction.objects.create(
            part=part,
            organization_id=part.organization_id,
            transaction_type=PartTransaction.TransactionType.RETURN,
            quantity=quantity,
            unit_cost=part.average_cost,
            quantity_after=part.quantity_on_hand,
            work_order_id=work_order_id,
            notes=reason,
            performed_by=returned_by,
        )

        logger.info(f"Returned {quantity} x {part.part_number}")

        return transaction

    # ==========================================================================
    # Reservations
    # ==========================================================================

    def reserve_parts(
        self,
        part_id: uuid.UUID,
        quantity: int,
        work_order_id: uuid.UUID = None
    ) -> PartsInventory:
        """Reserve parts for a work order."""
        part = self.get_part(part_id)

        if quantity > part.quantity_available:
            from . import InsufficientInventoryError
            raise InsufficientInventoryError(
                f"Insufficient quantity to reserve. "
                f"Requested: {quantity}, Available: {part.quantity_available}"
            )

        part.reserve(quantity, work_order_id)

        logger.info(f"Reserved {quantity} x {part.part_number}")
        return part

    def release_reservation(
        self,
        part_id: uuid.UUID,
        quantity: int
    ) -> PartsInventory:
        """Release reserved parts."""
        part = self.get_part(part_id)
        part.release_reservation(quantity)

        logger.info(f"Released {quantity} x {part.part_number} from reservation")
        return part

    # ==========================================================================
    # Queries
    # ==========================================================================

    def get_low_stock_parts(
        self,
        organization_id: uuid.UUID,
        location_id: uuid.UUID = None
    ) -> List[PartsInventory]:
        """Get parts with low stock."""
        queryset = PartsInventory.objects.filter(
            organization_id=organization_id,
            status=PartsInventory.Status.ACTIVE,
            quantity_available__lte=F('minimum_quantity')
        )

        if location_id:
            queryset = queryset.filter(location_id=location_id)

        return list(queryset.order_by('quantity_available'))

    def get_part_transactions(
        self,
        part_id: uuid.UUID,
        limit: int = 50
    ) -> List[PartTransaction]:
        """Get transaction history for a part."""
        return list(
            PartTransaction.objects.filter(part_id=part_id)
            .order_by('-performed_at')[:limit]
        )

    def get_work_order_parts(
        self,
        work_order_id: uuid.UUID
    ) -> List[PartTransaction]:
        """Get all parts used in a work order."""
        return list(
            PartTransaction.objects.filter(
                work_order_id=work_order_id,
                transaction_type=PartTransaction.TransactionType.ISSUE
            ).select_related('part')
        )

    def search_parts(
        self,
        organization_id: uuid.UUID,
        query: str
    ) -> List[PartsInventory]:
        """Search parts by number, description, or manufacturer."""
        return list(
            PartsInventory.objects.filter(
                organization_id=organization_id,
                status=PartsInventory.Status.ACTIVE
            ).filter(
                Q(part_number__icontains=query) |
                Q(description__icontains=query) |
                Q(manufacturer__icontains=query) |
                Q(alternate_part_numbers__contains=[query.upper()])
            ).order_by('part_number')[:50]
        )

    # ==========================================================================
    # Statistics
    # ==========================================================================

    def get_inventory_statistics(
        self,
        organization_id: uuid.UUID,
        location_id: uuid.UUID = None
    ) -> Dict[str, Any]:
        """Get inventory statistics."""
        queryset = PartsInventory.objects.filter(
            organization_id=organization_id,
            status=PartsInventory.Status.ACTIVE
        )

        if location_id:
            queryset = queryset.filter(location_id=location_id)

        # Aggregate stats
        stats = queryset.aggregate(
            total_parts=Sum('quantity_on_hand'),
            total_value=Sum(F('quantity_on_hand') * F('average_cost')),
        )

        # Counts
        total_items = queryset.count()
        low_stock = queryset.filter(
            quantity_available__lte=F('minimum_quantity')
        ).count()

        return {
            'total_line_items': total_items,
            'total_quantity': stats['total_parts'] or 0,
            'total_value': float(stats['total_value'] or 0),
            'low_stock_count': low_stock,
        }
