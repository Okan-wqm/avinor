# services/finance-service/src/apps/core/api/serializers/pricing_serializers.py
"""
Pricing Serializers

DRF serializers for pricing rule management.
"""

from decimal import Decimal
from rest_framework import serializers

from ...models.pricing import PricingRule, PricingType, CalculationMethod


class TierSerializer(serializers.Serializer):
    """Serializer for pricing tiers."""

    from_units = serializers.DecimalField(
        max_digits=10, decimal_places=2, source='from'
    )
    to_units = serializers.DecimalField(
        max_digits=10, decimal_places=2, source='to', allow_null=True
    )
    price = serializers.DecimalField(max_digits=10, decimal_places=2)


class BulkDiscountTierSerializer(serializers.Serializer):
    """Serializer for bulk discount tiers."""

    min_units = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = serializers.DecimalField(max_digits=5, decimal_places=2)


class PricingRuleSerializer(serializers.ModelSerializer):
    """Base pricing rule serializer."""

    is_effective = serializers.BooleanField(read_only=True)

    class Meta:
        model = PricingRule
        fields = [
            'id',
            'organization_id',
            'name',
            'code',
            'description',
            'pricing_type',
            'target_id',
            'target_type',
            'base_price',
            'currency',
            'unit',
            'calculation_method',
            'is_active',
            'is_effective',
            'priority',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'organization_id',
            'created_at',
        ]


class PricingRuleListSerializer(serializers.ModelSerializer):
    """Serializer for pricing rule list views."""

    is_effective = serializers.BooleanField(read_only=True)

    class Meta:
        model = PricingRule
        fields = [
            'id',
            'name',
            'code',
            'pricing_type',
            'target_id',
            'target_type',
            'base_price',
            'currency',
            'unit',
            'calculation_method',
            'is_active',
            'is_effective',
            'priority',
            'effective_from',
            'effective_to',
            'created_at',
        ]


class PricingRuleDetailSerializer(serializers.ModelSerializer):
    """Detailed pricing rule serializer."""

    is_effective = serializers.BooleanField(read_only=True)

    class Meta:
        model = PricingRule
        fields = [
            'id',
            'organization_id',
            'name',
            'code',
            'description',
            'pricing_type',
            'target_id',
            'target_type',
            'base_price',
            'currency',
            'unit',
            'unit_name',
            'calculation_method',
            'block_size',
            'minimum_charge',
            'minimum_units',
            'tiers',
            'time_based_rates',
            'weekend_rate_multiplier',
            'holiday_rate_multiplier',
            'night_rate_multiplier',
            'peak_rate_multiplier',
            'peak_hours_start',
            'peak_hours_end',
            'discount_eligible',
            'member_discount_percent',
            'bulk_discount_enabled',
            'bulk_discount_tiers',
            'tax_inclusive',
            'tax_rate',
            'tax_category',
            'applicable_aircraft_types',
            'applicable_user_types',
            'applicable_membership_levels',
            'effective_from',
            'effective_to',
            'is_active',
            'is_effective',
            'priority',
            'metadata',
            'created_by',
            'created_at',
            'updated_at',
        ]


class PricingRuleCreateSerializer(serializers.Serializer):
    """Serializer for pricing rule creation."""

    name = serializers.CharField(max_length=255)
    code = serializers.CharField(max_length=50, required=False)
    description = serializers.CharField(required=False)
    pricing_type = serializers.ChoiceField(choices=PricingType.choices)
    target_id = serializers.UUIDField(required=False)
    target_type = serializers.CharField(max_length=50, required=False)
    base_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal('0')
    )
    currency = serializers.CharField(max_length=3, default='USD')
    unit = serializers.CharField(max_length=20, default='hour')
    unit_name = serializers.CharField(max_length=50, required=False)
    calculation_method = serializers.ChoiceField(
        choices=CalculationMethod.choices,
        default=CalculationMethod.PER_UNIT
    )
    block_size = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    minimum_charge = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    minimum_units = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    tiers = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    weekend_rate_multiplier = serializers.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('1.00')
    )
    holiday_rate_multiplier = serializers.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('1.00')
    )
    night_rate_multiplier = serializers.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('1.00')
    )
    peak_rate_multiplier = serializers.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('1.00')
    )
    peak_hours_start = serializers.TimeField(required=False)
    peak_hours_end = serializers.TimeField(required=False)
    member_discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    bulk_discount_tiers = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    tax_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    tax_inclusive = serializers.BooleanField(default=False)
    effective_from = serializers.DateField(required=False)
    effective_to = serializers.DateField(required=False)
    priority = serializers.IntegerField(default=0)
    metadata = serializers.JSONField(required=False, default=dict)


