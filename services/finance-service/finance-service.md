# 💰 MODÜL 11: FİNANS SERVİSİ (Finance Service)

## 1. GENEL BAKIŞ

### 1.1 Servis Bilgileri

| Özellik | Değer |
|---------|-------|
| Servis Adı | finance-service |
| Port | 8010 |
| Veritabanı | finance_db |
| Prefix | /api/v1/finance |

### 1.2 Sorumluluklar

- Hesap ve bakiye yönetimi
- Fatura oluşturma ve yönetimi
- Ödeme işlemleri
- Fiyatlandırma ve ücret hesaplama
- Kredi/Paket yönetimi
- Mali raporlama
- Ödeme gateway entegrasyonları

---

## 2. VERİTABANI ŞEMASI

### 2.1 Accounts (Hesaplar)

```sql
-- =============================================================================
-- ACCOUNTS (Müşteri Hesapları)
-- =============================================================================
CREATE TABLE accounts (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Hesap Sahibi
    account_type            VARCHAR(20) NOT NULL,
    -- student, pilot, instructor, company
    
    owner_id                UUID NOT NULL,  -- user_id veya company_id
    owner_type              VARCHAR(20) NOT NULL,
    -- user, company
    
    -- Hesap Numarası
    account_number          VARCHAR(50) UNIQUE,
    
    -- Bakiye
    balance                 DECIMAL(12,2) DEFAULT 0,
    credit_limit            DECIMAL(12,2) DEFAULT 0,
    available_balance       DECIMAL(12,2) DEFAULT 0,
    
    -- Para Birimi
    currency                CHAR(3) DEFAULT 'USD',
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'active',
    -- active, suspended, closed
    
    -- Ayarlar
    auto_charge             BOOLEAN DEFAULT true,
    require_prepayment      BOOLEAN DEFAULT false,
    minimum_balance         DECIMAL(10,2) DEFAULT 0,
    low_balance_alert       DECIMAL(10,2) DEFAULT 100,
    
    -- Ödeme Bilgileri
    payment_terms_days      INTEGER DEFAULT 30,
    default_payment_method  UUID,
    
    -- İstatistikler
    total_charged           DECIMAL(12,2) DEFAULT 0,
    total_paid              DECIMAL(12,2) DEFAULT 0,
    total_refunded          DECIMAL(12,2) DEFAULT 0,
    
    last_transaction_at     TIMESTAMP,
    last_payment_at         TIMESTAMP,
    
    -- Notlar
    notes                   TEXT,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_accounts_org ON accounts(organization_id);
CREATE INDEX idx_accounts_owner ON accounts(owner_id, owner_type);
CREATE INDEX idx_accounts_balance ON accounts(balance);
```

### 2.2 Transactions (İşlemler)

```sql
-- =============================================================================
-- TRANSACTIONS (Finansal İşlemler)
-- =============================================================================
CREATE TABLE transactions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    account_id              UUID NOT NULL REFERENCES accounts(id),
    
    -- İşlem Numarası
    transaction_number      VARCHAR(50) UNIQUE,
    
    -- Tip
    transaction_type        VARCHAR(50) NOT NULL,
    -- charge, payment, refund, credit, adjustment, transfer
    
    -- Alt Tip
    transaction_subtype     VARCHAR(50),
    -- flight_charge, instructor_charge, fuel_charge,
    -- membership_fee, deposit, credit_purchase,
    -- cancellation_fee, no_show_fee
    
    -- Tutar
    amount                  DECIMAL(12,2) NOT NULL,
    currency                CHAR(3) DEFAULT 'USD',
    
    -- Bakiye Etkisi
    balance_before          DECIMAL(12,2),
    balance_after           DECIMAL(12,2),
    
    -- İlişkili Kayıtlar
    reference_type          VARCHAR(50),
    -- flight, booking, invoice, package, membership
    reference_id            UUID,
    
    -- Açıklama
    description             TEXT,
    line_items              JSONB DEFAULT '[]',
    -- [{"description": "Aircraft rental - 1.5 hrs", "amount": 225.00}]
    
    -- Ödeme Bilgisi
    payment_method          VARCHAR(50),
    -- cash, credit_card, bank_transfer, account_credit, package
    
    payment_reference       VARCHAR(255),
    gateway_transaction_id  VARCHAR(255),
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'completed',
    -- pending, completed, failed, cancelled, reversed
    
    -- İptal/İade
    reversed                BOOLEAN DEFAULT false,
    reversal_id             UUID,
    reversal_reason         TEXT,
    
    -- Fatura
    invoice_id              UUID,
    
    -- Vergi
    tax_amount              DECIMAL(10,2) DEFAULT 0,
    tax_rate                DECIMAL(5,2),
    
    -- İşlemi Yapan
    created_by              UUID,
    approved_by             UUID,
    
    -- Metadata
    metadata                JSONB DEFAULT '{}',
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_transactions_org ON transactions(organization_id);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
CREATE INDEX idx_transactions_date ON transactions(created_at DESC);
CREATE INDEX idx_transactions_reference ON transactions(reference_type, reference_id);
```

