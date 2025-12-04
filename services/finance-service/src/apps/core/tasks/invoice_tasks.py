# services/finance-service/src/apps/core/tasks/invoice_tasks.py
"""
Invoice Celery Tasks

Background tasks for invoice operations.
"""

import logging
from celery import shared_task
from datetime import date, timedelta
from django.db.models import Q

logger = logging.getLogger(__name__)


@shared_task(name='finance.send_invoice_reminders')
def send_invoice_reminders():
    """
    Send payment reminders for overdue invoices.

    Runs daily to send reminders based on configured schedule.
    """
    from ..models.invoice import Invoice, InvoiceStatus
    from ..services.invoice_service import InvoiceService

    today = date.today()
    reminder_days = [7, 14, 30, 60]  # Days overdue to send reminders

    sent_count = 0
    error_count = 0

    for days in reminder_days:
        target_date = today - timedelta(days=days)

        invoices = Invoice.objects.filter(
            due_date=target_date,
            auto_remind=True
        ).exclude(
            status__in=[InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.VOID]
        )

        for invoice in invoices:
            try:
                InvoiceService.send_reminder(invoice.id)
                sent_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to send reminder for invoice {invoice.invoice_number}: {e}"
                )
                error_count += 1

    logger.info(
        f"Invoice reminders sent: {sent_count}, errors: {error_count}"
    )

    return {'sent': sent_count, 'errors': error_count}


@shared_task(name='finance.mark_overdue_invoices')
def mark_overdue_invoices():
    """
    Mark invoices as overdue.

    Runs daily to update invoice status.
    """
    from ..models.invoice import Invoice, InvoiceStatus
    from ..events.publishers import publish_invoice_overdue

    today = date.today()

    # Find invoices that should be marked overdue
    invoices = Invoice.objects.filter(
        due_date__lt=today,
        status__in=[InvoiceStatus.PENDING, InvoiceStatus.SENT, InvoiceStatus.VIEWED, InvoiceStatus.PARTIAL]
    )

    marked_count = 0

    for invoice in invoices:
        invoice.status = InvoiceStatus.OVERDUE
        invoice.save(update_fields=['status', 'updated_at'])

        # Publish event
        publish_invoice_overdue(
            invoice_id=str(invoice.id),
            invoice_number=invoice.invoice_number,
            amount_due=float(invoice.amount_due),
            days_overdue=invoice.days_overdue,
            account_id=str(invoice.account_id),
            organization_id=str(invoice.organization_id)
        )

        marked_count += 1

    logger.info(f"Marked {marked_count} invoices as overdue")

    return {'marked': marked_count}


@shared_task(name='finance.generate_recurring_invoices')
def generate_recurring_invoices():
    """
    Generate invoices for recurring billing.

    Runs daily to create invoices from recurring templates.
    """
    from ..models.invoice import Invoice, InvoiceType, InvoiceStatus
    from ..services.invoice_service import InvoiceService

    today = date.today()

    # Find recurring invoice templates due for generation
    templates = Invoice.objects.filter(
        invoice_type=InvoiceType.RECURRING,
        status=InvoiceStatus.PENDING
    )

    # For now, just return - full implementation would check
    # recurring schedule and generate new invoices

    generated_count = 0

    logger.info(f"Generated {generated_count} recurring invoices")

    return {'generated': generated_count}
