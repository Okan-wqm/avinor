# services/finance-service/src/apps/core/events/handlers.py
"""
Finance Service Event Handlers

Handles incoming events from other services.
"""

import json
import logging
from typing import Dict, Any
from decimal import Decimal
from django.db import transaction

logger = logging.getLogger(__name__)


def handle_flight_completed(data: Dict[str, Any]) -> bool:
    """
    Handle flight completed event from Flight Service.

    Creates charge transaction for the flight.

    Args:
        data: Event data containing flight details

    Returns:
        True if handled successfully
    """
    from ..services.account_service import AccountService
    from ..services.transaction_service import TransactionService
    from ..services.pricing_service import PricingService

    try:
        organization_id = data.get('organization_id')
        user_id = data.get('pilot_id')
        flight_id = data.get('flight_id')
        aircraft_id = data.get('aircraft_id')
        instructor_id = data.get('instructor_id')
        hobbs_time = Decimal(str(data.get('hobbs_time', 0)))
        instructor_time = Decimal(str(data.get('instructor_time', 0)))
        flight_datetime = data.get('flight_datetime')

        # Get or create account for user
        account, _ = AccountService.get_or_create_account(
            organization_id=organization_id,
            owner_id=user_id,
            owner_type='user'
        )

        # Calculate flight price
        price_result = PricingService.calculate_flight_price(
            organization_id=organization_id,
            aircraft_id=aircraft_id,
            hobbs_time=hobbs_time,
            instructor_id=instructor_id,
            instructor_time=instructor_time,
            is_member=True  # Determine from user data
        )

        # Create charge transaction
        with transaction.atomic():
            txn = TransactionService.create_charge(
                organization_id=organization_id,
                account_id=account.id,
                amount=Decimal(str(price_result['total'])),
                subtype='flight_charge',
                description=f"Flight: {hobbs_time} hours",
                reference_type='flight',
                reference_id=flight_id,
                line_items=price_result['line_items']
            )

        logger.info(
            f"Created charge for flight {flight_id}",
            extra={
                'flight_id': flight_id,
                'transaction_id': str(txn.id),
                'amount': price_result['total']
            }
        )

        return True

    except Exception as e:
        logger.error(
            f"Failed to handle flight_completed event: {e}",
            extra={'data': data}
        )
        return False


def handle_booking_created(data: Dict[str, Any]) -> bool:
    """
    Handle booking created event from Booking Service.

    Creates pending charge for deposit if required.

    Args:
        data: Event data containing booking details

    Returns:
        True if handled successfully
    """
    from ..services.account_service import AccountService

    try:
        organization_id = data.get('organization_id')
        user_id = data.get('user_id')
        booking_id = data.get('booking_id')
        deposit_required = data.get('deposit_required', False)
        deposit_amount = Decimal(str(data.get('deposit_amount', 0)))

        if not deposit_required or deposit_amount <= 0:
            return True

        # Get or create account
        account, _ = AccountService.get_or_create_account(
            organization_id=organization_id,
            owner_id=user_id,
            owner_type='user'
        )

        # Add pending charge
        account.add_pending_charge(deposit_amount)
        account.save()

        logger.info(
            f"Added pending charge for booking {booking_id}",
            extra={
                'booking_id': booking_id,
                'amount': float(deposit_amount)
            }
        )

        return True

    except Exception as e:
        logger.error(
            f"Failed to handle booking_created event: {e}",
            extra={'data': data}
        )
        return False


