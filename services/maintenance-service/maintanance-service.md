# 🔧 MODÜL 05: BAKIM SERVİSİ (Maintenance Service)

## 1. GENEL BAKIŞ

### 1.1 Servis Bilgileri

| Özellik | Değer |
|---------|-------|
| Servis Adı | maintenance-service |
| Port | 8004 |
| Veritabanı | maintenance_db |
| Prefix | /api/v1/maintenance |

### 1.2 Sorumluluklar

- Bakım öğeleri yönetimi (100hr, Annual, AD, SB)
- Bakım planlaması ve takibi
- Bakım kayıtları
- Parça ve envanter yönetimi
- İş emirleri (Work Orders)
- AD/SB (Airworthiness Directive/Service Bulletin) takibi
- Bakım uyarıları ve bildirimleri

---

## 2. VERİTABANI ŞEMASI

### 2.1 Maintenance Items (Bakım Öğeleri)

```sql
-- =============================================================================
-- MAINTENANCE_ITEMS (Bakım Öğeleri Tanımı)
-- =============================================================================
CREATE TABLE maintenance_items (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    aircraft_id             UUID,  -- NULL ise şablon
    
    -- Tanımlama
    name                    VARCHAR(255) NOT NULL,
    code                    VARCHAR(50),
    description             TEXT,
    
    -- Kategori
    category                VARCHAR(50) NOT NULL,
    -- inspection, service, overhaul, replacement, ad, sb, life_limited
    
    item_type               VARCHAR(50) NOT NULL,
    -- recurring, one_time, on_condition
    
    ata_chapter             VARCHAR(10),
    
    -- Bileşen (Opsiyonel)
    component_type          VARCHAR(50),
    -- airframe, engine, propeller, avionics, landing_gear, etc.
    component_id            UUID,  -- engine_id veya propeller_id
    
    -- Düzenleyici
    is_mandatory            BOOLEAN DEFAULT true,
    regulatory_reference    VARCHAR(255),
    ad_number               VARCHAR(100),
    sb_number               VARCHAR(100),
    
    -- Tekrarlama Aralıkları
    interval_hours          DECIMAL(10,2),
    interval_cycles         INTEGER,
    interval_days           INTEGER,
    interval_months         INTEGER,
    interval_calendar_months INTEGER,
    
    -- Limit (Life Limited Parts)
    life_limit_hours        DECIMAL(10,2),
    life_limit_cycles       INTEGER,
    life_limit_months       INTEGER,
    
    -- Tolerans
    tolerance_hours         DECIMAL(10,2),
    tolerance_days          INTEGER,
    tolerance_percent       DECIMAL(5,2),
    
    -- Uyarı Eşikleri
    warning_hours           DECIMAL(10,2) DEFAULT 10,
    warning_days            INTEGER DEFAULT 30,
    critical_hours          DECIMAL(10,2) DEFAULT 5,
    critical_days           INTEGER DEFAULT 7,
    
    -- Son Yapılma
    last_done_date          DATE,
    last_done_hours         DECIMAL(10,2),
    last_done_cycles        INTEGER,
    last_done_by            VARCHAR(255),
    last_done_notes         TEXT,
    last_work_order_id      UUID,
    
    -- Sonraki Due
    next_due_date           DATE,
    next_due_hours          DECIMAL(10,2),
    next_due_cycles         INTEGER,
    
    -- Kalan (Hesaplanmış)
    remaining_hours         DECIMAL(10,2),
    remaining_days          INTEGER,
    remaining_cycles        INTEGER,
    remaining_percent       DECIMAL(5,2),
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'active',
    -- active, due, overdue, completed, deferred, not_applicable
    
    compliance_status       VARCHAR(20) DEFAULT 'compliant',
    -- compliant, due_soon, due, overdue, deferred
    
    -- Tahmini
    estimated_labor_hours   DECIMAL(6,2),
    estimated_cost          DECIMAL(10,2),
    estimated_downtime_hours INTEGER,
    
    -- Dokümanlar
    documentation_url       VARCHAR(500),
    compliance_doc_url      VARCHAR(500),
    
    -- Notlar
    notes                   TEXT,
    internal_notes          TEXT,
    
    -- Metadata
    metadata                JSONB DEFAULT '{}',
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_aircraft_maintenance_code UNIQUE(aircraft_id, code)
);

CREATE INDEX idx_maint_items_org ON maintenance_items(organization_id);
CREATE INDEX idx_maint_items_aircraft ON maintenance_items(aircraft_id);
CREATE INDEX idx_maint_items_status ON maintenance_items(status);
CREATE INDEX idx_maint_items_compliance ON maintenance_items(compliance_status);
CREATE INDEX idx_maint_items_next_due ON maintenance_items(next_due_date, next_due_hours);
CREATE INDEX idx_maint_items_category ON maintenance_items(category);
```

