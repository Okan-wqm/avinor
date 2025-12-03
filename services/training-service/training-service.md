# 🎓 MODÜL 08: EĞİTİM SERVİSİ (Training Service)

## 1. GENEL BAKIŞ

### 1.1 Servis Bilgileri

| Özellik | Değer |
|---------|-------|
| Servis Adı | training-service |
| Port | 8007 |
| Veritabanı | training_db |
| Prefix | /api/v1/training |

### 1.2 Sorumluluklar

- Eğitim programları ve müfredat yönetimi
- Ders ve egzersiz tanımları
- Öğrenci ilerleme takibi
- Yetkinlik (competency) değerlendirmesi
- Kademe (stage) kontrolleri
- Eğitmen atamaları
- Syllabus yönetimi

---

## 2. VERİTABANI ŞEMASI

### 2.1 Training Programs (Eğitim Programları)

```sql
-- =============================================================================
-- TRAINING_PROGRAMS (Eğitim Programları)
-- =============================================================================
CREATE TABLE training_programs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Tanımlama
    code                    VARCHAR(50) NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    description             TEXT,
    
    -- Tip
    program_type            VARCHAR(50) NOT NULL,
    -- ppl, cpl, ir, me, fi, atp, type_rating, recurrent
    
    -- Düzenleyici
    regulatory_authority    VARCHAR(20),  -- EASA, FAA, SHGM
    approval_number         VARCHAR(100),
    approval_date           DATE,
    
    -- Gereksinimler
    min_hours_total         DECIMAL(6,2),
    min_hours_dual          DECIMAL(6,2),
    min_hours_solo          DECIMAL(6,2),
    min_hours_pic           DECIMAL(6,2),
    min_hours_cross_country DECIMAL(6,2),
    min_hours_night         DECIMAL(6,2),
    min_hours_instrument    DECIMAL(6,2),
    min_hours_simulator     DECIMAL(6,2),
    
    -- Ön Koşullar
    prerequisites           JSONB DEFAULT '[]',
    -- [{"type": "license", "value": "PPL"}, {"type": "hours", "value": 200}]
    
    min_age                 INTEGER,
    required_medical_class  INTEGER,  -- 1, 2, 3
    
    -- Süre
    estimated_duration_days INTEGER,
    max_duration_months     INTEGER,
    
    -- Fiyatlandırma
    base_price              DECIMAL(10,2),
    currency                CHAR(3) DEFAULT 'USD',
    
    -- İçerik
    syllabus_version        VARCHAR(50),
    syllabus_document_url   VARCHAR(500),
    
    -- Kademeler
    stages                  JSONB DEFAULT '[]',
    -- [{"id": "uuid", "name": "Pre-Solo", "order": 1}]
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'active',
    -- draft, active, deprecated, archived
    
    is_published            BOOLEAN DEFAULT false,
    
    -- Görsel
    thumbnail_url           VARCHAR(500),
    
    -- Metadata
    metadata                JSONB DEFAULT '{}',
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID
);

CREATE INDEX idx_programs_org ON training_programs(organization_id);
CREATE INDEX idx_programs_type ON training_programs(program_type);
CREATE INDEX idx_programs_status ON training_programs(status);
CREATE UNIQUE INDEX idx_programs_code ON training_programs(organization_id, code);
```

### 2.2 Syllabus Lessons (Dersler)

