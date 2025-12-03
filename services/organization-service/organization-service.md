# 🏢 MODÜL 03: ORGANİZASYON SERVİSİ (Organization Service)

## 1. GENEL BAKIŞ

### 1.1 Servis Bilgileri

| Özellik | Değer |
|---------|-------|
| Servis Adı | organization-service |
| Port | 8002 |
| Veritabanı | org_db |
| Prefix | /api/v1/organizations, /api/v1/locations |

### 1.2 Sorumluluklar

- Organizasyon (uçuş okulu) yönetimi
- Lokasyon/Üs yönetimi
- Multi-tenant yapı yönetimi
- Organizasyon ayarları
- Abonelik ve lisans yönetimi
- White-label yapılandırması

### 1.3 Bağımlılıklar

**Bağlı Olduğu Servisler:**
- user-service (admin kullanıcı bilgisi)

**Bağımlı Servisler:**
- Tüm diğer servisler (organization_id için)

---

## 2. VERİTABANI ŞEMASI

### 2.1 Organizations Tablosu

```sql
-- =============================================================================
-- ORGANIZATIONS (Uçuş Okulları / Organizasyonlar)
-- =============================================================================
CREATE TABLE organizations (
    -- Primary Key
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Temel Bilgiler
    name                    VARCHAR(255) NOT NULL,
    legal_name              VARCHAR(255),
    slug                    VARCHAR(100) UNIQUE NOT NULL,
    
    -- Tip
    organization_type       VARCHAR(50) DEFAULT 'flight_school',
    -- flight_school, flying_club, university, simulator_center, airline_training
    
    -- İletişim
    email                   VARCHAR(255) NOT NULL,
    phone                   VARCHAR(50),
    fax                     VARCHAR(50),
    website                 VARCHAR(255),
    
    -- Adres
    address_line1           VARCHAR(255),
    address_line2           VARCHAR(255),
    city                    VARCHAR(100),
    state_province          VARCHAR(100),
    postal_code             VARCHAR(20),
    country_code            CHAR(2) NOT NULL,
    
    -- Koordinatlar
    latitude                DECIMAL(10, 8),
    longitude               DECIMAL(11, 8),
    
    -- Branding
    logo_url                VARCHAR(500),
    logo_dark_url           VARCHAR(500),
    favicon_url             VARCHAR(500),
    primary_color           CHAR(7) DEFAULT '#3B82F6',
    secondary_color         CHAR(7) DEFAULT '#1E40AF',
    accent_color            CHAR(7) DEFAULT '#10B981',
    
    -- White Label
    custom_domain           VARCHAR(255),
    custom_domain_verified  BOOLEAN DEFAULT false,
    custom_email_domain     VARCHAR(255),
    
    -- Bölgesel Ayarlar
    timezone                VARCHAR(50) NOT NULL DEFAULT 'UTC',
    date_format             VARCHAR(20) DEFAULT 'DD/MM/YYYY',
    time_format             VARCHAR(10) DEFAULT '24h',
    currency_code           CHAR(3) NOT NULL DEFAULT 'USD',
    language                VARCHAR(10) DEFAULT 'en',
    
    -- Operasyonel Ayarlar
    fiscal_year_start_month INTEGER DEFAULT 1,
    week_start_day          INTEGER DEFAULT 1,  -- 1=Monday
    
    -- Rezervasyon Ayarları
    default_booking_duration_minutes    INTEGER DEFAULT 60,
    min_booking_notice_hours           INTEGER DEFAULT 2,
    max_booking_advance_days           INTEGER DEFAULT 30,
    cancellation_notice_hours          INTEGER DEFAULT 24,
    late_cancellation_fee_percent      DECIMAL(5,2) DEFAULT 0,
    no_show_fee_percent                DECIMAL(5,2) DEFAULT 100,
    
    -- Uçuş Ayarları
    default_preflight_minutes          INTEGER DEFAULT 30,
    default_postflight_minutes         INTEGER DEFAULT 30,
    time_tracking_method               VARCHAR(20) DEFAULT 'block_time',
    -- block_time, hobbs_time, tach_time, airborne_time
    
    -- Finans Ayarları
    auto_charge_flights                BOOLEAN DEFAULT true,
    require_positive_balance           BOOLEAN DEFAULT true,
    minimum_balance_warning            DECIMAL(10,2) DEFAULT 100,
    payment_terms_days                 INTEGER DEFAULT 30,
    
    -- Düzenleyici
    regulatory_authority               VARCHAR(20) NOT NULL DEFAULT 'EASA',
    -- EASA, FAA, TCCA, CASA, CAAC, SHGM, etc.
    ato_certificate_number             VARCHAR(100),
    ato_certificate_expiry             DATE,
    ato_approval_type                  VARCHAR(50),
    -- Part-FCL, Part-141, etc.
    
    -- Abonelik
    subscription_plan                  VARCHAR(50) DEFAULT 'trial',
    -- trial, starter, professional, enterprise
    subscription_status                VARCHAR(20) DEFAULT 'active',
    -- active, past_due, cancelled, suspended
    subscription_started_at            TIMESTAMP,
    subscription_ends_at               TIMESTAMP,
    trial_ends_at                      TIMESTAMP,
    
    -- Limitler (Plan bazlı)
    max_users                          INTEGER DEFAULT 10,
    max_aircraft                       INTEGER DEFAULT 5,
    max_students                       INTEGER DEFAULT 50,
    storage_limit_gb                   INTEGER DEFAULT 10,
    
    -- Özellik Bayrakları
    features                           JSONB DEFAULT '{}',
    -- {"advanced_reporting": true, "api_access": true, "white_label": false}
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'active',
    -- pending, active, suspended, cancelled
    
    -- Metadata
    metadata                JSONB DEFAULT '{}',
    
    -- Audit
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID,
    updated_by              UUID,
    deleted_at              TIMESTAMP
);

-- Indexes
CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_status ON organizations(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_organizations_country ON organizations(country_code);
CREATE INDEX idx_organizations_regulatory ON organizations(regulatory_authority);
CREATE INDEX idx_organizations_subscription ON organizations(subscription_status);
CREATE UNIQUE INDEX idx_organizations_custom_domain ON organizations(custom_domain) 
    WHERE custom_domain IS NOT NULL AND custom_domain_verified = true;
```

