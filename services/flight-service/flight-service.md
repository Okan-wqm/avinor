# ✈️ MODÜL 07: UÇUŞ KAYIT SERVİSİ (Flight Service)

## 1. GENEL BAKIŞ

### 1.1 Servis Bilgileri

| Özellik | Değer |
|---------|-------|
| Servis Adı | flight-service |
| Port | 8006 |
| Veritabanı | flight_db |
| Prefix | /api/v1/flights |

### 1.2 Sorumluluklar

- Uçuş kayıtları (Logbook entries)
- Uçuş onay workflow'u
- Pilot logbook yönetimi
- Uçuş istatistikleri
- Deneyim hesaplamaları
- Gece/IFR/XC saat takibi
- Yakıt kayıtları
- Rota ve waypoint yönetimi

---

## 2. VERİTABANI ŞEMASI

### 2.1 Flights Tablosu

```sql
-- =============================================================================
-- FLIGHTS (Uçuş Kayıtları)
-- =============================================================================
CREATE TABLE flights (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- İlişkiler
    booking_id              UUID,
    aircraft_id             UUID NOT NULL,
    
    -- Kişiler
    pic_id                  UUID NOT NULL,  -- Pilot in Command
    sic_id                  UUID,           -- Second in Command
    instructor_id           UUID,
    student_id              UUID,
    examiner_id             UUID,           -- Check ride için
    
    -- Ek Mürettebat/Yolcular
    crew_members            JSONB DEFAULT '[]',
    passengers              JSONB DEFAULT '[]',
    pax_count               INTEGER DEFAULT 0,
    
    -- Uçuş Tarihi
    flight_date             DATE NOT NULL,
    
    -- Rota
    departure_airport       CHAR(4) NOT NULL,
    arrival_airport         CHAR(4) NOT NULL,
    route                   TEXT,
    waypoints               JSONB DEFAULT '[]',
    -- [{"icao": "LTFM", "type": "departure"}, {"icao": "LTBA", "type": "arrival"}]
    
    via_airports            TEXT[],  -- Ara iniş yapılan havalimanları
    
    -- Zamanlar
    block_off               TIMESTAMP,
    takeoff_time            TIMESTAMP,
    landing_time            TIMESTAMP,
    block_on                TIMESTAMP,
    
    -- Süreler (saat cinsinden)
    block_time              DECIMAL(5,2),
    flight_time             DECIMAL(5,2),
    air_time                DECIMAL(5,2),  -- Takeoff to landing
    
    -- Hobbs/Tach (başlangıç ve bitiş)
    hobbs_start             DECIMAL(10,2),
    hobbs_end               DECIMAL(10,2),
    hobbs_time              DECIMAL(5,2),
    tach_start              DECIMAL(10,2),
    tach_end                DECIMAL(10,2),
    tach_time               DECIMAL(5,2),
    
    -- Sayaçlar
    landings_day            INTEGER DEFAULT 0,
    landings_night          INTEGER DEFAULT 0,
    full_stop_day           INTEGER DEFAULT 0,
    full_stop_night         INTEGER DEFAULT 0,
    touch_and_go            INTEGER DEFAULT 0,
    
    -- Uçuş Tipleri (saat cinsinden)
    time_day                DECIMAL(5,2) DEFAULT 0,
    time_night              DECIMAL(5,2) DEFAULT 0,
    time_ifr                DECIMAL(5,2) DEFAULT 0,
    time_actual_instrument  DECIMAL(5,2) DEFAULT 0,
    time_simulated_instrument DECIMAL(5,2) DEFAULT 0,
    time_cross_country      DECIMAL(5,2) DEFAULT 0,
    
    -- Pilot Function Time
    time_pic                DECIMAL(5,2) DEFAULT 0,
    time_sic                DECIMAL(5,2) DEFAULT 0,
    time_dual_received      DECIMAL(5,2) DEFAULT 0,
    time_dual_given         DECIMAL(5,2) DEFAULT 0,
    time_solo               DECIMAL(5,2) DEFAULT 0,
    
    -- Spesifik Eğitim
    time_simulated_flight   DECIMAL(5,2) DEFAULT 0,  -- FTD/FSTD
    
    -- Approach Types
    approaches              JSONB DEFAULT '[]',
    -- [{"type": "ILS", "airport": "LTBA", "runway": "05", "count": 2}]
    approach_count          INTEGER DEFAULT 0,
    
    -- Holding
    holds                   INTEGER DEFAULT 0,
    
    -- Mesafe
    distance_nm             DECIMAL(10,2),
    
    -- Yakıt
    fuel_start_liters       DECIMAL(8,2),
    fuel_end_liters         DECIMAL(8,2),
    fuel_used_liters        DECIMAL(8,2),
    fuel_added_liters       DECIMAL(8,2),
    fuel_cost               DECIMAL(10,2),
    
    -- Yağ
    oil_added_liters        DECIMAL(5,2),
    
    -- Uçuş Tipi
    flight_type             VARCHAR(50) NOT NULL DEFAULT 'training',
    -- training, solo, rental, charter, check_ride, proficiency
    
    flight_rules            VARCHAR(10) DEFAULT 'VFR',
    -- VFR, IFR, SVFR
    
    flight_category         VARCHAR(50),
    -- local, cross_country, night, instrument
    
    -- Eğitim
    training_type           VARCHAR(50),
    -- dual, solo, supervised_solo, stage_check, check_ride
    
    lesson_id               UUID,
    exercises_completed     JSONB DEFAULT '[]',
    lesson_completed        BOOLEAN DEFAULT false,
    
    -- Hava Durumu
    weather_conditions      VARCHAR(20),
    -- VMC, IMC
    
    weather_briefing        TEXT,
    metar_departure         TEXT,
    metar_arrival           TEXT,
    
    -- Risk
    risk_assessment         JSONB,
    risk_score              INTEGER,
    
    -- Durumlar
    flight_status           VARCHAR(20) DEFAULT 'draft',
    -- draft, submitted, pending_review, approved, rejected, cancelled
    
    approval_status         VARCHAR(20) DEFAULT 'pending',
    -- pending, approved, rejected
    
    approved_by             UUID,
    approved_at             TIMESTAMP,
    rejection_reason        TEXT,
    
    -- İmzalar
    pic_signature           JSONB,
    pic_signed_at           TIMESTAMP,
    instructor_signature    JSONB,
    instructor_signed_at    TIMESTAMP,
    student_signature       JSONB,
    student_signed_at       TIMESTAMP,
    
    -- Billing
    is_billed               BOOLEAN DEFAULT false,
    billing_status          VARCHAR(20) DEFAULT 'pending',
    -- pending, calculated, invoiced, paid
    
    aircraft_charge         DECIMAL(10,2),
    instructor_charge       DECIMAL(10,2),
    fuel_charge             DECIMAL(10,2),
    other_charges           DECIMAL(10,2),
    total_charge            DECIMAL(10,2),
    
    transaction_id          UUID,
    
    -- Squawks
    has_squawks             BOOLEAN DEFAULT false,
    squawk_ids              UUID[],
    
    -- Dosyalar
    documents               JSONB DEFAULT '[]',
    track_file_url          VARCHAR(500),  -- GPS track
    
    -- Notlar
    pilot_remarks           TEXT,
    instructor_remarks      TEXT,
    internal_notes          TEXT,
    
    -- Metadata
    metadata                JSONB DEFAULT '{}',
    
    -- Audit
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID NOT NULL,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by              UUID
);

-- Indexes
CREATE INDEX idx_flights_org ON flights(organization_id);
CREATE INDEX idx_flights_date ON flights(flight_date DESC);
CREATE INDEX idx_flights_aircraft ON flights(aircraft_id, flight_date);
CREATE INDEX idx_flights_pic ON flights(pic_id, flight_date);
CREATE INDEX idx_flights_instructor ON flights(instructor_id, flight_date);
CREATE INDEX idx_flights_student ON flights(student_id, flight_date);
CREATE INDEX idx_flights_booking ON flights(booking_id);
CREATE INDEX idx_flights_status ON flights(flight_status);
CREATE INDEX idx_flights_billing ON flights(billing_status) WHERE billing_status != 'paid';
```