```sql
-- =============================================================================
-- SYLLABUS_LESSONS (Dersler)
-- =============================================================================
CREATE TABLE syllabus_lessons (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    program_id              UUID NOT NULL REFERENCES training_programs(id) ON DELETE CASCADE,
    
    -- Hiyerarşi
    stage_id                UUID,
    parent_lesson_id        UUID REFERENCES syllabus_lessons(id),
    
    -- Tanımlama
    code                    VARCHAR(50) NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    description             TEXT,
    objective               TEXT,
    
    -- Tip
    lesson_type             VARCHAR(50) NOT NULL,
    -- ground, flight, simulator, briefing, exam, stage_check
    
    -- Sıralama
    sort_order              INTEGER DEFAULT 0,
    
    -- Süre
    duration_hours          DECIMAL(4,2),
    ground_hours            DECIMAL(4,2),
    flight_hours            DECIMAL(4,2),
    simulator_hours         DECIMAL(4,2),
    
    -- Gereksinimler
    required_aircraft_type  VARCHAR(50),  -- single_engine, multi_engine
    required_conditions     TEXT[],  -- ["vfr", "day", "dual"]
    
    -- Ön Koşullar
    prerequisite_lessons    UUID[],
    prerequisite_hours      DECIMAL(6,2),
    prerequisite_conditions JSONB DEFAULT '[]',
    
    -- İçerik
    content                 TEXT,  -- Markdown
    resources               JSONB DEFAULT '[]',
    -- [{"type": "video", "url": "...", "title": "..."}]
    
    -- Değerlendirme
    grading_criteria        JSONB DEFAULT '[]',
    min_grade_to_pass       INTEGER DEFAULT 70,
    max_attempts            INTEGER,
    
    -- Tamamlama Kriterleri
    completion_criteria     JSONB DEFAULT '{}',
    -- {"min_grade": 70, "instructor_signoff": true}
    
    -- Egzersizler
    exercises               JSONB DEFAULT '[]',
    -- Ayrı tabloda da tutulabilir
    
    -- Notlar
    instructor_notes        TEXT,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'active',
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_lessons_program ON syllabus_lessons(program_id);
CREATE INDEX idx_lessons_stage ON syllabus_lessons(stage_id);
CREATE INDEX idx_lessons_order ON syllabus_lessons(program_id, sort_order);
```

### 2.3 Exercises (Egzersizler)

```sql
-- =============================================================================
-- EXERCISES (Egzersizler)
-- =============================================================================
CREATE TABLE exercises (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    lesson_id               UUID NOT NULL REFERENCES syllabus_lessons(id) ON DELETE CASCADE,
    
    -- Tanımlama
    code                    VARCHAR(50) NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    description             TEXT,
    
    -- Sıralama
    sort_order              INTEGER DEFAULT 0,
    
    -- ATO Reference (EASA vb.)
    ato_reference           VARCHAR(100),
    
    -- Değerlendirme Kriterleri
    competency_elements     JSONB DEFAULT '[]',
    -- [{"name": "Coordination", "weight": 20}, {"name": "Altitude Control", "weight": 30}]
    
    grading_scale           VARCHAR(20) DEFAULT 'numeric',
    -- numeric (1-100), letter (A-F), satisfactory (S/U), competency (1-4)
    
    -- Standartlar
    tolerances              JSONB DEFAULT '{}',
    -- {"altitude_ft": 100, "heading_deg": 10, "airspeed_kts": 5}
    
    -- Tamamlama
    min_demonstrations      INTEGER DEFAULT 1,
    min_grade               INTEGER,
    
    -- Kaynaklar
    resources               JSONB DEFAULT '[]',
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_exercises_lesson ON exercises(lesson_id);
```

### 2.4 Student Enrollments (Kayıtlar)

