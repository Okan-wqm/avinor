# ✈️ MODÜL 04: UÇAK SERVİSİ (Aircraft Service)

## 1. GENEL BAKIŞ

### 1.1 Servis Bilgileri

| Özellik | Değer |
|---------|-------|
| Servis Adı | aircraft-service |
| Port | 8003 |
| Veritabanı | aircraft_db |
| Prefix | /api/v1/aircraft |

### 1.2 Sorumluluklar

- Uçak CRUD işlemleri
- Filo yönetimi
- Uçak durumu takibi
- Sayaç yönetimi (airframe, engine, prop)
- Squawk/arıza yönetimi
- Uçuşa elverişlilik kontrolü
- Uçak doküman yönetimi

### 1.3 Bağımlılıklar

**Bağlı Olduğu Servisler:**
- organization-service (lokasyon bilgisi)
- user-service (yetki kontrolü)

**Bağımlı Servisler:**
- booking-service (uçak uygunluğu)
- flight-service (sayaç güncelleme)
- maintenance-service (bakım durumu)

---

## 2. VERİTABANI ŞEMASI

### 2.1 Aircraft Tablosu

```sql
-- =============================================================================
-- AIRCRAFT (Uçaklar)
-- =============================================================================
CREATE TABLE aircraft (
    -- Primary Key
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Tanımlama
    registration            VARCHAR(20) NOT NULL,
    serial_number           VARCHAR(100),
    
    -- Tip Bilgisi
    aircraft_type_id        UUID REFERENCES aircraft_types(id),
    manufacturer            VARCHAR(100),
    model                   VARCHAR(100),
    variant                 VARCHAR(100),
    year_manufactured       INTEGER,
    
    -- Sınıflandırma
    category                VARCHAR(50) NOT NULL DEFAULT 'airplane',
    -- airplane, helicopter, glider, balloon, powered_lift
    
    class                   VARCHAR(50),
    -- single_engine_land, single_engine_sea, multi_engine_land, multi_engine_sea
    
    aircraft_class          VARCHAR(50) DEFAULT 'single_engine',
    -- single_engine, multi_engine, complex, high_performance, tailwheel
    
    -- Özellikler
    is_complex              BOOLEAN DEFAULT false,
    is_high_performance     BOOLEAN DEFAULT false,
    is_tailwheel            BOOLEAN DEFAULT false,
    is_pressurized          BOOLEAN DEFAULT false,
    is_turbine              BOOLEAN DEFAULT false,
    is_jet                  BOOLEAN DEFAULT false,
    is_aerobatic            BOOLEAN DEFAULT false,
    
    -- Motor Bilgileri
    engine_count            INTEGER DEFAULT 1,
    engine_type             VARCHAR(50) DEFAULT 'piston',
    -- piston, turboprop, turbojet, turbofan, electric
    engine_manufacturer     VARCHAR(100),
    engine_model            VARCHAR(100),
    engine_power_hp         INTEGER,
    
    -- Teknik Özellikler
    mtow_kg                 DECIMAL(10,2),
    empty_weight_kg         DECIMAL(10,2),
    useful_load_kg          DECIMAL(10,2),
    max_fuel_kg             DECIMAL(10,2),
    fuel_capacity_liters    DECIMAL(10,2),
    fuel_type               VARCHAR(50) DEFAULT 'avgas_100ll',
    -- avgas_100ll, avgas_100, jet_a, jet_a1, mogas
    oil_capacity_liters     DECIMAL(10,2),
    
    -- Kapasite
    seat_count              INTEGER DEFAULT 4,
    passenger_count         INTEGER DEFAULT 3,
    baggage_capacity_kg     DECIMAL(10,2),
    
    -- Performans
    cruise_speed_kts        INTEGER,
    max_speed_kts           INTEGER,
    never_exceed_kts        INTEGER,
    stall_speed_kts         INTEGER,
    best_climb_kts          INTEGER,
    best_glide_kts          INTEGER,
    range_nm                INTEGER,
    endurance_hours         DECIMAL(4,2),
    service_ceiling_ft      INTEGER,
    rate_of_climb_fpm       INTEGER,
    fuel_consumption_lph    DECIMAL(6,2),
    
    -- Aviyonik
    avionics_type           VARCHAR(100),
    -- steam_gauges, glass_cockpit, g1000, g3x, avidyne, etc.
    gps_type                VARCHAR(100),
    autopilot_type          VARCHAR(100),
    ifr_certified           BOOLEAN DEFAULT false,
    ifr_equipped            BOOLEAN DEFAULT false,
    gps_equipped            BOOLEAN DEFAULT false,
    autopilot_equipped      BOOLEAN DEFAULT false,
    adsb_out                BOOLEAN DEFAULT false,
    adsb_in                 BOOLEAN DEFAULT false,
    
    -- Lokasyon
    home_base_id            UUID,
    current_location_id     UUID,
    current_airport_icao    CHAR(4),
    last_known_position     JSONB,
    -- {"latitude": 41.123, "longitude": 29.456, "updated_at": "..."}
    
    -- Sayaçlar (Güncel Değerler)
    total_time_hours        DECIMAL(10,2) DEFAULT 0,
    total_landings          INTEGER DEFAULT 0,
    total_cycles            INTEGER DEFAULT 0,
    
    -- Hobbs & Tach
    hobbs_time              DECIMAL(10,2) DEFAULT 0,
    tach_time               DECIMAL(10,2) DEFAULT 0,
    hobbs_offset            DECIMAL(10,2) DEFAULT 0,
    
    -- Operasyonel Durum
    status                  VARCHAR(20) DEFAULT 'active',
    -- active, maintenance, grounded, sold, retired, storage
    
    operational_status      VARCHAR(20) DEFAULT 'available',
    -- available, in_use, reserved, unavailable
    
    is_airworthy            BOOLEAN DEFAULT true,
    grounded_reason         TEXT,
    grounded_at             TIMESTAMP,
    grounded_by             UUID,
    
    -- Uçuşa Elverişlilik
    airworthiness_cert_type VARCHAR(50),
    -- standard, restricted, experimental, special
    airworthiness_cert_date DATE,
    arc_expiry_date         DATE,  -- Airworthiness Review Certificate
    
    -- Squawks
    has_open_squawks        BOOLEAN DEFAULT false,
    has_grounding_squawks   BOOLEAN DEFAULT false,
    open_squawk_count       INTEGER DEFAULT 0,
    
    -- Fiyatlandırma
    hourly_rate_dry         DECIMAL(10,2),
    hourly_rate_wet         DECIMAL(10,2),
    block_rate              DECIMAL(10,2),
    daily_rate              DECIMAL(10,2),
    daily_minimum_hours     DECIMAL(5,2),
    
    -- Zaman Hesaplama
    billing_time_source     VARCHAR(20) DEFAULT 'hobbs',
    -- hobbs, tach, block, airborne
    
    -- Sigorta
    insurance_policy_number VARCHAR(100),
    insurance_provider      VARCHAR(255),
    insurance_expiry_date   DATE,
    hull_value              DECIMAL(12,2),
    liability_coverage      DECIMAL(12,2),
    
    -- Tracking
    tracking_device_id      VARCHAR(100),
    tracking_provider       VARCHAR(50),
    -- spidertracks, flightradar24, adsb
    
    -- Dokümanlar (URLs)
    registration_doc_url    VARCHAR(500),
    airworthiness_cert_url  VARCHAR(500),
    insurance_cert_url      VARCHAR(500),
    weight_balance_url      VARCHAR(500),
    poh_url                 VARCHAR(500),
    checklist_url           VARCHAR(500),
    
    -- Görsel
    photo_url               VARCHAR(500),
    thumbnail_url           VARCHAR(500),
    gallery                 JSONB DEFAULT '[]',
    
    -- Notlar
    notes                   TEXT,
    pilot_notes             TEXT,
    internal_notes          TEXT,
    
    -- Metadata
    metadata                JSONB DEFAULT '{}',
    display_order           INTEGER DEFAULT 0,
    
    -- Audit
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID,
    updated_by              UUID,
    deleted_at              TIMESTAMP,
    
    CONSTRAINT unique_org_registration UNIQUE(organization_id, registration)
);

-- Indexes
CREATE INDEX idx_aircraft_org ON aircraft(organization_id);
CREATE INDEX idx_aircraft_registration ON aircraft(registration);
CREATE INDEX idx_aircraft_status ON aircraft(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_aircraft_type ON aircraft(aircraft_type_id);
CREATE INDEX idx_aircraft_home_base ON aircraft(home_base_id);
CREATE INDEX idx_aircraft_current_location ON aircraft(current_location_id);
CREATE INDEX idx_aircraft_airworthy ON aircraft(is_airworthy);
CREATE INDEX idx_aircraft_squawks ON aircraft(has_open_squawks);
```