def handle_booking_cancelled(data: Dict[str, Any]) -> bool:
    """
    Handle booking cancelled event from Booking Service.

    Removes pending charge and may apply cancellation fee.

    Args:
        data: Event data containing booking details

    Returns:
        True if handled successfully
    """
    from ..services.account_service import AccountService
    from ..services.transaction_service import TransactionService

    try:
        organization_id = data.get('organization_id')
        user_id = data.get('user_id')
        booking_id = data.get('booking_id')
        cancellation_fee = Decimal(str(data.get('cancellation_fee', 0)))
        deposit_amount = Decimal(str(data.get('deposit_amount', 0)))

        # Get account
        account = AccountService.get_account_by_owner(
            organization_id=organization_id,
            owner_id=user_id,
            owner_type='user'
        )

        if not account:
            return True

        with transaction.atomic():
            # Remove pending charge
            if deposit_amount > 0:
                account.pending_charges = max(
                    Decimal('0'),
                    account.pending_charges - deposit_amount
                )
                account.save()

            # Apply cancellation fee if any
            if cancellation_fee > 0:
                TransactionService.create_charge(
                    organization_id=organization_id,
                    account_id=account.id,
                    amount=cancellation_fee,
                    subtype='cancellation_fee',
                    description=f"Cancellation fee for booking {booking_id}",
                    reference_type='booking',
                    reference_id=booking_id
                )

        logger.info(
            f"Processed booking cancellation {booking_id}",
            extra={
                'booking_id': booking_id,
                'cancellation_fee': float(cancellation_fee)
            }
        )

        return True

    except Exception as e:
        logger.error(
            f"Failed to handle booking_cancelled event: {e}",
            extra={'data': data}
        )
        return False


def handle_user_created(data: Dict[str, Any]) -> bool:
    """
    Handle user created event from User Service.

    Creates a financial account for the new user.

    Args:
        data: Event data containing user details

    Returns:
        True if handled successfully
    """
    from ..services.account_service import AccountService

    try:
        organization_id = data.get('organization_id')
        user_id = data.get('user_id')
        user_type = data.get('user_type', 'student')
        email = data.get('email')
        name = data.get('name')

        # Map user type to account type
        account_type_map = {
            'student': 'student',
            'pilot': 'pilot',
            'instructor': 'instructor',
            'staff': 'corporate',
            'admin': 'corporate',
        }

        account_type = account_type_map.get(user_type, 'student')

        # Create account
        account = AccountService.create_account(
            organization_id=organization_id,
            owner_id=user_id,
            owner_type='user',
            account_type=account_type,
            billing_name=name,
            billing_email=email
        )

        logger.info(
            f"Created account for user {user_id}",
            extra={
                'user_id': user_id,
                'account_id': str(account.id)
            }
        )

        return True

    except Exception as e:
        logger.error(
            f"Failed to handle user_created event: {e}",
            extra={'data': data}
        )
        return False


def handle_membership_changed(data: Dict[str, Any]) -> bool:
    """
    Handle membership changed event from Organization Service.

    Updates account type based on membership level.

    Args:
        data: Event data containing membership details

    Returns:
        True if handled successfully
    """
    from ..services.account_service import AccountService
    from ..models.account import AccountType

    try:
        organization_id = data.get('organization_id')
        user_id = data.get('user_id')
        membership_level = data.get('membership_level')
        is_member = data.get('is_member', False)

        # Get account
        account = AccountService.get_account_by_owner(
            organization_id=organization_id,
            owner_id=user_id,
            owner_type='user'
        )

        if not account:
            return True

        # Update account type based on membership
        if is_member:
            if membership_level in ['premium', 'gold', 'platinum']:
                account.account_type = AccountType.CLUB_MEMBER
            else:
                account.account_type = AccountType.MEMBER
        else:
            # Revert to basic type
            account.account_type = AccountType.STUDENT

        # Store membership level in metadata
        account.metadata['membership_level'] = membership_level
        account.metadata['is_member'] = is_member
        account.save()

        logger.info(
            f"Updated account for membership change",
            extra={
                'user_id': user_id,
                'membership_level': membership_level,
                'account_type': account.account_type
            }
        )

        return True

    except Exception as e:
        logger.error(
            f"Failed to handle membership_changed event: {e}",
            extra={'data': data}
        )
        return False


def handle_event(event_type: str, data: Dict[str, Any]) -> bool:
    """
    Route event to appropriate handler.

    Args:
        event_type: Type of event
        data: Event payload

    Returns:
        True if handled successfully
    """
    handlers = {
        'flight.completed': handle_flight_completed,
        'booking.created': handle_booking_created,
        'booking.cancelled': handle_booking_cancelled,
        'user.created': handle_user_created,
        'membership.changed': handle_membership_changed,
    }

    handler = handlers.get(event_type)

    if not handler:
        logger.warning(f"No handler for event type: {event_type}")
        return False

    return handler(data)