### 2.2 Locations Tablosu

```sql
-- =============================================================================
-- LOCATIONS (Lokasyonlar / Üsler)
-- =============================================================================
CREATE TABLE locations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Temel Bilgiler
    name                    VARCHAR(255) NOT NULL,
    code                    VARCHAR(20),
    description             TEXT,
    
    -- Tip
    location_type           VARCHAR(50) DEFAULT 'base',
    -- base, satellite, training_area, simulator_center
    
    -- Havalimanı Bilgisi
    airport_icao            CHAR(4),
    airport_iata            CHAR(3),
    airport_name            VARCHAR(255),
    
    -- İletişim
    email                   VARCHAR(255),
    phone                   VARCHAR(50),
    
    -- Adres
    address_line1           VARCHAR(255),
    address_line2           VARCHAR(255),
    city                    VARCHAR(100),
    state_province          VARCHAR(100),
    postal_code             VARCHAR(20),
    country_code            CHAR(2),
    
    -- Koordinatlar
    latitude                DECIMAL(10, 8),
    longitude               DECIMAL(11, 8),
    elevation_ft            INTEGER,
    
    -- Operasyonel
    is_primary              BOOLEAN DEFAULT false,
    is_active               BOOLEAN DEFAULT true,
    
    -- Çalışma Saatleri
    operating_hours         JSONB DEFAULT '{}',
    -- {
    --   "monday": {"open": "08:00", "close": "20:00"},
    --   "tuesday": {"open": "08:00", "close": "20:00"},
    --   ...
    --   "holidays": [{"date": "2024-01-01", "closed": true}]
    -- }
    
    -- Timezone (farklı olabilir)
    timezone                VARCHAR(50),
    
    -- Tesisler
    facilities              JSONB DEFAULT '[]',
    -- ["hangar", "classroom", "briefing_room", "simulator", "fuel_station"]
    
    -- Pist Bilgileri
    runways                 JSONB DEFAULT '[]',
    -- [{"designator": "09/27", "length_ft": 3000, "surface": "asphalt"}]
    
    -- Frekanslar
    frequencies             JSONB DEFAULT '[]',
    -- [{"type": "tower", "frequency": "118.1"}, {"type": "ground", "frequency": "121.9"}]
    
    -- Hava Durumu
    weather_station_id      VARCHAR(50),  -- METAR/TAF için
    
    -- Notlar
    notes                   TEXT,
    pilot_notes             TEXT,  -- Pilotlar için özel notlar
    
    -- Görsel
    photo_url               VARCHAR(500),
    
    -- Metadata
    metadata                JSONB DEFAULT '{}',
    
    -- Sıralama
    display_order           INTEGER DEFAULT 0,
    
    -- Audit
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_org_location_code UNIQUE(organization_id, code)
);

CREATE INDEX idx_locations_org ON locations(organization_id);
CREATE INDEX idx_locations_airport ON locations(airport_icao);
CREATE INDEX idx_locations_primary ON locations(organization_id, is_primary) WHERE is_primary = true;
CREATE INDEX idx_locations_active ON locations(organization_id, is_active) WHERE is_active = true;
```

### 2.3 Organization Settings Tablosu

```sql
-- =============================================================================
-- ORGANIZATION_SETTINGS (Detaylı Ayarlar)
-- =============================================================================
CREATE TABLE organization_settings (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Kategori ve Anahtar
    category                VARCHAR(50) NOT NULL,
    key                     VARCHAR(100) NOT NULL,
    value                   JSONB NOT NULL,
    
    -- Metadata
    description             TEXT,
    is_secret               BOOLEAN DEFAULT false,  -- Hassas veri (API key vb.)
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_org_setting UNIQUE(organization_id, category, key)
);

CREATE INDEX idx_org_settings_org ON organization_settings(organization_id);
CREATE INDEX idx_org_settings_category ON organization_settings(organization_id, category);

-- =============================================================================
-- ÖRNEK AYARLAR
-- =============================================================================

-- Booking Settings
INSERT INTO organization_settings (organization_id, category, key, value, description) VALUES
('org-uuid', 'booking', 'allow_student_self_booking', 'true', 'Öğrenciler kendi rezervasyonlarını yapabilir'),
('org-uuid', 'booking', 'require_instructor_approval', 'false', 'Eğitmen onayı gerekli'),
('org-uuid', 'booking', 'max_concurrent_bookings', '3', 'Maksimum eşzamanlı rezervasyon'),
('org-uuid', 'booking', 'booking_slot_duration', '30', 'Rezervasyon slot süresi (dakika)'),
('org-uuid', 'booking', 'buffer_between_bookings', '15', 'Rezervasyonlar arası tampon (dakika)');

-- Flight Settings
INSERT INTO organization_settings (organization_id, category, key, value, description) VALUES
('org-uuid', 'flight', 'require_dual_signature', 'true', 'Öğrenci ve eğitmen imzası gerekli'),
('org-uuid', 'flight', 'auto_calculate_times', 'true', 'Süreleri otomatik hesapla'),
('org-uuid', 'flight', 'fuel_unit', '"liters"', 'Yakıt birimi (liters/gallons)'),
('org-uuid', 'flight', 'distance_unit', '"nm"', 'Mesafe birimi (nm/km/sm)');

-- Finance Settings
INSERT INTO organization_settings (organization_id, category, key, value, description) VALUES
('org-uuid', 'finance', 'tax_rate', '18', 'Vergi oranı (%)'),
('org-uuid', 'finance', 'tax_name', '"KDV"', 'Vergi adı'),
('org-uuid', 'finance', 'invoice_prefix', '"INV"', 'Fatura numarası ön eki'),
('org-uuid', 'finance', 'invoice_footer', '"Ödeme için teşekkürler"', 'Fatura alt bilgisi');

-- Notification Settings
INSERT INTO organization_settings (organization_id, category, key, value, description) VALUES
('org-uuid', 'notification', 'booking_reminder_hours', '[24, 2]', 'Hatırlatma zamanları (saat önce)'),
('org-uuid', 'notification', 'certificate_expiry_days', '[90, 60, 30, 7]', 'Sertifika uyarı günleri'),
('org-uuid', 'notification', 'low_balance_threshold', '500', 'Düşük bakiye eşiği');

-- Integration Settings (Secret)
INSERT INTO organization_settings (organization_id, category, key, value, description, is_secret) VALUES
('org-uuid', 'integration', 'stripe_secret_key', '"sk_live_xxx"', 'Stripe API Key', true),
('org-uuid', 'integration', 'sendgrid_api_key', '"SG.xxx"', 'SendGrid API Key', true);
```

