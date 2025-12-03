# shared/common/clients.py
"""
Service Clients for Inter-Service Communication
"""

import httpx
import logging
from typing import Dict, Any, Optional, List
from django.conf import settings
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for handling service failures.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 30
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.success_count = 0
        self.state = 'closed'  # closed, open, half_open
        self.last_failure_time = None

    def _should_try_reset(self) -> bool:
        import time
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.timeout

    def record_success(self):
        if self.state == 'half_open':
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._reset()

    def record_failure(self):
        import time
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def _reset(self):
        self.state = 'closed'
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info("Circuit breaker reset to closed state")

    def can_execute(self) -> bool:
        if self.state == 'closed':
            return True
        if self.state == 'open':
            if self._should_try_reset():
                self.state = 'half_open'
                return True
            return False
        return True  # half_open


def with_circuit_breaker(circuit_breaker: CircuitBreaker):
    """Decorator to wrap async functions with circuit breaker logic"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not circuit_breaker.can_execute():
                raise CircuitBreakerError("Circuit breaker is open")
            try:
                result = await func(*args, **kwargs)
                circuit_breaker.record_success()
                return result
            except Exception as e:
                circuit_breaker.record_failure()
                raise
        return wrapper
    return decorator


# =============================================================================
# BASE SERVICE CLIENT
# =============================================================================

class BaseServiceClient:
    """
    Base class for service-to-service HTTP communication.
    """

    def __init__(self, service_name: str, base_url: str = None):
        self.service_name = service_name
        self.base_url = base_url or self._get_service_url(service_name)
        self.timeout = httpx.Timeout(10.0, connect=5.0)
        self.auth_token = getattr(settings, 'SERVICE_AUTH_TOKEN', '')
        self.circuit_breaker = CircuitBreaker()

    def _get_service_url(self, service_name: str) -> str:
        """Get service URL from settings"""
        service_urls = getattr(settings, 'SERVICE_URLS', {})
        return service_urls.get(service_name, f'http://{service_name}:8000')

    def _get_headers(self, extra_headers: Dict = None) -> Dict:
        """Build request headers"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Service-Auth': self.auth_token,
            'X-Source-Service': getattr(settings, 'SERVICE_NAME', 'unknown'),
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        params: Dict = None,
        data: Dict = None,
        headers: Dict = None
    ) -> Dict:
        """Make HTTP request to service"""
        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerError(f"Circuit breaker open for {self.service_name}")

        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=self._get_headers(headers)
                )
                response.raise_for_status()
                self.circuit_breaker.record_success()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error calling {self.service_name}: {e.response.status_code}",
                    extra={'url': url, 'status_code': e.response.status_code}
                )
                if e.response.status_code >= 500:
                    self.circuit_breaker.record_failure()
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error calling {self.service_name}: {e}")
                self.circuit_breaker.record_failure()
                raise

    async def get(self, path: str, params: Dict = None, headers: Dict = None) -> Dict:
        return await self._request('GET', path, params=params, headers=headers)

    async def post(self, path: str, data: Dict = None, headers: Dict = None) -> Dict:
        return await self._request('POST', path, data=data, headers=headers)

    async def put(self, path: str, data: Dict = None, headers: Dict = None) -> Dict:
        return await self._request('PUT', path, data=data, headers=headers)

    async def patch(self, path: str, data: Dict = None, headers: Dict = None) -> Dict:
        return await self._request('PATCH', path, data=data, headers=headers)

    async def delete(self, path: str, headers: Dict = None) -> Dict:
        return await self._request('DELETE', path, headers=headers)


# =============================================================================
# SPECIFIC SERVICE CLIENTS
# =============================================================================

class UserServiceClient(BaseServiceClient):
    """Client for User Service"""

    def __init__(self):
        super().__init__('user-service')

    async def get_user(self, user_id: str) -> Dict:
        return await self.get(f'/api/v1/users/{user_id}/')

    async def get_users(self, params: Dict = None) -> Dict:
        return await self.get('/api/v1/users/', params=params)

    async def verify_token(self, token: str) -> Dict:
        return await self.post('/api/v1/auth/verify/', {'token': token})

    async def get_user_permissions(self, user_id: str) -> List[str]:
        response = await self.get(f'/api/v1/users/{user_id}/permissions/')
        return response.get('permissions', [])

    async def get_users_by_organization(self, org_id: str) -> List[Dict]:
        response = await self.get('/api/v1/users/', params={'organization_id': org_id})
        return response.get('results', [])


class OrganizationServiceClient(BaseServiceClient):
    """Client for Organization Service"""

    def __init__(self):
        super().__init__('organization-service')

    async def get_organization(self, org_id: str) -> Dict:
        return await self.get(f'/api/v1/organizations/{org_id}/')

    async def get_organization_settings(self, org_id: str) -> Dict:
        return await self.get(f'/api/v1/organizations/{org_id}/settings/')

    async def get_locations(self, org_id: str) -> List[Dict]:
        response = await self.get(f'/api/v1/organizations/{org_id}/locations/')
        return response.get('results', [])


class AircraftServiceClient(BaseServiceClient):
    """Client for Aircraft Service"""

    def __init__(self):
        super().__init__('aircraft-service')

    async def get_aircraft(self, aircraft_id: str) -> Dict:
        return await self.get(f'/api/v1/aircraft/{aircraft_id}/')

    async def get_aircraft_list(self, org_id: str = None) -> List[Dict]:
        params = {'organization_id': org_id} if org_id else None
        response = await self.get('/api/v1/aircraft/', params=params)
        return response.get('results', [])

    async def check_availability(
        self,
        aircraft_id: str,
        start: str,
        end: str
    ) -> bool:
        response = await self.get(
            f'/api/v1/aircraft/{aircraft_id}/availability/',
            params={'start': start, 'end': end}
        )
        return response.get('available', False)

    async def update_hours(self, aircraft_id: str, hours: float) -> Dict:
        return await self.post(
            f'/api/v1/aircraft/{aircraft_id}/update-hours/',
            {'hours': hours}
        )

    async def get_aircraft_status(self, aircraft_id: str) -> Dict:
        return await self.get(f'/api/v1/aircraft/{aircraft_id}/status/')


