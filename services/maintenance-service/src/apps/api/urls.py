# services/maintenance-service/src/apps/api/urls.py
"""
Maintenance Service API URL Configuration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.api.views import (
    MaintenanceItemViewSet,
    WorkOrderViewSet,
    WorkOrderTaskViewSet,
    MaintenanceLogViewSet,
    PartsInventoryViewSet,
    PartTransactionViewSet,
    ADSBTrackingViewSet,
)

app_name = 'api'

router = DefaultRouter()

# Maintenance Items
router.register(r'items', MaintenanceItemViewSet, basename='maintenance-item')

# Work Orders
router.register(r'work-orders', WorkOrderViewSet, basename='work-order')
router.register(r'tasks', WorkOrderTaskViewSet, basename='work-order-task')

# Maintenance Logs
router.register(r'logs', MaintenanceLogViewSet, basename='maintenance-log')

# Parts Inventory
router.register(r'parts', PartsInventoryViewSet, basename='parts-inventory')
router.register(r'transactions', PartTransactionViewSet, basename='part-transaction')

# AD/SB Compliance
router.register(r'directives', ADSBTrackingViewSet, basename='adsb-tracking')

urlpatterns = [
    path('', include(router.urls)),
]
