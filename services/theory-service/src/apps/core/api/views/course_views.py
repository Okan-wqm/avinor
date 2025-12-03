# services/theory-service/src/apps/core/api/views/course_views.py
"""
Course Views

ViewSets for course-related API endpoints.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from ...models import Course, CourseModule, CourseAttachment
from ...services import CourseService
from ..serializers import (
    CourseListSerializer,
    CourseDetailSerializer,
    CourseCreateSerializer,
    CourseUpdateSerializer,
    CourseModuleSerializer,
    CourseModuleCreateSerializer,
    CourseModuleUpdateSerializer,
    CourseAttachmentSerializer,
    ModuleReorderSerializer,
)


class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing theory courses.

    Provides CRUD operations plus publish, archive, clone actions.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get courses filtered by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        return CourseService.get_courses(
            organization_id=organization_id,
            category=self.request.query_params.get('category'),
            program_type=self.request.query_params.get('program_type'),
            status=self.request.query_params.get('status'),
            is_published=self.request.query_params.get('is_published'),
            search=self.request.query_params.get('search'),
        )

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'list':
            return CourseListSerializer
        elif self.action == 'create':
            return CourseCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CourseUpdateSerializer
        return CourseDetailSerializer

    def create(self, request, *args, **kwargs):
        """Create a new course."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        course = CourseService.create_course(
            organization_id=organization_id,
            created_by=str(request.user.id),
            **serializer.validated_data
        )

        return Response(
            CourseDetailSerializer(course).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """Update a course."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = self.get_serializer(data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)

        course = CourseService.update_course(
            course_id=kwargs['pk'],
            organization_id=organization_id,
            **serializer.validated_data
        )

        return Response(CourseDetailSerializer(course).data)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish a course."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            course = CourseService.publish_course(
                course_id=pk,
                organization_id=organization_id
            )
            return Response(CourseDetailSerializer(course).data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a course."""
        organization_id = request.headers.get('X-Organization-ID')

        course = CourseService.archive_course(
            course_id=pk,
            organization_id=organization_id
        )

        return Response(CourseDetailSerializer(course).data)

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone a course."""
        organization_id = request.headers.get('X-Organization-ID')
        new_code = request.data.get('new_code')
        new_name = request.data.get('new_name')

        if not new_code:
            return Response(
                {'error': 'new_code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            course = CourseService.clone_course(
                course_id=pk,
                organization_id=organization_id,
                new_code=new_code,
                new_name=new_name
            )
            return Response(
                CourseDetailSerializer(course).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get course statistics."""
        organization_id = request.headers.get('X-Organization-ID')

        stats = CourseService.get_course_statistics(
            course_id=pk,
            organization_id=organization_id
        )

        return Response(stats)

    @action(detail=True, methods=['get'])
    def modules(self, request, pk=None):
        """Get course modules."""
        organization_id = request.headers.get('X-Organization-ID')

        modules = CourseService.get_course_modules(
            course_id=pk,
            organization_id=organization_id
        )

        return Response(CourseModuleSerializer(modules, many=True).data)

    @action(detail=True, methods=['post'], url_path='modules/reorder')
    def reorder_modules(self, request, pk=None):
        """Reorder course modules."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = ModuleReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        modules = CourseService.reorder_modules(
            course_id=pk,
            organization_id=organization_id,
            module_order=[str(m) for m in serializer.validated_data['module_order']]
        )

        return Response(CourseModuleSerializer(modules, many=True).data)


class CourseModuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing course modules.

    Nested under courses.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CourseModuleSerializer

    def get_queryset(self):
        """Get modules for a course."""
        organization_id = self.request.headers.get('X-Organization-ID')
        course_id = self.kwargs.get('course_pk')

        return CourseService.get_course_modules(
            course_id=course_id,
            organization_id=organization_id
        )

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'create':
            return CourseModuleCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CourseModuleUpdateSerializer
        return CourseModuleSerializer

    def create(self, request, *args, **kwargs):
        """Create a new module."""
        organization_id = request.headers.get('X-Organization-ID')
        course_id = kwargs.get('course_pk')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        module = CourseService.create_module(
            course_id=course_id,
            organization_id=organization_id,
            **serializer.validated_data
        )

        return Response(
            CourseModuleSerializer(module).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """Update a module."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = self.get_serializer(data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)

        module = CourseService.update_module(
            module_id=kwargs['pk'],
            organization_id=organization_id,
            **serializer.validated_data
        )

        return Response(CourseModuleSerializer(module).data)

    def destroy(self, request, *args, **kwargs):
        """Delete a module."""
        organization_id = request.headers.get('X-Organization-ID')

        CourseService.delete_module(
            module_id=kwargs['pk'],
            organization_id=organization_id
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def content(self, request, course_pk=None, pk=None):
        """Get module content for learning."""
        organization_id = request.headers.get('X-Organization-ID')

        module = get_object_or_404(
            CourseModule,
            id=pk,
            course_id=course_pk,
            course__organization_id=organization_id
        )

        return Response({
            'id': str(module.id),
            'name': module.name,
            'description': module.description,
            'content_type': module.content_type,
            'content': module.content,
            'content_html': module.content_html,
            'video_url': module.video_url,
            'video_duration_seconds': module.video_duration_seconds,
            'audio_url': module.audio_url,
            'document_url': module.document_url,
            'learning_objectives': module.learning_objectives,
            'key_points': module.key_points,
            'resources': module.resources,
            'has_quiz': module.has_quiz,
            'quiz_id': str(module.quiz_id) if module.quiz_id else None,
            'completion_criteria': module.completion_criteria,
        })


class CourseAttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing course attachments.

    Nested under courses.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CourseAttachmentSerializer

    def get_queryset(self):
        """Get attachments for a course."""
        organization_id = self.request.headers.get('X-Organization-ID')
        course_id = self.kwargs.get('course_pk')

        return CourseAttachment.objects.filter(
            course_id=course_id,
            course__organization_id=organization_id
        ).order_by('sort_order')

    def create(self, request, *args, **kwargs):
        """Create a new attachment."""
        organization_id = request.headers.get('X-Organization-ID')
        course_id = kwargs.get('course_pk')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        attachment = CourseService.add_attachment(
            course_id=course_id,
            organization_id=organization_id,
            **serializer.validated_data
        )

        return Response(
            CourseAttachmentSerializer(attachment).data,
            status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        """Delete an attachment."""
        organization_id = request.headers.get('X-Organization-ID')

        CourseService.delete_attachment(
            attachment_id=kwargs['pk'],
            organization_id=organization_id
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def download(self, request, course_pk=None, pk=None):
        """Record download and return file URL."""
        organization_id = request.headers.get('X-Organization-ID')

        attachment = get_object_or_404(
            CourseAttachment,
            id=pk,
            course_id=course_pk,
            course__organization_id=organization_id
        )

        attachment.download_count += 1
        attachment.save()

        return Response({
            'file_url': attachment.file_url,
            'file_name': attachment.name
        })
