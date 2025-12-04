# services/finance-service/src/apps/core/tests/test_services.py
"""
Service Tests

Tests for Finance Service business logic services.
"""

import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock

from ..models.account import Account, AccountType, AccountStatus
from ..models.transaction import Transaction, TransactionType
from ..models.invoice import Invoice, InvoiceStatus
from ..models.pricing import PricingRule, PricingType, CalculationMethod
from ..models.package import CreditPackage, UserPackage, PackageType

from ..services.account_service import (
    AccountService,
    InsufficientBalanceError,
    AccountSuspendedError,
    AccountNotFoundError,
)
from ..services.transaction_service import (
    TransactionService,
    TransactionNotFoundError,
    TransactionReversalError,
)
from ..services.invoice_service import InvoiceService
from ..services.pricing_service import PricingService, PricingRuleNotFoundError
from ..services.package_service import PackageService, InsufficientCreditsError


class AccountServiceTest(TestCase):
    """Tests for AccountService."""

    def setUp(self):
        self.organization_id = uuid.uuid4()
        self.owner_id = uuid.uuid4()

    def test_create_account(self):
        """Test account creation."""
        account = AccountService.create_account(
            organization_id=self.organization_id,
            owner_id=self.owner_id,
            owner_type='user',
            account_type=AccountType.STUDENT
        )

        self.assertIsNotNone(account.id)
        self.assertEqual(account.owner_id, self.owner_id)
        self.assertEqual(account.balance, Decimal('0'))

    def test_get_or_create_account(self):
        """Test get or create account."""
        account1, created1 = AccountService.get_or_create_account(
            organization_id=self.organization_id,
            owner_id=self.owner_id,
            owner_type='user'
        )

        self.assertTrue(created1)

        account2, created2 = AccountService.get_or_create_account(
            organization_id=self.organization_id,
            owner_id=self.owner_id,
            owner_type='user'
        )

        self.assertFalse(created2)
        self.assertEqual(account1.id, account2.id)

    def test_charge_account(self):
        """Test charging an account."""
        account = AccountService.create_account(
            organization_id=self.organization_id,
            owner_id=self.owner_id,
            owner_type='user',
            credit_limit=Decimal('500.00')
        )

        result = AccountService.charge_account(
            account_id=account.id,
            amount=Decimal('100.00'),
            description='Test charge'
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['amount'], Decimal('100.00'))

        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal('-100.00'))

    def test_charge_insufficient_balance(self):
        """Test charging with insufficient balance."""
        account = AccountService.create_account(
            organization_id=self.organization_id,
            owner_id=self.owner_id,
            owner_type='user',
            credit_limit=Decimal('100.00')
        )

        with self.assertRaises(InsufficientBalanceError):
            AccountService.charge_account(
                account_id=account.id,
                amount=Decimal('200.00'),
                allow_credit=True
            )

    def test_credit_account(self):
        """Test crediting an account."""
        account = AccountService.create_account(
            organization_id=self.organization_id,
            owner_id=self.owner_id,
            owner_type='user'
        )

        result = AccountService.credit_account(
            account_id=account.id,
            amount=Decimal('500.00'),
            description='Test credit'
        )

        self.assertTrue(result['success'])

        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal('500.00'))

    def test_transfer_balance(self):
        """Test balance transfer between accounts."""
        account1 = AccountService.create_account(
            organization_id=self.organization_id,
            owner_id=uuid.uuid4(),
            owner_type='user'
        )

        account2 = AccountService.create_account(
            organization_id=self.organization_id,
            owner_id=uuid.uuid4(),
            owner_type='user'
        )

        # Credit first account
        AccountService.credit_account(account1.id, Decimal('500.00'))

        # Transfer
        result = AccountService.transfer_balance(
            from_account_id=account1.id,
            to_account_id=account2.id,
            amount=Decimal('200.00')
        )

        self.assertTrue(result['success'])

        account1.refresh_from_db()
        account2.refresh_from_db()

        self.assertEqual(account1.balance, Decimal('300.00'))
        self.assertEqual(account2.balance, Decimal('200.00'))

    def test_suspend_account(self):
        """Test account suspension."""
        account = AccountService.create_account(
            organization_id=self.organization_id,
            owner_id=self.owner_id,
            owner_type='user'
        )

        AccountService.suspend_account(
            account_id=account.id,
            reason='Test suspension'
        )

        account.refresh_from_db()
        self.assertEqual(account.status, AccountStatus.SUSPENDED)

    def test_charge_suspended_account(self):
        """Test that suspended accounts cannot be charged."""
        account = AccountService.create_account(
            organization_id=self.organization_id,
            owner_id=self.owner_id,
            owner_type='user',
            credit_limit=Decimal('1000.00')
        )

        AccountService.suspend_account(account.id, 'Test')

        with self.assertRaises(AccountSuspendedError):
            AccountService.charge_account(
                account_id=account.id,
                amount=Decimal('100.00')
            )


