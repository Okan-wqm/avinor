# services/finance-service/src/apps/core/api/serializers/transaction_serializers.py
"""
Transaction Serializers

DRF serializers for transaction management.
"""

from decimal import Decimal
from rest_framework import serializers

from ...models.transaction import (
    Transaction, TransactionType, TransactionSubtype, TransactionStatus
)


class TransactionSerializer(serializers.ModelSerializer):
    """Base transaction serializer."""

    net_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    is_debit = serializers.BooleanField(read_only=True)
    is_credit = serializers.BooleanField(read_only=True)
    is_reversible = serializers.BooleanField(read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id',
            'organization_id',
            'account',
            'transaction_number',
            'transaction_type',
            'transaction_subtype',
            'amount',
            'currency',
            'balance_before',
            'balance_after',
            'balance_impact',
            'reference_type',
            'reference_id',
            'description',
            'status',
            'reversed',
            'tax_amount',
            'discount_amount',
            'net_amount',
            'is_debit',
            'is_credit',
            'is_reversible',
            'transaction_date',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'organization_id',
            'transaction_number',
            'balance_before',
            'balance_after',
            'balance_impact',
            'created_at',
        ]


class TransactionListSerializer(serializers.ModelSerializer):
    """Serializer for transaction list views."""

    account_number = serializers.CharField(source='account.account_number', read_only=True)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id',
            'transaction_number',
            'account',
            'account_number',
            'transaction_type',
            'transaction_subtype',
            'amount',
            'currency',
            'balance_impact',
            'description',
            'status',
            'reversed',
            'net_amount',
            'transaction_date',
            'created_at',
        ]


class TransactionDetailSerializer(serializers.ModelSerializer):
    """Detailed transaction serializer."""

    account_number = serializers.CharField(source='account.account_number', read_only=True)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_debit = serializers.BooleanField(read_only=True)
    is_credit = serializers.BooleanField(read_only=True)
    is_reversible = serializers.BooleanField(read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id',
            'organization_id',
            'account',
            'account_number',
            'transaction_number',
            'transaction_type',
            'transaction_subtype',
            'amount',
            'currency',
            'balance_before',
            'balance_after',
            'balance_impact',
            'reference_type',
            'reference_id',
            'external_reference',
            'description',
            'line_items',
            'payment_method',
            'payment_method_id',
            'payment_reference',
            'gateway_name',
            'gateway_transaction_id',
            'status',
            'status_message',
            'reversed',
            'reversal_id',
            'reversal_reason',
            'original_transaction_id',
            'invoice_id',
            'tax_amount',
            'tax_rate',
            'tax_breakdown',
            'discount_amount',
            'discount_code',
            'discount_description',
            'net_amount',
            'is_debit',
            'is_credit',
            'is_reversible',
            'created_by',
            'approved_by',
            'metadata',
            'transaction_date',
            'created_at',
            'updated_at',
        ]


class LineItemSerializer(serializers.Serializer):
    """Serializer for transaction line items."""

    description = serializers.CharField(max_length=500)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    quantity = serializers.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('1')
    )
    unit_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    type = serializers.CharField(max_length=50, required=False)
    reference_id = serializers.CharField(required=False)


class CreateChargeSerializer(serializers.Serializer):
    """Serializer for creating a charge transaction."""

    account_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    subtype = serializers.ChoiceField(
        choices=TransactionSubtype.choices,
        default=TransactionSubtype.OTHER_CHARGE
    )
    description = serializers.CharField(max_length=500, required=False)
    reference_type = serializers.CharField(max_length=50, required=False)
    reference_id = serializers.UUIDField(required=False)
    line_items = LineItemSerializer(many=True, required=False)
    tax_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0')
    )
    tax_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    discount_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0')
    )
    discount_code = serializers.CharField(max_length=50, required=False)
    invoice_id = serializers.UUIDField(required=False)
    metadata = serializers.JSONField(required=False, default=dict)