### 2.4 Subscription Plans Tablosu

```sql
-- =============================================================================
-- SUBSCRIPTION_PLANS (Abonelik Planları)
-- =============================================================================
CREATE TABLE subscription_plans (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Tanımlama
    code                    VARCHAR(50) UNIQUE NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    description             TEXT,
    
    -- Fiyatlandırma
    price_monthly           DECIMAL(10,2) NOT NULL,
    price_yearly            DECIMAL(10,2),
    currency                CHAR(3) DEFAULT 'USD',
    
    -- Limitler
    max_users               INTEGER,
    max_aircraft            INTEGER,
    max_students            INTEGER,
    max_locations           INTEGER,
    storage_limit_gb        INTEGER,
    
    -- Özellikler
    features                JSONB NOT NULL DEFAULT '{}',
    -- {
    --   "api_access": true,
    --   "white_label": false,
    --   "advanced_reporting": true,
    --   "custom_domain": false,
    --   "priority_support": false,
    --   "sla_uptime": 99.5
    -- }
    
    -- Durum
    is_active               BOOLEAN DEFAULT true,
    is_public               BOOLEAN DEFAULT true,  -- Herkese açık mı?
    
    -- Sıralama
    display_order           INTEGER DEFAULT 0,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Varsayılan planlar
INSERT INTO subscription_plans (code, name, price_monthly, max_users, max_aircraft, max_students, features) VALUES
('trial', 'Deneme', 0, 5, 2, 10, '{"api_access": false, "advanced_reporting": false}'),
('starter', 'Başlangıç', 99, 15, 5, 50, '{"api_access": false, "advanced_reporting": true}'),
('professional', 'Profesyonel', 299, 50, 20, 200, '{"api_access": true, "advanced_reporting": true, "custom_domain": true}'),
('enterprise', 'Kurumsal', 999, -1, -1, -1, '{"api_access": true, "advanced_reporting": true, "custom_domain": true, "white_label": true, "priority_support": true}');
```

### 2.5 Organization Invitations

```sql
-- =============================================================================
-- ORGANIZATION_INVITATIONS (Davetler)
-- =============================================================================
CREATE TABLE organization_invitations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Davet Bilgileri
    email                   VARCHAR(255) NOT NULL,
    role_id                 UUID,  -- Atanacak rol
    
    -- Token
    token                   VARCHAR(255) NOT NULL UNIQUE,
    expires_at              TIMESTAMP NOT NULL,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'pending',
    -- pending, accepted, expired, cancelled
    
    accepted_at             TIMESTAMP,
    accepted_by_user_id     UUID,
    
    -- Gönderen
    invited_by              UUID NOT NULL,
    message                 TEXT,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_invitations_org ON organization_invitations(organization_id);
CREATE INDEX idx_invitations_email ON organization_invitations(email);
CREATE INDEX idx_invitations_token ON organization_invitations(token);
CREATE INDEX idx_invitations_status ON organization_invitations(status);
```

---

## 3. DJANGO MODELS

### 3.1 Organization Model