class TransactionServiceTest(TestCase):
    """Tests for TransactionService."""

    def setUp(self):
        self.organization_id = uuid.uuid4()
        self.account = Account.objects.create(
            organization_id=self.organization_id,
            account_number='ACC-2024-000001',
            owner_id=uuid.uuid4(),
            owner_type='user',
            credit_limit=Decimal('1000.00')
        )

    def test_create_charge(self):
        """Test charge transaction creation."""
        txn = TransactionService.create_charge(
            organization_id=self.organization_id,
            account_id=self.account.id,
            amount=Decimal('150.00'),
            description='Flight charge'
        )

        self.assertEqual(txn.transaction_type, TransactionType.CHARGE)
        self.assertEqual(txn.amount, Decimal('150.00'))
        self.assertEqual(txn.balance_impact, Decimal('-150.00'))

    def test_create_payment(self):
        """Test payment transaction creation."""
        txn = TransactionService.create_payment(
            organization_id=self.organization_id,
            account_id=self.account.id,
            amount=Decimal('500.00'),
            payment_method='credit_card',
            description='Card payment'
        )

        self.assertEqual(txn.transaction_type, TransactionType.PAYMENT)
        self.assertEqual(txn.balance_impact, Decimal('500.00'))

    def test_reverse_transaction(self):
        """Test transaction reversal."""
        # Create original charge
        original = TransactionService.create_charge(
            organization_id=self.organization_id,
            account_id=self.account.id,
            amount=Decimal('100.00')
        )

        # Reverse it
        reversal = TransactionService.reverse_transaction(
            transaction_id=original.id,
            reason='Customer request'
        )

        self.assertEqual(reversal.transaction_type, TransactionType.REVERSAL)
        self.assertEqual(reversal.original_transaction_id, original.id)

        original.refresh_from_db()
        self.assertTrue(original.reversed)

    def test_cannot_reverse_reversed_transaction(self):
        """Test that reversed transactions cannot be reversed again."""
        original = TransactionService.create_charge(
            organization_id=self.organization_id,
            account_id=self.account.id,
            amount=Decimal('100.00')
        )

        TransactionService.reverse_transaction(original.id, 'First reversal')

        with self.assertRaises(TransactionReversalError):
            TransactionService.reverse_transaction(original.id, 'Second attempt')


class PricingServiceTest(TestCase):
    """Tests for PricingService."""

    def setUp(self):
        self.organization_id = uuid.uuid4()

    def test_create_pricing_rule(self):
        """Test pricing rule creation."""
        rule = PricingService.create_pricing_rule(
            organization_id=self.organization_id,
            name='Cessna 172 Rental',
            pricing_type=PricingType.AIRCRAFT,
            base_price=Decimal('150.00'),
            unit='hour'
        )

        self.assertIsNotNone(rule.id)
        self.assertEqual(rule.base_price, Decimal('150.00'))

    def test_calculate_price(self):
        """Test price calculation."""
        rule = PricingService.create_pricing_rule(
            organization_id=self.organization_id,
            name='Test Rule',
            pricing_type=PricingType.AIRCRAFT,
            base_price=Decimal('100.00'),
            unit='hour'
        )

        result = PricingService.calculate_price(
            organization_id=self.organization_id,
            pricing_type=PricingType.AIRCRAFT,
            quantity=Decimal('2.5')
        )

        self.assertEqual(result['total'], 250.0)

    def test_calculate_price_with_discount(self):
        """Test price calculation with member discount."""
        rule = PricingService.create_pricing_rule(
            organization_id=self.organization_id,
            name='Test Rule',
            pricing_type=PricingType.INSTRUCTOR,
            base_price=Decimal('75.00'),
            unit='hour',
            member_discount_percent=Decimal('10.00')
        )

        result = PricingService.calculate_price(
            organization_id=self.organization_id,
            pricing_type=PricingType.INSTRUCTOR,
            quantity=Decimal('2.0'),
            is_member=True
        )

        # 75 * 2 = 150, 10% discount = 15, total = 135
        self.assertEqual(result['total'], 135.0)

    def test_calculate_price_no_rule(self):
        """Test price calculation with no rule."""
        with self.assertRaises(PricingRuleNotFoundError):
            PricingService.calculate_price(
                organization_id=self.organization_id,
                pricing_type=PricingType.LANDING,
                quantity=Decimal('1.0')
            )


