# 📅 MODÜL 06: REZERVASYON SERVİSİ (Booking Service)

## 1. GENEL BAKIŞ

### 1.1 Servis Bilgileri

| Özellik | Değer |
|---------|-------|
| Servis Adı | booking-service |
| Port | 8005 |
| Veritabanı | booking_db |
| Prefix | /api/v1/bookings |

### 1.2 Sorumluluklar

- Uçak ve eğitmen rezervasyonları
- Takvim yönetimi
- Çakışma kontrolü
- Müsaitlik yönetimi
- Rezervasyon kuralları
- Check-in/Check-out işlemleri
- Bekleme listesi yönetimi

---

## 2. VERİTABANI ŞEMASI

### 2.1 Bookings Tablosu

```sql
-- =============================================================================
-- BOOKINGS (Rezervasyonlar)
-- =============================================================================
CREATE TABLE bookings (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Rezervasyon Numarası
    booking_number          VARCHAR(20) NOT NULL,
    
    -- Tip
    booking_type            VARCHAR(50) NOT NULL DEFAULT 'flight',
    -- flight, simulator, ground_training, maintenance, other
    
    -- Kaynaklar
    aircraft_id             UUID,
    simulator_id            UUID,
    instructor_id           UUID,
    student_id              UUID,
    pilot_id                UUID,  -- Solo/Rental uçuşlar için
    
    -- Lokasyon
    location_id             UUID NOT NULL,
    departure_airport       CHAR(4),
    arrival_airport         CHAR(4),
    
    -- Zaman
    scheduled_start         TIMESTAMP NOT NULL,
    scheduled_end           TIMESTAMP NOT NULL,
    actual_start            TIMESTAMP,
    actual_end              TIMESTAMP,
    
    -- Süre (dakika)
    scheduled_duration      INTEGER NOT NULL,
    actual_duration         INTEGER,
    
    -- Buffer
    preflight_minutes       INTEGER DEFAULT 30,
    postflight_minutes      INTEGER DEFAULT 30,
    block_start             TIMESTAMP,  -- scheduled_start - preflight
    block_end               TIMESTAMP,  -- scheduled_end + postflight
    
    -- Eğitim Bilgisi
    lesson_id               UUID,
    exercise_ids            UUID[],
    training_type           VARCHAR(50),
    -- dual, solo, solo_supervised, check_ride, stage_check
    
    -- Açıklama
    title                   VARCHAR(255),
    description             TEXT,
    route                   TEXT,
    objectives              TEXT,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'scheduled',
    -- draft, pending_approval, scheduled, confirmed, checked_in,
    -- in_progress, completed, cancelled, no_show
    
    -- İptal
    cancelled_at            TIMESTAMP,
    cancelled_by            UUID,
    cancellation_reason     TEXT,
    cancellation_type       VARCHAR(20),
    -- pilot_request, instructor_request, weather, maintenance, other
    
    is_late_cancellation    BOOLEAN DEFAULT false,
    cancellation_fee        DECIMAL(10,2),
    
    -- Onay
    requires_approval       BOOLEAN DEFAULT false,
    approved_by             UUID,
    approved_at             TIMESTAMP,
    rejection_reason        TEXT,
    
    -- Check-in/Check-out
    checked_in_at           TIMESTAMP,
    checked_in_by           UUID,
    checked_out_at          TIMESTAMP,
    checked_out_by          UUID,
    
    -- Dispatch
    dispatched_by           UUID,
    dispatched_at           TIMESTAMP,
    dispatch_notes          TEXT,
    
    -- Hava Durumu
    weather_briefing_done   BOOLEAN DEFAULT false,
    weather_briefing_at     TIMESTAMP,
    
    -- Risk Değerlendirmesi
    risk_assessment_done    BOOLEAN DEFAULT false,
    risk_score              INTEGER,
    risk_factors            JSONB DEFAULT '[]',
    
    -- Önkoşul Kontrolleri
    prerequisites_checked   BOOLEAN DEFAULT false,
    prerequisites_met       BOOLEAN DEFAULT false,
    prerequisite_issues     JSONB DEFAULT '[]',
    
    -- İlgili Kayıtlar
    flight_id               UUID,  -- Oluşturulan uçuş kaydı
    
    -- Tekrarlama
    is_recurring            BOOLEAN DEFAULT false,
    recurring_pattern_id    UUID,
    recurrence_parent_id    UUID,
    
    -- Fiyatlandırma
    estimated_cost          DECIMAL(10,2),
    actual_cost             DECIMAL(10,2),
    payment_status          VARCHAR(20) DEFAULT 'pending',
    -- pending, prepaid, charged, refunded
    
    -- Notlar
    pilot_notes             TEXT,
    instructor_notes        TEXT,
    internal_notes          TEXT,
    
    -- Metadata
    metadata                JSONB DEFAULT '{}',
    tags                    TEXT[],
    
    -- Audit
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID NOT NULL,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by              UUID,
    
    CONSTRAINT valid_booking_times CHECK (scheduled_end > scheduled_start),
    CONSTRAINT valid_block_times CHECK (block_end > block_start)
);

-- Indexes
CREATE INDEX idx_bookings_org ON bookings(organization_id);
CREATE INDEX idx_bookings_number ON bookings(booking_number);
CREATE INDEX idx_bookings_aircraft ON bookings(aircraft_id, scheduled_start);
CREATE INDEX idx_bookings_instructor ON bookings(instructor_id, scheduled_start);
CREATE INDEX idx_bookings_student ON bookings(student_id, scheduled_start);
CREATE INDEX idx_bookings_pilot ON bookings(pilot_id, scheduled_start);
CREATE INDEX idx_bookings_location ON bookings(location_id, scheduled_start);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_bookings_date_range ON bookings(scheduled_start, scheduled_end);
CREATE INDEX idx_bookings_block_range ON bookings(block_start, block_end);

-- Çakışma kontrolü için partial index
CREATE INDEX idx_bookings_active ON bookings(aircraft_id, block_start, block_end)
    WHERE status NOT IN ('cancelled', 'no_show', 'draft');
```