```sql
-- =============================================================================
-- STUDENT_ENROLLMENTS (Öğrenci Kayıtları)
-- =============================================================================
CREATE TABLE student_enrollments (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- İlişkiler
    student_id              UUID NOT NULL,
    program_id              UUID NOT NULL REFERENCES training_programs(id),
    
    -- Atanan Eğitmen
    primary_instructor_id   UUID,
    
    -- Tarihler
    enrollment_date         DATE NOT NULL,
    start_date              DATE,
    expected_completion     DATE,
    actual_completion       DATE,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'active',
    -- pending, active, on_hold, completed, withdrawn, expired
    
    hold_reason             TEXT,
    withdrawal_reason       TEXT,
    
    -- İlerleme
    current_stage_id        UUID,
    current_lesson_id       UUID,
    
    -- Toplam Saatler
    total_flight_hours      DECIMAL(6,2) DEFAULT 0,
    total_ground_hours      DECIMAL(6,2) DEFAULT 0,
    total_simulator_hours   DECIMAL(6,2) DEFAULT 0,
    
    -- Kategori Saatleri
    dual_hours              DECIMAL(6,2) DEFAULT 0,
    solo_hours              DECIMAL(6,2) DEFAULT 0,
    pic_hours               DECIMAL(6,2) DEFAULT 0,
    cross_country_hours     DECIMAL(6,2) DEFAULT 0,
    night_hours             DECIMAL(6,2) DEFAULT 0,
    instrument_hours        DECIMAL(6,2) DEFAULT 0,
    
    -- İstatistikler
    lessons_completed       INTEGER DEFAULT 0,
    lessons_total           INTEGER DEFAULT 0,
    completion_percentage   DECIMAL(5,2) DEFAULT 0,
    
    -- Finansal
    total_paid              DECIMAL(10,2) DEFAULT 0,
    total_charges           DECIMAL(10,2) DEFAULT 0,
    balance                 DECIMAL(10,2) DEFAULT 0,
    
    -- Notlar
    notes                   TEXT,
    
    -- Metadata
    metadata                JSONB DEFAULT '{}',
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_student_program UNIQUE(student_id, program_id)
);

CREATE INDEX idx_enrollments_student ON student_enrollments(student_id);
CREATE INDEX idx_enrollments_program ON student_enrollments(program_id);
CREATE INDEX idx_enrollments_instructor ON student_enrollments(primary_instructor_id);
CREATE INDEX idx_enrollments_status ON student_enrollments(status);
```

### 2.5 Lesson Completions (Ders Tamamlamaları)

```sql
-- =============================================================================
-- LESSON_COMPLETIONS (Ders Tamamlamaları)
-- =============================================================================
CREATE TABLE lesson_completions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- İlişkiler
    enrollment_id           UUID NOT NULL REFERENCES student_enrollments(id),
    lesson_id               UUID NOT NULL REFERENCES syllabus_lessons(id),
    student_id              UUID NOT NULL,
    instructor_id           UUID,
    
    -- İlgili Uçuş/Oturum
    flight_id               UUID,
    session_date            DATE NOT NULL,
    
    -- Süre
    ground_time             DECIMAL(4,2),
    flight_time             DECIMAL(4,2),
    simulator_time          DECIMAL(4,2),
    
    -- Deneme
    attempt_number          INTEGER DEFAULT 1,
    
    -- Değerlendirme
    grade                   INTEGER,  -- 0-100
    grade_letter            CHAR(2),
    status                  VARCHAR(20) DEFAULT 'in_progress',
    -- not_started, in_progress, completed, failed, deferred
    
    -- Egzersiz Değerlendirmeleri
    exercise_grades         JSONB DEFAULT '[]',
    -- [{"exercise_id": "uuid", "grade": 85, "notes": "..."}]
    
    -- Yetkinlik Değerlendirmesi
    competency_scores       JSONB DEFAULT '{}',
    -- {"situational_awareness": 4, "communication": 3}
    
    -- Tamamlama
    is_completed            BOOLEAN DEFAULT false,
    completed_at            TIMESTAMP,
    
    -- İmzalar
    student_signed_at       TIMESTAMP,
    instructor_signed_at    TIMESTAMP,
    
    -- Notlar
    instructor_comments     TEXT,
    student_comments        TEXT,
    areas_of_improvement    TEXT[],
    
    -- Sonraki Adımlar
    recommendations         TEXT,
    repeat_required         BOOLEAN DEFAULT false,
    repeat_items            TEXT[],
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_completions_enrollment ON lesson_completions(enrollment_id);
CREATE INDEX idx_completions_lesson ON lesson_completions(lesson_id);
CREATE INDEX idx_completions_student ON lesson_completions(student_id);
CREATE INDEX idx_completions_date ON lesson_completions(session_date);
```

### 2.6 Stage Checks (Kademe Kontrolleri)

