# services/finance-service/src/apps/core/services/pricing_service.py
"""
Pricing Service

Business logic for dynamic pricing calculations.
"""

import uuid
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import date, datetime, time
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ..models.pricing import PricingRule, PricingType, CalculationMethod

logger = logging.getLogger(__name__)


class PricingServiceError(Exception):
    """Base exception for pricing service errors."""
    pass


class PricingRuleNotFoundError(PricingServiceError):
    """Raised when pricing rule is not found."""
    pass


class PricingService:
    """
    Service for pricing calculations.

    Handles pricing rule management and price calculations
    with support for tiered, block, and time-based pricing.
    """

    @staticmethod
    def create_pricing_rule(
        organization_id: uuid.UUID,
        name: str,
        pricing_type: str,
        base_price: Decimal,
        currency: str = 'USD',
        unit: str = 'hour',
        calculation_method: str = CalculationMethod.PER_UNIT,
        target_id: uuid.UUID = None,
        target_type: str = None,
        code: str = None,
        description: str = None,
        minimum_charge: Decimal = None,
        minimum_units: Decimal = None,
        block_size: Decimal = None,
        tiers: List[Dict] = None,
        weekend_rate_multiplier: Decimal = Decimal('1.00'),
        holiday_rate_multiplier: Decimal = Decimal('1.00'),
        night_rate_multiplier: Decimal = Decimal('1.00'),
        peak_rate_multiplier: Decimal = Decimal('1.00'),
        peak_hours_start: time = None,
        peak_hours_end: time = None,
        member_discount_percent: Decimal = None,
        bulk_discount_tiers: List[Dict] = None,
        tax_rate: Decimal = None,
        tax_inclusive: bool = False,
        effective_from: date = None,
        effective_to: date = None,
        priority: int = 0,
        metadata: Dict = None,
        created_by: uuid.UUID = None
    ) -> PricingRule:
        """
        Create a new pricing rule.

        Args:
            organization_id: Organization UUID
            name: Rule name
            pricing_type: Type of pricing (aircraft, instructor, etc.)
            base_price: Base price per unit
            currency: Currency code
            unit: Unit of measure
            calculation_method: Calculation method
            target_id: Specific target (aircraft_id, user_id, etc.)
            target_type: Target type
            code: Short code
            description: Description
            minimum_charge: Minimum charge amount
            minimum_units: Minimum billable units
            block_size: Block size for block pricing
            tiers: Tiered pricing configuration
            weekend_rate_multiplier: Weekend rate multiplier
            holiday_rate_multiplier: Holiday rate multiplier
            night_rate_multiplier: Night rate multiplier
            peak_rate_multiplier: Peak hours multiplier
            peak_hours_start: Peak hours start time
            peak_hours_end: Peak hours end time
            member_discount_percent: Member discount percentage
            bulk_discount_tiers: Bulk discount configuration
            tax_rate: Default tax rate
            tax_inclusive: Is tax included in price
            effective_from: Start date
            effective_to: End date
            priority: Rule priority
            metadata: Additional metadata
            created_by: User who created the rule

        Returns:
            Created PricingRule instance
        """
        rule = PricingRule.objects.create(
            organization_id=organization_id,
            name=name,
            code=code,
            description=description,
            pricing_type=pricing_type,
            target_id=target_id,
            target_type=target_type,
            base_price=base_price,
            currency=currency,
            unit=unit,
            calculation_method=calculation_method,
            minimum_charge=minimum_charge,
            minimum_units=minimum_units,
            block_size=block_size,
            tiers=tiers or [],
            weekend_rate_multiplier=weekend_rate_multiplier,
            holiday_rate_multiplier=holiday_rate_multiplier,
            night_rate_multiplier=night_rate_multiplier,
            peak_rate_multiplier=peak_rate_multiplier,
            peak_hours_start=peak_hours_start,
            peak_hours_end=peak_hours_end,
            member_discount_percent=member_discount_percent,
            bulk_discount_enabled=bool(bulk_discount_tiers),
            bulk_discount_tiers=bulk_discount_tiers or [],
            tax_rate=tax_rate,
            tax_inclusive=tax_inclusive,
            effective_from=effective_from,
            effective_to=effective_to,
            priority=priority,
            metadata=metadata or {},
            created_by=created_by
        )

        logger.info(
            f"Created pricing rule: {name}",
            extra={
                'rule_id': str(rule.id),
                'organization_id': str(organization_id),
                'pricing_type': pricing_type
            }
        )

        return rule

    @staticmethod
    def update_pricing_rule(
        rule_id: uuid.UUID,
        organization_id: uuid.UUID = None,
        updated_by: uuid.UUID = None,
        **updates
    ) -> PricingRule:
        """
        Update a pricing rule.

        Args:
            rule_id: Rule UUID
            organization_id: Optional organization filter
            updated_by: User who updated
            **updates: Fields to update

        Returns:
            Updated PricingRule instance
        """
        rule = PricingService.get_pricing_rule(rule_id, organization_id)

        protected_fields = {'id', 'organization_id', 'created_at', 'created_by'}

        for field, value in updates.items():
            if field not in protected_fields:
                setattr(rule, field, value)

        rule.updated_by = updated_by
        rule.save()

        logger.info(
            f"Updated pricing rule: {rule.name}",
            extra={
                'rule_id': str(rule_id),
                'updates': list(updates.keys())
            }
        )

        return rule

    @staticmethod
    def get_pricing_rule(
        rule_id: uuid.UUID,
        organization_id: uuid.UUID = None
    ) -> PricingRule:
        """
        Get pricing rule by ID.

        Args:
            rule_id: Rule UUID
            organization_id: Optional organization filter

        Returns:
            PricingRule instance

        Raises:
            PricingRuleNotFoundError: If not found
        """
        queryset = PricingRule.objects.filter(id=rule_id)

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        rule = queryset.first()

        if not rule:
            raise PricingRuleNotFoundError(f"Pricing rule {rule_id} not found")

        return rule

    @staticmethod
    def get_applicable_rule(
        organization_id: uuid.UUID,
        pricing_type: str,
        target_id: uuid.UUID = None,
        effective_date: date = None
    ) -> Optional[PricingRule]:
        """
        Get the most applicable pricing rule.

        Args:
            organization_id: Organization UUID
            pricing_type: Type of pricing
            target_id: Specific target ID (aircraft, user, etc.)
            effective_date: Date to check effectiveness

        Returns:
            Most applicable PricingRule or None
        """
        effective_date = effective_date or date.today()

        queryset = PricingRule.objects.filter(
            organization_id=organization_id,
            pricing_type=pricing_type,
            is_active=True
        )

        # Filter by effective dates
        queryset = queryset.filter(
            Q(effective_from__isnull=True) | Q(effective_from__lte=effective_date),
            Q(effective_to__isnull=True) | Q(effective_to__gte=effective_date)
        )

        # Try to find target-specific rule first
        if target_id:
            specific_rule = queryset.filter(target_id=target_id).order_by('-priority').first()
            if specific_rule:
                return specific_rule

        # Fall back to general rule
        return queryset.filter(target_id__isnull=True).order_by('-priority').first()

    @staticmethod
    def calculate_price(
        organization_id: uuid.UUID,
        pricing_type: str,
        quantity: Decimal,
        target_id: uuid.UUID = None,
        is_weekend: bool = False,
        is_holiday: bool = False,
        is_night: bool = False,
        is_peak: bool = False,
        is_member: bool = False,
        effective_date: date = None,
        rule_id: uuid.UUID = None
    ) -> Dict[str, Any]:
        """
        Calculate price based on pricing rules.

        Args:
            organization_id: Organization UUID
            pricing_type: Type of pricing
            quantity: Quantity/units
            target_id: Specific target ID
            is_weekend: Weekend rate applies
            is_holiday: Holiday rate applies
            is_night: Night rate applies
            is_peak: Peak hour rate applies
            is_member: Member discount applies
            effective_date: Effective date for rule lookup
            rule_id: Specific rule to use (overrides lookup)

        Returns:
            Dict with price breakdown

        Raises:
            PricingRuleNotFoundError: If no applicable rule found
        """
        # Get pricing rule
        if rule_id:
            rule = PricingService.get_pricing_rule(rule_id, organization_id)
        else:
            rule = PricingService.get_applicable_rule(
                organization_id=organization_id,
                pricing_type=pricing_type,
                target_id=target_id,
                effective_date=effective_date
            )

        if not rule:
            raise PricingRuleNotFoundError(
                f"No pricing rule found for type: {pricing_type}"
            )

        # Calculate using the rule
        result = rule.calculate_price(
            quantity=quantity,
            is_weekend=is_weekend,
            is_holiday=is_holiday,
            is_night=is_night,
            is_peak=is_peak,
            is_member=is_member
        )

        # Add rule info
        result['rule_id'] = str(rule.id)
        result['rule_name'] = rule.name

        logger.debug(
            f"Calculated price using rule {rule.name}",
            extra={
                'rule_id': str(rule.id),
                'quantity': float(quantity),
                'total': result['total']
            }
        )

        return result

    @staticmethod
    def calculate_flight_price(
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID,
        hobbs_time: Decimal,
        instructor_id: uuid.UUID = None,
        instructor_time: Decimal = None,
        flight_datetime: datetime = None,
        is_member: bool = False,
        include_fuel: bool = False,
        fuel_gallons: Decimal = None
    ) -> Dict[str, Any]:
        """
        Calculate complete flight price.

        Args:
            organization_id: Organization UUID
            aircraft_id: Aircraft UUID
            hobbs_time: Hobbs time in hours
            instructor_id: Instructor UUID (if instructed flight)
            instructor_time: Instructor time in hours
            flight_datetime: Flight date/time for rate determination
            is_member: Member discount applies
            include_fuel: Include fuel charge
            fuel_gallons: Fuel quantity in gallons

        Returns:
            Dict with complete price breakdown
        """
        flight_datetime = flight_datetime or timezone.now()

        # Determine time-based modifiers
        is_weekend = flight_datetime.weekday() >= 5
        is_night = PricingService._is_night_time(flight_datetime.time())
        is_peak = PricingService._is_peak_time(flight_datetime.time())
        is_holiday = PricingService._is_holiday(flight_datetime.date())

        line_items = []
        total = Decimal('0')

        # Aircraft rental
        aircraft_price = PricingService.calculate_price(
            organization_id=organization_id,
            pricing_type=PricingType.AIRCRAFT,
            quantity=hobbs_time,
            target_id=aircraft_id,
            is_weekend=is_weekend,
            is_holiday=is_holiday,
            is_night=is_night,
            is_peak=is_peak,
            is_member=is_member
        )

        line_items.append({
            'type': 'aircraft_rental',
            'description': f"Aircraft rental ({hobbs_time} hours)",
            **aircraft_price
        })
        total += Decimal(str(aircraft_price['total']))

        # Instructor fee
        if instructor_id and instructor_time:
            instructor_price = PricingService.calculate_price(
                organization_id=organization_id,
                pricing_type=PricingType.INSTRUCTOR,
                quantity=instructor_time,
                target_id=instructor_id,
                is_weekend=is_weekend,
                is_holiday=is_holiday,
                is_member=is_member
            )

            line_items.append({
                'type': 'instructor_fee',
                'description': f"Instructor fee ({instructor_time} hours)",
                **instructor_price
            })
            total += Decimal(str(instructor_price['total']))

        # Fuel
        if include_fuel and fuel_gallons:
            fuel_price = PricingService.calculate_price(
                organization_id=organization_id,
                pricing_type=PricingType.FUEL,
                quantity=fuel_gallons,
                is_member=is_member
            )

            line_items.append({
                'type': 'fuel',
                'description': f"Fuel ({fuel_gallons} gallons)",
                **fuel_price
            })
            total += Decimal(str(fuel_price['total']))

        return {
            'line_items': line_items,
            'total': float(total),
            'currency': aircraft_price['currency'],
            'flight_datetime': flight_datetime.isoformat(),
            'modifiers_applied': {
                'weekend': is_weekend,
                'holiday': is_holiday,
                'night': is_night,
                'peak': is_peak,
                'member': is_member,
            }
        }

    @staticmethod
    def list_pricing_rules(
        organization_id: uuid.UUID,
        pricing_type: str = None,
        target_id: uuid.UUID = None,
        is_active: bool = None,
        effective_on: date = None,
        search: str = None,
        order_by: str = '-priority',
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List pricing rules with filtering.

        Args:
            organization_id: Organization UUID
            pricing_type: Filter by type
            target_id: Filter by target
            is_active: Filter by active status
            effective_on: Filter rules effective on date
            search: Search in name and description
            order_by: Order by field
            limit: Max results
            offset: Result offset

        Returns:
            Dict with rules and pagination info
        """
        queryset = PricingRule.objects.filter(organization_id=organization_id)

        if pricing_type:
            queryset = queryset.filter(pricing_type=pricing_type)

        if target_id:
            queryset = queryset.filter(target_id=target_id)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        if effective_on:
            queryset = queryset.filter(
                Q(effective_from__isnull=True) | Q(effective_from__lte=effective_on),
                Q(effective_to__isnull=True) | Q(effective_to__gte=effective_on)
            )

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(code__icontains=search)
            )

        total = queryset.count()
        rules = queryset.order_by(order_by)[offset:offset + limit]

        return {
            'rules': [
                PricingService._rule_to_dict(rule)
                for rule in rules
            ],
            'total': total,
            'limit': limit,
            'offset': offset,
        }

    @staticmethod
    def delete_pricing_rule(
        rule_id: uuid.UUID,
        organization_id: uuid.UUID = None
    ) -> bool:
        """
        Delete (deactivate) a pricing rule.

        Args:
            rule_id: Rule UUID
            organization_id: Optional organization filter

        Returns:
            True if deleted
        """
        rule = PricingService.get_pricing_rule(rule_id, organization_id)
        rule.is_active = False
        rule.save(update_fields=['is_active', 'updated_at'])

        logger.info(
            f"Deactivated pricing rule: {rule.name}",
            extra={'rule_id': str(rule_id)}
        )

        return True

    @staticmethod
    def duplicate_pricing_rule(
        rule_id: uuid.UUID,
        new_name: str = None,
        organization_id: uuid.UUID = None,
        created_by: uuid.UUID = None
    ) -> PricingRule:
        """
        Duplicate a pricing rule.

        Args:
            rule_id: Rule to duplicate
            new_name: Name for the new rule
            organization_id: Optional organization filter
            created_by: User who created

        Returns:
            New PricingRule instance
        """
        original = PricingService.get_pricing_rule(rule_id, organization_id)

        # Create copy
        new_rule = PricingRule.objects.create(
            organization_id=original.organization_id,
            name=new_name or f"{original.name} (Copy)",
            code=None,  # Clear code to avoid duplicates
            description=original.description,
            pricing_type=original.pricing_type,
            target_id=original.target_id,
            target_type=original.target_type,
            base_price=original.base_price,
            currency=original.currency,
            unit=original.unit,
            calculation_method=original.calculation_method,
            minimum_charge=original.minimum_charge,
            minimum_units=original.minimum_units,
            block_size=original.block_size,
            tiers=original.tiers,
            weekend_rate_multiplier=original.weekend_rate_multiplier,
            holiday_rate_multiplier=original.holiday_rate_multiplier,
            night_rate_multiplier=original.night_rate_multiplier,
            peak_rate_multiplier=original.peak_rate_multiplier,
            peak_hours_start=original.peak_hours_start,
            peak_hours_end=original.peak_hours_end,
            member_discount_percent=original.member_discount_percent,
            bulk_discount_enabled=original.bulk_discount_enabled,
            bulk_discount_tiers=original.bulk_discount_tiers,
            tax_rate=original.tax_rate,
            tax_inclusive=original.tax_inclusive,
            priority=original.priority,
            metadata=original.metadata,
            created_by=created_by,
            is_active=True
        )

        logger.info(
            f"Duplicated pricing rule: {original.name} -> {new_rule.name}",
            extra={
                'original_rule_id': str(rule_id),
                'new_rule_id': str(new_rule.id)
            }
        )

        return new_rule

    @staticmethod
    def _is_night_time(t: time) -> bool:
        """Check if time is considered night (after sunset/before sunrise)."""
        # Simple check: night is between 8 PM and 6 AM
        night_start = time(20, 0)
        night_end = time(6, 0)
        return t >= night_start or t <= night_end

    @staticmethod
    def _is_peak_time(t: time) -> bool:
        """Check if time is peak hours."""
        # Peak hours: 9 AM - 12 PM and 3 PM - 6 PM
        morning_peak = time(9, 0) <= t <= time(12, 0)
        afternoon_peak = time(15, 0) <= t <= time(18, 0)
        return morning_peak or afternoon_peak

    @staticmethod
    def _is_holiday(d: date) -> bool:
        """Check if date is a holiday."""
        # This should be expanded with proper holiday calendar
        # For now, just return False
        # In production, integrate with holiday calendar service
        return False

    @staticmethod
    def _rule_to_dict(rule: PricingRule) -> Dict[str, Any]:
        """Convert pricing rule to dictionary."""
        return {
            'id': str(rule.id),
            'name': rule.name,
            'code': rule.code,
            'description': rule.description,
            'pricing_type': rule.pricing_type,
            'target_id': str(rule.target_id) if rule.target_id else None,
            'target_type': rule.target_type,
            'base_price': float(rule.base_price),
            'currency': rule.currency,
            'unit': rule.unit,
            'calculation_method': rule.calculation_method,
            'minimum_charge': float(rule.minimum_charge) if rule.minimum_charge else None,
            'minimum_units': float(rule.minimum_units) if rule.minimum_units else None,
            'block_size': float(rule.block_size) if rule.block_size else None,
            'tiers': rule.tiers,
            'weekend_rate_multiplier': float(rule.weekend_rate_multiplier),
            'holiday_rate_multiplier': float(rule.holiday_rate_multiplier),
            'night_rate_multiplier': float(rule.night_rate_multiplier),
            'peak_rate_multiplier': float(rule.peak_rate_multiplier),
            'member_discount_percent': float(rule.member_discount_percent) if rule.member_discount_percent else None,
            'bulk_discount_enabled': rule.bulk_discount_enabled,
            'bulk_discount_tiers': rule.bulk_discount_tiers,
            'tax_rate': float(rule.tax_rate) if rule.tax_rate else None,
            'tax_inclusive': rule.tax_inclusive,
            'effective_from': rule.effective_from.isoformat() if rule.effective_from else None,
            'effective_to': rule.effective_to.isoformat() if rule.effective_to else None,
            'is_active': rule.is_active,
            'is_effective': rule.is_effective,
            'priority': rule.priority,
            'created_at': rule.created_at.isoformat(),
        }
