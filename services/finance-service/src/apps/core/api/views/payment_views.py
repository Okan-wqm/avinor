# services/finance-service/src/apps/core/api/views/payment_views.py
"""
Payment Views

DRF viewsets for payment method and processing management.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models.payment import PaymentMethod
from ...services.payment_service import (
    PaymentService,
    PaymentServiceError,
    PaymentMethodNotFoundError,
    PaymentFailedError,
    PaymentGatewayError,
)
from ..serializers.payment_serializers import (
    PaymentMethodSerializer,
    PaymentMethodListSerializer,
    PaymentMethodDetailSerializer,
    PaymentMethodCreateSerializer,
    PaymentMethodUpdateSerializer,
    ProcessPaymentSerializer,
    ProcessRefundSerializer,
    VerifyPaymentMethodSerializer,
    PaymentResultSerializer,
    RefundResultSerializer,
)

logger = logging.getLogger(__name__)


class PaymentMethodViewSet(viewsets.ViewSet):
    """
    ViewSet for managing payment methods.

    Provides payment method CRUD operations.
    """

    permission_classes = [IsAuthenticated]

    def get_organization_id(self, request):
        """Get organization ID from request."""
        return request.headers.get('X-Organization-ID') or request.user.organization_id

    def list(self, request):
        """
        List payment methods.

        GET /api/v1/finance/payment-methods/
        """
        organization_id = self.get_organization_id(request)
        account_id = request.query_params.get('account_id')

        if not account_id:
            return Response(
                {'error': 'account_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_methods = PaymentService.get_account_payment_methods(
            account_id=account_id,
            organization_id=organization_id,
            status=request.query_params.get('status'),
            method_type=request.query_params.get('method_type')
        )

        return Response({
            'payment_methods': PaymentMethodListSerializer(payment_methods, many=True).data,
            'count': len(payment_methods),
        })

    def retrieve(self, request, pk=None):
        """
        Get payment method details.

        GET /api/v1/finance/payment-methods/{id}/
        """
        try:
            organization_id = self.get_organization_id(request)
            payment_method = PaymentService.get_payment_method(pk, organization_id)
            serializer = PaymentMethodDetailSerializer(payment_method)
            return Response(serializer.data)
        except PaymentMethodNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    def create(self, request):
        """
        Create a new payment method.

        POST /api/v1/finance/payment-methods/
        """
        serializer = PaymentMethodCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            payment_method = PaymentService.create_payment_method(
                organization_id=organization_id,
                **serializer.validated_data
            )

            return Response(
                PaymentMethodDetailSerializer(payment_method).data,
                status=status.HTTP_201_CREATED
            )
        except PaymentGatewayError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except PaymentServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def partial_update(self, request, pk=None):
        """
        Update payment method.

        PATCH /api/v1/finance/payment-methods/{id}/
        """
        serializer = PaymentMethodUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            payment_method = PaymentService.get_payment_method(pk, organization_id)

            # Update fields
            data = serializer.validated_data
            if 'nickname' in data:
                payment_method.nickname = data['nickname']
            if 'is_default' in data and data['is_default']:
                payment_method.set_as_default()

            if 'billing_address' in data:
                billing = data['billing_address']
                payment_method.billing_name = billing.get('name')
                payment_method.billing_email = billing.get('email')
                payment_method.billing_phone = billing.get('phone')
                payment_method.billing_address_line1 = billing.get('line1')
                payment_method.billing_address_line2 = billing.get('line2')
                payment_method.billing_city = billing.get('city')
                payment_method.billing_state = billing.get('state')
                payment_method.billing_postal_code = billing.get('postal_code')
                payment_method.billing_country = billing.get('country', 'US')

            payment_method.save()

            return Response(PaymentMethodDetailSerializer(payment_method).data)
        except PaymentMethodNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    def destroy(self, request, pk=None):
        """
        Delete payment method.

        DELETE /api/v1/finance/payment-methods/{id}/
        """
        organization_id = self.get_organization_id(request)

        try:
            PaymentService.delete_payment_method(pk, organization_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PaymentMethodNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PaymentGatewayError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """
        Set as default payment method.

        POST /api/v1/finance/payment-methods/{id}/set_default/
        """
        organization_id = self.get_organization_id(request)

        try:
            payment_method = PaymentService.set_default_payment_method(pk, organization_id)
            return Response(PaymentMethodDetailSerializer(payment_method).data)
        except PaymentMethodNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PaymentServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """
        Verify payment method.

        POST /api/v1/finance/payment-methods/{id}/verify/
        """
        serializer = VerifyPaymentMethodSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = PaymentService.verify_payment_method(
                payment_method_id=pk,
                **serializer.validated_data
            )

            return Response(result)
        except PaymentMethodNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PaymentServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def default(self, request):
        """
        Get default payment method for account.

        GET /api/v1/finance/payment-methods/default/?account_id=...
        """
        account_id = request.query_params.get('account_id')

        if not account_id:
            return Response(
                {'error': 'account_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_method = PaymentService.get_default_payment_method(account_id)

        if not payment_method:
            return Response(
                {'error': 'No default payment method found'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(PaymentMethodDetailSerializer(payment_method).data)

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """
        Get cards expiring soon.

        GET /api/v1/finance/payment-methods/expiring/?days_ahead=30
        """
        organization_id = self.get_organization_id(request)
        days_ahead = int(request.query_params.get('days_ahead', 30))

        payment_methods = PaymentService.check_expiring_cards(
            organization_id=organization_id,
            days_ahead=days_ahead
        )

        return Response({
            'payment_methods': PaymentMethodListSerializer(payment_methods, many=True).data,
            'count': len(payment_methods),
        })


class PaymentViewSet(viewsets.ViewSet):
    """
    ViewSet for payment processing.

    Provides payment and refund processing.
    """

    permission_classes = [IsAuthenticated]

    def get_organization_id(self, request):
        """Get organization ID from request."""
        return request.headers.get('X-Organization-ID') or request.user.organization_id

    @action(detail=False, methods=['post'])
    def process(self, request):
        """
        Process a payment.

        POST /api/v1/finance/payments/process/
        """
        serializer = ProcessPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            result = PaymentService.process_payment(
                organization_id=organization_id,
                **serializer.validated_data
            )

            return Response(result, status=status.HTTP_201_CREATED)
        except PaymentFailedError as e:
            return Response(
                {'error': str(e), 'success': False},
                status=status.HTTP_400_BAD_REQUEST
            )
        except PaymentGatewayError as e:
            return Response(
                {'error': str(e), 'success': False},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except PaymentServiceError as e:
            return Response(
                {'error': str(e), 'success': False},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def refund(self, request):
        """
        Process a refund.

        POST /api/v1/finance/payments/refund/
        """
        serializer = ProcessRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            result = PaymentService.process_refund(
                organization_id=organization_id,
                **serializer.validated_data
            )

            return Response(result, status=status.HTTP_201_CREATED)
        except PaymentFailedError as e:
            return Response(
                {'error': str(e), 'success': False},
                status=status.HTTP_400_BAD_REQUEST
            )
        except PaymentGatewayError as e:
            return Response(
                {'error': str(e), 'success': False},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except PaymentServiceError as e:
            return Response(
                {'error': str(e), 'success': False},
                status=status.HTTP_400_BAD_REQUEST
            )
