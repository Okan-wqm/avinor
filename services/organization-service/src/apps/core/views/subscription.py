# services/organization-service/src/apps/core/views/subscription.py
"""
Subscription ViewSets

REST API endpoints for subscription and plan management.
"""

import logging
from typing import Any

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import transaction

from apps.core.models import SubscriptionPlan, SubscriptionHistory
from apps.core.serializers import (
    SubscriptionPlanSerializer,
    SubscriptionPlanListSerializer,
    SubscriptionStatusSerializer,
    SubscriptionChangeSerializer,
    SubscriptionCancelSerializer,
    SubscriptionHistorySerializer,
)
from apps.core.services import (
    SubscriptionService,
    SubscriptionError,
)

logger = logging.getLogger(__name__)


class SubscriptionPlanViewSet(viewsets.ViewSet):
    """
    ViewSet for Subscription Plans (mostly read-only for end users).

    Endpoints:
    - GET /subscription-plans/ - List available plans
    - GET /subscription-plans/{id}/ - Get plan details
    - GET /subscription-plans/compare/ - Compare plans
    """

    permission_classes = [AllowAny]  # Plans are public

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.subscription_service = SubscriptionService()

    def list(self, request: Request) -> Response:
        """List all available subscription plans."""
        queryset = SubscriptionPlan.objects.filter(
            is_active=True
        ).order_by('display_order', 'price_monthly')

        # Filter by public visibility
        is_public = request.query_params.get('public_only', 'true')
        if is_public.lower() == 'true':
            queryset = queryset.filter(is_public=True)

        serializer = SubscriptionPlanListSerializer(queryset, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data,
            'count': queryset.count(),
        })

    def retrieve(self, request: Request, pk: str = None) -> Response:
        """Get subscription plan details."""
        try:
            plan = SubscriptionPlan.objects.get(id=pk, is_active=True)
            serializer = SubscriptionPlanSerializer(plan)
            return Response({
                'status': 'success',
                'data': serializer.data,
            })

        except SubscriptionPlan.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Subscription plan not found',
                'code': 'NOT_FOUND',
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='by-code/(?P<code>[^/.]+)')
    def get_by_code(self, request: Request, code: str = None) -> Response:
        """Get subscription plan by code."""
        try:
            plan = SubscriptionPlan.objects.get(code=code, is_active=True)
            serializer = SubscriptionPlanSerializer(plan)
            return Response({
                'status': 'success',
                'data': serializer.data,
            })

        except SubscriptionPlan.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Subscription plan not found',
                'code': 'NOT_FOUND',
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='compare')
    def compare(self, request: Request) -> Response:
        """Compare subscription plans features and limits."""
        plans = SubscriptionPlan.objects.filter(
            is_active=True,
            is_public=True
        ).order_by('display_order')

        comparison = {
            'plans': [],
            'features': set(),
            'limits': ['max_users', 'max_aircraft', 'max_students', 'max_locations', 'storage_limit_gb'],
        }

        for plan in plans:
            plan_data = {
                'id': str(plan.id),
                'code': plan.code,
                'name': plan.name,
                'description': plan.description,
                'price_monthly': str(plan.price_monthly),
                'price_yearly': str(plan.price_yearly),
                'yearly_discount_percent': str(plan.yearly_discount_percent),
                'limits': {
                    'max_users': plan.max_users,
                    'max_aircraft': plan.max_aircraft,
                    'max_students': plan.max_students,
                    'max_locations': plan.max_locations,
                    'storage_limit_gb': plan.storage_limit_gb,
                },
                'features': plan.features,
                'badge_text': plan.badge_text,
                'badge_color': plan.badge_color,
            }
            comparison['plans'].append(plan_data)

            # Collect all features
            if plan.features:
                comparison['features'].update(plan.features.keys())

        comparison['features'] = sorted(list(comparison['features']))

        return Response({
            'status': 'success',
            'data': comparison,
        })


