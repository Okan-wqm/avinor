# services/organization-service/src/apps/core/tests/test_middleware.py
"""
Middleware Tests

Unit tests for Organization Service middleware components.
"""

import uuid
from unittest.mock import Mock, patch, MagicMock

import pytest
from django.http import HttpRequest, JsonResponse
from django.test import RequestFactory

from apps.core.middleware import (
    TenantMiddleware,
    get_current_organization,
    set_current_organization,
    clear_current_organization,
    OrganizationContext,
)
from apps.core.middleware.audit import AuditMiddleware
from apps.core.middleware.rate_limit import RateLimitMiddleware


# =============================================================================
# Tenant Middleware Tests
# =============================================================================

@pytest.mark.django_db
class TestTenantMiddleware:
    """Tests for TenantMiddleware."""

    @pytest.fixture
    def request_factory(self):
        return RequestFactory()

    @pytest.fixture
    def mock_get_response(self):
        def get_response(request):
            return JsonResponse({'status': 'ok'})
        return get_response

    @pytest.fixture
    def middleware(self, mock_get_response):
        return TenantMiddleware(mock_get_response)

    def test_exempt_path_health_check(self, middleware, request_factory):
        """Test that health check is exempt from tenant middleware."""
        request = request_factory.get('/health/')
        response = middleware(request)

        assert response.status_code == 200

    def test_exempt_path_subscription_plans(self, middleware, request_factory):
        """Test that subscription plans endpoint is exempt."""
        request = request_factory.get('/api/v1/subscription-plans/')
        response = middleware(request)

        assert response.status_code == 200

    def test_extract_org_from_url(self, middleware, request_factory, test_organization):
        """Test extracting organization ID from URL path."""
        request = request_factory.get(
            f'/api/v1/organizations/{test_organization.id}/locations/'
        )

        with patch.object(middleware, '_load_organization_context') as mock_load:
            mock_load.return_value = OrganizationContext(
                organization_id=test_organization.id,
                organization_name=test_organization.name,
                is_active=True,
            )
            response = middleware(request)

        assert hasattr(request, 'organization')

    def test_extract_org_from_header(self, middleware, request_factory, test_organization):
        """Test extracting organization ID from X-Organization-ID header."""
        request = request_factory.get(
            '/api/v1/some-endpoint/',
            HTTP_X_ORGANIZATION_ID=str(test_organization.id)
        )

        with patch.object(middleware, '_load_organization_context') as mock_load:
            mock_load.return_value = OrganizationContext(
                organization_id=test_organization.id,
                is_active=True,
            )
            response = middleware(request)

    def test_inactive_organization_forbidden(self, middleware, request_factory, test_organization):
        """Test that inactive organization returns 403."""
        request = request_factory.get(
            f'/api/v1/organizations/{test_organization.id}/locations/'
        )

        with patch.object(middleware, '_load_organization_context') as mock_load:
            mock_load.return_value = OrganizationContext(
                organization_id=test_organization.id,
                is_active=False,  # Inactive
            )
            response = middleware(request)

        assert response.status_code == 403

    def test_context_cleared_after_request(self, middleware, request_factory, test_organization):
        """Test that organization context is cleared after request."""
        request = request_factory.get('/health/')

        # Set some context before
        set_current_organization(OrganizationContext(
            organization_id=uuid.uuid4(),
        ))

        middleware(request)

        # Context should be cleared
        assert get_current_organization() is None


# =============================================================================
# Organization Context Tests
# =============================================================================

class TestOrganizationContext:
    """Tests for OrganizationContext."""

    def test_has_feature(self):
        """Test has_feature method."""
        context = OrganizationContext(
            organization_id=uuid.uuid4(),
            features={'scheduling': True, 'reporting': False},
        )

        assert context.has_feature('scheduling') is True
        assert context.has_feature('reporting') is False
        assert context.has_feature('nonexistent') is False

    def test_has_feature_no_features(self):
        """Test has_feature when features is None."""
        context = OrganizationContext(
            organization_id=uuid.uuid4(),
            features=None,
        )

        assert context.has_feature('anything') is False

    def test_get_limit(self):
        """Test get_limit method."""
        context = OrganizationContext(
            organization_id=uuid.uuid4(),
            limits={'max_users': 10, 'max_aircraft': 5},
        )

        assert context.get_limit('max_users') == 10
        assert context.get_limit('max_aircraft') == 5
        assert context.get_limit('nonexistent', default=100) == 100

    def test_get_limit_no_limits(self):
        """Test get_limit when limits is None."""
        context = OrganizationContext(
            organization_id=uuid.uuid4(),
            limits=None,
        )

        assert context.get_limit('max_users', default=5) == 5


# =============================================================================
# Thread-Local Context Tests
# =============================================================================

