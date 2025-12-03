# services/training-service/src/apps/core/api/views/training_program_views.py
"""
Training Program Views

API ViewSet for training program endpoints.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError

from ...models import TrainingProgram
from ...services import TrainingProgramService
from ..serializers.training_program_serializers import (
    TrainingProgramSerializer,
    TrainingProgramCreateSerializer,
    TrainingProgramUpdateSerializer,
    TrainingProgramListSerializer,
    TrainingProgramDetailSerializer,
    ProgramStatisticsSerializer,
    ProgramStageSerializer,
    StageCreateSerializer,
    StageUpdateSerializer,
    StageReorderSerializer,
    ProgramCloneSerializer,
)

logger = logging.getLogger(__name__)


class TrainingProgramViewSet(viewsets.ModelViewSet):
    """
    ViewSet for training program CRUD and management.

    Endpoints:
    - GET /programs/ - List all programs
    - POST /programs/ - Create a program
    - GET /programs/{id}/ - Get program details
    - PUT/PATCH /programs/{id}/ - Update program
    - DELETE /programs/{id}/ - Delete program
    - POST /programs/{id}/publish/ - Publish program
    - POST /programs/{id}/unpublish/ - Unpublish program
    - GET /programs/{id}/statistics/ - Get program statistics
    - POST /programs/{id}/stages/ - Add stage
    - PUT /programs/{id}/stages/{stage_id}/ - Update stage
    - DELETE /programs/{id}/stages/{stage_id}/ - Delete stage
    - POST /programs/{id}/stages/reorder/ - Reorder stages
    - POST /programs/{id}/clone/ - Clone program
    - GET /programs/{id}/export/ - Export program
    - GET /programs/{id}/syllabus/ - Get full syllabus
    """

    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        """Get queryset filtered by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        return TrainingProgram.objects.filter(
            organization_id=organization_id
        ).select_related()

    def get_serializer_class(self):
        """Get appropriate serializer based on action."""
        if self.action == 'create':
            return TrainingProgramCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TrainingProgramUpdateSerializer
        elif self.action == 'list':
            return TrainingProgramListSerializer
        elif self.action == 'retrieve':
            return TrainingProgramDetailSerializer
        elif self.action == 'statistics':
            return ProgramStatisticsSerializer
        return TrainingProgramSerializer

    def get_serializer_context(self):
        """Add organization_id to serializer context."""
        context = super().get_serializer_context()
        context['organization_id'] = self.request.headers.get('X-Organization-ID')
        return context

    def list(self, request):
        """List training programs with filters."""
        organization_id = request.headers.get('X-Organization-ID')

        status_filter = request.query_params.get('status')
        program_type = request.query_params.get('program_type')
        is_published = request.query_params.get('is_published')
        search = request.query_params.get('search')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        if is_published is not None:
            is_published = is_published.lower() == 'true'

        programs, total = TrainingProgramService.list_programs(
            organization_id=organization_id,
            status=status_filter,
            program_type=program_type,
            is_published=is_published,
            search=search,
            page=page,
            page_size=page_size
        )

        serializer = self.get_serializer(programs, many=True)

        return Response({
            'results': serializer.data,
            'total': total,
            'page': page,
            'page_size': page_size,
        })

    def create(self, request):
        """Create a new training program."""
        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            program = TrainingProgramService.create_program(
                organization_id=organization_id,
                created_by=user_id,
                **serializer.validated_data
            )

            response_serializer = TrainingProgramDetailSerializer(program)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, id=None):
        """Update a training program."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            program = TrainingProgramService.update_program(
                program_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = TrainingProgramDetailSerializer(program)
            return Response(response_serializer.data)

        except TrainingProgram.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, id=None):
        """Delete a training program."""
        organization_id = request.headers.get('X-Organization-ID')
        force = request.query_params.get('force', 'false').lower() == 'true'

        try:
            TrainingProgramService.delete_program(
                program_id=id,
                organization_id=organization_id,
                force=force
            )
            return Response(status=status.HTTP_204_NO_CONTENT)

        except TrainingProgram.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def publish(self, request, id=None):
        """Publish a training program."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            program = TrainingProgramService.publish_program(
                program_id=id,
                organization_id=organization_id
            )

            serializer = TrainingProgramDetailSerializer(program)
            return Response(serializer.data)

        except TrainingProgram.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def unpublish(self, request, id=None):
        """Unpublish a training program."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            program = TrainingProgramService.unpublish_program(
                program_id=id,
                organization_id=organization_id
            )

            serializer = TrainingProgramDetailSerializer(program)
            return Response(serializer.data)

        except TrainingProgram.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    def statistics(self, request, id=None):
        """Get program statistics."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            stats = TrainingProgramService.get_program_statistics(
                program_id=id,
                organization_id=organization_id
            )

            return Response(stats)

        except TrainingProgram.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], url_path='stages')
    def add_stage(self, request, id=None):
        """Add a stage to the program."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = StageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stage = TrainingProgramService.add_stage(
                program_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            return Response(stage, status=status.HTTP_201_CREATED)

        except TrainingProgram.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['put'], url_path='stages/(?P<stage_id>[^/.]+)')
    def update_stage(self, request, id=None, stage_id=None):
        """Update a stage in the program."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = StageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stage = TrainingProgramService.update_stage(
                program_id=id,
                organization_id=organization_id,
                stage_id=stage_id,
                **serializer.validated_data
            )

            return Response(stage)

        except TrainingProgram.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['delete'], url_path='stages/(?P<stage_id>[^/.]+)/delete')
    def delete_stage(self, request, id=None, stage_id=None):
        """Delete a stage from the program."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            TrainingProgramService.remove_stage(
                program_id=id,
                organization_id=organization_id,
                stage_id=stage_id
            )

            return Response(status=status.HTTP_204_NO_CONTENT)

        except TrainingProgram.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='stages/reorder')
    def reorder_stages(self, request, id=None):
        """Reorder stages in the program."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = StageReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stages = TrainingProgramService.reorder_stages(
                program_id=id,
                organization_id=organization_id,
                stage_order=serializer.validated_data['stage_order']
            )

            return Response({'stages': stages})

        except TrainingProgram.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def clone(self, request, id=None):
        """Clone a training program."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = ProgramCloneSerializer(
            data=request.data,
            context={'organization_id': organization_id}
        )
        serializer.is_valid(raise_exception=True)

        try:
            new_program = TrainingProgramService.clone_program(
                source_program_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = TrainingProgramDetailSerializer(new_program)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except TrainingProgram.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def export(self, request, id=None):
        """Export program data."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            data = TrainingProgramService.export_program(
                program_id=id,
                organization_id=organization_id
            )

            return Response(data)

        except TrainingProgram.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    def syllabus(self, request, id=None):
        """Get complete program syllabus structure."""
        organization_id = request.headers.get('X-Organization-ID')

        from ...services import SyllabusService

        try:
            syllabus = SyllabusService.get_program_syllabus(
                program_id=id,
                organization_id=organization_id
            )

            return Response(syllabus)

        except TrainingProgram.DoesNotExist:
            return Response(
                {'error': 'Program not found'},
                status=status.HTTP_404_NOT_FOUND
            )