class CreatePaymentSerializer(serializers.Serializer):
    """Serializer for creating a payment transaction."""

    account_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    payment_method = serializers.CharField(max_length=50, required=True)
    subtype = serializers.ChoiceField(
        choices=[
            TransactionSubtype.CASH_PAYMENT,
            TransactionSubtype.CARD_PAYMENT,
            TransactionSubtype.BANK_TRANSFER,
            TransactionSubtype.CHECK_PAYMENT,
            TransactionSubtype.PACKAGE_CREDIT,
            TransactionSubtype.DEPOSIT,
        ],
        default=TransactionSubtype.CARD_PAYMENT
    )
    description = serializers.CharField(max_length=500, required=False)
    reference_type = serializers.CharField(max_length=50, required=False)
    reference_id = serializers.UUIDField(required=False)
    payment_method_id = serializers.UUIDField(required=False)
    payment_reference = serializers.CharField(max_length=255, required=False)
    gateway_name = serializers.CharField(max_length=50, required=False)
    gateway_transaction_id = serializers.CharField(max_length=255, required=False)
    invoice_id = serializers.UUIDField(required=False)
    metadata = serializers.JSONField(required=False, default=dict)


class CreateRefundSerializer(serializers.Serializer):
    """Serializer for creating a refund transaction."""

    account_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    original_transaction_id = serializers.UUIDField(required=False)
    description = serializers.CharField(max_length=500, required=False)
    reference_type = serializers.CharField(max_length=50, required=False)
    reference_id = serializers.UUIDField(required=False)
    gateway_name = serializers.CharField(max_length=50, required=False)
    gateway_transaction_id = serializers.CharField(max_length=255, required=False)
    metadata = serializers.JSONField(required=False, default=dict)


class CreateCreditSerializer(serializers.Serializer):
    """Serializer for creating a credit transaction."""

    account_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    subtype = serializers.ChoiceField(
        choices=[
            TransactionSubtype.PROMO_CREDIT,
            TransactionSubtype.COURTESY_CREDIT,
            TransactionSubtype.CORRECTION,
        ],
        default=TransactionSubtype.PROMO_CREDIT
    )
    description = serializers.CharField(max_length=500, required=False)
    reference_type = serializers.CharField(max_length=50, required=False)
    reference_id = serializers.UUIDField(required=False)
    metadata = serializers.JSONField(required=False, default=dict)


class CreateAdjustmentSerializer(serializers.Serializer):
    """Serializer for creating an adjustment transaction."""

    account_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    is_credit = serializers.BooleanField(required=True)
    description = serializers.CharField(max_length=500, required=True)
    reason = serializers.CharField(max_length=500, required=False)
    metadata = serializers.JSONField(required=False, default=dict)


class ReverseTransactionSerializer(serializers.Serializer):
    """Serializer for reversing a transaction."""

    reason = serializers.CharField(max_length=500, required=True)


class TransactionSummarySerializer(serializers.Serializer):
    """Serializer for transaction summary response."""

    period = serializers.DictField(child=serializers.CharField(allow_null=True))
    charges = serializers.DictField(child=serializers.FloatField())
    payments = serializers.DictField(child=serializers.FloatField())
    refunds = serializers.DictField(child=serializers.FloatField())
    credits = serializers.DictField(child=serializers.FloatField())
    net_revenue = serializers.FloatField()


class TransactionFilterSerializer(serializers.Serializer):
    """Serializer for transaction filtering parameters."""

    account_id = serializers.UUIDField(required=False)
    transaction_type = serializers.ChoiceField(
        choices=TransactionType.choices,
        required=False
    )
    status = serializers.ChoiceField(
        choices=TransactionStatus.choices,
        required=False
    )
    reference_type = serializers.CharField(max_length=50, required=False)
    reference_id = serializers.UUIDField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    min_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )
    max_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )
    order_by = serializers.CharField(default='-created_at')
    limit = serializers.IntegerField(default=50, max_value=100)
    offset = serializers.IntegerField(default=0)
