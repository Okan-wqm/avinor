# 📜 MODÜL 10: SERTİFİKA SERVİSİ (Certificate Service)

## 1. GENEL BAKIŞ

### 1.1 Servis Bilgileri

| Özellik | Değer |
|---------|-------|
| Servis Adı | certificate-service |
| Port | 8009 |
| Veritabanı | certificate_db |
| Prefix | /api/v1/certificates |

### 1.2 Sorumluluklar

- Pilot lisans ve sertifika yönetimi
- Sağlık sertifikası takibi (Medical)
- Rating ve endorsement yönetimi
- Currency takibi ve uyarıları
- Sertifika doğrulama
- Geçerlilik takibi ve hatırlatmalar
- Düzenleyici uyum kontrolü

---

## 2. VERİTABANI ŞEMASI

### 2.1 Certificates (Sertifikalar)

```sql
-- =============================================================================
-- CERTIFICATES (Sertifikalar/Lisanslar)
-- =============================================================================
CREATE TABLE certificates (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    user_id                 UUID NOT NULL,
    
    -- Sertifika Tipi
    certificate_type        VARCHAR(50) NOT NULL,
    -- pilot_license, medical, language_proficiency, 
    -- instructor_certificate, examiner_authorization,
    -- radio_license, dangerous_goods, crew_resource_management
    
    -- Alt Tip
    certificate_subtype     VARCHAR(50),
    -- PPL, CPL, ATPL, SPL (pilot_license için)
    -- Class 1, Class 2, Class 3, LAPL (medical için)
    
    -- Düzenleyici
    issuing_authority       VARCHAR(50) NOT NULL,
    -- EASA, FAA, SHGM, TCCA, CASA, CAAC
    
    issuing_country         CHAR(2),  -- ISO country code
    
    -- Numara ve Referans
    certificate_number      VARCHAR(100) NOT NULL,
    reference_number        VARCHAR(100),
    
    -- Tarihler
    issue_date              DATE NOT NULL,
    expiry_date             DATE,
    first_issue_date        DATE,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'active',
    -- active, expired, suspended, revoked, pending_renewal
    
    -- Kısıtlamalar
    restrictions            TEXT[],
    limitations             TEXT,
    
    -- Doğrulama
    verified                BOOLEAN DEFAULT false,
    verified_at             TIMESTAMP,
    verified_by             UUID,
    verification_method     VARCHAR(50),
    -- document_check, authority_verification, online_verification
    
    -- Doküman
    document_url            VARCHAR(500),
    document_number         VARCHAR(100),
    
    -- Notlar
    notes                   TEXT,
    
    -- Hatırlatma
    reminder_days           INTEGER[] DEFAULT '{90, 60, 30, 14, 7}',
    last_reminder_sent      TIMESTAMP,
    
    -- Metadata
    metadata                JSONB DEFAULT '{}',
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID
);

CREATE INDEX idx_certificates_user ON certificates(user_id);
CREATE INDEX idx_certificates_org ON certificates(organization_id);
CREATE INDEX idx_certificates_type ON certificates(certificate_type);
CREATE INDEX idx_certificates_expiry ON certificates(expiry_date);
CREATE INDEX idx_certificates_status ON certificates(status);
```

### 2.2 Ratings (Yetkiler)

```sql
-- =============================================================================
-- RATINGS (Rating ve Yetkiler)
-- =============================================================================
CREATE TABLE ratings (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    user_id                 UUID NOT NULL,
    certificate_id          UUID REFERENCES certificates(id) ON DELETE SET NULL,
    
    -- Rating Tipi
    rating_type             VARCHAR(50) NOT NULL,
    -- aircraft_type, class, instrument, instructor, night, 
    -- aerobatic, towing, mountain, seaplane
    
    -- Detay
    rating_code             VARCHAR(50),
    rating_name             VARCHAR(255) NOT NULL,
    
    -- Uçak Tipi (type rating için)
    aircraft_type_id        UUID,
    aircraft_icao           VARCHAR(10),
    
    -- Tarihler
    issue_date              DATE NOT NULL,
    expiry_date             DATE,
    last_proficiency_date   DATE,
    
    -- Yeterlilik Gereksinimleri
    validity_period_months  INTEGER,
    proficiency_check_months INTEGER,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'active',
    -- active, expired, suspended, lapsed
    
    -- Kısıtlamalar
    restrictions            TEXT[],
    -- ["SIC only", "VFR only", "Day only"]
    
    -- Eğitim Bilgisi
    training_organization   VARCHAR(255),
    training_completion_date DATE,
    examiner_id             UUID,
    examiner_name           VARCHAR(255),
    
    -- Doküman
    document_url            VARCHAR(500),
    
    notes                   TEXT,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ratings_user ON ratings(user_id);
CREATE INDEX idx_ratings_certificate ON ratings(certificate_id);
CREATE INDEX idx_ratings_type ON ratings(rating_type);
CREATE INDEX idx_ratings_expiry ON ratings(expiry_date);
```

