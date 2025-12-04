# services/finance-service/src/apps/core/api/serializers/payment_serializers.py
"""
Payment Serializers

DRF serializers for payment method and processing management.
"""

from decimal import Decimal
from rest_framework import serializers

from ...models.payment import PaymentMethod, PaymentMethodType, PaymentMethodStatus


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Base payment method serializer."""

    display_name = serializers.CharField(read_only=True)
    is_card = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    expiry_display = serializers.CharField(read_only=True)

    class Meta:
        model = PaymentMethod
        fields = [
            'id',
            'organization_id',
            'account',
            'method_type',
            'card_brand',
            'card_last_four',
            'card_exp_month',
            'card_exp_year',
            'bank_name',
            'bank_last_four',
            'display_name',
            'is_card',
            'is_expired',
            'is_expiring_soon',
            'expiry_display',
            'is_default',
            'is_verified',
            'status',
            'nickname',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'organization_id',
            'created_at',
        ]


class PaymentMethodListSerializer(serializers.ModelSerializer):
    """Serializer for payment method list views."""

    display_name = serializers.CharField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    expiry_display = serializers.CharField(read_only=True)
    account_number = serializers.CharField(source='account.account_number', read_only=True)

    class Meta:
        model = PaymentMethod
        fields = [
            'id',
            'account',
            'account_number',
            'method_type',
            'card_brand',
            'card_last_four',
            'card_exp_month',
            'card_exp_year',
            'bank_name',
            'bank_last_four',
            'display_name',
            'expiry_display',
            'is_expired',
            'is_expiring_soon',
            'is_default',
            'is_verified',
            'status',
            'nickname',
            'created_at',
        ]


class PaymentMethodDetailSerializer(serializers.ModelSerializer):
    """Detailed payment method serializer."""

    display_name = serializers.CharField(read_only=True)
    is_card = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    expiry_display = serializers.CharField(read_only=True)
    account_number = serializers.CharField(source='account.account_number', read_only=True)

    class Meta:
        model = PaymentMethod
        fields = [
            'id',
            'organization_id',
            'account',
            'account_number',
            'method_type',
            'card_brand',
            'card_last_four',
            'card_exp_month',
            'card_exp_year',
            'card_holder_name',
            'card_funding',
            'bank_name',
            'bank_account_type',
            'bank_last_four',
            'bank_routing_last_four',
            'gateway_name',
            'billing_name',
            'billing_email',
            'billing_phone',
            'billing_address_line1',
            'billing_address_line2',
            'billing_city',
            'billing_state',
            'billing_postal_code',
            'billing_country',
            'display_name',
            'is_card',
            'is_expired',
            'is_expiring_soon',
            'expiry_display',
            'is_default',
            'is_verified',
            'verified_at',
            'status',
            'status_reason',
            'nickname',
            'total_charges',
            'total_amount_charged',
            'last_charge_at',
            'failure_count',
            'last_failure_at',
            'last_failure_reason',
            'metadata',
            'created_at',
            'updated_at',
        ]


class BillingAddressSerializer(serializers.Serializer):
    """Serializer for billing address."""

    name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=50, required=False)
    line1 = serializers.CharField(max_length=255, required=False)
    line2 = serializers.CharField(max_length=255, required=False)
    city = serializers.CharField(max_length=100, required=False)
    state = serializers.CharField(max_length=100, required=False)
    postal_code = serializers.CharField(max_length=20, required=False)
    country = serializers.CharField(max_length=2, default='US')


class PaymentMethodCreateSerializer(serializers.Serializer):
    """Serializer for creating a payment method."""

    account_id = serializers.UUIDField(required=True)
    method_type = serializers.ChoiceField(choices=PaymentMethodType.choices)
    gateway_name = serializers.CharField(max_length=50, default='stripe')
    gateway_token = serializers.CharField(required=False)

    # Card fields
    card_brand = serializers.CharField(max_length=50, required=False)
    card_last_four = serializers.CharField(max_length=4, required=False)
    card_exp_month = serializers.IntegerField(required=False, min_value=1, max_value=12)
    card_exp_year = serializers.IntegerField(required=False, min_value=2020)
    card_holder_name = serializers.CharField(max_length=255, required=False)

    # Bank fields
    bank_name = serializers.CharField(max_length=255, required=False)
    bank_account_type = serializers.ChoiceField(
        choices=['checking', 'savings'],
        required=False
    )
    bank_last_four = serializers.CharField(max_length=4, required=False)

    # Billing address
    billing_address = BillingAddressSerializer(required=False)

    # Options
    nickname = serializers.CharField(max_length=100, required=False)
    is_default = serializers.BooleanField(default=False)
    metadata = serializers.JSONField(required=False, default=dict)

    def validate(self, data):
        method_type = data.get('method_type')

        # Validate card fields for card types
        if method_type in [PaymentMethodType.CREDIT_CARD, PaymentMethodType.DEBIT_CARD]:
            if not data.get('card_last_four'):
                raise serializers.ValidationError({
                    'card_last_four': 'Required for card payment methods'
                })

        # Validate bank fields for bank types
        if method_type in [PaymentMethodType.BANK_ACCOUNT, PaymentMethodType.ACH]:
            if not data.get('bank_last_four'):
                raise serializers.ValidationError({
                    'bank_last_four': 'Required for bank account payment methods'
                })

        return data


class PaymentMethodUpdateSerializer(serializers.Serializer):
    """Serializer for updating a payment method."""

    nickname = serializers.CharField(max_length=100, required=False, allow_null=True)
    billing_address = BillingAddressSerializer(required=False)
    is_default = serializers.BooleanField(required=False)
    metadata = serializers.JSONField(required=False)


class ProcessPaymentSerializer(serializers.Serializer):
    """Serializer for processing a payment."""

    account_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    payment_method_id = serializers.UUIDField(required=False)
    description = serializers.CharField(max_length=500, required=False)
    invoice_id = serializers.UUIDField(required=False)
    idempotency_key = serializers.CharField(max_length=255, required=False)
    metadata = serializers.JSONField(required=False, default=dict)


class ProcessRefundSerializer(serializers.Serializer):
    """Serializer for processing a refund."""

    original_transaction_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        min_value=Decimal('0.01')
    )
    reason = serializers.CharField(max_length=500, required=False)


class VerifyPaymentMethodSerializer(serializers.Serializer):
    """Serializer for verifying a payment method."""

    verification_amounts = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=99),
        min_length=2,
        max_length=2,
        required=False,
        help_text='Two micro-deposit amounts in cents'
    )


class PaymentResultSerializer(serializers.Serializer):
    """Serializer for payment processing result."""

    success = serializers.BooleanField()
    transaction_id = serializers.CharField()
    transaction_number = serializers.CharField()
    gateway_transaction_id = serializers.CharField(allow_null=True)
    amount = serializers.FloatField()
    payment_method_id = serializers.CharField(allow_null=True)


class RefundResultSerializer(serializers.Serializer):
    """Serializer for refund processing result."""

    success = serializers.BooleanField()
    transaction_id = serializers.CharField()
    transaction_number = serializers.CharField()
    gateway_refund_id = serializers.CharField(allow_null=True)
    amount = serializers.FloatField()


class VerificationResultSerializer(serializers.Serializer):
    """Serializer for verification result."""

    success = serializers.BooleanField()
    payment_method_id = serializers.CharField()
    already_verified = serializers.BooleanField(required=False)
    verification_attempts = serializers.IntegerField(required=False)
    message = serializers.CharField(required=False)


class PaymentMethodFilterSerializer(serializers.Serializer):
    """Serializer for payment method filtering parameters."""

    account_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=PaymentMethodStatus.choices, required=False
    )
    method_type = serializers.ChoiceField(
        choices=PaymentMethodType.choices, required=False
    )
    order_by = serializers.CharField(default='-created_at')
    limit = serializers.IntegerField(default=50, max_value=100)
    offset = serializers.IntegerField(default=0)


class ExpiringCardsFilterSerializer(serializers.Serializer):
    """Serializer for finding expiring cards."""

    days_ahead = serializers.IntegerField(default=30, min_value=1, max_value=365)
