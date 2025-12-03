# services/organization-service/src/apps/core/serializers/subscription.py
"""
Subscription Serializers

Serializers for subscription management API endpoints.
"""

from rest_framework import serializers
from apps.core.models import SubscriptionPlan, SubscriptionHistory


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Full subscription plan serializer."""

    yearly_savings = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    yearly_discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id',
            'code',
            'name',
            'description',
            'price_monthly',
            'price_yearly',
            'yearly_savings',
            'yearly_discount_percent',
            'currency',
            'max_users',
            'max_aircraft',
            'max_students',
            'max_locations',
            'storage_limit_gb',
            'features',
            'trial_days',
            'badge_text',
            'badge_color',
            'display_order',
            'is_active',
            'is_public',
        ]


class SubscriptionPlanListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for plan lists."""

    yearly_discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id',
            'code',
            'name',
            'description',
            'price_monthly',
            'price_yearly',
            'yearly_discount_percent',
            'currency',
            'max_users',
            'max_aircraft',
            'max_students',
            'features',
            'badge_text',
            'badge_color',
            'display_order',
        ]


class SubscriptionStatusSerializer(serializers.Serializer):
    """Serializer for subscription status response."""

    organization_id = serializers.UUIDField(read_only=True)
    status = serializers.CharField(read_only=True)
    plan = serializers.DictField(read_only=True, allow_null=True)
    is_trial = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    limits = serializers.DictField(read_only=True)
    features = serializers.DictField(read_only=True)
    dates = serializers.DictField(read_only=True)
    trial = serializers.DictField(read_only=True, required=False)


class SubscriptionChangeSerializer(serializers.Serializer):
    """Serializer for changing subscription plans."""

    plan_code = serializers.CharField(max_length=50)
    billing_cycle = serializers.ChoiceField(
        choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')],
        default='monthly'
    )
    payment_reference = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True
    )


class SubscriptionCancelSerializer(serializers.Serializer):
    """Serializer for cancelling subscription."""

    reason = serializers.CharField(required=False, allow_blank=True)
    end_immediately = serializers.BooleanField(default=False)


class SubscriptionHistorySerializer(serializers.ModelSerializer):
    """Serializer for subscription history."""

    from_plan_name = serializers.CharField(
        source='from_plan.name',
        read_only=True,
        allow_null=True
    )
    from_plan_code = serializers.CharField(
        source='from_plan.code',
        read_only=True,
        allow_null=True
    )
    to_plan_name = serializers.CharField(
        source='to_plan.name',
        read_only=True,
        allow_null=True
    )
    to_plan_code = serializers.CharField(
        source='to_plan.code',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = SubscriptionHistory
        fields = [
            'id',
            'change_type',
            'from_plan_name',
            'from_plan_code',
            'to_plan_name',
            'to_plan_code',
            'reason',
            'amount',
            'currency',
            'billing_period_start',
            'billing_period_end',
            'payment_reference',
            'metadata',
            'created_at',
            'created_by',
        ]
