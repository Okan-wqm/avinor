# services/finance-service/src/apps/core/tests/test_models.py
"""
Model Tests

Tests for Finance Service database models.
"""

import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone

from ..models.account import Account, AccountType, AccountStatus
from ..models.transaction import Transaction, TransactionType, TransactionStatus
from ..models.invoice import Invoice, InvoiceType, InvoiceStatus
from ..models.pricing import PricingRule, PricingType, CalculationMethod
from ..models.package import CreditPackage, UserPackage, PackageType, PackageStatus
from ..models.payment import PaymentMethod, PaymentMethodType, PaymentMethodStatus


class AccountModelTest(TestCase):
    """Tests for Account model."""

    def setUp(self):
        self.organization_id = uuid.uuid4()
        self.owner_id = uuid.uuid4()

    def test_create_account(self):
        """Test account creation."""
        account = Account.objects.create(
            organization_id=self.organization_id,
            account_number='ACC-2024-000001',
            owner_id=self.owner_id,
            owner_type='user',
            account_type=AccountType.STUDENT,
            balance=Decimal('500.00'),
            credit_limit=Decimal('1000.00')
        )

        self.assertEqual(account.balance, Decimal('500.00'))
        self.assertEqual(account.account_type, AccountType.STUDENT)
        self.assertEqual(account.status, AccountStatus.ACTIVE)

    def test_available_balance(self):
        """Test available balance calculation."""
        account = Account.objects.create(
            organization_id=self.organization_id,
            account_number='ACC-2024-000002',
            owner_id=self.owner_id,
            owner_type='user',
            balance=Decimal('200.00'),
            credit_limit=Decimal('500.00')
        )

        self.assertEqual(account.available_balance, Decimal('700.00'))

    def test_is_overdrawn(self):
        """Test overdrawn detection."""
        account = Account.objects.create(
            organization_id=self.organization_id,
            account_number='ACC-2024-000003',
            owner_id=self.owner_id,
            owner_type='user',
            balance=Decimal('-100.00')
        )

        self.assertTrue(account.is_overdrawn)

    def test_can_charge(self):
        """Test charge capability check."""
        account = Account.objects.create(
            organization_id=self.organization_id,
            account_number='ACC-2024-000004',
            owner_id=self.owner_id,
            owner_type='user',
            balance=Decimal('100.00'),
            credit_limit=Decimal('200.00')
        )

        self.assertTrue(account.can_charge(Decimal('250.00')))
        self.assertFalse(account.can_charge(Decimal('350.00')))


class TransactionModelTest(TestCase):
    """Tests for Transaction model."""

    def setUp(self):
        self.organization_id = uuid.uuid4()
        self.account = Account.objects.create(
            organization_id=self.organization_id,
            account_number='ACC-2024-000001',
            owner_id=uuid.uuid4(),
            owner_type='user'
        )

    def test_create_transaction(self):
        """Test transaction creation."""
        txn = Transaction.objects.create(
            organization_id=self.organization_id,
            account=self.account,
            transaction_number='TXN-20241201-000001',
            transaction_type=TransactionType.CHARGE,
            amount=Decimal('150.00'),
            balance_impact=Decimal('-150.00')
        )

        self.assertEqual(txn.amount, Decimal('150.00'))
        self.assertTrue(txn.is_debit)
        self.assertFalse(txn.is_credit)

    def test_net_amount(self):
        """Test net amount calculation."""
        txn = Transaction.objects.create(
            organization_id=self.organization_id,
            account=self.account,
            transaction_number='TXN-20241201-000002',
            transaction_type=TransactionType.CHARGE,
            amount=Decimal('100.00'),
            tax_amount=Decimal('10.00'),
            discount_amount=Decimal('5.00'),
            balance_impact=Decimal('-105.00')
        )

        self.assertEqual(txn.net_amount, Decimal('105.00'))


class InvoiceModelTest(TestCase):
    """Tests for Invoice model."""

    def setUp(self):
        self.organization_id = uuid.uuid4()
        self.account = Account.objects.create(
            organization_id=self.organization_id,
            account_number='ACC-2024-000001',
            owner_id=uuid.uuid4(),
            owner_type='user',
            billing_name='Test User'
        )

    def test_create_invoice(self):
        """Test invoice creation."""
        invoice = Invoice.objects.create(
            organization_id=self.organization_id,
            account=self.account,
            invoice_number='INV-2024-000001',
            customer_name='Test User',
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            total_amount=Decimal('500.00')
        )

        self.assertEqual(invoice.total_amount, Decimal('500.00'))
        self.assertEqual(invoice.amount_due, Decimal('500.00'))
        self.assertFalse(invoice.is_overdue)

    def test_overdue_detection(self):
        """Test overdue invoice detection."""
        invoice = Invoice.objects.create(
            organization_id=self.organization_id,
            account=self.account,
            invoice_number='INV-2024-000002',
            customer_name='Test User',
            invoice_date=date.today() - timedelta(days=60),
            due_date=date.today() - timedelta(days=30),
            total_amount=Decimal('500.00'),
            status=InvoiceStatus.SENT
        )

        self.assertTrue(invoice.is_overdue)
        self.assertEqual(invoice.days_overdue, 30)

    def test_record_payment(self):
        """Test recording payment on invoice."""
        invoice = Invoice.objects.create(
            organization_id=self.organization_id,
            account=self.account,
            invoice_number='INV-2024-000003',
            customer_name='Test User',
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            total_amount=Decimal('500.00'),
            status=InvoiceStatus.SENT
        )

        invoice.record_payment(Decimal('250.00'))
        invoice.save()

        self.assertEqual(invoice.amount_paid, Decimal('250.00'))
        self.assertEqual(invoice.amount_due, Decimal('250.00'))
        self.assertEqual(invoice.status, InvoiceStatus.PARTIAL)