class PricingRuleUpdateSerializer(serializers.Serializer):
    """Serializer for pricing rule updates."""

    name = serializers.CharField(max_length=255, required=False)
    code = serializers.CharField(max_length=50, required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_null=True)
    base_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, min_value=Decimal('0')
    )
    currency = serializers.CharField(max_length=3, required=False)
    unit = serializers.CharField(max_length=20, required=False)
    calculation_method = serializers.ChoiceField(
        choices=CalculationMethod.choices, required=False
    )
    block_size = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    minimum_charge = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    minimum_units = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    tiers = serializers.ListField(
        child=serializers.DictField(), required=False
    )
    weekend_rate_multiplier = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    holiday_rate_multiplier = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    night_rate_multiplier = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    peak_rate_multiplier = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    member_discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    bulk_discount_tiers = serializers.ListField(
        child=serializers.DictField(), required=False
    )
    tax_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    tax_inclusive = serializers.BooleanField(required=False)
    effective_from = serializers.DateField(required=False, allow_null=True)
    effective_to = serializers.DateField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)
    priority = serializers.IntegerField(required=False)
    metadata = serializers.JSONField(required=False)


class CalculatePriceSerializer(serializers.Serializer):
    """Serializer for price calculation request."""

    pricing_type = serializers.ChoiceField(choices=PricingType.choices)
    quantity = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal('0.01')
    )
    target_id = serializers.UUIDField(required=False)
    rule_id = serializers.UUIDField(required=False)
    is_weekend = serializers.BooleanField(default=False)
    is_holiday = serializers.BooleanField(default=False)
    is_night = serializers.BooleanField(default=False)
    is_peak = serializers.BooleanField(default=False)
    is_member = serializers.BooleanField(default=False)
    effective_date = serializers.DateField(required=False)


class CalculateFlightPriceSerializer(serializers.Serializer):
    """Serializer for flight price calculation request."""

    aircraft_id = serializers.UUIDField(required=True)
    hobbs_time = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal('0.1')
    )
    instructor_id = serializers.UUIDField(required=False)
    instructor_time = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, min_value=Decimal('0')
    )
    flight_datetime = serializers.DateTimeField(required=False)
    is_member = serializers.BooleanField(default=False)
    include_fuel = serializers.BooleanField(default=False)
    fuel_gallons = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False
    )


class PriceCalculationResultSerializer(serializers.Serializer):
    """Serializer for price calculation result."""

    rule_id = serializers.CharField()
    rule_name = serializers.CharField()
    base_price = serializers.FloatField()
    quantity = serializers.FloatField()
    base_amount = serializers.FloatField()
    modifiers = serializers.ListField(child=serializers.DictField())
    adjusted_amount = serializers.FloatField()
    discount_amount = serializers.FloatField()
    subtotal = serializers.FloatField()
    tax_rate = serializers.FloatField(allow_null=True)
    tax_amount = serializers.FloatField()
    total = serializers.FloatField()
    currency = serializers.CharField()
    unit = serializers.CharField()


class FlightPriceResultSerializer(serializers.Serializer):
    """Serializer for flight price calculation result."""

    line_items = serializers.ListField(child=serializers.DictField())
    total = serializers.FloatField()
    currency = serializers.CharField()
    flight_datetime = serializers.CharField()
    modifiers_applied = serializers.DictField()


class DuplicatePricingRuleSerializer(serializers.Serializer):
    """Serializer for duplicating pricing rule."""

    new_name = serializers.CharField(max_length=255, required=False)


class PricingRuleFilterSerializer(serializers.Serializer):
    """Serializer for pricing rule filtering parameters."""

    pricing_type = serializers.ChoiceField(
        choices=PricingType.choices, required=False
    )
    target_id = serializers.UUIDField(required=False)
    is_active = serializers.BooleanField(required=False)
    effective_on = serializers.DateField(required=False)
    search = serializers.CharField(required=False)
    order_by = serializers.CharField(default='-priority')
    limit = serializers.IntegerField(default=50, max_value=100)
    offset = serializers.IntegerField(default=0)
