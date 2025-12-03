# services/maintenance-service/src/apps/core/models/parts_inventory.py
"""
Parts Inventory Model

Manages aviation parts inventory and transactions.
"""

import uuid
from decimal import Decimal
from datetime import date

from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField


class PartsInventory(models.Model):
    """
    Parts inventory management.

    Tracks aviation parts, quantities, and locations.
    """

    class Condition(models.TextChoices):
        NEW = 'new', 'New'
        OVERHAULED = 'overhauled', 'Overhauled'
        REPAIRED = 'repaired', 'Repaired'
        SERVICEABLE = 'serviceable', 'Serviceable'
        UNSERVICEABLE = 'unserviceable', 'Unserviceable'
        SCRAP = 'scrap', 'Scrap'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        DISCONTINUED = 'discontinued', 'Discontinued'
        OBSOLETE = 'obsolete', 'Obsolete'

    class UnitOfMeasure(models.TextChoices):
        EACH = 'each', 'Each'
        SET = 'set', 'Set'
        KIT = 'kit', 'Kit'
        GALLON = 'gallon', 'Gallon'
        LITER = 'liter', 'Liter'
        QUART = 'quart', 'Quart'
        POUND = 'pound', 'Pound'
        FOOT = 'foot', 'Foot'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    location_id = models.UUIDField(blank=True, null=True)

    # ==========================================================================
    # Part Information
    # ==========================================================================

    part_number = models.CharField(max_length=100, db_index=True)
    alternate_part_numbers = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True
    )
    description = models.CharField(max_length=500)

    # ==========================================================================
    # Categorization
    # ==========================================================================

    category = models.CharField(max_length=50, blank=True, null=True)
    ata_chapter = models.CharField(max_length=10, blank=True, null=True)

    # ==========================================================================
    # Manufacturer
    # ==========================================================================

    manufacturer = models.CharField(max_length=255, blank=True, null=True)
    manufacturer_code = models.CharField(max_length=50, blank=True, null=True)

    # ==========================================================================
    # Stock
    # ==========================================================================

    quantity_on_hand = models.IntegerField(default=0)
    quantity_reserved = models.IntegerField(default=0)
    quantity_available = models.IntegerField(default=0)
    minimum_quantity = models.IntegerField(default=0)
    reorder_quantity = models.IntegerField(blank=True, null=True)

    unit_of_measure = models.CharField(
        max_length=20,
        choices=UnitOfMeasure.choices,
        default=UnitOfMeasure.EACH
    )

    # ==========================================================================
    # Location
    # ==========================================================================

    bin_location = models.CharField(max_length=100, blank=True, null=True)
    shelf = models.CharField(max_length=50, blank=True, null=True)

    # ==========================================================================
    # Condition
    # ==========================================================================

    condition = models.CharField(
        max_length=20,
        choices=Condition.choices,
        default=Condition.NEW
    )

    # ==========================================================================
    # Certification
    # ==========================================================================

    is_serialized = models.BooleanField(default=False)
    is_lot_controlled = models.BooleanField(default=False)
    requires_certification = models.BooleanField(default=True)

    # ==========================================================================
    # Pricing
    # ==========================================================================

    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    average_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    last_purchase_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    # ==========================================================================
    # Last Operations
    # ==========================================================================

    last_received_date = models.DateField(blank=True, null=True)
    last_issued_date = models.DateField(blank=True, null=True)
    last_count_date = models.DateField(blank=True, null=True)

    # ==========================================================================
    # Vendor
    # ==========================================================================

    preferred_vendor_id = models.UUIDField(blank=True, null=True)
    preferred_vendor_name = models.CharField(max_length=255, blank=True, null=True)
    vendor_part_number = models.CharField(max_length=100, blank=True, null=True)
    lead_time_days = models.IntegerField(blank=True, null=True)

    # ==========================================================================
    # Documentation
    # ==========================================================================

    specification_url = models.URLField(max_length=500, blank=True, null=True)

    # ==========================================================================
    # Notes
    # ==========================================================================

    notes = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Metadata
    # ==========================================================================

    metadata = models.JSONField(default=dict, blank=True)

    # ==========================================================================
    # Status
    # ==========================================================================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    # ==========================================================================
    # Timestamps
    # ==========================================================================

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'parts_inventory'
        verbose_name = 'Part Inventory'
        verbose_name_plural = 'Parts Inventory'
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['part_number']),
            models.Index(fields=['location_id']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'part_number', 'location_id', 'condition'],
                name='unique_part_location_condition'
            )
        ]

    def __str__(self):
        return f"{self.part_number}: {self.description}"

    def save(self, *args, **kwargs):
        self.quantity_available = self.quantity_on_hand - self.quantity_reserved
        super().save(*args, **kwargs)

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def is_low_stock(self) -> bool:
        return self.quantity_available <= self.minimum_quantity

    @property
    def needs_reorder(self) -> bool:
        if self.reorder_quantity:
            return self.quantity_available <= self.minimum_quantity
        return False

    @property
    def total_value(self) -> Decimal:
        cost = self.average_cost or self.unit_cost or Decimal('0')
        return cost * self.quantity_on_hand

    # ==========================================================================
    # Methods
    # ==========================================================================

    def receive(
        self,
        quantity: int,
        unit_cost: Decimal = None,
        received_by: uuid.UUID = None,
        reference: str = None,
        notes: str = None
    ) -> 'PartTransaction':
        """Receive parts into inventory."""
        # Update average cost
        if unit_cost and self.quantity_on_hand > 0:
            total_value = (self.average_cost or Decimal('0')) * self.quantity_on_hand
            new_value = unit_cost * quantity
            self.average_cost = (total_value + new_value) / (self.quantity_on_hand + quantity)

        self.quantity_on_hand += quantity
        self.last_received_date = date.today()
        if unit_cost:
            self.last_purchase_price = unit_cost
        self.save()

        # Create transaction
        return PartTransaction.objects.create(
            part=self,
            organization_id=self.organization_id,
            transaction_type=PartTransaction.TransactionType.RECEIVE,
            quantity=quantity,
            unit_cost=unit_cost,
            quantity_after=self.quantity_on_hand,
            reference=reference,
            notes=notes,
            performed_by=received_by,
        )

    def issue(
        self,
        quantity: int,
        work_order_id: uuid.UUID = None,
        aircraft_id: uuid.UUID = None,
        issued_by: uuid.UUID = None,
        reference: str = None,
        notes: str = None
    ) -> 'PartTransaction':
        """Issue parts from inventory."""
        if quantity > self.quantity_available:
            raise ValueError(f"Insufficient quantity available. Available: {self.quantity_available}")

        self.quantity_on_hand -= quantity
        self.last_issued_date = date.today()
        self.save()

        return PartTransaction.objects.create(
            part=self,
            organization_id=self.organization_id,
            transaction_type=PartTransaction.TransactionType.ISSUE,
            quantity=-quantity,
            unit_cost=self.average_cost,
            quantity_after=self.quantity_on_hand,
            work_order_id=work_order_id,
            aircraft_id=aircraft_id,
            reference=reference,
            notes=notes,
            performed_by=issued_by,
        )

    def reserve(self, quantity: int, work_order_id: uuid.UUID = None) -> None:
        """Reserve parts for a work order."""
        if quantity > self.quantity_available:
            raise ValueError(f"Insufficient quantity available. Available: {self.quantity_available}")

        self.quantity_reserved += quantity
        self.save()

    def release_reservation(self, quantity: int) -> None:
        """Release reserved parts."""
        self.quantity_reserved = max(0, self.quantity_reserved - quantity)
        self.save()

    def adjust(
        self,
        new_quantity: int,
        reason: str,
        adjusted_by: uuid.UUID = None
    ) -> 'PartTransaction':
        """Adjust inventory count."""
        difference = new_quantity - self.quantity_on_hand
        old_quantity = self.quantity_on_hand

        self.quantity_on_hand = new_quantity
        self.last_count_date = date.today()
        self.save()

        return PartTransaction.objects.create(
            part=self,
            organization_id=self.organization_id,
            transaction_type=PartTransaction.TransactionType.ADJUSTMENT,
            quantity=difference,
            quantity_after=new_quantity,
            notes=f"Adjustment from {old_quantity} to {new_quantity}. Reason: {reason}",
            performed_by=adjusted_by,
        )


class PartTransaction(models.Model):
    """
    Part inventory transaction log.
    """

    class TransactionType(models.TextChoices):
        RECEIVE = 'receive', 'Receive'
        ISSUE = 'issue', 'Issue'
        RETURN = 'return', 'Return'
        ADJUSTMENT = 'adjustment', 'Adjustment'
        TRANSFER = 'transfer', 'Transfer'
        SCRAP = 'scrap', 'Scrap'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    part = models.ForeignKey(
        PartsInventory,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    organization_id = models.UUIDField(db_index=True)

    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices
    )
    quantity = models.IntegerField()
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    quantity_after = models.IntegerField()

    # Related records
    work_order_id = models.UUIDField(blank=True, null=True)
    aircraft_id = models.UUIDField(blank=True, null=True)

    # Reference
    reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # Performer
    performed_by = models.UUIDField(blank=True, null=True)
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'part_transactions'
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['part', '-performed_at']),
            models.Index(fields=['work_order_id']),
        ]

    def __str__(self):
        return f"{self.transaction_type}: {self.part.part_number} ({self.quantity})"

    @property
    def total_value(self) -> Decimal:
        if self.unit_cost:
            return self.unit_cost * abs(self.quantity)
        return Decimal('0')