```python
# apps/core/models/organization.py

import uuid
from django.db import models
from django.utils import timezone
from common.models import BaseModel, SoftDeleteModel


class Organization(SoftDeleteModel):
    """Organizasyon modeli"""
    
    class OrganizationType(models.TextChoices):
        FLIGHT_SCHOOL = 'flight_school', 'Uçuş Okulu'
        FLYING_CLUB = 'flying_club', 'Uçuş Kulübü'
        UNIVERSITY = 'university', 'Üniversite'
        SIMULATOR_CENTER = 'simulator_center', 'Simülatör Merkezi'
        AIRLINE_TRAINING = 'airline_training', 'Havayolu Eğitim'
    
    class RegulatoryAuthority(models.TextChoices):
        EASA = 'EASA', 'EASA (European)'
        FAA = 'FAA', 'FAA (United States)'
        TCCA = 'TCCA', 'TCCA (Canada)'
        CASA = 'CASA', 'CASA (Australia)'
        CAAC = 'CAAC', 'CAAC (China)'
        SHGM = 'SHGM', 'SHGM (Turkey)'
        CAA_UK = 'CAA_UK', 'CAA (United Kingdom)'
        DGCA_INDIA = 'DGCA_INDIA', 'DGCA (India)'
    
    class SubscriptionStatus(models.TextChoices):
        ACTIVE = 'active', 'Aktif'
        TRIAL = 'trial', 'Deneme'
        PAST_DUE = 'past_due', 'Ödeme Gecikmiş'
        CANCELLED = 'cancelled', 'İptal Edildi'
        SUSPENDED = 'suspended', 'Askıya Alındı'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Beklemede'
        ACTIVE = 'active', 'Aktif'
        SUSPENDED = 'suspended', 'Askıya Alındı'
        CANCELLED = 'cancelled', 'İptal Edildi'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Temel Bilgiler
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True, null=True)
    slug = models.SlugField(max_length=100, unique=True)
    organization_type = models.CharField(
        max_length=50,
        choices=OrganizationType.choices,
        default=OrganizationType.FLIGHT_SCHOOL
    )
    
    # İletişim
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True, null=True)
    fax = models.CharField(max_length=50, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    
    # Adres
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state_province = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country_code = models.CharField(max_length=2)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    
    # Branding
    logo_url = models.URLField(max_length=500, blank=True, null=True)
    logo_dark_url = models.URLField(max_length=500, blank=True, null=True)
    favicon_url = models.URLField(max_length=500, blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#3B82F6')
    secondary_color = models.CharField(max_length=7, default='#1E40AF')
    accent_color = models.CharField(max_length=7, default='#10B981')
    
    # White Label
    custom_domain = models.CharField(max_length=255, blank=True, null=True, unique=True)
    custom_domain_verified = models.BooleanField(default=False)
    custom_email_domain = models.CharField(max_length=255, blank=True, null=True)
    
    # Bölgesel Ayarlar
    timezone = models.CharField(max_length=50, default='UTC')
    date_format = models.CharField(max_length=20, default='DD/MM/YYYY')
    time_format = models.CharField(max_length=10, default='24h')
    currency_code = models.CharField(max_length=3, default='USD')
    language = models.CharField(max_length=10, default='en')
    
    # Operasyonel Ayarlar
    fiscal_year_start_month = models.IntegerField(default=1)
    week_start_day = models.IntegerField(default=1)
    
    # Rezervasyon Ayarları
    default_booking_duration_minutes = models.IntegerField(default=60)
    min_booking_notice_hours = models.IntegerField(default=2)
    max_booking_advance_days = models.IntegerField(default=30)
    cancellation_notice_hours = models.IntegerField(default=24)
    
    # Uçuş Ayarları
    default_preflight_minutes = models.IntegerField(default=30)
    default_postflight_minutes = models.IntegerField(default=30)
    time_tracking_method = models.CharField(max_length=20, default='block_time')
    
    # Finans Ayarları
    auto_charge_flights = models.BooleanField(default=True)
    require_positive_balance = models.BooleanField(default=True)
    minimum_balance_warning = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    payment_terms_days = models.IntegerField(default=30)
    
    # Düzenleyici
    regulatory_authority = models.CharField(
        max_length=20,
        choices=RegulatoryAuthority.choices,
        default=RegulatoryAuthority.EASA
    )
    ato_certificate_number = models.CharField(max_length=100, blank=True, null=True)
    ato_certificate_expiry = models.DateField(blank=True, null=True)
    ato_approval_type = models.CharField(max_length=50, blank=True, null=True)
    
    # Abonelik
    subscription_plan = models.ForeignKey(
        'SubscriptionPlan',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIAL
    )
    subscription_started_at = models.DateTimeField(blank=True, null=True)
    subscription_ends_at = models.DateTimeField(blank=True, null=True)
    trial_ends_at = models.DateTimeField(blank=True, null=True)
    
    # Limitler
    max_users = models.IntegerField(default=10)
    max_aircraft = models.IntegerField(default=5)
    max_students = models.IntegerField(default=50)
    storage_limit_gb = models.IntegerField(default=10)
    
    # Özellikler
    features = models.JSONField(default=dict)
    
    # Durum
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Metadata
    metadata = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'organizations'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def is_trial(self):
        return self.subscription_status == self.SubscriptionStatus.TRIAL
    
    @property
    def is_trial_expired(self):
        if not self.trial_ends_at:
            return False
        return timezone.now() > self.trial_ends_at
    
    @property
    def is_subscription_active(self):
        return self.subscription_status in [
            self.SubscriptionStatus.ACTIVE,
            self.SubscriptionStatus.TRIAL
        ]
    
    def has_feature(self, feature_name: str) -> bool:
        """Özellik kontrolü"""
        return self.features.get(feature_name, False)
    
    def get_setting(self, category: str, key: str, default=None):
        """Ayar değeri getir"""
        try:
            setting = self.settings.get(category=category, key=key)
            return setting.value
        except OrganizationSetting.DoesNotExist:
            return default


class Location(BaseModel):
    """Lokasyon modeli"""
    
    class LocationType(models.TextChoices):
        BASE = 'base', 'Ana Üs'
        SATELLITE = 'satellite', 'Uydu Üs'
        TRAINING_AREA = 'training_area', 'Eğitim Alanı'
        SIMULATOR_CENTER = 'simulator_center', 'Simülatör Merkezi'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='locations'
    )
    
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    location_type = models.CharField(
        max_length=50,
        choices=LocationType.choices,
        default=LocationType.BASE
    )
    
    # Havalimanı
    airport_icao = models.CharField(max_length=4, blank=True, null=True)
    airport_iata = models.CharField(max_length=3, blank=True, null=True)
    airport_name = models.CharField(max_length=255, blank=True, null=True)
    
    # İletişim
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    
    # Adres
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state_province = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country_code = models.CharField(max_length=2, blank=True, null=True)
    
    # Koordinatlar
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    elevation_ft = models.IntegerField(blank=True, null=True)
    
    # Operasyonel
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Çalışma Saatleri
    operating_hours = models.JSONField(default=dict)
    timezone = models.CharField(max_length=50, blank=True, null=True)
    
    # Tesisler
    facilities = models.JSONField(default=list)
    runways = models.JSONField(default=list)
    frequencies = models.JSONField(default=list)
    
    # Hava Durumu
    weather_station_id = models.CharField(max_length=50, blank=True, null=True)
    
    # Notlar
    notes = models.TextField(blank=True, null=True)
    pilot_notes = models.TextField(blank=True, null=True)
    
    # Görsel
    photo_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Metadata
    metadata = models.JSONField(default=dict)
    display_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'locations'
        ordering = ['display_order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'code'],
                name='unique_org_location_code'
            )
        ]
    
    def __str__(self):
        return f"{self.name} ({self.airport_icao or 'N/A'})"
    
    def save(self, *args, **kwargs):
        # Sadece bir primary location olabilir
        if self.is_primary:
            Location.objects.filter(
                organization=self.organization,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class OrganizationSetting(models.Model):
    """Organizasyon ayarları"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='settings'
    )
    
    category = models.CharField(max_length=50)
    key = models.CharField(max_length=100)
    value = models.JSONField()
    description = models.TextField(blank=True, null=True)
    is_secret = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'organization_settings'
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'category', 'key'],
                name='unique_org_setting'
            )
        ]
    
    def __str__(self):
        return f"{self.organization.name} - {self.category}.{self.key}"


class SubscriptionPlan(models.Model):
    """Abonelik planları"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD')
    
    max_users = models.IntegerField(null=True)
    max_aircraft = models.IntegerField(null=True)
    max_students = models.IntegerField(null=True)
    max_locations = models.IntegerField(null=True)
    storage_limit_gb = models.IntegerField(null=True)
    
    features = models.JSONField(default=dict)
    
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscription_plans'
        ordering = ['display_order', 'price_monthly']
    
    def __str__(self):
        return self.name
```

