# services/flight-service/src/apps/core/services/__init__.py
"""
Flight Service - Service Layer

Business logic layer for flight management operations.
"""

from .exceptions import (
    FlightServiceError,
    FlightNotFoundError,
    FlightValidationError,
    FlightStateError,
    FlightPermissionError,
    LogbookError,
    CurrencyError,
    StatisticsError,
)

from .flight_service import FlightService
from .logbook_service import LogbookService
from .statistics_service import StatisticsService
from .currency_service import CurrencyService

__all__ = [
    # Exceptions
    'FlightServiceError',
    'FlightNotFoundError',
    'FlightValidationError',
    'FlightStateError',
    'FlightPermissionError',
    'LogbookError',
    'CurrencyError',
    'StatisticsError',
    # Services
    'FlightService',
    'LogbookService',
    'StatisticsService',
    'CurrencyService',
]
