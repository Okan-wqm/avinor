# services/finance-service/src/apps/core/services/transaction_service.py
"""
Transaction Service

Business logic for financial transaction processing.
"""

import uuid
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta
from django.db import transaction
from django.db.models import Sum, Q, Count
from django.utils import timezone

from ..models.account import Account, AccountStatus
from ..models.transaction import (
    Transaction, TransactionType, TransactionSubtype, TransactionStatus
)

logger = logging.getLogger(__name__)


class TransactionServiceError(Exception):
    """Base exception for transaction service errors."""
    pass


class TransactionNotFoundError(TransactionServiceError):
    """Raised when transaction is not found."""
    pass


class TransactionReversalError(TransactionServiceError):
    """Raised when transaction reversal fails."""
    pass


class TransactionService:
    """
    Service for managing financial transactions.

    Handles transaction creation, reversal, and querying.
    """

    @staticmethod
    @transaction.atomic
    def create_charge(
        organization_id: uuid.UUID,
        account_id: uuid.UUID,
        amount: Decimal,
        subtype: str = TransactionSubtype.OTHER_CHARGE,
        description: str = None,
        reference_type: str = None,
        reference_id: uuid.UUID = None,
        line_items: List[Dict] = None,
        tax_amount: Decimal = Decimal('0'),
        tax_rate: Decimal = None,
        discount_amount: Decimal = Decimal('0'),
        discount_code: str = None,
        invoice_id: uuid.UUID = None,
        created_by: uuid.UUID = None,
        metadata: Dict = None
    ) -> Transaction:
        """
        Create a charge transaction.

        Args:
            organization_id: Organization UUID
            account_id: Account UUID
            amount: Charge amount
            subtype: Charge subtype
            description: Charge description
            reference_type: Reference type
            reference_id: Reference UUID
            line_items: Line item breakdown
            tax_amount: Tax amount
            tax_rate: Tax rate percentage
            discount_amount: Discount amount
            discount_code: Discount code used
            invoice_id: Related invoice UUID
            created_by: User who created the transaction
            metadata: Additional metadata

        Returns:
            Created Transaction instance
        """
        # Lock account
        account = Account.objects.select_for_update().get(id=account_id)

        # Check account status
        if account.status in [AccountStatus.SUSPENDED, AccountStatus.CLOSED]:
            raise TransactionServiceError(
                f"Cannot charge to account with status: {account.status}"
            )

        # Record balance before
        balance_before = account.balance

        # Apply charge
        account.balance -= amount
        account.total_charged += amount
        account.last_transaction_at = timezone.now()
        account.save(update_fields=[
            'balance', 'total_charged', 'last_transaction_at', 'updated_at'
        ])

        # Create transaction
        txn = Transaction.objects.create(
            organization_id=organization_id,
            account=account,
            transaction_type=TransactionType.CHARGE,
            transaction_subtype=subtype,
            amount=amount,
            currency=account.currency,
            balance_before=balance_before,
            balance_after=account.balance,
            balance_impact=-amount,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
            line_items=line_items or [],
            tax_amount=tax_amount,
            tax_rate=tax_rate,
            discount_amount=discount_amount,
            discount_code=discount_code,
            invoice_id=invoice_id,
            created_by=created_by,
            metadata=metadata or {},
            status=TransactionStatus.COMPLETED
        )

        logger.info(
            f"Created charge transaction {txn.transaction_number}",
            extra={
                'transaction_id': str(txn.id),
                'account_id': str(account_id),
                'amount': float(amount)
            }
        )

        return txn

    @staticmethod
    @transaction.atomic
    def create_payment(
        organization_id: uuid.UUID,
        account_id: uuid.UUID,
        amount: Decimal,
        payment_method: str,
        subtype: str = TransactionSubtype.CARD_PAYMENT,
        description: str = None,
        reference_type: str = None,
        reference_id: uuid.UUID = None,
        payment_method_id: uuid.UUID = None,
        payment_reference: str = None,
        gateway_name: str = None,
        gateway_transaction_id: str = None,
        gateway_response: Dict = None,
        invoice_id: uuid.UUID = None,
        created_by: uuid.UUID = None,
        metadata: Dict = None
    ) -> Transaction:
        """
        Create a payment transaction.

        Args:
            organization_id: Organization UUID
            account_id: Account UUID
            amount: Payment amount
            payment_method: Payment method type
            subtype: Payment subtype
            description: Payment description
            reference_type: Reference type
            reference_id: Reference UUID
            payment_method_id: Stored payment method UUID
            payment_reference: Payment reference (check number, etc.)
            gateway_name: Payment gateway name
            gateway_transaction_id: Gateway transaction ID
            gateway_response: Full gateway response
            invoice_id: Related invoice UUID
            created_by: User who created the transaction
            metadata: Additional metadata

        Returns:
            Created Transaction instance
        """
        # Lock account
        account = Account.objects.select_for_update().get(id=account_id)

        # Record balance before
        balance_before = account.balance

        # Apply payment
        account.balance += amount
        account.total_paid += amount
        account.last_transaction_at = timezone.now()
        account.last_payment_at = timezone.now()
        account.save(update_fields=[
            'balance', 'total_paid', 'last_transaction_at',
            'last_payment_at', 'updated_at'
        ])

        # Create transaction
        txn = Transaction.objects.create(
            organization_id=organization_id,
            account=account,
            transaction_type=TransactionType.PAYMENT,
            transaction_subtype=subtype,
            amount=amount,
            currency=account.currency,
            balance_before=balance_before,
            balance_after=account.balance,
            balance_impact=amount,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description or f"Payment via {payment_method}",
            payment_method=payment_method,
            payment_method_id=payment_method_id,
            payment_reference=payment_reference,
            gateway_name=gateway_name,
            gateway_transaction_id=gateway_transaction_id,
            gateway_response=gateway_response or {},
            invoice_id=invoice_id,
            created_by=created_by,
            metadata=metadata or {},
            status=TransactionStatus.COMPLETED
        )

        logger.info(
            f"Created payment transaction {txn.transaction_number}",
            extra={
                'transaction_id': str(txn.id),
                'account_id': str(account_id),
                'amount': float(amount),
                'payment_method': payment_method
            }
        )

        return txn

    @staticmethod
    @transaction.atomic
    def create_refund(
        organization_id: uuid.UUID,
        account_id: uuid.UUID,
        amount: Decimal,
        original_transaction_id: uuid.UUID = None,
        description: str = None,
        reference_type: str = None,
        reference_id: uuid.UUID = None,
        gateway_name: str = None,
        gateway_transaction_id: str = None,
        gateway_response: Dict = None,
        created_by: uuid.UUID = None,
        metadata: Dict = None
    ) -> Transaction:
        """
        Create a refund transaction.

        Args:
            organization_id: Organization UUID
            account_id: Account UUID
            amount: Refund amount
            original_transaction_id: Original payment transaction UUID
            description: Refund description
            reference_type: Reference type
            reference_id: Reference UUID
            gateway_name: Payment gateway name
            gateway_transaction_id: Gateway refund ID
            gateway_response: Full gateway response
            created_by: User who created the refund
            metadata: Additional metadata

        Returns:
            Created Transaction instance
        """
        # Lock account
        account = Account.objects.select_for_update().get(id=account_id)

        # Record balance before
        balance_before = account.balance

        # Apply refund (increases balance like payment)
        account.balance += amount
        account.total_refunded += amount
        account.last_transaction_at = timezone.now()
        account.save(update_fields=[
            'balance', 'total_refunded', 'last_transaction_at', 'updated_at'
        ])

        # Create transaction
        txn = Transaction.objects.create(
            organization_id=organization_id,
            account=account,
            transaction_type=TransactionType.REFUND,
            amount=amount,
            currency=account.currency,
            balance_before=balance_before,
            balance_after=account.balance,
            balance_impact=amount,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description or "Refund",
            original_transaction_id=original_transaction_id,
            gateway_name=gateway_name,
            gateway_transaction_id=gateway_transaction_id,
            gateway_response=gateway_response or {},
            created_by=created_by,
            metadata=metadata or {},
            status=TransactionStatus.COMPLETED
        )

        logger.info(
            f"Created refund transaction {txn.transaction_number}",
            extra={
                'transaction_id': str(txn.id),
                'account_id': str(account_id),
                'amount': float(amount),
                'original_transaction_id': str(original_transaction_id) if original_transaction_id else None
            }
        )

        return txn

    @staticmethod
    @transaction.atomic
    def create_credit(
        organization_id: uuid.UUID,
        account_id: uuid.UUID,
        amount: Decimal,
        subtype: str = TransactionSubtype.PROMO_CREDIT,
        description: str = None,
        reference_type: str = None,
        reference_id: uuid.UUID = None,
        created_by: uuid.UUID = None,
        metadata: Dict = None
    ) -> Transaction:
        """
        Create a credit transaction (promotional credit, courtesy credit, etc.).

        Args:
            organization_id: Organization UUID
            account_id: Account UUID
            amount: Credit amount
            subtype: Credit subtype
            description: Credit description
            reference_type: Reference type
            reference_id: Reference UUID
            created_by: User who created the credit
            metadata: Additional metadata

        Returns:
            Created Transaction instance
        """
        # Lock account
        account = Account.objects.select_for_update().get(id=account_id)

        # Record balance before
        balance_before = account.balance

        # Apply credit
        account.balance += amount
        account.last_transaction_at = timezone.now()
        account.save(update_fields=['balance', 'last_transaction_at', 'updated_at'])

        # Create transaction
        txn = Transaction.objects.create(
            organization_id=organization_id,
            account=account,
            transaction_type=TransactionType.CREDIT,
            transaction_subtype=subtype,
            amount=amount,
            currency=account.currency,
            balance_before=balance_before,
            balance_after=account.balance,
            balance_impact=amount,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description or "Account credit",
            created_by=created_by,
            metadata=metadata or {},
            status=TransactionStatus.COMPLETED
        )

        logger.info(
            f"Created credit transaction {txn.transaction_number}",
            extra={
                'transaction_id': str(txn.id),
                'account_id': str(account_id),
                'amount': float(amount)
            }
        )

        return txn

    @staticmethod
    @transaction.atomic
    def create_adjustment(
        organization_id: uuid.UUID,
        account_id: uuid.UUID,
        amount: Decimal,
        is_credit: bool,
        description: str,
        reason: str = None,
        created_by: uuid.UUID = None,
        approved_by: uuid.UUID = None,
        metadata: Dict = None
    ) -> Transaction:
        """
        Create an adjustment transaction.

        Args:
            organization_id: Organization UUID
            account_id: Account UUID
            amount: Adjustment amount (always positive)
            is_credit: True if credit adjustment, False if debit
            description: Adjustment description
            reason: Adjustment reason
            created_by: User who created the adjustment
            approved_by: User who approved the adjustment
            metadata: Additional metadata

        Returns:
            Created Transaction instance
        """
        # Lock account
        account = Account.objects.select_for_update().get(id=account_id)

        # Record balance before
        balance_before = account.balance

        # Apply adjustment
        if is_credit:
            account.balance += amount
            balance_impact = amount
        else:
            account.balance -= amount
            balance_impact = -amount

        account.last_transaction_at = timezone.now()
        account.save(update_fields=['balance', 'last_transaction_at', 'updated_at'])

        # Create transaction
        txn = Transaction.objects.create(
            organization_id=organization_id,
            account=account,
            transaction_type=TransactionType.ADJUSTMENT,
            transaction_subtype=TransactionSubtype.CORRECTION,
            amount=amount,
            currency=account.currency,
            balance_before=balance_before,
            balance_after=account.balance,
            balance_impact=balance_impact,
            description=description,
            created_by=created_by,
            approved_by=approved_by,
            metadata={
                'reason': reason,
                'is_credit': is_credit,
                **(metadata or {})
            },
            status=TransactionStatus.COMPLETED
        )

        logger.info(
            f"Created adjustment transaction {txn.transaction_number}",
            extra={
                'transaction_id': str(txn.id),
                'account_id': str(account_id),
                'amount': float(amount),
                'is_credit': is_credit
            }
        )

        return txn

    @staticmethod
    @transaction.atomic
    def reverse_transaction(
        transaction_id: uuid.UUID,
        reason: str,
        reversed_by: uuid.UUID = None
    ) -> Transaction:
        """
        Reverse a completed transaction.

        Args:
            transaction_id: Transaction to reverse
            reason: Reversal reason
            reversed_by: User who reversed the transaction

        Returns:
            Reversal Transaction instance

        Raises:
            TransactionReversalError: If reversal not possible
        """
        # Lock original transaction
        original = Transaction.objects.select_for_update().get(id=transaction_id)

        if not original.is_reversible:
            raise TransactionReversalError(
                f"Transaction {original.transaction_number} cannot be reversed"
            )

        if original.reversed:
            raise TransactionReversalError(
                f"Transaction {original.transaction_number} already reversed"
            )

        # Lock account
        account = Account.objects.select_for_update().get(id=original.account_id)

        # Record balance before
        balance_before = account.balance

        # Reverse the balance impact
        reversal_impact = -original.balance_impact
        account.balance += reversal_impact
        account.last_transaction_at = timezone.now()
        account.save(update_fields=['balance', 'last_transaction_at', 'updated_at'])

        # Create reversal transaction
        reversal = Transaction.objects.create(
            organization_id=original.organization_id,
            account=account,
            transaction_type=TransactionType.REVERSAL,
            amount=original.amount,
            currency=original.currency,
            balance_before=balance_before,
            balance_after=account.balance,
            balance_impact=reversal_impact,
            original_transaction_id=original.id,
            description=f"Reversal of {original.transaction_number}: {reason}",
            reversal_reason=reason,
            created_by=reversed_by,
            metadata={
                'original_transaction_type': original.transaction_type,
                'original_amount': float(original.amount),
                'reason': reason
            },
            status=TransactionStatus.COMPLETED
        )

        # Mark original as reversed
        original.reversed = True
        original.reversal_id = reversal.id
        original.reversal_reason = reason
        original.save(update_fields=['reversed', 'reversal_id', 'reversal_reason', 'updated_at'])

        logger.info(
            f"Reversed transaction {original.transaction_number}",
            extra={
                'original_transaction_id': str(transaction_id),
                'reversal_transaction_id': str(reversal.id),
                'reason': reason
            }
        )

        return reversal

    @staticmethod
    def get_transaction(
        transaction_id: uuid.UUID,
        organization_id: uuid.UUID = None
    ) -> Transaction:
        """
        Get transaction by ID.

        Args:
            transaction_id: Transaction UUID
            organization_id: Optional organization filter

        Returns:
            Transaction instance

        Raises:
            TransactionNotFoundError: If not found
        """
        queryset = Transaction.objects.filter(id=transaction_id)

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        txn = queryset.select_related('account').first()

        if not txn:
            raise TransactionNotFoundError(f"Transaction {transaction_id} not found")

        return txn

    @staticmethod
    def list_transactions(
        organization_id: uuid.UUID,
        account_id: uuid.UUID = None,
        transaction_type: str = None,
        status: str = None,
        reference_type: str = None,
        reference_id: uuid.UUID = None,
        date_from: date = None,
        date_to: date = None,
        min_amount: Decimal = None,
        max_amount: Decimal = None,
        order_by: str = '-created_at',
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List transactions with filtering.

        Args:
            organization_id: Organization UUID
            account_id: Filter by account
            transaction_type: Filter by type
            status: Filter by status
            reference_type: Filter by reference type
            reference_id: Filter by reference ID
            date_from: Filter from date
            date_to: Filter to date
            min_amount: Minimum amount
            max_amount: Maximum amount
            order_by: Order by field
            limit: Max results
            offset: Result offset

        Returns:
            Dict with transactions and pagination info
        """
        queryset = Transaction.objects.filter(organization_id=organization_id)

        if account_id:
            queryset = queryset.filter(account_id=account_id)

        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        if status:
            queryset = queryset.filter(status=status)

        if reference_type:
            queryset = queryset.filter(reference_type=reference_type)

        if reference_id:
            queryset = queryset.filter(reference_id=reference_id)

        if date_from:
            queryset = queryset.filter(transaction_date__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(transaction_date__date__lte=date_to)

        if min_amount is not None:
            queryset = queryset.filter(amount__gte=min_amount)

        if max_amount is not None:
            queryset = queryset.filter(amount__lte=max_amount)

        total = queryset.count()
        transactions = queryset.order_by(order_by).select_related('account')[offset:offset + limit]

        return {
            'transactions': [
                TransactionService._transaction_to_dict(txn)
                for txn in transactions
            ],
            'total': total,
            'limit': limit,
            'offset': offset,
        }

    @staticmethod
    def get_transaction_summary(
        organization_id: uuid.UUID,
        account_id: uuid.UUID = None,
        date_from: date = None,
        date_to: date = None
    ) -> Dict[str, Any]:
        """
        Get transaction summary/statistics.

        Args:
            organization_id: Organization UUID
            account_id: Optional account filter
            date_from: Start date
            date_to: End date

        Returns:
            Dict with summary statistics
        """
        queryset = Transaction.objects.filter(
            organization_id=organization_id,
            status=TransactionStatus.COMPLETED
        )

        if account_id:
            queryset = queryset.filter(account_id=account_id)

        if date_from:
            queryset = queryset.filter(transaction_date__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(transaction_date__date__lte=date_to)

        # Aggregate by type
        charges = queryset.filter(
            transaction_type=TransactionType.CHARGE
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )

        payments = queryset.filter(
            transaction_type=TransactionType.PAYMENT
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )

        refunds = queryset.filter(
            transaction_type=TransactionType.REFUND
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )

        credits = queryset.filter(
            transaction_type=TransactionType.CREDIT
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )

        return {
            'period': {
                'from': date_from.isoformat() if date_from else None,
                'to': date_to.isoformat() if date_to else None,
            },
            'charges': {
                'total': float(charges['total'] or 0),
                'count': charges['count'] or 0,
            },
            'payments': {
                'total': float(payments['total'] or 0),
                'count': payments['count'] or 0,
            },
            'refunds': {
                'total': float(refunds['total'] or 0),
                'count': refunds['count'] or 0,
            },
            'credits': {
                'total': float(credits['total'] or 0),
                'count': credits['count'] or 0,
            },
            'net_revenue': float(
                (charges['total'] or 0) -
                (refunds['total'] or 0)
            ),
        }

    @staticmethod
    def get_transactions_by_reference(
        reference_type: str,
        reference_id: uuid.UUID,
        organization_id: uuid.UUID = None
    ) -> List[Transaction]:
        """
        Get all transactions for a reference.

        Args:
            reference_type: Reference type
            reference_id: Reference UUID
            organization_id: Optional organization filter

        Returns:
            List of transactions
        """
        queryset = Transaction.objects.filter(
            reference_type=reference_type,
            reference_id=reference_id
        )

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        return list(queryset.order_by('-created_at'))

    @staticmethod
    def _transaction_to_dict(txn: Transaction) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            'id': str(txn.id),
            'transaction_number': txn.transaction_number,
            'account_id': str(txn.account_id),
            'account_number': txn.account.account_number,
            'transaction_type': txn.transaction_type,
            'transaction_subtype': txn.transaction_subtype,
            'amount': float(txn.amount),
            'currency': txn.currency,
            'balance_before': float(txn.balance_before) if txn.balance_before else None,
            'balance_after': float(txn.balance_after) if txn.balance_after else None,
            'balance_impact': float(txn.balance_impact),
            'description': txn.description,
            'reference_type': txn.reference_type,
            'reference_id': str(txn.reference_id) if txn.reference_id else None,
            'status': txn.status,
            'reversed': txn.reversed,
            'tax_amount': float(txn.tax_amount),
            'discount_amount': float(txn.discount_amount),
            'net_amount': float(txn.net_amount),
            'transaction_date': txn.transaction_date.isoformat(),
            'created_at': txn.created_at.isoformat(),
        }
