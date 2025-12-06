# Shared Common Library for Flight Training Management System
# This package contains shared utilities, authentication, permissions,
# and other common components used across all microservices.

__version__ = "1.0.0"

# Export commonly used components
from .exceptions import (
    BaseServiceException,
    ValidationError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    RateLimitError,
    ServiceUnavailableError,
    ExternalServiceError,
)

from .validators import (
    validate_uuid,
    validate_email,
    validate_phone_number,
    validate_date_range,
    validate_required_fields,
)

from .constants import (
    UserRole,
    UserStatus,
    AircraftCategory,
    BookingStatus,
    FlightStatus,
    SERVICE_PORTS,
    ERROR_CODES,
)

from .health import (
    HealthStatus,
    check_database,
    check_cache,
    check_nats,
    check_celery,
    get_health_urlpatterns,
)

from .openapi import (
    get_spectacular_settings,
    get_api_docs_urlpatterns,
    api_docs,
)

__all__ = [
    # Version
    '__version__',

    # Exceptions
    'BaseServiceException',
    'ValidationError',
    'NotFoundError',
    'AuthenticationError',
    'AuthorizationError',
    'ConflictError',
    'RateLimitError',
    'ServiceUnavailableError',
    'ExternalServiceError',

    # Validators
    'validate_uuid',
    'validate_email',
    'validate_phone_number',
    'validate_date_range',
    'validate_required_fields',

    # Constants
    'UserRole',
    'UserStatus',
    'AircraftCategory',
    'BookingStatus',
    'FlightStatus',
    'SERVICE_PORTS',
    'ERROR_CODES',

    # Health
    'HealthStatus',
    'check_database',
    'check_cache',
    'check_nats',
    'check_celery',
    'get_health_urlpatterns',

    # OpenAPI
    'get_spectacular_settings',
    'get_api_docs_urlpatterns',
    'api_docs',
]
