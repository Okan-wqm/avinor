# services/certificate-service/src/apps/core/api/views/ftl_views.py
"""
Flight Time Limitations (FTL) API Views
"""

from uuid import UUID
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from ...models import (
    FTLConfiguration,
    DutyPeriod,
    RestPeriod,
    FTLViolation,
    PilotFTLSummary,
)
from ...services import FTLService
from ..serializers import (
    FTLConfigurationSerializer,
    DutyPeriodSerializer,
    DutyPeriodStartSerializer,
    DutyPeriodEndSerializer,
    RestPeriodSerializer,
    RestPeriodCreateSerializer,
    FTLViolationSerializer,
    FTLViolationResolveSerializer,
    PilotFTLSummarySerializer,
    FTLPlanValidationSerializer,
)


class FTLConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for FTL Configuration management.

    Endpoints:
    - GET /api/v1/ftl/configuration/ - Get config
    - PUT /api/v1/ftl/configuration/ - Update config
    """

    queryset = FTLConfiguration.objects.all()
    serializer_class = FTLConfigurationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by organization."""
        org_id = self.request.headers.get('X-Organization-ID')
        if org_id:
            return FTLConfiguration.objects.filter(organization_id=org_id)
        return FTLConfiguration.objects.none()

    def list(self, request, *args, **kwargs):
        """Get organization's FTL configuration."""
        org_id = UUID(request.headers.get('X-Organization-ID'))
        config = FTLService.get_or_create_config(org_id)
        serializer = self.get_serializer(config)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """Update FTL configuration."""
        org_id = UUID(request.headers.get('X-Organization-ID'))
        config = FTLService.update_config(org_id, **request.data)
        serializer = self.get_serializer(config)
        return Response(serializer.data)


class DutyPeriodViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Duty Period management.

    Endpoints:
    - GET /api/v1/ftl/duty-periods/ - List duty periods
    - POST /api/v1/ftl/duty-periods/start/ - Start duty
    - POST /api/v1/ftl/duty-periods/{id}/end/ - End duty
    - GET /api/v1/ftl/duty-periods/active/ - Get active duty
    """

    queryset = DutyPeriod.objects.all()
    serializer_class = DutyPeriodSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by organization and user."""
        queryset = super().get_queryset()
        org_id = self.request.headers.get('X-Organization-ID')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset.order_by('-start_time')

    @action(detail=False, methods=['post'])
    def start(self, request):
        """Start a new duty period."""
        serializer = DutyPeriodStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        org_id = UUID(request.headers.get('X-Organization-ID'))
        user_id = UUID(request.data.get('user_id'))

        result = FTLService.start_duty_period(
            organization_id=org_id,
            user_id=user_id,
            **serializer.validated_data
        )

        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """End a duty period."""
        serializer = DutyPeriodEndSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = FTLService.end_duty_period(
            duty_id=UUID(pk),
            **serializer.validated_data
        )

        return Response(result)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active (uncompleted) duty period for user."""
        org_id = UUID(request.headers.get('X-Organization-ID'))
        user_id = UUID(request.query_params.get('user_id'))

        duty = DutyPeriod.objects.filter(
            organization_id=org_id,
            user_id=user_id,
            is_completed=False
        ).first()

        if duty:
            serializer = self.get_serializer(duty)
            return Response(serializer.data)

        return Response({'detail': 'No active duty period'}, status=status.HTTP_404_NOT_FOUND)


class RestPeriodViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Rest Period management.

    Endpoints:
    - GET /api/v1/ftl/rest-periods/ - List rest periods
    - POST /api/v1/ftl/rest-periods/ - Record rest
    """

    queryset = RestPeriod.objects.all()
    serializer_class = RestPeriodSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by organization and user."""
        queryset = super().get_queryset()
        org_id = self.request.headers.get('X-Organization-ID')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset.order_by('-start_time')

    def create(self, request, *args, **kwargs):
        """Record a rest period."""
        serializer = RestPeriodCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        org_id = UUID(request.headers.get('X-Organization-ID'))
        user_id = UUID(request.data.get('user_id'))

        result = FTLService.record_rest_period(
            organization_id=org_id,
            user_id=user_id,
            **serializer.validated_data
        )

        return Response(result, status=status.HTTP_201_CREATED)


class FTLViolationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for FTL Violations (read-only with resolve action).

    Endpoints:
    - GET /api/v1/ftl/violations/ - List violations
    - GET /api/v1/ftl/violations/{id}/ - Get violation
    - POST /api/v1/ftl/violations/{id}/resolve/ - Resolve violation
    """

    queryset = FTLViolation.objects.all()
    serializer_class = FTLViolationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by organization and user."""
        queryset = super().get_queryset()
        org_id = self.request.headers.get('X-Organization-ID')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        is_resolved = self.request.query_params.get('is_resolved')
        if is_resolved is not None:
            queryset = queryset.filter(is_resolved=is_resolved.lower() == 'true')

        return queryset.order_by('-violation_date')

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an FTL violation."""
        serializer = FTLViolationResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        violation = self.get_object()
        violation.resolve(
            resolved_by=request.user.id,
            notes=serializer.validated_data.get('resolution_notes')
        )

        if serializer.validated_data.get('commander_discretion'):
            violation.commander_discretion = True
            violation.discretion_reason = serializer.validated_data.get('discretion_reason')
            violation.save()

        return Response(self.get_serializer(violation).data)


class PilotFTLStatusView(APIView):
    """
    API View for Pilot FTL Status.

    Endpoints:
    - GET /api/v1/ftl/pilot-status/ - Get pilot FTL status
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get comprehensive FTL status for a pilot."""
        org_id = UUID(request.headers.get('X-Organization-ID'))
        user_id = UUID(request.query_params.get('user_id'))

        result = FTLService.get_pilot_ftl_status(
            organization_id=org_id,
            user_id=user_id
        )

        return Response(result)


class FTLComplianceCheckView(APIView):
    """
    API View for FTL Compliance Checking.

    Endpoints:
    - GET /api/v1/ftl/compliance-check/ - Check cumulative limits
    - POST /api/v1/ftl/validate-plan/ - Validate planned duty
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Check cumulative FTL limits."""
        org_id = UUID(request.headers.get('X-Organization-ID'))
        user_id = UUID(request.query_params.get('user_id'))

        result = FTLService.check_cumulative_limits(
            organization_id=org_id,
            user_id=user_id
        )

        return Response(result)


class FTLPlanValidationView(APIView):
    """
    API View for validating planned duty.

    Endpoints:
    - POST /api/v1/ftl/validate-plan/ - Validate planned duty
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Validate a planned duty period."""
        serializer = FTLPlanValidationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        org_id = UUID(request.headers.get('X-Organization-ID'))
        user_id = UUID(request.data.get('user_id'))

        result = FTLService.validate_planned_duty(
            organization_id=org_id,
            user_id=user_id,
            **serializer.validated_data
        )

        return Response(result)


class FTLRestCheckView(APIView):
    """
    API View for checking rest requirements.

    Endpoints:
    - GET /api/v1/ftl/rest-check/ - Check rest requirements
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Check rest requirements compliance."""
        org_id = UUID(request.headers.get('X-Organization-ID'))
        user_id = UUID(request.query_params.get('user_id'))

        result = FTLService.check_rest_requirements(
            organization_id=org_id,
            user_id=user_id
        )

        return Response(result)