### 2.2 Maintenance Logs (Bakım Kayıtları)

```sql
-- =============================================================================
-- MAINTENANCE_LOGS (Yapılan Bakım Kayıtları)
-- =============================================================================
CREATE TABLE maintenance_logs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    aircraft_id             UUID NOT NULL,
    maintenance_item_id     UUID REFERENCES maintenance_items(id),
    work_order_id           UUID REFERENCES work_orders(id),
    
    -- Bakım Bilgileri
    log_number              VARCHAR(50),
    title                   VARCHAR(255) NOT NULL,
    description             TEXT,
    work_performed          TEXT NOT NULL,
    
    -- Kategori
    category                VARCHAR(50) NOT NULL,
    maintenance_type        VARCHAR(50),
    -- scheduled, unscheduled, ad_compliance, sb_compliance, inspection
    
    -- Tarih/Saat
    performed_date          DATE NOT NULL,
    started_at              TIMESTAMP,
    completed_at            TIMESTAMP,
    
    -- Uçuş Saatleri (Yapılma Anında)
    aircraft_hours          DECIMAL(10,2),
    aircraft_cycles         INTEGER,
    engine_hours            JSONB,  -- {"1": 1234.5, "2": 1234.5}
    
    -- Yapan
    performed_by            VARCHAR(255),
    technician_license      VARCHAR(100),
    organization_name       VARCHAR(255),
    organization_approval   VARCHAR(100),  -- Part-145 approval number
    
    -- İmza/Onay
    certified_by            VARCHAR(255),
    certification_type      VARCHAR(50),  -- CRS (Certificate of Release to Service)
    certification_date      TIMESTAMP,
    certification_reference VARCHAR(100),
    
    -- Dijital İmza
    signature_data          JSONB,
    signed_at               TIMESTAMP,
    signed_by_user_id       UUID,
    
    -- Parçalar
    parts_used              JSONB DEFAULT '[]',
    -- [
    --   {
    --     "part_number": "xxx",
    --     "description": "xxx",
    --     "serial_number": "xxx",
    --     "quantity": 1,
    --     "unit_cost": 100.00,
    --     "condition": "new/overhauled/serviceable"
    --   }
    -- ]
    
    parts_removed           JSONB DEFAULT '[]',
    
    -- Maliyetler
    labor_hours             DECIMAL(6,2),
    labor_rate              DECIMAL(10,2),
    labor_cost              DECIMAL(10,2),
    parts_cost              DECIMAL(10,2),
    other_cost              DECIMAL(10,2),
    total_cost              DECIMAL(10,2),
    
    -- İlgili Squawk
    squawk_id               UUID,
    
    -- Dokümanlar
    documents               JSONB DEFAULT '[]',
    photos                  JSONB DEFAULT '[]',
    
    -- Sonraki Bakım
    sets_next_due           BOOLEAN DEFAULT true,
    next_due_date           DATE,
    next_due_hours          DECIMAL(10,2),
    next_due_cycles         INTEGER,
    
    -- Notlar
    notes                   TEXT,
    internal_notes          TEXT,
    findings                TEXT,  -- Bulunan sorunlar
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'completed',
    -- draft, pending_approval, completed, rejected
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at             TIMESTAMP,
    approved_by             UUID
);

CREATE INDEX idx_maint_logs_org ON maintenance_logs(organization_id);
CREATE INDEX idx_maint_logs_aircraft ON maintenance_logs(aircraft_id);
CREATE INDEX idx_maint_logs_item ON maintenance_logs(maintenance_item_id);
CREATE INDEX idx_maint_logs_date ON maintenance_logs(performed_date DESC);
CREATE INDEX idx_maint_logs_work_order ON maintenance_logs(work_order_id);
```