---

## 4. API ENDPOINTS

### 4.1 Organization Endpoints

```yaml
# =============================================================================
# ORGANIZATION API
# =============================================================================

# Organization CRUD
GET /api/v1/organizations:
  summary: Organizasyon listesi (Super Admin)
  security:
    - bearerAuth: []
  parameters:
    - name: status
      in: query
      schema:
        type: string
    - name: country_code
      in: query
      schema:
        type: string
  responses:
    200:
      description: Organizasyon listesi

POST /api/v1/organizations:
  summary: Yeni organizasyon oluştur
  security:
    - bearerAuth: []
  requestBody:
    required: true
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/CreateOrganization'
  responses:
    201:
      description: Organizasyon oluşturuldu

GET /api/v1/organizations/{id}:
  summary: Organizasyon detayı
  security:
    - bearerAuth: []
  responses:
    200:
      description: Organizasyon detayı

PUT /api/v1/organizations/{id}:
  summary: Organizasyon güncelle
  security:
    - bearerAuth: []
  responses:
    200:
      description: Güncellendi

DELETE /api/v1/organizations/{id}:
  summary: Organizasyon sil
  security:
    - bearerAuth: []
  responses:
    204:
      description: Silindi

# Current Organization (Tenant)
GET /api/v1/organizations/current:
  summary: Mevcut organizasyon
  security:
    - bearerAuth: []
  responses:
    200:
      description: Organizasyon bilgileri

PUT /api/v1/organizations/current:
  summary: Mevcut organizasyonu güncelle
  security:
    - bearerAuth: []
  responses:
    200:
      description: Güncellendi

# Branding
PUT /api/v1/organizations/current/branding:
  summary: Marka ayarları
  security:
    - bearerAuth: []
  requestBody:
    content:
      application/json:
        schema:
          type: object
          properties:
            logo_url:
              type: string
            primary_color:
              type: string
            secondary_color:
              type: string
  responses:
    200:
      description: Güncellendi

POST /api/v1/organizations/current/logo:
  summary: Logo yükle
  security:
    - bearerAuth: []
  requestBody:
    content:
      multipart/form-data:
        schema:
          type: object
          properties:
            logo:
              type: string
              format: binary
  responses:
    200:
      description: Logo yüklendi

# Settings
GET /api/v1/organizations/current/settings:
  summary: Tüm ayarlar
  security:
    - bearerAuth: []
  responses:
    200:
      description: Ayarlar

GET /api/v1/organizations/current/settings/{category}:
  summary: Kategori bazlı ayarlar
  security:
    - bearerAuth: []
  responses:
    200:
      description: Ayarlar

PUT /api/v1/organizations/current/settings/{category}/{key}:
  summary: Ayar güncelle
  security:
    - bearerAuth: []
  responses:
    200:
      description: Güncellendi

# Subscription
GET /api/v1/organizations/current/subscription:
  summary: Abonelik bilgisi
  security:
    - bearerAuth: []
  responses:
    200:
      description: Abonelik

PUT /api/v1/organizations/current/subscription:
  summary: Plan değiştir
  security:
    - bearerAuth: []
  responses:
    200:
      description: Güncellendi

GET /api/v1/organizations/current/usage:
  summary: Kullanım istatistikleri
  security:
    - bearerAuth: []
  responses:
    200:
      description: Kullanım
      content:
        application/json:
          schema:
            type: object
            properties:
              users:
                type: object
                properties:
                  current: { type: integer }
                  limit: { type: integer }
              aircraft:
                type: object
              storage:
                type: object
```

### 4.2 Location Endpoints