### 2.2 Recurring Patterns (Tekrarlama Kalıpları)

```sql
-- =============================================================================
-- RECURRING_PATTERNS (Tekrarlama Kalıpları)
-- =============================================================================
CREATE TABLE recurring_patterns (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Temel Rezervasyon Bilgisi
    booking_template        JSONB NOT NULL,
    
    -- Tekrarlama Kuralı
    frequency               VARCHAR(20) NOT NULL,
    -- daily, weekly, biweekly, monthly
    
    days_of_week            INTEGER[],  -- 0=Sunday, 1=Monday, etc.
    day_of_month            INTEGER,
    
    -- Başlangıç/Bitiş
    start_date              DATE NOT NULL,
    end_date                DATE,
    occurrence_count        INTEGER,
    
    -- Zaman
    start_time              TIME NOT NULL,
    duration_minutes        INTEGER NOT NULL,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'active',
    -- active, paused, completed, cancelled
    
    -- Oluşturulan Rezervasyonlar
    created_bookings_count  INTEGER DEFAULT 0,
    next_occurrence_date    DATE,
    last_created_date       DATE,
    
    -- Audit
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID NOT NULL
);
```

### 2.3 Availability (Müsaitlik)

```sql
-- =============================================================================
-- AVAILABILITY (Müsaitlik Tanımları)
-- =============================================================================
CREATE TABLE availability (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Kaynak
    resource_type           VARCHAR(20) NOT NULL,
    -- instructor, aircraft, simulator, location
    resource_id             UUID NOT NULL,
    
    -- Tip
    availability_type       VARCHAR(20) NOT NULL,
    -- available, unavailable, limited
    
    -- Zaman
    start_datetime          TIMESTAMP NOT NULL,
    end_datetime            TIMESTAMP NOT NULL,
    
    -- Tekrarlama (Opsiyonel)
    is_recurring            BOOLEAN DEFAULT false,
    recurrence_rule         VARCHAR(255),  -- RRULE format
    
    -- Detaylar
    reason                  VARCHAR(255),
    notes                   TEXT,
    
    -- Rezervasyon Sınırlamaları
    max_bookings            INTEGER,  -- Bu sürede max rezervasyon
    booking_types_allowed   TEXT[],   -- Sadece belirli tipler
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID
);

CREATE INDEX idx_availability_resource ON availability(resource_type, resource_id);
CREATE INDEX idx_availability_time ON availability(start_datetime, end_datetime);
```

### 2.4 Booking Rules (Rezervasyon Kuralları)