### 2.2 Aircraft Types (Referans Tablosu)

```sql
-- =============================================================================
-- AIRCRAFT_TYPES (Uçak Tipleri - Referans)
-- =============================================================================
CREATE TABLE aircraft_types (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Tanımlama
    icao_code               VARCHAR(10),
    iata_code               VARCHAR(10),
    manufacturer            VARCHAR(100) NOT NULL,
    model                   VARCHAR(100) NOT NULL,
    variant                 VARCHAR(100),
    
    -- Görüntü Adı
    display_name            VARCHAR(255),
    short_name              VARCHAR(50),
    
    -- Sınıflandırma
    category                VARCHAR(50) NOT NULL,
    class                   VARCHAR(50),
    
    -- Özellikler
    is_complex              BOOLEAN DEFAULT false,
    is_high_performance     BOOLEAN DEFAULT false,
    is_multi_engine         BOOLEAN DEFAULT false,
    requires_type_rating    BOOLEAN DEFAULT false,
    
    -- Varsayılan Değerler
    default_seat_count      INTEGER,
    default_fuel_capacity   DECIMAL(10,2),
    default_fuel_burn       DECIMAL(6,2),
    default_cruise_speed    INTEGER,
    
    -- Görsel
    silhouette_url          VARCHAR(500),
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Örnek Veriler
INSERT INTO aircraft_types (icao_code, manufacturer, model, display_name, short_name, category, class) VALUES
('C172', 'Cessna', '172', 'Cessna 172 Skyhawk', 'C172', 'airplane', 'single_engine_land'),
('C152', 'Cessna', '152', 'Cessna 152', 'C152', 'airplane', 'single_engine_land'),
('PA28', 'Piper', 'PA-28', 'Piper Cherokee', 'PA28', 'airplane', 'single_engine_land'),
('PA44', 'Piper', 'PA-44', 'Piper Seminole', 'PA44', 'airplane', 'multi_engine_land'),
('BE76', 'Beechcraft', '76', 'Beechcraft Duchess', 'BE76', 'airplane', 'multi_engine_land'),
('DA40', 'Diamond', 'DA40', 'Diamond DA40', 'DA40', 'airplane', 'single_engine_land'),
('DA42', 'Diamond', 'DA42', 'Diamond DA42 Twin Star', 'DA42', 'airplane', 'multi_engine_land'),
('SR22', 'Cirrus', 'SR22', 'Cirrus SR22', 'SR22', 'airplane', 'single_engine_land'),
('R22', 'Robinson', 'R22', 'Robinson R22', 'R22', 'helicopter', 'helicopter'),
('R44', 'Robinson', 'R44', 'Robinson R44', 'R44', 'helicopter', 'helicopter');
```

