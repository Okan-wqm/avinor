"""
Report Service URL Configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api.views import (
    ReportTemplateViewSet,
    ReportViewSet,
    DashboardViewSet,
    WidgetViewSet,
    ScheduleViewSet,
)

router = DefaultRouter()
router.register(r'templates', ReportTemplateViewSet, basename='template')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'dashboards', DashboardViewSet, basename='dashboard')
router.register(r'widgets', WidgetViewSet, basename='widget')
router.register(r'schedules', ScheduleViewSet, basename='schedule')

urlpatterns = [
    path('', include(router.urls)),
]
