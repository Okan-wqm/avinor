# shared/common/exceptions.py
"""
Custom Exception Classes and Exception Handler
"""

import logging
import traceback
from typing import Dict, Any, Optional
from rest_framework import status
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.conf import settings

logger = logging.getLogger(__name__)


# =============================================================================
# BASE EXCEPTIONS
# =============================================================================

class BaseAPIException(APIException):
    """Base exception class for all custom API exceptions"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'An unexpected error occurred.'
    default_code = 'error'
    error_code = 'INTERNAL_ERROR'

    def __init__(
        self,
        detail: Optional[str] = None,
        code: Optional[str] = None,
        error_code: Optional[str] = None,
        extra_data: Optional[Dict] = None
    ):
        super().__init__(detail=detail, code=code)
        self.error_code = error_code or self.error_code
        self.extra_data = extra_data or {}


# =============================================================================
# CLIENT ERRORS (4xx)
# =============================================================================

class BadRequestException(BaseAPIException):
    """400 Bad Request"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Bad request.'
    default_code = 'bad_request'
    error_code = 'BAD_REQUEST'


class ValidationException(BaseAPIException):
    """400 Validation Error"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Validation error.'
    default_code = 'validation_error'
    error_code = 'VALIDATION_ERROR'

    def __init__(self, errors: Dict[str, Any], detail: str = None):
        super().__init__(detail=detail)
        self.extra_data = {'errors': errors}


class UnauthorizedException(BaseAPIException):
    """401 Unauthorized"""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Authentication credentials were not provided or are invalid.'
    default_code = 'unauthorized'
    error_code = 'UNAUTHORIZED'


class ForbiddenException(BaseAPIException):
    """403 Forbidden"""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You do not have permission to perform this action.'
    default_code = 'forbidden'
    error_code = 'FORBIDDEN'


class NotFoundException(BaseAPIException):
    """404 Not Found"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'The requested resource was not found.'
    default_code = 'not_found'
    error_code = 'NOT_FOUND'


class ConflictException(BaseAPIException):
    """409 Conflict"""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'A conflict occurred with the current state of the resource.'
    default_code = 'conflict'
    error_code = 'CONFLICT'


class GoneException(BaseAPIException):
    """410 Gone"""
    status_code = status.HTTP_410_GONE
    default_detail = 'The requested resource is no longer available.'
    default_code = 'gone'
    error_code = 'GONE'


class UnprocessableEntityException(BaseAPIException):
    """422 Unprocessable Entity"""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = 'The request was well-formed but could not be processed.'
    default_code = 'unprocessable_entity'
    error_code = 'UNPROCESSABLE_ENTITY'


class TooManyRequestsException(BaseAPIException):
    """429 Too Many Requests"""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = 'Too many requests. Please try again later.'
    default_code = 'too_many_requests'
    error_code = 'RATE_LIMITED'


# =============================================================================
# SERVER ERRORS (5xx)
# =============================================================================

class InternalServerException(BaseAPIException):
    """500 Internal Server Error"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'An internal server error occurred.'
    default_code = 'internal_server_error'
    error_code = 'INTERNAL_ERROR'


class ServiceUnavailableException(BaseAPIException):
    """503 Service Unavailable"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'The service is temporarily unavailable.'
    default_code = 'service_unavailable'
    error_code = 'SERVICE_UNAVAILABLE'


class GatewayTimeoutException(BaseAPIException):
    """504 Gateway Timeout"""
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    default_detail = 'The upstream service did not respond in time.'
    default_code = 'gateway_timeout'
    error_code = 'GATEWAY_TIMEOUT'


# =============================================================================
# DOMAIN-SPECIFIC EXCEPTIONS
# =============================================================================

class ResourceLockedException(BaseAPIException):
    """Resource is locked and cannot be modified"""
    status_code = status.HTTP_423_LOCKED
    default_detail = 'The resource is locked and cannot be modified.'
    default_code = 'locked'
    error_code = 'RESOURCE_LOCKED'


class InsufficientBalanceException(BaseAPIException):
    """Insufficient balance for operation"""
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = 'Insufficient balance to complete this operation.'
    default_code = 'insufficient_balance'
    error_code = 'INSUFFICIENT_BALANCE'