### 2.3 Medical Certificates (Sağlık Sertifikaları)

```sql
-- =============================================================================
-- MEDICAL_CERTIFICATES (Sağlık Sertifikaları)
-- =============================================================================
CREATE TABLE medical_certificates (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    user_id                 UUID NOT NULL,
    
    -- Sınıf
    medical_class           VARCHAR(20) NOT NULL,
    -- class_1, class_2, class_3, lapl, basicmed
    
    -- Düzenleyici
    issuing_authority       VARCHAR(50) NOT NULL,
    issuing_country         CHAR(2),
    
    -- Numara
    certificate_number      VARCHAR(100),
    
    -- AME (Aviation Medical Examiner)
    ame_name                VARCHAR(255),
    ame_license_number      VARCHAR(100),
    ame_address             TEXT,
    
    -- Tarihler
    examination_date        DATE NOT NULL,
    issue_date              DATE NOT NULL,
    expiry_date             DATE NOT NULL,
    
    -- Yaşa Göre Geçerlilik
    pilot_age_at_exam       INTEGER,
    -- Class 1: <40 = 12 ay, 40-59 = 6 ay, 60+ = 6 ay
    -- Class 2: <40 = 60 ay, 40-49 = 24 ay, 50+ = 12 ay
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'active',
    -- active, expired, suspended, revoked
    
    -- Kısıtlamalar
    limitations             TEXT[],
    -- ["VDL - Shall wear corrective lenses", "OML - Valid only with valid OSL"]
    
    limitation_codes        TEXT[],
    -- ["VDL", "OML", "SSL", "TML"]
    
    -- Muayene Sonuçları (özet)
    examination_results     JSONB DEFAULT '{}',
    
    -- Doküman
    document_url            VARCHAR(500),
    
    notes                   TEXT,
    
    -- Hatırlatma
    reminder_sent_90_days   BOOLEAN DEFAULT false,
    reminder_sent_60_days   BOOLEAN DEFAULT false,
    reminder_sent_30_days   BOOLEAN DEFAULT false,
    reminder_sent_14_days   BOOLEAN DEFAULT false,
    reminder_sent_7_days    BOOLEAN DEFAULT false,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_medical_user ON medical_certificates(user_id);
CREATE INDEX idx_medical_expiry ON medical_certificates(expiry_date);
CREATE INDEX idx_medical_status ON medical_certificates(status);
```

### 2.4 Endorsements (Onaylar)

```sql
-- =============================================================================
-- ENDORSEMENTS (Eğitmen Onayları)
-- =============================================================================
CREATE TABLE endorsements (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- İlişkiler
    student_id              UUID NOT NULL,
    instructor_id           UUID NOT NULL,
    
    -- Onay Tipi
    endorsement_type        VARCHAR(100) NOT NULL,
    -- solo_flight, solo_cross_country, checkride_recommendation,
    -- night_flight, instrument_flight, complex_aircraft,
    -- high_performance, tailwheel, pressurized_aircraft
    
    -- Onay Kodu (FAA vb.)
    endorsement_code        VARCHAR(50),
    
    -- Detay
    description             TEXT,
    
    -- Kapsam
    aircraft_type           VARCHAR(100),
    aircraft_registration   VARCHAR(20),
    airports                TEXT[],
    area_description        TEXT,
    
    -- Geçerlilik
    issue_date              DATE NOT NULL,
    expiry_date             DATE,
    
    is_permanent            BOOLEAN DEFAULT false,
    validity_days           INTEGER,  -- 90 gün gibi
    
    -- Kısıtlamalar
    conditions              TEXT[],
    limitations             TEXT,
    
    -- İmza
    instructor_signature    JSONB,
    signed_at               TIMESTAMP,
    
    instructor_certificate_number VARCHAR(100),
    instructor_certificate_expiry DATE,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'active',
    -- active, expired, revoked
    
    -- İlgili Uçuş/Eğitim
    related_flight_id       UUID,
    related_lesson_id       UUID,
    
    notes                   TEXT,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_endorsements_student ON endorsements(student_id);
CREATE INDEX idx_endorsements_instructor ON endorsements(instructor_id);
CREATE INDEX idx_endorsements_type ON endorsements(endorsement_type);
```