### 2.3 Aircraft Engines

```sql
-- =============================================================================
-- AIRCRAFT_ENGINES (Motor Detayları)
-- =============================================================================
CREATE TABLE aircraft_engines (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aircraft_id             UUID NOT NULL REFERENCES aircraft(id) ON DELETE CASCADE,
    
    -- Pozisyon
    position                INTEGER NOT NULL DEFAULT 1,
    position_name           VARCHAR(50),  -- Left, Right, Center
    
    -- Motor Bilgileri
    manufacturer            VARCHAR(100),
    model                   VARCHAR(100),
    serial_number           VARCHAR(100),
    
    -- Özellikler
    power_hp                INTEGER,
    displacement            VARCHAR(50),
    cylinders               INTEGER,
    
    -- Sayaçlar
    total_time_hours        DECIMAL(10,2) DEFAULT 0,
    tsmoh                   DECIMAL(10,2) DEFAULT 0,  -- Time Since Major Overhaul
    tsoh                    DECIMAL(10,2) DEFAULT 0,  -- Time Since Overhaul
    tso                     DECIMAL(10,2) DEFAULT 0,  -- Time Since New/Overhaul
    
    -- TBO
    tbo_hours               INTEGER,  -- Time Between Overhaul
    tbo_years               INTEGER,
    
    -- Son Bakım
    last_overhaul_date      DATE,
    last_overhaul_hours     DECIMAL(10,2),
    last_overhaul_shop      VARCHAR(255),
    
    -- Kurulum
    install_date            DATE,
    install_hours           DECIMAL(10,2),
    
    -- Notlar
    notes                   TEXT,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_aircraft_engine_position UNIQUE(aircraft_id, position)
);
```

### 2.4 Aircraft Propellers

```sql
-- =============================================================================
-- AIRCRAFT_PROPELLERS (Pervane Detayları)
-- =============================================================================
CREATE TABLE aircraft_propellers (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aircraft_id             UUID NOT NULL REFERENCES aircraft(id) ON DELETE CASCADE,
    engine_id               UUID REFERENCES aircraft_engines(id),
    
    -- Pozisyon
    position                INTEGER NOT NULL DEFAULT 1,
    
    -- Pervane Bilgileri
    manufacturer            VARCHAR(100),
    model                   VARCHAR(100),
    serial_number           VARCHAR(100),
    
    -- Tip
    propeller_type          VARCHAR(50),  -- fixed, constant_speed, feathering
    blade_count             INTEGER DEFAULT 2,
    
    -- Sayaçlar
    total_time_hours        DECIMAL(10,2) DEFAULT 0,
    tsmoh                   DECIMAL(10,2) DEFAULT 0,
    
    -- TBO
    tbo_hours               INTEGER,
    tbo_years               INTEGER,
    
    -- Son Bakım
    last_overhaul_date      DATE,
    last_overhaul_hours     DECIMAL(10,2),
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_aircraft_prop_position UNIQUE(aircraft_id, position)
);
```

### 2.5 Aircraft Squawks

```sql
-- =============================================================================
-- AIRCRAFT_SQUAWKS (Arıza Bildirimleri)
-- =============================================================================
CREATE TABLE aircraft_squawks (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    aircraft_id             UUID NOT NULL REFERENCES aircraft(id) ON DELETE CASCADE,
    
    -- Raporlayan
    reported_by             UUID NOT NULL,
    reported_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- İlgili Uçuş
    flight_id               UUID,
    
    -- Arıza Detayları
    squawk_number           VARCHAR(20),  -- SQ-2024-001
    title                   VARCHAR(255) NOT NULL,
    description             TEXT NOT NULL,
    
    -- Kategorilendirme
    category                VARCHAR(50) NOT NULL,
    -- engine, airframe, avionics, instruments, electrical, 
    -- landing_gear, flight_controls, fuel, hydraulic, other
    
    ata_chapter             VARCHAR(10),  -- ATA 100 chapter
    
    -- Sistem Bileşeni
    system                  VARCHAR(100),
    component               VARCHAR(100),
    
    -- Önem Seviyesi
    severity                VARCHAR(20) NOT NULL DEFAULT 'minor',
    -- minor, major, grounding, aog
    
    priority                VARCHAR(20) DEFAULT 'normal',
    -- low, normal, high, urgent
    
    -- Uçuşa Etkisi
    is_grounding            BOOLEAN DEFAULT false,
    is_mel_item             BOOLEAN DEFAULT false,
    mel_category            CHAR(1),  -- A, B, C, D
    mel_reference           VARCHAR(100),
    
    -- CDL/NEF
    is_cdl_item             BOOLEAN DEFAULT false,
    cdl_reference           VARCHAR(100),
    
    -- Erteleme (Deferral)
    is_deferred             BOOLEAN DEFAULT false,
    deferred_until          DATE,
    deferred_until_hours    DECIMAL(10,2),
    deferred_until_cycles   INTEGER,
    deferral_reason         TEXT,
    deferral_approved_by    UUID,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'open',
    -- open, in_progress, deferred, resolved, closed, cancelled
    
    -- Çözüm
    resolution              TEXT,
    resolved_by             UUID,
    resolved_at             TIMESTAMP,
    
    -- İş Emri
    work_order_id           UUID,
    work_order_number       VARCHAR(50),
    
    -- Maliyet
    estimated_hours         DECIMAL(6,2),
    estimated_cost          DECIMAL(10,2),
    actual_hours            DECIMAL(6,2),
    actual_cost             DECIMAL(10,2),
    
    -- Ekler
    photos                  JSONB DEFAULT '[]',
    documents               JSONB DEFAULT '[]',
    
    -- Uçuş Saati (Bildirim Anında)
    aircraft_hours_at       DECIMAL(10,2),
    aircraft_cycles_at      INTEGER,
    
    -- Metadata
    metadata                JSONB DEFAULT '{}',
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_squawks_org ON aircraft_squawks(organization_id);
CREATE INDEX idx_squawks_aircraft ON aircraft_squawks(aircraft_id);
CREATE INDEX idx_squawks_status ON aircraft_squawks(status);
CREATE INDEX idx_squawks_grounding ON aircraft_squawks(is_grounding) WHERE is_grounding = true;
CREATE INDEX idx_squawks_open ON aircraft_squawks(aircraft_id, status) WHERE status = 'open';
```