class TestThreadLocalContext:
    """Tests for thread-local organization context."""

    def test_set_and_get_context(self):
        """Test setting and getting context."""
        org_id = uuid.uuid4()
        context = OrganizationContext(
            organization_id=org_id,
            organization_name='Test Org',
        )

        set_current_organization(context)
        retrieved = get_current_organization()

        assert retrieved is not None
        assert retrieved.organization_id == org_id
        assert retrieved.organization_name == 'Test Org'

        # Clean up
        clear_current_organization()

    def test_clear_context(self):
        """Test clearing context."""
        context = OrganizationContext(organization_id=uuid.uuid4())
        set_current_organization(context)

        clear_current_organization()

        assert get_current_organization() is None

    def test_clear_nonexistent_context(self):
        """Test clearing when no context exists."""
        clear_current_organization()  # Should not raise
        assert get_current_organization() is None


# =============================================================================
# Audit Middleware Tests
# =============================================================================

@pytest.mark.django_db
class TestAuditMiddleware:
    """Tests for AuditMiddleware."""

    @pytest.fixture
    def request_factory(self):
        return RequestFactory()

    @pytest.fixture
    def mock_get_response(self):
        def get_response(request):
            return JsonResponse({'status': 'ok'})
        return get_response

    @pytest.fixture
    def middleware(self, mock_get_response):
        return AuditMiddleware(mock_get_response)

    def test_adds_request_id(self, middleware, request_factory):
        """Test that request ID is added to response headers."""
        request = request_factory.get('/api/v1/organizations/')
        response = middleware(request)

        assert 'X-Request-ID' in response

    def test_excluded_path_health(self, middleware, request_factory):
        """Test that health endpoint is excluded from audit logging."""
        request = request_factory.get('/health/')

        with patch('apps.core.middleware.audit.logger') as mock_logger:
            response = middleware(request)
            # Should not log for health check
            mock_logger.info.assert_not_called()

    def test_logs_mutations(self, middleware, request_factory):
        """Test that mutation requests are logged."""
        request = request_factory.post(
            '/api/v1/organizations/',
            data='{"name": "Test"}',
            content_type='application/json'
        )

        with patch('apps.core.middleware.audit.logger') as mock_logger:
            response = middleware(request)
            mock_logger.info.assert_called()

    def test_masks_sensitive_data(self, middleware):
        """Test that sensitive fields are masked."""
        data = {
            'username': 'testuser',
            'password': 'secret123',
            'api_key': 'key123',
        }

        masked = middleware._mask_sensitive_data(data)

        assert masked['username'] == 'testuser'
        assert masked['password'] == '***MASKED***'
        assert masked['api_key'] == '***MASKED***'


# =============================================================================
# Rate Limit Middleware Tests
# =============================================================================

@pytest.mark.django_db
class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    @pytest.fixture
    def request_factory(self):
        return RequestFactory()

    @pytest.fixture
    def mock_get_response(self):
        def get_response(request):
            response = JsonResponse({'status': 'ok'})
            return response
        return get_response

    @pytest.fixture
    def middleware(self, mock_get_response):
        middleware = RateLimitMiddleware(mock_get_response)
        middleware.enabled = True
        return middleware

    def test_adds_rate_limit_headers(self, middleware, request_factory, test_user):
        """Test that rate limit headers are added."""
        request = request_factory.get('/api/v1/organizations/')
        request.user = test_user

        with patch.object(middleware, '_check_rate_limit', return_value=(True, 99, 1234567890)):
            response = middleware(request)

        assert 'X-RateLimit-Limit' in response
        assert 'X-RateLimit-Remaining' in response
        assert 'X-RateLimit-Reset' in response

    def test_exempt_health_endpoint(self, middleware, request_factory):
        """Test that health endpoint is exempt from rate limiting."""
        request = request_factory.get('/health/')
        response = middleware(request)

        assert response.status_code == 200
        assert 'X-RateLimit-Limit' not in response

    def test_rate_limit_exceeded(self, middleware, request_factory, test_user):
        """Test rate limit exceeded response."""
        request = request_factory.get('/api/v1/organizations/')
        request.user = test_user

        with patch.object(middleware, '_check_rate_limit', return_value=(False, 0, 1234567890)):
            with patch.object(middleware, '_get_rate_limit_config', return_value=('key', 100)):
                response = middleware(request)

        assert response.status_code == 429
        assert 'Retry-After' in response

    def test_get_client_ip_from_forwarded(self, middleware, request_factory):
        """Test extracting client IP from X-Forwarded-For."""
        request = request_factory.get(
            '/api/v1/organizations/',
            HTTP_X_FORWARDED_FOR='192.168.1.1, 10.0.0.1'
        )

        ip = middleware._get_client_ip(request)
        assert ip == '192.168.1.1'

    def test_get_client_ip_from_remote_addr(self, middleware, request_factory):
        """Test extracting client IP from REMOTE_ADDR."""
        request = request_factory.get('/api/v1/organizations/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        ip = middleware._get_client_ip(request)
        assert ip == '127.0.0.1'