```sql
-- =============================================================================
-- STAGE_CHECKS (Kademe Kontrolleri)
-- =============================================================================
CREATE TABLE stage_checks (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- İlişkiler
    enrollment_id           UUID NOT NULL REFERENCES student_enrollments(id),
    stage_id                UUID NOT NULL,
    student_id              UUID NOT NULL,
    examiner_id             UUID NOT NULL,  -- Check pilot
    
    -- Tarih
    scheduled_date          DATE,
    actual_date             DATE,
    
    -- İlgili Uçuş
    flight_id               UUID,
    
    -- Deneme
    attempt_number          INTEGER DEFAULT 1,
    
    -- Sonuç
    result                  VARCHAR(20),
    -- pass, fail, incomplete, deferred
    
    overall_grade           INTEGER,
    
    -- Detaylı Değerlendirme
    oral_grade              INTEGER,
    flight_grade            INTEGER,
    
    evaluation_items        JSONB DEFAULT '[]',
    -- [{"item": "Steep Turns", "grade": "S", "notes": "..."}]
    
    -- Gereksinimler Kontrolü
    requirements_met        JSONB DEFAULT '{}',
    -- {"min_hours": true, "solo_xc": true}
    
    -- Notlar
    examiner_comments       TEXT,
    areas_of_concern        TEXT[],
    recommendations         TEXT,
    
    -- Onay
    approved_for_next_stage BOOLEAN DEFAULT false,
    
    -- Dokümanlar
    documents               JSONB DEFAULT '[]',
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stage_checks_enrollment ON stage_checks(enrollment_id);
CREATE INDEX idx_stage_checks_student ON stage_checks(student_id);
```

---

## 3. DJANGO MODELS