### 2.6 Aircraft Documents

```sql
-- =============================================================================
-- AIRCRAFT_DOCUMENTS (Uçak Dokümanları)
-- =============================================================================
CREATE TABLE aircraft_documents (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    aircraft_id             UUID NOT NULL REFERENCES aircraft(id) ON DELETE CASCADE,
    
    -- Doküman Bilgileri
    document_type           VARCHAR(50) NOT NULL,
    -- registration, airworthiness, insurance, weight_balance, poh,
    -- checklist, maintenance_manual, parts_catalog, ad_compliance, sb_compliance
    
    title                   VARCHAR(255) NOT NULL,
    description             TEXT,
    
    -- Dosya
    file_url                VARCHAR(500) NOT NULL,
    file_name               VARCHAR(255),
    file_size_bytes         BIGINT,
    file_type               VARCHAR(50),  -- pdf, jpg, png
    
    -- Versiyon
    version                 VARCHAR(50),
    effective_date          DATE,
    expiry_date             DATE,
    
    -- Doküman Numarası
    document_number         VARCHAR(100),
    
    -- Durum
    is_current              BOOLEAN DEFAULT true,
    is_required             BOOLEAN DEFAULT false,
    
    -- Hatırlatma
    reminder_days           INTEGER,  -- Son kullanma tarihinden kaç gün önce
    
    -- Erişim
    is_public               BOOLEAN DEFAULT false,  -- Pilotlar görebilir mi
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_aircraft_docs_aircraft ON aircraft_documents(aircraft_id);
CREATE INDEX idx_aircraft_docs_type ON aircraft_documents(document_type);
CREATE INDEX idx_aircraft_docs_expiry ON aircraft_documents(expiry_date) WHERE expiry_date IS NOT NULL;
```

### 2.7 Aircraft Time Logs

```sql
-- =============================================================================
-- AIRCRAFT_TIME_LOGS (Sayaç Geçmişi)
-- =============================================================================
CREATE TABLE aircraft_time_logs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aircraft_id             UUID NOT NULL REFERENCES aircraft(id) ON DELETE CASCADE,
    
    -- İlgili Kaynak
    source_type             VARCHAR(50) NOT NULL,
    -- flight, maintenance, adjustment, import
    source_id               UUID,
    
    -- Zaman Değişimi
    log_date                DATE NOT NULL,
    
    -- Değerler (Önceki ve Sonraki)
    hobbs_before            DECIMAL(10,2),
    hobbs_after             DECIMAL(10,2),
    hobbs_change            DECIMAL(10,2),
    
    tach_before             DECIMAL(10,2),
    tach_after              DECIMAL(10,2),
    tach_change             DECIMAL(10,2),
    
    total_time_before       DECIMAL(10,2),
    total_time_after        DECIMAL(10,2),
    total_time_change       DECIMAL(10,2),
    
    landings_before         INTEGER,
    landings_after          INTEGER,
    landings_change         INTEGER,
    
    cycles_before           INTEGER,
    cycles_after            INTEGER,
    cycles_change           INTEGER,
    
    -- Motor Saatleri (JSONB - her motor için)
    engine_times            JSONB DEFAULT '{}',
    -- {"1": {"before": 1234.5, "after": 1235.7, "change": 1.2}}
    
    -- Notlar
    notes                   TEXT,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID
);

CREATE INDEX idx_time_logs_aircraft ON aircraft_time_logs(aircraft_id);
CREATE INDEX idx_time_logs_date ON aircraft_time_logs(log_date DESC);
CREATE INDEX idx_time_logs_source ON aircraft_time_logs(source_type, source_id);
```

---

## 3. DJANGO MODELS

### 3.1 Aircraft Model