class BookingConflictException(ConflictException):
    """Booking conflict (overlapping reservations)"""
    default_detail = 'The requested time slot conflicts with an existing booking.'
    error_code = 'BOOKING_CONFLICT'


class AircraftUnavailableException(BaseAPIException):
    """Aircraft is not available"""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'The aircraft is not available for the requested time period.'
    default_code = 'aircraft_unavailable'
    error_code = 'AIRCRAFT_UNAVAILABLE'


class InstructorUnavailableException(BaseAPIException):
    """Instructor is not available"""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'The instructor is not available for the requested time period.'
    default_code = 'instructor_unavailable'
    error_code = 'INSTRUCTOR_UNAVAILABLE'


class CertificateExpiredException(BaseAPIException):
    """Certificate has expired"""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'The required certificate has expired.'
    default_code = 'certificate_expired'
    error_code = 'CERTIFICATE_EXPIRED'


class MaintenanceRequiredException(BaseAPIException):
    """Aircraft requires maintenance"""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'The aircraft requires maintenance before it can be used.'
    default_code = 'maintenance_required'
    error_code = 'MAINTENANCE_REQUIRED'


class WeatherMinimumException(BaseAPIException):
    """Weather does not meet minimums"""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = 'Weather conditions do not meet the required minimums.'
    default_code = 'weather_minimum'
    error_code = 'WEATHER_MINIMUM_NOT_MET'


# =============================================================================
# EXCEPTION HANDLER
# =============================================================================

def custom_exception_handler(exc, context) -> Optional[Response]:
    """
    Custom exception handler for DRF.
    Provides consistent error response format across all services.
    """

    # Get the request ID for tracing
    request = context.get('request')
    request_id = getattr(request, 'request_id', None) if request else None

    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    # If DRF handled it, format the response
    if response is not None:
        return format_error_response(exc, response, request_id)

    # Handle Django ValidationError
    if isinstance(exc, DjangoValidationError):
        errors = exc.message_dict if hasattr(exc, 'message_dict') else {'detail': exc.messages}
        return Response(
            {
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Validation error',
                    'details': errors,
                    'request_id': request_id,
                }
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Handle Http404
    if isinstance(exc, Http404):
        return Response(
            {
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': str(exc) or 'Resource not found',
                    'request_id': request_id,
                }
            },
            status=status.HTTP_404_NOT_FOUND
        )

    # Log unexpected exceptions
    logger.exception(
        f"Unhandled exception: {exc}",
        extra={
            'request_id': request_id,
            'exception_type': type(exc).__name__,
            'traceback': traceback.format_exc(),
        }
    )

    # Return generic error in production, detailed in debug
    if settings.DEBUG:
        return Response(
            {
                'success': False,
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': str(exc),
                    'type': type(exc).__name__,
                    'traceback': traceback.format_exc().split('\n'),
                    'request_id': request_id,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response(
        {
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred. Please try again later.',
                'request_id': request_id,
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def format_error_response(exc, response: Response, request_id: str = None) -> Response:
    """Format error response in consistent structure"""

    error_code = getattr(exc, 'error_code', 'ERROR')
    extra_data = getattr(exc, 'extra_data', {})

    error_data = {
        'success': False,
        'error': {
            'code': error_code,
            'message': get_error_message(exc, response),
            'request_id': request_id,
        }
    }

    # Add validation errors if present
    if extra_data.get('errors'):
        error_data['error']['details'] = extra_data['errors']
    elif isinstance(response.data, dict) and 'detail' not in response.data:
        # Field-level validation errors from DRF
        error_data['error']['details'] = response.data

    response.data = error_data
    return response


def get_error_message(exc, response: Response) -> str:
    """Extract error message from exception or response"""

    if hasattr(exc, 'detail'):
        if isinstance(exc.detail, str):
            return exc.detail
        if isinstance(exc.detail, list) and exc.detail:
            return str(exc.detail[0])
        if isinstance(exc.detail, dict):
            return exc.detail.get('detail', str(exc.detail))

    if isinstance(response.data, dict):
        return response.data.get('detail', str(response.data))

    return str(response.data)
