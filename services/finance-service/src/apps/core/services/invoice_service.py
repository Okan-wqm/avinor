# services/finance-service/src/apps/core/services/invoice_service.py
"""
Invoice Service

Business logic for invoice management.
"""

import uuid
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string

from ..models.account import Account
from ..models.invoice import Invoice, InvoiceItem, InvoiceType, InvoiceStatus
from ..models.transaction import TransactionType

logger = logging.getLogger(__name__)


class InvoiceServiceError(Exception):
    """Base exception for invoice service errors."""
    pass


class InvoiceNotFoundError(InvoiceServiceError):
    """Raised when invoice is not found."""
    pass


class InvoiceAlreadyPaidError(InvoiceServiceError):
    """Raised when invoice is already paid."""
    pass


class InvoiceService:
    """
    Service for managing invoices.

    Handles invoice creation, sending, payment tracking, and reminders.
    """

    @staticmethod
    @transaction.atomic
    def create_invoice(
        organization_id: uuid.UUID,
        account_id: uuid.UUID,
        line_items: List[Dict],
        invoice_type: str = InvoiceType.STANDARD,
        invoice_date: date = None,
        due_date: date = None,
        payment_terms_days: int = 30,
        notes: str = None,
        terms: str = None,
        discount_type: str = None,
        discount_value: Decimal = None,
        discount_code: str = None,
        tax_details: List[Dict] = None,
        metadata: Dict = None,
        created_by: uuid.UUID = None
    ) -> Invoice:
        """
        Create a new invoice.

        Args:
            organization_id: Organization UUID
            account_id: Account UUID
            line_items: List of line items
            invoice_type: Invoice type
            invoice_date: Invoice date (defaults to today)
            due_date: Due date (calculated from payment terms if not provided)
            payment_terms_days: Days until due
            notes: Customer-visible notes
            terms: Payment terms text
            discount_type: 'percentage' or 'fixed'
            discount_value: Discount amount or percentage
            discount_code: Discount code used
            tax_details: Tax breakdown
            metadata: Additional metadata
            created_by: User who created the invoice

        Returns:
            Created Invoice instance
        """
        account = Account.objects.get(id=account_id)

        # Set dates
        invoice_date = invoice_date or date.today()
        due_date = due_date or (invoice_date + timedelta(days=payment_terms_days))

        # Calculate discount
        discount_amount = Decimal('0')
        subtotal = sum(Decimal(str(item.get('amount', 0))) for item in line_items)

        if discount_type and discount_value:
            if discount_type == 'percentage':
                discount_amount = subtotal * (discount_value / 100)
            else:
                discount_amount = discount_value

        # Create invoice
        invoice = Invoice.objects.create(
            organization_id=organization_id,
            account=account,
            invoice_type=invoice_type,
            customer_name=account.billing_name or '',
            customer_email=account.billing_email,
            customer_phone=account.billing_phone,
            customer_address=InvoiceService._format_address(account),
            billing_address_line1=account.billing_address_line1,
            billing_address_line2=account.billing_address_line2,
            billing_city=account.billing_city,
            billing_state=account.billing_state,
            billing_postal_code=account.billing_postal_code,
            billing_country=account.billing_country,
            invoice_date=invoice_date,
            due_date=due_date,
            line_items=line_items,
            tax_details=tax_details or [],
            discount_type=discount_type,
            discount_value=discount_value,
            discount_code=discount_code,
            discount_amount=discount_amount,
            notes=notes,
            terms=terms,
            metadata=metadata or {},
            created_by=created_by,
            status=InvoiceStatus.DRAFT
        )

        # Calculate totals (done in save)
        invoice.save()

        logger.info(
            f"Created invoice {invoice.invoice_number}",
            extra={
                'invoice_id': str(invoice.id),
                'account_id': str(account_id),
                'total_amount': float(invoice.total_amount)
            }
        )

        return invoice

    @staticmethod
    def create_invoice_from_transactions(
        organization_id: uuid.UUID,
        account_id: uuid.UUID,
        transaction_ids: List[uuid.UUID],
        **kwargs
    ) -> Invoice:
        """
        Create invoice from existing transactions.

        Args:
            organization_id: Organization UUID
            account_id: Account UUID
            transaction_ids: List of transaction UUIDs to include
            **kwargs: Additional invoice parameters

        Returns:
            Created Invoice instance
        """
        from .transaction_service import TransactionService

        line_items = []

        for txn_id in transaction_ids:
            txn = TransactionService.get_transaction(txn_id, organization_id)

            if txn.account_id != account_id:
                raise InvoiceServiceError(
                    f"Transaction {txn_id} does not belong to account {account_id}"
                )

            if txn.transaction_type != TransactionType.CHARGE:
                continue

            # Create line item from transaction
            item = {
                'description': txn.description or f"Charge: {txn.transaction_subtype}",
                'quantity': 1,
                'unit': 'item',
                'unit_price': float(txn.amount),
                'amount': float(txn.amount),
                'tax_rate': float(txn.tax_rate) if txn.tax_rate else None,
                'tax_amount': float(txn.tax_amount),
                'reference_type': 'transaction',
                'reference_id': str(txn.id),
            }
            line_items.append(item)

        if not line_items:
            raise InvoiceServiceError("No valid transactions to invoice")

        return InvoiceService.create_invoice(
            organization_id=organization_id,
            account_id=account_id,
            line_items=line_items,
            **kwargs
        )

    @staticmethod
    def add_line_item(
        invoice_id: uuid.UUID,
        description: str,
        quantity: float,
        unit_price: Decimal,
        unit: str = 'item',
        tax_rate: Decimal = None,
        reference_type: str = None,
        reference_id: uuid.UUID = None
    ) -> Invoice:
        """
        Add a line item to an invoice.

        Args:
            invoice_id: Invoice UUID
            description: Item description
            quantity: Quantity
            unit_price: Unit price
            unit: Unit of measure
            tax_rate: Tax rate percentage
            reference_type: Reference type
            reference_id: Reference UUID

        Returns:
            Updated Invoice instance
        """
        invoice = InvoiceService.get_invoice(invoice_id)

        if invoice.status not in [InvoiceStatus.DRAFT, InvoiceStatus.PENDING]:
            raise InvoiceServiceError(
                f"Cannot modify invoice in status: {invoice.status}"
            )

        invoice.add_line_item(
            description=description,
            quantity=quantity,
            unit_price=unit_price,
            unit=unit,
            tax_rate=tax_rate,
            reference_type=reference_type,
            reference_id=reference_id
        )

        invoice.save()

        return invoice

    @staticmethod
    def finalize_invoice(
        invoice_id: uuid.UUID,
        finalized_by: uuid.UUID = None
    ) -> Invoice:
        """
        Finalize a draft invoice.

        Args:
            invoice_id: Invoice UUID
            finalized_by: User who finalized

        Returns:
            Updated Invoice instance
        """
        invoice = InvoiceService.get_invoice(invoice_id)

        if invoice.status != InvoiceStatus.DRAFT:
            raise InvoiceServiceError(
                f"Can only finalize draft invoices, current status: {invoice.status}"
            )

        if not invoice.line_items:
            raise InvoiceServiceError("Invoice has no line items")

        invoice.status = InvoiceStatus.PENDING
        invoice.updated_by = finalized_by
        invoice.save()

        logger.info(
            f"Finalized invoice {invoice.invoice_number}",
            extra={'invoice_id': str(invoice_id)}
        )

        return invoice

    @staticmethod
    def send_invoice(
        invoice_id: uuid.UUID,
        email: str = None,
        cc: List[str] = None,
        subject: str = None,
        message: str = None
    ) -> Invoice:
        """
        Send invoice via email.

        Args:
            invoice_id: Invoice UUID
            email: Recipient email (uses customer email if not provided)
            cc: CC email addresses
            subject: Email subject
            message: Email message

        Returns:
            Updated Invoice instance
        """
        invoice = InvoiceService.get_invoice(invoice_id)

        if invoice.status == InvoiceStatus.DRAFT:
            raise InvoiceServiceError("Cannot send draft invoice")

        recipient = email or invoice.customer_email

        if not recipient:
            raise InvoiceServiceError("No email address for invoice")

        # Generate PDF if needed
        if not invoice.pdf_url:
            InvoiceService.generate_pdf(invoice_id)

        # Prepare email
        subject = subject or f"Invoice {invoice.invoice_number}"
        context = {
            'invoice': invoice,
            'message': message,
        }

        html_content = render_to_string('emails/invoice.html', context)
        text_content = render_to_string('emails/invoice.txt', context)

        # Send email
        try:
            send_mail(
                subject=subject,
                message=text_content,
                from_email=None,  # Use default
                recipient_list=[recipient],
                html_message=html_content,
            )

            # Update invoice
            invoice.mark_sent(email=recipient)
            if cc:
                invoice.sent_cc = ', '.join(cc)
            invoice.save()

            logger.info(
                f"Sent invoice {invoice.invoice_number} to {recipient}",
                extra={'invoice_id': str(invoice_id)}
            )

        except Exception as e:
            logger.error(
                f"Failed to send invoice {invoice.invoice_number}",
                extra={'invoice_id': str(invoice_id), 'error': str(e)}
            )
            raise InvoiceServiceError(f"Failed to send invoice: {str(e)}")

        return invoice

    @staticmethod
    @transaction.atomic
    def record_payment(
        invoice_id: uuid.UUID,
        amount: Decimal,
        payment_method: str = None,
        payment_reference: str = None,
        paid_date: date = None,
        recorded_by: uuid.UUID = None
    ) -> Invoice:
        """
        Record a payment against an invoice.

        Args:
            invoice_id: Invoice UUID
            amount: Payment amount
            payment_method: Payment method used
            payment_reference: Payment reference
            paid_date: Date of payment
            recorded_by: User who recorded payment

        Returns:
            Updated Invoice instance
        """
        invoice = Invoice.objects.select_for_update().get(id=invoice_id)

        if invoice.status in [InvoiceStatus.CANCELLED, InvoiceStatus.VOID]:
            raise InvoiceServiceError(
                f"Cannot record payment for invoice with status: {invoice.status}"
            )

        if invoice.status == InvoiceStatus.PAID:
            raise InvoiceAlreadyPaidError(
                f"Invoice {invoice.invoice_number} is already paid"
            )

        invoice.record_payment(amount, paid_date)
        invoice.updated_by = recorded_by
        invoice.save()

        logger.info(
            f"Recorded payment of {amount} for invoice {invoice.invoice_number}",
            extra={
                'invoice_id': str(invoice_id),
                'amount': float(amount),
                'new_status': invoice.status
            }
        )

        return invoice

    @staticmethod
    def void_invoice(
        invoice_id: uuid.UUID,
        reason: str,
        voided_by: uuid.UUID = None
    ) -> Invoice:
        """
        Void an invoice.

        Args:
            invoice_id: Invoice UUID
            reason: Void reason
            voided_by: User who voided

        Returns:
            Updated Invoice instance
        """
        invoice = InvoiceService.get_invoice(invoice_id)

        if invoice.status == InvoiceStatus.PAID:
            raise InvoiceServiceError("Cannot void paid invoice")

        if invoice.status == InvoiceStatus.VOID:
            raise InvoiceServiceError("Invoice already voided")

        invoice.void(reason, voided_by)
        invoice.save()

        logger.info(
            f"Voided invoice {invoice.invoice_number}",
            extra={
                'invoice_id': str(invoice_id),
                'reason': reason
            }
        )

        return invoice

    @staticmethod
    @transaction.atomic
    def create_credit_note(
        invoice_id: uuid.UUID,
        line_items: List[Dict] = None,
        reason: str = None,
        created_by: uuid.UUID = None
    ) -> Invoice:
        """
        Create a credit note for an invoice.

        Args:
            invoice_id: Original invoice UUID
            line_items: Credit note line items (uses original if not provided)
            reason: Credit note reason
            created_by: User who created

        Returns:
            Created credit note Invoice instance
        """
        original = InvoiceService.get_invoice(invoice_id)

        if original.status not in [InvoiceStatus.PAID, InvoiceStatus.PARTIAL]:
            raise InvoiceServiceError(
                "Can only create credit note for paid/partially paid invoices"
            )

        # Use original line items if not provided
        if not line_items:
            line_items = [
                {**item, 'amount': -abs(item.get('amount', 0))}
                for item in original.line_items
            ]

        credit_note = Invoice.objects.create(
            organization_id=original.organization_id,
            account=original.account,
            invoice_type=InvoiceType.CREDIT_NOTE,
            customer_name=original.customer_name,
            customer_email=original.customer_email,
            billing_address_line1=original.billing_address_line1,
            billing_city=original.billing_city,
            billing_state=original.billing_state,
            billing_postal_code=original.billing_postal_code,
            billing_country=original.billing_country,
            invoice_date=date.today(),
            due_date=date.today(),
            line_items=line_items,
            notes=reason,
            related_invoice_id=original.id,
            created_by=created_by,
            status=InvoiceStatus.PENDING
        )

        logger.info(
            f"Created credit note {credit_note.invoice_number} for {original.invoice_number}",
            extra={
                'credit_note_id': str(credit_note.id),
                'original_invoice_id': str(invoice_id)
            }
        )

        return credit_note

    @staticmethod
    def generate_pdf(invoice_id: uuid.UUID) -> str:
        """
        Generate PDF for invoice.

        Args:
            invoice_id: Invoice UUID

        Returns:
            PDF URL
        """
        invoice = InvoiceService.get_invoice(invoice_id)

        # PDF generation logic would go here
        # Using weasyprint or reportlab
        # For now, just mark as generated

        invoice.pdf_generated_at = timezone.now()
        invoice.save(update_fields=['pdf_generated_at', 'updated_at'])

        logger.info(
            f"Generated PDF for invoice {invoice.invoice_number}",
            extra={'invoice_id': str(invoice_id)}
        )

        return invoice.pdf_url

    @staticmethod
    def send_reminder(
        invoice_id: uuid.UUID,
        message: str = None
    ) -> Invoice:
        """
        Send payment reminder for overdue invoice.

        Args:
            invoice_id: Invoice UUID
            message: Custom reminder message

        Returns:
            Updated Invoice instance
        """
        invoice = InvoiceService.get_invoice(invoice_id)

        if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.VOID]:
            raise InvoiceServiceError(
                f"Cannot send reminder for invoice with status: {invoice.status}"
            )

        if not invoice.customer_email:
            raise InvoiceServiceError("No email address for reminder")

        # Prepare reminder email
        subject = f"Payment Reminder: Invoice {invoice.invoice_number}"
        context = {
            'invoice': invoice,
            'message': message,
            'amount_due': invoice.amount_due,
            'days_overdue': invoice.days_overdue,
        }

        html_content = render_to_string('emails/invoice_reminder.html', context)
        text_content = render_to_string('emails/invoice_reminder.txt', context)

        try:
            send_mail(
                subject=subject,
                message=text_content,
                from_email=None,
                recipient_list=[invoice.customer_email],
                html_message=html_content,
            )

            invoice.reminder_count += 1
            invoice.last_reminder_at = timezone.now()
            invoice.save(update_fields=['reminder_count', 'last_reminder_at', 'updated_at'])

            logger.info(
                f"Sent reminder for invoice {invoice.invoice_number}",
                extra={
                    'invoice_id': str(invoice_id),
                    'reminder_count': invoice.reminder_count
                }
            )

        except Exception as e:
            logger.error(
                f"Failed to send reminder for invoice {invoice.invoice_number}",
                extra={'invoice_id': str(invoice_id), 'error': str(e)}
            )
            raise InvoiceServiceError(f"Failed to send reminder: {str(e)}")

        return invoice

    @staticmethod
    def get_invoice(
        invoice_id: uuid.UUID,
        organization_id: uuid.UUID = None
    ) -> Invoice:
        """
        Get invoice by ID.

        Args:
            invoice_id: Invoice UUID
            organization_id: Optional organization filter

        Returns:
            Invoice instance

        Raises:
            InvoiceNotFoundError: If not found
        """
        queryset = Invoice.objects.filter(id=invoice_id)

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        invoice = queryset.select_related('account').first()

        if not invoice:
            raise InvoiceNotFoundError(f"Invoice {invoice_id} not found")

        return invoice

    @staticmethod
    def get_invoice_by_number(
        invoice_number: str,
        organization_id: uuid.UUID = None
    ) -> Invoice:
        """
        Get invoice by number.

        Args:
            invoice_number: Invoice number
            organization_id: Optional organization filter

        Returns:
            Invoice instance
        """
        queryset = Invoice.objects.filter(invoice_number=invoice_number)

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        invoice = queryset.select_related('account').first()

        if not invoice:
            raise InvoiceNotFoundError(f"Invoice {invoice_number} not found")

        return invoice

    @staticmethod
    def list_invoices(
        organization_id: uuid.UUID,
        account_id: uuid.UUID = None,
        status: str = None,
        invoice_type: str = None,
        is_overdue: bool = None,
        date_from: date = None,
        date_to: date = None,
        search: str = None,
        order_by: str = '-invoice_date',
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List invoices with filtering.

        Args:
            organization_id: Organization UUID
            account_id: Filter by account
            status: Filter by status
            invoice_type: Filter by type
            is_overdue: Filter overdue invoices
            date_from: Filter from date
            date_to: Filter to date
            search: Search in invoice number and customer name
            order_by: Order by field
            limit: Max results
            offset: Result offset

        Returns:
            Dict with invoices and pagination info
        """
        queryset = Invoice.objects.filter(organization_id=organization_id)

        if account_id:
            queryset = queryset.filter(account_id=account_id)

        if status:
            queryset = queryset.filter(status=status)

        if invoice_type:
            queryset = queryset.filter(invoice_type=invoice_type)

        if is_overdue is not None:
            today = date.today()
            if is_overdue:
                queryset = queryset.filter(
                    due_date__lt=today
                ).exclude(
                    status__in=[InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.VOID]
                )
            else:
                queryset = queryset.filter(
                    Q(due_date__gte=today) |
                    Q(status__in=[InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.VOID])
                )

        if date_from:
            queryset = queryset.filter(invoice_date__gte=date_from)

        if date_to:
            queryset = queryset.filter(invoice_date__lte=date_to)

        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search) |
                Q(customer_name__icontains=search)
            )

        total = queryset.count()
        invoices = queryset.order_by(order_by).select_related('account')[offset:offset + limit]

        return {
            'invoices': [
                InvoiceService._invoice_to_dict(inv)
                for inv in invoices
            ],
            'total': total,
            'limit': limit,
            'offset': offset,
        }

    @staticmethod
    def get_overdue_invoices(
        organization_id: uuid.UUID,
        min_days_overdue: int = 1
    ) -> List[Invoice]:
        """
        Get overdue invoices.

        Args:
            organization_id: Organization UUID
            min_days_overdue: Minimum days overdue

        Returns:
            List of overdue invoices
        """
        cutoff_date = date.today() - timedelta(days=min_days_overdue)

        return list(Invoice.objects.filter(
            organization_id=organization_id,
            due_date__lt=cutoff_date
        ).exclude(
            status__in=[InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.VOID]
        ).order_by('due_date'))

    @staticmethod
    def get_invoice_summary(
        organization_id: uuid.UUID,
        date_from: date = None,
        date_to: date = None
    ) -> Dict[str, Any]:
        """
        Get invoice summary statistics.

        Args:
            organization_id: Organization UUID
            date_from: Start date
            date_to: End date

        Returns:
            Dict with summary statistics
        """
        queryset = Invoice.objects.filter(organization_id=organization_id)

        if date_from:
            queryset = queryset.filter(invoice_date__gte=date_from)

        if date_to:
            queryset = queryset.filter(invoice_date__lte=date_to)

        total_invoiced = queryset.exclude(
            status__in=[InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED, InvoiceStatus.VOID]
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        total_paid = queryset.filter(
            status=InvoiceStatus.PAID
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        total_outstanding = queryset.exclude(
            status__in=[InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.VOID]
        ).aggregate(total=Sum('total_amount') - Sum('amount_paid'))

        outstanding = (total_outstanding.get('total') or Decimal('0')) - (
            total_outstanding.get('amount_paid') or Decimal('0')
        )

        overdue_count = queryset.filter(
            due_date__lt=date.today()
        ).exclude(
            status__in=[InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.VOID]
        ).count()

        return {
            'period': {
                'from': date_from.isoformat() if date_from else None,
                'to': date_to.isoformat() if date_to else None,
            },
            'total_invoiced': float(total_invoiced),
            'total_paid': float(total_paid),
            'total_outstanding': float(outstanding) if isinstance(outstanding, Decimal) else 0,
            'overdue_count': overdue_count,
            'status_breakdown': InvoiceService._get_status_breakdown(queryset),
        }

    @staticmethod
    def _get_status_breakdown(queryset) -> Dict[str, int]:
        """Get count of invoices by status."""
        from django.db.models import Count

        breakdown = queryset.values('status').annotate(
            count=Count('id')
        )

        return {item['status']: item['count'] for item in breakdown}

    @staticmethod
    def _format_address(account: Account) -> str:
        """Format billing address as single string."""
        parts = [
            account.billing_address_line1,
            account.billing_address_line2,
            f"{account.billing_city}, {account.billing_state} {account.billing_postal_code}",
            account.billing_country
        ]
        return '\n'.join(filter(None, parts))

    @staticmethod
    def _invoice_to_dict(invoice: Invoice) -> Dict[str, Any]:
        """Convert invoice to dictionary."""
        return {
            'id': str(invoice.id),
            'invoice_number': invoice.invoice_number,
            'invoice_type': invoice.invoice_type,
            'account_id': str(invoice.account_id),
            'customer_name': invoice.customer_name,
            'customer_email': invoice.customer_email,
            'invoice_date': invoice.invoice_date.isoformat(),
            'due_date': invoice.due_date.isoformat(),
            'subtotal': float(invoice.subtotal),
            'tax_amount': float(invoice.tax_amount),
            'discount_amount': float(invoice.discount_amount),
            'total_amount': float(invoice.total_amount),
            'amount_paid': float(invoice.amount_paid),
            'amount_due': float(invoice.amount_due),
            'currency': invoice.currency,
            'status': invoice.status,
            'is_overdue': invoice.is_overdue,
            'days_overdue': invoice.days_overdue,
            'line_items': invoice.line_items,
            'sent_at': invoice.sent_at.isoformat() if invoice.sent_at else None,
            'paid_date': invoice.paid_date.isoformat() if invoice.paid_date else None,
            'created_at': invoice.created_at.isoformat(),
        }
