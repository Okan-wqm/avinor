# shared/common/pagination.py
"""
Custom Pagination Classes for API responses
"""

from rest_framework.pagination import (
    PageNumberPagination,
    LimitOffsetPagination,
    CursorPagination
)
from rest_framework.response import Response
from collections import OrderedDict
from typing import Any, Dict


class StandardPagination(PageNumberPagination):
    """
    Standard page number pagination with configurable page size.
    Returns total count, page info, and navigation links.
    """

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'

    def get_paginated_response(self, data: Any) -> Response:
        return Response(OrderedDict([
            ('success', True),
            ('count', self.page.paginator.count),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.get_page_size(self.request)),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))

    def get_paginated_response_schema(self, schema: Dict) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean', 'example': True},
                'count': {'type': 'integer', 'example': 100},
                'total_pages': {'type': 'integer', 'example': 5},
                'current_page': {'type': 'integer', 'example': 1},
                'page_size': {'type': 'integer', 'example': 20},
                'next': {'type': 'string', 'nullable': True},
                'previous': {'type': 'string', 'nullable': True},
                'results': schema,
            }
        }


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination for large result sets with higher default page size.
    """

    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500

    def get_paginated_response(self, data: Any) -> Response:
        return Response(OrderedDict([
            ('success', True),
            ('count', self.page.paginator.count),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.get_page_size(self.request)),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


class SmallResultsSetPagination(PageNumberPagination):
    """
    Pagination for small result sets or embedded resources.
    """

    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

    def get_paginated_response(self, data: Any) -> Response:
        return Response(OrderedDict([
            ('success', True),
            ('count', self.page.paginator.count),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.get_page_size(self.request)),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


class OffsetPagination(LimitOffsetPagination):
    """
    Offset-based pagination for more precise control.
    Useful for data grids and tables.
    """

    default_limit = 20
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 100

    def get_paginated_response(self, data: Any) -> Response:
        return Response(OrderedDict([
            ('success', True),
            ('count', self.count),
            ('limit', self.limit),
            ('offset', self.offset),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


class CursorBasedPagination(CursorPagination):
    """
    Cursor-based pagination for real-time data and infinite scroll.
    More efficient for large datasets and prevents page drift.
    """

    page_size = 20
    cursor_query_param = 'cursor'
    ordering = '-created_at'  # Default ordering

    def get_paginated_response(self, data: Any) -> Response:
        return Response(OrderedDict([
            ('success', True),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


class TimeBasedPagination(CursorPagination):
    """
    Cursor pagination optimized for time-series data.
    Orders by timestamp for consistent pagination.
    """

    page_size = 50
    cursor_query_param = 'cursor'
    ordering = '-timestamp'
    page_size_query_param = 'page_size'
    max_page_size = 200

    def get_paginated_response(self, data: Any) -> Response:
        return Response(OrderedDict([
            ('success', True),
            ('page_size', self.page_size),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


class NoPagination:
    """
    Dummy pagination class when pagination is not needed.
    Returns all results.
    """

    display_page_controls = False

    def paginate_queryset(self, queryset, request, view=None):
        return None

    def get_paginated_response(self, data: Any) -> Response:
        return Response(OrderedDict([
            ('success', True),
            ('count', len(data)),
            ('results', data)
        ]))


def get_pagination_class(pagination_type: str = 'standard'):
    """
    Factory function to get pagination class by type.

    Args:
        pagination_type: One of 'standard', 'large', 'small', 'offset', 'cursor', 'time', 'none'

    Returns:
        Pagination class
    """
    pagination_classes = {
        'standard': StandardPagination,
        'large': LargeResultsSetPagination,
        'small': SmallResultsSetPagination,
        'offset': OffsetPagination,
        'cursor': CursorBasedPagination,
        'time': TimeBasedPagination,
        'none': NoPagination,
    }

    return pagination_classes.get(pagination_type, StandardPagination)
