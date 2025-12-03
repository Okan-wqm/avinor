from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
# ViewSets will be registered here when created
# router.register(r'tasks', MaintenanceTaskViewSet, basename='maintenance-task')
# router.register(r'records', MaintenanceRecordViewSet, basename='maintenance-record')
# router.register(r'schedules', MaintenanceScheduleViewSet, basename='maintenance-schedule')
# router.register(r'mel', MELItemViewSet, basename='mel-item')

urlpatterns = [
    path('', include(router.urls)),
]