class PricingRuleModelTest(TestCase):
    """Tests for PricingRule model."""

    def setUp(self):
        self.organization_id = uuid.uuid4()

    def test_create_pricing_rule(self):
        """Test pricing rule creation."""
        rule = PricingRule.objects.create(
            organization_id=self.organization_id,
            name='Cessna 172 Rental',
            pricing_type=PricingType.AIRCRAFT,
            base_price=Decimal('150.00'),
            unit='hour'
        )

        self.assertEqual(rule.base_price, Decimal('150.00'))
        self.assertTrue(rule.is_effective)

    def test_calculate_price_per_unit(self):
        """Test per-unit price calculation."""
        rule = PricingRule.objects.create(
            organization_id=self.organization_id,
            name='Instructor Fee',
            pricing_type=PricingType.INSTRUCTOR,
            base_price=Decimal('75.00'),
            unit='hour',
            calculation_method=CalculationMethod.PER_UNIT
        )

        result = rule.calculate_price(Decimal('2.5'))

        self.assertEqual(result['total'], 187.5)  # 75 * 2.5

    def test_calculate_price_with_multipliers(self):
        """Test price calculation with time multipliers."""
        rule = PricingRule.objects.create(
            organization_id=self.organization_id,
            name='Weekend Aircraft Rental',
            pricing_type=PricingType.AIRCRAFT,
            base_price=Decimal('150.00'),
            unit='hour',
            weekend_rate_multiplier=Decimal('1.20')
        )

        result = rule.calculate_price(Decimal('2.0'), is_weekend=True)

        self.assertEqual(result['total'], 360.0)  # 150 * 2 * 1.2


class CreditPackageModelTest(TestCase):
    """Tests for CreditPackage model."""

    def setUp(self):
        self.organization_id = uuid.uuid4()

    def test_create_package(self):
        """Test package creation."""
        package = CreditPackage.objects.create(
            organization_id=self.organization_id,
            name='10 Hour Block',
            package_type=PackageType.FLIGHT_HOURS,
            price=Decimal('1400.00'),
            hours_amount=Decimal('10.00'),
            validity_days=365
        )

        self.assertEqual(package.price, Decimal('1400.00'))
        self.assertTrue(package.is_purchasable)


class UserPackageModelTest(TestCase):
    """Tests for UserPackage model."""

    def setUp(self):
        self.organization_id = uuid.uuid4()
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
        self.user_id = uuid.uuid4()

    def test_create_user_package(self):
        """Test user package creation."""
        user_package = UserPackage.objects.create(
            organization_id=self.organization_id,
            user_id=self.user_id,
            package=self.package,
            purchase_price=self.package.price,
            credit_remaining=self.package.effective_credit_amount,
            hours_remaining=self.package.hours_amount,
            expires_at=timezone.now() + timedelta(days=365)
        )

        self.assertEqual(user_package.credit_remaining, Decimal('1500.00'))
        self.assertEqual(user_package.hours_remaining, Decimal('10.00'))
        self.assertFalse(user_package.is_expired)

    def test_use_credit(self):
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

        user_package.use_credit(Decimal('200.00'), 'Flight charge')
        user_package.save()

        self.assertEqual(user_package.credit_remaining, Decimal('1300.00'))
        self.assertEqual(user_package.credit_used, Decimal('200.00'))


class PaymentMethodModelTest(TestCase):
    """Tests for PaymentMethod model."""

    def setUp(self):
        self.organization_id = uuid.uuid4()
        self.account = Account.objects.create(
            organization_id=self.organization_id,
            account_number='ACC-2024-000001',
            owner_id=uuid.uuid4(),
            owner_type='user'
        )

    def test_create_payment_method(self):
        """Test payment method creation."""
        pm = PaymentMethod.objects.create(
            organization_id=self.organization_id,
            account=self.account,
            method_type=PaymentMethodType.CREDIT_CARD,
            card_brand='visa',
            card_last_four='4242',
            card_exp_month=12,
            card_exp_year=2025
        )

        self.assertEqual(pm.card_brand, 'visa')
        self.assertTrue(pm.is_card)
        self.assertFalse(pm.is_expired)

    def test_expired_card_detection(self):
        """Test expired card detection."""
        pm = PaymentMethod.objects.create(
            organization_id=self.organization_id,
            account=self.account,
            method_type=PaymentMethodType.CREDIT_CARD,
            card_brand='visa',
            card_last_four='4242',
            card_exp_month=1,
            card_exp_year=2020
        )

        self.assertTrue(pm.is_expired)