```python
# apps/core/models/training.py

import uuid
from django.db import models
from common.models import TenantModel


class TrainingProgram(TenantModel):
    """Eğitim programı modeli"""
    
    class ProgramType(models.TextChoices):
        PPL = 'ppl', 'Private Pilot License'
        CPL = 'cpl', 'Commercial Pilot License'
        IR = 'ir', 'Instrument Rating'
        ME = 'me', 'Multi-Engine Rating'
        FI = 'fi', 'Flight Instructor'
        ATP = 'atp', 'Airline Transport Pilot'
        TYPE_RATING = 'type_rating', 'Type Rating'
        RECURRENT = 'recurrent', 'Recurrent Training'
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Taslak'
        ACTIVE = 'active', 'Aktif'
        DEPRECATED = 'deprecated', 'Kullanımdan Kaldırıldı'
        ARCHIVED = 'archived', 'Arşivlendi'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    program_type = models.CharField(
        max_length=50,
        choices=ProgramType.choices
    )
    
    regulatory_authority = models.CharField(max_length=20, blank=True, null=True)
    approval_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Gereksinimler
    min_hours_total = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True
    )
    min_hours_dual = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True
    )
    min_hours_solo = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True
    )
    
    prerequisites = models.JSONField(default=list)
    min_age = models.IntegerField(blank=True, null=True)
    required_medical_class = models.IntegerField(blank=True, null=True)
    
    # Süre
    estimated_duration_days = models.IntegerField(blank=True, null=True)
    
    # Fiyat
    base_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    
    # Kademeler
    stages = models.JSONField(default=list)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    is_published = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'training_programs'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'code'],
                name='unique_program_code'
            )
        ]
    
    def __str__(self):
        return f"{self.code}: {self.name}"


class SyllabusLesson(TenantModel):
    """Ders modeli"""
    
    class LessonType(models.TextChoices):
        GROUND = 'ground', 'Yer Dersi'
        FLIGHT = 'flight', 'Uçuş Dersi'
        SIMULATOR = 'simulator', 'Simülatör'
        BRIEFING = 'briefing', 'Brifing'
        EXAM = 'exam', 'Sınav'
        STAGE_CHECK = 'stage_check', 'Kademe Kontrolü'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(
        TrainingProgram,
        on_delete=models.CASCADE,
        related_name='lessons'
    )
    
    stage_id = models.UUIDField(blank=True, null=True)
    parent_lesson = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_lessons'
    )
    
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    objective = models.TextField(blank=True, null=True)
    
    lesson_type = models.CharField(
        max_length=50,
        choices=LessonType.choices
    )
    
    sort_order = models.IntegerField(default=0)
    
    duration_hours = models.DecimalField(
        max_digits=4, decimal_places=2, blank=True, null=True
    )
    ground_hours = models.DecimalField(
        max_digits=4, decimal_places=2, blank=True, null=True
    )
    flight_hours = models.DecimalField(
        max_digits=4, decimal_places=2, blank=True, null=True
    )
    
    prerequisite_lessons = models.JSONField(default=list)
    
    content = models.TextField(blank=True, null=True)
    resources = models.JSONField(default=list)
    
    min_grade_to_pass = models.IntegerField(default=70)
    
    status = models.CharField(max_length=20, default='active')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'syllabus_lessons'
        ordering = ['sort_order']
    
    def __str__(self):
        return f"{self.code}: {self.name}"


class StudentEnrollment(TenantModel):
    """Öğrenci kaydı modeli"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Beklemede'
        ACTIVE = 'active', 'Aktif'
        ON_HOLD = 'on_hold', 'Askıda'
        COMPLETED = 'completed', 'Tamamlandı'
        WITHDRAWN = 'withdrawn', 'Çekildi'
        EXPIRED = 'expired', 'Süresi Doldu'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    student_id = models.UUIDField(db_index=True)
    program = models.ForeignKey(
        TrainingProgram,
        on_delete=models.PROTECT,
        related_name='enrollments'
    )
    primary_instructor_id = models.UUIDField(blank=True, null=True)
    
    enrollment_date = models.DateField()
    start_date = models.DateField(blank=True, null=True)
    expected_completion = models.DateField(blank=True, null=True)
    actual_completion = models.DateField(blank=True, null=True)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    current_stage_id = models.UUIDField(blank=True, null=True)
    current_lesson_id = models.UUIDField(blank=True, null=True)
    
    # Saatler
    total_flight_hours = models.DecimalField(
        max_digits=6, decimal_places=2, default=0
    )
    total_ground_hours = models.DecimalField(
        max_digits=6, decimal_places=2, default=0
    )
    dual_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    solo_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # İlerleme
    lessons_completed = models.IntegerField(default=0)
    lessons_total = models.IntegerField(default=0)
    completion_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    
    notes = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'student_enrollments'
        constraints = [
            models.UniqueConstraint(
                fields=['student_id', 'program'],
                name='unique_student_program_enrollment'
            )
        ]
    
    def __str__(self):
        return f"Enrollment: {self.student_id} - {self.program.code}"
    
    def update_progress(self):
        """İlerlemeyi güncelle"""
        completed = LessonCompletion.objects.filter(
            enrollment=self,
            is_completed=True
        ).count()
        
        total = self.program.lessons.filter(status='active').count()
        
        self.lessons_completed = completed
        self.lessons_total = total
        
        if total > 0:
            self.completion_percentage = (completed / total) * 100
        
        self.save()


class LessonCompletion(TenantModel):
    """Ders tamamlama kaydı"""
    
    class Status(models.TextChoices):
        NOT_STARTED = 'not_started', 'Başlanmadı'
        IN_PROGRESS = 'in_progress', 'Devam Ediyor'
        COMPLETED = 'completed', 'Tamamlandı'
        FAILED = 'failed', 'Başarısız'
        DEFERRED = 'deferred', 'Ertelendi'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    enrollment = models.ForeignKey(
        StudentEnrollment,
        on_delete=models.CASCADE,
        related_name='completions'
    )
    lesson = models.ForeignKey(
        SyllabusLesson,
        on_delete=models.PROTECT
    )
    student_id = models.UUIDField()
    instructor_id = models.UUIDField(blank=True, null=True)
    
    flight_id = models.UUIDField(blank=True, null=True)
    session_date = models.DateField()
    
    ground_time = models.DecimalField(
        max_digits=4, decimal_places=2, blank=True, null=True
    )
    flight_time = models.DecimalField(
        max_digits=4, decimal_places=2, blank=True, null=True
    )
    
    attempt_number = models.IntegerField(default=1)
    grade = models.IntegerField(blank=True, null=True)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS
    )
    
    exercise_grades = models.JSONField(default=list)
    competency_scores = models.JSONField(default=dict)
    
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    instructor_comments = models.TextField(blank=True, null=True)
    areas_of_improvement = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'lesson_completions'
        ordering = ['-session_date']
    
    def __str__(self):
        return f"{self.lesson.code} - {self.session_date}"
    
    def complete(self, grade: int, instructor_id: str):
        """Dersi tamamla"""
        from django.utils import timezone
        
        self.grade = grade
        self.instructor_id = instructor_id
        self.is_completed = grade >= self.lesson.min_grade_to_pass
        self.status = self.Status.COMPLETED if self.is_completed else self.Status.FAILED
        self.completed_at = timezone.now()
        self.save()
        
        # Enrollment ilerlemesini güncelle
        self.enrollment.update_progress()
```