```python
# apps/core/models/aircraft.py

import uuid
from django.db import models
from django.utils import timezone
from common.models import TenantModel, SoftDeleteModel


class Aircraft(TenantModel, SoftDeleteModel):
    """Uçak modeli"""
    
    class Category(models.TextChoices):
        AIRPLANE = 'airplane', 'Uçak'
        HELICOPTER = 'helicopter', 'Helikopter'
        GLIDER = 'glider', 'Planör'
        BALLOON = 'balloon', 'Balon'
        POWERED_LIFT = 'powered_lift', 'Powered Lift'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Aktif'
        MAINTENANCE = 'maintenance', 'Bakımda'
        GROUNDED = 'grounded', 'Ground Edildi'
        SOLD = 'sold', 'Satıldı'
        RETIRED = 'retired', 'Emekli'
        STORAGE = 'storage', 'Depoda'
    
    class OperationalStatus(models.TextChoices):
        AVAILABLE = 'available', 'Müsait'
        IN_USE = 'in_use', 'Kullanımda'
        RESERVED = 'reserved', 'Rezerve'
        UNAVAILABLE = 'unavailable', 'Müsait Değil'
    
    class BillingTimeSource(models.TextChoices):
        HOBBS = 'hobbs', 'Hobbs'
        TACH = 'tach', 'Tach'
        BLOCK = 'block', 'Block Time'
        AIRBORNE = 'airborne', 'Airborne Time'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Tanımlama
    registration = models.CharField(max_length=20)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Tip
    aircraft_type = models.ForeignKey(
        'AircraftType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    manufacturer = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    variant = models.CharField(max_length=100, blank=True, null=True)
    year_manufactured = models.IntegerField(blank=True, null=True)
    
    # Sınıflandırma
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.AIRPLANE
    )
    aircraft_class = models.CharField(max_length=50, blank=True, null=True)
    
    # Özellikler
    is_complex = models.BooleanField(default=False)
    is_high_performance = models.BooleanField(default=False)
    is_tailwheel = models.BooleanField(default=False)
    is_pressurized = models.BooleanField(default=False)
    is_ifr_certified = models.BooleanField(default=False)
    
    # Motor
    engine_count = models.IntegerField(default=1)
    engine_type = models.CharField(max_length=50, default='piston')
    
    # Kapasite
    seat_count = models.IntegerField(default=4)
    fuel_capacity_liters = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    
    # Performans
    cruise_speed_kts = models.IntegerField(blank=True, null=True)
    fuel_consumption_lph = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True
    )
    
    # Lokasyon
    home_base_id = models.UUIDField(blank=True, null=True)
    current_location_id = models.UUIDField(blank=True, null=True)
    current_airport_icao = models.CharField(max_length=4, blank=True, null=True)
    
    # Sayaçlar
    total_time_hours = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    total_landings = models.IntegerField(default=0)
    total_cycles = models.IntegerField(default=0)
    hobbs_time = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tach_time = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Durum
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    operational_status = models.CharField(
        max_length=20,
        choices=OperationalStatus.choices,
        default=OperationalStatus.AVAILABLE
    )
    is_airworthy = models.BooleanField(default=True)
    grounded_reason = models.TextField(blank=True, null=True)
    grounded_at = models.DateTimeField(blank=True, null=True)
    grounded_by = models.UUIDField(blank=True, null=True)
    
    # Sertifikalar
    arc_expiry_date = models.DateField(blank=True, null=True)
    insurance_expiry_date = models.DateField(blank=True, null=True)
    
    # Squawks
    has_open_squawks = models.BooleanField(default=False)
    has_grounding_squawks = models.BooleanField(default=False)
    open_squawk_count = models.IntegerField(default=0)
    
    # Fiyatlandırma
    hourly_rate_dry = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    hourly_rate_wet = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    billing_time_source = models.CharField(
        max_length=20,
        choices=BillingTimeSource.choices,
        default=BillingTimeSource.HOBBS
    )
    
    # Görseller
    photo_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Notlar
    notes = models.TextField(blank=True, null=True)
    pilot_notes = models.TextField(blank=True, null=True)
    
    # Metadata
    metadata = models.JSONField(default=dict)
    display_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'aircraft'
        ordering = ['display_order', 'registration']
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'registration'],
                name='unique_org_registration'
            )
        ]
    
    def __str__(self):
        return f"{self.registration} ({self.model or 'Unknown'})"
    
    @property
    def display_name(self):
        if self.model:
            return f"{self.registration} - {self.model}"
        return self.registration
    
    @property
    def is_available(self):
        return (
            self.status == self.Status.ACTIVE and
            self.operational_status == self.OperationalStatus.AVAILABLE and
            self.is_airworthy and
            not self.has_grounding_squawks
        )
    
    def ground(self, reason: str, grounded_by: uuid.UUID):
        """Uçağı ground et"""
        self.is_airworthy = False
        self.grounded_reason = reason
        self.grounded_at = timezone.now()
        self.grounded_by = grounded_by
        self.status = self.Status.GROUNDED
        self.save()
    
    def unground(self):
        """Ground'u kaldır"""
        self.is_airworthy = True
        self.grounded_reason = None
        self.grounded_at = None
        self.grounded_by = None
        self.status = self.Status.ACTIVE
        self.save()
    
    def update_counters(self, flight_hours: float, landings: int = 0, cycles: int = 0):
        """Sayaçları güncelle"""
        self.total_time_hours += flight_hours
        self.hobbs_time += flight_hours
        self.total_landings += landings
        self.total_cycles += cycles
        self.save()
    
    def update_squawk_status(self):
        """Squawk durumunu güncelle"""
        from apps.core.models import AircraftSquawk
        
        open_squawks = AircraftSquawk.objects.filter(
            aircraft=self,
            status__in=['open', 'in_progress', 'deferred']
        )
        
        self.open_squawk_count = open_squawks.count()
        self.has_open_squawks = self.open_squawk_count > 0
        self.has_grounding_squawks = open_squawks.filter(is_grounding=True).exists()
        
        # Grounding squawk varsa otomatik ground et
        if self.has_grounding_squawks and self.is_airworthy:
            self.is_airworthy = False
            self.status = self.Status.GROUNDED
        
        self.save()


class AircraftSquawk(TenantModel):
    """Arıza bildirimi modeli"""
    
    class Severity(models.TextChoices):
        MINOR = 'minor', 'Küçük'
        MAJOR = 'major', 'Önemli'
        GROUNDING = 'grounding', 'Ground Edici'
        AOG = 'aog', 'Aircraft on Ground'
    
    class Status(models.TextChoices):
        OPEN = 'open', 'Açık'
        IN_PROGRESS = 'in_progress', 'İşlemde'
        DEFERRED = 'deferred', 'Ertelendi'
        RESOLVED = 'resolved', 'Çözüldü'
        CLOSED = 'closed', 'Kapatıldı'
        CANCELLED = 'cancelled', 'İptal'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aircraft = models.ForeignKey(
        Aircraft,
        on_delete=models.CASCADE,
        related_name='squawks'
    )
    
    # Raporlayan
    reported_by = models.UUIDField()
    reported_at = models.DateTimeField(default=timezone.now)
    flight_id = models.UUIDField(blank=True, null=True)
    
    # Detaylar
    squawk_number = models.CharField(max_length=20, blank=True, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50)
    
    # Önem
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MINOR
    )
    is_grounding = models.BooleanField(default=False)
    is_mel_item = models.BooleanField(default=False)
    
    # Durum
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )
    
    # Çözüm
    resolution = models.TextField(blank=True, null=True)
    resolved_by = models.UUIDField(blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    
    # Ekler
    photos = models.JSONField(default=list)
    
    # Uçuş saati
    aircraft_hours_at = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'aircraft_squawks'
        ordering = ['-reported_at']
    
    def __str__(self):
        return f"{self.squawk_number or 'SQ'}: {self.title}"
    
    def save(self, *args, **kwargs):
        # Squawk numarası oluştur
        if not self.squawk_number:
            year = timezone.now().year
            count = AircraftSquawk.objects.filter(
                organization_id=self.organization_id,
                created_at__year=year
            ).count() + 1
            self.squawk_number = f"SQ-{year}-{count:04d}"
        
        # Grounding kontrolü
        if self.severity in [self.Severity.GROUNDING, self.Severity.AOG]:
            self.is_grounding = True
        
        super().save(*args, **kwargs)
        
        # Aircraft squawk durumunu güncelle
        self.aircraft.update_squawk_status()
    
    def resolve(self, resolution: str, resolved_by: uuid.UUID):
        """Squawk'ı çöz"""
        self.status = self.Status.RESOLVED
        self.resolution = resolution
        self.resolved_by = resolved_by
        self.resolved_at = timezone.now()
        self.save()
    
    def close(self):
        """Squawk'ı kapat"""
        self.status = self.Status.CLOSED
        self.save()
```

