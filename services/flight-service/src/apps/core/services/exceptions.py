# services/flight-service/src/apps/core/services/exceptions.py
"""
Flight Service Exceptions

Custom exceptions for flight service operations.
"""

from typing import Optional, Dict, Any


class FlightServiceError(Exception):
    """Base exception for flight service errors."""

    def __init__(
        self,
        message: str,
        code: str = "FLIGHT_SERVICE_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


class FlightNotFoundError(FlightServiceError):
    """Raised when a flight is not found."""

    def __init__(
        self,
        flight_id: str = None,
        message: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        msg = message or f"Flight not found: {flight_id}"
        super().__init__(
            message=msg,
            code="FLIGHT_NOT_FOUND",
            details=details or {"flight_id": flight_id}
        )


class FlightValidationError(FlightServiceError):
    """Raised when flight data validation fails."""

    def __init__(
        self,
        message: str,
        field: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(
            message=message,
            code="FLIGHT_VALIDATION_ERROR",
            details=error_details
        )


class FlightStateError(FlightServiceError):
    """Raised when flight state transition is invalid."""

    def __init__(
        self,
        current_state: str,
        target_state: str,
        message: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        msg = message or f"Cannot transition from {current_state} to {target_state}"
        error_details = details or {}
        error_details.update({
            "current_state": current_state,
            "target_state": target_state
        })
        super().__init__(
            message=msg,
            code="FLIGHT_STATE_ERROR",
            details=error_details
        )


class FlightPermissionError(FlightServiceError):
    """Raised when user lacks permission for an operation."""

    def __init__(
        self,
        operation: str,
        user_id: str = None,
        message: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        msg = message or f"Permission denied for operation: {operation}"
        error_details = details or {}
        error_details["operation"] = operation
        if user_id:
            error_details["user_id"] = user_id
        super().__init__(
            message=msg,
            code="FLIGHT_PERMISSION_ERROR",
            details=error_details
        )


class LogbookError(FlightServiceError):
    """Raised when logbook operations fail."""

    def __init__(
        self,
        message: str,
        user_id: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if user_id:
            error_details["user_id"] = user_id
        super().__init__(
            message=message,
            code="LOGBOOK_ERROR",
            details=error_details
        )


class CurrencyError(FlightServiceError):
    """Raised when currency check or update fails."""

    def __init__(
        self,
        message: str,
        currency_type: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if currency_type:
            error_details["currency_type"] = currency_type
        super().__init__(
            message=message,
            code="CURRENCY_ERROR",
            details=error_details
        )


class StatisticsError(FlightServiceError):
    """Raised when statistics calculation fails."""

    def __init__(
        self,
        message: str,
        operation: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if operation:
            error_details["operation"] = operation
        super().__init__(
            message=message,
            code="STATISTICS_ERROR",
            details=error_details
        )


class ApproachError(FlightServiceError):
    """Raised when approach operations fail."""

    def __init__(
        self,
        message: str,
        approach_id: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if approach_id:
            error_details["approach_id"] = approach_id
        super().__init__(
            message=message,
            code="APPROACH_ERROR",
            details=error_details
        )


class FuelRecordError(FlightServiceError):
    """Raised when fuel record operations fail."""

    def __init__(
        self,
        message: str,
        record_id: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if record_id:
            error_details["record_id"] = record_id
        super().__init__(
            message=message,
            code="FUEL_RECORD_ERROR",
            details=error_details
        )


class SignatureError(FlightServiceError):
    """Raised when signature operations fail."""

    def __init__(
        self,
        message: str,
        signer_role: str = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if signer_role:
            error_details["signer_role"] = signer_role
        super().__init__(
            message=message,
            code="SIGNATURE_ERROR",
            details=error_details
        )
