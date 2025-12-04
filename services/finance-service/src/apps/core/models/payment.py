# services/finance-service/src/apps/core/models/payment.py
"""
Payment Models

Payment methods and gateway integration.
"""

import uuid
from datetime import date
from django.db import models
from django.utils import timezone


class PaymentMethodType(models.TextChoices):
    """Payment method type choices."""
    CREDIT_CARD = 'credit_card', 'Credit Card'
    DEBIT_CARD = 'debit_card', 'Debit Card'
    BANK_ACCOUNT = 'bank_account', 'Bank Account'
    PAYPAL = 'paypal', 'PayPal'
    APPLE_PAY = 'apple_pay', 'Apple Pay'
    GOOGLE_PAY = 'google_pay', 'Google Pay'
    ACH = 'ach', 'ACH Transfer'
    WIRE = 'wire', 'Wire Transfer'


class PaymentMethodStatus(models.TextChoices):
    """Payment method status choices."""
    ACTIVE = 'active', 'Active'
    EXPIRED = 'expired', 'Expired'
    INVALID = 'invalid', 'Invalid'
    PENDING_VERIFICATION = 'pending_verification', 'Pending Verification'
    SUSPENDED = 'suspended', 'Suspended'


class PaymentMethod(models.Model):
    """
    Stored payment method model.

    Stores tokenized payment methods for recurring charges.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    account = models.ForeignKey(
        'Account',
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )

    # Type
    method_type = models.CharField(
        max_length=50,
        choices=PaymentMethodType.choices
    )

    # Card Details (for credit/debit cards)
    card_brand = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='visa, mastercard, amex, discover'
    )
    card_last_four = models.CharField(
        max_length=4,
        blank=True,
        null=True
    )
    card_exp_month = models.IntegerField(blank=True, null=True)
    card_exp_year = models.IntegerField(blank=True, null=True)
    card_holder_name = models.CharField(max_length=255, blank=True, null=True)
    card_funding = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='credit, debit, prepaid'
    )

    # Bank Account Details (for ACH)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    bank_account_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='checking, savings'
    )
    bank_last_four = models.CharField(
        max_length=4,
        blank=True,
        null=True
    )
    bank_routing_last_four = models.CharField(
        max_length=4,
        blank=True,
        null=True
    )

    # Gateway Information
    gateway_name = models.CharField(
        max_length=50,
        default='stripe',
        help_text='stripe, paypal, etc.'
    )
    gateway_customer_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True
    )
    gateway_payment_method_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True
    )

    # Billing Address
    billing_name = models.CharField(max_length=255, blank=True, null=True)
    billing_email = models.EmailField(blank=True, null=True)
    billing_phone = models.CharField(max_length=50, blank=True, null=True)
    billing_address_line1 = models.CharField(max_length=255, blank=True, null=True)
    billing_address_line2 = models.CharField(max_length=255, blank=True, null=True)
    billing_city = models.CharField(max_length=100, blank=True, null=True)
    billing_state = models.CharField(max_length=100, blank=True, null=True)
    billing_postal_code = models.CharField(max_length=20, blank=True, null=True)
    billing_country = models.CharField(max_length=2, default='US')

    # Status
    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    status = models.CharField(
        max_length=30,
        choices=PaymentMethodStatus.choices,
        default=PaymentMethodStatus.ACTIVE,
        db_index=True
    )
    status_reason = models.TextField(blank=True, null=True)

    # Verification
    verification_method = models.CharField(max_length=50, blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    verification_attempts = models.IntegerField(default=0)
    last_verification_attempt = models.DateTimeField(blank=True, null=True)

    # Display
    nickname = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='User-friendly name for the payment method'
    )

    # Usage Stats
    total_charges = models.IntegerField(default=0)
    total_amount_charged = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    last_charge_at = models.DateTimeField(blank=True, null=True)
    last_charge_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    failure_count = models.IntegerField(default=0)
    last_failure_at = models.DateTimeField(blank=True, null=True)
    last_failure_reason = models.TextField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    fingerprint = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Card fingerprint for duplicate detection'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_methods'
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['organization_id', 'account_id', 'status']),
            models.Index(fields=['gateway_customer_id']),
        ]

    def __str__(self):
        if self.method_type in [PaymentMethodType.CREDIT_CARD, PaymentMethodType.DEBIT_CARD]:
            return f"{self.card_brand} •••• {self.card_last_four}"
        elif self.method_type == PaymentMethodType.BANK_ACCOUNT:
            return f"{self.bank_name} •••• {self.bank_last_four}"
        return f"{self.get_method_type_display()}"

    @property
    def display_name(self) -> str:
        """Get display name for the payment method."""
        if self.nickname:
            return self.nickname
        return str(self)

    @property
    def is_card(self) -> bool:
        """Check if payment method is a card."""
        return self.method_type in [
            PaymentMethodType.CREDIT_CARD,
            PaymentMethodType.DEBIT_CARD
        ]

    @property
    def is_expired(self) -> bool:
        """Check if card is expired."""
        if not self.is_card or not self.card_exp_year or not self.card_exp_month:
            return False
        today = date.today()
        exp_date = date(self.card_exp_year, self.card_exp_month, 1)
        return exp_date < today

    @property
    def is_expiring_soon(self) -> bool:
        """Check if card expires within 30 days."""
        if not self.is_card or not self.card_exp_year or not self.card_exp_month:
            return False
        today = date.today()
        exp_date = date(self.card_exp_year, self.card_exp_month, 1)
        days_until_expiry = (exp_date - today).days
        return 0 < days_until_expiry <= 30

    @property
    def expiry_display(self) -> str:
        """Get expiry date display."""
        if self.card_exp_month and self.card_exp_year:
            return f"{self.card_exp_month:02d}/{self.card_exp_year % 100:02d}"
        return None

    def set_as_default(self) -> None:
        """Set this payment method as default."""
        # Remove default from other methods
        PaymentMethod.objects.filter(
            account=self.account,
            is_default=True
        ).exclude(id=self.id).update(is_default=False)

        self.is_default = True
        self.save(update_fields=['is_default', 'updated_at'])

    def record_charge(self, amount, success: bool, failure_reason: str = None) -> None:
        """Record a charge attempt."""
        if success:
            self.total_charges += 1
            self.total_amount_charged += amount
            self.last_charge_at = timezone.now()
            self.last_charge_amount = amount
        else:
            self.failure_count += 1
            self.last_failure_at = timezone.now()
            self.last_failure_reason = failure_reason

    def mark_expired(self) -> None:
        """Mark payment method as expired."""
        self.status = PaymentMethodStatus.EXPIRED
        self.status_reason = 'Card expired'

    def mark_invalid(self, reason: str) -> None:
        """Mark payment method as invalid."""
        self.status = PaymentMethodStatus.INVALID
        self.status_reason = reason


class PaymentGatewayLog(models.Model):
    """
    Payment gateway log model.

    Records all interactions with payment gateways.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # Gateway
    gateway_name = models.CharField(max_length=50)
    gateway_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True
    )

    # Operation
    operation = models.CharField(
        max_length=50,
        help_text='charge, refund, verify, etc.'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )
    currency = models.CharField(max_length=3, blank=True, null=True)

    # References
    account_id = models.UUIDField(blank=True, null=True, db_index=True)
    payment_method_id = models.UUIDField(blank=True, null=True)
    transaction_id = models.UUIDField(blank=True, null=True, db_index=True)
    invoice_id = models.UUIDField(blank=True, null=True)

    # Request
    request_data = models.JSONField(default=dict, blank=True)
    request_headers = models.JSONField(default=dict, blank=True)

    # Response
    response_code = models.CharField(max_length=50, blank=True, null=True)
    response_message = models.TextField(blank=True, null=True)
    response_data = models.JSONField(default=dict, blank=True)
    http_status_code = models.IntegerField(blank=True, null=True)

    # Result
    success = models.BooleanField(default=False)
    error_code = models.CharField(max_length=100, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    error_type = models.CharField(max_length=100, blank=True, null=True)

    # Timing
    request_at = models.DateTimeField(default=timezone.now)
    response_at = models.DateTimeField(blank=True, null=True)
    duration_ms = models.IntegerField(blank=True, null=True)

    # Metadata
    idempotency_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payment_gateway_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization_id', '-created_at']),
            models.Index(fields=['gateway_name', 'operation', '-created_at']),
        ]

    def __str__(self):
        return f"{self.gateway_name} {self.operation}: {self.gateway_transaction_id}"

    def save(self, *args, **kwargs):
        """Calculate duration if response_at is set."""
        if self.response_at and self.request_at:
            delta = self.response_at - self.request_at
            self.duration_ms = int(delta.total_seconds() * 1000)
        super().save(*args, **kwargs)