---

## 4. API ENDPOINTS

```yaml
# =============================================================================
# AIRCRAFT API
# =============================================================================

# Aircraft CRUD
GET /api/v1/aircraft:
  summary: Uçak listesi
  parameters:
    - name: status
      in: query
      schema:
        type: string
        enum: [active, maintenance, grounded]
    - name: location_id
      in: query
      schema:
        type: string
    - name: category
      in: query
      schema:
        type: string
    - name: available_only
      in: query
      schema:
        type: boolean

POST /api/v1/aircraft:
  summary: Uçak ekle

GET /api/v1/aircraft/{id}:
  summary: Uçak detayı

PUT /api/v1/aircraft/{id}:
  summary: Uçak güncelle

DELETE /api/v1/aircraft/{id}:
  summary: Uçak sil

# Status
GET /api/v1/aircraft/{id}/status:
  summary: Uçak durumu
  responses:
    200:
      content:
        application/json:
          schema:
            type: object
            properties:
              status:
                type: string
              is_airworthy:
                type: boolean
              is_available:
                type: boolean
              warnings:
                type: array
              squawks:
                type: array

PUT /api/v1/aircraft/{id}/ground:
  summary: Uçağı ground et
  requestBody:
    content:
      application/json:
        schema:
          type: object
          required:
            - reason
          properties:
            reason:
              type: string

PUT /api/v1/aircraft/{id}/unground:
  summary: Ground'u kaldır

# Counters
GET /api/v1/aircraft/{id}/counters:
  summary: Sayaçları getir

PUT /api/v1/aircraft/{id}/counters:
  summary: Sayaçları güncelle
  requestBody:
    content:
      application/json:
        schema:
          type: object
          properties:
            hobbs_time:
              type: number
            tach_time:
              type: number
            total_time_hours:
              type: number

POST /api/v1/aircraft/{id}/counters/adjustment:
  summary: Sayaç düzeltmesi
  requestBody:
    content:
      application/json:
        schema:
          type: object
          required:
            - field
            - new_value
            - reason
          properties:
            field:
              type: string
            new_value:
              type: number
            reason:
              type: string

# Availability
GET /api/v1/aircraft/{id}/availability:
  summary: Uygunluk kontrolü
  parameters:
    - name: start
      in: query
      required: true
      schema:
        type: string
        format: date-time
    - name: end
      in: query
      required: true
      schema:
        type: string
        format: date-time

# Squawks
GET /api/v1/aircraft/{id}/squawks:
  summary: Arıza listesi
  parameters:
    - name: status
      in: query
      schema:
        type: string

POST /api/v1/aircraft/{id}/squawks:
  summary: Arıza bildir

GET /api/v1/aircraft/{id}/squawks/{squawk_id}:
  summary: Arıza detayı

PUT /api/v1/aircraft/{id}/squawks/{squawk_id}:
  summary: Arıza güncelle

POST /api/v1/aircraft/{id}/squawks/{squawk_id}/resolve:
  summary: Arızayı çöz

POST /api/v1/aircraft/{id}/squawks/{squawk_id}/defer:
  summary: Arızayı ertele

# Documents
GET /api/v1/aircraft/{id}/documents:
  summary: Doküman listesi

POST /api/v1/aircraft/{id}/documents:
  summary: Doküman yükle

DELETE /api/v1/aircraft/{id}/documents/{doc_id}:
  summary: Doküman sil

# History
GET /api/v1/aircraft/{id}/time-logs:
  summary: Sayaç geçmişi

GET /api/v1/aircraft/{id}/flight-history:
  summary: Uçuş geçmişi

# Engines
GET /api/v1/aircraft/{id}/engines:
  summary: Motor listesi

PUT /api/v1/aircraft/{id}/engines/{engine_id}:
  summary: Motor güncelle
```

