from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
# ViewSets will be registered here when created
# router.register(r'templates', ReportTemplateViewSet, basename='template')
# router.register(r'reports', ReportViewSet, basename='report')
# router.register(r'schedules', ReportScheduleViewSet, basename='schedule')
# router.register(r'dashboards', DashboardViewSet, basename='dashboard')
# router.register(r'widgets', WidgetViewSet, basename='widget')

urlpatterns = [
    path('', include(router.urls)),
]