### 2.5 Currency Requirements (Güncellik Gereksinimleri)

```sql
-- =============================================================================
-- CURRENCY_REQUIREMENTS (Güncellik Gereksinimleri)
-- =============================================================================
CREATE TABLE currency_requirements (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Tanımlama
    name                    VARCHAR(255) NOT NULL,
    code                    VARCHAR(50) NOT NULL,
    description             TEXT,
    
    -- Düzenleyici Kaynak
    regulatory_reference    VARCHAR(255),
    -- FAR 61.57, EASA FCL.060
    
    -- Gereksinim Tipi
    requirement_type        VARCHAR(50) NOT NULL,
    -- takeoff_landing, night, ifr, type_specific, instructor
    
    -- Kriter
    criteria                JSONB NOT NULL,
    -- {
    --   "period_days": 90,
    --   "min_takeoffs": 3,
    --   "min_landings": 3,
    --   "full_stop_required": true,
    --   "conditions": ["day"]
    -- }
    
    -- Kapsam
    applies_to              JSONB DEFAULT '{}',
    -- {"license_types": ["PPL", "CPL"], "operation_types": ["passenger"]}
    
    -- Aktiflik
    is_active               BOOLEAN DEFAULT true,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- USER_CURRENCY_STATUS (Kullanıcı Güncellik Durumu)
-- =============================================================================
CREATE TABLE user_currency_status (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    user_id                 UUID NOT NULL,
    requirement_id          UUID NOT NULL REFERENCES currency_requirements(id),
    
    -- Durum
    is_current              BOOLEAN DEFAULT false,
    
    -- Son Aktivite
    last_activity_date      DATE,
    last_activity_id        UUID,  -- flight_id
    
    -- Mevcut Sayılar
    current_count           JSONB DEFAULT '{}',
    -- {"takeoffs": 5, "landings": 5, "night_landings": 2}
    
    -- Geçerlilik
    valid_until             DATE,
    
    -- Son Kontrol
    last_checked_at         TIMESTAMP,
    
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_user_currency UNIQUE(user_id, requirement_id)
);

CREATE INDEX idx_currency_status_user ON user_currency_status(user_id);
CREATE INDEX idx_currency_status_current ON user_currency_status(is_current);
```

---

## 3. DJANGO MODELS