class PackageServiceTest(TestCase):
    """Tests for PackageService."""

    def setUp(self):
        self.organization_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.account = Account.objects.create(
            organization_id=self.organization_id,
            account_number='ACC-2024-000001',
            owner_id=self.user_id,
            owner_type='user'
        )
        self.package = CreditPackage.objects.create(
            organization_id=self.organization_id,
            name='10 Hour Block',
            package_type=PackageType.FLIGHT_HOURS,
            price=Decimal('1400.00'),
            hours_amount=Decimal('10.00'),
            credit_amount=Decimal('1500.00'),
            effective_credit_amount=Decimal('1500.00'),
            validity_days=365
        )

    @patch('apps.core.services.transaction_service.TransactionService.create_payment')
    def test_purchase_package(self, mock_payment):
        """Test package purchase."""
        mock_payment.return_value = MagicMock(id=uuid.uuid4())

        user_package = PackageService.purchase_package(
            organization_id=self.organization_id,
            package_id=self.package.id,
            user_id=self.user_id,
            account_id=self.account.id
        )

        self.assertIsNotNone(user_package.id)
        self.assertEqual(user_package.credit_remaining, Decimal('1500.00'))
        self.assertEqual(user_package.hours_remaining, Decimal('10.00'))

    def test_use_package_credit(self):
        """Test using credit from package."""
        user_package = UserPackage.objects.create(
            organization_id=self.organization_id,
            user_id=self.user_id,
            package=self.package,
            purchase_price=self.package.price,
            credit_remaining=Decimal('1500.00'),
            hours_remaining=Decimal('10.00'),
            expires_at=timezone.now() + timedelta(days=365)
        )

        result = PackageService.use_package_credit(
            user_package_id=user_package.id,
            amount=Decimal('200.00'),
            description='Flight charge'
        )

        self.assertEqual(result['credit_remaining'], 1300.0)

    def test_use_package_insufficient_credit(self):
        """Test using more credit than available."""
        user_package = UserPackage.objects.create(
            organization_id=self.organization_id,
            user_id=self.user_id,
            package=self.package,
            purchase_price=self.package.price,
            credit_remaining=Decimal('100.00'),
            hours_remaining=Decimal('1.00'),
            expires_at=timezone.now() + timedelta(days=365)
        )

        with self.assertRaises(InsufficientCreditsError):
            PackageService.use_package_credit(
                user_package_id=user_package.id,
                amount=Decimal('200.00')
            )

    def test_get_available_credit(self):
        """Test getting total available credit."""
        UserPackage.objects.create(
            organization_id=self.organization_id,
            user_id=self.user_id,
            package=self.package,
            purchase_price=self.package.price,
            credit_remaining=Decimal('500.00'),
            expires_at=timezone.now() + timedelta(days=365)
        )

        UserPackage.objects.create(
            organization_id=self.organization_id,
            user_id=self.user_id,
            package=self.package,
            purchase_price=self.package.price,
            credit_remaining=Decimal('300.00'),
            expires_at=timezone.now() + timedelta(days=365)
        )

        total = PackageService.get_available_credit(
            organization_id=self.organization_id,
            user_id=self.user_id
        )

        self.assertEqual(total, Decimal('800.00'))


class InvoiceServiceTest(TestCase):
    """Tests for InvoiceService."""

    def setUp(self):
        self.organization_id = uuid.uuid4()
        self.account = Account.objects.create(
            organization_id=self.organization_id,
            account_number='ACC-2024-000001',
            owner_id=uuid.uuid4(),
            owner_type='user',
            billing_name='Test User',
            billing_email='test@example.com'
        )

    def test_create_invoice(self):
        """Test invoice creation."""
        line_items = [
            {
                'description': 'Flight Training',
                'quantity': 2,
                'unit_price': 150.00,
                'amount': 300.00
            }
        ]

        invoice = InvoiceService.create_invoice(
            organization_id=self.organization_id,
            account_id=self.account.id,
            line_items=line_items
        )

        self.assertIsNotNone(invoice.id)
        self.assertEqual(invoice.total_amount, Decimal('300.00'))
        self.assertEqual(invoice.status, InvoiceStatus.DRAFT)

    def test_record_payment_partial(self):
        """Test recording partial payment."""
        invoice = Invoice.objects.create(
            organization_id=self.organization_id,
            account=self.account,
            invoice_number='INV-2024-000001',
            customer_name='Test User',
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            total_amount=Decimal('500.00'),
            status=InvoiceStatus.SENT
        )

        InvoiceService.record_payment(
            invoice_id=invoice.id,
            amount=Decimal('200.00')
        )

        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal('200.00'))
        self.assertEqual(invoice.status, InvoiceStatus.PARTIAL)

    def test_record_payment_full(self):
        """Test recording full payment."""
        invoice = Invoice.objects.create(
            organization_id=self.organization_id,
            account=self.account,
            invoice_number='INV-2024-000002',
            customer_name='Test User',
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            total_amount=Decimal('500.00'),
            status=InvoiceStatus.SENT
        )

        InvoiceService.record_payment(
            invoice_id=invoice.id,
            amount=Decimal('500.00')
        )

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, InvoiceStatus.PAID)