### 2.3 Invoices (Faturalar)

```sql
-- =============================================================================
-- INVOICES (Faturalar)
-- =============================================================================
CREATE TABLE invoices (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    account_id              UUID NOT NULL REFERENCES accounts(id),
    
    -- Fatura Numarası
    invoice_number          VARCHAR(50) UNIQUE NOT NULL,
    
    -- Tip
    invoice_type            VARCHAR(20) DEFAULT 'standard',
    -- standard, credit_note, proforma
    
    -- Müşteri Bilgileri
    customer_name           VARCHAR(255),
    customer_email          VARCHAR(255),
    customer_address        TEXT,
    customer_tax_id         VARCHAR(100),
    
    -- Tarihler
    invoice_date            DATE NOT NULL,
    due_date                DATE NOT NULL,
    paid_date               DATE,
    
    -- Tutarlar
    subtotal                DECIMAL(12,2) NOT NULL,
    tax_amount              DECIMAL(10,2) DEFAULT 0,
    discount_amount         DECIMAL(10,2) DEFAULT 0,
    total_amount            DECIMAL(12,2) NOT NULL,
    
    amount_paid             DECIMAL(12,2) DEFAULT 0,
    amount_due              DECIMAL(12,2),
    
    -- Para Birimi
    currency                CHAR(3) DEFAULT 'USD',
    exchange_rate           DECIMAL(10,6) DEFAULT 1,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'draft',
    -- draft, sent, viewed, paid, partial, overdue, cancelled, void
    
    -- Kalemler
    line_items              JSONB NOT NULL DEFAULT '[]',
    -- [
    --   {
    --     "description": "Flight Training - C172",
    --     "quantity": 1.5,
    --     "unit": "hour",
    --     "unit_price": 150.00,
    --     "amount": 225.00,
    --     "tax_rate": 18,
    --     "reference_type": "flight",
    --     "reference_id": "uuid"
    --   }
    -- ]
    
    -- Vergi Detayları
    tax_details             JSONB DEFAULT '[]',
    -- [{"name": "KDV", "rate": 18, "amount": 40.50}]
    
    -- Notlar
    notes                   TEXT,
    terms                   TEXT,
    footer                  TEXT,
    
    -- PDF
    pdf_url                 VARCHAR(500),
    pdf_generated_at        TIMESTAMP,
    
    -- Gönderim
    sent_at                 TIMESTAMP,
    sent_to                 VARCHAR(255),
    viewed_at               TIMESTAMP,
    
    -- Hatırlatmalar
    reminder_count          INTEGER DEFAULT 0,
    last_reminder_at        TIMESTAMP,
    
    -- Ödeme
    payment_link            VARCHAR(500),
    payment_instructions    TEXT,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID
);

CREATE INDEX idx_invoices_account ON invoices(account_id);
CREATE INDEX idx_invoices_org ON invoices(organization_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_due ON invoices(due_date) WHERE status NOT IN ('paid', 'cancelled');
```

### 2.4 Pricing Rules (Fiyatlandırma Kuralları)