```python
# apps/core/models/certificate.py

import uuid
from datetime import date, timedelta
from django.db import models
from django.utils import timezone
from common.models import TenantModel


class Certificate(TenantModel):
    """Sertifika/Lisans modeli"""
    
    class CertificateType(models.TextChoices):
        PILOT_LICENSE = 'pilot_license', 'Pilot Lisansı'
        MEDICAL = 'medical', 'Sağlık Sertifikası'
        LANGUAGE_PROFICIENCY = 'language_proficiency', 'Dil Yeterliliği'
        INSTRUCTOR_CERTIFICATE = 'instructor_certificate', 'Eğitmen Sertifikası'
        EXAMINER_AUTHORIZATION = 'examiner_authorization', 'Examiner Yetkisi'
        RADIO_LICENSE = 'radio_license', 'Telsiz Lisansı'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Aktif'
        EXPIRED = 'expired', 'Süresi Dolmuş'
        SUSPENDED = 'suspended', 'Askıya Alınmış'
        REVOKED = 'revoked', 'İptal Edilmiş'
        PENDING_RENEWAL = 'pending_renewal', 'Yenileme Bekliyor'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    
    certificate_type = models.CharField(
        max_length=50,
        choices=CertificateType.choices
    )
    certificate_subtype = models.CharField(max_length=50, blank=True, null=True)
    
    issuing_authority = models.CharField(max_length=50)
    issuing_country = models.CharField(max_length=2, blank=True, null=True)
    
    certificate_number = models.CharField(max_length=100)
    
    issue_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    
    restrictions = models.JSONField(default=list)
    
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.UUIDField(blank=True, null=True)
    
    document_url = models.URLField(max_length=500, blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)
    
    reminder_days = models.JSONField(default=lambda: [90, 60, 30, 14, 7])
    last_reminder_sent = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'certificates'
        ordering = ['-issue_date']
    
    def __str__(self):
        return f"{self.certificate_type}: {self.certificate_number}"
    
    @property
    def is_expired(self) -> bool:
        if not self.expiry_date:
            return False
        return self.expiry_date < date.today()
    
    @property
    def days_until_expiry(self) -> int | None:
        if not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days
    
    @property
    def is_expiring_soon(self) -> bool:
        days = self.days_until_expiry
        if days is None:
            return False
        return 0 < days <= 90
    
    def update_status(self):
        """Durumu güncelle"""
        if self.is_expired:
            self.status = self.Status.EXPIRED
        elif self.is_expiring_soon:
            self.status = self.Status.PENDING_RENEWAL
        self.save()


class MedicalCertificate(TenantModel):
    """Sağlık sertifikası modeli"""
    
    class MedicalClass(models.TextChoices):
        CLASS_1 = 'class_1', 'Class 1'
        CLASS_2 = 'class_2', 'Class 2'
        CLASS_3 = 'class_3', 'Class 3'
        LAPL = 'lapl', 'LAPL Medical'
        BASICMED = 'basicmed', 'BasicMed'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Aktif'
        EXPIRED = 'expired', 'Süresi Dolmuş'
        SUSPENDED = 'suspended', 'Askıya Alınmış'
        REVOKED = 'revoked', 'İptal Edilmiş'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    
    medical_class = models.CharField(
        max_length=20,
        choices=MedicalClass.choices
    )
    
    issuing_authority = models.CharField(max_length=50)
    issuing_country = models.CharField(max_length=2, blank=True, null=True)
    
    certificate_number = models.CharField(max_length=100, blank=True, null=True)
    
    ame_name = models.CharField(max_length=255, blank=True, null=True)
    ame_license_number = models.CharField(max_length=100, blank=True, null=True)
    
    examination_date = models.DateField()
    issue_date = models.DateField()
    expiry_date = models.DateField()
    
    pilot_age_at_exam = models.IntegerField(blank=True, null=True)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    
    limitations = models.JSONField(default=list)
    limitation_codes = models.JSONField(default=list)
    
    document_url = models.URLField(max_length=500, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_certificates'
        ordering = ['-expiry_date']
    
    def __str__(self):
        return f"{self.medical_class}: {self.user_id}"
    
    @property
    def is_valid(self) -> bool:
        return (
            self.status == self.Status.ACTIVE and
            self.expiry_date >= date.today()
        )
    
    @property
    def days_until_expiry(self) -> int:
        return (self.expiry_date - date.today()).days


class Rating(TenantModel):
    """Rating/Yetki modeli"""
    
    class RatingType(models.TextChoices):
        AIRCRAFT_TYPE = 'aircraft_type', 'Uçak Tipi'
        CLASS = 'class', 'Sınıf'
        INSTRUMENT = 'instrument', 'Aletli Uçuş'
        INSTRUCTOR = 'instructor', 'Eğitmen'
        NIGHT = 'night', 'Gece'
        AEROBATIC = 'aerobatic', 'Akrobasi'
        TOWING = 'towing', 'Çekme'
        MOUNTAIN = 'mountain', 'Dağ'
        SEAPLANE = 'seaplane', 'Deniz Uçağı'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    certificate = models.ForeignKey(
        Certificate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ratings'
    )
    
    rating_type = models.CharField(
        max_length=50,
        choices=RatingType.choices
    )
    rating_code = models.CharField(max_length=50, blank=True, null=True)
    rating_name = models.CharField(max_length=255)
    
    aircraft_icao = models.CharField(max_length=10, blank=True, null=True)
    
    issue_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    last_proficiency_date = models.DateField(blank=True, null=True)
    
    status = models.CharField(max_length=20, default='active')
    restrictions = models.JSONField(default=list)
    
    document_url = models.URLField(max_length=500, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ratings'
        ordering = ['rating_type', 'rating_name']
    
    def __str__(self):
        return f"{self.rating_type}: {self.rating_name}"


class Endorsement(TenantModel):
    """Eğitmen onayı modeli"""
    
    class EndorsementType(models.TextChoices):
        SOLO_FLIGHT = 'solo_flight', 'Solo Uçuş'
        SOLO_CROSS_COUNTRY = 'solo_cross_country', 'Solo Cross Country'
        CHECKRIDE_RECOMMENDATION = 'checkride_recommendation', 'Sınav Tavsiyesi'
        NIGHT_FLIGHT = 'night_flight', 'Gece Uçuşu'
        COMPLEX_AIRCRAFT = 'complex_aircraft', 'Kompleks Uçak'
        HIGH_PERFORMANCE = 'high_performance', 'Yüksek Performans'
        TAILWHEEL = 'tailwheel', 'Tailwheel'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    student_id = models.UUIDField(db_index=True)
    instructor_id = models.UUIDField(db_index=True)
    
    endorsement_type = models.CharField(
        max_length=100,
        choices=EndorsementType.choices
    )
    endorsement_code = models.CharField(max_length=50, blank=True, null=True)
    
    description = models.TextField(blank=True, null=True)
    
    aircraft_type = models.CharField(max_length=100, blank=True, null=True)
    aircraft_registration = models.CharField(max_length=20, blank=True, null=True)
    
    issue_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    
    is_permanent = models.BooleanField(default=False)
    validity_days = models.IntegerField(blank=True, null=True)
    
    conditions = models.JSONField(default=list)
    limitations = models.TextField(blank=True, null=True)
    
    instructor_signature = models.JSONField(blank=True, null=True)
    signed_at = models.DateTimeField(blank=True, null=True)
    
    instructor_certificate_number = models.CharField(max_length=100, blank=True, null=True)
    
    status = models.CharField(max_length=20, default='active')
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'endorsements'
        ordering = ['-issue_date']
    
    def __str__(self):
        return f"{self.endorsement_type}: {self.student_id}"
    
    @property
    def is_valid(self) -> bool:
        if self.status != 'active':
            return False
        if self.is_permanent:
            return True
        if self.expiry_date:
            return self.expiry_date >= date.today()
        return True
```