```sql
-- =============================================================================
-- BOOKING_RULES (Rezervasyon Kuralları)
-- =============================================================================
CREATE TABLE booking_rules (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Kapsam
    rule_type               VARCHAR(50) NOT NULL,
    -- global, aircraft, instructor, student, location
    
    target_id               UUID,  -- NULL ise genel kural
    
    -- Zaman Sınırlamaları
    min_booking_duration    INTEGER,  -- dakika
    max_booking_duration    INTEGER,
    min_notice_hours        INTEGER,  -- En az kaç saat önceden
    max_advance_days        INTEGER,  -- En fazla kaç gün sonrası
    
    -- Günlük/Haftalık Limitler
    max_daily_hours         DECIMAL(4,2),
    max_weekly_hours        DECIMAL(5,2),
    max_daily_bookings      INTEGER,
    max_concurrent_bookings INTEGER,
    
    -- Çalışma Saatleri
    operating_hours         JSONB,
    -- {"monday": {"start": "08:00", "end": "20:00"}, ...}
    
    -- Buffer Kuralları
    required_buffer_minutes INTEGER,
    
    -- Yetki
    who_can_book            TEXT[],  -- role codes
    requires_approval_from  TEXT[],  -- role codes
    
    -- Ön Koşullar
    required_qualifications JSONB DEFAULT '[]',
    required_currency       JSONB DEFAULT '[]',
    
    -- Finansal
    require_positive_balance BOOLEAN DEFAULT true,
    minimum_balance         DECIMAL(10,2),
    
    -- İptal Kuralları
    free_cancellation_hours INTEGER DEFAULT 24,
    late_cancellation_fee_percent DECIMAL(5,2),
    no_show_fee_percent     DECIMAL(5,2) DEFAULT 100,
    
    -- Durum
    is_active               BOOLEAN DEFAULT true,
    priority                INTEGER DEFAULT 0,  -- Yüksek = öncelikli
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.5 Waitlist (Bekleme Listesi)

```sql
-- =============================================================================
-- WAITLIST (Bekleme Listesi)
-- =============================================================================
CREATE TABLE waitlist (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- İsteyen
    user_id                 UUID NOT NULL,
    
    -- İstek Detayları
    requested_date          DATE NOT NULL,
    preferred_start_time    TIME,
    preferred_end_time      TIME,
    
    aircraft_id             UUID,
    instructor_id           UUID,
    location_id             UUID,
    
    booking_type            VARCHAR(50),
    duration_minutes        INTEGER,
    
    -- Esneklik
    flexibility_days        INTEGER DEFAULT 0,  -- Kaç gün esnek
    flexibility_hours       INTEGER DEFAULT 0,  -- Kaç saat esnek
    any_aircraft            BOOLEAN DEFAULT false,
    any_instructor          BOOLEAN DEFAULT false,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'waiting',
    -- waiting, offered, accepted, expired, cancelled
    
    -- Teklif
    offered_booking_id      UUID,
    offered_at              TIMESTAMP,
    offer_expires_at        TIMESTAMP,
    
    -- Notlar
    notes                   TEXT,
    
    -- Öncelik
    priority                INTEGER DEFAULT 0,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at              TIMESTAMP
);

CREATE INDEX idx_waitlist_date ON waitlist(requested_date);
CREATE INDEX idx_waitlist_status ON waitlist(status);
```

---

## 3. DJANGO MODELS

```python
# apps/core/models/booking.py

import uuid
from datetime import datetime, timedelta
from django.db import models
from django.utils import timezone
from common.models import TenantModel


