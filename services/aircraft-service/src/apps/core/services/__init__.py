# services/aircraft-service/src/apps/core/services/__init__.py
"""
Aircraft Service Business Logic

This module exports all services and exceptions for the Aircraft Service.
"""

from .aircraft_service import AircraftService
from .squawk_service import SquawkService
from .counter_service import CounterService
from .document_service import DocumentService

# Custom Exceptions
class AircraftServiceError(Exception):
    """Base exception for aircraft service errors."""
    pass


class AircraftNotFoundError(AircraftServiceError):
    """Aircraft not found."""
    pass


class AircraftValidationError(AircraftServiceError):
    """Validation error for aircraft data."""
    pass


class AircraftConflictError(AircraftServiceError):
    """Conflict error (e.g., duplicate registration)."""
    pass


class SquawkError(AircraftServiceError):
    """Squawk related error."""
    pass


class DocumentError(AircraftServiceError):
    """Document related error."""
    pass


class CounterError(AircraftServiceError):
    """Counter/time tracking related error."""
    pass


__all__ = [
    # Services
    'AircraftService',
    'SquawkService',
    'CounterService',
    'DocumentService',

    # Exceptions
    'AircraftServiceError',
    'AircraftNotFoundError',
    'AircraftValidationError',
    'AircraftConflictError',
    'SquawkError',
    'DocumentError',
    'CounterError',
]
