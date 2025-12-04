# services/finance-service/src/apps/core/api/serializers/account_serializers.py
"""
Account Serializers

DRF serializers for account management.
"""

from decimal import Decimal
from rest_framework import serializers

from ...models.account import Account, AccountType, AccountStatus


class AccountSerializer(serializers.ModelSerializer):
    """Base account serializer."""

    available_balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    outstanding_balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    is_low_balance = serializers.BooleanField(read_only=True)
    is_overdrawn = serializers.BooleanField(read_only=True)

    class Meta:
        model = Account
        fields = [
            'id',
            'organization_id',
            'account_number',
            'owner_id',
            'owner_type',
            'account_type',
            'status',
            'balance',
            'credit_limit',
            'available_balance',
            'pending_charges',
            'outstanding_balance',
            'is_low_balance',
            'is_overdrawn',
            'currency',
            'auto_pay_enabled',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'organization_id',
            'account_number',
            'balance',
            'pending_charges',
            'created_at',
            'updated_at',
        ]


class AccountListSerializer(serializers.ModelSerializer):
    """Serializer for account list views."""

    available_balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    is_overdrawn = serializers.BooleanField(read_only=True)

    class Meta:
        model = Account
        fields = [
            'id',
            'account_number',
            'owner_id',
            'owner_type',
            'account_type',
            'status',
            'balance',
            'credit_limit',
            'available_balance',
            'is_overdrawn',
            'currency',
            'last_transaction_at',
            'created_at',
        ]


class AccountDetailSerializer(serializers.ModelSerializer):
    """Detailed account serializer."""

    available_balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    outstanding_balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    is_low_balance = serializers.BooleanField(read_only=True)
    is_overdrawn = serializers.BooleanField(read_only=True)

    class Meta:
        model = Account
        fields = [
            'id',
            'organization_id',
            'account_number',
            'owner_id',
            'owner_type',
            'account_type',
            'status',
            'status_reason',
            'balance',
            'credit_limit',
            'available_balance',
            'pending_charges',
            'outstanding_balance',
            'is_low_balance',
            'is_overdrawn',
            'low_balance_threshold',
            'total_charged',
            'total_paid',
            'total_refunded',
            'currency',
            'billing_name',
            'billing_email',
            'billing_phone',
            'billing_address_line1',
            'billing_address_line2',
            'billing_city',
            'billing_state',
            'billing_postal_code',
            'billing_country',
            'auto_pay_enabled',
            'default_payment_method_id',
            'invoice_email',
            'invoice_cc',
            'payment_terms_days',
            'last_transaction_at',
            'last_payment_at',
            'created_at',
            'updated_at',
            'closed_at',
            'metadata',
        ]
        read_only_fields = [
            'id',
            'organization_id',
            'account_number',
            'balance',
            'pending_charges',
            'total_charged',
            'total_paid',
            'total_refunded',
            'last_transaction_at',
            'last_payment_at',
            'created_at',
            'updated_at',
            'closed_at',
        ]


class AccountCreateSerializer(serializers.Serializer):
    """Serializer for account creation."""

    owner_id = serializers.UUIDField(required=True)
    owner_type = serializers.ChoiceField(
        choices=['user', 'organization'],
        default='user'
    )
    account_type = serializers.ChoiceField(
        choices=AccountType.choices,
        default=AccountType.STUDENT
    )
    currency = serializers.CharField(max_length=3, default='USD')
    credit_limit = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        min_value=Decimal('0')
    )
    billing_name = serializers.CharField(max_length=255, required=False)
    billing_email = serializers.EmailField(required=False)
    billing_phone = serializers.CharField(max_length=50, required=False)
    billing_address_line1 = serializers.CharField(max_length=255, required=False)
    billing_address_line2 = serializers.CharField(max_length=255, required=False)
    billing_city = serializers.CharField(max_length=100, required=False)
    billing_state = serializers.CharField(max_length=100, required=False)
    billing_postal_code = serializers.CharField(max_length=20, required=False)
    billing_country = serializers.CharField(max_length=2, default='US')
    auto_pay_enabled = serializers.BooleanField(default=False)
    payment_terms_days = serializers.IntegerField(default=30)
    metadata = serializers.JSONField(required=False, default=dict)


class AccountUpdateSerializer(serializers.Serializer):
    """Serializer for account updates."""

    account_type = serializers.ChoiceField(
        choices=AccountType.choices,
        required=False
    )
    credit_limit = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        min_value=Decimal('0')
    )
    low_balance_threshold = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False
    )
    billing_name = serializers.CharField(max_length=255, required=False)
    billing_email = serializers.EmailField(required=False, allow_null=True)
    billing_phone = serializers.CharField(max_length=50, required=False, allow_null=True)
    billing_address_line1 = serializers.CharField(max_length=255, required=False, allow_null=True)
    billing_address_line2 = serializers.CharField(max_length=255, required=False, allow_null=True)
    billing_city = serializers.CharField(max_length=100, required=False, allow_null=True)
    billing_state = serializers.CharField(max_length=100, required=False, allow_null=True)
    billing_postal_code = serializers.CharField(max_length=20, required=False, allow_null=True)
    billing_country = serializers.CharField(max_length=2, required=False)
    auto_pay_enabled = serializers.BooleanField(required=False)
    default_payment_method_id = serializers.UUIDField(required=False, allow_null=True)
    invoice_email = serializers.EmailField(required=False, allow_null=True)
    invoice_cc = serializers.CharField(required=False, allow_null=True)
    payment_terms_days = serializers.IntegerField(required=False)
    metadata = serializers.JSONField(required=False)


class AccountSummarySerializer(serializers.Serializer):
    """Serializer for account summary response."""

    account_id = serializers.UUIDField()
    account_number = serializers.CharField()
    owner_id = serializers.UUIDField()
    owner_type = serializers.CharField()
    account_type = serializers.CharField()
    status = serializers.CharField()
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    credit_limit = serializers.DecimalField(max_digits=12, decimal_places=2)
    available_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_charges = serializers.DecimalField(max_digits=12, decimal_places=2)
    outstanding_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    is_low_balance = serializers.BooleanField()
    is_overdrawn = serializers.BooleanField()
    total_charged = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_refunded = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    auto_pay_enabled = serializers.BooleanField()
    last_transaction_at = serializers.DateTimeField(allow_null=True)
    last_payment_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()


class ChargeAccountSerializer(serializers.Serializer):
    """Serializer for charging an account."""

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    description = serializers.CharField(max_length=500, required=False)
    reference_type = serializers.CharField(max_length=50, required=False)
    reference_id = serializers.UUIDField(required=False)
    allow_credit = serializers.BooleanField(default=True)


class CreditAccountSerializer(serializers.Serializer):
    """Serializer for crediting an account."""

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    description = serializers.CharField(max_length=500, required=False)
    reference_type = serializers.CharField(max_length=50, required=False)
    reference_id = serializers.UUIDField(required=False)


class TransferBalanceSerializer(serializers.Serializer):
    """Serializer for balance transfer."""

    to_account_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    description = serializers.CharField(max_length=500, required=False)


class SuspendAccountSerializer(serializers.Serializer):
    """Serializer for suspending an account."""

    reason = serializers.CharField(max_length=500, required=True)


class CloseAccountSerializer(serializers.Serializer):
    """Serializer for closing an account."""

    reason = serializers.CharField(max_length=500, required=False)


class UpdateCreditLimitSerializer(serializers.Serializer):
    """Serializer for updating credit limit."""

    credit_limit = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0')
    )
    reason = serializers.CharField(max_length=500, required=False)