### 2.2 Pilot Logbook Summary

```sql
-- =============================================================================
-- PILOT_LOGBOOK_SUMMARY (Pilot Özet İstatistikleri)
-- =============================================================================
CREATE TABLE pilot_logbook_summary (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    pilot_id                UUID NOT NULL,
    
    -- Toplam Süreler
    total_time              DECIMAL(10,2) DEFAULT 0,
    total_pic               DECIMAL(10,2) DEFAULT 0,
    total_sic               DECIMAL(10,2) DEFAULT 0,
    total_dual_received     DECIMAL(10,2) DEFAULT 0,
    total_dual_given        DECIMAL(10,2) DEFAULT 0,
    total_solo              DECIMAL(10,2) DEFAULT 0,
    
    -- Koşullar
    total_day               DECIMAL(10,2) DEFAULT 0,
    total_night             DECIMAL(10,2) DEFAULT 0,
    total_ifr               DECIMAL(10,2) DEFAULT 0,
    total_actual_instrument DECIMAL(10,2) DEFAULT 0,
    total_simulated_instrument DECIMAL(10,2) DEFAULT 0,
    total_cross_country     DECIMAL(10,2) DEFAULT 0,
    
    -- İniş Sayıları
    total_landings          INTEGER DEFAULT 0,
    total_landings_day      INTEGER DEFAULT 0,
    total_landings_night    INTEGER DEFAULT 0,
    total_full_stop_day     INTEGER DEFAULT 0,
    total_full_stop_night   INTEGER DEFAULT 0,
    
    -- Approach
    total_approaches        INTEGER DEFAULT 0,
    
    -- Uçak Kategorileri
    time_single_engine      DECIMAL(10,2) DEFAULT 0,
    time_multi_engine       DECIMAL(10,2) DEFAULT 0,
    time_complex            DECIMAL(10,2) DEFAULT 0,
    time_high_performance   DECIMAL(10,2) DEFAULT 0,
    time_turbine            DECIMAL(10,2) DEFAULT 0,
    time_tailwheel          DECIMAL(10,2) DEFAULT 0,
    time_helicopter         DECIMAL(10,2) DEFAULT 0,
    time_glider             DECIMAL(10,2) DEFAULT 0,
    
    -- Simülatör
    time_ftd                DECIMAL(10,2) DEFAULT 0,
    time_ffs                DECIMAL(10,2) DEFAULT 0,
    
    -- Son Uçuş
    last_flight_date        DATE,
    last_flight_id          UUID,
    
    -- Currency (Son 90 gün)
    landings_last_90_days   INTEGER DEFAULT 0,
    night_landings_last_90_days INTEGER DEFAULT 0,
    ifr_approaches_last_6_months INTEGER DEFAULT 0,
    
    -- Uçuş Sayısı
    total_flights           INTEGER DEFAULT 0,
    
    -- Uçak Tipleri (Her tip için süre)
    aircraft_type_times     JSONB DEFAULT '{}',
    -- {"C172": 150.5, "PA28": 45.0, "DA42": 20.0}
    
    -- Havalimanı ziyaretleri
    airports_visited        TEXT[],
    airports_visited_count  INTEGER DEFAULT 0,
    
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_pilot_logbook UNIQUE(organization_id, pilot_id)
);

CREATE INDEX idx_logbook_pilot ON pilot_logbook_summary(pilot_id);
```