### 2.3 Work Orders (İş Emirleri)

```sql
-- =============================================================================
-- WORK_ORDERS (İş Emirleri)
-- =============================================================================
CREATE TABLE work_orders (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    aircraft_id             UUID NOT NULL,
    
    -- Tanımlama
    work_order_number       VARCHAR(50) NOT NULL,
    title                   VARCHAR(255) NOT NULL,
    description             TEXT,
    
    -- Tip
    work_order_type         VARCHAR(50) NOT NULL,
    -- scheduled_maintenance, unscheduled_maintenance, inspection,
    -- repair, modification, ad_compliance, sb_compliance
    
    priority                VARCHAR(20) DEFAULT 'normal',
    -- low, normal, high, urgent, aog
    
    -- Planlama
    scheduled_start         TIMESTAMP,
    scheduled_end           TIMESTAMP,
    actual_start            TIMESTAMP,
    actual_end              TIMESTAMP,
    
    -- Bakım Lokasyonu
    location_id             UUID,
    hangar                  VARCHAR(100),
    
    -- Atama
    assigned_to             UUID,
    assigned_team           VARCHAR(100),
    
    -- İlgili Öğeler
    maintenance_items       UUID[],  -- İlgili bakım öğeleri
    squawk_ids              UUID[],  -- İlgili squawk'lar
    
    -- Tahminler
    estimated_hours         DECIMAL(6,2),
    estimated_cost          DECIMAL(10,2),
    estimated_parts_cost    DECIMAL(10,2),
    
    -- Gerçekleşen
    actual_hours            DECIMAL(6,2),
    actual_cost             DECIMAL(10,2),
    actual_parts_cost       DECIMAL(10,2),
    
    -- Parçalar
    required_parts          JSONB DEFAULT '[]',
    parts_status            VARCHAR(20) DEFAULT 'pending',
    -- pending, ordered, partial, complete
    
    -- Onay
    requires_approval       BOOLEAN DEFAULT false,
    approved_by             UUID,
    approved_at             TIMESTAMP,
    approval_notes          TEXT,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'draft',
    -- draft, planned, in_progress, on_hold, completed, cancelled
    
    on_hold_reason          TEXT,
    cancellation_reason     TEXT,
    
    -- Müşteri Onayı (Harici bakım için)
    customer_approved       BOOLEAN DEFAULT false,
    customer_approved_at    TIMESTAMP,
    customer_approval_ref   VARCHAR(100),
    
    -- Sonuç
    completion_notes        TEXT,
    findings                TEXT,
    recommendations         TEXT,
    
    -- Dokümanlar
    documents               JSONB DEFAULT '[]',
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at            TIMESTAMP,
    completed_by            UUID
);

CREATE INDEX idx_work_orders_org ON work_orders(organization_id);
CREATE INDEX idx_work_orders_aircraft ON work_orders(aircraft_id);
CREATE INDEX idx_work_orders_status ON work_orders(status);
CREATE INDEX idx_work_orders_scheduled ON work_orders(scheduled_start);
CREATE INDEX idx_work_orders_number ON work_orders(work_order_number);
```

### 2.4 Parts Inventory (Parça Envanteri)

