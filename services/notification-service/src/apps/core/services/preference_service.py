"""
Preference Service.

Business logic for managing notification preferences.
"""
import logging
from typing import Optional, Dict
from uuid import UUID

from django.db import transaction

from ..models import NotificationPreference, DeviceToken

logger = logging.getLogger(__name__)


class PreferenceService:
    """Service for managing notification preferences."""

    @staticmethod
    def get_for_user(user_id: UUID) -> NotificationPreference:
        """Get or create preferences for a user."""
        preference, created = NotificationPreference.objects.get_or_create(
            user_id=user_id,
            defaults={
                'email_enabled': True,
                'sms_enabled': False,
                'push_enabled': True,
                'in_app_enabled': True,
            }
        )
        if created:
            logger.info(f"Created default preferences for user {user_id}")
        return preference

    @staticmethod
    @transaction.atomic
    def update(user_id: UUID, **updates) -> NotificationPreference:
        """Update user preferences."""
        preference = PreferenceService.get_for_user(user_id)

        allowed_fields = [
            'email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled',
            'category_preferences', 'quiet_hours_enabled', 'quiet_hours_start',
            'quiet_hours_end', 'timezone'
        ]

        for field, value in updates.items():
            if field in allowed_fields:
                setattr(preference, field, value)

        preference.save()
        logger.info(f"Updated preferences for user {user_id}")
        return preference

    @staticmethod
    def is_channel_enabled(user_id: UUID, channel: str) -> bool:
        """Check if a channel is enabled for a user."""
        preference = PreferenceService.get_for_user(user_id)

        channel_map = {
            'email': preference.email_enabled,
            'sms': preference.sms_enabled,
            'push': preference.push_enabled,
            'in_app': preference.in_app_enabled,
        }

        return channel_map.get(channel, True)

    @staticmethod
    def is_category_enabled(user_id: UUID, category: str) -> bool:
        """Check if a notification category is enabled for a user."""
        preference = PreferenceService.get_for_user(user_id)
        return preference.category_preferences.get(category, True)

    @staticmethod
    def register_device(
        user_id: UUID,
        token: str,
        platform: str,
        device_name: str = ""
    ) -> DeviceToken:
        """Register a device for push notifications."""
        device, created = DeviceToken.objects.update_or_create(
            user_id=user_id,
            token=token,
            defaults={
                'platform': platform,
                'device_name': device_name,
                'is_active': True,
            }
        )

        logger.info(f"{'Registered' if created else 'Updated'} device for user {user_id}")
        return device

    @staticmethod
    def unregister_device(user_id: UUID, token: str) -> bool:
        """Unregister a device."""
        deleted, _ = DeviceToken.objects.filter(
            user_id=user_id,
            token=token
        ).delete()

        return deleted > 0

    @staticmethod
    def get_user_devices(user_id: UUID) -> list:
        """Get all active devices for a user."""
        return list(DeviceToken.objects.filter(
            user_id=user_id,
            is_active=True
        ).values('id', 'platform', 'device_name', 'created_at'))