```sql
-- =============================================================================
-- PRICING_RULES (Fiyatlandırma Kuralları)
-- =============================================================================
CREATE TABLE pricing_rules (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Tanımlama
    name                    VARCHAR(255) NOT NULL,
    code                    VARCHAR(50),
    description             TEXT,
    
    -- Kapsam
    pricing_type            VARCHAR(50) NOT NULL,
    -- aircraft, instructor, fuel, landing, package, membership
    
    target_id               UUID,  -- aircraft_id, user_id vs.
    
    -- Fiyat
    base_price              DECIMAL(10,2) NOT NULL,
    currency                CHAR(3) DEFAULT 'USD',
    
    unit                    VARCHAR(20) NOT NULL,
    -- hour, flight, day, month, landing, liter, gallon
    
    -- Hesaplama
    calculation_method      VARCHAR(20) DEFAULT 'per_unit',
    -- per_unit, flat, tiered, block
    
    -- Blok Fiyatlandırma
    block_size              DECIMAL(5,2),  -- örn: 0.1 saat bloklar
    minimum_charge          DECIMAL(10,2),
    
    -- Kademeli Fiyatlandırma
    tiers                   JSONB DEFAULT '[]',
    -- [{"from": 0, "to": 10, "price": 150}, {"from": 10, "to": null, "price": 140}]
    
    -- Zaman Bazlı Fiyatlandırma
    time_based_rates        JSONB DEFAULT '{}',
    -- {"weekend": 1.1, "night": 1.2, "holiday": 1.25}
    
    -- İndirimler
    discount_eligible       BOOLEAN DEFAULT true,
    member_discount_percent DECIMAL(5,2),
    
    -- Vergi
    tax_inclusive           BOOLEAN DEFAULT false,
    tax_rate                DECIMAL(5,2),
    
    -- Geçerlilik
    effective_from          DATE,
    effective_to            DATE,
    
    -- Durum
    is_active               BOOLEAN DEFAULT true,
    priority                INTEGER DEFAULT 0,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pricing_org ON pricing_rules(organization_id);
CREATE INDEX idx_pricing_type ON pricing_rules(pricing_type);
CREATE INDEX idx_pricing_active ON pricing_rules(is_active) WHERE is_active = true;
```

### 2.5 Credit Packages (Kredi Paketleri)

```sql
-- =============================================================================
-- CREDIT_PACKAGES (Kredi/Saat Paketleri)
-- =============================================================================
CREATE TABLE credit_packages (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Tanımlama
    name                    VARCHAR(255) NOT NULL,
    description             TEXT,
    
    -- Paket Tipi
    package_type            VARCHAR(50) NOT NULL,
    -- flight_hours, credit_amount, block_hours
    
    -- İçerik
    credit_amount           DECIMAL(10,2),  -- Para tutarı
    flight_hours            DECIMAL(6,2),   -- Uçuş saati
    
    -- Fiyat
    price                   DECIMAL(10,2) NOT NULL,
    currency                CHAR(3) DEFAULT 'USD',
    
    -- Tasarruf
    savings_amount          DECIMAL(10,2),
    savings_percent         DECIMAL(5,2),
    
    -- Kapsam
    applicable_aircraft     UUID[],  -- Boş ise tümü
    applicable_services     TEXT[],
    
    -- Geçerlilik
    validity_days           INTEGER,  -- Satın almadan itibaren
    
    -- Sınırlamalar
    max_purchases_per_user  INTEGER,
    total_available         INTEGER,
    total_sold              INTEGER DEFAULT 0,
    
    -- Durum
    is_active               BOOLEAN DEFAULT true,
    is_featured             BOOLEAN DEFAULT false,
    
    -- Görsel
    image_url               VARCHAR(500),
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- USER_PACKAGES (Kullanıcı Paketleri)
-- =============================================================================
CREATE TABLE user_packages (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    account_id              UUID NOT NULL REFERENCES accounts(id),
    package_id              UUID NOT NULL REFERENCES credit_packages(id),
    
    -- Satın Alma
    purchase_date           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    purchase_price          DECIMAL(10,2),
    transaction_id          UUID,
    
    -- Bakiye
    original_amount         DECIMAL(10,2),  -- Kredi veya saat
    remaining_amount        DECIMAL(10,2),
    
    -- Geçerlilik
    expires_at              TIMESTAMP,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'active',
    -- active, depleted, expired, cancelled
    
    -- Kullanım Geçmişi
    usage_history           JSONB DEFAULT '[]',
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_packages_account ON user_packages(account_id);
CREATE INDEX idx_user_packages_status ON user_packages(status);
```