```sql
-- =============================================================================
-- PARTS_INVENTORY (Parça Envanteri)
-- =============================================================================
CREATE TABLE parts_inventory (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    location_id             UUID,
    
    -- Parça Bilgileri
    part_number             VARCHAR(100) NOT NULL,
    alternate_part_numbers  TEXT[],
    description             VARCHAR(500) NOT NULL,
    
    -- Kategorilendirme
    category                VARCHAR(50),
    ata_chapter             VARCHAR(10),
    
    -- Üretici
    manufacturer            VARCHAR(255),
    manufacturer_code       VARCHAR(50),
    
    -- Stok
    quantity_on_hand        INTEGER DEFAULT 0,
    quantity_reserved       INTEGER DEFAULT 0,
    quantity_available      INTEGER DEFAULT 0,
    minimum_quantity        INTEGER DEFAULT 0,
    reorder_quantity        INTEGER,
    
    -- Birim
    unit_of_measure         VARCHAR(20) DEFAULT 'each',
    -- each, set, kit, gallon, liter, quart
    
    -- Konum
    bin_location            VARCHAR(100),
    shelf                   VARCHAR(50),
    
    -- Durum
    condition               VARCHAR(20) DEFAULT 'new',
    -- new, overhauled, repaired, serviceable, unserviceable
    
    -- Sertifikasyon
    is_serialized           BOOLEAN DEFAULT false,
    is_lot_controlled       BOOLEAN DEFAULT false,
    requires_certification  BOOLEAN DEFAULT true,
    
    -- Fiyat
    unit_cost               DECIMAL(10,2),
    average_cost            DECIMAL(10,2),
    last_purchase_price     DECIMAL(10,2),
    
    -- Son İşlemler
    last_received_date      DATE,
    last_issued_date        DATE,
    last_count_date         DATE,
    
    -- Tedarikçi
    preferred_vendor_id     UUID,
    vendor_part_number      VARCHAR(100),
    lead_time_days          INTEGER,
    
    -- Dokümanlar
    specification_url       VARCHAR(500),
    
    -- Notlar
    notes                   TEXT,
    
    -- Metadata
    metadata                JSONB DEFAULT '{}',
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'active',
    -- active, discontinued, obsolete
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_parts_org ON parts_inventory(organization_id);
CREATE INDEX idx_parts_number ON parts_inventory(part_number);
CREATE INDEX idx_parts_location ON parts_inventory(location_id);
CREATE INDEX idx_parts_low_stock ON parts_inventory(quantity_available) 
    WHERE quantity_available <= minimum_quantity;
```

### 2.5 AD/SB Tracking

```sql
-- =============================================================================
-- AD_SB_TRACKING (AD/SB Takibi)
-- =============================================================================
CREATE TABLE ad_sb_tracking (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    aircraft_id             UUID NOT NULL,
    
    -- Tip
    directive_type          VARCHAR(10) NOT NULL,  -- AD, SB, SL, SIL
    
    -- Tanımlama
    directive_number        VARCHAR(100) NOT NULL,
    title                   VARCHAR(500) NOT NULL,
    description             TEXT,
    
    -- Yayınlayan
    issuing_authority       VARCHAR(50),  -- FAA, EASA, manufacturer
    issue_date              DATE,
    effective_date          DATE,
    
    -- Uygulanabilirlik
    applicability           TEXT,
    affected_serial_numbers TEXT,
    is_applicable           BOOLEAN DEFAULT true,
    not_applicable_reason   TEXT,
    
    -- Uyum Gereksinimleri
    compliance_required     BOOLEAN DEFAULT true,
    compliance_method       TEXT,
    
    -- Terminating Action
    is_terminating          BOOLEAN DEFAULT false,
    terminating_action      TEXT,
    
    -- Uyum Tarihleri
    initial_compliance_date DATE,
    initial_compliance_hours DECIMAL(10,2),
    recurring_interval_days INTEGER,
    recurring_interval_hours DECIMAL(10,2),
    
    -- Mevcut Uyum Durumu
    compliance_status       VARCHAR(20) DEFAULT 'pending',
    -- pending, compliant, non_compliant, not_applicable, deferred
    
    last_compliance_date    DATE,
    last_compliance_hours   DECIMAL(10,2),
    next_compliance_date    DATE,
    next_compliance_hours   DECIMAL(10,2),
    
    -- İlgili Bakım
    maintenance_item_id     UUID REFERENCES maintenance_items(id),
    work_order_id           UUID,
    
    -- Dokümanlar
    directive_document_url  VARCHAR(500),
    compliance_document_url VARCHAR(500),
    
    -- Notlar
    notes                   TEXT,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ad_sb_org ON ad_sb_tracking(organization_id);
CREATE INDEX idx_ad_sb_aircraft ON ad_sb_tracking(aircraft_id);
CREATE INDEX idx_ad_sb_status ON ad_sb_tracking(compliance_status);
CREATE INDEX idx_ad_sb_type ON ad_sb_tracking(directive_type);
```

