"""
Schedule Views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...services import ScheduleService
from ..serializers import ScheduleSerializer, ScheduleCreateSerializer, ScheduleUpdateSerializer


class ScheduleViewSet(viewsets.ViewSet):
    """ViewSet for managing report schedules."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """List schedules."""
        organization_id = request.headers.get('X-Organization-ID')
        template_id = request.query_params.get('template_id')
        is_active = request.query_params.get('is_active')

        if is_active is not None:
            is_active = is_active.lower() == 'true'

        schedules = ScheduleService.get_list(
            organization_id=organization_id,
            template_id=template_id,
            is_active=is_active,
        )

        serializer = ScheduleSerializer(schedules, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Get a specific schedule."""
        organization_id = request.headers.get('X-Organization-ID')
        schedule = ScheduleService.get_by_id(pk, organization_id)
        serializer = ScheduleSerializer(schedule)
        return Response(serializer.data)

    def create(self, request):
        """Create a new schedule."""
        serializer = ScheduleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        schedule = ScheduleService.create(
            organization_id=organization_id,
            created_by_id=user_id,
            **serializer.validated_data
        )

        return Response(ScheduleSerializer(schedule).data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        """Update a schedule."""
        serializer = ScheduleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        schedule = ScheduleService.update(
            schedule_id=pk,
            organization_id=organization_id,
            user_id=user_id,
            **serializer.validated_data
        )

        return Response(ScheduleSerializer(schedule).data)

    def destroy(self, request, pk=None):
        """Delete a schedule."""
        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        ScheduleService.delete(pk, organization_id, user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """Toggle schedule active status."""
        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        schedule = ScheduleService.toggle_active(pk, organization_id, user_id)
        return Response(ScheduleSerializer(schedule).data)