```yaml
# =============================================================================
# LOCATION API
# =============================================================================

GET /api/v1/locations:
  summary: Lokasyon listesi
  security:
    - bearerAuth: []
  parameters:
    - name: is_active
      in: query
      schema:
        type: boolean
    - name: location_type
      in: query
      schema:
        type: string
  responses:
    200:
      description: Lokasyon listesi

POST /api/v1/locations:
  summary: Lokasyon oluştur
  security:
    - bearerAuth: []
  requestBody:
    required: true
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/CreateLocation'
  responses:
    201:
      description: Oluşturuldu

GET /api/v1/locations/{id}:
  summary: Lokasyon detayı
  security:
    - bearerAuth: []
  responses:
    200:
      description: Detay

PUT /api/v1/locations/{id}:
  summary: Lokasyon güncelle
  security:
    - bearerAuth: []
  responses:
    200:
      description: Güncellendi

DELETE /api/v1/locations/{id}:
  summary: Lokasyon sil
  security:
    - bearerAuth: []
  responses:
    204:
      description: Silindi

PUT /api/v1/locations/{id}/set-primary:
  summary: Ana lokasyon yap
  security:
    - bearerAuth: []
  responses:
    200:
      description: Güncellendi

GET /api/v1/locations/{id}/weather:
  summary: Hava durumu bilgisi
  security:
    - bearerAuth: []
  responses:
    200:
      description: METAR/TAF bilgisi
```

---

## 5. SERVİS KATMANI

### 5.1 Organization Service

