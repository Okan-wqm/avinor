"""Notification Service Views."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.template import Template, Context

from .models import NotificationTemplate, Notification, NotificationPreference, DeviceToken, NotificationBatch
from .serializers import (
    NotificationTemplateSerializer, NotificationSerializer, NotificationListSerializer,
    NotificationCreateSerializer, NotificationPreferenceSerializer,
    DeviceTokenSerializer, NotificationBatchSerializer
)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['template_type', 'organization_id', 'is_active']
    search_fields = ['name', 'code']


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['user_id', 'channel', 'status', 'organization_id']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return NotificationListSerializer
        if self.action == 'create':
            return NotificationCreateSerializer
        return NotificationSerializer

    def create(self, request, *args, **kwargs):
        """Create and optionally send a notification."""
        serializer = NotificationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Get template if specified
        template = None
        if 'template_code' in data:
            template = NotificationTemplate.objects.filter(code=data['template_code'], is_active=True).first()

        # Render content from template
        subject = data.get('subject', '')
        body = data.get('body', '')
        body_html = ''

        if template:
            context = Context(data.get('context', {}))
            subject = subject or Template(template.subject).render(context)
            body = body or Template(template.body_text).render(context)
            body_html = Template(template.body_html).render(context)

        notification = Notification.objects.create(
            user_id=data['user_id'],
            template=template,
            channel=data['channel'],
            priority=data.get('priority', 'normal'),
            subject=subject,
            body=body,
            body_html=body_html,
            context=data.get('context', {}),
            scheduled_at=data.get('scheduled_at'),
            status=Notification.Status.PENDING
        )

        # Queue for sending via Celery
        from .tasks import send_notification
        if not notification.scheduled_at:
            # Send immediately if not scheduled
            send_notification.delay(str(notification.id))

        return Response(NotificationSerializer(notification).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def my_notifications(self, request):
        """Get current user's notifications."""
        notifications = self.queryset.filter(
            user_id=request.user.id,
            channel=Notification.Channel.IN_APP
        )
        page = self.paginate_queryset(notifications)
        serializer = NotificationListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count."""
        count = self.queryset.filter(
            user_id=request.user.id,
            channel=Notification.Channel.IN_APP,
            read_at__isnull=True
        ).count()
        return Response({'unread_count': count})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read."""
        notification = self.get_object()
        notification.read_at = timezone.now()
        notification.status = Notification.Status.READ
        notification.save()
        return Response({'status': 'read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        self.queryset.filter(
            user_id=request.user.id,
            read_at__isnull=True
        ).update(read_at=timezone.now(), status=Notification.Status.READ)
        return Response({'status': 'all_read'})


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    queryset = NotificationPreference.objects.all()
    serializer_class = NotificationPreferenceSerializer

    @action(detail=False, methods=['get', 'put', 'patch'])
    def my_preferences(self, request):
        """Get or update current user's preferences."""
        prefs, created = NotificationPreference.objects.get_or_create(user_id=request.user.id)

        if request.method == 'GET':
            return Response(NotificationPreferenceSerializer(prefs).data)

        serializer = NotificationPreferenceSerializer(
            prefs, data=request.data, partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DeviceTokenViewSet(viewsets.ModelViewSet):
    queryset = DeviceToken.objects.all()
    serializer_class = DeviceTokenSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user_id', 'platform', 'is_active']

    @action(detail=False, methods=['post'])
    def register(self, request):
        """Register a device token."""
        data = request.data.copy()
        data['user_id'] = request.user.id

        # Deactivate existing token if same
        DeviceToken.objects.filter(
            user_id=request.user.id,
            token=data.get('token')
        ).update(is_active=False)

        serializer = DeviceTokenSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class NotificationBatchViewSet(viewsets.ModelViewSet):
    queryset = NotificationBatch.objects.all()
    serializer_class = NotificationBatchSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['organization_id', 'status']
    ordering = ['-created_at']