---

## 4. API ENDPOINTS

```yaml
# =============================================================================
# CERTIFICATE API
# =============================================================================

# Certificates
GET /api/v1/certificates:
  summary: Sertifika listesi
  parameters:
    - name: user_id
    - name: type
    - name: status

POST /api/v1/certificates:
  summary: Sertifika ekle

GET /api/v1/certificates/{id}:
  summary: Sertifika detayı

PUT /api/v1/certificates/{id}:
  summary: Sertifika güncelle

DELETE /api/v1/certificates/{id}:
  summary: Sertifika sil

POST /api/v1/certificates/{id}/verify:
  summary: Sertifikayı doğrula

# Medical
GET /api/v1/certificates/medical:
  summary: Sağlık sertifikaları

POST /api/v1/certificates/medical:
  summary: Sağlık sertifikası ekle

GET /api/v1/certificates/medical/{id}:
  summary: Sağlık sertifikası detayı

# Ratings
GET /api/v1/certificates/ratings:
  summary: Rating listesi

POST /api/v1/certificates/ratings:
  summary: Rating ekle

# Endorsements
GET /api/v1/certificates/endorsements:
  summary: Endorsement listesi

POST /api/v1/certificates/endorsements:
  summary: Endorsement oluştur

POST /api/v1/certificates/endorsements/{id}/sign:
  summary: Endorsement imzala

# Currency
GET /api/v1/certificates/currency:
  summary: Currency durumu
  parameters:
    - name: user_id

GET /api/v1/certificates/currency/check:
  summary: Currency kontrolü
  parameters:
    - name: user_id
    - name: operation_type

# Expiry Alerts
GET /api/v1/certificates/expiring:
  summary: Süresi dolacak sertifikalar
  parameters:
    - name: days_ahead
      default: 90

# User Summary
GET /api/v1/certificates/user/{user_id}/summary:
  summary: Kullanıcı sertifika özeti

GET /api/v1/certificates/user/{user_id}/validity:
  summary: Kullanıcı geçerlilik durumu
```