class SubscriptionViewSet(viewsets.ViewSet):
    """
    ViewSet for Organization Subscription management.

    Endpoints:
    - GET /organizations/{org_id}/subscription/ - Get subscription status
    - POST /organizations/{org_id}/subscription/change/ - Change plan
    - POST /organizations/{org_id}/subscription/cancel/ - Cancel subscription
    - POST /organizations/{org_id}/subscription/reactivate/ - Reactivate
    - GET /organizations/{org_id}/subscription/history/ - Get history
    - GET /organizations/{org_id}/subscription/limits/ - Get usage limits
    - POST /organizations/{org_id}/subscription/start-trial/ - Start trial
    - POST /organizations/{org_id}/subscription/extend-trial/ - Extend trial
    """

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.subscription_service = SubscriptionService()

    def retrieve(self, request: Request, organization_pk: str = None) -> Response:
        """Get current subscription status."""
        try:
            status_data = self.subscription_service.get_subscription_status(
                organization_pk
            )

            serializer = SubscriptionStatusSerializer(data=status_data)
            serializer.is_valid()

            return Response({
                'status': 'success',
                'data': status_data,
            })

        except SubscriptionError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'SUBSCRIPTION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='change')
    def change_plan(self, request: Request, organization_pk: str = None) -> Response:
        """Change subscription plan."""
        serializer = SubscriptionChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                result = self.subscription_service.change_plan(
                    organization_id=organization_pk,
                    plan_code=serializer.validated_data['plan_code'],
                    billing_cycle=serializer.validated_data.get('billing_cycle', 'monthly'),
                    changed_by_user_id=request.user.id,
                    payment_reference=serializer.validated_data.get('payment_reference')
                )

            return Response({
                'status': 'success',
                'message': 'Subscription plan changed successfully',
                'data': result,
            })

        except SubscriptionError as e:
            logger.warning(f"Subscription change failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'SUBSCRIPTION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='cancel')
    def cancel(self, request: Request, organization_pk: str = None) -> Response:
        """Cancel subscription."""
        serializer = SubscriptionCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                result = self.subscription_service.cancel_subscription(
                    organization_id=organization_pk,
                    reason=serializer.validated_data.get('reason', ''),
                    end_immediately=serializer.validated_data.get('end_immediately', False),
                    cancelled_by_user_id=request.user.id
                )

            return Response({
                'status': 'success',
                'message': 'Subscription cancelled',
                'data': result,
            })

        except SubscriptionError as e:
            logger.warning(f"Subscription cancellation failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'SUBSCRIPTION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='reactivate')
    def reactivate(self, request: Request, organization_pk: str = None) -> Response:
        """Reactivate cancelled subscription."""
        try:
            with transaction.atomic():
                result = self.subscription_service.reactivate_subscription(
                    organization_id=organization_pk,
                    reactivated_by_user_id=request.user.id
                )

            return Response({
                'status': 'success',
                'message': 'Subscription reactivated',
                'data': result,
            })

        except SubscriptionError as e:
            logger.warning(f"Subscription reactivation failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'SUBSCRIPTION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='history')
    def history(self, request: Request, organization_pk: str = None) -> Response:
        """Get subscription history."""
        history = SubscriptionHistory.objects.filter(
            organization_id=organization_pk
        ).select_related(
            'from_plan', 'to_plan'
        ).order_by('-created_at')

        # Limit results
        limit = int(request.query_params.get('limit', 50))
        history = history[:limit]

        serializer = SubscriptionHistorySerializer(history, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data,
            'count': len(serializer.data),
        })

    @action(detail=False, methods=['get'], url_path='limits')
    def get_limits(self, request: Request, organization_pk: str = None) -> Response:
        """Get current usage limits."""
        try:
            limits = self.subscription_service.get_subscription_limits(
                organization_pk
            )

            return Response({
                'status': 'success',
                'data': limits,
            })

        except SubscriptionError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'SUBSCRIPTION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='start-trial')
    def start_trial(self, request: Request, organization_pk: str = None) -> Response:
        """Start a trial period."""
        plan_code = request.data.get('plan_code')
        trial_days = request.data.get('trial_days', 14)

        if not plan_code:
            return Response({
                'status': 'error',
                'message': 'Plan code is required',
                'code': 'VALIDATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                result = self.subscription_service.start_trial(
                    organization_id=organization_pk,
                    plan_code=plan_code,
                    trial_days=trial_days
                )

            return Response({
                'status': 'success',
                'message': f'Trial started for {trial_days} days',
                'data': result,
            })

        except SubscriptionError as e:
            logger.warning(f"Trial start failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'SUBSCRIPTION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='extend-trial')
    def extend_trial(self, request: Request, organization_pk: str = None) -> Response:
        """Extend trial period."""
        days = request.data.get('days', 7)

        try:
            with transaction.atomic():
                result = self.subscription_service.extend_trial(
                    organization_id=organization_pk,
                    days=days
                )

            return Response({
                'status': 'success',
                'message': f'Trial extended by {days} days',
                'data': result,
            })

        except SubscriptionError as e:
            logger.warning(f"Trial extension failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'SUBSCRIPTION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='convert-trial')
    def convert_trial(self, request: Request, organization_pk: str = None) -> Response:
        """Convert trial to paid subscription."""
        billing_cycle = request.data.get('billing_cycle', 'monthly')
        payment_reference = request.data.get('payment_reference')

        try:
            with transaction.atomic():
                result = self.subscription_service.convert_trial_to_paid(
                    organization_id=organization_pk,
                    billing_cycle=billing_cycle,
                    payment_reference=payment_reference,
                    converted_by_user_id=request.user.id
                )

            return Response({
                'status': 'success',
                'message': 'Trial converted to paid subscription',
                'data': result,
            })

        except SubscriptionError as e:
            logger.warning(f"Trial conversion failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'SUBSCRIPTION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='can-upgrade/(?P<plan_code>[^/.]+)')
    def can_upgrade(self, request: Request, organization_pk: str = None, plan_code: str = None) -> Response:
        """Check if organization can upgrade to a specific plan."""
        try:
            result = self.subscription_service.can_change_to_plan(
                organization_id=organization_pk,
                plan_code=plan_code
            )

            return Response({
                'status': 'success',
                'data': result,
            })

        except SubscriptionError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'SUBSCRIPTION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='check-limit/(?P<resource>[^/.]+)')
    def check_limit(
        self, request: Request, organization_pk: str = None, resource: str = None
    ) -> Response:
        """Check if a specific resource limit allows adding more."""
        try:
            can_add = self.subscription_service.check_limit(
                organization_id=organization_pk,
                resource=resource
            )

            return Response({
                'status': 'success',
                'data': {
                    'resource': resource,
                    'can_add': can_add,
                },
            })

        except SubscriptionError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'SUBSCRIPTION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)
