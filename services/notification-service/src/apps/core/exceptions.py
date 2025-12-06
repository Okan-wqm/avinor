"""
Notification Service Exceptions.
"""
from rest_framework import status
from rest_framework.exceptions import APIException


class NotificationServiceException(APIException):
    """Base exception for notification service."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "An error occurred in the notification service."
    default_code = "notification_service_error"


class TemplateNotFound(NotificationServiceException):
    """Raised when a template is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Notification template not found."
    default_code = "template_not_found"


class NotificationNotFound(NotificationServiceException):
    """Raised when a notification is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Notification not found."
    default_code = "notification_not_found"


class InvalidChannel(NotificationServiceException):
    """Raised when notification channel is invalid."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid notification channel."
    default_code = "invalid_channel"


class DeliveryFailed(NotificationServiceException):
    """Raised when notification delivery fails."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Failed to deliver notification."
    default_code = "delivery_failed"


class RecipientRequired(NotificationServiceException):
    """Raised when recipient is not provided."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Recipient is required."
    default_code = "recipient_required"


class RateLimitExceeded(NotificationServiceException):
    """Raised when rate limit is exceeded."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Rate limit exceeded. Please try again later."
    default_code = "rate_limit_exceeded"


class InvalidTemplate(NotificationServiceException):
    """Raised when template content is invalid."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid template content."
    default_code = "invalid_template"


class BatchNotFound(NotificationServiceException):
    """Raised when a batch is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Notification batch not found."
    default_code = "batch_not_found"