---

## 5. SERVİS KATMANI

```python
# apps/core/services/aircraft_service.py

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from apps.core.models import Aircraft, AircraftSquawk, AircraftTimeLog
from apps.core.repositories import AircraftRepository
from common.exceptions import ValidationError, NotFoundError, ConflictError
from common.events import EventBus, EventTypes
from common.clients import BookingServiceClient, MaintenanceServiceClient


class AircraftService:
    def __init__(self):
        self.repo = AircraftRepository()
        self.event_bus = EventBus()
        self.booking_client = BookingServiceClient()
        self.maintenance_client = MaintenanceServiceClient()
    
    async def create_aircraft(
        self,
        organization_id: str,
        registration: str,
        **kwargs
    ) -> Aircraft:
        """Uçak oluştur"""
        
        # Registration kontrolü
        existing = await self.repo.find_by_registration(
            organization_id, registration
        )
        if existing:
            raise ConflictError(f'{registration} tescili zaten kayıtlı')
        
        # Registration format kontrolü
        self._validate_registration(registration)
        
        aircraft = await self.repo.create(
            organization_id=organization_id,
            registration=registration.upper(),
            **kwargs
        )
        
        self.event_bus.publish(EventTypes.AIRCRAFT_CREATED, {
            'aircraft_id': str(aircraft.id),
            'organization_id': organization_id,
            'registration': registration
        })
        
        return aircraft
    
    async def get_aircraft_status(self, aircraft_id: str) -> Dict[str, Any]:
        """Uçak durumunu getir"""
        
        aircraft = await self.repo.get_by_id(aircraft_id)
        if not aircraft:
            raise NotFoundError('Uçak bulunamadı')
        
        warnings = []
        blockers = []
        
        # Squawk kontrolü
        if aircraft.has_grounding_squawks:
            blockers.append({
                'type': 'squawk',
                'message': 'Grounding squawk mevcut'
            })
        elif aircraft.has_open_squawks:
            warnings.append({
                'type': 'squawk',
                'message': f'{aircraft.open_squawk_count} açık arıza bildirimi'
            })
        
        # ARC kontrolü
        if aircraft.arc_expiry_date:
            days_to_expiry = (aircraft.arc_expiry_date - date.today()).days
            if days_to_expiry < 0:
                blockers.append({
                    'type': 'arc',
                    'message': 'ARC süresi dolmuş'
                })
            elif days_to_expiry <= 30:
                warnings.append({
                    'type': 'arc',
                    'message': f'ARC {days_to_expiry} gün içinde dolacak'
                })
        
        # Sigorta kontrolü
        if aircraft.insurance_expiry_date:
            days_to_expiry = (aircraft.insurance_expiry_date - date.today()).days
            if days_to_expiry < 0:
                blockers.append({
                    'type': 'insurance',
                    'message': 'Sigorta süresi dolmuş'
                })
            elif days_to_expiry <= 30:
                warnings.append({
                    'type': 'insurance',
                    'message': f'Sigorta {days_to_expiry} gün içinde dolacak'
                })
        
        # Bakım kontrolü
        maintenance_status = await self.maintenance_client.get_aircraft_status(aircraft_id)
        if maintenance_status:
            for item in maintenance_status.get('upcoming', []):
                if item.get('is_overdue'):
                    blockers.append({
                        'type': 'maintenance',
                        'message': f"{item['name']} bakımı gecikmiş"
                    })
                elif item.get('remaining_hours', 100) < 10:
                    warnings.append({
                        'type': 'maintenance',
                        'message': f"{item['name']}: {item['remaining_hours']:.1f} saat kaldı"
                    })
        
        # Mevcut rezervasyon
        current_booking = await self.booking_client.get_current_booking(aircraft_id)
        
        return {
            'aircraft_id': str(aircraft.id),
            'registration': aircraft.registration,
            'status': aircraft.status,
            'operational_status': aircraft.operational_status,
            'is_airworthy': aircraft.is_airworthy,
            'is_available': len(blockers) == 0 and aircraft.is_airworthy,
            'current_booking': current_booking,
            'warnings': warnings,
            'blockers': blockers,
            'counters': {
                'total_time': float(aircraft.total_time_hours),
                'hobbs': float(aircraft.hobbs_time),
                'tach': float(aircraft.tach_time),
                'landings': aircraft.total_landings,
                'cycles': aircraft.total_cycles
            }
        }
    
    async def check_availability(
        self,
        aircraft_id: str,
        start: datetime,
        end: datetime
    ) -> Dict[str, Any]:
        """Uygunluk kontrolü"""
        
        status = await self.get_aircraft_status(aircraft_id)
        
        if not status['is_available']:
            return {
                'available': False,
                'reason': 'aircraft_not_available',
                'blockers': status['blockers']
            }
        
        # Çakışan rezervasyon kontrolü
        conflicting = await self.booking_client.check_conflicts(
            aircraft_id, start.isoformat(), end.isoformat()
        )
        
        if conflicting:
            return {
                'available': False,
                'reason': 'booking_conflict',
                'conflicts': conflicting
            }
        
        # Bakım planı kontrolü
        maintenance = await self.maintenance_client.check_scheduled(
            aircraft_id, start.isoformat(), end.isoformat()
        )
        
        if maintenance:
            return {
                'available': False,
                'reason': 'scheduled_maintenance',
                'maintenance': maintenance
            }
        
        return {
            'available': True,
            'warnings': status['warnings']
        }
    
    @transaction.atomic
    async def update_counters(
        self,
        aircraft_id: str,
        hobbs_change: Decimal = None,
        tach_change: Decimal = None,
        landings: int = 0,
        cycles: int = 0,
        source_type: str = 'flight',
        source_id: str = None,
        user_id: str = None
    ):
        """Sayaçları güncelle"""
        
        aircraft = await self.repo.get_by_id(aircraft_id)
        if not aircraft:
            raise NotFoundError('Uçak bulunamadı')
        
        # Önceki değerler
        hobbs_before = aircraft.hobbs_time
        tach_before = aircraft.tach_time
        total_before = aircraft.total_time_hours
        landings_before = aircraft.total_landings
        cycles_before = aircraft.total_cycles
        
        # Güncelle
        if hobbs_change:
            aircraft.hobbs_time += hobbs_change
            aircraft.total_time_hours += hobbs_change
        
        if tach_change:
            aircraft.tach_time += tach_change
        
        aircraft.total_landings += landings
        aircraft.total_cycles += cycles
        
        await self.repo.update(aircraft_id, {
            'hobbs_time': aircraft.hobbs_time,
            'tach_time': aircraft.tach_time,
            'total_time_hours': aircraft.total_time_hours,
            'total_landings': aircraft.total_landings,
            'total_cycles': aircraft.total_cycles
        })
        
        # Log kaydet
        await AircraftTimeLog.objects.acreate(
            aircraft_id=aircraft_id,
            source_type=source_type,
            source_id=source_id,
            log_date=date.today(),
            hobbs_before=hobbs_before,
            hobbs_after=aircraft.hobbs_time,
            hobbs_change=hobbs_change or 0,
            tach_before=tach_before,
            tach_after=aircraft.tach_time,
            tach_change=tach_change or 0,
            total_time_before=total_before,
            total_time_after=aircraft.total_time_hours,
            total_time_change=hobbs_change or 0,
            landings_before=landings_before,
            landings_after=aircraft.total_landings,
            landings_change=landings,
            created_by=user_id
        )
    
    async def ground_aircraft(
        self,
        aircraft_id: str,
        reason: str,
        grounded_by: str
    ):
        """Uçağı ground et"""
        
        aircraft = await self.repo.get_by_id(aircraft_id)
        if not aircraft:
            raise NotFoundError('Uçak bulunamadı')
        
        # Aktif rezervasyonları iptal et
        await self.booking_client.cancel_future_bookings(
            aircraft_id,
            reason=f'Uçak ground edildi: {reason}'
        )
        
        # Ground
        aircraft.ground(reason, grounded_by)
        
        self.event_bus.publish(EventTypes.AIRCRAFT_GROUNDED, {
            'aircraft_id': aircraft_id,
            'reason': reason,
            'grounded_by': grounded_by
        })
    
    async def create_squawk(
        self,
        aircraft_id: str,
        reported_by: str,
        title: str,
        description: str,
        category: str,
        severity: str,
        flight_id: str = None,
        photos: List[str] = None
    ) -> AircraftSquawk:
        """Arıza bildir"""
        
        aircraft = await self.repo.get_by_id(aircraft_id)
        if not aircraft:
            raise NotFoundError('Uçak bulunamadı')
        
        squawk = await AircraftSquawk.objects.acreate(
            organization_id=aircraft.organization_id,
            aircraft=aircraft,
            reported_by=reported_by,
            flight_id=flight_id,
            title=title,
            description=description,
            category=category,
            severity=severity,
            aircraft_hours_at=aircraft.total_time_hours,
            photos=photos or []
        )
        
        self.event_bus.publish('aircraft.squawk_created', {
            'squawk_id': str(squawk.id),
            'aircraft_id': aircraft_id,
            'severity': severity,
            'is_grounding': squawk.is_grounding
        })
        
        return squawk
    
    def _validate_registration(self, registration: str):
        """Registration format validasyonu"""
        import re
        
        # Türkiye: TC-XXX
        # USA: N12345
        # Europe: D-EXXX, G-XXXX, etc.
        
        patterns = [
            r'^TC-[A-Z]{3}$',  # Turkey
            r'^N\d{1,5}[A-Z]{0,2}$',  # USA
            r'^[A-Z]-[A-Z]{4}$',  # Europe single letter
            r'^[A-Z]{2}-[A-Z]{3}$',  # Europe double letter
        ]
        
        for pattern in patterns:
            if re.match(pattern, registration.upper()):
                return True
        
        raise ValidationError('Geçersiz tescil formatı')
```

---

## 6. EVENTS

```python
# Aircraft Service Events

AIRCRAFT_CREATED = 'aircraft.created'
AIRCRAFT_UPDATED = 'aircraft.updated'
AIRCRAFT_DELETED = 'aircraft.deleted'

AIRCRAFT_STATUS_CHANGED = 'aircraft.status_changed'
AIRCRAFT_GROUNDED = 'aircraft.grounded'
AIRCRAFT_UNGROUNDED = 'aircraft.ungrounded'

AIRCRAFT_COUNTERS_UPDATED = 'aircraft.counters_updated'
AIRCRAFT_LOCATION_CHANGED = 'aircraft.location_changed'

SQUAWK_CREATED = 'aircraft.squawk_created'
SQUAWK_RESOLVED = 'aircraft.squawk_resolved'
SQUAWK_DEFERRED = 'aircraft.squawk_deferred'

# Consumed Events
FLIGHT_COMPLETED = 'flight.completed'
# Handler: Sayaçları güncelle

MAINTENANCE_COMPLETED = 'maintenance.completed'
# Handler: İlgili squawk'ları kapat
```

---

Bu doküman Aircraft Service'in tüm detaylarını içermektedir.