---

## 5. SERVİS KATMANI

```python
# apps/core/services/certificate_service.py

from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.models import (
    Certificate, MedicalCertificate, Rating, Endorsement,
    CurrencyRequirement, UserCurrencyStatus
)
from common.events import EventBus
from common.clients import FlightServiceClient


class CertificateService:
    def __init__(self):
        self.event_bus = EventBus()
        self.flight_client = FlightServiceClient()
    
    async def get_user_validity_status(
        self,
        user_id: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """Kullanıcının genel geçerlilik durumunu getir"""
        
        issues = []
        warnings = []
        
        # Pilot Lisansı
        pilot_license = await Certificate.objects.filter(
            user_id=user_id,
            certificate_type='pilot_license',
            status='active'
        ).order_by('-issue_date').afirst()
        
        if not pilot_license:
            issues.append({
                'type': 'pilot_license',
                'message': 'Geçerli pilot lisansı bulunamadı',
                'severity': 'error'
            })
        elif pilot_license.expiry_date:
            days = pilot_license.days_until_expiry
            if days <= 0:
                issues.append({
                    'type': 'pilot_license',
                    'message': 'Pilot lisansı süresi dolmuş',
                    'severity': 'error'
                })
            elif days <= 30:
                warnings.append({
                    'type': 'pilot_license',
                    'message': f'Pilot lisansı {days} gün içinde dolacak',
                    'severity': 'warning'
                })
        
        # Medical
        medical = await MedicalCertificate.objects.filter(
            user_id=user_id,
            status='active'
        ).order_by('-expiry_date').afirst()
        
        if not medical:
            issues.append({
                'type': 'medical',
                'message': 'Geçerli sağlık sertifikası bulunamadı',
                'severity': 'error'
            })
        else:
            days = medical.days_until_expiry
            if days <= 0:
                issues.append({
                    'type': 'medical',
                    'message': 'Sağlık sertifikası süresi dolmuş',
                    'severity': 'error'
                })
            elif days <= 30:
                warnings.append({
                    'type': 'medical',
                    'message': f'Sağlık sertifikası {days} gün içinde dolacak',
                    'severity': 'warning'
                })
        
        # Currency
        currency_status = await self.check_currency(user_id, organization_id)
        if not currency_status['is_current']:
            for issue in currency_status['issues']:
                issues.append(issue)
        
        is_valid = len([i for i in issues if i['severity'] == 'error']) == 0
        
        return {
            'user_id': user_id,
            'is_valid': is_valid,
            'can_fly': is_valid,
            'issues': issues,
            'warnings': warnings,
            'checked_at': timezone.now().isoformat()
        }
    
    async def check_currency(
        self,
        user_id: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """Currency durumunu kontrol et"""
        
        issues = []
        
        # Son 90 gündeki uçuşları al
        ninety_days_ago = date.today() - timedelta(days=90)
        flights = await self.flight_client.get_pilot_flights(
            user_id,
            start_date=ninety_days_ago.isoformat()
        )
        
        # Gündüz inişleri say
        day_landings = sum(f.get('landings_day', 0) for f in flights)
        night_landings = sum(f.get('landings_night', 0) for f in flights)
        
        # Gündüz currency (3 iniş / 90 gün)
        if day_landings < 3:
            issues.append({
                'type': 'day_currency',
                'message': f'Son 90 günde {day_landings}/3 gündüz inişi',
                'severity': 'error'
            })
        
        # Gece currency (3 gece inişi / 90 gün - yolcu için)
        if night_landings < 3:
            issues.append({
                'type': 'night_currency',
                'message': f'Son 90 günde {night_landings}/3 gece inişi',
                'severity': 'warning'
            })
        
        # IFR currency (6 approach / 6 ay)
        six_months_ago = date.today() - timedelta(days=180)
        ifr_flights = await self.flight_client.get_pilot_flights(
            user_id,
            start_date=six_months_ago.isoformat()
        )
        approaches = sum(f.get('approach_count', 0) for f in ifr_flights)
        
        if approaches < 6:
            issues.append({
                'type': 'ifr_currency',
                'message': f'Son 6 ayda {approaches}/6 IFR approach',
                'severity': 'warning'
            })
        
        return {
            'is_current': len([i for i in issues if i['severity'] == 'error']) == 0,
            'issues': issues,
            'stats': {
                'day_landings_90d': day_landings,
                'night_landings_90d': night_landings,
                'ifr_approaches_6m': approaches
            }
        }
    
    @transaction.atomic
    async def create_endorsement(
        self,
        organization_id: str,
        student_id: str,
        instructor_id: str,
        endorsement_type: str,
        issue_date: date,
        **kwargs
    ) -> Endorsement:
        """Endorsement oluştur"""
        
        # Eğitmenin sertifikasını kontrol et
        instructor_cert = await Certificate.objects.filter(
            user_id=instructor_id,
            certificate_type='instructor_certificate',
            status='active'
        ).afirst()
        
        if not instructor_cert:
            raise ValueError('Geçerli eğitmen sertifikası bulunamadı')
        
        endorsement = await Endorsement.objects.acreate(
            organization_id=organization_id,
            student_id=student_id,
            instructor_id=instructor_id,
            endorsement_type=endorsement_type,
            issue_date=issue_date,
            instructor_certificate_number=instructor_cert.certificate_number,
            instructor_certificate_expiry=instructor_cert.expiry_date,
            **kwargs
        )
        
        # Event
        self.event_bus.publish('certificate.endorsement_created', {
            'endorsement_id': str(endorsement.id),
            'student_id': student_id,
            'instructor_id': instructor_id,
            'type': endorsement_type
        })
        
        return endorsement
    
    async def get_expiring_certificates(
        self,
        organization_id: str,
        days_ahead: int = 90
    ) -> List[Dict[str, Any]]:
        """Süresi dolacak sertifikaları getir"""
        
        expiry_date = date.today() + timedelta(days=days_ahead)
        
        expiring = []
        
        # Sertifikalar
        async for cert in Certificate.objects.filter(
            organization_id=organization_id,
            status='active',
            expiry_date__lte=expiry_date,
            expiry_date__gte=date.today()
        ):
            expiring.append({
                'type': 'certificate',
                'subtype': cert.certificate_type,
                'user_id': str(cert.user_id),
                'certificate_id': str(cert.id),
                'expiry_date': cert.expiry_date.isoformat(),
                'days_remaining': cert.days_until_expiry
            })
        
        # Medical
        async for med in MedicalCertificate.objects.filter(
            organization_id=organization_id,
            status='active',
            expiry_date__lte=expiry_date,
            expiry_date__gte=date.today()
        ):
            expiring.append({
                'type': 'medical',
                'subtype': med.medical_class,
                'user_id': str(med.user_id),
                'certificate_id': str(med.id),
                'expiry_date': med.expiry_date.isoformat(),
                'days_remaining': med.days_until_expiry
            })
        
        # Sıralama
        expiring.sort(key=lambda x: x['days_remaining'])
        
        return expiring
```

---

## 6. EVENTS

```python
# Certificate Service Events

CERTIFICATE_CREATED = 'certificate.created'
CERTIFICATE_UPDATED = 'certificate.updated'
CERTIFICATE_EXPIRED = 'certificate.expired'
CERTIFICATE_EXPIRING_SOON = 'certificate.expiring_soon'

MEDICAL_CREATED = 'certificate.medical_created'
MEDICAL_EXPIRED = 'certificate.medical_expired'

RATING_ADDED = 'certificate.rating_added'
RATING_EXPIRED = 'certificate.rating_expired'

ENDORSEMENT_CREATED = 'certificate.endorsement_created'
ENDORSEMENT_SIGNED = 'certificate.endorsement_signed'

CURRENCY_LOST = 'certificate.currency_lost'
CURRENCY_WARNING = 'certificate.currency_warning'

# Consumed Events
FLIGHT_APPROVED = 'flight.approved'
# Handler: Currency durumunu güncelle
```

---

Bu doküman Certificate Service'in tüm detaylarını içermektedir.