---

## 4. API ENDPOINTS

```yaml
# =============================================================================
# TRAINING API
# =============================================================================

# Programs
GET /api/v1/training/programs:
  summary: Eğitim programları listesi

POST /api/v1/training/programs:
  summary: Program oluştur

GET /api/v1/training/programs/{id}:
  summary: Program detayı

PUT /api/v1/training/programs/{id}:
  summary: Program güncelle

GET /api/v1/training/programs/{id}/syllabus:
  summary: Program müfredatı

# Lessons
GET /api/v1/training/lessons:
  summary: Ders listesi

POST /api/v1/training/lessons:
  summary: Ders oluştur

GET /api/v1/training/lessons/{id}:
  summary: Ders detayı

# Enrollments
GET /api/v1/training/enrollments:
  summary: Kayıt listesi
  parameters:
    - name: student_id
    - name: program_id
    - name: status

POST /api/v1/training/enrollments:
  summary: Öğrenci kaydet

GET /api/v1/training/enrollments/{id}:
  summary: Kayıt detayı

PUT /api/v1/training/enrollments/{id}:
  summary: Kayıt güncelle

GET /api/v1/training/enrollments/{id}/progress:
  summary: İlerleme durumu

# Lesson Completions
GET /api/v1/training/completions:
  summary: Tamamlama kayıtları

POST /api/v1/training/completions:
  summary: Ders tamamlama kaydı

PUT /api/v1/training/completions/{id}:
  summary: Tamamlama güncelle

POST /api/v1/training/completions/{id}/sign:
  summary: İmzala

# Student Progress
GET /api/v1/training/students/{student_id}/progress:
  summary: Öğrenci genel ilerleme

GET /api/v1/training/students/{student_id}/enrollments:
  summary: Öğrenci kayıtları

GET /api/v1/training/students/{student_id}/next-lesson:
  summary: Sonraki ders önerisi

# Stage Checks
POST /api/v1/training/stage-checks:
  summary: Kademe kontrolü kaydet

GET /api/v1/training/stage-checks/{id}:
  summary: Kademe kontrolü detayı
```

---

## 5. SERVİS KATMANI