```python
# apps/core/services/organization_service.py

from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.utils.text import slugify
from django.core.cache import cache

from apps.core.models import Organization, Location, OrganizationSetting, SubscriptionPlan
from apps.core.repositories import OrganizationRepository, LocationRepository
from common.exceptions import ValidationError, NotFoundError, LimitExceededError
from common.events import EventBus, EventTypes


class OrganizationService:
    def __init__(self):
        self.org_repo = OrganizationRepository()
        self.location_repo = LocationRepository()
        self.event_bus = EventBus()
    
    async def create_organization(
        self,
        name: str,
        email: str,
        country_code: str,
        admin_user_id: str,
        **kwargs
    ) -> Organization:
        """Yeni organizasyon oluştur"""
        
        # Slug oluştur
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        while await self.org_repo.exists_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Trial plan bul
        trial_plan = await SubscriptionPlan.objects.filter(code='trial').afirst()
        
        # Organizasyon oluştur
        org = await self.org_repo.create(
            name=name,
            slug=slug,
            email=email,
            country_code=country_code,
            subscription_plan=trial_plan,
            subscription_status='trial',
            trial_ends_at=timezone.now() + timezone.timedelta(days=14),
            max_users=trial_plan.max_users if trial_plan else 5,
            max_aircraft=trial_plan.max_aircraft if trial_plan else 2,
            max_students=trial_plan.max_students if trial_plan else 10,
            **kwargs
        )
        
        # Varsayılan ayarları oluştur
        await self._create_default_settings(org)
        
        # Event yayınla
        self.event_bus.publish(EventTypes.ORGANIZATION_CREATED, {
            'organization_id': str(org.id),
            'name': org.name,
            'admin_user_id': admin_user_id
        })
        
        return org
    
    async def update_organization(
        self,
        organization_id: str,
        data: Dict[str, Any],
        updated_by: str
    ) -> Organization:
        """Organizasyon güncelle"""
        
        org = await self.org_repo.get_by_id(organization_id)
        if not org:
            raise NotFoundError('Organizasyon bulunamadı')
        
        # Güncellenebilir alanlar
        allowed_fields = [
            'name', 'legal_name', 'email', 'phone', 'fax', 'website',
            'address_line1', 'address_line2', 'city', 'state_province',
            'postal_code', 'country_code', 'timezone', 'date_format',
            'time_format', 'currency_code', 'language',
            'default_booking_duration_minutes', 'min_booking_notice_hours',
            'max_booking_advance_days', 'cancellation_notice_hours',
            'default_preflight_minutes', 'default_postflight_minutes',
            'time_tracking_method', 'auto_charge_flights',
            'require_positive_balance', 'minimum_balance_warning',
            'regulatory_authority', 'ato_certificate_number',
            'ato_certificate_expiry', 'ato_approval_type',
            'metadata'
        ]
        
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        update_data['updated_by'] = updated_by
        
        org = await self.org_repo.update(organization_id, update_data)
        
        # Cache temizle
        self._invalidate_cache(organization_id)
        
        # Event yayınla
        self.event_bus.publish(EventTypes.ORGANIZATION_UPDATED, {
            'organization_id': organization_id,
            'changed_fields': list(update_data.keys()),
            'updated_by': updated_by
        })
        
        return org
    
    async def update_branding(
        self,
        organization_id: str,
        logo_url: str = None,
        logo_dark_url: str = None,
        primary_color: str = None,
        secondary_color: str = None,
        accent_color: str = None
    ) -> Organization:
        """Marka ayarlarını güncelle"""
        
        update_data = {}
        if logo_url:
            update_data['logo_url'] = logo_url
        if logo_dark_url:
            update_data['logo_dark_url'] = logo_dark_url
        if primary_color:
            self._validate_color(primary_color)
            update_data['primary_color'] = primary_color
        if secondary_color:
            self._validate_color(secondary_color)
            update_data['secondary_color'] = secondary_color
        if accent_color:
            self._validate_color(accent_color)
            update_data['accent_color'] = accent_color
        
        return await self.org_repo.update(organization_id, update_data)
    
    async def get_usage_stats(self, organization_id: str) -> Dict[str, Any]:
        """Kullanım istatistiklerini getir"""
        
        org = await self.org_repo.get_by_id(organization_id)
        
        # Servislerden kullanım bilgisi al
        user_count = await self._get_user_count(organization_id)
        aircraft_count = await self._get_aircraft_count(organization_id)
        student_count = await self._get_student_count(organization_id)
        storage_used = await self._get_storage_used(organization_id)
        
        return {
            'users': {
                'current': user_count,
                'limit': org.max_users,
                'percentage': (user_count / org.max_users * 100) if org.max_users > 0 else 0
            },
            'aircraft': {
                'current': aircraft_count,
                'limit': org.max_aircraft,
                'percentage': (aircraft_count / org.max_aircraft * 100) if org.max_aircraft > 0 else 0
            },
            'students': {
                'current': student_count,
                'limit': org.max_students,
                'percentage': (student_count / org.max_students * 100) if org.max_students > 0 else 0
            },
            'storage': {
                'used_gb': storage_used,
                'limit_gb': org.storage_limit_gb,
                'percentage': (storage_used / org.storage_limit_gb * 100) if org.storage_limit_gb > 0 else 0
            }
        }
    
    async def check_limit(
        self,
        organization_id: str,
        resource_type: str
    ) -> bool:
        """Limit kontrolü"""
        
        org = await self.org_repo.get_by_id(organization_id)
        usage = await self.get_usage_stats(organization_id)
        
        resource_map = {
            'user': 'users',
            'aircraft': 'aircraft',
            'student': 'students'
        }
        
        resource = resource_map.get(resource_type)
        if not resource:
            return True
        
        current = usage[resource]['current']
        limit = usage[resource]['limit']
        
        if limit == -1:  # Unlimited
            return True
        
        return current < limit
    
    async def change_subscription(
        self,
        organization_id: str,
        plan_code: str
    ) -> Organization:
        """Abonelik planını değiştir"""
        
        plan = await SubscriptionPlan.objects.filter(code=plan_code, is_active=True).afirst()
        if not plan:
            raise NotFoundError('Plan bulunamadı')
        
        org = await self.org_repo.get_by_id(organization_id)
        
        # Yeni plan limitleri yeterli mi kontrol et
        usage = await self.get_usage_stats(organization_id)
        
        if plan.max_users and plan.max_users != -1:
            if usage['users']['current'] > plan.max_users:
                raise LimitExceededError(f"Mevcut kullanıcı sayısı ({usage['users']['current']}) yeni plan limitini ({plan.max_users}) aşıyor")
        
        # Planı güncelle
        update_data = {
            'subscription_plan': plan,
            'subscription_status': 'active',
            'subscription_started_at': timezone.now(),
            'max_users': plan.max_users or -1,
            'max_aircraft': plan.max_aircraft or -1,
            'max_students': plan.max_students or -1,
            'storage_limit_gb': plan.storage_limit_gb or -1,
            'features': plan.features
        }
        
        return await self.org_repo.update(organization_id, update_data)
    
    # =========================================================================
    # SETTINGS
    # =========================================================================
    
    async def get_settings(
        self,
        organization_id: str,
        category: str = None
    ) -> Dict[str, Any]:
        """Ayarları getir"""
        
        cache_key = f'org_settings:{organization_id}'
        if category:
            cache_key += f':{category}'
        
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        query = OrganizationSetting.objects.filter(organization_id=organization_id)
        if category:
            query = query.filter(category=category)
        
        settings = {}
        async for setting in query:
            if setting.category not in settings:
                settings[setting.category] = {}
            
            # Secret değerleri maskele
            if setting.is_secret:
                settings[setting.category][setting.key] = '********'
            else:
                settings[setting.category][setting.key] = setting.value
        
        cache.set(cache_key, settings, 300)
        return settings
    
    async def update_setting(
        self,
        organization_id: str,
        category: str,
        key: str,
        value: Any
    ) -> OrganizationSetting:
        """Ayar güncelle"""
        
        setting, created = await OrganizationSetting.objects.aupdate_or_create(
            organization_id=organization_id,
            category=category,
            key=key,
            defaults={'value': value}
        )
        
        # Cache temizle
        cache.delete(f'org_settings:{organization_id}')
        cache.delete(f'org_settings:{organization_id}:{category}')
        
        return setting
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    async def _create_default_settings(self, org: Organization):
        """Varsayılan ayarları oluştur"""
        
        default_settings = [
            ('booking', 'allow_student_self_booking', True),
            ('booking', 'require_instructor_approval', False),
            ('booking', 'max_concurrent_bookings', 3),
            ('flight', 'require_dual_signature', True),
            ('flight', 'auto_calculate_times', True),
            ('finance', 'tax_rate', 0),
            ('finance', 'invoice_prefix', 'INV'),
            ('notification', 'booking_reminder_hours', [24, 2]),
            ('notification', 'certificate_expiry_days', [90, 60, 30, 7]),
        ]
        
        for category, key, value in default_settings:
            await OrganizationSetting.objects.acreate(
                organization=org,
                category=category,
                key=key,
                value=value
            )
    
    def _validate_color(self, color: str):
        """Hex renk validasyonu"""
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
            raise ValidationError('Geçersiz renk formatı. #RRGGBB kullanın.')
    
    def _invalidate_cache(self, organization_id: str):
        """Cache temizle"""
        cache.delete(f'organization:{organization_id}')
        cache.delete(f'org_settings:{organization_id}')


class LocationService:
    def __init__(self):
        self.location_repo = LocationRepository()
        self.org_service = OrganizationService()
        self.event_bus = EventBus()
    
    async def create_location(
        self,
        organization_id: str,
        name: str,
        **kwargs
    ) -> Location:
        """Lokasyon oluştur"""
        
        # İlk lokasyonsa primary yap
        existing_count = await self.location_repo.count_by_org(organization_id)
        is_primary = existing_count == 0
        
        location = await self.location_repo.create(
            organization_id=organization_id,
            name=name,
            is_primary=is_primary,
            **kwargs
        )
        
        self.event_bus.publish('location.created', {
            'location_id': str(location.id),
            'organization_id': organization_id,
            'name': name
        })
        
        return location
    
    async def update_location(
        self,
        location_id: str,
        data: Dict[str, Any]
    ) -> Location:
        """Lokasyon güncelle"""
        
        return await self.location_repo.update(location_id, data)
    
    async def set_primary(
        self,
        organization_id: str,
        location_id: str
    ) -> Location:
        """Primary lokasyon yap"""
        
        # Tüm lokasyonların primary'sini kaldır
        await Location.objects.filter(
            organization_id=organization_id,
            is_primary=True
        ).aupdate(is_primary=False)
        
        # Yeni primary'yi ayarla
        return await self.location_repo.update(location_id, {'is_primary': True})
    
    async def get_weather(self, location_id: str) -> Dict[str, Any]:
        """Hava durumu bilgisi"""
        
        location = await self.location_repo.get_by_id(location_id)
        if not location or not location.airport_icao:
            return None
        
        # METAR/TAF API çağrısı (örnek)
        # Bu kısım gerçek API entegrasyonu gerektirir
        return {
            'metar': f'METAR for {location.airport_icao}',
            'taf': f'TAF for {location.airport_icao}',
            'fetched_at': timezone.now().isoformat()
        }
```