### 2.3 Flight Crew Log (Her kişi için ayrı kayıt)

```sql
-- =============================================================================
-- FLIGHT_CREW_LOG (Mürettebat Uçuş Kaydı)
-- =============================================================================
CREATE TABLE flight_crew_log (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flight_id               UUID NOT NULL REFERENCES flights(id) ON DELETE CASCADE,
    organization_id         UUID NOT NULL,
    
    -- Kişi
    user_id                 UUID NOT NULL,
    role                    VARCHAR(50) NOT NULL,
    -- pic, sic, instructor, student, examiner
    
    -- Bu kişi için süreler
    flight_time             DECIMAL(5,2),
    time_pic                DECIMAL(5,2) DEFAULT 0,
    time_sic                DECIMAL(5,2) DEFAULT 0,
    time_dual_received      DECIMAL(5,2) DEFAULT 0,
    time_dual_given         DECIMAL(5,2) DEFAULT 0,
    time_solo               DECIMAL(5,2) DEFAULT 0,
    
    -- Koşullar
    time_day                DECIMAL(5,2) DEFAULT 0,
    time_night              DECIMAL(5,2) DEFAULT 0,
    time_ifr                DECIMAL(5,2) DEFAULT 0,
    time_cross_country      DECIMAL(5,2) DEFAULT 0,
    
    -- İnişler
    landings_day            INTEGER DEFAULT 0,
    landings_night          INTEGER DEFAULT 0,
    
    -- Approach
    approaches              INTEGER DEFAULT 0,
    
    -- İmza
    signature               JSONB,
    signed_at               TIMESTAMP,
    
    -- Notlar
    remarks                 TEXT,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_crew_log_flight ON flight_crew_log(flight_id);
CREATE INDEX idx_crew_log_user ON flight_crew_log(user_id, created_at);
```

---

## 3. DJANGO MODELS