### 2.6 Payment Methods (Ödeme Yöntemleri)

```sql
-- =============================================================================
-- PAYMENT_METHODS (Kayıtlı Ödeme Yöntemleri)
-- =============================================================================
CREATE TABLE payment_methods (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    account_id              UUID NOT NULL REFERENCES accounts(id),
    
    -- Tip
    method_type             VARCHAR(50) NOT NULL,
    -- credit_card, bank_account, paypal
    
    -- Kart Bilgileri (tokenized)
    card_brand              VARCHAR(50),  -- visa, mastercard, amex
    card_last_four          CHAR(4),
    card_exp_month          INTEGER,
    card_exp_year           INTEGER,
    
    -- Gateway Token
    gateway_customer_id     VARCHAR(255),
    gateway_payment_method_id VARCHAR(255),
    
    -- Banka Bilgileri
    bank_name               VARCHAR(255),
    account_last_four       CHAR(4),
    
    -- Durum
    is_default              BOOLEAN DEFAULT false,
    is_verified             BOOLEAN DEFAULT false,
    
    status                  VARCHAR(20) DEFAULT 'active',
    -- active, expired, invalid
    
    -- Etiket
    nickname                VARCHAR(100),
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_payment_methods_account ON payment_methods(account_id);
```

---

## 3. DJANGO MODELS

