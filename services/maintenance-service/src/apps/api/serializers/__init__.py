# services/maintenance-service/src/apps/api/serializers/__init__.py
"""
API Serializers
"""

from .maintenance_item import (
    MaintenanceItemSerializer,
    MaintenanceItemListSerializer,
    MaintenanceItemDetailSerializer,
    MaintenanceItemCreateSerializer,
    MaintenanceItemUpdateSerializer,
    MaintenanceItemComplianceSerializer,
)
from .work_order import (
    WorkOrderSerializer,
    WorkOrderListSerializer,
    WorkOrderDetailSerializer,
    WorkOrderCreateSerializer,
    WorkOrderUpdateSerializer,
    WorkOrderTaskSerializer,
    WorkOrderTaskCreateSerializer,
    WorkOrderTaskCompleteSerializer,
)
from .maintenance_log import (
    MaintenanceLogSerializer,
    MaintenanceLogListSerializer,
    MaintenanceLogDetailSerializer,
    MaintenanceLogCreateSerializer,
)
from .parts_inventory import (
    PartsInventorySerializer,
    PartsInventoryListSerializer,
    PartsInventoryDetailSerializer,
    PartsInventoryCreateSerializer,
    PartsInventoryUpdateSerializer,
    PartTransactionSerializer,
    PartReceiveSerializer,
    PartIssueSerializer,
)
from .compliance import (
    ADSBTrackingSerializer,
    ADSBTrackingListSerializer,
    ADSBTrackingDetailSerializer,
    ADSBTrackingCreateSerializer,
    ADSBTrackingComplianceSerializer,
)

__all__ = [
    # Maintenance Item
    'MaintenanceItemSerializer',
    'MaintenanceItemListSerializer',
    'MaintenanceItemDetailSerializer',
    'MaintenanceItemCreateSerializer',
    'MaintenanceItemUpdateSerializer',
    'MaintenanceItemComplianceSerializer',

    # Work Order
    'WorkOrderSerializer',
    'WorkOrderListSerializer',
    'WorkOrderDetailSerializer',
    'WorkOrderCreateSerializer',
    'WorkOrderUpdateSerializer',
    'WorkOrderTaskSerializer',
    'WorkOrderTaskCreateSerializer',
    'WorkOrderTaskCompleteSerializer',

    # Maintenance Log
    'MaintenanceLogSerializer',
    'MaintenanceLogListSerializer',
    'MaintenanceLogDetailSerializer',
    'MaintenanceLogCreateSerializer',

    # Parts Inventory
    'PartsInventorySerializer',
    'PartsInventoryListSerializer',
    'PartsInventoryDetailSerializer',
    'PartsInventoryCreateSerializer',
    'PartsInventoryUpdateSerializer',
    'PartTransactionSerializer',
    'PartReceiveSerializer',
    'PartIssueSerializer',

    # Compliance
    'ADSBTrackingSerializer',
    'ADSBTrackingListSerializer',
    'ADSBTrackingDetailSerializer',
    'ADSBTrackingCreateSerializer',
    'ADSBTrackingComplianceSerializer',
]