```python
# apps/core/models/flight.py

import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from common.models import TenantModel


class Flight(TenantModel):
    """Uçuş kaydı modeli"""
    
    class FlightType(models.TextChoices):
        TRAINING = 'training', 'Eğitim'
        SOLO = 'solo', 'Solo'
        RENTAL = 'rental', 'Kiralama'
        CHARTER = 'charter', 'Charter'
        CHECK_RIDE = 'check_ride', 'Sınav Uçuşu'
        PROFICIENCY = 'proficiency', 'Yeterlilik'
    
    class FlightRules(models.TextChoices):
        VFR = 'VFR', 'VFR'
        IFR = 'IFR', 'IFR'
        SVFR = 'SVFR', 'Special VFR'
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Taslak'
        SUBMITTED = 'submitted', 'Gönderildi'
        PENDING_REVIEW = 'pending_review', 'İncelemede'
        APPROVED = 'approved', 'Onaylandı'
        REJECTED = 'rejected', 'Reddedildi'
        CANCELLED = 'cancelled', 'İptal'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_id = models.UUIDField(blank=True, null=True)
    aircraft_id = models.UUIDField(db_index=True)
    
    # Kişiler
    pic_id = models.UUIDField(db_index=True)
    sic_id = models.UUIDField(blank=True, null=True)
    instructor_id = models.UUIDField(blank=True, null=True, db_index=True)
    student_id = models.UUIDField(blank=True, null=True, db_index=True)
    
    pax_count = models.IntegerField(default=0)
    
    # Uçuş tarihi
    flight_date = models.DateField(db_index=True)
    
    # Rota
    departure_airport = models.CharField(max_length=4)
    arrival_airport = models.CharField(max_length=4)
    route = models.TextField(blank=True, null=True)
    
    # Zamanlar
    block_off = models.DateTimeField(blank=True, null=True)
    takeoff_time = models.DateTimeField(blank=True, null=True)
    landing_time = models.DateTimeField(blank=True, null=True)
    block_on = models.DateTimeField(blank=True, null=True)
    
    # Süreler
    block_time = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    flight_time = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    
    # Hobbs
    hobbs_start = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    hobbs_end = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    hobbs_time = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    
    # Sayaçlar
    landings_day = models.IntegerField(default=0)
    landings_night = models.IntegerField(default=0)
    full_stop_day = models.IntegerField(default=0)
    full_stop_night = models.IntegerField(default=0)
    
    # Uçuş tipleri
    time_day = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_night = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_ifr = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_cross_country = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Pilot fonksiyonu
    time_pic = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_sic = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_dual_received = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_dual_given = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_solo = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Approach
    approaches = models.JSONField(default=list)
    approach_count = models.IntegerField(default=0)
    
    # Yakıt
    fuel_used_liters = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    fuel_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Tip
    flight_type = models.CharField(
        max_length=50,
        choices=FlightType.choices,
        default=FlightType.TRAINING
    )
    flight_rules = models.CharField(
        max_length=10,
        choices=FlightRules.choices,
        default=FlightRules.VFR
    )
    
    # Eğitim
    lesson_id = models.UUIDField(blank=True, null=True)
    lesson_completed = models.BooleanField(default=False)
    
    # Durum
    flight_status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    # Onay
    approved_by = models.UUIDField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # İmzalar
    pic_signed_at = models.DateTimeField(blank=True, null=True)
    instructor_signed_at = models.DateTimeField(blank=True, null=True)
    student_signed_at = models.DateTimeField(blank=True, null=True)
    
    # Billing
    is_billed = models.BooleanField(default=False)
    total_charge = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Squawks
    has_squawks = models.BooleanField(default=False)
    
    # Notlar
    pilot_remarks = models.TextField(blank=True, null=True)
    instructor_remarks = models.TextField(blank=True, null=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField()
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'flights'
        ordering = ['-flight_date', '-block_off']
    
    def __str__(self):
        return f"{self.flight_date} {self.departure_airport}-{self.arrival_airport}"
    
    @property
    def total_landings(self):
        return self.landings_day + self.landings_night
    
    @property
    def duration_display(self):
        if self.flight_time:
            hours = int(self.flight_time)
            minutes = int((self.flight_time - hours) * 60)
            return f"{hours}:{minutes:02d}"
        return "0:00"
    
    def calculate_times(self):
        """Süreleri hesapla"""
        if self.block_off and self.block_on:
            diff = (self.block_on - self.block_off).total_seconds() / 3600
            self.block_time = Decimal(str(round(diff, 2)))
        
        if self.takeoff_time and self.landing_time:
            diff = (self.landing_time - self.takeoff_time).total_seconds() / 3600
            self.flight_time = Decimal(str(round(diff, 2)))
        
        if self.hobbs_start and self.hobbs_end:
            self.hobbs_time = self.hobbs_end - self.hobbs_start
    
    def submit(self):
        """Uçuşu onaya gönder"""
        self.calculate_times()
        self.flight_status = self.Status.SUBMITTED
        self.save()
    
    def approve(self, approver_id: uuid.UUID):
        """Uçuşu onayla"""
        self.flight_status = self.Status.APPROVED
        self.approved_by = approver_id
        self.approved_at = timezone.now()
        self.save()
    
    def reject(self, reason: str):
        """Uçuşu reddet"""
        self.flight_status = self.Status.REJECTED
        self.rejection_reason = reason
        self.save()


class PilotLogbookSummary(models.Model):
    """Pilot logbook özeti"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField()
    pilot_id = models.UUIDField(db_index=True)
    
    # Toplam süreler
    total_time = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_pic = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_sic = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_dual_received = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_dual_given = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_solo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Koşullar
    total_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_night = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_ifr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_cross_country = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Sayılar
    total_landings = models.IntegerField(default=0)
    total_landings_day = models.IntegerField(default=0)
    total_landings_night = models.IntegerField(default=0)
    total_approaches = models.IntegerField(default=0)
    total_flights = models.IntegerField(default=0)
    
    # Uçak kategorileri
    time_single_engine = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    time_multi_engine = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Son uçuş
    last_flight_date = models.DateField(blank=True, null=True)
    last_flight_id = models.UUIDField(blank=True, null=True)
    
    # Currency
    landings_last_90_days = models.IntegerField(default=0)
    night_landings_last_90_days = models.IntegerField(default=0)
    
    # Uçak tipleri
    aircraft_type_times = models.JSONField(default=dict)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pilot_logbook_summary'
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'pilot_id'],
                name='unique_pilot_logbook'
            )
        ]
    
    def __str__(self):
        return f"Logbook Summary: {self.pilot_id}"
```