```python
# apps/core/services/training_service.py

from typing import List, Dict, Any, Optional
from datetime import date
from decimal import Decimal
from django.db import transaction

from apps.core.models import (
    TrainingProgram, SyllabusLesson, StudentEnrollment,
    LessonCompletion, StageCheck
)
from common.events import EventBus
from common.clients import UserServiceClient, FlightServiceClient


class TrainingService:
    def __init__(self):
        self.event_bus = EventBus()
        self.user_client = UserServiceClient()
        self.flight_client = FlightServiceClient()
    
    @transaction.atomic
    async def enroll_student(
        self,
        organization_id: str,
        student_id: str,
        program_id: str,
        instructor_id: str = None,
        start_date: date = None
    ) -> StudentEnrollment:
        """Öğrenciyi programa kaydet"""
        
        program = await TrainingProgram.objects.aget(id=program_id)
        
        # Ön koşul kontrolü
        prereq_check = await self._check_prerequisites(student_id, program)
        if not prereq_check['met']:
            raise ValueError(f"Ön koşullar karşılanmadı: {prereq_check['missing']}")
        
        # Kayıt oluştur
        enrollment = await StudentEnrollment.objects.acreate(
            organization_id=organization_id,
            student_id=student_id,
            program=program,
            primary_instructor_id=instructor_id,
            enrollment_date=date.today(),
            start_date=start_date or date.today(),
            lessons_total=await program.lessons.filter(status='active').acount()
        )
        
        # İlk kademeyi ayarla
        if program.stages:
            enrollment.current_stage_id = program.stages[0]['id']
        
        # İlk dersi ayarla
        first_lesson = await program.lessons.filter(
            status='active'
        ).order_by('sort_order').afirst()
        
        if first_lesson:
            enrollment.current_lesson_id = first_lesson.id
        
        await enrollment.asave()
        
        self.event_bus.publish('training.student_enrolled', {
            'enrollment_id': str(enrollment.id),
            'student_id': student_id,
            'program_id': program_id
        })
        
        return enrollment
    
    async def record_lesson_completion(
        self,
        enrollment_id: str,
        lesson_id: str,
        session_date: date,
        instructor_id: str,
        grade: int = None,
        flight_id: str = None,
        flight_time: float = None,
        ground_time: float = None,
        exercise_grades: List[Dict] = None,
        comments: str = None
    ) -> LessonCompletion:
        """Ders tamamlama kaydı"""
        
        enrollment = await StudentEnrollment.objects.aget(id=enrollment_id)
        lesson = await SyllabusLesson.objects.aget(id=lesson_id)
        
        # Önceki denemeler
        attempts = await LessonCompletion.objects.filter(
            enrollment=enrollment,
            lesson=lesson
        ).acount()
        
        completion = await LessonCompletion.objects.acreate(
            organization_id=enrollment.organization_id,
            enrollment=enrollment,
            lesson=lesson,
            student_id=enrollment.student_id,
            instructor_id=instructor_id,
            session_date=session_date,
            flight_id=flight_id,
            flight_time=Decimal(str(flight_time)) if flight_time else None,
            ground_time=Decimal(str(ground_time)) if ground_time else None,
            attempt_number=attempts + 1,
            grade=grade,
            exercise_grades=exercise_grades or [],
            instructor_comments=comments
        )
        
        # Değerlendirme yap
        if grade is not None:
            is_passed = grade >= lesson.min_grade_to_pass
            completion.is_completed = is_passed
            completion.status = 'completed' if is_passed else 'failed'
            await completion.asave()
        
        # Enrollment saatlerini güncelle
        if flight_time:
            enrollment.total_flight_hours += Decimal(str(flight_time))
            enrollment.dual_hours += Decimal(str(flight_time))
        if ground_time:
            enrollment.total_ground_hours += Decimal(str(ground_time))
        
        await enrollment.asave()
        
        # İlerlemeyi güncelle
        enrollment.update_progress()
        
        # Sonraki dersi belirle
        if completion.is_completed:
            next_lesson = await self._get_next_lesson(enrollment, lesson)
            if next_lesson:
                enrollment.current_lesson_id = next_lesson.id
                await enrollment.asave()
        
        return completion
    
    async def get_student_progress(
        self,
        student_id: str,
        organization_id: str = None
    ) -> Dict[str, Any]:
        """Öğrenci ilerleme özeti"""
        
        query = StudentEnrollment.objects.filter(student_id=student_id)
        if organization_id:
            query = query.filter(organization_id=organization_id)
        
        enrollments = []
        async for enrollment in query.select_related('program'):
            completions = await LessonCompletion.objects.filter(
                enrollment=enrollment,
                is_completed=True
            ).acount()
            
            enrollments.append({
                'enrollment_id': str(enrollment.id),
                'program': {
                    'id': str(enrollment.program.id),
                    'code': enrollment.program.code,
                    'name': enrollment.program.name
                },
                'status': enrollment.status,
                'start_date': enrollment.start_date.isoformat() if enrollment.start_date else None,
                'progress': {
                    'lessons_completed': completions,
                    'lessons_total': enrollment.lessons_total,
                    'percentage': float(enrollment.completion_percentage)
                },
                'hours': {
                    'flight': float(enrollment.total_flight_hours),
                    'ground': float(enrollment.total_ground_hours),
                    'dual': float(enrollment.dual_hours),
                    'solo': float(enrollment.solo_hours)
                }
            })
        
        return {
            'student_id': student_id,
            'enrollments': enrollments
        }
    
    async def get_next_lesson_recommendation(
        self,
        enrollment_id: str
    ) -> Optional[Dict[str, Any]]:
        """Sonraki ders önerisi"""
        
        enrollment = await StudentEnrollment.objects.select_related('program').aget(
            id=enrollment_id
        )
        
        # Tamamlanmış dersler
        completed_ids = set()
        async for c in LessonCompletion.objects.filter(
            enrollment=enrollment,
            is_completed=True
        ).values_list('lesson_id', flat=True):
            completed_ids.add(c)
        
        # Tamamlanmamış dersleri bul
        async for lesson in enrollment.program.lessons.filter(
            status='active'
        ).order_by('sort_order'):
            if lesson.id not in completed_ids:
                # Ön koşulları kontrol et
                prereqs_met = all(
                    prereq_id in completed_ids
                    for prereq_id in (lesson.prerequisite_lessons or [])
                )
                
                if prereqs_met:
                    return {
                        'lesson_id': str(lesson.id),
                        'code': lesson.code,
                        'name': lesson.name,
                        'type': lesson.lesson_type,
                        'duration': float(lesson.duration_hours) if lesson.duration_hours else None,
                        'objective': lesson.objective
                    }
        
        return None
    
    async def _check_prerequisites(
        self,
        student_id: str,
        program: TrainingProgram
    ) -> Dict[str, Any]:
        """Ön koşulları kontrol et"""
        
        missing = []
        
        for prereq in program.prerequisites:
            if prereq['type'] == 'license':
                # Lisans kontrolü
                has_license = await self.user_client.has_license(
                    student_id, prereq['value']
                )
                if not has_license:
                    missing.append(f"Gerekli lisans: {prereq['value']}")
            
            elif prereq['type'] == 'hours':
                # Saat kontrolü
                total_hours = await self.flight_client.get_total_hours(student_id)
                if total_hours < prereq['value']:
                    missing.append(f"Minimum {prereq['value']} saat gerekli")
            
            elif prereq['type'] == 'age':
                # Yaş kontrolü
                age = await self.user_client.get_age(student_id)
                if age < prereq['value']:
                    missing.append(f"Minimum yaş: {prereq['value']}")
        
        return {
            'met': len(missing) == 0,
            'missing': missing
        }
    
    async def _get_next_lesson(
        self,
        enrollment: StudentEnrollment,
        current_lesson: SyllabusLesson
    ) -> Optional[SyllabusLesson]:
        """Sonraki dersi bul"""
        
        return await SyllabusLesson.objects.filter(
            program=enrollment.program,
            status='active',
            sort_order__gt=current_lesson.sort_order
        ).order_by('sort_order').afirst()
```

---

## 6. EVENTS

```python
# Training Service Events

STUDENT_ENROLLED = 'training.student_enrolled'
LESSON_COMPLETED = 'training.lesson_completed'
STAGE_COMPLETED = 'training.stage_completed'
PROGRAM_COMPLETED = 'training.program_completed'
STAGE_CHECK_PASSED = 'training.stage_check_passed'
STAGE_CHECK_FAILED = 'training.stage_check_failed'

# Consumed Events
FLIGHT_APPROVED = 'flight.approved'
# Handler: Eğitim uçuşuysa ilerlemeyi güncelle
```

---

Bu doküman Training Service'in tüm detaylarını içermektedir.