"""
Data Fetcher Service.

Service for fetching data from other microservices.
"""
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
import httpx
from django.conf import settings

from ..exceptions import DataSourceUnavailable, InvalidQueryConfiguration
from ..constants import (
    DATA_SOURCE_FLIGHT,
    DATA_SOURCE_BOOKING,
    DATA_SOURCE_TRAINING,
    DATA_SOURCE_FINANCE,
    DATA_SOURCE_AIRCRAFT,
    DATA_SOURCE_MAINTENANCE,
    DATA_SOURCE_USER,
    WIDGET_QUERY_TIMEOUT,
)

logger = logging.getLogger(__name__)


class DataFetcherService:
    """Service for fetching data from other microservices."""

    # Service URL mappings
    SERVICE_URLS = {
        DATA_SOURCE_FLIGHT: getattr(settings, 'FLIGHT_SERVICE_URL', 'http://flight-service:8005'),
        DATA_SOURCE_BOOKING: getattr(settings, 'BOOKING_SERVICE_URL', 'http://booking-service:8004'),
        DATA_SOURCE_TRAINING: getattr(settings, 'TRAINING_SERVICE_URL', 'http://training-service:8007'),
        DATA_SOURCE_FINANCE: getattr(settings, 'FINANCE_SERVICE_URL', 'http://finance-service:8010'),
        DATA_SOURCE_AIRCRAFT: getattr(settings, 'AIRCRAFT_SERVICE_URL', 'http://aircraft-service:8003'),
        DATA_SOURCE_MAINTENANCE: getattr(settings, 'MAINTENANCE_SERVICE_URL', 'http://maintenance-service:8012'),
        DATA_SOURCE_USER: getattr(settings, 'USER_SERVICE_URL', 'http://user-service:8001'),
    }

    # Endpoint mappings for different data types
    ENDPOINTS = {
        DATA_SOURCE_FLIGHT: {
            'flights': '/api/v1/flights/',
            'flight_logs': '/api/v1/flight-logs/',
            'flight_stats': '/api/v1/flights/stats/',
        },
        DATA_SOURCE_BOOKING: {
            'bookings': '/api/v1/bookings/',
            'availability': '/api/v1/bookings/availability/',
            'booking_stats': '/api/v1/bookings/stats/',
        },
        DATA_SOURCE_TRAINING: {
            'enrollments': '/api/v1/enrollments/',
            'progress': '/api/v1/progress/',
            'training_stats': '/api/v1/training/stats/',
        },
        DATA_SOURCE_FINANCE: {
            'transactions': '/api/v1/transactions/',
            'invoices': '/api/v1/invoices/',
            'accounts': '/api/v1/accounts/',
            'finance_stats': '/api/v1/finance/stats/',
        },
        DATA_SOURCE_AIRCRAFT: {
            'aircraft': '/api/v1/aircraft/',
            'utilization': '/api/v1/aircraft/utilization/',
            'aircraft_stats': '/api/v1/aircraft/stats/',
        },
        DATA_SOURCE_MAINTENANCE: {
            'work_orders': '/api/v1/work-orders/',
            'maintenance_logs': '/api/v1/maintenance-logs/',
            'maintenance_stats': '/api/v1/maintenance/stats/',
        },
        DATA_SOURCE_USER: {
            'users': '/api/v1/users/',
            'instructors': '/api/v1/users/instructors/',
            'students': '/api/v1/users/students/',
            'user_stats': '/api/v1/users/stats/',
        },
    }

    @classmethod
    def fetch_data(
        cls,
        data_source: str,
        query_config: Dict[str, Any],
        parameters: Dict[str, Any],
        organization_id: UUID,
    ) -> List[Dict]:
        """
        Fetch data from a source service.

        Args:
            data_source: Service name to query
            query_config: Query configuration (endpoint, filters, etc.)
            parameters: Dynamic parameters (date range, etc.)
            organization_id: Organization UUID for filtering

        Returns:
            List of data records

        Raises:
            DataSourceUnavailable: If service is unreachable
            InvalidQueryConfiguration: If query config is invalid
        """
        base_url = cls.SERVICE_URLS.get(data_source)
        if not base_url:
            raise DataSourceUnavailable(detail=f"Unknown data source: {data_source}")

        # Get endpoint
        endpoint_key = query_config.get('endpoint', 'default')
        endpoints = cls.ENDPOINTS.get(data_source, {})
        endpoint = endpoints.get(endpoint_key, list(endpoints.values())[0] if endpoints else '/api/v1/')

        # Build URL
        url = f"{base_url}{endpoint}"

        # Build query parameters
        params = cls._build_query_params(query_config, parameters, organization_id)

        try:
            logger.info(
                f"Fetching data from {data_source}",
                extra={
                    'url': url,
                    'organization_id': str(organization_id),
                }
            )

            with httpx.Client(timeout=WIDGET_QUERY_TIMEOUT) as client:
                response = client.get(
                    url,
                    params=params,
                    headers={
                        'X-Organization-ID': str(organization_id),
                        'Accept': 'application/json',
                    }
                )
                response.raise_for_status()

                data = response.json()

                # Handle paginated responses
                if isinstance(data, dict):
                    if 'results' in data:
                        return data['results']
                    elif 'data' in data:
                        return data['data']
                    else:
                        return [data]

                return data if isinstance(data, list) else [data]

        except httpx.TimeoutException:
            logger.error(f"Timeout fetching from {data_source}")
            raise DataSourceUnavailable(
                detail=f"Timeout connecting to {data_source}"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from {data_source}: {e.response.status_code}")
            raise DataSourceUnavailable(
                detail=f"Error from {data_source}: {e.response.status_code}"
            )
        except Exception as e:
            logger.error(f"Error fetching from {data_source}: {e}", exc_info=True)
            raise DataSourceUnavailable(detail=str(e))

    @classmethod
    def _build_query_params(
        cls,
        query_config: Dict[str, Any],
        parameters: Dict[str, Any],
        organization_id: UUID,
    ) -> Dict[str, Any]:
        """Build query parameters from config and parameters."""
        params = {
            'organization_id': str(organization_id),
        }

        # Add date range if present
        if 'start_date' in parameters:
            params['start_date'] = parameters['start_date']
        if 'end_date' in parameters:
            params['end_date'] = parameters['end_date']

        # Add filters from query config
        filters = query_config.get('filters', [])
        for filter_item in filters:
            field = filter_item.get('field')
            operator = filter_item.get('operator', 'eq')
            value = filter_item.get('value')

            if field and value is not None:
                if operator == 'eq':
                    params[field] = value
                elif operator == 'in':
                    params[f'{field}__in'] = ','.join(map(str, value))
                elif operator == 'gte':
                    params[f'{field}__gte'] = value
                elif operator == 'lte':
                    params[f'{field}__lte'] = value
                elif operator == 'contains':
                    params[f'{field}__contains'] = value

        # Add pagination
        limit = query_config.get('limit', 1000)
        params['page_size'] = min(limit, 1000)

        # Add sorting
        if query_config.get('order_by'):
            params['ordering'] = query_config['order_by']

        return params

    @classmethod
    def get_aggregated_data(
        cls,
        data_source: str,
        query_config: Dict[str, Any],
        parameters: Dict[str, Any],
        organization_id: UUID,
        aggregations: List[Dict],
    ) -> Dict[str, Any]:
        """
        Fetch and aggregate data.

        Args:
            data_source: Service to query
            query_config: Query configuration
            parameters: Dynamic parameters
            organization_id: Organization UUID
            aggregations: Aggregation configuration

        Returns:
            Aggregated data dictionary
        """
        raw_data = cls.fetch_data(data_source, query_config, parameters, organization_id)

        if not raw_data:
            return {}

        results = {}

        for agg in aggregations:
            field = agg.get('field')
            func = agg.get('function')
            alias = agg.get('alias', f'{func}_{field}')

            values = [row.get(field) for row in raw_data if row.get(field) is not None]

            if not values:
                results[alias] = None
                continue

            # Convert to numbers if needed
            try:
                numeric_values = [float(v) for v in values]
            except (ValueError, TypeError):
                numeric_values = values

            if func == 'sum':
                results[alias] = sum(numeric_values)
            elif func == 'avg':
                results[alias] = sum(numeric_values) / len(numeric_values)
            elif func == 'count':
                results[alias] = len(values)
            elif func == 'min':
                results[alias] = min(numeric_values)
            elif func == 'max':
                results[alias] = max(numeric_values)
            elif func == 'first':
                results[alias] = values[0]
            elif func == 'last':
                results[alias] = values[-1]

        return results

    @classmethod
    def check_health(cls, data_source: str) -> bool:
        """Check if a data source service is healthy."""
        base_url = cls.SERVICE_URLS.get(data_source)
        if not base_url:
            return False

        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{base_url}/health/")
                return response.status_code == 200
        except Exception:
            return False

    @classmethod
    def get_available_sources(cls) -> List[Dict[str, Any]]:
        """Get list of available data sources with health status."""
        sources = []
        for source, url in cls.SERVICE_URLS.items():
            sources.append({
                'name': source,
                'url': url,
                'healthy': cls.check_health(source),
                'endpoints': list(cls.ENDPOINTS.get(source, {}).keys()),
            })
        return sources
