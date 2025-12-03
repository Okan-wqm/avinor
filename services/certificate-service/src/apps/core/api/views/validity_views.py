# services/certificate-service/src/apps/core/api/views/validity_views.py
"""
Validity ViewSet

API endpoints for comprehensive validity checking.
"""

import logging
from uuid import UUID

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...services import ValidityService
from ..serializers import (
    ValidityCheckSerializer,
    ValidityCheckResponseSerializer,
    UserSummarySerializer,
    FlightValidityCheckSerializer,
    FlightValidityResponseSerializer,
    ExpirationAlertSerializer,
    OrganizationComplianceSerializer,
    StudentProgressSerializer,
    InstructorValiditySerializer,
)

logger = logging.getLogger(__name__)


class ValidityViewSet(viewsets.ViewSet):
    """
    ViewSet for comprehensive validity checking.

    Provides endpoints for:
    - Pre-flight validity checks
    - Pilot compliance summary
    - Organization-wide compliance reports
    - Expiration alerts

    Endpoints:
    - POST /validity/check/ - Check user validity
    - POST /validity/pre-flight/ - Pre-flight check
    - GET /validity/summary/{user_id}/ - User summary
    - GET /validity/compliance/ - Organization compliance
    - GET /validity/alerts/ - Expiration alerts
    - GET /validity/student/{student_id}/ - Student progress
    - GET /validity/instructor/{instructor_id}/ - Instructor validity
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def check(self, request):
        """
        Comprehensive validity check for a user.

        POST /validity/check/
        {
            "user_id": "uuid",
            "operation_type": "vfr_day",
            "aircraft_type": "C172",
            "check_currency": true,
            "check_medical": true,
            "check_ratings": true,
            "check_endorsements": true
        }
        """
        serializer = ValidityCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = ValidityService()
        result = service.check_validity(
            user_id=serializer.validated_data['user_id'],
            operation_type=serializer.validated_data.get('operation_type'),
            aircraft_type=serializer.validated_data.get('aircraft_type'),
            aircraft_icao=serializer.validated_data.get('aircraft_icao'),
            check_currency=serializer.validated_data.get('check_currency', True),
            check_medical=serializer.validated_data.get('check_medical', True),
            check_ratings=serializer.validated_data.get('check_ratings', True),
            check_endorsements=serializer.validated_data.get('check_endorsements', True)
        )

        return Response(result)

    @action(detail=False, methods=['post'], url_path='pre-flight')
    def pre_flight(self, request):
        """
        Pre-flight validity check.

        POST /validity/pre-flight/
        {
            "user_id": "uuid",
            "flight_date": "2024-01-15",
            "flight_type": "vfr_day",
            "aircraft_type": "C172",
            "role": "pic",
            "is_night": false,
            "carrying_passengers": true
        }
        """
        serializer = FlightValidityCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = ValidityService()
        result = service.pre_flight_check(
            **serializer.validated_data
        )

        return Response(result)

    @action(detail=False, methods=['get'], url_path='summary/(?P<user_id>[^/.]+)')
    def user_summary(self, request, user_id=None):
        """
        Get comprehensive certification summary for a user.

        GET /validity/summary/{user_id}/
        """
        service = ValidityService()
        summary = service.get_user_summary(user_id=UUID(user_id))

        return Response(summary)

    @action(detail=False, methods=['get'])
    def compliance(self, request):
        """
        Get organization-wide compliance report.

        GET /validity/compliance/
        """
        organization_id = request.headers.get('X-Organization-ID')

        if not organization_id:
            return Response(
                {'detail': 'Organization ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = ValidityService()
        report = service.get_organization_compliance(
            organization_id=UUID(organization_id)
        )

        return Response(report)

    @action(detail=False, methods=['get'])
    def alerts(self, request):
        """
        Get expiration alerts.

        GET /validity/alerts/?days=30&severity=warning
        """
        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.query_params.get('user_id')
        days = int(request.query_params.get('days', 30))
        severity = request.query_params.get('severity')

        service = ValidityService()
        alerts = service.get_expiration_alerts(
            organization_id=UUID(organization_id) if organization_id else None,
            user_id=UUID(user_id) if user_id else None,
            days_ahead=days,
            severity=severity
        )

        serializer = ExpirationAlertSerializer(alerts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='student/(?P<student_id>[^/.]+)')
    def student_progress(self, request, student_id=None):
        """
        Get student pilot progress summary.

        GET /validity/student/{student_id}/
        """
        service = ValidityService()
        progress = service.get_student_progress(student_id=UUID(student_id))

        return Response(progress)

    @action(detail=False, methods=['get'], url_path='instructor/(?P<instructor_id>[^/.]+)')
    def instructor_validity(self, request, instructor_id=None):
        """
        Get instructor validity check.

        GET /validity/instructor/{instructor_id}/
        """
        service = ValidityService()
        validity = service.check_instructor_validity(
            instructor_id=UUID(instructor_id)
        )

        return Response(validity)

    @action(detail=False, methods=['get'], url_path='flight-privileges/(?P<user_id>[^/.]+)')
    def flight_privileges(self, request, user_id=None):
        """
        Get flight privileges for a user.

        GET /validity/flight-privileges/{user_id}/
        """
        service = ValidityService()
        privileges = service.get_flight_privileges(user_id=UUID(user_id))

        return Response(privileges)

    @action(detail=False, methods=['get'], url_path='action-items/(?P<user_id>[^/.]+)')
    def action_items(self, request, user_id=None):
        """
        Get action items for a user (things that need attention).

        GET /validity/action-items/{user_id}/
        """
        service = ValidityService()
        items = service.get_action_items(user_id=UUID(user_id))

        return Response(items)

    @action(detail=False, methods=['get'], url_path='upcoming-expirations')
    def upcoming_expirations(self, request):
        """
        Get upcoming expirations for organization.

        GET /validity/upcoming-expirations/?days=90
        """
        organization_id = request.headers.get('X-Organization-ID')
        days = int(request.query_params.get('days', 90))

        service = ValidityService()
        expirations = service.get_upcoming_expirations(
            organization_id=UUID(organization_id) if organization_id else None,
            days_ahead=days
        )

        return Response(expirations)

    @action(detail=False, methods=['post'], url_path='can-fly')
    def can_fly(self, request):
        """
        Simple check if user can fly.

        POST /validity/can-fly/
        {
            "user_id": "uuid",
            "aircraft_type": "C172" (optional)
        }
        """
        user_id = request.data.get('user_id')
        aircraft_type = request.data.get('aircraft_type')

        if not user_id:
            return Response(
                {'detail': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = ValidityService()
        result = service.can_fly(
            user_id=UUID(user_id),
            aircraft_type=aircraft_type
        )

        return Response(result)

    @action(detail=False, methods=['post'], url_path='can-instruct')
    def can_instruct(self, request):
        """
        Simple check if user can provide instruction.

        POST /validity/can-instruct/
        {
            "user_id": "uuid",
            "aircraft_type": "C172" (optional)
        }
        """
        user_id = request.data.get('user_id')
        aircraft_type = request.data.get('aircraft_type')

        if not user_id:
            return Response(
                {'detail': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = ValidityService()
        result = service.can_instruct(
            user_id=UUID(user_id),
            aircraft_type=aircraft_type
        )

        return Response(result)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Get dashboard data for current user.

        GET /validity/dashboard/
        """
        user_id = request.user.id

        service = ValidityService()
        dashboard = service.get_dashboard_data(user_id=user_id)

        return Response(dashboard)

    @action(detail=False, methods=['get'], url_path='organization-dashboard')
    def organization_dashboard(self, request):
        """
        Get organization dashboard data.

        GET /validity/organization-dashboard/
        """
        organization_id = request.headers.get('X-Organization-ID')

        if not organization_id:
            return Response(
                {'detail': 'Organization ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = ValidityService()
        dashboard = service.get_organization_dashboard(
            organization_id=UUID(organization_id)
        )

        return Response(dashboard)
