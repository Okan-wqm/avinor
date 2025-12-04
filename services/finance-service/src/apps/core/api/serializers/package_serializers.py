# services/finance-service/src/apps/core/api/serializers/package_serializers.py
"""
Package Serializers

DRF serializers for credit package management.
"""

from decimal import Decimal
from rest_framework import serializers

from ...models.package import (
    CreditPackage, UserPackage, PackageType, PackageStatus, UserPackageStatus
)


class CreditPackageSerializer(serializers.ModelSerializer):
    """Base credit package serializer."""

    is_purchasable = serializers.BooleanField(read_only=True)
    value_per_dollar = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )

    class Meta:
        model = CreditPackage
        fields = [
            'id',
            'organization_id',
            'name',
            'description',
            'package_type',
            'price',
            'currency',
            'credit_amount',
            'hours_amount',
            'effective_credit_amount',
            'features',
            'validity_days',
            'bonus_percent',
            'discount_percent',
            'is_purchasable',
            'value_per_dollar',
            'status',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'organization_id',
            'effective_credit_amount',
            'created_at',
        ]


class CreditPackageListSerializer(serializers.ModelSerializer):
    """Serializer for package list views."""

    is_purchasable = serializers.BooleanField(read_only=True)

    class Meta:
        model = CreditPackage
        fields = [
            'id',
            'name',
            'description',
            'package_type',
            'price',
            'currency',
            'credit_amount',
            'hours_amount',
            'effective_credit_amount',
            'validity_days',
            'bonus_percent',
            'discount_percent',
            'is_purchasable',
            'is_featured',
            'is_promotional',
            'status',
            'sort_order',
            'created_at',
        ]


class CreditPackageDetailSerializer(serializers.ModelSerializer):
    """Detailed credit package serializer."""

    is_purchasable = serializers.BooleanField(read_only=True)
    value_per_dollar = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )

    class Meta:
        model = CreditPackage
        fields = [
            'id',
            'organization_id',
            'name',
            'description',
            'package_type',
            'price',
            'currency',
            'credit_amount',
            'hours_amount',
            'effective_credit_amount',
            'features',
            'terms',
            'validity_days',
            'bonus_percent',
            'discount_percent',
            'max_purchases_per_user',
            'applicable_aircraft_ids',
            'applicable_instructor_ids',
            'is_transferable',
            'is_refundable',
            'is_promotional',
            'promotion_start',
            'promotion_end',
            'is_featured',
            'is_purchasable',
            'value_per_dollar',
            'status',
            'available_from',
            'available_to',
            'total_sold',
            'total_revenue',
            'sort_order',
            'metadata',
            'created_by',
            'created_at',
            'updated_at',
        ]


class CreditPackageCreateSerializer(serializers.Serializer):
    """Serializer for credit package creation."""

    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False)
    package_type = serializers.ChoiceField(choices=PackageType.choices)
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal('0')
    )
    currency = serializers.CharField(max_length=3, default='USD')
    credit_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )
    hours_amount = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False
    )
    features = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    terms = serializers.CharField(required=False)
    validity_days = serializers.IntegerField(default=365)
    bonus_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    max_purchases_per_user = serializers.IntegerField(required=False)
    applicable_aircraft_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False
    )
    applicable_instructor_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False
    )
    is_transferable = serializers.BooleanField(default=False)
    is_refundable = serializers.BooleanField(default=False)
    is_promotional = serializers.BooleanField(default=False)
    promotion_start = serializers.DateField(required=False)
    promotion_end = serializers.DateField(required=False)
    is_featured = serializers.BooleanField(default=False)
    available_from = serializers.DateField(required=False)
    available_to = serializers.DateField(required=False)
    sort_order = serializers.IntegerField(default=0)
    metadata = serializers.JSONField(required=False, default=dict)


class CreditPackageUpdateSerializer(serializers.Serializer):
    """Serializer for credit package updates."""

    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_null=True)
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, min_value=Decimal('0')
    )
    credit_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )
    hours_amount = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False
    )
    features = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    terms = serializers.CharField(required=False, allow_null=True)
    validity_days = serializers.IntegerField(required=False)
    bonus_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    max_purchases_per_user = serializers.IntegerField(required=False, allow_null=True)
    is_promotional = serializers.BooleanField(required=False)
    promotion_start = serializers.DateField(required=False, allow_null=True)
    promotion_end = serializers.DateField(required=False, allow_null=True)
    is_featured = serializers.BooleanField(required=False)
    status = serializers.ChoiceField(choices=PackageStatus.choices, required=False)
    available_from = serializers.DateField(required=False, allow_null=True)
    available_to = serializers.DateField(required=False, allow_null=True)
    sort_order = serializers.IntegerField(required=False)
    metadata = serializers.JSONField(required=False)


