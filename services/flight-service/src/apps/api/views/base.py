# services/flight-service/src/apps/api/views/base.py
"""
Base Views and Mixins

Common functionality for Flight Service API views.
"""

import logging
from typing import Optional
from uuid import UUID

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from apps.core.services.exceptions import (
    FlightServiceError,
    FlightNotFoundError,
    FlightValidationError,
    FlightStateError,
    FlightPermissionError,
    LogbookError,
    CurrencyError,
    StatisticsError,
)

logger = logging.getLogger(__name__)


class OrganizationMixin:
    """
    Mixin for extracting organization context from request.

    Expects organization_id to be provided via:
    - Request header: X-Organization-ID
    - Request query param: organization_id
    - JWT token claim (if using auth)
    """

    def get_organization_id(self) -> UUID:
        """
        Extract organization ID from request.

        Returns:
            Organization UUID

        Raises:
            ValidationError: If organization ID not provided
        """
        # Try header first
        org_id = self.request.headers.get('X-Organization-ID')

        # Then try query param
        if not org_id:
            org_id = self.request.query_params.get('organization_id')

        # Then try request data
        if not org_id and hasattr(self.request, 'data'):
            org_id = self.request.data.get('organization_id')

        # Then try JWT claims (if using auth middleware)
        if not org_id and hasattr(self.request, 'auth'):
            org_id = getattr(self.request.auth, 'organization_id', None)

        if not org_id:
            raise FlightValidationError(
                message="Organization ID is required",
                field="organization_id"
            )

        try:
            return UUID(str(org_id))
        except ValueError:
            raise FlightValidationError(
                message="Invalid organization ID format",
                field="organization_id"
            )


class UserContextMixin:
    """
    Mixin for extracting user context from request.

    Expects user_id to be provided via:
    - Request header: X-User-ID
    - JWT token claim (if using auth)
    """

    def get_user_id(self) -> UUID:
        """
        Extract user ID from request.

        Returns:
            User UUID

        Raises:
            ValidationError: If user ID not provided
        """
        # Try header first
        user_id = self.request.headers.get('X-User-ID')

        # Then try JWT claims
        if not user_id and hasattr(self.request, 'auth'):
            user_id = getattr(self.request.auth, 'user_id', None)

        # Then try request.user
        if not user_id and hasattr(self.request, 'user'):
            user_id = getattr(self.request.user, 'id', None)

        if not user_id:
            raise FlightValidationError(
                message="User ID is required",
                field="user_id"
            )

        try:
            return UUID(str(user_id))
        except ValueError:
            raise FlightValidationError(
                message="Invalid user ID format",
                field="user_id"
            )

    def get_optional_user_id(self) -> Optional[UUID]:
        """
        Extract user ID from request, returning None if not provided.

        Returns:
            User UUID or None
        """
        try:
            return self.get_user_id()
        except FlightValidationError:
            return None


class ExceptionHandlerMixin:
    """Mixin for handling service layer exceptions."""

    def handle_exception(self, exc):
        """Convert service exceptions to appropriate HTTP responses."""

        if isinstance(exc, FlightNotFoundError):
            return Response(
                exc.to_dict(),
                status=status.HTTP_404_NOT_FOUND
            )

        if isinstance(exc, FlightValidationError):
            return Response(
                exc.to_dict(),
                status=status.HTTP_400_BAD_REQUEST
            )

        if isinstance(exc, FlightStateError):
            return Response(
                exc.to_dict(),
                status=status.HTTP_409_CONFLICT
            )

        if isinstance(exc, FlightPermissionError):
            return Response(
                exc.to_dict(),
                status=status.HTTP_403_FORBIDDEN
            )

        if isinstance(exc, (LogbookError, CurrencyError, StatisticsError)):
            return Response(
                exc.to_dict(),
                status=status.HTTP_400_BAD_REQUEST
            )

        if isinstance(exc, FlightServiceError):
            return Response(
                exc.to_dict(),
                status=status.HTTP_400_BAD_REQUEST
            )

        # Re-raise for default handling
        raise exc


class BaseFlightViewSet(
    OrganizationMixin,
    UserContextMixin,
    ExceptionHandlerMixin,
    ViewSet
):
    """
    Base ViewSet for Flight Service.

    Provides organization and user context extraction,
    plus exception handling.
    """

    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to handle exceptions."""
        try:
            return super().dispatch(request, *args, **kwargs)
        except FlightServiceError as e:
            return self.handle_exception(e)

    def get_serializer_context(self):
        """Add organization and user to serializer context."""
        context = {
            'request': self.request,
            'view': self,
        }
        try:
            context['organization_id'] = self.get_organization_id()
        except FlightValidationError:
            pass
        try:
            context['user_id'] = self.get_user_id()
        except FlightValidationError:
            pass
        return context


class PaginationMixin:
    """Mixin for pagination support."""

    default_page_size = 20
    max_page_size = 100

    def get_pagination_params(self):
        """Extract pagination parameters from request."""
        try:
            page = int(self.request.query_params.get('page', 1))
            page = max(1, page)
        except (TypeError, ValueError):
            page = 1

        try:
            page_size = int(self.request.query_params.get('page_size', self.default_page_size))
            page_size = min(max(1, page_size), self.max_page_size)
        except (TypeError, ValueError):
            page_size = self.default_page_size

        return page, page_size


class FilterMixin:
    """Mixin for filtering support."""

    def get_filters(self, filter_serializer_class):
        """
        Extract and validate filters from request.

        Args:
            filter_serializer_class: Serializer class for filter validation

        Returns:
            Dictionary of validated filters
        """
        serializer = filter_serializer_class(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        return {k: v for k, v in serializer.validated_data.items() if v is not None}


class DateRangeMixin:
    """Mixin for date range filtering."""

    def get_date_range(self):
        """Extract date range from request."""
        from datetime import datetime

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                raise FlightValidationError(
                    message="Invalid start_date format. Use YYYY-MM-DD.",
                    field="start_date"
                )

        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                raise FlightValidationError(
                    message="Invalid end_date format. Use YYYY-MM-DD.",
                    field="end_date"
                )

        if start_date and end_date and end_date < start_date:
            raise FlightValidationError(
                message="end_date must be after start_date",
                field="end_date"
            )

        return start_date, end_date