---

## 3. DJANGO MODELS

```python
# apps/core/models/maintenance.py

import uuid
from django.db import models
from django.utils import timezone
from decimal import Decimal
from common.models import TenantModel


class MaintenanceItem(TenantModel):
    """Bakım öğesi modeli"""
    
    class Category(models.TextChoices):
        INSPECTION = 'inspection', 'Denetim'
        SERVICE = 'service', 'Servis'
        OVERHAUL = 'overhaul', 'Revizyon'
        REPLACEMENT = 'replacement', 'Değişim'
        AD = 'ad', 'Uçuşa Elverişlilik Direktifi'
        SB = 'sb', 'Servis Bülteni'
        LIFE_LIMITED = 'life_limited', 'Ömür Sınırlı'
    
    class ItemType(models.TextChoices):
        RECURRING = 'recurring', 'Tekrarlayan'
        ONE_TIME = 'one_time', 'Tek Seferlik'
        ON_CONDITION = 'on_condition', 'Koşula Bağlı'
    
    class ComplianceStatus(models.TextChoices):
        COMPLIANT = 'compliant', 'Uyumlu'
        DUE_SOON = 'due_soon', 'Yaklaşıyor'
        DUE = 'due', 'Zamanı Geldi'
        OVERDUE = 'overdue', 'Gecikmiş'
        DEFERRED = 'deferred', 'Ertelendi'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aircraft_id = models.UUIDField(db_index=True)
    
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    category = models.CharField(max_length=50, choices=Category.choices)
    item_type = models.CharField(
        max_length=50,
        choices=ItemType.choices,
        default=ItemType.RECURRING
    )
    
    is_mandatory = models.BooleanField(default=True)
    regulatory_reference = models.CharField(max_length=255, blank=True, null=True)
    
    # Aralıklar
    interval_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    interval_days = models.IntegerField(blank=True, null=True)
    interval_months = models.IntegerField(blank=True, null=True)
    
    # Uyarı eşikleri
    warning_hours = models.DecimalField(
        max_digits=10, decimal_places=2, default=10
    )
    warning_days = models.IntegerField(default=30)
    
    # Son yapılma
    last_done_date = models.DateField(blank=True, null=True)
    last_done_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    
    # Sonraki due
    next_due_date = models.DateField(blank=True, null=True)
    next_due_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    
    # Kalan
    remaining_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    remaining_days = models.IntegerField(blank=True, null=True)
    
    # Durum
    compliance_status = models.CharField(
        max_length=20,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.COMPLIANT
    )
    
    # Tahmini
    estimated_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'maintenance_items'
        ordering = ['next_due_hours', 'next_due_date']
    
    def __str__(self):
        return f"{self.name} ({self.code or '-'})"
    
    def calculate_remaining(self, current_hours: Decimal):
        """Kalan süreyi hesapla"""
        if self.next_due_hours:
            self.remaining_hours = self.next_due_hours - current_hours
        
        if self.next_due_date:
            from datetime import date
            self.remaining_days = (self.next_due_date - date.today()).days
        
        self._update_compliance_status()
        self.save()
    
    def _update_compliance_status(self):
        """Uyumluluk durumunu güncelle"""
        is_overdue = False
        is_due = False
        is_due_soon = False
        
        if self.remaining_hours is not None:
            if self.remaining_hours <= 0:
                is_overdue = True
            elif self.remaining_hours <= Decimal('5'):
                is_due = True
            elif self.remaining_hours <= self.warning_hours:
                is_due_soon = True
        
        if self.remaining_days is not None:
            if self.remaining_days < 0:
                is_overdue = True
            elif self.remaining_days <= 7:
                is_due = True
            elif self.remaining_days <= self.warning_days:
                is_due_soon = True
        
        if is_overdue:
            self.compliance_status = self.ComplianceStatus.OVERDUE
        elif is_due:
            self.compliance_status = self.ComplianceStatus.DUE
        elif is_due_soon:
            self.compliance_status = self.ComplianceStatus.DUE_SOON
        else:
            self.compliance_status = self.ComplianceStatus.COMPLIANT
    
    def record_compliance(
        self,
        done_date: 'date',
        done_hours: Decimal,
        notes: str = None
    ):
        """Bakım yapıldığını kaydet"""
        self.last_done_date = done_date
        self.last_done_hours = done_hours
        self.last_done_notes = notes
        
        # Sonraki due hesapla
        if self.interval_hours:
            self.next_due_hours = done_hours + self.interval_hours
        
        if self.interval_days:
            from datetime import timedelta
            self.next_due_date = done_date + timedelta(days=self.interval_days)
        elif self.interval_months:
            from dateutil.relativedelta import relativedelta
            self.next_due_date = done_date + relativedelta(months=self.interval_months)
        
        self.calculate_remaining(done_hours)


class WorkOrder(TenantModel):
    """İş emri modeli"""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Taslak'
        PLANNED = 'planned', 'Planlandı'
        IN_PROGRESS = 'in_progress', 'Devam Ediyor'
        ON_HOLD = 'on_hold', 'Beklemede'
        COMPLETED = 'completed', 'Tamamlandı'
        CANCELLED = 'cancelled', 'İptal'
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Düşük'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'Yüksek'
        URGENT = 'urgent', 'Acil'
        AOG = 'aog', 'AOG'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aircraft_id = models.UUIDField(db_index=True)
    
    work_order_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    work_order_type = models.CharField(max_length=50)
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL
    )
    
    scheduled_start = models.DateTimeField(blank=True, null=True)
    scheduled_end = models.DateTimeField(blank=True, null=True)
    actual_start = models.DateTimeField(blank=True, null=True)
    actual_end = models.DateTimeField(blank=True, null=True)
    
    assigned_to = models.UUIDField(blank=True, null=True)
    
    estimated_hours = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True
    )
    estimated_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    
    actual_hours = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True
    )
    actual_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    completion_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField()
    completed_at = models.DateTimeField(blank=True, null=True)
    completed_by = models.UUIDField(blank=True, null=True)
    
    class Meta:
        db_table = 'work_orders'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.work_order_number}: {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.work_order_number:
            year = timezone.now().year
            count = WorkOrder.objects.filter(
                organization_id=self.organization_id,
                created_at__year=year
            ).count() + 1
            self.work_order_number = f"WO-{year}-{count:05d}"
        super().save(*args, **kwargs)


class MaintenanceLog(TenantModel):
    """Bakım kaydı modeli"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aircraft_id = models.UUIDField(db_index=True)
    maintenance_item = models.ForeignKey(
        MaintenanceItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    log_number = models.CharField(max_length=50, blank=True, null=True)
    title = models.CharField(max_length=255)
    work_performed = models.TextField()
    
    performed_date = models.DateField()
    aircraft_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    
    performed_by = models.CharField(max_length=255)
    technician_license = models.CharField(max_length=100, blank=True, null=True)
    
    parts_used = models.JSONField(default=list)
    
    labor_hours = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True
    )
    labor_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    parts_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    total_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    
    notes = models.TextField(blank=True, null=True)
    documents = models.JSONField(default=list)
    
    status = models.CharField(max_length=20, default='completed')
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField()
    
    class Meta:
        db_table = 'maintenance_logs'
        ordering = ['-performed_date']
    
    def __str__(self):
        return f"{self.log_number}: {self.title}"
```