class Booking(TenantModel):
    """Rezervasyon modeli"""
    
    class BookingType(models.TextChoices):
        FLIGHT = 'flight', 'Uçuş'
        SIMULATOR = 'simulator', 'Simülatör'
        GROUND_TRAINING = 'ground_training', 'Yer Eğitimi'
        MAINTENANCE = 'maintenance', 'Bakım'
        OTHER = 'other', 'Diğer'
    
    class TrainingType(models.TextChoices):
        DUAL = 'dual', 'Dual (Eğitmenli)'
        SOLO = 'solo', 'Solo'
        SOLO_SUPERVISED = 'solo_supervised', 'Solo (Gözetimli)'
        CHECK_RIDE = 'check_ride', 'Sınav Uçuşu'
        STAGE_CHECK = 'stage_check', 'Kademe Kontrolü'
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Taslak'
        PENDING_APPROVAL = 'pending_approval', 'Onay Bekliyor'
        SCHEDULED = 'scheduled', 'Planlandı'
        CONFIRMED = 'confirmed', 'Onaylandı'
        CHECKED_IN = 'checked_in', 'Check-in Yapıldı'
        IN_PROGRESS = 'in_progress', 'Devam Ediyor'
        COMPLETED = 'completed', 'Tamamlandı'
        CANCELLED = 'cancelled', 'İptal Edildi'
        NO_SHOW = 'no_show', 'Gelmedi'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_number = models.CharField(max_length=20, unique=True)
    
    booking_type = models.CharField(
        max_length=50,
        choices=BookingType.choices,
        default=BookingType.FLIGHT
    )
    
    # Kaynaklar
    aircraft_id = models.UUIDField(blank=True, null=True, db_index=True)
    instructor_id = models.UUIDField(blank=True, null=True, db_index=True)
    student_id = models.UUIDField(blank=True, null=True, db_index=True)
    pilot_id = models.UUIDField(blank=True, null=True)
    
    # Lokasyon
    location_id = models.UUIDField(db_index=True)
    departure_airport = models.CharField(max_length=4, blank=True, null=True)
    arrival_airport = models.CharField(max_length=4, blank=True, null=True)
    
    # Zaman
    scheduled_start = models.DateTimeField(db_index=True)
    scheduled_end = models.DateTimeField()
    actual_start = models.DateTimeField(blank=True, null=True)
    actual_end = models.DateTimeField(blank=True, null=True)
    
    scheduled_duration = models.IntegerField()  # dakika
    
    # Buffer
    preflight_minutes = models.IntegerField(default=30)
    postflight_minutes = models.IntegerField(default=30)
    block_start = models.DateTimeField()
    block_end = models.DateTimeField()
    
    # Eğitim
    lesson_id = models.UUIDField(blank=True, null=True)
    training_type = models.CharField(
        max_length=50,
        choices=TrainingType.choices,
        blank=True,
        null=True
    )
    
    # Açıklama
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    route = models.TextField(blank=True, null=True)
    
    # Durum
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    
    # İptal
    cancelled_at = models.DateTimeField(blank=True, null=True)
    cancelled_by = models.UUIDField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    is_late_cancellation = models.BooleanField(default=False)
    cancellation_fee = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    
    # Check-in
    checked_in_at = models.DateTimeField(blank=True, null=True)
    checked_in_by = models.UUIDField(blank=True, null=True)
    
    # İlişkili uçuş
    flight_id = models.UUIDField(blank=True, null=True)
    
    # Fiyatlandırma
    estimated_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    
    # Notlar
    pilot_notes = models.TextField(blank=True, null=True)
    instructor_notes = models.TextField(blank=True, null=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField()
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bookings'
        ordering = ['scheduled_start']
    
    def __str__(self):
        return f"{self.booking_number}: {self.scheduled_start.strftime('%Y-%m-%d %H:%M')}"
    
    def save(self, *args, **kwargs):
        # Booking numarası oluştur
        if not self.booking_number:
            date_str = timezone.now().strftime('%Y%m%d')
            count = Booking.objects.filter(
                organization_id=self.organization_id,
                created_at__date=timezone.now().date()
            ).count() + 1
            self.booking_number = f"BK-{date_str}-{count:04d}"
        
        # Block times hesapla
        if self.scheduled_start and not self.block_start:
            self.block_start = self.scheduled_start - timedelta(
                minutes=self.preflight_minutes
            )
        if self.scheduled_end and not self.block_end:
            self.block_end = self.scheduled_end + timedelta(
                minutes=self.postflight_minutes
            )
        
        super().save(*args, **kwargs)
    
    @property
    def duration_hours(self):
        return self.scheduled_duration / 60
    
    @property
    def is_past(self):
        return self.scheduled_end < timezone.now()
    
    @property
    def is_today(self):
        return self.scheduled_start.date() == timezone.now().date()
    
    @property
    def can_cancel(self):
        return self.status in [
            self.Status.SCHEDULED,
            self.Status.CONFIRMED,
            self.Status.PENDING_APPROVAL
        ]
    
    @property
    def can_check_in(self):
        if self.status != self.Status.CONFIRMED:
            return False
        # 2 saat öncesinden itibaren check-in yapılabilir
        check_in_window = self.scheduled_start - timedelta(hours=2)
        return timezone.now() >= check_in_window
    
    def check_in(self, user_id: uuid.UUID):
        """Check-in yap"""
        self.status = self.Status.CHECKED_IN
        self.checked_in_at = timezone.now()
        self.checked_in_by = user_id
        self.save()
    
    def start(self):
        """Rezervasyonu başlat"""
        self.status = self.Status.IN_PROGRESS
        self.actual_start = timezone.now()
        self.save()
    
    def complete(self, flight_id: uuid.UUID = None):
        """Rezervasyonu tamamla"""
        self.status = self.Status.COMPLETED
        self.actual_end = timezone.now()
        if flight_id:
            self.flight_id = flight_id
        self.save()
    
    def cancel(self, user_id: uuid.UUID, reason: str):
        """Rezervasyonu iptal et"""
        self.status = self.Status.CANCELLED
        self.cancelled_at = timezone.now()
        self.cancelled_by = user_id
        self.cancellation_reason = reason
        
        # Geç iptal kontrolü
        hours_until = (self.scheduled_start - timezone.now()).total_seconds() / 3600
        if hours_until < 24:  # Organizasyon ayarlarından alınmalı
            self.is_late_cancellation = True
        
        self.save()
```

---

## 4. API ENDPOINTS

```yaml
# =============================================================================
# BOOKING API
# =============================================================================

# Booking CRUD
GET /api/v1/bookings:
  summary: Rezervasyon listesi
  parameters:
    - name: start_date
      in: query
      schema:
        type: string
        format: date
    - name: end_date
      in: query
      schema:
        type: string
        format: date
    - name: aircraft_id
      in: query
    - name: instructor_id
      in: query
    - name: student_id
      in: query
    - name: status
      in: query
    - name: location_id
      in: query

POST /api/v1/bookings:
  summary: Rezervasyon oluştur
  requestBody:
    content:
      application/json:
        schema:
          type: object
          required:
            - booking_type
            - scheduled_start
            - scheduled_end
            - location_id
          properties:
            booking_type:
              type: string
            aircraft_id:
              type: string
            instructor_id:
              type: string
            student_id:
              type: string
            scheduled_start:
              type: string
              format: date-time
            scheduled_end:
              type: string
              format: date-time
            location_id:
              type: string
            training_type:
              type: string
            lesson_id:
              type: string
            description:
              type: string
            route:
              type: string

GET /api/v1/bookings/{id}:
  summary: Rezervasyon detayı

PUT /api/v1/bookings/{id}:
  summary: Rezervasyon güncelle

DELETE /api/v1/bookings/{id}:
  summary: Rezervasyon sil (sadece draft)

# Status Actions
POST /api/v1/bookings/{id}/confirm:
  summary: Rezervasyonu onayla

POST /api/v1/bookings/{id}/cancel:
  summary: Rezervasyonu iptal et
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

POST /api/v1/bookings/{id}/check-in:
  summary: Check-in yap

POST /api/v1/bookings/{id}/dispatch:
  summary: Dispatch (uçuşa gönder)

POST /api/v1/bookings/{id}/complete:
  summary: Rezervasyonu tamamla

POST /api/v1/bookings/{id}/no-show:
  summary: No-show olarak işaretle

# Availability
GET /api/v1/bookings/availability:
  summary: Müsaitlik kontrolü
  parameters:
    - name: date
      required: true
    - name: aircraft_id
    - name: instructor_id
    - name: location_id

GET /api/v1/bookings/available-slots:
  summary: Müsait slotları getir
  parameters:
    - name: date
      required: true
    - name: aircraft_id
    - name: instructor_id
    - name: duration_minutes

POST /api/v1/bookings/check-conflicts:
  summary: Çakışma kontrolü
  requestBody:
    content:
      application/json:
        schema:
          type: object
          required:
            - start
            - end
          properties:
            start:
              type: string
            end:
              type: string
            aircraft_id:
              type: string
            instructor_id:
              type: string
            exclude_booking_id:
              type: string

# Calendar
GET /api/v1/bookings/calendar:
  summary: Takvim görünümü
  parameters:
    - name: view
      schema:
        type: string
        enum: [day, week, month]
    - name: date
    - name: resource_type
      schema:
        type: string
        enum: [aircraft, instructor]
    - name: resource_ids

# My Bookings
GET /api/v1/bookings/my:
  summary: Benim rezervasyonlarım

GET /api/v1/bookings/my/upcoming:
  summary: Yaklaşan rezervasyonlarım

GET /api/v1/bookings/my/history:
  summary: Geçmiş rezervasyonlarım

# Waitlist
POST /api/v1/bookings/waitlist:
  summary: Bekleme listesine ekle

GET /api/v1/bookings/waitlist/my:
  summary: Bekleme listesindeki isteklerim
```

---

## 5. SERVİS KATMANI

```python
# apps/core/services/booking_service.py

from typing import List, Dict, Any, Optional
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.models import Booking, BookingRule, Availability
from common.exceptions import ValidationError, ConflictError, NotFoundError
from common.events import EventBus
from common.clients import (
    AircraftServiceClient,
    UserServiceClient,
    TrainingServiceClient,
    FinanceServiceClient
)


class BookingService:
    def __init__(self):
        self.event_bus = EventBus()
        self.aircraft_client = AircraftServiceClient()
        self.user_client = UserServiceClient()
        self.training_client = TrainingServiceClient()
        self.finance_client = FinanceServiceClient()
    
    @transaction.atomic
    async def create_booking(
        self,
        organization_id: str,
        user_id: str,
        booking_type: str,
        scheduled_start: datetime,
        scheduled_end: datetime,
        location_id: str,
        aircraft_id: str = None,
        instructor_id: str = None,
        student_id: str = None,
        **kwargs
    ) -> Booking:
        """Rezervasyon oluştur"""
        
        # 1. Temel validasyonlar
        self._validate_times(scheduled_start, scheduled_end)
        
        # 2. Kuralları al
        rules = await self._get_applicable_rules(
            organization_id, aircraft_id, instructor_id
        )
        
        # 3. Kural kontrolü
        await self._check_booking_rules(
            organization_id, user_id, rules,
            scheduled_start, scheduled_end,
            aircraft_id, instructor_id, student_id
        )
        
        # 4. Çakışma kontrolü
        await self._check_conflicts(
            organization_id,
            scheduled_start, scheduled_end,
            aircraft_id, instructor_id
        )
        
        # 5. Ön koşul kontrolü (eğitim uçuşları için)
        if student_id and kwargs.get('lesson_id'):
            prereq_result = await self._check_prerequisites(
                student_id, kwargs['lesson_id']
            )
            if not prereq_result['met']:
                raise ValidationError(
                    f"Ön koşullar karşılanmadı: {prereq_result['issues']}"
                )
        
        # 6. Bakiye kontrolü
        if student_id or kwargs.get('pilot_id'):
            payer_id = student_id or kwargs.get('pilot_id')
            await self._check_balance(
                organization_id, payer_id, aircraft_id,
                (scheduled_end - scheduled_start).total_seconds() / 3600
            )
        
        # 7. Tahmini maliyet hesapla
        estimated_cost = await self._calculate_estimated_cost(
            aircraft_id, instructor_id,
            (scheduled_end - scheduled_start).total_seconds() / 3600
        )
        
        # 8. Rezervasyonu oluştur
        duration_minutes = int((scheduled_end - scheduled_start).total_seconds() / 60)
        
        booking = await Booking.objects.acreate(
            organization_id=organization_id,
            booking_type=booking_type,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            scheduled_duration=duration_minutes,
            location_id=location_id,
            aircraft_id=aircraft_id,
            instructor_id=instructor_id,
            student_id=student_id,
            estimated_cost=estimated_cost,
            created_by=user_id,
            **kwargs
        )
        
        # 9. Event yayınla
        self.event_bus.publish('booking.created', {
            'booking_id': str(booking.id),
            'organization_id': organization_id,
            'aircraft_id': aircraft_id,
            'instructor_id': instructor_id,
            'student_id': student_id,
            'scheduled_start': scheduled_start.isoformat()
        })
        
        return booking
    
    async def check_conflicts(
        self,
        organization_id: str,
        start: datetime,
        end: datetime,
        aircraft_id: str = None,
        instructor_id: str = None,
        exclude_booking_id: str = None
    ) -> List[Dict[str, Any]]:
        """Çakışma kontrolü"""
        
        conflicts = []
        
        # Uçak çakışması
        if aircraft_id:
            aircraft_conflicts = await self._get_resource_conflicts(
                organization_id, 'aircraft', aircraft_id,
                start, end, exclude_booking_id
            )
            conflicts.extend(aircraft_conflicts)
        
        # Eğitmen çakışması
        if instructor_id:
            instructor_conflicts = await self._get_resource_conflicts(
                organization_id, 'instructor', instructor_id,
                start, end, exclude_booking_id
            )
            conflicts.extend(instructor_conflicts)
        
        return conflicts
    
    async def get_available_slots(
        self,
        organization_id: str,
        date: date,
        duration_minutes: int,
        aircraft_id: str = None,
        instructor_id: str = None,
        location_id: str = None
    ) -> List[Dict[str, Any]]:
        """Müsait slotları getir"""
        
        # Çalışma saatlerini al
        operating_hours = await self._get_operating_hours(
            organization_id, location_id, date
        )
        
        if not operating_hours:
            return []
        
        start_time = operating_hours['start']
        end_time = operating_hours['end']
        
        # Mevcut rezervasyonları al
        existing = await self._get_bookings_for_date(
            organization_id, date, aircraft_id, instructor_id
        )
        
        # Bloklanmış zamanları hesapla
        blocked_times = []
        for booking in existing:
            blocked_times.append({
                'start': booking.block_start,
                'end': booking.block_end
            })
        
        # Müsait slotları hesapla
        slots = self._calculate_available_slots(
            date, start_time, end_time,
            blocked_times, duration_minutes
        )
        
        return slots
    
    async def cancel_booking(
        self,
        booking_id: str,
        user_id: str,
        reason: str
    ) -> Booking:
        """Rezervasyonu iptal et"""
        
        booking = await Booking.objects.aget(id=booking_id)
        
        if not booking.can_cancel:
            raise ValidationError('Bu rezervasyon iptal edilemez')
        
        # Geç iptal kontrolü
        hours_until = (booking.scheduled_start - timezone.now()).total_seconds() / 3600
        
        # Organizasyon kurallarını al
        rules = await self._get_applicable_rules(
            booking.organization_id, booking.aircraft_id
        )
        
        free_cancel_hours = 24  # Default
        late_cancel_fee_percent = 50
        
        for rule in rules:
            if rule.free_cancellation_hours:
                free_cancel_hours = rule.free_cancellation_hours
            if rule.late_cancellation_fee_percent:
                late_cancel_fee_percent = rule.late_cancellation_fee_percent
        
        cancellation_fee = None
        is_late = False
        
        if hours_until < free_cancel_hours:
            is_late = True
            if booking.estimated_cost:
                cancellation_fee = booking.estimated_cost * Decimal(str(late_cancel_fee_percent / 100))
        
        booking.status = Booking.Status.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.cancelled_by = user_id
        booking.cancellation_reason = reason
        booking.is_late_cancellation = is_late
        booking.cancellation_fee = cancellation_fee
        await booking.asave()
        
        # İptal ücreti varsa işle
        if cancellation_fee and cancellation_fee > 0:
            await self.finance_client.charge_cancellation_fee(
                booking.organization_id,
                booking.student_id or booking.pilot_id,
                cancellation_fee,
                str(booking.id)
            )
        
        # Event
        self.event_bus.publish('booking.cancelled', {
            'booking_id': str(booking.id),
            'cancelled_by': user_id,
            'is_late_cancellation': is_late,
            'cancellation_fee': float(cancellation_fee) if cancellation_fee else 0
        })
        
        # Bekleme listesini kontrol et
        await self._process_waitlist(booking)
        
        return booking
    
    async def dispatch(
        self,
        booking_id: str,
        dispatcher_id: str,
        notes: str = None
    ) -> Booking:
        """Dispatch - uçuşa gönder"""
        
        booking = await Booking.objects.aget(id=booking_id)
        
        if booking.status != Booking.Status.CHECKED_IN:
            raise ValidationError('Dispatch için önce check-in yapılmalı')
        
        # Son kontroller
        checks = await self._perform_dispatch_checks(booking)
        
        if not checks['passed']:
            raise ValidationError(
                f"Dispatch kontrolleri başarısız: {checks['failures']}"
            )
        
        booking.status = Booking.Status.IN_PROGRESS
        booking.actual_start = timezone.now()
        booking.dispatched_by = dispatcher_id
        booking.dispatched_at = timezone.now()
        booking.dispatch_notes = notes
        await booking.asave()
        
        # Event
        self.event_bus.publish('booking.dispatched', {
            'booking_id': str(booking.id),
            'aircraft_id': str(booking.aircraft_id),
            'dispatcher_id': dispatcher_id
        })
        
        return booking
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    def _validate_times(self, start: datetime, end: datetime):
        """Zaman validasyonu"""
        if end <= start:
            raise ValidationError('Bitiş zamanı başlangıçtan sonra olmalı')
        
        if start < timezone.now():
            raise ValidationError('Geçmiş zamana rezervasyon yapılamaz')
        
        duration = (end - start).total_seconds() / 60
        if duration < 30:
            raise ValidationError('Minimum süre 30 dakikadır')
        if duration > 480:
            raise ValidationError('Maksimum süre 8 saattir')
    
    async def _check_conflicts(
        self,
        organization_id: str,
        start: datetime,
        end: datetime,
        aircraft_id: str,
        instructor_id: str
    ):
        """Çakışma kontrolü"""
        conflicts = await self.check_conflicts(
            organization_id, start, end, aircraft_id, instructor_id
        )
        
        if conflicts:
            conflict_msgs = [c['message'] for c in conflicts]
            raise ConflictError(f"Çakışma tespit edildi: {', '.join(conflict_msgs)}")
    
    async def _get_resource_conflicts(
        self,
        organization_id: str,
        resource_type: str,
        resource_id: str,
        start: datetime,
        end: datetime,
        exclude_booking_id: str = None
    ) -> List[Dict[str, Any]]:
        """Kaynak çakışmalarını getir"""
        
        query = Booking.objects.filter(
            organization_id=organization_id,
            status__in=[
                Booking.Status.SCHEDULED,
                Booking.Status.CONFIRMED,
                Booking.Status.CHECKED_IN,
                Booking.Status.IN_PROGRESS
            ]
        ).filter(
            Q(block_start__lt=end) & Q(block_end__gt=start)
        )
        
        if resource_type == 'aircraft':
            query = query.filter(aircraft_id=resource_id)
        elif resource_type == 'instructor':
            query = query.filter(instructor_id=resource_id)
        
        if exclude_booking_id:
            query = query.exclude(id=exclude_booking_id)
        
        conflicts = []
        async for booking in query:
            conflicts.append({
                'booking_id': str(booking.id),
                'resource_type': resource_type,
                'resource_id': resource_id,
                'start': booking.block_start.isoformat(),
                'end': booking.block_end.isoformat(),
                'message': f"{resource_type.title()} bu saatlerde başka bir rezervasyonda"
            })
        
        return conflicts
    
    async def _perform_dispatch_checks(self, booking: Booking) -> Dict[str, Any]:
        """Dispatch öncesi kontroller"""
        failures = []
        
        # Uçak kontrolü
        if booking.aircraft_id:
            aircraft_status = await self.aircraft_client.get_status(
                str(booking.aircraft_id)
            )
            
            if not aircraft_status.get('is_available'):
                failures.append('Uçak müsait değil')
            
            if aircraft_status.get('blockers'):
                for blocker in aircraft_status['blockers']:
                    failures.append(blocker['message'])
        
        # Pilot/Öğrenci kontrolü
        pilot_id = booking.student_id or booking.pilot_id
        if pilot_id:
            # Bakiye kontrolü
            balance = await self.finance_client.get_balance(
                booking.organization_id, str(pilot_id)
            )
            if balance < 0:
                failures.append('Yetersiz bakiye')
            
            # Sertifika kontrolü
            certs = await self.user_client.get_valid_certificates(str(pilot_id))
            if not certs.get('medical_valid'):
                failures.append('Geçerli sağlık sertifikası yok')
        
        return {
            'passed': len(failures) == 0,
            'failures': failures
        }
    
    def _calculate_available_slots(
        self,
        date: date,
        start_time: time,
        end_time: time,
        blocked_times: List[Dict],
        duration_minutes: int
    ) -> List[Dict[str, Any]]:
        """Müsait slotları hesapla"""
        
        slots = []
        slot_duration = timedelta(minutes=duration_minutes)
        step = timedelta(minutes=30)  # 30 dakikalık adımlar
        
        current = datetime.combine(date, start_time)
        day_end = datetime.combine(date, end_time)
        
        while current + slot_duration <= day_end:
            slot_end = current + slot_duration
            
            # Bu slot bloklanmış mı kontrol et
            is_blocked = False
            for blocked in blocked_times:
                if current < blocked['end'] and slot_end > blocked['start']:
                    is_blocked = True
                    break
            
            if not is_blocked:
                slots.append({
                    'start': current.isoformat(),
                    'end': slot_end.isoformat(),
                    'duration_minutes': duration_minutes
                })
            
            current += step
        
        return slots
```

---

## 6. EVENTS

```python
# Booking Service Events

BOOKING_CREATED = 'booking.created'
BOOKING_UPDATED = 'booking.updated'
BOOKING_CANCELLED = 'booking.cancelled'
BOOKING_CONFIRMED = 'booking.confirmed'

BOOKING_CHECKED_IN = 'booking.checked_in'
BOOKING_DISPATCHED = 'booking.dispatched'
BOOKING_COMPLETED = 'booking.completed'
BOOKING_NO_SHOW = 'booking.no_show'

# Consumed Events
AIRCRAFT_STATUS_CHANGED = 'aircraft.status_changed'
# Handler: İlgili rezervasyonları kontrol et, gerekirse iptal et/bildirim gönder

MAINTENANCE_SCHEDULED = 'maintenance.scheduled'
# Handler: Çakışan rezervasyonları kontrol et
```

---

Bu doküman Booking Service'in tüm detaylarını içermektedir.