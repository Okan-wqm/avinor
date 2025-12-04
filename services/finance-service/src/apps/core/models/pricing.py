# services/finance-service/src/apps/core/models/pricing.py
"""
Pricing Model

Dynamic pricing rules for flights, services, and products.
"""

import uuid
from decimal import Decimal
from datetime import date
from django.db import models
from django.contrib.postgres.fields import ArrayField


class PricingType(models.TextChoices):
    """Pricing type choices."""
    AIRCRAFT = 'aircraft', 'Aircraft Rental'
    INSTRUCTOR = 'instructor', 'Instructor Fee'
    FUEL = 'fuel', 'Fuel'
    LANDING = 'landing', 'Landing Fee'
    HANGAR = 'hangar', 'Hangar Fee'
    PARKING = 'parking', 'Parking Fee'
    EQUIPMENT = 'equipment', 'Equipment Rental'
    GROUND_INSTRUCTION = 'ground_instruction', 'Ground Instruction'
    EXAMINATION = 'examination', 'Examination Fee'
    MEMBERSHIP = 'membership', 'Membership Fee'
    PACKAGE = 'package', 'Package'
    OTHER = 'other', 'Other'


class CalculationMethod(models.TextChoices):
    """Calculation method choices."""
    PER_UNIT = 'per_unit', 'Per Unit'
    FLAT = 'flat', 'Flat Rate'
    TIERED = 'tiered', 'Tiered Pricing'
    BLOCK = 'block', 'Block Pricing'
    PERCENTAGE = 'percentage', 'Percentage'