---

## 4. API ENDPOINTS

```yaml
# =============================================================================
# FLIGHT API
# =============================================================================

# Flight CRUD
GET /api/v1/flights:
  summary: Uçuş listesi
  parameters:
    - name: start_date
    - name: end_date
    - name: aircraft_id
    - name: pilot_id
    - name: instructor_id
    - name: student_id
    - name: status

POST /api/v1/flights:
  summary: Uçuş kaydı oluştur

GET /api/v1/flights/{id}:
  summary: Uçuş detayı

PUT /api/v1/flights/{id}:
  summary: Uçuş güncelle

DELETE /api/v1/flights/{id}:
  summary: Uçuş sil (sadece draft)

# Workflow
POST /api/v1/flights/{id}/submit:
  summary: Onaya gönder

POST /api/v1/flights/{id}/approve:
  summary: Uçuşu onayla

POST /api/v1/flights/{id}/reject:
  summary: Uçuşu reddet
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

# Signatures
POST /api/v1/flights/{id}/sign:
  summary: Uçuşu imzala
  requestBody:
    content:
      application/json:
        schema:
          type: object
          required:
            - role
            - signature_data
          properties:
            role:
              type: string
              enum: [pic, instructor, student]
            signature_data:
              type: string
              description: Base64 encoded signature

# From Booking
POST /api/v1/flights/from-booking/{booking_id}:
  summary: Rezervasyondan uçuş oluştur

# Squawks
POST /api/v1/flights/{id}/squawks:
  summary: Uçuşa squawk ekle

# Logbook
GET /api/v1/flights/logbook:
  summary: Pilot logbook
  parameters:
    - name: pilot_id
    - name: start_date
    - name: end_date
    - name: format
      schema:
        type: string
        enum: [json, pdf, csv]

GET /api/v1/flights/logbook/summary:
  summary: Logbook özeti

GET /api/v1/flights/logbook/currency:
  summary: Currency durumu

# Statistics
GET /api/v1/flights/statistics:
  summary: Uçuş istatistikleri
  parameters:
    - name: pilot_id
    - name: period
      schema:
        type: string
        enum: [week, month, year, all]

GET /api/v1/flights/statistics/by-aircraft:
  summary: Uçak bazlı istatistikler

GET /api/v1/flights/statistics/by-airport:
  summary: Havalimanı bazlı istatistikler

# Recent
GET /api/v1/flights/recent:
  summary: Son uçuşlar

# Pending Approval
GET /api/v1/flights/pending-approval:
  summary: Onay bekleyen uçuşlar
```

---

## 5. SERVİS KATMANI