```python
# apps/core/models/finance.py

import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from common.models import TenantModel


class Account(TenantModel):
    """Finansal hesap modeli"""
    
    class AccountType(models.TextChoices):
        STUDENT = 'student', 'Öğrenci'
        PILOT = 'pilot', 'Pilot'
        INSTRUCTOR = 'instructor', 'Eğitmen'
        COMPANY = 'company', 'Şirket'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Aktif'
        SUSPENDED = 'suspended', 'Askıda'
        CLOSED = 'closed', 'Kapatılmış'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices
    )
    owner_id = models.UUIDField(db_index=True)
    owner_type = models.CharField(max_length=20)
    
    account_number = models.CharField(max_length=50, unique=True)
    
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    currency = models.CharField(max_length=3, default='USD')
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    
    auto_charge = models.BooleanField(default=True)
    require_prepayment = models.BooleanField(default=False)
    minimum_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    low_balance_alert = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    
    payment_terms_days = models.IntegerField(default=30)
    
    total_charged = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    last_transaction_at = models.DateTimeField(blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts'
    
    def __str__(self):
        return f"{self.account_number}: {self.owner_id}"
    
    @property
    def available_balance(self) -> Decimal:
        return self.balance + self.credit_limit
    
    @property
    def is_low_balance(self) -> bool:
        return self.balance < self.low_balance_alert
    
    def can_charge(self, amount: Decimal) -> bool:
        """Ücret alınabilir mi?"""
        return self.available_balance >= amount
    
    def charge(self, amount: Decimal):
        """Hesaptan ücret al"""
        self.balance -= amount
        self.total_charged += amount
        self.last_transaction_at = timezone.now()
        self.save()
    
    def credit(self, amount: Decimal):
        """Hesaba kredi ekle"""
        self.balance += amount
        self.total_paid += amount
        self.last_transaction_at = timezone.now()
        self.save()


class Transaction(TenantModel):
    """Finansal işlem modeli"""
    
    class TransactionType(models.TextChoices):
        CHARGE = 'charge', 'Ücret'
        PAYMENT = 'payment', 'Ödeme'
        REFUND = 'refund', 'İade'
        CREDIT = 'credit', 'Kredi'
        ADJUSTMENT = 'adjustment', 'Düzeltme'
        TRANSFER = 'transfer', 'Transfer'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Beklemede'
        COMPLETED = 'completed', 'Tamamlandı'
        FAILED = 'failed', 'Başarısız'
        CANCELLED = 'cancelled', 'İptal'
        REVERSED = 'reversed', 'Geri Alındı'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='transactions'
    )
    
    transaction_number = models.CharField(max_length=50, unique=True)
    
    transaction_type = models.CharField(
        max_length=50,
        choices=TransactionType.choices
    )
    transaction_subtype = models.CharField(max_length=50, blank=True, null=True)
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    balance_before = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True
    )
    balance_after = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True
    )
    
    reference_type = models.CharField(max_length=50, blank=True, null=True)
    reference_id = models.UUIDField(blank=True, null=True)
    
    description = models.TextField(blank=True, null=True)
    line_items = models.JSONField(default=list)
    
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    payment_reference = models.CharField(max_length=255, blank=True, null=True)
    gateway_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.COMPLETED
    )
    
    reversed = models.BooleanField(default=False)
    reversal_reason = models.TextField(blank=True, null=True)
    
    invoice_id = models.UUIDField(blank=True, null=True)
    
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    
    created_by = models.UUIDField(blank=True, null=True)
    
    metadata = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction_number}: {self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.transaction_number:
            date_str = timezone.now().strftime('%Y%m%d')
            count = Transaction.objects.filter(
                organization_id=self.organization_id,
                created_at__date=timezone.now().date()
            ).count() + 1
            self.transaction_number = f"TXN-{date_str}-{count:06d}"
        super().save(*args, **kwargs)


class Invoice(TenantModel):
    """Fatura modeli"""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Taslak'
        SENT = 'sent', 'Gönderildi'
        VIEWED = 'viewed', 'Görüntülendi'
        PAID = 'paid', 'Ödendi'
        PARTIAL = 'partial', 'Kısmi Ödeme'
        OVERDUE = 'overdue', 'Gecikmiş'
        CANCELLED = 'cancelled', 'İptal'
        VOID = 'void', 'Geçersiz'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='invoices'
    )
    
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_type = models.CharField(max_length=20, default='standard')
    
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField(blank=True, null=True)
    customer_address = models.TextField(blank=True, null=True)
    
    invoice_date = models.DateField()
    due_date = models.DateField()
    paid_date = models.DateField(blank=True, null=True)
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    currency = models.CharField(max_length=3, default='USD')
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    line_items = models.JSONField(default=list)
    tax_details = models.JSONField(default=list)
    
    notes = models.TextField(blank=True, null=True)
    terms = models.TextField(blank=True, null=True)
    
    pdf_url = models.URLField(max_length=500, blank=True, null=True)
    
    sent_at = models.DateTimeField(blank=True, null=True)
    viewed_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)
    
    class Meta:
        db_table = 'invoices'
        ordering = ['-invoice_date']
    
    def __str__(self):
        return f"{self.invoice_number}: {self.total_amount}"
    
    @property
    def amount_due(self) -> Decimal:
        return self.total_amount - self.amount_paid
    
    @property
    def is_overdue(self) -> bool:
        from datetime import date
        return (
            self.status not in [self.Status.PAID, self.Status.CANCELLED] and
            self.due_date < date.today()
        )
```

---

## 4. API ENDPOINTS

