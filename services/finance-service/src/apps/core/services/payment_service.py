# services/finance-service/src/apps/core/services/payment_service.py
"""
Payment Service

Business logic for payment processing and gateway integration.
"""

import uuid
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from ..models.account import Account
from ..models.payment import (
    PaymentMethod, PaymentGatewayLog,
    PaymentMethodType, PaymentMethodStatus
)
from ..models.invoice import Invoice, InvoiceStatus

logger = logging.getLogger(__name__)


class PaymentServiceError(Exception):
    """Base exception for payment service errors."""
    pass


class PaymentMethodNotFoundError(PaymentServiceError):
    """Raised when payment method is not found."""
    pass


class PaymentFailedError(PaymentServiceError):
    """Raised when payment processing fails."""
    pass


class PaymentGatewayError(PaymentServiceError):
    """Raised when gateway communication fails."""
    pass


class PaymentService:
    """
    Service for payment processing.

    Handles payment method management, gateway integration,
    and payment processing.
    """

    # ==================== PAYMENT METHOD MANAGEMENT ====================

    @staticmethod
    @transaction.atomic
    def create_payment_method(
        organization_id: uuid.UUID,
        account_id: uuid.UUID,
        method_type: str,
        gateway_name: str = 'stripe',
        gateway_token: str = None,
        card_brand: str = None,
        card_last_four: str = None,
        card_exp_month: int = None,
        card_exp_year: int = None,
        card_holder_name: str = None,
        bank_name: str = None,
        bank_account_type: str = None,
        bank_last_four: str = None,
        billing_address: Dict = None,
        nickname: str = None,
        is_default: bool = False,
        metadata: Dict = None
    ) -> PaymentMethod:
        """
        Create a new payment method.

        Args:
            organization_id: Organization UUID
            account_id: Account UUID
            method_type: Payment method type
            gateway_name: Payment gateway name
            gateway_token: Gateway payment method token
            card_brand: Card brand (visa, mastercard, etc.)
            card_last_four: Last 4 digits of card
            card_exp_month: Card expiration month
            card_exp_year: Card expiration year
            card_holder_name: Cardholder name
            bank_name: Bank name (for ACH)
            bank_account_type: Account type (checking/savings)
            bank_last_four: Last 4 of account number
            billing_address: Billing address dict
            nickname: User-friendly name
            is_default: Set as default payment method
            metadata: Additional metadata

        Returns:
            Created PaymentMethod instance
        """
        account = Account.objects.get(id=account_id)

        # Create gateway customer if needed
        gateway_customer_id = account.metadata.get(f'{gateway_name}_customer_id')

        if not gateway_customer_id:
            gateway_customer_id = PaymentService._create_gateway_customer(
                gateway_name=gateway_name,
                account=account
            )
            # Store customer ID in account metadata
            account.metadata[f'{gateway_name}_customer_id'] = gateway_customer_id
            account.save(update_fields=['metadata', 'updated_at'])

        # Attach payment method to gateway customer
        gateway_payment_method_id = None
        if gateway_token:
            gateway_payment_method_id = PaymentService._attach_payment_method_to_customer(
                gateway_name=gateway_name,
                customer_id=gateway_customer_id,
                token=gateway_token
            )

        # Extract billing address
        billing = billing_address or {}

        payment_method = PaymentMethod.objects.create(
            organization_id=organization_id,
            account=account,
            method_type=method_type,
            gateway_name=gateway_name,
            gateway_customer_id=gateway_customer_id,
            gateway_payment_method_id=gateway_payment_method_id,
            card_brand=card_brand,
            card_last_four=card_last_four,
            card_exp_month=card_exp_month,
            card_exp_year=card_exp_year,
            card_holder_name=card_holder_name,
            bank_name=bank_name,
            bank_account_type=bank_account_type,
            bank_last_four=bank_last_four,
            billing_name=billing.get('name'),
            billing_email=billing.get('email'),
            billing_phone=billing.get('phone'),
            billing_address_line1=billing.get('line1'),
            billing_address_line2=billing.get('line2'),
            billing_city=billing.get('city'),
            billing_state=billing.get('state'),
            billing_postal_code=billing.get('postal_code'),
            billing_country=billing.get('country', 'US'),
            nickname=nickname,
            is_verified=True,  # Assume verified if gateway accepted
            verified_at=timezone.now(),
            metadata=metadata or {},
            status=PaymentMethodStatus.ACTIVE
        )

        # Set as default if requested or first payment method
        if is_default or not PaymentMethod.objects.filter(
            account=account, is_default=True
        ).exists():
            payment_method.set_as_default()

        logger.info(
            f"Created payment method for account {account.account_number}",
            extra={
                'payment_method_id': str(payment_method.id),
                'account_id': str(account_id),
                'method_type': method_type
            }
        )

        return payment_method

    @staticmethod
    def get_payment_method(
        payment_method_id: uuid.UUID,
        organization_id: uuid.UUID = None
    ) -> PaymentMethod:
        """
        Get payment method by ID.

        Args:
            payment_method_id: PaymentMethod UUID
            organization_id: Optional organization filter

        Returns:
            PaymentMethod instance

        Raises:
            PaymentMethodNotFoundError: If not found
        """
        queryset = PaymentMethod.objects.filter(id=payment_method_id)

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        payment_method = queryset.select_related('account').first()

        if not payment_method:
            raise PaymentMethodNotFoundError(
                f"Payment method {payment_method_id} not found"
            )

        return payment_method

    @staticmethod
    def get_account_payment_methods(
        account_id: uuid.UUID,
        organization_id: uuid.UUID = None,
        status: str = None,
        method_type: str = None
    ) -> List[PaymentMethod]:
        """
        Get all payment methods for an account.

        Args:
            account_id: Account UUID
            organization_id: Optional organization filter
            status: Filter by status
            method_type: Filter by type

        Returns:
            List of PaymentMethod instances
        """
        queryset = PaymentMethod.objects.filter(account_id=account_id)

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        if status:
            queryset = queryset.filter(status=status)

        if method_type:
            queryset = queryset.filter(method_type=method_type)

        return list(queryset.order_by('-is_default', '-created_at'))

    @staticmethod
    def get_default_payment_method(
        account_id: uuid.UUID
    ) -> Optional[PaymentMethod]:
        """
        Get default payment method for an account.

        Args:
            account_id: Account UUID

        Returns:
            Default PaymentMethod or None
        """
        return PaymentMethod.objects.filter(
            account_id=account_id,
            is_default=True,
            status=PaymentMethodStatus.ACTIVE
        ).first()

    @staticmethod
    def set_default_payment_method(
        payment_method_id: uuid.UUID,
        organization_id: uuid.UUID = None
    ) -> PaymentMethod:
        """
        Set payment method as default.

        Args:
            payment_method_id: PaymentMethod UUID
            organization_id: Optional organization filter

        Returns:
            Updated PaymentMethod instance
        """
        payment_method = PaymentService.get_payment_method(
            payment_method_id, organization_id
        )

        if payment_method.status != PaymentMethodStatus.ACTIVE:
            raise PaymentServiceError(
                f"Cannot set inactive payment method as default"
            )

        payment_method.set_as_default()

        logger.info(
            f"Set payment method {payment_method_id} as default",
            extra={'account_id': str(payment_method.account_id)}
        )

        return payment_method

    @staticmethod
    @transaction.atomic
    def delete_payment_method(
        payment_method_id: uuid.UUID,
        organization_id: uuid.UUID = None
    ) -> bool:
        """
        Delete (deactivate) a payment method.

        Args:
            payment_method_id: PaymentMethod UUID
            organization_id: Optional organization filter

        Returns:
            True if deleted
        """
        payment_method = PaymentService.get_payment_method(
            payment_method_id, organization_id
        )

        # Remove from gateway
        if payment_method.gateway_payment_method_id:
            PaymentService._detach_payment_method_from_gateway(
                gateway_name=payment_method.gateway_name,
                payment_method_id=payment_method.gateway_payment_method_id
            )

        # Mark as invalid
        payment_method.mark_invalid("Deleted by user")
        payment_method.is_default = False
        payment_method.save()

        # Set new default if this was default
        if payment_method.is_default:
            next_default = PaymentMethod.objects.filter(
                account=payment_method.account,
                status=PaymentMethodStatus.ACTIVE
            ).exclude(id=payment_method_id).first()

            if next_default:
                next_default.set_as_default()

        logger.info(
            f"Deleted payment method {payment_method_id}",
            extra={'account_id': str(payment_method.account_id)}
        )

        return True

    # ==================== PAYMENT PROCESSING ====================

    @staticmethod
    @transaction.atomic
    def process_payment(
        organization_id: uuid.UUID,
        account_id: uuid.UUID,
        amount: Decimal,
        payment_method_id: uuid.UUID = None,
        description: str = None,
        invoice_id: uuid.UUID = None,
        metadata: Dict = None,
        idempotency_key: str = None
    ) -> Dict[str, Any]:
        """
        Process a payment.

        Args:
            organization_id: Organization UUID
            account_id: Account UUID
            amount: Payment amount
            payment_method_id: Payment method to use (uses default if not provided)
            description: Payment description
            invoice_id: Related invoice UUID
            metadata: Additional metadata
            idempotency_key: Idempotency key for deduplication

        Returns:
            Dict with payment result

        Raises:
            PaymentFailedError: If payment fails
        """
        # Get payment method
        if payment_method_id:
            payment_method = PaymentService.get_payment_method(
                payment_method_id, organization_id
            )
        else:
            payment_method = PaymentService.get_default_payment_method(account_id)

        if not payment_method:
            raise PaymentServiceError("No payment method available")

        if payment_method.status != PaymentMethodStatus.ACTIVE:
            raise PaymentServiceError(
                f"Payment method is not active: {payment_method.status}"
            )

        # Check for expired card
        if payment_method.is_expired:
            payment_method.mark_expired()
            payment_method.save()
            raise PaymentServiceError("Payment method has expired")

        # Create gateway log entry
        log = PaymentGatewayLog.objects.create(
            organization_id=organization_id,
            gateway_name=payment_method.gateway_name,
            operation='charge',
            amount=amount,
            currency=payment_method.account.currency,
            account_id=account_id,
            payment_method_id=payment_method_id,
            invoice_id=invoice_id,
            idempotency_key=idempotency_key,
            request_at=timezone.now()
        )

        try:
            # Process via gateway
            gateway_result = PaymentService._charge_payment_method(
                gateway_name=payment_method.gateway_name,
                customer_id=payment_method.gateway_customer_id,
                payment_method_id=payment_method.gateway_payment_method_id,
                amount=amount,
                currency=payment_method.account.currency,
                description=description,
                metadata=metadata,
                idempotency_key=idempotency_key
            )

            # Update log
            log.gateway_transaction_id = gateway_result.get('transaction_id')
            log.response_data = gateway_result
            log.success = True
            log.response_at = timezone.now()
            log.save()

            # Record charge on payment method
            payment_method.record_charge(amount, success=True)
            payment_method.save()

            # Create transaction
            from .transaction_service import TransactionService

            txn = TransactionService.create_payment(
                organization_id=organization_id,
                account_id=account_id,
                amount=amount,
                payment_method=payment_method.method_type,
                description=description or f"Payment via {payment_method.display_name}",
                payment_method_id=payment_method.id,
                gateway_name=payment_method.gateway_name,
                gateway_transaction_id=gateway_result.get('transaction_id'),
                gateway_response=gateway_result,
                invoice_id=invoice_id,
                metadata=metadata
            )

            # Update invoice if provided
            if invoice_id:
                from .invoice_service import InvoiceService
                InvoiceService.record_payment(
                    invoice_id=invoice_id,
                    amount=amount,
                    payment_method=payment_method.method_type,
                    payment_reference=txn.transaction_number
                )

            logger.info(
                f"Processed payment of {amount} for account {account_id}",
                extra={
                    'transaction_id': str(txn.id),
                    'gateway_transaction_id': gateway_result.get('transaction_id')
                }
            )

            return {
                'success': True,
                'transaction_id': str(txn.id),
                'transaction_number': txn.transaction_number,
                'gateway_transaction_id': gateway_result.get('transaction_id'),
                'amount': float(amount),
                'payment_method_id': str(payment_method.id),
            }

        except Exception as e:
            # Log failure
            log.success = False
            log.error_message = str(e)
            log.response_at = timezone.now()
            log.save()

            # Record failure on payment method
            payment_method.record_charge(amount, success=False, failure_reason=str(e))
            payment_method.save()

            logger.error(
                f"Payment failed for account {account_id}",
                extra={
                    'account_id': str(account_id),
                    'amount': float(amount),
                    'error': str(e)
                }
            )

            raise PaymentFailedError(f"Payment failed: {str(e)}")

    @staticmethod
    @transaction.atomic
    def process_refund(
        organization_id: uuid.UUID,
        original_transaction_id: uuid.UUID,
        amount: Decimal = None,
        reason: str = None
    ) -> Dict[str, Any]:
        """
        Process a refund.

        Args:
            organization_id: Organization UUID
            original_transaction_id: Original payment transaction
            amount: Refund amount (full refund if not provided)
            reason: Refund reason

        Returns:
            Dict with refund result
        """
        from .transaction_service import TransactionService

        original_txn = TransactionService.get_transaction(
            original_transaction_id, organization_id
        )

        if not original_txn.gateway_transaction_id:
            raise PaymentServiceError(
                "Cannot refund transaction without gateway reference"
            )

        # Use full amount if not specified
        refund_amount = amount or original_txn.amount

        if refund_amount > original_txn.amount:
            raise PaymentServiceError(
                f"Refund amount ({refund_amount}) exceeds original ({original_txn.amount})"
            )

        # Create gateway log
        log = PaymentGatewayLog.objects.create(
            organization_id=organization_id,
            gateway_name=original_txn.gateway_name,
            operation='refund',
            amount=refund_amount,
            currency=original_txn.currency,
            account_id=original_txn.account_id,
            transaction_id=original_transaction_id,
            request_at=timezone.now()
        )

        try:
            # Process refund via gateway
            gateway_result = PaymentService._refund_charge(
                gateway_name=original_txn.gateway_name,
                charge_id=original_txn.gateway_transaction_id,
                amount=refund_amount,
                reason=reason
            )

            # Update log
            log.gateway_transaction_id = gateway_result.get('refund_id')
            log.response_data = gateway_result
            log.success = True
            log.response_at = timezone.now()
            log.save()

            # Create refund transaction
            refund_txn = TransactionService.create_refund(
                organization_id=organization_id,
                account_id=original_txn.account_id,
                amount=refund_amount,
                original_transaction_id=original_transaction_id,
                description=reason or f"Refund for {original_txn.transaction_number}",
                gateway_name=original_txn.gateway_name,
                gateway_transaction_id=gateway_result.get('refund_id'),
                gateway_response=gateway_result
            )

            logger.info(
                f"Processed refund of {refund_amount} for transaction {original_transaction_id}",
                extra={
                    'refund_transaction_id': str(refund_txn.id),
                    'original_transaction_id': str(original_transaction_id)
                }
            )

            return {
                'success': True,
                'transaction_id': str(refund_txn.id),
                'transaction_number': refund_txn.transaction_number,
                'gateway_refund_id': gateway_result.get('refund_id'),
                'amount': float(refund_amount),
            }

        except Exception as e:
            log.success = False
            log.error_message = str(e)
            log.response_at = timezone.now()
            log.save()

            logger.error(
                f"Refund failed for transaction {original_transaction_id}",
                extra={'error': str(e)}
            )

            raise PaymentFailedError(f"Refund failed: {str(e)}")

    @staticmethod
    def verify_payment_method(
        payment_method_id: uuid.UUID,
        verification_amounts: List[int] = None
    ) -> Dict[str, Any]:
        """
        Verify a payment method (for bank accounts).

        Args:
            payment_method_id: PaymentMethod UUID
            verification_amounts: Micro-deposit amounts in cents

        Returns:
            Dict with verification result
        """
        payment_method = PaymentService.get_payment_method(payment_method_id)

        if payment_method.is_verified:
            return {
                'success': True,
                'already_verified': True,
                'payment_method_id': str(payment_method_id)
            }

        if payment_method.method_type not in [
            PaymentMethodType.BANK_ACCOUNT,
            PaymentMethodType.ACH
        ]:
            return {
                'success': True,
                'message': 'Verification not required for this payment method type',
                'payment_method_id': str(payment_method_id)
            }

        # Verify via gateway
        try:
            result = PaymentService._verify_bank_account(
                gateway_name=payment_method.gateway_name,
                payment_method_id=payment_method.gateway_payment_method_id,
                amounts=verification_amounts
            )

            if result.get('verified'):
                payment_method.is_verified = True
                payment_method.verified_at = timezone.now()
                payment_method.verification_method = 'micro_deposit'
                payment_method.save()

            return {
                'success': result.get('verified', False),
                'payment_method_id': str(payment_method_id),
                'verification_attempts': payment_method.verification_attempts + 1,
            }

        except Exception as e:
            payment_method.verification_attempts += 1
            payment_method.last_verification_attempt = timezone.now()
            payment_method.save()

            raise PaymentServiceError(f"Verification failed: {str(e)}")

    @staticmethod
    def check_expiring_cards(
        organization_id: uuid.UUID,
        days_ahead: int = 30
    ) -> List[PaymentMethod]:
        """
        Find cards expiring soon.

        Args:
            organization_id: Organization UUID
            days_ahead: Days to look ahead

        Returns:
            List of expiring payment methods
        """
        from datetime import date
        from dateutil.relativedelta import relativedelta

        today = date.today()
        check_date = today + relativedelta(months=1, days=days_ahead)

        return list(PaymentMethod.objects.filter(
            organization_id=organization_id,
            method_type__in=[PaymentMethodType.CREDIT_CARD, PaymentMethodType.DEBIT_CARD],
            status=PaymentMethodStatus.ACTIVE,
            card_exp_year__lte=check_date.year,
            card_exp_month__lte=check_date.month if check_date.year == today.year else 12
        ).select_related('account'))

    @staticmethod
    def update_expired_cards() -> int:
        """
        Mark expired cards as expired.

        Returns:
            Number of cards marked expired
        """
        from datetime import date

        today = date.today()

        expired = PaymentMethod.objects.filter(
            method_type__in=[PaymentMethodType.CREDIT_CARD, PaymentMethodType.DEBIT_CARD],
            status=PaymentMethodStatus.ACTIVE
        )

        count = 0
        for pm in expired:
            if pm.is_expired:
                pm.mark_expired()
                pm.save()
                count += 1

        if count > 0:
            logger.info(f"Marked {count} payment methods as expired")

        return count

    # ==================== GATEWAY INTEGRATION ====================

    @staticmethod
    def _create_gateway_customer(
        gateway_name: str,
        account: Account
    ) -> str:
        """Create customer in payment gateway."""
        if gateway_name == 'stripe':
            return PaymentService._stripe_create_customer(account)
        else:
            raise PaymentGatewayError(f"Unsupported gateway: {gateway_name}")

    @staticmethod
    def _attach_payment_method_to_customer(
        gateway_name: str,
        customer_id: str,
        token: str
    ) -> str:
        """Attach payment method to gateway customer."""
        if gateway_name == 'stripe':
            return PaymentService._stripe_attach_payment_method(customer_id, token)
        else:
            raise PaymentGatewayError(f"Unsupported gateway: {gateway_name}")

    @staticmethod
    def _detach_payment_method_from_gateway(
        gateway_name: str,
        payment_method_id: str
    ) -> bool:
        """Detach payment method from gateway."""
        if gateway_name == 'stripe':
            return PaymentService._stripe_detach_payment_method(payment_method_id)
        else:
            raise PaymentGatewayError(f"Unsupported gateway: {gateway_name}")

    @staticmethod
    def _charge_payment_method(
        gateway_name: str,
        customer_id: str,
        payment_method_id: str,
        amount: Decimal,
        currency: str,
        description: str = None,
        metadata: Dict = None,
        idempotency_key: str = None
    ) -> Dict[str, Any]:
        """Charge payment method via gateway."""
        if gateway_name == 'stripe':
            return PaymentService._stripe_charge(
                customer_id=customer_id,
                payment_method_id=payment_method_id,
                amount=amount,
                currency=currency,
                description=description,
                metadata=metadata,
                idempotency_key=idempotency_key
            )
        else:
            raise PaymentGatewayError(f"Unsupported gateway: {gateway_name}")

    @staticmethod
    def _refund_charge(
        gateway_name: str,
        charge_id: str,
        amount: Decimal,
        reason: str = None
    ) -> Dict[str, Any]:
        """Refund a charge via gateway."""
        if gateway_name == 'stripe':
            return PaymentService._stripe_refund(charge_id, amount, reason)
        else:
            raise PaymentGatewayError(f"Unsupported gateway: {gateway_name}")

    @staticmethod
    def _verify_bank_account(
        gateway_name: str,
        payment_method_id: str,
        amounts: List[int]
    ) -> Dict[str, Any]:
        """Verify bank account via gateway."""
        if gateway_name == 'stripe':
            return PaymentService._stripe_verify_bank_account(payment_method_id, amounts)
        else:
            raise PaymentGatewayError(f"Unsupported gateway: {gateway_name}")

    # ==================== STRIPE INTEGRATION ====================

    @staticmethod
    def _stripe_create_customer(account: Account) -> str:
        """Create Stripe customer."""
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY

            customer = stripe.Customer.create(
                email=account.billing_email,
                name=account.billing_name,
                metadata={
                    'account_id': str(account.id),
                    'organization_id': str(account.organization_id),
                }
            )

            return customer.id

        except Exception as e:
            logger.error(f"Stripe customer creation failed: {e}")
            raise PaymentGatewayError(f"Failed to create Stripe customer: {e}")

    @staticmethod
    def _stripe_attach_payment_method(customer_id: str, token: str) -> str:
        """Attach payment method to Stripe customer."""
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY

            payment_method = stripe.PaymentMethod.attach(
                token,
                customer=customer_id
            )

            return payment_method.id

        except Exception as e:
            logger.error(f"Stripe payment method attachment failed: {e}")
            raise PaymentGatewayError(f"Failed to attach payment method: {e}")

    @staticmethod
    def _stripe_detach_payment_method(payment_method_id: str) -> bool:
        """Detach payment method from Stripe."""
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY

            stripe.PaymentMethod.detach(payment_method_id)
            return True

        except Exception as e:
            logger.error(f"Stripe payment method detachment failed: {e}")
            raise PaymentGatewayError(f"Failed to detach payment method: {e}")

    @staticmethod
    def _stripe_charge(
        customer_id: str,
        payment_method_id: str,
        amount: Decimal,
        currency: str,
        description: str = None,
        metadata: Dict = None,
        idempotency_key: str = None
    ) -> Dict[str, Any]:
        """Create Stripe payment intent."""
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY

            # Convert to cents
            amount_cents = int(amount * 100)

            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                customer=customer_id,
                payment_method=payment_method_id,
                description=description,
                metadata=metadata or {},
                confirm=True,
                off_session=True,
                idempotency_key=idempotency_key
            )

            return {
                'transaction_id': intent.id,
                'status': intent.status,
                'amount': amount_cents,
                'currency': currency,
            }

        except Exception as e:
            logger.error(f"Stripe charge failed: {e}")
            raise PaymentGatewayError(f"Stripe charge failed: {e}")

    @staticmethod
    def _stripe_refund(
        charge_id: str,
        amount: Decimal,
        reason: str = None
    ) -> Dict[str, Any]:
        """Create Stripe refund."""
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY

            # Convert to cents
            amount_cents = int(amount * 100)

            refund = stripe.Refund.create(
                payment_intent=charge_id,
                amount=amount_cents,
                reason='requested_by_customer' if not reason else None,
                metadata={'reason': reason} if reason else {}
            )

            return {
                'refund_id': refund.id,
                'status': refund.status,
                'amount': amount_cents,
            }

        except Exception as e:
            logger.error(f"Stripe refund failed: {e}")
            raise PaymentGatewayError(f"Stripe refund failed: {e}")

    @staticmethod
    def _stripe_verify_bank_account(
        payment_method_id: str,
        amounts: List[int]
    ) -> Dict[str, Any]:
        """Verify Stripe bank account."""
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY

            # Note: Stripe's verification flow depends on the bank account type
            # This is a simplified example
            result = stripe.PaymentMethod.verify_microdeposits(
                payment_method_id,
                amounts=amounts
            )

            return {
                'verified': True,
                'payment_method_id': payment_method_id,
            }

        except Exception as e:
            logger.error(f"Stripe bank verification failed: {e}")
            raise PaymentGatewayError(f"Bank verification failed: {e}")