---

## 4. API ENDPOINTS

```yaml
# =============================================================================
# MAINTENANCE API
# =============================================================================

# Maintenance Items
GET /api/v1/maintenance/items:
  summary: Bakım öğeleri listesi
  parameters:
    - name: aircraft_id
      required: true
    - name: status
    - name: category

POST /api/v1/maintenance/items:
  summary: Bakım öğesi oluştur

GET /api/v1/maintenance/items/{id}:
  summary: Bakım öğesi detayı

PUT /api/v1/maintenance/items/{id}:
  summary: Bakım öğesi güncelle

DELETE /api/v1/maintenance/items/{id}:
  summary: Bakım öğesi sil

POST /api/v1/maintenance/items/{id}/record-compliance:
  summary: Bakım yapıldığını kaydet
  requestBody:
    content:
      application/json:
        schema:
          type: object
          required:
            - done_date
            - done_hours
          properties:
            done_date:
              type: string
              format: date
            done_hours:
              type: number
            notes:
              type: string

# Work Orders
GET /api/v1/maintenance/work-orders:
  summary: İş emirleri listesi

POST /api/v1/maintenance/work-orders:
  summary: İş emri oluştur

GET /api/v1/maintenance/work-orders/{id}:
  summary: İş emri detayı

PUT /api/v1/maintenance/work-orders/{id}:
  summary: İş emri güncelle

PUT /api/v1/maintenance/work-orders/{id}/start:
  summary: İş emrini başlat

PUT /api/v1/maintenance/work-orders/{id}/complete:
  summary: İş emrini tamamla

PUT /api/v1/maintenance/work-orders/{id}/cancel:
  summary: İş emrini iptal et

# Maintenance Logs
GET /api/v1/maintenance/logs:
  summary: Bakım kayıtları

POST /api/v1/maintenance/logs:
  summary: Bakım kaydı oluştur

GET /api/v1/maintenance/logs/{id}:
  summary: Bakım kaydı detayı

# Aircraft Status
GET /api/v1/maintenance/aircraft/{aircraft_id}/status:
  summary: Uçak bakım durumu

GET /api/v1/maintenance/aircraft/{aircraft_id}/upcoming:
  summary: Yaklaşan bakımlar

GET /api/v1/maintenance/aircraft/{aircraft_id}/history:
  summary: Bakım geçmişi

# Dashboard
GET /api/v1/maintenance/dashboard:
  summary: Bakım dashboard
  responses:
    200:
      content:
        application/json:
          schema:
            type: object
            properties:
              overdue_count:
                type: integer
              due_soon_count:
                type: integer
              open_work_orders:
                type: integer
              aog_aircraft:
                type: array
```