class UserPackageSerializer(serializers.ModelSerializer):
    """Base user package serializer."""

    package_name = serializers.CharField(source='package.name', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_fully_used = serializers.BooleanField(read_only=True)
    credit_usage_percent = serializers.FloatField(read_only=True)
    hours_usage_percent = serializers.FloatField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = UserPackage
        fields = [
            'id',
            'organization_id',
            'user_id',
            'package',
            'package_name',
            'credit_remaining',
            'credit_used',
            'hours_remaining',
            'hours_used',
            'credit_usage_percent',
            'hours_usage_percent',
            'is_expired',
            'is_fully_used',
            'days_until_expiry',
            'expires_at',
            'status',
            'purchased_at',
        ]


class UserPackageListSerializer(serializers.ModelSerializer):
    """Serializer for user package list views."""

    package_name = serializers.CharField(source='package.name', read_only=True)
    package_type = serializers.CharField(source='package.package_type', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = UserPackage
        fields = [
            'id',
            'user_id',
            'package',
            'package_name',
            'package_type',
            'credit_remaining',
            'hours_remaining',
            'is_expired',
            'days_until_expiry',
            'expires_at',
            'status',
            'purchased_at',
        ]


class UserPackageDetailSerializer(serializers.ModelSerializer):
    """Detailed user package serializer."""

    package_name = serializers.CharField(source='package.name', read_only=True)
    package_type = serializers.CharField(source='package.package_type', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_fully_used = serializers.BooleanField(read_only=True)
    credit_usage_percent = serializers.FloatField(read_only=True)
    hours_usage_percent = serializers.FloatField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = UserPackage
        fields = [
            'id',
            'organization_id',
            'user_id',
            'package',
            'package_name',
            'package_type',
            'purchase_price',
            'currency',
            'credit_remaining',
            'credit_used',
            'hours_remaining',
            'hours_used',
            'credit_usage_percent',
            'hours_usage_percent',
            'usage_history',
            'usage_count',
            'is_expired',
            'is_fully_used',
            'days_until_expiry',
            'expires_at',
            'last_used_at',
            'payment_method',
            'payment_reference',
            'status',
            'cancellation_reason',
            'cancelled_at',
            'metadata',
            'purchased_at',
        ]


class PurchasePackageSerializer(serializers.Serializer):
    """Serializer for purchasing a package."""

    package_id = serializers.UUIDField(required=True)
    user_id = serializers.UUIDField(required=True)
    account_id = serializers.UUIDField(required=True)
    payment_method = serializers.CharField(max_length=50, default='account')
    payment_reference = serializers.CharField(max_length=255, required=False)
    metadata = serializers.JSONField(required=False, default=dict)


class UsePackageCreditSerializer(serializers.Serializer):
    """Serializer for using package credit."""

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    description = serializers.CharField(max_length=500, required=False)
    reference_type = serializers.CharField(max_length=50, required=False)
    reference_id = serializers.UUIDField(required=False)


class UsePackageHoursSerializer(serializers.Serializer):
    """Serializer for using package hours."""

    hours = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=Decimal('0.1')
    )
    description = serializers.CharField(max_length=500, required=False)
    reference_type = serializers.CharField(max_length=50, required=False)
    reference_id = serializers.UUIDField(required=False)


class CancelUserPackageSerializer(serializers.Serializer):
    """Serializer for cancelling user package."""

    reason = serializers.CharField(max_length=500, required=False)
    refund_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )


class PackageUsageStatsSerializer(serializers.Serializer):
    """Serializer for package usage statistics."""

    user_package_id = serializers.UUIDField()
    package_name = serializers.CharField()
    credit = serializers.DictField(child=serializers.FloatField())
    hours = serializers.DictField(child=serializers.FloatField())
    usage_history = serializers.ListField(child=serializers.DictField())
    usage_count = serializers.IntegerField()
    last_used_at = serializers.CharField(allow_null=True)
    purchased_at = serializers.CharField()
    expires_at = serializers.CharField(allow_null=True)
    days_until_expiry = serializers.IntegerField(allow_null=True)
    status = serializers.CharField()


class AvailableCreditSerializer(serializers.Serializer):
    """Serializer for available credit response."""

    user_id = serializers.UUIDField()
    total_credit = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_hours = serializers.DecimalField(max_digits=8, decimal_places=2)
    active_packages = UserPackageListSerializer(many=True)


class PackageFilterSerializer(serializers.Serializer):
    """Serializer for package filtering parameters."""

    package_type = serializers.ChoiceField(
        choices=PackageType.choices, required=False
    )
    is_active = serializers.BooleanField(required=False)
    is_available = serializers.BooleanField(required=False)
    search = serializers.CharField(required=False)
    order_by = serializers.CharField(default='-sort_order')
    limit = serializers.IntegerField(default=50, max_value=100)
    offset = serializers.IntegerField(default=0)


class UserPackageFilterSerializer(serializers.Serializer):
    """Serializer for user package filtering parameters."""

    user_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=UserPackageStatus.choices, required=False
    )
    include_expired = serializers.BooleanField(default=False)
    order_by = serializers.CharField(default='-purchased_at')
    limit = serializers.IntegerField(default=50, max_value=100)
    offset = serializers.IntegerField(default=0)
