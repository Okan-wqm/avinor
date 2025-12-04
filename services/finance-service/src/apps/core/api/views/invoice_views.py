# services/finance-service/src/apps/core/api/views/invoice_views.py
"""
Invoice Views

DRF viewset for invoice management.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models.invoice import Invoice
from ...services.invoice_service import (
    InvoiceService,
    InvoiceServiceError,
    InvoiceNotFoundError,
    InvoiceAlreadyPaidError,
)
from ..serializers.invoice_serializers import (
    InvoiceSerializer,
    InvoiceListSerializer,
    InvoiceDetailSerializer,
    InvoiceCreateSerializer,
    InvoiceFromTransactionsSerializer,
    AddLineItemSerializer,
    RecordPaymentSerializer,
    SendInvoiceSerializer,
    VoidInvoiceSerializer,
    CreateCreditNoteSerializer,
    SendReminderSerializer,
    InvoiceSummarySerializer,
)

logger = logging.getLogger(__name__)


class InvoiceViewSet(viewsets.ViewSet):
    """
    ViewSet for managing invoices.

    Provides invoice CRUD, sending, and payment tracking.
    """

    permission_classes = [IsAuthenticated]

    def get_organization_id(self, request):
        """Get organization ID from request."""
        return request.headers.get('X-Organization-ID') or request.user.organization_id

    def list(self, request):
        """
        List invoices with filtering.

        GET /api/v1/finance/invoices/
        """
        organization_id = self.get_organization_id(request)

        result = InvoiceService.list_invoices(
            organization_id=organization_id,
            account_id=request.query_params.get('account_id'),
            status=request.query_params.get('status'),
            invoice_type=request.query_params.get('invoice_type'),
            is_overdue=request.query_params.get('is_overdue'),
            date_from=request.query_params.get('date_from'),
            date_to=request.query_params.get('date_to'),
            search=request.query_params.get('search'),
            order_by=request.query_params.get('order_by', '-invoice_date'),
            limit=int(request.query_params.get('limit', 50)),
            offset=int(request.query_params.get('offset', 0)),
        )

        return Response(result)

    def retrieve(self, request, pk=None):
        """
        Get invoice details.

        GET /api/v1/finance/invoices/{id}/
        """
        try:
            organization_id = self.get_organization_id(request)
            invoice = InvoiceService.get_invoice(pk, organization_id)
            serializer = InvoiceDetailSerializer(invoice)
            return Response(serializer.data)
        except InvoiceNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    def create(self, request):
        """
        Create a new invoice.

        POST /api/v1/finance/invoices/
        """
        serializer = InvoiceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            invoice = InvoiceService.create_invoice(
                organization_id=organization_id,
                created_by=request.user.id,
                **serializer.validated_data
            )

            return Response(
                InvoiceDetailSerializer(invoice).data,
                status=status.HTTP_201_CREATED
            )
        except InvoiceServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def from_transactions(self, request):
        """
        Create invoice from transactions.

        POST /api/v1/finance/invoices/from_transactions/
        """
        serializer = InvoiceFromTransactionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            invoice = InvoiceService.create_invoice_from_transactions(
                organization_id=organization_id,
                created_by=request.user.id,
                **serializer.validated_data
            )

            return Response(
                InvoiceDetailSerializer(invoice).data,
                status=status.HTTP_201_CREATED
            )
        except InvoiceServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def add_line_item(self, request, pk=None):
        """
        Add a line item to invoice.

        POST /api/v1/finance/invoices/{id}/add_line_item/
        """
        serializer = AddLineItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            invoice = InvoiceService.add_line_item(
                invoice_id=pk,
                **serializer.validated_data
            )

            return Response(InvoiceDetailSerializer(invoice).data)
        except InvoiceNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except InvoiceServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        """
        Finalize a draft invoice.

        POST /api/v1/finance/invoices/{id}/finalize/
        """
        try:
            invoice = InvoiceService.finalize_invoice(
                invoice_id=pk,
                finalized_by=request.user.id
            )

            return Response(InvoiceDetailSerializer(invoice).data)
        except InvoiceNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except InvoiceServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """
        Send invoice via email.

        POST /api/v1/finance/invoices/{id}/send/
        """
        serializer = SendInvoiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            invoice = InvoiceService.send_invoice(
                invoice_id=pk,
                **serializer.validated_data
            )

            return Response(InvoiceDetailSerializer(invoice).data)
        except InvoiceNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except InvoiceServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def record_payment(self, request, pk=None):
        """
        Record a payment against invoice.

        POST /api/v1/finance/invoices/{id}/record_payment/
        """
        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            invoice = InvoiceService.record_payment(
                invoice_id=pk,
                recorded_by=request.user.id,
                **serializer.validated_data
            )

            return Response(InvoiceDetailSerializer(invoice).data)
        except InvoiceNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except InvoiceAlreadyPaidError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except InvoiceServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        """
        Void an invoice.

        POST /api/v1/finance/invoices/{id}/void/
        """
        serializer = VoidInvoiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            invoice = InvoiceService.void_invoice(
                invoice_id=pk,
                reason=serializer.validated_data['reason'],
                voided_by=request.user.id
            )

            return Response(InvoiceDetailSerializer(invoice).data)
        except InvoiceNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except InvoiceServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def credit_note(self, request, pk=None):
        """
        Create a credit note for invoice.

        POST /api/v1/finance/invoices/{id}/credit_note/
        """
        serializer = CreateCreditNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            credit_note = InvoiceService.create_credit_note(
                invoice_id=pk,
                created_by=request.user.id,
                **serializer.validated_data
            )

            return Response(
                InvoiceDetailSerializer(credit_note).data,
                status=status.HTTP_201_CREATED
            )
        except InvoiceNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except InvoiceServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def generate_pdf(self, request, pk=None):
        """
        Generate PDF for invoice.

        POST /api/v1/finance/invoices/{id}/generate_pdf/
        """
        try:
            pdf_url = InvoiceService.generate_pdf(pk)

            return Response({'pdf_url': pdf_url})
        except InvoiceNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def send_reminder(self, request, pk=None):
        """
        Send payment reminder.

        POST /api/v1/finance/invoices/{id}/send_reminder/
        """
        serializer = SendReminderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            invoice = InvoiceService.send_reminder(
                invoice_id=pk,
                message=serializer.validated_data.get('message')
            )

            return Response(InvoiceDetailSerializer(invoice).data)
        except InvoiceNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except InvoiceServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def mark_viewed(self, request, pk=None):
        """
        Mark invoice as viewed.

        POST /api/v1/finance/invoices/{id}/mark_viewed/
        """
        try:
            invoice = InvoiceService.get_invoice(pk)
            invoice.mark_viewed()
            invoice.save()

            return Response(InvoiceDetailSerializer(invoice).data)
        except InvoiceNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def by_number(self, request):
        """
        Get invoice by number.

        GET /api/v1/finance/invoices/by_number/?invoice_number=INV-2024-000001
        """
        organization_id = self.get_organization_id(request)
        invoice_number = request.query_params.get('invoice_number')

        if not invoice_number:
            return Response(
                {'error': 'invoice_number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            invoice = InvoiceService.get_invoice_by_number(
                invoice_number=invoice_number,
                organization_id=organization_id
            )

            return Response(InvoiceDetailSerializer(invoice).data)
        except InvoiceNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """
        Get overdue invoices.

        GET /api/v1/finance/invoices/overdue/?min_days_overdue=1
        """
        organization_id = self.get_organization_id(request)
        min_days_overdue = int(request.query_params.get('min_days_overdue', 1))

        invoices = InvoiceService.get_overdue_invoices(
            organization_id=organization_id,
            min_days_overdue=min_days_overdue
        )

        return Response({
            'invoices': InvoiceListSerializer(invoices, many=True).data,
            'count': len(invoices),
        })

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get invoice summary.

        GET /api/v1/finance/invoices/summary/
        """
        organization_id = self.get_organization_id(request)

        summary = InvoiceService.get_invoice_summary(
            organization_id=organization_id,
            date_from=request.query_params.get('date_from'),
            date_to=request.query_params.get('date_to'),
        )

        return Response(summary)
