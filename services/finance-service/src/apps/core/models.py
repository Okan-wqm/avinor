"""
Finance Service Models.
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from shared.common.mixins import UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class Account(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Financial accounts for organizations and individuals.
    """
    class AccountType(models.TextChoices):
        ORGANIZATION = 'organization', 'Organization Account'
        STUDENT = 'student', 'Student Account'
        INSTRUCTOR = 'instructor', 'Instructor Account'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'
        CLOSED = 'closed', 'Closed'

    organization_id = models.UUIDField()
    account_holder_id = models.UUIDField()  # User ID
    account_type = models.CharField(max_length=20, choices=AccountType.choices)

    # Account details
    account_number = models.CharField(max_length=50, unique=True)
    account_name = models.CharField(max_length=255)

    # Balance
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    # Billing
    billing_email = models.EmailField()
    billing_address = models.JSONField(default=dict, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'accounts'
        ordering = ['account_number']
        indexes = [
            models.Index(fields=['account_number']),
            models.Index(fields=['account_holder_id']),
            models.Index(fields=['organization_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.account_number} - {self.account_name}"


class Invoice(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Invoices for services and training.
    """
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SENT = 'sent', 'Sent'
        PAID = 'paid', 'Paid'
        PARTIAL = 'partial', 'Partially Paid'
        OVERDUE = 'overdue', 'Overdue'
        CANCELLED = 'cancelled', 'Cancelled'

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='invoices'
    )
    organization_id = models.UUIDField()

    # Invoice details
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField()
    due_date = models.DateField()

    # Billing
    bill_to = models.JSONField(default=dict)  # Name, address, etc.

    # Amounts
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Line items
    line_items = models.JSONField(default=list)  # [{description, quantity, rate, amount}]

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    # Payment info
    payment_terms = models.CharField(max_length=100, blank=True)
    payment_instructions = models.TextField(blank=True)

    # Notes
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    # References
    booking_ids = models.JSONField(default=list, blank=True)
    flight_ids = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'invoices'
        ordering = ['-invoice_date']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['account']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.total_amount}"


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Payment records.
    """
    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Cash'
        CHECK = 'check', 'Check'
        CREDIT_CARD = 'credit_card', 'Credit Card'
        DEBIT_CARD = 'debit_card', 'Debit Card'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        ONLINE = 'online', 'Online Payment'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='payments',
        null=True,
        blank=True
    )

    # Payment details
    payment_number = models.CharField(max_length=50, unique=True)
    payment_date = models.DateTimeField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])

    # Method
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    transaction_reference = models.CharField(max_length=255, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # Processor info (for online payments)
    processor = models.CharField(max_length=50, blank=True)  # Stripe, PayPal, etc.
    processor_transaction_id = models.CharField(max_length=255, blank=True)
    processor_fee = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Notes
    notes = models.TextField(blank=True)
    receipt_url = models.URLField(blank=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['payment_number']),
            models.Index(fields=['account']),
            models.Index(fields=['invoice']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.payment_number} - {self.amount}"


class Transaction(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Financial transactions (ledger entries).
    """
    class TransactionType(models.TextChoices):
        CHARGE = 'charge', 'Charge'
        PAYMENT = 'payment', 'Payment'
        REFUND = 'refund', 'Refund'
        ADJUSTMENT = 'adjustment', 'Adjustment'
        CREDIT = 'credit', 'Credit'
        DEBIT = 'debit', 'Debit'

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='transactions'
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        related_name='transactions',
        null=True,
        blank=True
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        related_name='transactions',
        null=True,
        blank=True
    )

    # Transaction details
    transaction_number = models.CharField(max_length=50, unique=True)
    transaction_date = models.DateTimeField()
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)

    # Amounts
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)

    # Description
    description = models.CharField(max_length=255)
    notes = models.TextField(blank=True)

    # References
    reference_type = models.CharField(max_length=50, blank=True)  # booking, flight, etc.
    reference_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'transactions'
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['transaction_number']),
            models.Index(fields=['account']),
            models.Index(fields=['transaction_date']),
        ]

    def __str__(self):
        return f"{self.transaction_number} - {self.amount}"


class PriceList(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Pricing for various services.
    """
    class ItemType(models.TextChoices):
        AIRCRAFT_RENTAL = 'aircraft_rental', 'Aircraft Rental'
        INSTRUCTOR = 'instructor', 'Flight Instructor'
        GROUND_INSTRUCTION = 'ground_instruction', 'Ground Instruction'
        SIMULATOR = 'simulator', 'Simulator Time'
        EXAM_FEE = 'exam_fee', 'Exam Fee'
        COURSE = 'course', 'Course Fee'
        LANDING_FEE = 'landing_fee', 'Landing Fee'
        FUEL = 'fuel', 'Fuel'
        OTHER = 'other', 'Other'

    organization_id = models.UUIDField()

    # Item details
    item_code = models.CharField(max_length=50)
    item_name = models.CharField(max_length=255)
    item_type = models.CharField(max_length=30, choices=ItemType.choices)
    description = models.TextField(blank=True)

    # Pricing
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50, default='hour')  # hour, session, each, etc.

    # Discounts
    student_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    member_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    # Tax
    taxable = models.BooleanField(default=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    # Status
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)

    # Reference
    reference_id = models.UUIDField(null=True, blank=True)  # Aircraft ID, Course ID, etc.

    class Meta:
        db_table = 'price_lists'
        ordering = ['item_code']
        unique_together = ['organization_id', 'item_code', 'effective_date']
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['item_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.item_code} - {self.item_name} ({self.unit_price}/{self.unit})"
