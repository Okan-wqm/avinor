# services/booking-service/src/apps/api/views/rule_views.py
"""
Booking Rule API Views

Views for managing booking rules and validation.
"""

import logging
from datetime import datetime
from decimal import Decimal

from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.models import BookingRule
from apps.core.services import RuleService, RuleViolationError
from apps.api.serializers import (
    BookingRuleSerializer,
    BookingRuleListSerializer,
    BookingRuleDetailSerializer,
    BookingRuleCreateSerializer,
    BookingRuleUpdateSerializer,
    RuleValidationRequestSerializer,
    RuleValidationResultSerializer,
    MergedRulesSerializer,
    CancellationFeeRequestSerializer,
    CancellationFeeSerializer,
)
from .pagination import StandardResultsSetPagination

logger = logging.getLogger(__name__)


class BookingRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for booking rule management.

    Manages booking rules for organizations, aircraft, instructors, etc.
    """

    queryset = BookingRule.objects.all()
    serializer_class = BookingRuleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rule_type', 'target_type', 'target_id', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['priority', 'created_at', 'name']
    ordering = ['-priority', 'name']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rule_service = RuleService()

    def get_queryset(self):
        """Filter queryset by organization."""
        queryset = super().get_queryset()
        organization_id = self.request.headers.get('X-Organization-ID')

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        # Filter by effectiveness
        effective_only = self.request.query_params.get('effective_only', 'false').lower() == 'true'
        if effective_only:
            today = timezone.now().date()
            queryset = queryset.filter(
                is_active=True
            ).filter(
                models.Q(effective_from__isnull=True) | models.Q(effective_from__lte=today)
            ).filter(
                models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=today)
            )

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return BookingRuleListSerializer
        elif self.action == 'retrieve':
            return BookingRuleDetailSerializer
        elif self.action == 'create':
            return BookingRuleCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return BookingRuleUpdateSerializer
        return BookingRuleSerializer

    def create(self, request, *args, **kwargs):
        """Create a new booking rule."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            rule = self.rule_service.create_rule(
                created_by=request.user.id if hasattr(request, 'user') else None,
                **serializer.validated_data
            )

            output_serializer = BookingRuleDetailSerializer(rule)
            return Response(
                output_serializer.data,
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a rule."""
        rule = self.get_object()
        rule.is_active = True
        rule.save()

        serializer = BookingRuleDetailSerializer(rule)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a rule."""
        rule = self.get_object()
        rule.is_active = False
        rule.save()

        serializer = BookingRuleDetailSerializer(rule)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a rule with a new name."""
        rule = self.get_object()
        new_name = request.data.get('name', f"{rule.name} (Copy)")

        # Create a copy of the rule
        rule.pk = None
        rule.id = None
        rule.name = new_name
        rule.save()

        serializer = BookingRuleDetailSerializer(rule)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def for_target(self, request):
        """Get rules applicable to a specific target."""
        organization_id = request.headers.get('X-Organization-ID')
        target_type = request.query_params.get('target_type')
        target_id = request.query_params.get('target_id')

        if not target_type:
            return Response(
                {'error': 'target_type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rules = self.rule_service.list_rules(
            organization_id=organization_id,
            target_id=target_id,
            active_only=True
        )

        serializer = BookingRuleListSerializer(rules, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def merged(self, request):
        """Get merged/effective rules for a booking context."""
        organization_id = request.headers.get('X-Organization-ID')
        aircraft_id = request.query_params.get('aircraft_id')
        instructor_id = request.query_params.get('instructor_id')
        student_id = request.query_params.get('student_id')
        location_id = request.query_params.get('location_id')
        booking_type = request.query_params.get('booking_type')

        if not organization_id:
            return Response(
                {'error': 'Organization ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        merged = self.rule_service.get_merged_rules(
            organization_id=organization_id,
            aircraft_id=aircraft_id,
            instructor_id=instructor_id,
            student_id=student_id,
            location_id=location_id,
            booking_type=booking_type
        )

        serializer = MergedRulesSerializer(merged)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_update_priority(self, request):
        """Update priorities for multiple rules at once."""
        updates = request.data.get('updates', [])

        if not updates:
            return Response(
                {'error': 'updates list is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated_count = 0
        errors = []

        for update in updates:
            rule_id = update.get('id')
            priority = update.get('priority')

            if not rule_id or priority is None:
                errors.append({'id': rule_id, 'error': 'id and priority required'})
                continue

            try:
                rule = BookingRule.objects.get(id=rule_id)
                rule.priority = priority
                rule.save()
                updated_count += 1
            except BookingRule.DoesNotExist:
                errors.append({'id': rule_id, 'error': 'Rule not found'})
            except Exception as e:
                errors.append({'id': rule_id, 'error': str(e)})

        return Response({
            'updated_count': updated_count,
            'errors': errors,
        })


class RuleValidationView(APIView):
    """View for validating bookings against rules."""

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rule_service = RuleService()

    def post(self, request):
        """Validate a booking against all applicable rules."""
        serializer = RuleValidationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        result = self.rule_service.validate_booking(
            organization_id=data['organization_id'],
            scheduled_start=data['scheduled_start'],
            scheduled_end=data['scheduled_end'],
            user_id=data['user_id'],
            aircraft_id=data.get('aircraft_id'),
            instructor_id=data.get('instructor_id'),
            student_id=data.get('student_id'),
            location_id=data.get('location_id'),
            booking_type=data.get('booking_type')
        )

        output_serializer = RuleValidationResultSerializer(result)
        return Response(output_serializer.data)


class CancellationFeeView(APIView):
    """View for calculating cancellation fees."""

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rule_service = RuleService()

    def post(self, request):
        """Calculate cancellation fee for a booking."""
        serializer = CancellationFeeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        result = self.rule_service.calculate_cancellation_fee(
            organization_id=data['organization_id'],
            hours_until_start=data['hours_until_start'],
            estimated_cost=data['estimated_cost'],
            aircraft_id=data.get('aircraft_id')
        )

        # Add user-friendly message
        if result['is_free']:
            result['message'] = 'Free cancellation - no fee applies'
        elif result['is_late']:
            result['message'] = f"Late cancellation - {result['fee_percent']}% fee applies"
        else:
            result['message'] = f"Cancellation fee: {result['fee']} NOK"

        output_serializer = CancellationFeeSerializer(result)
        return Response(output_serializer.data)

    def get(self, request):
        """Get cancellation fee for a specific booking."""
        booking_id = request.query_params.get('booking_id')

        if not booking_id:
            return Response(
                {'error': 'booking_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from apps.core.models import Booking
        from apps.core.services import BookingNotFoundError

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response(
                {'error': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        hours_until = booking.hours_until_start
        estimated_cost = booking.estimated_cost or Decimal('0.00')

        result = self.rule_service.calculate_cancellation_fee(
            organization_id=booking.organization_id,
            hours_until_start=hours_until,
            estimated_cost=estimated_cost,
            aircraft_id=booking.aircraft_id
        )

        result['booking_number'] = booking.booking_number
        result['scheduled_start'] = booking.scheduled_start.isoformat()
        result['hours_until_start'] = hours_until

        if result['is_free']:
            result['message'] = 'Free cancellation - no fee applies'
        elif result['is_late']:
            result['message'] = f"Late cancellation - {result['fee_percent']}% fee applies"

        output_serializer = CancellationFeeSerializer(result)
        return Response(output_serializer.data)


# Import at the end to avoid circular imports
from django.db import models