class PricingRule(models.Model):
    """
    Pricing rule model.

    Defines pricing for aircraft, instructors, fuel,
    and other services with support for multiple
    calculation methods.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # Identification
    name = models.CharField(max_length=255)
    code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Short code for the pricing rule'
    )
    description = models.TextField(blank=True, null=True)

    # Scope
    pricing_type = models.CharField(
        max_length=50,
        choices=PricingType.choices,
        db_index=True
    )
    target_id = models.UUIDField(
        blank=True,
        null=True,
        db_index=True,
        help_text='Specific aircraft_id, user_id, etc.'
    )
    target_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='aircraft, user, fuel_type, etc.'
    )

    # Base Price
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Base price per unit'
    )
    currency = models.CharField(max_length=3, default='USD')

    # Unit
    unit = models.CharField(
        max_length=20,
        default='hour',
        help_text='hour, flight, day, month, landing, liter, gallon'
    )
    unit_name = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Display name for unit'
    )

    # Calculation Method
    calculation_method = models.CharField(
        max_length=20,
        choices=CalculationMethod.choices,
        default=CalculationMethod.PER_UNIT
    )

    # Block Pricing
    block_size = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Block size for block pricing (e.g., 0.1 hour)'
    )
    minimum_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Minimum charge amount'
    )
    minimum_units = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Minimum billable units'
    )

    # Tiered Pricing
    tiers = models.JSONField(
        default=list,
        blank=True,
        help_text='[{"from": 0, "to": 10, "price": 150}, {"from": 10, "to": null, "price": 140}]'
    )

    # Time-Based Pricing
    time_based_rates = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"weekend": 1.1, "night": 1.2, "holiday": 1.25}'
    )

    # Weekend/Holiday Modifiers
    weekend_rate_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text='Multiplier for weekend rates'
    )
    holiday_rate_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text='Multiplier for holiday rates'
    )
    night_rate_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text='Multiplier for night rates'
    )
    peak_rate_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text='Multiplier for peak hours'
    )
    peak_hours_start = models.TimeField(blank=True, null=True)
    peak_hours_end = models.TimeField(blank=True, null=True)

    # Discounts
    discount_eligible = models.BooleanField(
        default=True,
        help_text='Can discounts be applied?'
    )
    member_discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Discount for members'
    )
    bulk_discount_enabled = models.BooleanField(default=False)
    bulk_discount_tiers = models.JSONField(
        default=list,
        blank=True,
        help_text='[{"min_units": 10, "discount_percent": 5}, {"min_units": 20, "discount_percent": 10}]'
    )

    # Tax
    tax_inclusive = models.BooleanField(
        default=False,
        help_text='Is tax included in base price?'
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Default tax rate'
    )
    tax_category = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Tax category code'
    )

    # Applicability
    applicable_aircraft_types = ArrayField(
        models.UUIDField(),
        blank=True,
        null=True,
        help_text='Applicable to specific aircraft types'
    )
    applicable_user_types = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        null=True,
        help_text='student, pilot, instructor'
    )
    applicable_membership_levels = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        null=True
    )

    # Validity
    effective_from = models.DateField(blank=True, null=True)
    effective_to = models.DateField(blank=True, null=True)

    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    priority = models.IntegerField(
        default=0,
        help_text='Higher priority rules are applied first'
    )

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_by = models.UUIDField(blank=True, null=True)
    updated_by = models.UUIDField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pricing_rules'
        ordering = ['-priority', 'name']
        indexes = [
            models.Index(fields=['organization_id', 'pricing_type', 'is_active']),
            models.Index(fields=['organization_id', 'target_id']),
        ]

    def __str__(self):
        return f"{self.name}: {self.base_price} {self.currency}/{self.unit}"

    @property
    def is_effective(self) -> bool:
        """Check if pricing rule is currently effective."""
        today = date.today()
        if self.effective_from and today < self.effective_from:
            return False
        if self.effective_to and today > self.effective_to:
            return False
        return self.is_active

    def calculate_price(
        self,
        quantity: Decimal,
        is_weekend: bool = False,
        is_holiday: bool = False,
        is_night: bool = False,
        is_peak: bool = False,
        is_member: bool = False
    ) -> dict:
        """
        Calculate price based on quantity and modifiers.

        Returns dict with base_amount, modifiers, tax, and total.
        """
        # Base calculation
        if self.calculation_method == CalculationMethod.FLAT:
            base_amount = self.base_price
        elif self.calculation_method == CalculationMethod.TIERED:
            base_amount = self._calculate_tiered_price(quantity)
        elif self.calculation_method == CalculationMethod.BLOCK:
            base_amount = self._calculate_block_price(quantity)
        else:  # PER_UNIT
            base_amount = self.base_price * quantity

        # Apply minimum charge
        if self.minimum_charge and base_amount < self.minimum_charge:
            base_amount = self.minimum_charge

        # Apply time-based modifiers
        multiplier = Decimal('1.00')
        modifiers = []

        if is_weekend and self.weekend_rate_multiplier != Decimal('1.00'):
            multiplier *= self.weekend_rate_multiplier
            modifiers.append({
                'type': 'weekend',
                'multiplier': float(self.weekend_rate_multiplier)
            })

        if is_holiday and self.holiday_rate_multiplier != Decimal('1.00'):
            multiplier *= self.holiday_rate_multiplier
            modifiers.append({
                'type': 'holiday',
                'multiplier': float(self.holiday_rate_multiplier)
            })

        if is_night and self.night_rate_multiplier != Decimal('1.00'):
            multiplier *= self.night_rate_multiplier
            modifiers.append({
                'type': 'night',
                'multiplier': float(self.night_rate_multiplier)
            })

        if is_peak and self.peak_rate_multiplier != Decimal('1.00'):
            multiplier *= self.peak_rate_multiplier
            modifiers.append({
                'type': 'peak',
                'multiplier': float(self.peak_rate_multiplier)
            })

        adjusted_amount = base_amount * multiplier

        # Apply member discount
        discount_amount = Decimal('0')
        if is_member and self.member_discount_percent:
            discount_amount = adjusted_amount * (self.member_discount_percent / 100)
            modifiers.append({
                'type': 'member_discount',
                'percent': float(self.member_discount_percent),
                'amount': float(discount_amount)
            })

        # Apply bulk discount
        if self.bulk_discount_enabled and self.bulk_discount_tiers:
            bulk_discount = self._calculate_bulk_discount(quantity, adjusted_amount)
            if bulk_discount > Decimal('0'):
                discount_amount += bulk_discount
                modifiers.append({
                    'type': 'bulk_discount',
                    'amount': float(bulk_discount)
                })

        subtotal = adjusted_amount - discount_amount

        # Calculate tax
        tax_amount = Decimal('0')
        if self.tax_rate:
            if self.tax_inclusive:
                # Extract tax from price
                tax_amount = subtotal - (subtotal / (1 + self.tax_rate / 100))
            else:
                tax_amount = subtotal * (self.tax_rate / 100)

        total = subtotal if self.tax_inclusive else subtotal + tax_amount

        return {
            'base_price': float(self.base_price),
            'quantity': float(quantity),
            'base_amount': float(base_amount),
            'modifiers': modifiers,
            'adjusted_amount': float(adjusted_amount),
            'discount_amount': float(discount_amount),
            'subtotal': float(subtotal),
            'tax_rate': float(self.tax_rate) if self.tax_rate else None,
            'tax_amount': float(tax_amount),
            'total': float(total),
            'currency': self.currency,
            'unit': self.unit,
        }

    def _calculate_tiered_price(self, quantity: Decimal) -> Decimal:
        """Calculate price using tiered pricing."""
        if not self.tiers:
            return self.base_price * quantity

        total = Decimal('0')
        remaining = quantity

        for tier in sorted(self.tiers, key=lambda x: x.get('from', 0)):
            tier_from = Decimal(str(tier.get('from', 0)))
            tier_to = Decimal(str(tier.get('to'))) if tier.get('to') else None
            tier_price = Decimal(str(tier.get('price', self.base_price)))

            if remaining <= 0:
                break

            if tier_to:
                tier_quantity = min(remaining, tier_to - tier_from)
            else:
                tier_quantity = remaining

            total += tier_quantity * tier_price
            remaining -= tier_quantity

        return total

    def _calculate_block_price(self, quantity: Decimal) -> Decimal:
        """Calculate price using block pricing."""
        if not self.block_size or self.block_size <= 0:
            return self.base_price * quantity

        # Round up to nearest block
        blocks = (quantity / self.block_size).quantize(Decimal('1'), rounding='CEILING')
        block_quantity = blocks * self.block_size

        # Apply minimum units
        if self.minimum_units and block_quantity < self.minimum_units:
            block_quantity = self.minimum_units

        return self.base_price * block_quantity

    def _calculate_bulk_discount(self, quantity: Decimal, amount: Decimal) -> Decimal:
        """Calculate bulk discount amount."""
        if not self.bulk_discount_tiers:
            return Decimal('0')

        applicable_discount = Decimal('0')
        for tier in sorted(self.bulk_discount_tiers, key=lambda x: x.get('min_units', 0), reverse=True):
            if quantity >= Decimal(str(tier.get('min_units', 0))):
                applicable_discount = Decimal(str(tier.get('discount_percent', 0)))
                break

        if applicable_discount > 0:
            return amount * (applicable_discount / 100)
        return Decimal('0')
