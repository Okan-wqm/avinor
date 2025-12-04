# services/finance-service/src/apps/core/api/views/pricing_views.py
"""
Pricing Views

DRF viewset for pricing rule management.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models.pricing import PricingRule
from ...services.pricing_service import (
    PricingService,
    PricingServiceError,
    PricingRuleNotFoundError,
)
from ..serializers.pricing_serializers import (
    PricingRuleSerializer,
    PricingRuleListSerializer,
    PricingRuleDetailSerializer,
    PricingRuleCreateSerializer,
    PricingRuleUpdateSerializer,
    CalculatePriceSerializer,
    CalculateFlightPriceSerializer,
    PriceCalculationResultSerializer,
    FlightPriceResultSerializer,
    DuplicatePricingRuleSerializer,
)

logger = logging.getLogger(__name__)


class PricingRuleViewSet(viewsets.ViewSet):
    """
    ViewSet for managing pricing rules.

    Provides pricing rule CRUD and price calculations.
    """

    permission_classes = [IsAuthenticated]

    def get_organization_id(self, request):
        """Get organization ID from request."""
        return request.headers.get('X-Organization-ID') or request.user.organization_id

    def list(self, request):
        """
        List pricing rules with filtering.

        GET /api/v1/finance/pricing-rules/
        """
        organization_id = self.get_organization_id(request)

        result = PricingService.list_pricing_rules(
            organization_id=organization_id,
            pricing_type=request.query_params.get('pricing_type'),
            target_id=request.query_params.get('target_id'),
            is_active=request.query_params.get('is_active'),
            effective_on=request.query_params.get('effective_on'),
            search=request.query_params.get('search'),
            order_by=request.query_params.get('order_by', '-priority'),
            limit=int(request.query_params.get('limit', 50)),
            offset=int(request.query_params.get('offset', 0)),
        )

        return Response(result)

    def retrieve(self, request, pk=None):
        """
        Get pricing rule details.

        GET /api/v1/finance/pricing-rules/{id}/
        """
        try:
            organization_id = self.get_organization_id(request)
            rule = PricingService.get_pricing_rule(pk, organization_id)
            serializer = PricingRuleDetailSerializer(rule)
            return Response(serializer.data)
        except PricingRuleNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    def create(self, request):
        """
        Create a new pricing rule.

        POST /api/v1/finance/pricing-rules/
        """
        serializer = PricingRuleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            rule = PricingService.create_pricing_rule(
                organization_id=organization_id,
                created_by=request.user.id,
                **serializer.validated_data
            )

            return Response(
                PricingRuleDetailSerializer(rule).data,
                status=status.HTTP_201_CREATED
            )
        except PricingServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def partial_update(self, request, pk=None):
        """
        Update pricing rule.

        PATCH /api/v1/finance/pricing-rules/{id}/
        """
        serializer = PricingRuleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            rule = PricingService.update_pricing_rule(
                rule_id=pk,
                organization_id=organization_id,
                updated_by=request.user.id,
                **serializer.validated_data
            )

            return Response(PricingRuleDetailSerializer(rule).data)
        except PricingRuleNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PricingServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, pk=None):
        """
        Delete (deactivate) pricing rule.

        DELETE /api/v1/finance/pricing-rules/{id}/
        """
        organization_id = self.get_organization_id(request)

        try:
            PricingService.delete_pricing_rule(pk, organization_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PricingRuleNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Duplicate a pricing rule.

        POST /api/v1/finance/pricing-rules/{id}/duplicate/
        """
        serializer = DuplicatePricingRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            rule = PricingService.duplicate_pricing_rule(
                rule_id=pk,
                new_name=serializer.validated_data.get('new_name'),
                organization_id=organization_id,
                created_by=request.user.id
            )

            return Response(
                PricingRuleDetailSerializer(rule).data,
                status=status.HTTP_201_CREATED
            )
        except PricingRuleNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """
        Calculate price using pricing rules.

        POST /api/v1/finance/pricing-rules/calculate/
        """
        serializer = CalculatePriceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            result = PricingService.calculate_price(
                organization_id=organization_id,
                **serializer.validated_data
            )

            return Response(result)
        except PricingRuleNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PricingServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def calculate_flight(self, request):
        """
        Calculate complete flight price.

        POST /api/v1/finance/pricing-rules/calculate_flight/
        """
        serializer = CalculateFlightPriceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            result = PricingService.calculate_flight_price(
                organization_id=organization_id,
                **serializer.validated_data
            )

            return Response(result)
        except PricingRuleNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PricingServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def applicable(self, request):
        """
        Get applicable pricing rule for a type and target.

        GET /api/v1/finance/pricing-rules/applicable/?pricing_type=aircraft&target_id=...
        """
        organization_id = self.get_organization_id(request)
        pricing_type = request.query_params.get('pricing_type')
        target_id = request.query_params.get('target_id')
        effective_date = request.query_params.get('effective_date')

        if not pricing_type:
            return Response(
                {'error': 'pricing_type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rule = PricingService.get_applicable_rule(
            organization_id=organization_id,
            pricing_type=pricing_type,
            target_id=target_id,
            effective_date=effective_date
        )

        if not rule:
            return Response(
                {'error': 'No applicable pricing rule found'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(PricingRuleDetailSerializer(rule).data)
