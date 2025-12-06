"""
OpenAPI/Swagger Configuration Module.

Provides standardized OpenAPI configuration for all microservices.
Uses drf-spectacular for schema generation.
"""
from typing import Dict, Any, List, Optional
from functools import wraps


# =============================================================================
# OPENAPI SETTINGS GENERATOR
# =============================================================================

def get_spectacular_settings(
    service_name: str,
    service_description: str,
    version: str = "1.0.0",
    contact_email: str = "api@flighttraining.com",
    terms_of_service: str = "/terms/",
    external_docs_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate drf-spectacular settings for a microservice.

    Args:
        service_name: Name of the service (e.g., "User Service")
        service_description: Description of what the service does
        version: API version
        contact_email: Contact email for API support
        terms_of_service: URL to terms of service
        external_docs_url: URL to external documentation

    Returns:
        Dictionary of drf-spectacular settings
    """
    settings = {
        'TITLE': f'{service_name} API',
        'DESCRIPTION': service_description,
        'VERSION': version,
        'SERVE_INCLUDE_SCHEMA': False,

        # Contact Information
        'CONTACT': {
            'name': 'Flight Training System API Support',
            'email': contact_email,
        },

        # License
        'LICENSE': {
            'name': 'Proprietary',
        },

        # Terms of Service
        'TOS': terms_of_service,

        # Tags for grouping endpoints
        'TAGS': [],

        # Schema configuration
        'COMPONENT_SPLIT_REQUEST': True,
        'COMPONENT_NO_READ_ONLY_REQUIRED': True,

        # Enum handling
        'ENUM_NAME_OVERRIDES': {},
        'ENUM_ADD_EXPLICIT_BLANK_NULL_CHOICE': False,

        # Security
        'SECURITY': [
            {'BearerAuth': []},
        ],

        # Preprocessing hooks
        'PREPROCESSING_HOOKS': [
            'shared.common.openapi.preprocess_exclude_health',
        ],

        # Postprocessing hooks
        'POSTPROCESSING_HOOKS': [
            'shared.common.openapi.postprocess_add_security_schemes',
        ],

        # Schema path prefix
        'SCHEMA_PATH_PREFIX': r'/api/v[0-9]+/',

        # Swagger UI settings
        'SWAGGER_UI_SETTINGS': {
            'deepLinking': True,
            'persistAuthorization': True,
            'displayOperationId': False,
            'filter': True,
            'tagsSorter': 'alpha',
            'operationsSorter': 'alpha',
        },

        # ReDoc settings
        'REDOC_DIST': 'SIDECAR',

        # Sort operations
        'SORT_OPERATIONS': True,

        # Extensions
        'EXTENSIONS_INFO': {},
    }

    if external_docs_url:
        settings['EXTERNAL_DOCS'] = {
            'description': 'External Documentation',
            'url': external_docs_url,
        }

    return settings


# =============================================================================
# PREPROCESSING HOOKS
# =============================================================================

def preprocess_exclude_health(endpoints: List, **kwargs) -> List:
    """
    Exclude health check endpoints from API documentation.

    Args:
        endpoints: List of endpoint tuples

    Returns:
        Filtered list of endpoints
    """
    excluded_paths = [
        '/health/',
        '/health/live/',
        '/health/ready/',
        '/health/detailed/',
    ]

    return [
        (path, path_regex, method, callback)
        for path, path_regex, method, callback in endpoints
        if not any(path.endswith(excluded) for excluded in excluded_paths)
    ]


def preprocess_exclude_internal(endpoints: List, **kwargs) -> List:
    """
    Exclude internal endpoints from public API documentation.

    Args:
        endpoints: List of endpoint tuples

    Returns:
        Filtered list of endpoints
    """
    return [
        (path, path_regex, method, callback)
        for path, path_regex, method, callback in endpoints
        if '/internal/' not in path
    ]


# =============================================================================
# POSTPROCESSING HOOKS
# =============================================================================

def postprocess_add_security_schemes(result: Dict, **kwargs) -> Dict:
    """
    Add security schemes to OpenAPI schema.

    Args:
        result: OpenAPI schema dictionary

    Returns:
        Modified schema with security schemes
    """
    if 'components' not in result:
        result['components'] = {}

    result['components']['securitySchemes'] = {
        'BearerAuth': {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
            'description': 'JWT Authorization header using the Bearer scheme.',
        },
        'ApiKeyAuth': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-API-Key',
            'description': 'API key for service-to-service communication.',
        },
        'OrganizationId': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-Organization-ID',
            'description': 'Organization identifier for multi-tenant isolation.',
        },
    }

    return result


def postprocess_add_common_responses(result: Dict, **kwargs) -> Dict:
    """
    Add common response schemas to OpenAPI documentation.

    Args:
        result: OpenAPI schema dictionary

    Returns:
        Modified schema with common responses
    """
    if 'components' not in result:
        result['components'] = {}

    if 'schemas' not in result['components']:
        result['components']['schemas'] = {}

    # Add common error response schemas
    result['components']['schemas'].update({
        'ErrorResponse': {
            'type': 'object',
            'properties': {
                'error': {
                    'type': 'object',
                    'properties': {
                        'code': {
                            'type': 'string',
                            'description': 'Error code',
                            'example': 'VALIDATION_ERROR',
                        },
                        'message': {
                            'type': 'string',
                            'description': 'Human-readable error message',
                            'example': 'Invalid input data',
                        },
                        'details': {
                            'type': 'object',
                            'description': 'Additional error details',
                            'additionalProperties': True,
                        },
                    },
                    'required': ['code', 'message'],
                },
            },
            'required': ['error'],
        },
        'ValidationErrorResponse': {
            'type': 'object',
            'properties': {
                'error': {
                    'type': 'object',
                    'properties': {
                        'code': {
                            'type': 'string',
                            'example': 'VALIDATION_ERROR',
                        },
                        'message': {
                            'type': 'string',
                            'example': 'Validation failed',
                        },
                        'fields': {
                            'type': 'object',
                            'additionalProperties': {
                                'type': 'array',
                                'items': {'type': 'string'},
                            },
                            'example': {
                                'email': ['This field is required.'],
                                'password': ['Password must be at least 8 characters.'],
                            },
                        },
                    },
                },
            },
        },
        'PaginatedResponse': {
            'type': 'object',
            'properties': {
                'count': {
                    'type': 'integer',
                    'description': 'Total number of items',
                    'example': 100,
                },
                'next': {
                    'type': 'string',
                    'format': 'uri',
                    'nullable': True,
                    'description': 'URL to next page',
                },
                'previous': {
                    'type': 'string',
                    'format': 'uri',
                    'nullable': True,
                    'description': 'URL to previous page',
                },
                'results': {
                    'type': 'array',
                    'items': {},
                    'description': 'Page results',
                },
            },
        },
    })

    return result


# =============================================================================
# SCHEMA DECORATORS
# =============================================================================

def api_docs(
    summary: str = None,
    description: str = None,
    tags: List[str] = None,
    deprecated: bool = False,
    operation_id: str = None,
    request_body: Any = None,
    responses: Dict = None,
    parameters: List = None,
    examples: Dict = None,
):
    """
    Decorator for adding OpenAPI documentation to view methods.

    Usage:
        @api_docs(
            summary="Create a new user",
            description="Creates a new user account with the given data.",
            tags=["Users"],
            responses={
                201: UserSerializer,
                400: "Validation error",
            }
        )
        def create(self, request):
            ...
    """
    def decorator(func):
        # Store documentation metadata on function
        func._api_docs = {
            'summary': summary,
            'description': description,
            'tags': tags or [],
            'deprecated': deprecated,
            'operation_id': operation_id,
            'request_body': request_body,
            'responses': responses or {},
            'parameters': parameters or [],
            'examples': examples or {},
        }

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper
    return decorator


# =============================================================================
# URL PATTERNS FOR DOCUMENTATION
# =============================================================================

def get_api_docs_urlpatterns(title: str = "API Documentation"):
    """
    Returns URL patterns for API documentation endpoints.

    Usage in urls.py:
        from shared.common.openapi import get_api_docs_urlpatterns
        urlpatterns += get_api_docs_urlpatterns("User Service API")

    Returns:
        List of URL patterns for Swagger UI and ReDoc
    """
    from django.urls import path

    try:
        from drf_spectacular.views import (
            SpectacularAPIView,
            SpectacularSwaggerView,
            SpectacularRedocView,
        )

        return [
            # OpenAPI Schema (JSON/YAML)
            path(
                'api/schema/',
                SpectacularAPIView.as_view(),
                name='schema'
            ),
            # Swagger UI
            path(
                'api/docs/',
                SpectacularSwaggerView.as_view(url_name='schema'),
                name='swagger-ui'
            ),
            # ReDoc
            path(
                'api/redoc/',
                SpectacularRedocView.as_view(url_name='schema'),
                name='redoc'
            ),
        ]
    except ImportError:
        # drf-spectacular not installed
        return []


# =============================================================================
# SERVICE-SPECIFIC CONFIGURATIONS
# =============================================================================

# User Service
USER_SERVICE_OPENAPI = get_spectacular_settings(
    service_name="User Service",
    service_description="""
    User Management and Authentication Service.

    Provides user authentication, authorization, profile management,
    and role-based access control for the Flight Training System.

    ## Features
    - User registration and authentication
    - JWT token management
    - Role and permission management
    - User profile CRUD operations
    - Password reset and email verification
    - Multi-tenant user isolation
    """,
    version="1.0.0",
)

# Organization Service
ORGANIZATION_SERVICE_OPENAPI = get_spectacular_settings(
    service_name="Organization Service",
    service_description="""
    Organization and Multi-Tenancy Management Service.

    Manages flight training organizations, their settings,
    and multi-tenant data isolation.

    ## Features
    - Organization CRUD operations
    - Organization settings management
    - Member management
    - Subscription and billing integration
    - Organization-level permissions
    """,
    version="1.0.0",
)

# Aircraft Service
AIRCRAFT_SERVICE_OPENAPI = get_spectacular_settings(
    service_name="Aircraft Service",
    service_description="""
    Aircraft Fleet Management Service.

    Manages aircraft inventory, maintenance tracking,
    and airworthiness documentation.

    ## Features
    - Aircraft registration and management
    - Maintenance schedule tracking
    - Airworthiness directive compliance
    - Component and part tracking
    - Squawk and discrepancy management
    - MEL (Minimum Equipment List) management
    """,
    version="1.0.0",
)

# Booking Service
BOOKING_SERVICE_OPENAPI = get_spectacular_settings(
    service_name="Booking Service",
    service_description="""
    Resource Booking and Scheduling Service.

    Handles reservations for aircraft, instructors,
    classrooms, and other training resources.

    ## Features
    - Resource availability management
    - Booking creation and management
    - Recurring booking support
    - Conflict detection and resolution
    - Waitlist management
    - Booking notifications
    """,
    version="1.0.0",
)

# Flight Service
FLIGHT_SERVICE_OPENAPI = get_spectacular_settings(
    service_name="Flight Service",
    service_description="""
    Flight Operations and Logging Service.

    Manages flight operations, digital logbooks,
    and flight time tracking.

    ## Features
    - Flight dispatch and tracking
    - Digital pilot logbook
    - Flight time calculations
    - Route and fuel management
    - Weight and balance calculations
    - Flight safety documentation
    """,
    version="1.0.0",
)

# Weather Service
WEATHER_SERVICE_OPENAPI = get_spectacular_settings(
    service_name="Weather Service",
    service_description="""
    Aviation Weather Data Service.

    Provides real-time and forecast weather data
    for flight planning and operations.

    ## Features
    - METAR and TAF data
    - NOTAM integration
    - TFR (Temporary Flight Restriction) data
    - Weather briefing generation
    - Graphical weather products
    - Custom weather alerts
    """,
    version="1.0.0",
)

# Training Service
TRAINING_SERVICE_OPENAPI = get_spectacular_settings(
    service_name="Training Service",
    service_description="""
    Flight Training Program Management Service.

    Manages training syllabi, student progress,
    and certification requirements.

    ## Features
    - Syllabus management
    - Training record tracking
    - Stage check scheduling
    - Endorsement management
    - Competency-based training support
    - Training analytics and reporting
    """,
    version="1.0.0",
)

# Theory Service
THEORY_SERVICE_OPENAPI = get_spectacular_settings(
    service_name="Theory Service",
    service_description="""
    Ground School and Online Learning Service.

    Manages theoretical training content, online courses,
    and knowledge assessments.

    ## Features
    - Course content management
    - Quiz and exam creation
    - Progress tracking
    - Certificate generation
    - SCORM compliance
    - Video streaming integration
    """,
    version="1.0.0",
)

# Certificate Service
CERTIFICATE_SERVICE_OPENAPI = get_spectacular_settings(
    service_name="Certificate Service",
    service_description="""
    Pilot Certification and Currency Management Service.

    Tracks pilot certificates, ratings, medical certificates,
    and currency requirements.

    ## Features
    - Certificate and rating tracking
    - Medical certificate management
    - Currency requirement monitoring
    - Endorsement verification
    - Regulatory compliance checking
    - Certificate expiration alerts
    """,
    version="1.0.0",
)

# Finance Service
FINANCE_SERVICE_OPENAPI = get_spectacular_settings(
    service_name="Finance Service",
    service_description="""
    Financial Management and Billing Service.

    Handles accounts, transactions, invoicing,
    and payment processing.

    ## Features
    - Account management
    - Transaction processing
    - Invoice generation
    - Payment gateway integration
    - Pricing rule management
    - Financial reporting
    """,
    version="1.0.0",
)

# Notification Service
NOTIFICATION_SERVICE_OPENAPI = get_spectacular_settings(
    service_name="Notification Service",
    service_description="""
    Multi-Channel Notification Service.

    Delivers notifications across email, SMS, push,
    and in-app channels.

    ## Features
    - Template-based notifications
    - Multi-channel delivery
    - User preference management
    - Batch notification processing
    - Delivery tracking and analytics
    - Scheduled notifications
    """,
    version="1.0.0",
)

# Report Service
REPORT_SERVICE_OPENAPI = get_spectacular_settings(
    service_name="Report Service",
    service_description="""
    Reporting and Analytics Service.

    Generates reports, dashboards, and analytics
    for flight training operations.

    ## Features
    - Custom report templates
    - Scheduled report generation
    - Dashboard management
    - Widget-based visualizations
    - Multi-format export (PDF, Excel, CSV)
    - Data aggregation and analytics
    """,
    version="1.0.0",
)

# Document Service
DOCUMENT_SERVICE_OPENAPI = get_spectacular_settings(
    service_name="Document Service",
    service_description="""
    Document Management Service.

    Manages document storage, versioning,
    and organization.

    ## Features
    - Document upload and storage
    - Version control
    - Category and tagging
    - Access control
    - Full-text search
    - Document templates
    """,
    version="1.0.0",
)

# Audit Service
AUDIT_SERVICE_OPENAPI = get_spectacular_settings(
    service_name="Audit Service",
    service_description="""
    Audit Logging and Compliance Service.

    Tracks system activity and maintains audit trails
    for regulatory compliance.

    ## Features
    - Activity logging
    - Audit trail maintenance
    - Compliance reporting
    - Data retention management
    - Security event tracking
    - Change history
    """,
    version="1.0.0",
)
