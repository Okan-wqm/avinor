# services/finance-service/src/apps/core/models/invoice.py
"""
Invoice Model

Invoice management for billing and accounting.
"""

import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.db import models
from django.utils import timezone


class InvoiceType(models.TextChoices):
    """Invoice type choices."""
    STANDARD = 'standard', 'Standard Invoice'
    CREDIT_NOTE = 'credit_note', 'Credit Note'
    PROFORMA = 'proforma', 'Proforma Invoice'
    RECURRING = 'recurring', 'Recurring Invoice'
    DEPOSIT = 'deposit', 'Deposit Invoice'


class InvoiceStatus(models.TextChoices):
    """Invoice status choices."""
    DRAFT = 'draft', 'Draft'
    PENDING = 'pending', 'Pending'
    SENT = 'sent', 'Sent'
    VIEWED = 'viewed', 'Viewed'
    PAID = 'paid', 'Paid'
    PARTIAL = 'partial', 'Partially Paid'
    OVERDUE = 'overdue', 'Overdue'
    CANCELLED = 'cancelled', 'Cancelled'
    VOID = 'void', 'Void'
    DISPUTED = 'disputed', 'Disputed'


class Invoice(models.Model):
    """
    Invoice model for billing.

    Supports multiple invoice types, automatic numbering,
    and payment tracking.
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
        related_name='invoices'
    )

    # Invoice Number
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='External reference number'
    )

    # Type
    invoice_type = models.CharField(
        max_length=20,
        choices=InvoiceType.choices,
        default=InvoiceType.STANDARD
    )

    # Customer Information
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField(blank=True, null=True)
    customer_phone = models.CharField(max_length=50, blank=True, null=True)
    customer_address = models.TextField(blank=True, null=True)
    customer_tax_id = models.CharField(max_length=100, blank=True, null=True)

    # Billing Address
    billing_address_line1 = models.CharField(max_length=255, blank=True, null=True)
    billing_address_line2 = models.CharField(max_length=255, blank=True, null=True)
    billing_city = models.CharField(max_length=100, blank=True, null=True)
    billing_state = models.CharField(max_length=100, blank=True, null=True)
    billing_postal_code = models.CharField(max_length=20, blank=True, null=True)
    billing_country = models.CharField(max_length=2, default='US')

    # Dates
    invoice_date = models.DateField()
    due_date = models.DateField()
    paid_date = models.DateField(blank=True, null=True)
    period_start = models.DateField(blank=True, null=True, help_text='Billing period start')
    period_end = models.DateField(blank=True, null=True, help_text='Billing period end')

    # Amounts
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    shipping_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Currency
    currency = models.CharField(max_length=3, default='USD')
    exchange_rate = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=Decimal('1.000000')
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        db_index=True
    )

    # Line Items (stored as JSON)
    line_items = models.JSONField(
        default=list,
        help_text='Invoice line items'
    )

    # Tax Details
    tax_details = models.JSONField(
        default=list,
        help_text='Tax breakdown by type'
    )

    # Discount
    discount_code = models.CharField(max_length=50, blank=True, null=True)
    discount_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='percentage or fixed'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    # Notes
    notes = models.TextField(blank=True, null=True, help_text='Notes visible to customer')
    internal_notes = models.TextField(blank=True, null=True, help_text='Internal notes')
    terms = models.TextField(blank=True, null=True, help_text='Payment terms')
    footer = models.TextField(blank=True, null=True)

    # PDF
    pdf_url = models.URLField(max_length=500, blank=True, null=True)
    pdf_generated_at = models.DateTimeField(blank=True, null=True)

    # Delivery
    sent_at = models.DateTimeField(blank=True, null=True)
    sent_to = models.EmailField(blank=True, null=True)
    sent_cc = models.TextField(blank=True, null=True, help_text='CC email addresses')
    viewed_at = models.DateTimeField(blank=True, null=True)
    view_count = models.IntegerField(default=0)

    # Reminders
    reminder_count = models.IntegerField(default=0)
    last_reminder_at = models.DateTimeField(blank=True, null=True)
    next_reminder_at = models.DateTimeField(blank=True, null=True)
    auto_remind = models.BooleanField(default=True)

    # Payment
    payment_link = models.URLField(max_length=500, blank=True, null=True)
    payment_instructions = models.TextField(blank=True, null=True)
    accepted_payment_methods = models.JSONField(
        default=list,
        help_text='Accepted payment methods for this invoice'
    )

    # Related
    related_invoice_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Related invoice (for credit notes)'
    )
    recurring_invoice_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Parent recurring invoice template'
    )

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_by = models.UUIDField(blank=True, null=True)
    updated_by = models.UUIDField(blank=True, null=True)
    voided_by = models.UUIDField(blank=True, null=True)
    voided_at = models.DateTimeField(blank=True, null=True)
    void_reason = models.TextField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'invoices'
        ordering = ['-invoice_date', '-created_at']
        indexes = [
            models.Index(fields=['organization_id', 'account_id', '-invoice_date']),
            models.Index(fields=['organization_id', 'status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"{self.invoice_number}: {self.total_amount} {self.currency}"

    def save(self, *args, **kwargs):
        """Auto-generate invoice number and calculate totals."""
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        self.calculate_totals()
        super().save(*args, **kwargs)

    def generate_invoice_number(self) -> str:
        """Generate unique invoice number."""
        year = date.today().year
        count = Invoice.objects.filter(
            organization_id=self.organization_id,
            invoice_date__year=year
        ).count() + 1

        prefix = 'INV'
        if self.invoice_type == InvoiceType.CREDIT_NOTE:
            prefix = 'CN'
        elif self.invoice_type == InvoiceType.PROFORMA:
            prefix = 'PRO'

        return f"{prefix}-{year}-{count:06d}"

    @property
    def amount_due(self) -> Decimal:
        """Calculate remaining amount due."""
        return max(Decimal('0'), self.total_amount - self.amount_paid)

    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        return (
            self.status not in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.VOID] and
            self.due_date < date.today()
        )

    @property
    def days_overdue(self) -> int:
        """Calculate days overdue."""
        if not self.is_overdue:
            return 0
        return (date.today() - self.due_date).days

    @property
    def days_until_due(self) -> int:
        """Calculate days until due."""
        if self.due_date >= date.today():
            return (self.due_date - date.today()).days
        return 0

    @property
    def payment_status_display(self) -> str:
        """Get human-readable payment status."""
        if self.status == InvoiceStatus.PAID:
            return 'Paid in Full'
        elif self.status == InvoiceStatus.PARTIAL:
            percent = (self.amount_paid / self.total_amount * 100) if self.total_amount > 0 else 0
            return f'Partially Paid ({percent:.0f}%)'
        elif self.is_overdue:
            return f'Overdue by {self.days_overdue} days'
        else:
            return self.get_status_display()

    def calculate_totals(self) -> None:
        """Calculate subtotal, tax, and total from line items."""
        subtotal = Decimal('0')
        tax_total = Decimal('0')

        for item in self.line_items or []:
            amount = Decimal(str(item.get('amount', 0)))
            subtotal += amount

            item_tax = Decimal(str(item.get('tax_amount', 0)))
            tax_total += item_tax

        self.subtotal = subtotal
        self.tax_amount = tax_total
        self.total_amount = subtotal + tax_total - self.discount_amount + self.shipping_amount

    def add_line_item(
        self,
        description: str,
        quantity: float,
        unit_price: Decimal,
        unit: str = 'item',
        tax_rate: Decimal = None,
        reference_type: str = None,
        reference_id: str = None
    ) -> None:
        """Add a line item to the invoice."""
        amount = Decimal(str(quantity)) * unit_price
        tax_amount = amount * (tax_rate / 100) if tax_rate else Decimal('0')

        item = {
            'description': description,
            'quantity': quantity,
            'unit': unit,
            'unit_price': float(unit_price),
            'amount': float(amount),
            'tax_rate': float(tax_rate) if tax_rate else None,
            'tax_amount': float(tax_amount),
            'reference_type': reference_type,
            'reference_id': str(reference_id) if reference_id else None,
        }

        if not self.line_items:
            self.line_items = []
        self.line_items.append(item)

    def record_payment(self, amount: Decimal, paid_date: date = None) -> None:
        """Record a payment against this invoice."""
        self.amount_paid += amount
        if self.amount_paid >= self.total_amount:
            self.status = InvoiceStatus.PAID
            self.paid_date = paid_date or date.today()
        elif self.amount_paid > Decimal('0'):
            self.status = InvoiceStatus.PARTIAL

    def mark_sent(self, email: str = None) -> None:
        """Mark invoice as sent."""
        self.status = InvoiceStatus.SENT
        self.sent_at = timezone.now()
        if email:
            self.sent_to = email

    def mark_viewed(self) -> None:
        """Mark invoice as viewed."""
        if self.status == InvoiceStatus.SENT:
            self.status = InvoiceStatus.VIEWED
        self.viewed_at = timezone.now()
        self.view_count += 1

    def void(self, reason: str, voided_by: uuid.UUID = None) -> None:
        """Void the invoice."""
        self.status = InvoiceStatus.VOID
        self.void_reason = reason
        self.voided_by = voided_by
        self.voided_at = timezone.now()


class InvoiceItem(models.Model):
    """
    Invoice line item model (optional, for more complex scenarios).

    Can be used instead of JSON storage for line items.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items'
    )

    # Item Details
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit = models.CharField(max_length=20, default='item')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Tax
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Discount
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Reference
    reference_type = models.CharField(max_length=50, blank=True, null=True)
    reference_id = models.UUIDField(blank=True, null=True)

    # Order
    sort_order = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'invoice_items'
        ordering = ['sort_order', 'created_at']

    def __str__(self):
        return f"{self.description}: {self.amount}"

    def save(self, *args, **kwargs):
        """Calculate amount if not set."""
        if not self.amount:
            self.amount = self.quantity * self.unit_price
        if self.tax_rate and not self.tax_amount:
            self.tax_amount = self.amount * (self.tax_rate / 100)
        super().save(*args, **kwargs)