```python
# apps/core/services/flight_service.py

from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Count, F
from django.utils import timezone

from apps.core.models import Flight, PilotLogbookSummary, FlightCrewLog
from common.exceptions import ValidationError, NotFoundError
from common.events import EventBus
from common.clients import (
    AircraftServiceClient,
    BookingServiceClient,
    TrainingServiceClient,
    FinanceServiceClient
)


class FlightService:
    def __init__(self):
        self.event_bus = EventBus()
        self.aircraft_client = AircraftServiceClient()
        self.booking_client = BookingServiceClient()
        self.training_client = TrainingServiceClient()
        self.finance_client = FinanceServiceClient()
    
    @transaction.atomic
    async def create_flight(
        self,
        organization_id: str,
        user_id: str,
        aircraft_id: str,
        pic_id: str,
        flight_date: date,
        departure_airport: str,
        arrival_airport: str,
        **kwargs
    ) -> Flight:
        """Uçuş kaydı oluştur"""
        
        # Validasyonlar
        await self._validate_aircraft(aircraft_id)
        await self._validate_airports(departure_airport, arrival_airport)
        
        flight = await Flight.objects.acreate(
            organization_id=organization_id,
            aircraft_id=aircraft_id,
            pic_id=pic_id,
            flight_date=flight_date,
            departure_airport=departure_airport.upper(),
            arrival_airport=arrival_airport.upper(),
            created_by=user_id,
            **kwargs
        )
        
        return flight
    
    async def create_from_booking(
        self,
        booking_id: str,
        user_id: str,
        hobbs_start: Decimal = None,
        hobbs_end: Decimal = None,
        **kwargs
    ) -> Flight:
        """Rezervasyondan uçuş oluştur"""
        
        booking = await self.booking_client.get_booking(booking_id)
        
        if not booking:
            raise NotFoundError('Rezervasyon bulunamadı')
        
        flight = await self.create_flight(
            organization_id=booking['organization_id'],
            user_id=user_id,
            aircraft_id=booking['aircraft_id'],
            pic_id=booking.get('instructor_id') or booking.get('pilot_id'),
            flight_date=datetime.fromisoformat(booking['scheduled_start']).date(),
            departure_airport=booking.get('departure_airport', 'ZZZZ'),
            arrival_airport=booking.get('arrival_airport', 'ZZZZ'),
            booking_id=booking_id,
            instructor_id=booking.get('instructor_id'),
            student_id=booking.get('student_id'),
            lesson_id=booking.get('lesson_id'),
            block_off=booking.get('actual_start'),
            block_on=booking.get('actual_end'),
            hobbs_start=hobbs_start,
            hobbs_end=hobbs_end,
            **kwargs
        )
        
        # Booking'i complete yap
        await self.booking_client.complete_booking(booking_id, str(flight.id))
        
        return flight
    
    @transaction.atomic
    async def approve_flight(
        self,
        flight_id: str,
        approver_id: str
    ) -> Flight:
        """Uçuşu onayla"""
        
        flight = await Flight.objects.aget(id=flight_id)
        
        if flight.flight_status != Flight.Status.SUBMITTED:
            raise ValidationError('Sadece gönderilmiş uçuşlar onaylanabilir')
        
        # Süreleri hesapla
        flight.calculate_times()
        
        # Onayla
        flight.flight_status = Flight.Status.APPROVED
        flight.approved_by = approver_id
        flight.approved_at = timezone.now()
        await flight.asave()
        
        # Uçak sayaçlarını güncelle
        if flight.hobbs_time:
            await self.aircraft_client.update_counters(
                str(flight.aircraft_id),
                hobbs_change=float(flight.hobbs_time),
                landings=flight.total_landings
            )
        
        # Pilot logbook'u güncelle
        await self._update_pilot_logbook(flight)
        
        # Eğitim ilerlemesini güncelle
        if flight.student_id and flight.lesson_id:
            await self.training_client.record_flight_completion(
                str(flight.student_id),
                str(flight.lesson_id),
                str(flight.id),
                float(flight.flight_time or 0)
            )
        
        # Billing
        if not flight.is_billed:
            await self._calculate_and_charge(flight)
        
        # Event
        self.event_bus.publish('flight.approved', {
            'flight_id': str(flight.id),
            'aircraft_id': str(flight.aircraft_id),
            'flight_time': float(flight.flight_time or 0),
            'approved_by': approver_id
        })
        
        return flight
    
    async def get_logbook(
        self,
        pilot_id: str,
        organization_id: str = None,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Pilot logbook'unu getir"""
        
        query = Flight.objects.filter(
            flight_status=Flight.Status.APPROVED
        ).filter(
            models.Q(pic_id=pilot_id) |
            models.Q(sic_id=pilot_id) |
            models.Q(student_id=pilot_id)
        )
        
        if organization_id:
            query = query.filter(organization_id=organization_id)
        
        if start_date:
            query = query.filter(flight_date__gte=start_date)
        
        if end_date:
            query = query.filter(flight_date__lte=end_date)
        
        query = query.order_by('-flight_date', '-block_off')
        
        entries = []
        async for flight in query:
            entries.append(self._format_logbook_entry(flight, pilot_id))
        
        return entries
    
    async def get_logbook_summary(
        self,
        pilot_id: str,
        organization_id: str = None
    ) -> Dict[str, Any]:
        """Logbook özetini getir"""
        
        summary, _ = await PilotLogbookSummary.objects.aget_or_create(
            pilot_id=pilot_id,
            organization_id=organization_id or 'all',
            defaults={}
        )
        
        return {
            'total_time': float(summary.total_time),
            'total_pic': float(summary.total_pic),
            'total_sic': float(summary.total_sic),
            'total_dual_received': float(summary.total_dual_received),
            'total_dual_given': float(summary.total_dual_given),
            'total_solo': float(summary.total_solo),
            'total_day': float(summary.total_day),
            'total_night': float(summary.total_night),
            'total_ifr': float(summary.total_ifr),
            'total_cross_country': float(summary.total_cross_country),
            'total_landings': summary.total_landings,
            'total_landings_day': summary.total_landings_day,
            'total_landings_night': summary.total_landings_night,
            'total_approaches': summary.total_approaches,
            'total_flights': summary.total_flights,
            'time_single_engine': float(summary.time_single_engine),
            'time_multi_engine': float(summary.time_multi_engine),
            'last_flight_date': summary.last_flight_date.isoformat() if summary.last_flight_date else None,
            'aircraft_type_times': summary.aircraft_type_times
        }
    
    async def get_currency_status(
        self,
        pilot_id: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """Currency durumunu getir"""
        
        summary = await PilotLogbookSummary.objects.filter(
            pilot_id=pilot_id,
            organization_id=organization_id
        ).afirst()
        
        if not summary:
            return {
                'is_current': False,
                'issues': ['Uçuş kaydı bulunamadı']
            }
        
        issues = []
        warnings = []
        
        # Day currency (3 landings in 90 days)
        if summary.landings_last_90_days < 3:
            issues.append({
                'type': 'day_currency',
                'message': f'Son 90 günde {summary.landings_last_90_days}/3 gündüz inişi',
                'severity': 'error'
            })
        elif summary.landings_last_90_days < 6:
            warnings.append({
                'type': 'day_currency',
                'message': f'Son 90 günde {summary.landings_last_90_days} gündüz inişi (minimum 3)',
                'severity': 'warning'
            })
        
        # Night currency (3 night landings in 90 days for night pax)
        if summary.night_landings_last_90_days < 3:
            issues.append({
                'type': 'night_currency',
                'message': f'Son 90 günde {summary.night_landings_last_90_days}/3 gece inişi',
                'severity': 'warning'  # Yolcu taşımak için
            })
        
        # IFR currency (6 approaches in 6 months)
        if summary.ifr_approaches_last_6_months < 6:
            issues.append({
                'type': 'ifr_currency',
                'message': f'Son 6 ayda {summary.ifr_approaches_last_6_months}/6 IFR approach',
                'severity': 'warning'
            })
        
        return {
            'is_current': len([i for i in issues if i['severity'] == 'error']) == 0,
            'issues': issues,
            'warnings': warnings,
            'last_flight': summary.last_flight_date.isoformat() if summary.last_flight_date else None,
            'landings_90_days': summary.landings_last_90_days,
            'night_landings_90_days': summary.night_landings_last_90_days
        }
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    async def _update_pilot_logbook(self, flight: Flight):
        """Pilot logbook özetini güncelle"""
        
        # PIC için
        await self._update_summary_for_pilot(
            flight.pic_id,
            flight.organization_id,
            flight,
            'pic'
        )
        
        # Student için
        if flight.student_id:
            await self._update_summary_for_pilot(
                flight.student_id,
                flight.organization_id,
                flight,
                'student'
            )
        
        # Instructor için
        if flight.instructor_id:
            await self._update_summary_for_pilot(
                flight.instructor_id,
                flight.organization_id,
                flight,
                'instructor'
            )
    
    async def _update_summary_for_pilot(
        self,
        pilot_id: str,
        organization_id: str,
        flight: Flight,
        role: str
    ):
        """Belirli pilot için özet güncelle"""
        
        summary, _ = await PilotLogbookSummary.objects.aget_or_create(
            pilot_id=pilot_id,
            organization_id=organization_id,
            defaults={}
        )
        
        # Süreleri ekle
        summary.total_time += flight.flight_time or Decimal('0')
        summary.total_flights += 1
        summary.last_flight_date = flight.flight_date
        summary.last_flight_id = flight.id
        
        if role == 'pic':
            summary.total_pic += flight.time_pic or Decimal('0')
        elif role == 'student':
            summary.total_dual_received += flight.time_dual_received or Decimal('0')
            summary.total_solo += flight.time_solo or Decimal('0')
        elif role == 'instructor':
            summary.total_dual_given += flight.time_dual_given or Decimal('0')
        
        summary.total_day += flight.time_day or Decimal('0')
        summary.total_night += flight.time_night or Decimal('0')
        summary.total_ifr += flight.time_ifr or Decimal('0')
        summary.total_cross_country += flight.time_cross_country or Decimal('0')
        
        summary.total_landings += flight.total_landings
        summary.total_landings_day += flight.landings_day
        summary.total_landings_night += flight.landings_night
        summary.total_approaches += flight.approach_count
        
        # Currency güncelle
        await self._update_currency_counts(summary, pilot_id, organization_id)
        
        await summary.asave()
    
    async def _calculate_and_charge(self, flight: Flight):
        """Ücret hesapla ve tahsil et"""
        
        # Uçak ücreti
        aircraft = await self.aircraft_client.get_aircraft(str(flight.aircraft_id))
        hourly_rate = Decimal(str(aircraft.get('hourly_rate_wet', 0)))
        
        flight_hours = flight.hobbs_time or flight.flight_time or Decimal('0')
        aircraft_charge = hourly_rate * flight_hours
        
        # Eğitmen ücreti (varsa)
        instructor_charge = Decimal('0')
        if flight.instructor_id:
            instructor_rate = Decimal('50')  # Varsayılan, ayarlardan alınmalı
            instructor_charge = instructor_rate * (flight.time_dual_given or flight_hours)
        
        # Toplam
        total_charge = aircraft_charge + instructor_charge + (flight.fuel_cost or Decimal('0'))
        
        flight.aircraft_charge = aircraft_charge
        flight.instructor_charge = instructor_charge
        flight.total_charge = total_charge
        flight.billing_status = 'calculated'
        await flight.asave()
        
        # Finans servisine gönder
        payer_id = flight.student_id or flight.pic_id
        await self.finance_client.charge_flight(
            flight.organization_id,
            str(payer_id),
            str(flight.id),
            float(total_charge)
        )
        
        flight.is_billed = True
        flight.billing_status = 'invoiced'
        await flight.asave()
    
    def _format_logbook_entry(self, flight: Flight, pilot_id: str) -> Dict[str, Any]:
        """Logbook girişini formatla"""
        return {
            'id': str(flight.id),
            'date': flight.flight_date.isoformat(),
            'aircraft_id': str(flight.aircraft_id),
            'departure': flight.departure_airport,
            'arrival': flight.arrival_airport,
            'route': flight.route,
            'block_off': flight.block_off.isoformat() if flight.block_off else None,
            'block_on': flight.block_on.isoformat() if flight.block_on else None,
            'flight_time': float(flight.flight_time) if flight.flight_time else 0,
            'landings_day': flight.landings_day,
            'landings_night': flight.landings_night,
            'time_pic': float(flight.time_pic),
            'time_sic': float(flight.time_sic),
            'time_dual_received': float(flight.time_dual_received),
            'time_dual_given': float(flight.time_dual_given),
            'time_solo': float(flight.time_solo),
            'time_night': float(flight.time_night),
            'time_ifr': float(flight.time_ifr),
            'time_cross_country': float(flight.time_cross_country),
            'approaches': flight.approach_count,
            'remarks': flight.pilot_remarks
        }
```

---

## 6. EVENTS

```python
# Flight Service Events

FLIGHT_CREATED = 'flight.created'
FLIGHT_UPDATED = 'flight.updated'
FLIGHT_SUBMITTED = 'flight.submitted'
FLIGHT_APPROVED = 'flight.approved'
FLIGHT_REJECTED = 'flight.rejected'

# Consumed Events
BOOKING_COMPLETED = 'booking.completed'
# Handler: Otomatik uçuş kaydı oluştur (opsiyonel)
```

---

Bu doküman Flight Service'in tüm detaylarını içermektedir.