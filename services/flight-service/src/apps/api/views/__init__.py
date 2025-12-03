# services/flight-service/src/apps/api/views/__init__.py
"""
Flight Service API Views

REST API views for flight management.
"""

from .flight_views import FlightViewSet
from .approach_views import ApproachViewSet, HoldViewSet
from .fuel_views import FuelRecordViewSet, OilRecordViewSet
from .logbook_views import LogbookViewSet
from .statistics_views import StatisticsViewSet
from .currency_views import CurrencyViewSet

__all__ = [
    'FlightViewSet',
    'ApproachViewSet',
    'HoldViewSet',
    'FuelRecordViewSet',
    'OilRecordViewSet',
    'LogbookViewSet',
    'StatisticsViewSet',
    'CurrencyViewSet',
]
