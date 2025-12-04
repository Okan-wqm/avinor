# services/finance-service/src/apps/core/models/transaction.py
"""
Transaction Model

Financial transaction tracking and management.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone


class TransactionType(models.TextChoices):
    """Transaction type choices."""
    CHARGE = 'charge', 'Charge'
    PAYMENT = 'payment', 'Payment'
    REFUND = 'refund', 'Refund'
    CREDIT = 'credit', 'Credit'
    ADJUSTMENT = 'adjustment', 'Adjustment'
    TRANSFER = 'transfer', 'Transfer'
    REVERSAL = 'reversal', 'Reversal'


class TransactionSubtype(models.TextChoices):
    """Transaction subtype choices."""
    # Charge subtypes
    FLIGHT_CHARGE = 'flight_charge', 'Flight Charge'
    AIRCRAFT_RENTAL = 'aircraft_rental', 'Aircraft Rental'
    INSTRUCTOR_FEE = 'instructor_fee', 'Instructor Fee'
    FUEL_CHARGE = 'fuel_charge', 'Fuel Charge'
    LANDING_FEE = 'landing_fee', 'Landing Fee'
    MEMBERSHIP_FEE = 'membership_fee', 'Membership Fee'
    CANCELLATION_FEE = 'cancellation_fee', 'Cancellation Fee'
    NO_SHOW_FEE = 'no_show_fee', 'No-Show Fee'
    LATE_FEE = 'late_fee', 'Late Fee'
    EQUIPMENT_RENTAL = 'equipment_rental', 'Equipment Rental'
    GROUND_INSTRUCTION = 'ground_instruction', 'Ground Instruction'
    EXAM_FEE = 'exam_fee', 'Exam Fee'
    MATERIAL_FEE = 'material_fee', 'Material Fee'
    OTHER_CHARGE = 'other_charge', 'Other Charge'

    # Payment subtypes
    CASH_PAYMENT = 'cash_payment', 'Cash Payment'
    CARD_PAYMENT = 'card_payment', 'Card Payment'
    BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
    CHECK_PAYMENT = 'check_payment', 'Check Payment'
    PACKAGE_CREDIT = 'package_credit', 'Package Credit'
    DEPOSIT = 'deposit', 'Deposit'

    # Other subtypes
    PROMO_CREDIT = 'promo_credit', 'Promotional Credit'
    COURTESY_CREDIT = 'courtesy_credit', 'Courtesy Credit'
    CORRECTION = 'correction', 'Correction'


class TransactionStatus(models.TextChoices):
    """Transaction status choices."""
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'
    REVERSED = 'reversed', 'Reversed'


class Transaction(models.Model):
    """
    Financial transaction model.

    Records all financial movements including charges,
    payments, refunds, and adjustments.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    account = models.ForeignKey(
        'Account',
        on_delete=models.PROTECT,
        related_name='transactions'
    )

    # Transaction Number
    transaction_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True
    )

    # Type
    transaction_type = models.CharField(
        max_length=50,
        choices=TransactionType.choices,
        db_index=True
    )
    transaction_subtype = models.CharField(
        max_length=50,
        choices=TransactionSubtype.choices,
        blank=True,
        null=True
    )

    # Amount
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Transaction amount (always positive)'
    )
    currency = models.CharField(
        max_length=3,
        default='USD'
    )

    # Balance Impact
    balance_before = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )
    balance_impact = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        help_text='Net impact on balance (positive = credit, negative = debit)'
    )

    # Reference
    reference_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
        help_text='flight, booking, invoice, package, membership'
    )
    reference_id = models.UUIDField(
        blank=True,
        null=True,
        db_index=True
    )
    external_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='External reference number'
    )

    # Description
    description = models.TextField(
        blank=True,
        null=True
    )
    line_items = models.JSONField(
        default=list,
        help_text='Detailed breakdown of charges'
    )

    # Payment Information
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='cash, credit_card, bank_transfer, account_credit, package'
    )
    payment_method_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Reference to stored payment method'
    )
    payment_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Check number, transfer reference, etc.'
    )

    # Gateway Information
    gateway_name = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='stripe, paypal, etc.'
    )
    gateway_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True
    )
    gateway_response = models.JSONField(
        default=dict,
        blank=True
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.COMPLETED,
        db_index=True
    )
    status_message = models.TextField(
        blank=True,
        null=True,
        help_text='Error message or status details'
    )

    # Reversal
    reversed = models.BooleanField(default=False)
    reversal_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='ID of the reversing transaction'
    )
    reversal_reason = models.TextField(
        blank=True,
        null=True
    )
    original_transaction_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Original transaction if this is a reversal'
    )

    # Invoice
    invoice_id = models.UUIDField(
        blank=True,
        null=True,
        db_index=True
    )

    # Tax
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )
    tax_breakdown = models.JSONField(
        default=list,
        help_text='Tax breakdown by type'
    )

    # Discount
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    discount_code = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    discount_description = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # User Info
    created_by = models.UUIDField(
        blank=True,
        null=True,
        help_text='User who created the transaction'
    )
    approved_by = models.UUIDField(
        blank=True,
        null=True,
        help_text='User who approved the transaction'
    )

    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True
    )
    user_agent = models.TextField(
        blank=True,
        null=True
    )

    # Timestamps
    transaction_date = models.DateTimeField(
        default=timezone.now,
        help_text='Effective date of transaction'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization_id', 'account_id', '-created_at']),
            models.Index(fields=['organization_id', 'transaction_type', '-created_at']),
            models.Index(fields=['reference_type', 'reference_id']),
            models.Index(fields=['transaction_date']),
        ]

    def __str__(self):
        return f"{self.transaction_number}: {self.transaction_type} {self.amount}"

    def save(self, *args, **kwargs):
        """Auto-generate transaction number if not set."""
        if not self.transaction_number:
            self.transaction_number = self.generate_transaction_number()
        super().save(*args, **kwargs)

    def generate_transaction_number(self) -> str:
        """Generate unique transaction number."""
        date_str = timezone.now().strftime('%Y%m%d')
        count = Transaction.objects.filter(
            organization_id=self.organization_id,
            created_at__date=timezone.now().date()
        ).count() + 1
        return f"TXN-{date_str}-{count:06d}"

    @property
    def is_debit(self) -> bool:
        """Check if transaction is a debit (reduces balance)."""
        return self.transaction_type in [
            TransactionType.CHARGE,
        ]

    @property
    def is_credit(self) -> bool:
        """Check if transaction is a credit (increases balance)."""
        return self.transaction_type in [
            TransactionType.PAYMENT,
            TransactionType.REFUND,
            TransactionType.CREDIT,
        ]

    @property
    def net_amount(self) -> Decimal:
        """Get net amount including tax and discount."""
        return self.amount + self.tax_amount - self.discount_amount

    @property
    def is_reversible(self) -> bool:
        """Check if transaction can be reversed."""
        return (
            self.status == TransactionStatus.COMPLETED and
            not self.reversed
        )

    def get_line_items_summary(self) -> list:
        """Get formatted line items summary."""
        return self.line_items if self.line_items else []

    def add_line_item(
        self,
        description: str,
        amount: Decimal,
        quantity: float = 1,
        unit_price: Decimal = None,
        item_type: str = None,
        reference_id: str = None
    ) -> None:
        """Add a line item to the transaction."""
        item = {
            'description': description,
            'amount': float(amount),
            'quantity': quantity,
            'unit_price': float(unit_price) if unit_price else float(amount),
            'type': item_type,
            'reference_id': str(reference_id) if reference_id else None,
        }
        if not self.line_items:
            self.line_items = []
        self.line_items.append(item)
