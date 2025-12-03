# services/booking-service/src/apps/api/views/pagination.py
"""
API Pagination

Custom pagination classes for booking API.
"""

from rest_framework.pagination import PageNumberPagination, CursorPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for list views."""

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'count': {
                    'type': 'integer',
                    'example': 123,
                },
                'next': {
                    'type': 'string',
                    'nullable': True,
                    'format': 'uri',
                    'example': 'http://api.example.org/bookings/?page=4',
                },
                'previous': {
                    'type': 'string',
                    'nullable': True,
                    'format': 'uri',
                    'example': 'http://api.example.org/bookings/?page=2',
                },
                'results': schema,
            },
        }


class LargeResultsSetPagination(PageNumberPagination):
    """Larger pagination for bulk operations."""

    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


class BookingCursorPagination(CursorPagination):
    """Cursor-based pagination for real-time booking lists."""

    page_size = 20
    ordering = '-scheduled_start'
    cursor_query_param = 'cursor'


class CalendarPagination(PageNumberPagination):
    """Pagination for calendar views (by week/month)."""

    page_size = 7  # One week of data by default
    page_size_query_param = 'days'
    max_page_size = 31  # Maximum one month