class BookingServiceClient(BaseServiceClient):
    """Client for Booking Service"""

    def __init__(self):
        super().__init__('booking-service')

    async def get_booking(self, booking_id: str) -> Dict:
        return await self.get(f'/api/v1/bookings/{booking_id}/')

    async def get_bookings(
        self,
        start_date: str = None,
        end_date: str = None,
        user_id: str = None,
        aircraft_id: str = None
    ) -> List[Dict]:
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if user_id:
            params['user_id'] = user_id
        if aircraft_id:
            params['aircraft_id'] = aircraft_id

        response = await self.get('/api/v1/bookings/', params=params)
        return response.get('results', [])

    async def create_booking(self, data: Dict) -> Dict:
        return await self.post('/api/v1/bookings/', data)

    async def cancel_booking(self, booking_id: str, reason: str = None) -> Dict:
        return await self.post(
            f'/api/v1/bookings/{booking_id}/cancel/',
            {'reason': reason}
        )

    async def complete_booking(self, booking_id: str) -> Dict:
        return await self.post(f'/api/v1/bookings/{booking_id}/complete/', {})


class FlightServiceClient(BaseServiceClient):
    """Client for Flight Service"""

    def __init__(self):
        super().__init__('flight-service')

    async def get_flight(self, flight_id: str) -> Dict:
        return await self.get(f'/api/v1/flights/{flight_id}/')

    async def create_flight(self, data: Dict) -> Dict:
        return await self.post('/api/v1/flights/', data)

    async def get_logbook(self, user_id: str) -> List[Dict]:
        response = await self.get(f'/api/v1/logbook/', params={'user_id': user_id})
        return response.get('results', [])

    async def get_flight_totals(self, user_id: str) -> Dict:
        return await self.get(f'/api/v1/logbook/totals/', params={'user_id': user_id})


class TrainingServiceClient(BaseServiceClient):
    """Client for Training Service"""

    def __init__(self):
        super().__init__('training-service')

    async def get_student_progress(self, student_id: str) -> Dict:
        return await self.get(f'/api/v1/students/{student_id}/progress/')

    async def get_training_program(self, program_id: str) -> Dict:
        return await self.get(f'/api/v1/programs/{program_id}/')

    async def record_evaluation(self, data: Dict) -> Dict:
        return await self.post('/api/v1/evaluations/', data)


class FinanceServiceClient(BaseServiceClient):
    """Client for Finance Service"""

    def __init__(self):
        super().__init__('finance-service')

    async def get_balance(self, user_id: str) -> Dict:
        return await self.get(f'/api/v1/accounts/{user_id}/balance/')

    async def create_transaction(self, data: Dict) -> Dict:
        return await self.post('/api/v1/transactions/', data)

    async def create_invoice(self, data: Dict) -> Dict:
        return await self.post('/api/v1/invoices/', data)

    async def check_sufficient_balance(self, user_id: str, amount: float) -> bool:
        balance = await self.get_balance(user_id)
        return balance.get('available', 0) >= amount


class NotificationServiceClient(BaseServiceClient):
    """Client for Notification Service"""

    def __init__(self):
        super().__init__('notification-service')

    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = 'info',
        channels: List[str] = None
    ) -> Dict:
        return await self.post('/api/v1/notifications/', {
            'user_id': user_id,
            'title': title,
            'message': message,
            'type': notification_type,
            'channels': channels or ['push', 'email']
        })

    async def send_bulk_notification(
        self,
        user_ids: List[str],
        title: str,
        message: str
    ) -> Dict:
        return await self.post('/api/v1/notifications/bulk/', {
            'user_ids': user_ids,
            'title': title,
            'message': message
        })


class DocumentServiceClient(BaseServiceClient):
    """Client for Document Service"""

    def __init__(self):
        super().__init__('document-service')

    async def get_document(self, document_id: str) -> Dict:
        return await self.get(f'/api/v1/documents/{document_id}/')

    async def get_download_url(self, document_id: str) -> str:
        response = await self.get(f'/api/v1/documents/{document_id}/download-url/')
        return response.get('url', '')

    async def delete_document(self, document_id: str) -> Dict:
        return await self.delete(f'/api/v1/documents/{document_id}/')


# =============================================================================
# CLIENT FACTORY
# =============================================================================

class ServiceClientFactory:
    """Factory for creating service clients"""

    _clients = {
        'user': UserServiceClient,
        'organization': OrganizationServiceClient,
        'aircraft': AircraftServiceClient,
        'booking': BookingServiceClient,
        'flight': FlightServiceClient,
        'training': TrainingServiceClient,
        'finance': FinanceServiceClient,
        'notification': NotificationServiceClient,
        'document': DocumentServiceClient,
    }

    @classmethod
    def get_client(cls, service_name: str) -> BaseServiceClient:
        """Get a service client by name"""
        client_class = cls._clients.get(service_name)
        if not client_class:
            raise ValueError(f"Unknown service: {service_name}")
        return client_class()

    @classmethod
    def register_client(cls, name: str, client_class: type):
        """Register a custom client"""
        cls._clients[name] = client_class