---

## 6. EVENTS

### 6.1 Published Events

```python
# Organization Service tarafından yayınlanan event'ler

ORGANIZATION_CREATED = 'organization.created'
# Payload:
# {
#     "organization_id": "uuid",
#     "name": "string",
#     "admin_user_id": "uuid"
# }

ORGANIZATION_UPDATED = 'organization.updated'
# Payload:
# {
#     "organization_id": "uuid",
#     "changed_fields": ["field1", "field2"]
# }

ORGANIZATION_SUSPENDED = 'organization.suspended'
# Payload:
# {
#     "organization_id": "uuid",
#     "reason": "string"
# }

ORGANIZATION_DELETED = 'organization.deleted'
# Payload:
# {
#     "organization_id": "uuid"
# }

SUBSCRIPTION_CHANGED = 'organization.subscription_changed'
# Payload:
# {
#     "organization_id": "uuid",
#     "old_plan": "string",
#     "new_plan": "string"
# }

LOCATION_CREATED = 'location.created'
LOCATION_UPDATED = 'location.updated'
LOCATION_DELETED = 'location.deleted'
```

---

## 7. MULTI-TENANT MİMARİSİ

### 7.1 Tenant Middleware

```python
# common/middleware/tenant.py

from django.http import Http404
from django.core.cache import cache
from apps.core.models import Organization


class TenantMiddleware:
    """Multi-tenant middleware"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Organization ID'yi belirle
        organization_id = self._get_organization_id(request)
        
        if organization_id:
            organization = self._get_organization(organization_id)
            if not organization:
                raise Http404("Organization not found")
            
            if organization.status != 'active':
                raise Http404("Organization is not active")
            
            request.organization = organization
            request.organization_id = organization_id
        else:
            request.organization = None
            request.organization_id = None
        
        response = self.get_response(request)
        return response
    
    def _get_organization_id(self, request):
        """Organization ID'yi çeşitli kaynaklardan al"""
        
        # 1. Header'dan
        org_id = request.headers.get('X-Organization-ID')
        if org_id:
            return org_id
        
        # 2. JWT token'dan
        if hasattr(request, 'user') and hasattr(request.user, 'organization_id'):
            return str(request.user.organization_id)
        
        # 3. Custom domain'den
        host = request.get_host().split(':')[0]
        if host and host not in ['localhost', '127.0.0.1']:
            org = self._get_organization_by_domain(host)
            if org:
                return str(org.id)
        
        # 4. Subdomain'den
        subdomain = self._get_subdomain(request)
        if subdomain:
            org = self._get_organization_by_slug(subdomain)
            if org:
                return str(org.id)
        
        return None
    
    def _get_organization(self, organization_id):
        """Organization'ı cache'den veya DB'den al"""
        
        cache_key = f'organization:{organization_id}'
        org = cache.get(cache_key)
        
        if not org:
            try:
                org = Organization.objects.get(id=organization_id)
                cache.set(cache_key, org, 300)  # 5 dakika
            except Organization.DoesNotExist:
                return None
        
        return org
    
    def _get_organization_by_domain(self, domain):
        """Custom domain ile organization bul"""
        
        cache_key = f'org_domain:{domain}'
        org = cache.get(cache_key)
        
        if org is None:
            try:
                org = Organization.objects.get(
                    custom_domain=domain,
                    custom_domain_verified=True
                )
                cache.set(cache_key, org, 300)
            except Organization.DoesNotExist:
                cache.set(cache_key, False, 60)
                return None
        
        return org if org else None
    
    def _get_organization_by_slug(self, slug):
        """Slug ile organization bul"""
        
        cache_key = f'org_slug:{slug}'
        org = cache.get(cache_key)
        
        if org is None:
            try:
                org = Organization.objects.get(slug=slug)
                cache.set(cache_key, org, 300)
            except Organization.DoesNotExist:
                cache.set(cache_key, False, 60)
                return None
        
        return org if org else None
    
    def _get_subdomain(self, request):
        """Request'ten subdomain çıkar"""
        
        host = request.get_host().split(':')[0]
        parts = host.split('.')
        
        if len(parts) > 2:
            return parts[0]
        
        return None
```

### 7.2 Tenant-Aware QuerySet

```python
# common/models/managers.py

from django.db import models


class TenantManager(models.Manager):
    """Tenant-aware manager"""
    
    def get_queryset(self):
        return super().get_queryset()
    
    def for_organization(self, organization_id):
        """Organization'a göre filtrele"""
        return self.get_queryset().filter(organization_id=organization_id)


class TenantModel(models.Model):
    """Tenant-aware base model"""
    
    organization_id = models.UUIDField(db_index=True)
    
    objects = TenantManager()
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        # Organization ID zorunlu
        if not self.organization_id:
            raise ValueError("organization_id is required")
        super().save(*args, **kwargs)
```

---

Bu doküman Organization Service'in tüm detaylarını içermektedir.