# services/finance-service/src/apps/core/api/views/transaction_views.py
"""
Transaction Views

DRF viewset for transaction management.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models.transaction import Transaction
from ...services.transaction_service import (
    TransactionService,
    TransactionServiceError,
    TransactionNotFoundError,
    TransactionReversalError,
)
from ..serializers.transaction_serializers import (
    TransactionSerializer,
    TransactionListSerializer,
    TransactionDetailSerializer,
    CreateChargeSerializer,
    CreatePaymentSerializer,
    CreateRefundSerializer,
    CreateCreditSerializer,
    CreateAdjustmentSerializer,
    ReverseTransactionSerializer,
    TransactionSummarySerializer,
)

logger = logging.getLogger(__name__)


class TransactionViewSet(viewsets.ViewSet):
    """
    ViewSet for managing financial transactions.

    Provides transaction creation and querying.
    """

    permission_classes = [IsAuthenticated]

    def get_organization_id(self, request):
        """Get organization ID from request."""
        return request.headers.get('X-Organization-ID') or request.user.organization_id

    def list(self, request):
        """
        List transactions with filtering.

        GET /api/v1/finance/transactions/
        """
        organization_id = self.get_organization_id(request)

        result = TransactionService.list_transactions(
            organization_id=organization_id,
            account_id=request.query_params.get('account_id'),
            transaction_type=request.query_params.get('transaction_type'),
            status=request.query_params.get('status'),
            reference_type=request.query_params.get('reference_type'),
            reference_id=request.query_params.get('reference_id'),
            date_from=request.query_params.get('date_from'),
            date_to=request.query_params.get('date_to'),
            min_amount=request.query_params.get('min_amount'),
            max_amount=request.query_params.get('max_amount'),
            order_by=request.query_params.get('order_by', '-created_at'),
            limit=int(request.query_params.get('limit', 50)),
            offset=int(request.query_params.get('offset', 0)),
        )

        return Response(result)

    def retrieve(self, request, pk=None):
        """
        Get transaction details.

        GET /api/v1/finance/transactions/{id}/
        """
        try:
            organization_id = self.get_organization_id(request)
            txn = TransactionService.get_transaction(pk, organization_id)
            serializer = TransactionDetailSerializer(txn)
            return Response(serializer.data)
        except TransactionNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def charge(self, request):
        """
        Create a charge transaction.

        POST /api/v1/finance/transactions/charge/
        """
        serializer = CreateChargeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            txn = TransactionService.create_charge(
                organization_id=organization_id,
                created_by=request.user.id,
                **serializer.validated_data
            )

            return Response(
                TransactionDetailSerializer(txn).data,
                status=status.HTTP_201_CREATED
            )
        except TransactionServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def payment(self, request):
        """
        Create a payment transaction.

        POST /api/v1/finance/transactions/payment/
        """
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            txn = TransactionService.create_payment(
                organization_id=organization_id,
                created_by=request.user.id,
                **serializer.validated_data
            )

            return Response(
                TransactionDetailSerializer(txn).data,
                status=status.HTTP_201_CREATED
            )
        except TransactionServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def refund(self, request):
        """
        Create a refund transaction.

        POST /api/v1/finance/transactions/refund/
        """
        serializer = CreateRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            txn = TransactionService.create_refund(
                organization_id=organization_id,
                created_by=request.user.id,
                **serializer.validated_data
            )

            return Response(
                TransactionDetailSerializer(txn).data,
                status=status.HTTP_201_CREATED
            )
        except TransactionServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def credit(self, request):
        """
        Create a credit transaction.

        POST /api/v1/finance/transactions/credit/
        """
        serializer = CreateCreditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            txn = TransactionService.create_credit(
                organization_id=organization_id,
                created_by=request.user.id,
                **serializer.validated_data
            )

            return Response(
                TransactionDetailSerializer(txn).data,
                status=status.HTTP_201_CREATED
            )
        except TransactionServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def adjustment(self, request):
        """
        Create an adjustment transaction.

        POST /api/v1/finance/transactions/adjustment/
        """
        serializer = CreateAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            txn = TransactionService.create_adjustment(
                organization_id=organization_id,
                created_by=request.user.id,
                approved_by=request.user.id,
                **serializer.validated_data
            )

            return Response(
                TransactionDetailSerializer(txn).data,
                status=status.HTTP_201_CREATED
            )
        except TransactionServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        """
        Reverse a transaction.

        POST /api/v1/finance/transactions/{id}/reverse/
        """
        serializer = ReverseTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            reversal = TransactionService.reverse_transaction(
                transaction_id=pk,
                reason=serializer.validated_data['reason'],
                reversed_by=request.user.id
            )

            return Response(TransactionDetailSerializer(reversal).data)
        except TransactionNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except TransactionReversalError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get transaction summary.

        GET /api/v1/finance/transactions/summary/
        """
        organization_id = self.get_organization_id(request)

        summary = TransactionService.get_transaction_summary(
            organization_id=organization_id,
            account_id=request.query_params.get('account_id'),
            date_from=request.query_params.get('date_from'),
            date_to=request.query_params.get('date_to'),
        )

        return Response(summary)

    @action(detail=False, methods=['get'])
    def by_reference(self, request):
        """
        Get transactions by reference.

        GET /api/v1/finance/transactions/by_reference/?reference_type=flight&reference_id=...
        """
        organization_id = self.get_organization_id(request)
        reference_type = request.query_params.get('reference_type')
        reference_id = request.query_params.get('reference_id')

        if not reference_type or not reference_id:
            return Response(
                {'error': 'reference_type and reference_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        transactions = TransactionService.get_transactions_by_reference(
            reference_type=reference_type,
            reference_id=reference_id,
            organization_id=organization_id
        )

        return Response({
            'transactions': TransactionListSerializer(transactions, many=True).data,
            'count': len(transactions),
        })
