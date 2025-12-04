# services/finance-service/src/apps/core/api/serializers/invoice_serializers.py
"""
Invoice Serializers

DRF serializers for invoice management.
"""

from decimal import Decimal
from rest_framework import serializers

from ...models.invoice import Invoice, InvoiceItem, InvoiceType, InvoiceStatus


class InvoiceLineItemSerializer(serializers.Serializer):
    """Serializer for invoice line items."""

    description = serializers.CharField(max_length=500)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit = serializers.CharField(max_length=20, default='item')
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )
    tax_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    tax_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    reference_type = serializers.CharField(max_length=50, required=False)
    reference_id = serializers.CharField(required=False)


class InvoiceSerializer(serializers.ModelSerializer):
    """Base invoice serializer."""

    amount_due = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    is_overdue = serializers.BooleanField(read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)
    payment_status_display = serializers.CharField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id',
            'organization_id',
            'account',
            'invoice_number',
            'invoice_type',
            'customer_name',
            'customer_email',
            'invoice_date',
            'due_date',
            'subtotal',
            'tax_amount',
            'discount_amount',
            'total_amount',
            'amount_paid',
            'amount_due',
            'currency',
            'status',
            'is_overdue',
            'days_overdue',
            'payment_status_display',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'organization_id',
            'invoice_number',
            'subtotal',
            'total_amount',
            'created_at',
        ]


class InvoiceListSerializer(serializers.ModelSerializer):
    """Serializer for invoice list views."""

    amount_due = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    is_overdue = serializers.BooleanField(read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)
    account_number = serializers.CharField(source='account.account_number', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id',
            'invoice_number',
            'invoice_type',
            'account',
            'account_number',
            'customer_name',
            'customer_email',
            'invoice_date',
            'due_date',
            'total_amount',
            'amount_paid',
            'amount_due',
            'currency',
            'status',
            'is_overdue',
            'days_overdue',
            'sent_at',
            'created_at',
        ]


class InvoiceDetailSerializer(serializers.ModelSerializer):
    """Detailed invoice serializer."""

    amount_due = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    is_overdue = serializers.BooleanField(read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)
    days_until_due = serializers.IntegerField(read_only=True)
    payment_status_display = serializers.CharField(read_only=True)
    account_number = serializers.CharField(source='account.account_number', read_only=True)
    line_items = InvoiceLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id',
            'organization_id',
            'account',
            'account_number',
            'invoice_number',
            'reference_number',
            'invoice_type',
            'customer_name',
            'customer_email',
            'customer_phone',
            'customer_address',
            'customer_tax_id',
            'billing_address_line1',
            'billing_address_line2',
            'billing_city',
            'billing_state',
            'billing_postal_code',
            'billing_country',
            'invoice_date',
            'due_date',
            'paid_date',
            'period_start',
            'period_end',
            'subtotal',
            'tax_amount',
            'discount_amount',
            'shipping_amount',
            'total_amount',
            'amount_paid',
            'amount_due',
            'currency',
            'exchange_rate',
            'status',
            'is_overdue',
            'days_overdue',
            'days_until_due',
            'payment_status_display',
            'line_items',
            'tax_details',
            'discount_code',
            'discount_type',
            'discount_value',
            'notes',
            'terms',
            'footer',
            'pdf_url',
            'pdf_generated_at',
            'sent_at',
            'sent_to',
            'viewed_at',
            'view_count',
            'reminder_count',
            'last_reminder_at',
            'payment_link',
            'payment_instructions',
            'accepted_payment_methods',
            'related_invoice_id',
            'metadata',
            'created_by',
            'voided_at',
            'void_reason',
            'created_at',
            'updated_at',
        ]


class InvoiceCreateSerializer(serializers.Serializer):
    """Serializer for invoice creation."""

    account_id = serializers.UUIDField(required=True)
    invoice_type = serializers.ChoiceField(
        choices=InvoiceType.choices,
        default=InvoiceType.STANDARD
    )
    line_items = InvoiceLineItemSerializer(many=True, required=True)
    invoice_date = serializers.DateField(required=False)
    due_date = serializers.DateField(required=False)
    payment_terms_days = serializers.IntegerField(default=30)
    period_start = serializers.DateField(required=False)
    period_end = serializers.DateField(required=False)
    discount_type = serializers.ChoiceField(
        choices=['percentage', 'fixed'],
        required=False
    )
    discount_value = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    discount_code = serializers.CharField(max_length=50, required=False)
    tax_details = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    notes = serializers.CharField(required=False)
    terms = serializers.CharField(required=False)
    footer = serializers.CharField(required=False)
    reference_number = serializers.CharField(max_length=100, required=False)
    metadata = serializers.JSONField(required=False, default=dict)


class InvoiceFromTransactionsSerializer(serializers.Serializer):
    """Serializer for creating invoice from transactions."""

    account_id = serializers.UUIDField(required=True)
    transaction_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        min_length=1
    )
    invoice_type = serializers.ChoiceField(
        choices=InvoiceType.choices,
        default=InvoiceType.STANDARD
    )
    due_date = serializers.DateField(required=False)
    notes = serializers.CharField(required=False)
    metadata = serializers.JSONField(required=False, default=dict)


class AddLineItemSerializer(serializers.Serializer):
    """Serializer for adding a line item to invoice."""

    description = serializers.CharField(max_length=500)
    quantity = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal('0.01')
    )
    unit_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal('0')
    )
    unit = serializers.CharField(max_length=20, default='item')
    tax_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    reference_type = serializers.CharField(max_length=50, required=False)
    reference_id = serializers.UUIDField(required=False)


class RecordPaymentSerializer(serializers.Serializer):
    """Serializer for recording invoice payment."""

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    payment_method = serializers.CharField(max_length=50, required=False)
    payment_reference = serializers.CharField(max_length=255, required=False)
    paid_date = serializers.DateField(required=False)


class SendInvoiceSerializer(serializers.Serializer):
    """Serializer for sending invoice."""

    email = serializers.EmailField(required=False)
    cc = serializers.ListField(
        child=serializers.EmailField(),
        required=False
    )
    subject = serializers.CharField(max_length=255, required=False)
    message = serializers.CharField(required=False)


class VoidInvoiceSerializer(serializers.Serializer):
    """Serializer for voiding invoice."""

    reason = serializers.CharField(max_length=500, required=True)


class CreateCreditNoteSerializer(serializers.Serializer):
    """Serializer for creating credit note."""

    line_items = InvoiceLineItemSerializer(many=True, required=False)
    reason = serializers.CharField(max_length=500, required=False)


class SendReminderSerializer(serializers.Serializer):
    """Serializer for sending payment reminder."""

    message = serializers.CharField(required=False)


class InvoiceSummarySerializer(serializers.Serializer):
    """Serializer for invoice summary response."""

    period = serializers.DictField(child=serializers.CharField(allow_null=True))
    total_invoiced = serializers.FloatField()
    total_paid = serializers.FloatField()
    total_outstanding = serializers.FloatField()
    overdue_count = serializers.IntegerField()
    status_breakdown = serializers.DictField(child=serializers.IntegerField())


class InvoiceFilterSerializer(serializers.Serializer):
    """Serializer for invoice filtering parameters."""

    account_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=InvoiceStatus.choices,
        required=False
    )
    invoice_type = serializers.ChoiceField(
        choices=InvoiceType.choices,
        required=False
    )
    is_overdue = serializers.BooleanField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    search = serializers.CharField(required=False)
    order_by = serializers.CharField(default='-invoice_date')
    limit = serializers.IntegerField(default=50, max_value=100)
    offset = serializers.IntegerField(default=0)
