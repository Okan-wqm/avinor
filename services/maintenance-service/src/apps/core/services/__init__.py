# services/maintenance-service/src/apps/core/services/__init__.py
"""
Maintenance Service Business Logic

All services for maintenance management.
"""

from .maintenance_service import MaintenanceService
from .work_order_service import WorkOrderService
from .parts_service import PartsService
from .compliance_service import ComplianceService


# Custom Exceptions
class MaintenanceServiceError(Exception):
    """Base exception for maintenance service errors."""
    pass


class MaintenanceItemNotFoundError(MaintenanceServiceError):
    """Maintenance item not found."""
    pass


class WorkOrderNotFoundError(MaintenanceServiceError):
    """Work order not found."""
    pass


class WorkOrderStateError(MaintenanceServiceError):
    """Invalid work order state transition."""
    pass


class PartNotFoundError(MaintenanceServiceError):
    """Part not found in inventory."""
    pass


class InsufficientInventoryError(MaintenanceServiceError):
    """Insufficient parts in inventory."""
    pass


class ComplianceError(MaintenanceServiceError):
    """Compliance-related error."""
    pass


__all__ = [
    # Services
    'MaintenanceService',
    'WorkOrderService',
    'PartsService',
    'ComplianceService',

    # Exceptions
    'MaintenanceServiceError',
    'MaintenanceItemNotFoundError',
    'WorkOrderNotFoundError',
    'WorkOrderStateError',
    'PartNotFoundError',
    'InsufficientInventoryError',
    'ComplianceError',
]