---

## 5. SERVİS KATMANI

```python
# apps/core/services/maintenance_service.py

from typing import List, Dict, Any
from datetime import date, timedelta
from decimal import Decimal

from apps.core.models import MaintenanceItem, WorkOrder, MaintenanceLog
from common.clients import AircraftServiceClient
from common.events import EventBus


class MaintenanceService:
    def __init__(self):
        self.aircraft_client = AircraftServiceClient()
        self.event_bus = EventBus()
    
    async def get_aircraft_maintenance_status(
        self,
        aircraft_id: str
    ) -> Dict[str, Any]:
        """Uçak bakım durumunu getir"""
        
        # Uçak bilgisi
        aircraft = await self.aircraft_client.get_aircraft(aircraft_id)
        current_hours = Decimal(str(aircraft.get('total_time_hours', 0)))
        
        # Bakım öğelerini al ve hesapla
        items = MaintenanceItem.objects.filter(
            aircraft_id=aircraft_id
        )
        
        overdue = []
        due = []
        due_soon = []
        
        async for item in items:
            item.calculate_remaining(current_hours)
            
            if item.compliance_status == 'overdue':
                overdue.append(self._serialize_item(item))
            elif item.compliance_status == 'due':
                due.append(self._serialize_item(item))
            elif item.compliance_status == 'due_soon':
                due_soon.append(self._serialize_item(item))
        
        return {
            'aircraft_id': aircraft_id,
            'current_hours': float(current_hours),
            'overdue': overdue,
            'due': due,
            'due_soon': due_soon,
            'is_maintenance_required': len(overdue) > 0 or len(due) > 0
        }
    
    async def record_maintenance(
        self,
        aircraft_id: str,
        maintenance_item_id: str,
        performed_date: date,
        aircraft_hours: Decimal,
        work_performed: str,
        performed_by: str,
        user_id: str,
        **kwargs
    ) -> MaintenanceLog:
        """Bakım kaydı oluştur"""
        
        item = await MaintenanceItem.objects.aget(id=maintenance_item_id)
        
        # Log oluştur
        log = await MaintenanceLog.objects.acreate(
            organization_id=item.organization_id,
            aircraft_id=aircraft_id,
            maintenance_item=item,
            title=item.name,
            performed_date=performed_date,
            aircraft_hours=aircraft_hours,
            work_performed=work_performed,
            performed_by=performed_by,
            created_by=user_id,
            **kwargs
        )
        
        # Item'ı güncelle
        item.record_compliance(performed_date, aircraft_hours)
        
        # Event
        self.event_bus.publish('maintenance.completed', {
            'log_id': str(log.id),
            'aircraft_id': aircraft_id,
            'maintenance_item_id': maintenance_item_id
        })
        
        return log
    
    async def create_work_order(
        self,
        organization_id: str,
        aircraft_id: str,
        title: str,
        work_order_type: str,
        user_id: str,
        **kwargs
    ) -> WorkOrder:
        """İş emri oluştur"""
        
        work_order = await WorkOrder.objects.acreate(
            organization_id=organization_id,
            aircraft_id=aircraft_id,
            title=title,
            work_order_type=work_order_type,
            created_by=user_id,
            **kwargs
        )
        
        return work_order
    
    async def get_upcoming_maintenance(
        self,
        aircraft_id: str,
        hours_ahead: int = 50,
        days_ahead: int = 90
    ) -> List[Dict[str, Any]]:
        """Yaklaşan bakımları getir"""
        
        aircraft = await self.aircraft_client.get_aircraft(aircraft_id)
        current_hours = Decimal(str(aircraft.get('total_time_hours', 0)))
        
        items = MaintenanceItem.objects.filter(
            aircraft_id=aircraft_id
        ).exclude(
            compliance_status='overdue'
        )
        
        upcoming = []
        
        async for item in items:
            include = False
            
            if item.next_due_hours:
                remaining = item.next_due_hours - current_hours
                if remaining <= hours_ahead:
                    include = True
            
            if item.next_due_date:
                remaining_days = (item.next_due_date - date.today()).days
                if remaining_days <= days_ahead:
                    include = True
            
            if include:
                upcoming.append(self._serialize_item(item))
        
        return sorted(upcoming, key=lambda x: x.get('remaining_hours', 999))
    
    def _serialize_item(self, item: MaintenanceItem) -> Dict[str, Any]:
        return {
            'id': str(item.id),
            'name': item.name,
            'code': item.code,
            'category': item.category,
            'compliance_status': item.compliance_status,
            'next_due_hours': float(item.next_due_hours) if item.next_due_hours else None,
            'next_due_date': item.next_due_date.isoformat() if item.next_due_date else None,
            'remaining_hours': float(item.remaining_hours) if item.remaining_hours else None,
            'remaining_days': item.remaining_days,
            'is_mandatory': item.is_mandatory
        }
```

---

## 6. EVENTS

```python
# Maintenance Service Events

MAINTENANCE_ITEM_CREATED = 'maintenance.item_created'
MAINTENANCE_ITEM_UPDATED = 'maintenance.item_updated'
MAINTENANCE_DUE = 'maintenance.due'
MAINTENANCE_OVERDUE = 'maintenance.overdue'
MAINTENANCE_COMPLETED = 'maintenance.completed'

WORK_ORDER_CREATED = 'maintenance.work_order_created'
WORK_ORDER_STARTED = 'maintenance.work_order_started'
WORK_ORDER_COMPLETED = 'maintenance.work_order_completed'

# Consumed Events
FLIGHT_COMPLETED = 'flight.completed'
# Handler: Bakım öğelerinin kalan süresini güncelle

AIRCRAFT_COUNTERS_UPDATED = 'aircraft.counters_updated'
# Handler: Bakım durumlarını yeniden hesapla
```

---

Bu doküman Maintenance Service'in tüm detaylarını içermektedir.