```yaml
# =============================================================================
# FINANCE API
# =============================================================================

# Accounts
GET /api/v1/finance/accounts:
  summary: Hesap listesi

POST /api/v1/finance/accounts:
  summary: Hesap oluştur

GET /api/v1/finance/accounts/{id}:
  summary: Hesap detayı

GET /api/v1/finance/accounts/{id}/balance:
  summary: Bakiye bilgisi

GET /api/v1/finance/accounts/{id}/transactions:
  summary: Hesap hareketleri

GET /api/v1/finance/accounts/{id}/statement:
  summary: Hesap özeti (PDF)

# My Account
GET /api/v1/finance/my/account:
  summary: Kendi hesabım

GET /api/v1/finance/my/balance:
  summary: Bakiyem

GET /api/v1/finance/my/transactions:
  summary: İşlemlerim

# Transactions
GET /api/v1/finance/transactions:
  summary: İşlem listesi

POST /api/v1/finance/transactions:
  summary: İşlem oluştur (manuel)

GET /api/v1/finance/transactions/{id}:
  summary: İşlem detayı

POST /api/v1/finance/transactions/{id}/reverse:
  summary: İşlemi geri al

# Invoices
GET /api/v1/finance/invoices:
  summary: Fatura listesi

POST /api/v1/finance/invoices:
  summary: Fatura oluştur

GET /api/v1/finance/invoices/{id}:
  summary: Fatura detayı

PUT /api/v1/finance/invoices/{id}:
  summary: Fatura güncelle

POST /api/v1/finance/invoices/{id}/send:
  summary: Faturayı gönder

POST /api/v1/finance/invoices/{id}/record-payment:
  summary: Ödeme kaydet

GET /api/v1/finance/invoices/{id}/pdf:
  summary: Fatura PDF

# Payments
POST /api/v1/finance/payments:
  summary: Ödeme al

POST /api/v1/finance/payments/process:
  summary: Kart ile ödeme işle

# Pricing
GET /api/v1/finance/pricing:
  summary: Fiyat listesi

POST /api/v1/finance/pricing/calculate:
  summary: Fiyat hesapla
  requestBody:
    content:
      application/json:
        schema:
          type: object
          properties:
            aircraft_id:
              type: string
            duration_hours:
              type: number
            instructor_id:
              type: string

# Packages
GET /api/v1/finance/packages:
  summary: Paket listesi

POST /api/v1/finance/packages/{id}/purchase:
  summary: Paket satın al

GET /api/v1/finance/my/packages:
  summary: Paketlerim

# Reports
GET /api/v1/finance/reports/revenue:
  summary: Gelir raporu

GET /api/v1/finance/reports/outstanding:
  summary: Alacak raporu

GET /api/v1/finance/reports/aging:
  summary: Yaşlandırma raporu
```

---

## 5. SERVİS KATMANI

