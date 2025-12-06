# services/simulator-service/src/apps/api/views/session_views.py
"""
FSTD Session ViewSet
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

from apps.core.models import FSTDSession
from apps.api.serializers import (
    FSTDSessionSerializer,
    FSTDSessionListSerializer,
)
from apps.api.serializers.session_serializers import (
    FSTDSessionCreateSerializer,
    SessionAssessmentSerializer,
    SessionSignatureSerializer,
)


class FSTDSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for FSTD Session management

    Endpoints:
    - GET /api/v1/sessions/ - List sessions
    - POST /api/v1/sessions/ - Create session
    - GET /api/v1/sessions/{id}/ - Get session details
    - PUT /api/v1/sessions/{id}/ - Update session
    - POST /api/v1/sessions/{id}/start/ - Start session
    - POST /api/v1/sessions/{id}/complete/ - Complete session
    - POST /api/v1/sessions/{id}/cancel/ - Cancel session
    - POST /api/v1/sessions/{id}/assess/ - Record assessment
    - POST /api/v1/sessions/{id}/sign/ - Sign session
    - GET /api/v1/sessions/trainee/{trainee_id}/ - Get trainee sessions
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['session_type', 'status', 'assessment_result', 'session_date', 'fstd_device_id']
    search_fields = ['trainee_name', 'instructor_name', 'fstd_device_name']
    ordering_fields = ['session_date', 'scheduled_start', 'created_at']
    ordering = ['-session_date', '-scheduled_start']

    def get_queryset(self):
        """Filter by organization"""
        queryset = FSTDSession.objects.all()

        organization_id = getattr(self.request, 'organization_id', None)
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        # Filter by trainee_id if provided
        trainee_id = self.request.query_params.get('trainee_id')
        if trainee_id:
            queryset = queryset.filter(trainee_id=trainee_id)

        # Filter by instructor_id if provided
        instructor_id = self.request.query_params.get('instructor_id')
        if instructor_id:
            queryset = queryset.filter(instructor_id=instructor_id)

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(session_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(session_date__lte=end_date)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return FSTDSessionListSerializer
        elif self.action == 'create':
            return FSTDSessionCreateSerializer
        return FSTDSessionSerializer

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a session"""
        session = self.get_object()

        if session.status not in ['scheduled', 'confirmed']:
            return Response(
                {'error': 'Session cannot be started from current status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        session.start_session(user_id=request.user.id if hasattr(request, 'user') else None)

        return Response({
            'status': 'success',
            'message': 'Session started',
            'started_at': session.actual_start.isoformat()
        })

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a session"""
        session = self.get_object()

        if session.status != 'in_progress':
            return Response(
                {'error': 'Session must be in progress to complete'},
                status=status.HTTP_400_BAD_REQUEST
            )

        session.complete_session(user_id=request.user.id if hasattr(request, 'user') else None)

        # Update device statistics
        from apps.core.models import FSTDevice
        try:
            device = FSTDevice.objects.get(id=session.fstd_device_id)
            device.update_statistics(float(session.duration_hours))
        except FSTDevice.DoesNotExist:
            pass

        return Response({
            'status': 'success',
            'message': 'Session completed',
            'duration_minutes': session.actual_duration_minutes,
            'duration_hours': str(session.duration_hours)
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a session"""
        session = self.get_object()

        if session.status in ['completed', 'cancelled']:
            return Response(
                {'error': 'Session cannot be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')
        session.cancel_session(
            reason=reason,
            user_id=request.user.id if hasattr(request, 'user') else None
        )

        return Response({
            'status': 'success',
            'message': 'Session cancelled'
        })

    @action(detail=True, methods=['post'])
    def assess(self, request, pk=None):
        """Record assessment for a session"""
        session = self.get_object()

        serializer = SessionAssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        session.assessment_result = data.get('assessment_result', session.assessment_result)
        session.grade = data.get('grade', session.grade)
        session.competency_grades = data.get('competency_grades', session.competency_grades)
        session.exercises_completed = data.get('exercises_completed', session.exercises_completed)
        session.instructor_remarks = data.get('instructor_remarks', session.instructor_remarks)
        session.areas_for_improvement = data.get('areas_for_improvement', session.areas_for_improvement)
        session.strengths = data.get('strengths', session.strengths)
        session.recommendations = data.get('recommendations', session.recommendations)
        session.updated_by = request.user.id if hasattr(request, 'user') else None
        session.save()

        return Response({
            'status': 'success',
            'message': 'Assessment recorded',
            'result': session.assessment_result
        })

    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        """Sign a session"""
        session = self.get_object()

        serializer = SessionSignatureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        signer_type = data['signer_type']
        signature_data = data['signature_data']

        user_id = request.user.id if hasattr(request, 'user') else None

        if signer_type == 'instructor':
            session.sign_instructor(signature_data, user_id)
        elif signer_type == 'trainee':
            session.sign_trainee(signature_data, user_id)
        elif signer_type == 'examiner':
            session.examiner_signature = signature_data
            session.examiner_signed_at = timezone.now()
            session.save()

        return Response({
            'status': 'success',
            'message': f'{signer_type.capitalize()} signature recorded',
            'is_fully_signed': session.is_signed
        })

    @action(detail=False, methods=['get'], url_path='trainee/(?P<trainee_id>[^/.]+)')
    def trainee_sessions(self, request, trainee_id=None):
        """Get all sessions for a trainee"""
        sessions = FSTDSession.get_trainee_sessions(
            trainee_id=trainee_id,
            organization_id=getattr(request, 'organization_id', None)
        )

        # Pagination
        page = self.paginate_queryset(sessions)
        if page is not None:
            serializer = FSTDSessionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = FSTDSessionListSerializer(sessions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='trainee/(?P<trainee_id>[^/.]+)/summary')
    def trainee_summary(self, request, trainee_id=None):
        """Get summary statistics for a trainee"""
        from django.db.models import Sum, Count

        organization_id = getattr(request, 'organization_id', None)

        # Get total hours
        total_hours = FSTDSession.get_trainee_total_hours(
            trainee_id=trainee_id,
            organization_id=organization_id
        )

        # Get session counts by type
        sessions = FSTDSession.objects.filter(
            trainee_id=trainee_id,
            status='completed'
        )
        if organization_id:
            sessions = sessions.filter(organization_id=organization_id)

        by_type = sessions.values('session_type').annotate(
            count=Count('id'),
            total_minutes=Sum('actual_duration_minutes')
        )

        # Get assessment results
        by_result = sessions.values('assessment_result').annotate(count=Count('id'))

        return Response({
            'trainee_id': trainee_id,
            'total_hours': str(total_hours),
            'total_sessions': sessions.count(),
            'by_session_type': list(by_type),
            'by_assessment_result': list(by_result),
        })

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's sessions"""
        today = timezone.now().date()
        sessions = self.get_queryset().filter(session_date=today)

        serializer = FSTDSessionListSerializer(sessions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming sessions"""
        today = timezone.now().date()
        days = int(request.query_params.get('days', 7))

        from datetime import timedelta
        end_date = today + timedelta(days=days)

        sessions = self.get_queryset().filter(
            session_date__gte=today,
            session_date__lte=end_date,
            status__in=['scheduled', 'confirmed']
        )

        serializer = FSTDSessionListSerializer(sessions, many=True)
        return Response(serializer.data)
