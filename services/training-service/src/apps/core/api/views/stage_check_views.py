# services/training-service/src/apps/core/api/views/stage_check_views.py
"""
Stage Check Views

API ViewSet for stage check endpoints.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError

from ...models import StageCheck
from ...services import StageCheckService
from ..serializers.stage_check_serializers import (
    StageCheckSerializer,
    StageCheckCreateSerializer,
    StageCheckUpdateSerializer,
    StageCheckDetailSerializer,
    StageCheckListSerializer,
    ScheduleStageCheckSerializer,
    PassStageCheckSerializer,
    FailStageCheckSerializer,
    DeferStageCheckSerializer,
    CancelStageCheckSerializer,
    RemedialTrainingSerializer,
    CreateRecheckSerializer,
    VerifyPrerequisitesSerializer,
    OralTopicSerializer,
    FlightManeuverSerializer,
    StageCheckStatisticsSerializer,
)

logger = logging.getLogger(__name__)


class StageCheckViewSet(viewsets.ModelViewSet):
    """
    ViewSet for stage check CRUD and workflow.

    Endpoints:
    - GET /stage-checks/ - List stage checks
    - POST /stage-checks/ - Create stage check
    - GET /stage-checks/{id}/ - Get stage check details
    - PUT/PATCH /stage-checks/{id}/ - Update stage check
    - POST /stage-checks/{id}/schedule/ - Schedule stage check
    - POST /stage-checks/{id}/verify-prerequisites/ - Verify prerequisites
    - POST /stage-checks/{id}/start/ - Start stage check
    - POST /stage-checks/{id}/pass/ - Mark as passed
    - POST /stage-checks/{id}/fail/ - Mark as failed
    - POST /stage-checks/{id}/defer/ - Defer stage check
    - POST /stage-checks/{id}/cancel/ - Cancel stage check
    - POST /stage-checks/{id}/record-oral-topic/ - Record oral topic
    - POST /stage-checks/{id}/record-flight-maneuver/ - Record flight maneuver
    - POST /stage-checks/{id}/record-remedial-training/ - Record remedial training
    - POST /stage-checks/{id}/examiner-signoff/ - Examiner sign-off
    - POST /stage-checks/{id}/student-signoff/ - Student sign-off
    - POST /stage-checks/{id}/create-recheck/ - Create recheck
    - GET /stage-checks/statistics/ - Get stage check statistics
    """

    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        """Get queryset filtered by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        return StageCheck.objects.filter(
            organization_id=organization_id
        ).select_related('enrollment')

    def get_serializer_class(self):
        """Get appropriate serializer based on action."""
        if self.action == 'create':
            return StageCheckCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return StageCheckUpdateSerializer
        elif self.action == 'list':
            return StageCheckListSerializer
        elif self.action == 'retrieve':
            return StageCheckDetailSerializer
        return StageCheckSerializer

    def list(self, request):
        """List stage checks with filters."""
        organization_id = request.headers.get('X-Organization-ID')

        enrollment_id = request.query_params.get('enrollment_id')
        examiner_id = request.query_params.get('examiner_id')
        stage_id = request.query_params.get('stage_id')
        status_filter = request.query_params.get('status')
        result = request.query_params.get('result')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        stage_checks, total = StageCheckService.list_stage_checks(
            organization_id=organization_id,
            enrollment_id=enrollment_id,
            examiner_id=examiner_id,
            stage_id=stage_id,
            status=status_filter,
            result=result,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size
        )

        serializer = self.get_serializer(stage_checks, many=True)

        return Response({
            'results': serializer.data,
            'total': total,
            'page': page,
            'page_size': page_size,
        })

    def create(self, request):
        """Create a new stage check."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stage_check = StageCheckService.create_stage_check(
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = StageCheckDetailSerializer(stage_check)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, id=None):
        """Update a stage check."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stage_check = StageCheckService.update_stage_check(
                check_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = StageCheckDetailSerializer(stage_check)
            return Response(response_serializer.data)

        except StageCheck.DoesNotExist:
            return Response(
                {'error': 'Stage check not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def schedule(self, request, id=None):
        """Schedule a stage check."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = ScheduleStageCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stage_check = StageCheckService.schedule_stage_check(
                check_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = StageCheckDetailSerializer(stage_check)
            return Response(response_serializer.data)

        except StageCheck.DoesNotExist:
            return Response(
                {'error': 'Stage check not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], url_path='verify-prerequisites')
    def verify_prerequisites(self, request, id=None):
        """Verify prerequisites for stage check."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = VerifyPrerequisitesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = StageCheckService.verify_prerequisites(
                check_id=id,
                organization_id=organization_id,
                notes=serializer.validated_data.get('notes')
            )

            return Response(result)

        except StageCheck.DoesNotExist:
            return Response(
                {'error': 'Stage check not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def start(self, request, id=None):
        """Start a stage check."""
        organization_id = request.headers.get('X-Organization-ID')
        examiner_id = request.data.get('examiner_id')

        try:
            stage_check = StageCheckService.start_stage_check(
                check_id=id,
                organization_id=organization_id,
                examiner_id=examiner_id
            )

            response_serializer = StageCheckDetailSerializer(stage_check)
            return Response(response_serializer.data)

        except StageCheck.DoesNotExist:
            return Response(
                {'error': 'Stage check not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='pass')
    def pass_check(self, request, id=None):
        """Mark stage check as passed."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = PassStageCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stage_check = StageCheckService.pass_stage_check(
                check_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = StageCheckDetailSerializer(stage_check)
            return Response(response_serializer.data)

        except StageCheck.DoesNotExist:
            return Response(
                {'error': 'Stage check not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='fail')
    def fail_check(self, request, id=None):
        """Mark stage check as failed."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = FailStageCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stage_check = StageCheckService.fail_stage_check(
                check_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = StageCheckDetailSerializer(stage_check)
            return Response(response_serializer.data)

        except StageCheck.DoesNotExist:
            return Response(
                {'error': 'Stage check not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def defer(self, request, id=None):
        """Defer stage check."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = DeferStageCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stage_check = StageCheckService.defer_stage_check(
                check_id=id,
                organization_id=organization_id,
                reason=serializer.validated_data['reason']
            )

            response_serializer = StageCheckDetailSerializer(stage_check)
            return Response(response_serializer.data)

        except StageCheck.DoesNotExist:
            return Response(
                {'error': 'Stage check not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, id=None):
        """Cancel stage check."""
        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        serializer = CancelStageCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stage_check = StageCheckService.cancel_stage_check(
                check_id=id,
                organization_id=organization_id,
                reason=serializer.validated_data['reason'],
                cancelled_by=user_id
            )

            response_serializer = StageCheckDetailSerializer(stage_check)
            return Response(response_serializer.data)

        except StageCheck.DoesNotExist:
            return Response(
                {'error': 'Stage check not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='record-oral-topic')
    def record_oral_topic(self, request, id=None):
        """Record oral examination topic."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = OralTopicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stage_check = StageCheckService.record_oral_topic(
                check_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = StageCheckDetailSerializer(stage_check)
            return Response(response_serializer.data)

        except StageCheck.DoesNotExist:
            return Response(
                {'error': 'Stage check not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='record-flight-maneuver')
    def record_flight_maneuver(self, request, id=None):
        """Record flight maneuver result."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = FlightManeuverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stage_check = StageCheckService.record_flight_maneuver(
                check_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = StageCheckDetailSerializer(stage_check)
            return Response(response_serializer.data)

        except StageCheck.DoesNotExist:
            return Response(
                {'error': 'Stage check not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='record-remedial-training')
    def record_remedial_training(self, request, id=None):
        """Record remedial training."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = RemedialTrainingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stage_check = StageCheckService.record_remedial_training(
                check_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = StageCheckDetailSerializer(stage_check)
            return Response(response_serializer.data)

        except StageCheck.DoesNotExist:
            return Response(
                {'error': 'Stage check not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='examiner-signoff')
    def examiner_signoff(self, request, id=None):
        """Examiner sign-off."""
        organization_id = request.headers.get('X-Organization-ID')
        examiner_id = request.user.id

        try:
            stage_check = StageCheckService.examiner_signoff(
                check_id=id,
                organization_id=organization_id,
                examiner_id=examiner_id
            )

            response_serializer = StageCheckDetailSerializer(stage_check)
            return Response(response_serializer.data)

        except StageCheck.DoesNotExist:
            return Response(
                {'error': 'Stage check not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='student-signoff')
    def student_signoff(self, request, id=None):
        """Student sign-off."""
        organization_id = request.headers.get('X-Organization-ID')
        student_id = request.user.id

        try:
            stage_check = StageCheckService.student_signoff(
                check_id=id,
                organization_id=organization_id,
                student_id=student_id
            )

            response_serializer = StageCheckDetailSerializer(stage_check)
            return Response(response_serializer.data)

        except StageCheck.DoesNotExist:
            return Response(
                {'error': 'Stage check not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='create-recheck')
    def create_recheck(self, request, id=None):
        """Create a recheck for failed stage check."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = CreateRecheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            recheck = StageCheckService.create_recheck(
                check_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = StageCheckDetailSerializer(recheck)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except StageCheck.DoesNotExist:
            return Response(
                {'error': 'Stage check not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get stage check statistics."""
        organization_id = request.headers.get('X-Organization-ID')

        program_id = request.query_params.get('program_id')
        examiner_id = request.query_params.get('examiner_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        stats = StageCheckService.get_stage_check_statistics(
            organization_id=organization_id,
            program_id=program_id,
            examiner_id=examiner_id,
            date_from=date_from,
            date_to=date_to
        )

        return Response(stats)