```python
# apps/core/services/finance_service.py

from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.core.models import Account, Transaction, Invoice, PricingRule, CreditPackage
from common.exceptions import ValidationError, InsufficientFundsError
from common.events import EventBus
from common.clients import AircraftServiceClient


class FinanceService:
    def __init__(self):
        self.event_bus = EventBus()
        self.aircraft_client = AircraftServiceClient()
    
    async def get_or_create_account(
        self,
        organization_id: str,
        owner_id: str,
        owner_type: str = 'user',
        account_type: str = 'student'
    ) -> Account:
        """Hesap getir veya oluştur"""
        
        account = await Account.objects.filter(
            organization_id=organization_id,
            owner_id=owner_id,
            owner_type=owner_type
        ).afirst()
        
        if not account:
            # Hesap numarası oluştur
            count = await Account.objects.filter(
                organization_id=organization_id
            ).acount()
            account_number = f"ACC-{count + 1:06d}"
            
            account = await Account.objects.acreate(
                organization_id=organization_id,
                owner_id=owner_id,
                owner_type=owner_type,
                account_type=account_type,
                account_number=account_number
            )
        
        return account
    
    @transaction.atomic
    async def charge_flight(
        self,
        organization_id: str,
        account_id: str,
        flight_id: str,
        aircraft_id: str,
        flight_hours: float,
        instructor_id: str = None,
        instructor_hours: float = None,
        fuel_cost: float = None
    ) -> Transaction:
        """Uçuş ücreti tahsil et"""
        
        account = await Account.objects.aget(id=account_id)
        
        # Fiyatları hesapla
        line_items = []
        total = Decimal('0')
        
        # Uçak ücreti
        aircraft_rate = await self._get_aircraft_rate(organization_id, aircraft_id)
        aircraft_charge = aircraft_rate * Decimal(str(flight_hours))
        line_items.append({
            'description': f'Aircraft rental - {flight_hours} hrs',
            'quantity': flight_hours,
            'unit_price': float(aircraft_rate),
            'amount': float(aircraft_charge),
            'type': 'aircraft'
        })
        total += aircraft_charge
        
        # Eğitmen ücreti
        if instructor_id and instructor_hours:
            instructor_rate = await self._get_instructor_rate(
                organization_id, instructor_id
            )
            instructor_charge = instructor_rate * Decimal(str(instructor_hours))
            line_items.append({
                'description': f'Instructor - {instructor_hours} hrs',
                'quantity': instructor_hours,
                'unit_price': float(instructor_rate),
                'amount': float(instructor_charge),
                'type': 'instructor'
            })
            total += instructor_charge
        
        # Yakıt ücreti
        if fuel_cost:
            line_items.append({
                'description': 'Fuel',
                'amount': fuel_cost,
                'type': 'fuel'
            })
            total += Decimal(str(fuel_cost))
        
        # Bakiye kontrolü
        if not account.can_charge(total):
            raise InsufficientFundsError(
                f'Yetersiz bakiye. Gerekli: {total}, Mevcut: {account.available_balance}'
            )
        
        # İşlem oluştur
        balance_before = account.balance
        account.charge(total)
        
        txn = await Transaction.objects.acreate(
            organization_id=organization_id,
            account=account,
            transaction_type='charge',
            transaction_subtype='flight_charge',
            amount=total,
            balance_before=balance_before,
            balance_after=account.balance,
            reference_type='flight',
            reference_id=flight_id,
            description=f'Flight charge - {flight_hours} hrs',
            line_items=line_items
        )
        
        # Event
        self.event_bus.publish('finance.flight_charged', {
            'transaction_id': str(txn.id),
            'account_id': str(account.id),
            'flight_id': flight_id,
            'amount': float(total)
        })
        
        # Düşük bakiye uyarısı
        if account.is_low_balance:
            self.event_bus.publish('finance.low_balance_alert', {
                'account_id': str(account.id),
                'owner_id': str(account.owner_id),
                'balance': float(account.balance)
            })
        
        return txn
    
    @transaction.atomic
    async def process_payment(
        self,
        organization_id: str,
        account_id: str,
        amount: Decimal,
        payment_method: str,
        payment_reference: str = None,
        invoice_id: str = None
    ) -> Transaction:
        """Ödeme işle"""
        
        account = await Account.objects.aget(id=account_id)
        
        balance_before = account.balance
        account.credit(amount)
        
        txn = await Transaction.objects.acreate(
            organization_id=organization_id,
            account=account,
            transaction_type='payment',
            amount=amount,
            balance_before=balance_before,
            balance_after=account.balance,
            payment_method=payment_method,
            payment_reference=payment_reference,
            invoice_id=invoice_id,
            description=f'Payment received - {payment_method}'
        )
        
        # Fatura varsa güncelle
        if invoice_id:
            invoice = await Invoice.objects.aget(id=invoice_id)
            invoice.amount_paid += amount
            if invoice.amount_paid >= invoice.total_amount:
                invoice.status = Invoice.Status.PAID
                invoice.paid_date = date.today()
            else:
                invoice.status = Invoice.Status.PARTIAL
            await invoice.asave()
        
        # Event
        self.event_bus.publish('finance.payment_received', {
            'transaction_id': str(txn.id),
            'account_id': str(account.id),
            'amount': float(amount)
        })
        
        return txn
    
    async def calculate_flight_cost(
        self,
        organization_id: str,
        aircraft_id: str,
        duration_hours: float,
        instructor_id: str = None
    ) -> Dict[str, Any]:
        """Uçuş maliyetini hesapla (tahmini)"""
        
        breakdown = []
        total = Decimal('0')
        
        # Uçak
        aircraft_rate = await self._get_aircraft_rate(organization_id, aircraft_id)
        aircraft_cost = aircraft_rate * Decimal(str(duration_hours))
        breakdown.append({
            'item': 'Aircraft rental',
            'rate': float(aircraft_rate),
            'hours': duration_hours,
            'amount': float(aircraft_cost)
        })
        total += aircraft_cost
        
        # Eğitmen
        if instructor_id:
            instructor_rate = await self._get_instructor_rate(
                organization_id, instructor_id
            )
            instructor_cost = instructor_rate * Decimal(str(duration_hours))
            breakdown.append({
                'item': 'Instructor',
                'rate': float(instructor_rate),
                'hours': duration_hours,
                'amount': float(instructor_cost)
            })
            total += instructor_cost
        
        return {
            'breakdown': breakdown,
            'subtotal': float(total),
            'tax': 0,
            'total': float(total),
            'currency': 'USD'
        }
    
    @transaction.atomic
    async def create_invoice(
        self,
        organization_id: str,
        account_id: str,
        line_items: List[Dict],
        due_days: int = 30,
        notes: str = None
    ) -> Invoice:
        """Fatura oluştur"""
        
        account = await Account.objects.aget(id=account_id)
        
        # Hesapla
        subtotal = sum(Decimal(str(item['amount'])) for item in line_items)
        tax_rate = Decimal('0.18')  # Organizasyon ayarlarından alınmalı
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount
        
        # Fatura numarası
        year = date.today().year
        count = await Invoice.objects.filter(
            organization_id=organization_id,
            invoice_date__year=year
        ).acount() + 1
        invoice_number = f"INV-{year}-{count:06d}"
        
        invoice = await Invoice.objects.acreate(
            organization_id=organization_id,
            account=account,
            invoice_number=invoice_number,
            customer_name=f"Account {account.account_number}",
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=due_days),
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total,
            line_items=line_items,
            tax_details=[{'name': 'KDV', 'rate': 18, 'amount': float(tax_amount)}],
            notes=notes
        )
        
        return invoice
    
    async def get_account_statement(
        self,
        account_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Hesap ekstresi"""
        
        account = await Account.objects.aget(id=account_id)
        
        transactions = []
        async for txn in Transaction.objects.filter(
            account_id=account_id,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).order_by('created_at'):
            transactions.append({
                'date': txn.created_at.isoformat(),
                'number': txn.transaction_number,
                'type': txn.transaction_type,
                'description': txn.description,
                'amount': float(txn.amount),
                'balance': float(txn.balance_after) if txn.balance_after else None
            })
        
        return {
            'account_number': account.account_number,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'opening_balance': float(transactions[0]['balance'] + transactions[0]['amount']) if transactions else float(account.balance),
            'closing_balance': float(account.balance),
            'transactions': transactions,
            'summary': {
                'total_charges': sum(t['amount'] for t in transactions if t['type'] == 'charge'),
                'total_payments': sum(t['amount'] for t in transactions if t['type'] == 'payment')
            }
        }
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    async def _get_aircraft_rate(
        self,
        organization_id: str,
        aircraft_id: str
    ) -> Decimal:
        """Uçak saatlik ücretini al"""
        
        # Önce pricing rule'dan bak
        rule = await PricingRule.objects.filter(
            organization_id=organization_id,
            pricing_type='aircraft',
            target_id=aircraft_id,
            is_active=True
        ).afirst()
        
        if rule:
            return rule.base_price
        
        # Aircraft servisinden al
        aircraft = await self.aircraft_client.get_aircraft(aircraft_id)
        return Decimal(str(aircraft.get('hourly_rate_wet', 150)))
    
    async def _get_instructor_rate(
        self,
        organization_id: str,
        instructor_id: str
    ) -> Decimal:
        """Eğitmen saatlik ücretini al"""
        
        rule = await PricingRule.objects.filter(
            organization_id=organization_id,
            pricing_type='instructor',
            target_id=instructor_id,
            is_active=True
        ).afirst()
        
        if rule:
            return rule.base_price
        
        # Varsayılan
        return Decimal('50')
```

---

## 6. EVENTS

```python
# Finance Service Events

ACCOUNT_CREATED = 'finance.account_created'
BALANCE_UPDATED = 'finance.balance_updated'
LOW_BALANCE_ALERT = 'finance.low_balance_alert'

TRANSACTION_CREATED = 'finance.transaction_created'
FLIGHT_CHARGED = 'finance.flight_charged'
PAYMENT_RECEIVED = 'finance.payment_received'
REFUND_PROCESSED = 'finance.refund_processed'

INVOICE_CREATED = 'finance.invoice_created'
INVOICE_SENT = 'finance.invoice_sent'
INVOICE_PAID = 'finance.invoice_paid'
INVOICE_OVERDUE = 'finance.invoice_overdue'

PACKAGE_PURCHASED = 'finance.package_purchased'
PACKAGE_DEPLETED = 'finance.package_depleted'

# Consumed Events
FLIGHT_APPROVED = 'flight.approved'
# Handler: Uçuş ücretini hesapla ve tahsil et

BOOKING_CANCELLED = 'booking.cancelled'
# Handler: İptal ücreti tahsil et (late cancellation ise)
```

---

Bu doküman Finance Service'in tüm detaylarını içermektedir.