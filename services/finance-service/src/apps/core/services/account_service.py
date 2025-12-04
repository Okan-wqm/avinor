# services/finance-service/src/apps/core/services/account_service.py
"""
Account Service

Business logic for financial account management.
"""

import uuid
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from django.db import transaction
from django.db.models import Sum, Q, F
from django.utils import timezone
from django.core.exceptions import ValidationError

from ..models.account import Account, AccountType, AccountStatus

logger = logging.getLogger(__name__)


class AccountServiceError(Exception):
    """Base exception for account service errors."""
    pass


class InsufficientBalanceError(AccountServiceError):
    """Raised when account has insufficient balance."""
    pass


class AccountSuspendedError(AccountServiceError):
    """Raised when account is suspended."""
    pass


class AccountNotFoundError(AccountServiceError):
    """Raised when account is not found."""
    pass


class AccountService:
    """
    Service for managing financial accounts.

    Handles account creation, balance management,
    credit limits, and account status operations.
    """

    @staticmethod
    def create_account(
        organization_id: uuid.UUID,
        owner_id: uuid.UUID,
        owner_type: str,
        account_type: str = AccountType.STUDENT,
        currency: str = 'USD',
        credit_limit: Decimal = Decimal('0'),
        **kwargs
    ) -> Account:
        """
        Create a new financial account.

        Args:
            organization_id: Organization UUID
            owner_id: Owner (user/organization) UUID
            owner_type: Owner type (user, organization)
            account_type: Account type
            currency: Currency code
            credit_limit: Credit limit amount
            **kwargs: Additional account fields

        Returns:
            Created Account instance
        """
        with transaction.atomic():
            # Check for existing account
            existing = Account.objects.filter(
                organization_id=organization_id,
                owner_id=owner_id,
                owner_type=owner_type
            ).first()

            if existing:
                logger.warning(
                    f"Account already exists for owner {owner_id}",
                    extra={'account_id': str(existing.id)}
                )
                return existing

            # Generate account number
            account_number = AccountService._generate_account_number(
                organization_id
            )

            account = Account.objects.create(
                organization_id=organization_id,
                account_number=account_number,
                owner_id=owner_id,
                owner_type=owner_type,
                account_type=account_type,
                currency=currency,
                credit_limit=credit_limit,
                **kwargs
            )

            logger.info(
                f"Created account {account_number} for owner {owner_id}",
                extra={
                    'account_id': str(account.id),
                    'organization_id': str(organization_id)
                }
            )

            return account

    @staticmethod
    def get_account(
        account_id: uuid.UUID,
        organization_id: uuid.UUID = None
    ) -> Account:
        """
        Get account by ID.

        Args:
            account_id: Account UUID
            organization_id: Optional organization filter

        Returns:
            Account instance

        Raises:
            AccountNotFoundError: If account not found
        """
        queryset = Account.objects.filter(id=account_id)

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        account = queryset.first()

        if not account:
            raise AccountNotFoundError(f"Account {account_id} not found")

        return account

    @staticmethod
    def get_account_by_owner(
        organization_id: uuid.UUID,
        owner_id: uuid.UUID,
        owner_type: str = 'user'
    ) -> Optional[Account]:
        """
        Get account by owner.

        Args:
            organization_id: Organization UUID
            owner_id: Owner UUID
            owner_type: Owner type

        Returns:
            Account instance or None
        """
        return Account.objects.filter(
            organization_id=organization_id,
            owner_id=owner_id,
            owner_type=owner_type
        ).first()

    @staticmethod
    def get_or_create_account(
        organization_id: uuid.UUID,
        owner_id: uuid.UUID,
        owner_type: str = 'user',
        **defaults
    ) -> Tuple[Account, bool]:
        """
        Get existing account or create new one.

        Args:
            organization_id: Organization UUID
            owner_id: Owner UUID
            owner_type: Owner type
            **defaults: Default values for new account

        Returns:
            Tuple of (Account, created boolean)
        """
        account = AccountService.get_account_by_owner(
            organization_id=organization_id,
            owner_id=owner_id,
            owner_type=owner_type
        )

        if account:
            return account, False

        account = AccountService.create_account(
            organization_id=organization_id,
            owner_id=owner_id,
            owner_type=owner_type,
            **defaults
        )

        return account, True

    @staticmethod
    def update_account(
        account_id: uuid.UUID,
        organization_id: uuid.UUID = None,
        **updates
    ) -> Account:
        """
        Update account details.

        Args:
            account_id: Account UUID
            organization_id: Optional organization filter
            **updates: Fields to update

        Returns:
            Updated Account instance
        """
        account = AccountService.get_account(account_id, organization_id)

        # Protected fields
        protected_fields = {'id', 'organization_id', 'account_number', 'created_at'}

        for field, value in updates.items():
            if field not in protected_fields:
                setattr(account, field, value)

        account.save()

        logger.info(
            f"Updated account {account.account_number}",
            extra={
                'account_id': str(account_id),
                'updates': list(updates.keys())
            }
        )

        return account

    @staticmethod
    @transaction.atomic
    def charge_account(
        account_id: uuid.UUID,
        amount: Decimal,
        description: str = None,
        reference_type: str = None,
        reference_id: uuid.UUID = None,
        allow_credit: bool = True,
        created_by: uuid.UUID = None
    ) -> Dict[str, Any]:
        """
        Charge an amount to the account.

        Args:
            account_id: Account UUID
            amount: Amount to charge
            description: Charge description
            reference_type: Reference type (flight, booking, etc.)
            reference_id: Reference UUID
            allow_credit: Allow using credit limit
            created_by: User who initiated charge

        Returns:
            Dict with charge details

        Raises:
            InsufficientBalanceError: If insufficient balance
            AccountSuspendedError: If account is suspended
        """
        # Lock account row for update
        account = Account.objects.select_for_update().get(id=account_id)

        # Check account status
        if account.status == AccountStatus.SUSPENDED:
            raise AccountSuspendedError(
                f"Account {account.account_number} is suspended"
            )

        if account.status == AccountStatus.CLOSED:
            raise AccountServiceError(
                f"Account {account.account_number} is closed"
            )

        # Check balance
        available = account.available_balance if allow_credit else account.balance

        if amount > available:
            raise InsufficientBalanceError(
                f"Insufficient balance. Required: {amount}, Available: {available}"
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

        logger.info(
            f"Charged {amount} to account {account.account_number}",
            extra={
                'account_id': str(account_id),
                'amount': float(amount),
                'balance_before': float(balance_before),
                'balance_after': float(account.balance)
            }
        )

        return {
            'success': True,
            'account_id': account_id,
            'amount': amount,
            'balance_before': balance_before,
            'balance_after': account.balance,
            'description': description,
            'reference_type': reference_type,
            'reference_id': reference_id,
        }

    @staticmethod
    @transaction.atomic
    def credit_account(
        account_id: uuid.UUID,
        amount: Decimal,
        description: str = None,
        reference_type: str = None,
        reference_id: uuid.UUID = None,
        created_by: uuid.UUID = None
    ) -> Dict[str, Any]:
        """
        Add credit to the account.

        Args:
            account_id: Account UUID
            amount: Amount to credit
            description: Credit description
            reference_type: Reference type
            reference_id: Reference UUID
            created_by: User who initiated credit

        Returns:
            Dict with credit details
        """
        # Lock account row for update
        account = Account.objects.select_for_update().get(id=account_id)

        # Record balance before
        balance_before = account.balance

        # Apply credit
        account.balance += amount
        account.total_paid += amount
        account.last_transaction_at = timezone.now()
        account.last_payment_at = timezone.now()
        account.save(update_fields=[
            'balance', 'total_paid', 'last_transaction_at',
            'last_payment_at', 'updated_at'
        ])

        logger.info(
            f"Credited {amount} to account {account.account_number}",
            extra={
                'account_id': str(account_id),
                'amount': float(amount),
                'balance_before': float(balance_before),
                'balance_after': float(account.balance)
            }
        )

        return {
            'success': True,
            'account_id': account_id,
            'amount': amount,
            'balance_before': balance_before,
            'balance_after': account.balance,
            'description': description,
            'reference_type': reference_type,
            'reference_id': reference_id,
        }

    @staticmethod
    @transaction.atomic
    def transfer_balance(
        from_account_id: uuid.UUID,
        to_account_id: uuid.UUID,
        amount: Decimal,
        description: str = None,
        created_by: uuid.UUID = None
    ) -> Dict[str, Any]:
        """
        Transfer balance between accounts.

        Args:
            from_account_id: Source account UUID
            to_account_id: Destination account UUID
            amount: Amount to transfer
            description: Transfer description
            created_by: User who initiated transfer

        Returns:
            Dict with transfer details
        """
        if from_account_id == to_account_id:
            raise AccountServiceError("Cannot transfer to the same account")

        # Lock both accounts
        from_account = Account.objects.select_for_update().get(id=from_account_id)
        to_account = Account.objects.select_for_update().get(id=to_account_id)

        # Check source balance
        if from_account.balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient balance for transfer. "
                f"Required: {amount}, Available: {from_account.balance}"
            )

        # Perform transfer
        from_balance_before = from_account.balance
        to_balance_before = to_account.balance

        from_account.balance -= amount
        to_account.balance += amount

        from_account.last_transaction_at = timezone.now()
        to_account.last_transaction_at = timezone.now()

        from_account.save(update_fields=['balance', 'last_transaction_at', 'updated_at'])
        to_account.save(update_fields=['balance', 'last_transaction_at', 'updated_at'])

        logger.info(
            f"Transferred {amount} from {from_account.account_number} "
            f"to {to_account.account_number}",
            extra={
                'from_account_id': str(from_account_id),
                'to_account_id': str(to_account_id),
                'amount': float(amount)
            }
        )

        return {
            'success': True,
            'from_account_id': from_account_id,
            'to_account_id': to_account_id,
            'amount': amount,
            'from_balance_before': from_balance_before,
            'from_balance_after': from_account.balance,
            'to_balance_before': to_balance_before,
            'to_balance_after': to_account.balance,
            'description': description,
        }

    @staticmethod
    def update_credit_limit(
        account_id: uuid.UUID,
        new_limit: Decimal,
        reason: str = None,
        updated_by: uuid.UUID = None
    ) -> Account:
        """
        Update account credit limit.

        Args:
            account_id: Account UUID
            new_limit: New credit limit
            reason: Reason for change
            updated_by: User who made the change

        Returns:
            Updated Account instance
        """
        account = AccountService.get_account(account_id)
        old_limit = account.credit_limit

        account.credit_limit = new_limit
        account.save(update_fields=['credit_limit', 'updated_at'])

        logger.info(
            f"Updated credit limit for account {account.account_number}",
            extra={
                'account_id': str(account_id),
                'old_limit': float(old_limit),
                'new_limit': float(new_limit),
                'reason': reason
            }
        )

        return account

    @staticmethod
    def suspend_account(
        account_id: uuid.UUID,
        reason: str,
        suspended_by: uuid.UUID = None
    ) -> Account:
        """
        Suspend an account.

        Args:
            account_id: Account UUID
            reason: Suspension reason
            suspended_by: User who suspended the account

        Returns:
            Updated Account instance
        """
        account = AccountService.get_account(account_id)
        account.status = AccountStatus.SUSPENDED
        account.status_reason = reason
        account.save(update_fields=['status', 'status_reason', 'updated_at'])

        logger.warning(
            f"Suspended account {account.account_number}",
            extra={
                'account_id': str(account_id),
                'reason': reason,
                'suspended_by': str(suspended_by) if suspended_by else None
            }
        )

        return account

    @staticmethod
    def reactivate_account(
        account_id: uuid.UUID,
        reactivated_by: uuid.UUID = None
    ) -> Account:
        """
        Reactivate a suspended account.

        Args:
            account_id: Account UUID
            reactivated_by: User who reactivated the account

        Returns:
            Updated Account instance
        """
        account = AccountService.get_account(account_id)

        if account.status != AccountStatus.SUSPENDED:
            raise AccountServiceError(
                f"Account {account.account_number} is not suspended"
            )

        account.status = AccountStatus.ACTIVE
        account.status_reason = None
        account.save(update_fields=['status', 'status_reason', 'updated_at'])

        logger.info(
            f"Reactivated account {account.account_number}",
            extra={
                'account_id': str(account_id),
                'reactivated_by': str(reactivated_by) if reactivated_by else None
            }
        )

        return account

    @staticmethod
    def close_account(
        account_id: uuid.UUID,
        reason: str = None,
        closed_by: uuid.UUID = None
    ) -> Account:
        """
        Close an account.

        Args:
            account_id: Account UUID
            reason: Closure reason
            closed_by: User who closed the account

        Returns:
            Updated Account instance
        """
        account = AccountService.get_account(account_id)

        # Check for outstanding balance
        if account.balance < 0:
            raise AccountServiceError(
                f"Cannot close account with outstanding balance: {account.balance}"
            )

        account.status = AccountStatus.CLOSED
        account.status_reason = reason
        account.closed_at = timezone.now()
        account.save(update_fields=[
            'status', 'status_reason', 'closed_at', 'updated_at'
        ])

        logger.info(
            f"Closed account {account.account_number}",
            extra={
                'account_id': str(account_id),
                'reason': reason,
                'closed_by': str(closed_by) if closed_by else None
            }
        )

        return account

    @staticmethod
    def get_account_summary(
        account_id: uuid.UUID,
        organization_id: uuid.UUID = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive account summary.

        Args:
            account_id: Account UUID
            organization_id: Optional organization filter

        Returns:
            Dict with account summary
        """
        account = AccountService.get_account(account_id, organization_id)

        return {
            'account_id': str(account.id),
            'account_number': account.account_number,
            'owner_id': str(account.owner_id),
            'owner_type': account.owner_type,
            'account_type': account.account_type,
            'status': account.status,
            'balance': float(account.balance),
            'credit_limit': float(account.credit_limit),
            'available_balance': float(account.available_balance),
            'pending_charges': float(account.pending_charges),
            'outstanding_balance': float(account.outstanding_balance),
            'is_low_balance': account.is_low_balance,
            'is_overdrawn': account.is_overdrawn,
            'total_charged': float(account.total_charged),
            'total_paid': float(account.total_paid),
            'total_refunded': float(account.total_refunded),
            'currency': account.currency,
            'auto_pay_enabled': account.auto_pay_enabled,
            'last_transaction_at': account.last_transaction_at.isoformat() if account.last_transaction_at else None,
            'last_payment_at': account.last_payment_at.isoformat() if account.last_payment_at else None,
            'created_at': account.created_at.isoformat(),
        }

    @staticmethod
    def list_accounts(
        organization_id: uuid.UUID,
        account_type: str = None,
        status: str = None,
        is_overdrawn: bool = None,
        search: str = None,
        order_by: str = '-created_at',
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List accounts with filtering.

        Args:
            organization_id: Organization UUID
            account_type: Filter by account type
            status: Filter by status
            is_overdrawn: Filter by overdrawn status
            search: Search in account number and owner name
            order_by: Order by field
            limit: Max results
            offset: Result offset

        Returns:
            Dict with accounts and pagination info
        """
        queryset = Account.objects.filter(organization_id=organization_id)

        if account_type:
            queryset = queryset.filter(account_type=account_type)

        if status:
            queryset = queryset.filter(status=status)

        if is_overdrawn is not None:
            if is_overdrawn:
                queryset = queryset.filter(balance__lt=0)
            else:
                queryset = queryset.filter(balance__gte=0)

        if search:
            queryset = queryset.filter(
                Q(account_number__icontains=search) |
                Q(billing_name__icontains=search) |
                Q(billing_email__icontains=search)
            )

        total = queryset.count()
        accounts = queryset.order_by(order_by)[offset:offset + limit]

        return {
            'accounts': [
                AccountService.get_account_summary(acc.id)
                for acc in accounts
            ],
            'total': total,
            'limit': limit,
            'offset': offset,
        }

    @staticmethod
    def get_overdue_accounts(
        organization_id: uuid.UUID,
        days_overdue: int = 30
    ) -> List[Account]:
        """
        Get accounts with overdue balances.

        Args:
            organization_id: Organization UUID
            days_overdue: Minimum days overdue

        Returns:
            List of overdue accounts
        """
        cutoff_date = timezone.now() - timedelta(days=days_overdue)

        return list(Account.objects.filter(
            organization_id=organization_id,
            balance__lt=0,
            status=AccountStatus.ACTIVE,
            last_payment_at__lt=cutoff_date
        ).order_by('balance'))

    @staticmethod
    def get_low_balance_accounts(
        organization_id: uuid.UUID,
        threshold: Decimal = None
    ) -> List[Account]:
        """
        Get accounts with low balance.

        Args:
            organization_id: Organization UUID
            threshold: Balance threshold

        Returns:
            List of low balance accounts
        """
        queryset = Account.objects.filter(
            organization_id=organization_id,
            status=AccountStatus.ACTIVE
        )

        if threshold is not None:
            queryset = queryset.filter(balance__lt=threshold)
        else:
            queryset = queryset.filter(balance__lt=F('low_balance_threshold'))

        return list(queryset.order_by('balance'))

    @staticmethod
    def recalculate_totals(account_id: uuid.UUID) -> Account:
        """
        Recalculate account totals from transactions.

        Args:
            account_id: Account UUID

        Returns:
            Updated Account instance
        """
        from ..models.transaction import Transaction, TransactionType, TransactionStatus

        account = AccountService.get_account(account_id)

        # Calculate totals from completed transactions
        transactions = Transaction.objects.filter(
            account_id=account_id,
            status=TransactionStatus.COMPLETED
        )

        charged = transactions.filter(
            transaction_type=TransactionType.CHARGE
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        paid = transactions.filter(
            transaction_type=TransactionType.PAYMENT
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        refunded = transactions.filter(
            transaction_type=TransactionType.REFUND
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        credits = transactions.filter(
            transaction_type=TransactionType.CREDIT
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Update account
        account.total_charged = charged
        account.total_paid = paid
        account.total_refunded = refunded
        account.balance = paid + credits + refunded - charged

        account.save(update_fields=[
            'total_charged', 'total_paid', 'total_refunded',
            'balance', 'updated_at'
        ])

        logger.info(
            f"Recalculated totals for account {account.account_number}",
            extra={
                'account_id': str(account_id),
                'balance': float(account.balance)
            }
        )

        return account

    @staticmethod
    def _generate_account_number(organization_id: uuid.UUID) -> str:
        """Generate unique account number."""
        year = timezone.now().year
        count = Account.objects.filter(
            organization_id=organization_id,
            created_at__year=year
        ).count() + 1

        return f"ACC-{year}-{count:06d}"
