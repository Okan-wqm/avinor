# 📚 MODÜL 09: TEORİ SERVİSİ (Theory Service)

## 1. GENEL BAKIŞ

### 1.1 Servis Bilgileri

| Özellik | Değer |
|---------|-------|
| Servis Adı | theory-service |
| Port | 8008 |
| Veritabanı | theory_db |
| Prefix | /api/v1/theory |

### 1.2 Sorumluluklar

- Online teori kursları
- Soru bankası yönetimi
- Sınav oluşturma ve yönetimi
- Otomatik puanlama
- İlerleme takibi
- Sertifika üretimi
- Quiz ve pratik testler

---

## 2. VERİTABANI ŞEMASI

### 2.1 Courses (Kurslar)

```sql
-- =============================================================================
-- COURSES (Teori Kursları)
-- =============================================================================
CREATE TABLE courses (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Tanımlama
    code                    VARCHAR(50) NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    description             TEXT,
    
    -- Kategori
    category                VARCHAR(50) NOT NULL,
    -- air_law, meteorology, navigation, human_performance, 
    -- flight_planning, aircraft_general, principles_of_flight,
    -- operational_procedures, communications, mass_balance
    
    -- İlişkili Program
    program_type            VARCHAR(50),  -- ppl, cpl, atpl, ir
    
    -- Süre
    estimated_hours         DECIMAL(5,2),
    
    -- İçerik
    modules                 JSONB DEFAULT '[]',
    -- [{"id": "uuid", "name": "Module 1", "order": 1}]
    
    -- Gereksinimler
    prerequisites           UUID[],  -- Ön koşul kurslar
    min_score_to_pass       INTEGER DEFAULT 75,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'draft',
    -- draft, published, archived
    
    is_published            BOOLEAN DEFAULT false,
    published_at            TIMESTAMP,
    
    -- Görsel
    thumbnail_url           VARCHAR(500),
    
    -- İstatistikler
    enrolled_count          INTEGER DEFAULT 0,
    completion_rate         DECIMAL(5,2) DEFAULT 0,
    average_score           DECIMAL(5,2),
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID
);

CREATE INDEX idx_courses_org ON courses(organization_id);
CREATE INDEX idx_courses_category ON courses(category);
CREATE INDEX idx_courses_status ON courses(status);
```

### 2.2 Course Modules (Modüller)

```sql
-- =============================================================================
-- COURSE_MODULES (Kurs Modülleri)
-- =============================================================================
CREATE TABLE course_modules (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id               UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    
    -- Tanımlama
    name                    VARCHAR(255) NOT NULL,
    description             TEXT,
    
    -- Sıralama
    sort_order              INTEGER DEFAULT 0,
    
    -- İçerik
    content_type            VARCHAR(50) DEFAULT 'mixed',
    -- text, video, mixed
    
    content                 TEXT,  -- Markdown/HTML
    
    -- Multimedya
    video_url               VARCHAR(500),
    video_duration_minutes  INTEGER,
    attachments             JSONB DEFAULT '[]',
    
    -- Tahmini süre
    estimated_minutes       INTEGER,
    
    -- Quiz
    has_quiz                BOOLEAN DEFAULT false,
    quiz_id                 UUID,
    
    -- Tamamlama
    completion_criteria     JSONB DEFAULT '{}',
    -- {"video_watched": true, "quiz_passed": true, "min_time_spent": 300}
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_modules_course ON course_modules(course_id);
```

### 2.3 Question Bank (Soru Bankası)

```sql
-- =============================================================================
-- QUESTIONS (Soru Bankası)
-- =============================================================================
CREATE TABLE questions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Kategorilendirme
    category                VARCHAR(50) NOT NULL,
    subcategory             VARCHAR(100),
    topic                   VARCHAR(255),
    tags                    TEXT[],
    
    -- Referans
    reference_code          VARCHAR(100),  -- ATO referans
    learning_objective      VARCHAR(255),
    
    -- Soru Tipi
    question_type           VARCHAR(50) NOT NULL DEFAULT 'multiple_choice',
    -- multiple_choice, true_false, multi_select, fill_blank, matching
    
    -- Soru İçeriği
    question_text           TEXT NOT NULL,
    question_html           TEXT,  -- Formatlı içerik
    
    -- Medya
    image_url               VARCHAR(500),
    audio_url               VARCHAR(500),
    explanation_image_url   VARCHAR(500),
    
    -- Cevaplar
    options                 JSONB NOT NULL DEFAULT '[]',
    -- [
    --   {"id": "a", "text": "...", "is_correct": true},
    --   {"id": "b", "text": "...", "is_correct": false}
    -- ]
    
    correct_answer          JSONB NOT NULL,
    -- {"option_id": "a"} veya {"option_ids": ["a", "c"]}
    
    -- Açıklama
    explanation             TEXT,
    explanation_html        TEXT,
    
    -- Zorluk
    difficulty              VARCHAR(20) DEFAULT 'medium',
    -- easy, medium, hard, expert
    
    difficulty_score        INTEGER DEFAULT 50,  -- 1-100
    
    -- Puan
    points                  INTEGER DEFAULT 1,
    negative_points         INTEGER DEFAULT 0,  -- Yanlış cevap puanı
    
    -- Zaman
    time_limit_seconds      INTEGER,
    
    -- İstatistikler
    times_asked             INTEGER DEFAULT 0,
    times_correct           INTEGER DEFAULT 0,
    success_rate            DECIMAL(5,2),
    average_time_seconds    INTEGER,
    
    -- Aktiflik
    is_active               BOOLEAN DEFAULT true,
    
    -- Review
    review_status           VARCHAR(20) DEFAULT 'pending',
    -- pending, approved, rejected, needs_revision
    reviewed_by             UUID,
    reviewed_at             TIMESTAMP,
    
    -- Audit
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID
);

CREATE INDEX idx_questions_org ON questions(organization_id);
CREATE INDEX idx_questions_category ON questions(category);
CREATE INDEX idx_questions_difficulty ON questions(difficulty);
CREATE INDEX idx_questions_active ON questions(is_active) WHERE is_active = true;
CREATE INDEX idx_questions_tags ON questions USING GIN(tags);

-- Full text search
CREATE INDEX idx_questions_search ON questions 
    USING GIN(to_tsvector('english', question_text));
```

### 2.4 Exams (Sınavlar)

```sql
-- =============================================================================
-- EXAMS (Sınav Tanımları)
-- =============================================================================
CREATE TABLE exams (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- İlişki
    course_id               UUID REFERENCES courses(id),
    module_id               UUID REFERENCES course_modules(id),
    
    -- Tanımlama
    code                    VARCHAR(50),
    name                    VARCHAR(255) NOT NULL,
    description             TEXT,
    instructions            TEXT,
    
    -- Tip
    exam_type               VARCHAR(50) NOT NULL DEFAULT 'standard',
    -- standard, practice, mock, final, progress_check
    
    -- Soru Seçimi
    question_selection      VARCHAR(20) DEFAULT 'random',
    -- fixed, random, adaptive
    
    -- Sabit sorular (fixed selection için)
    fixed_questions         UUID[],
    
    -- Random seçim kuralları
    random_rules            JSONB DEFAULT '[]',
    -- [
    --   {"category": "air_law", "count": 10, "difficulty": "medium"},
    --   {"category": "meteorology", "count": 15}
    -- ]
    
    total_questions         INTEGER NOT NULL,
    
    -- Zaman
    time_limit_minutes      INTEGER,
    allow_pause             BOOLEAN DEFAULT false,
    
    -- Geçme Kriteri
    passing_score           INTEGER NOT NULL DEFAULT 75,
    passing_type            VARCHAR(20) DEFAULT 'percentage',
    -- percentage, points
    
    -- Deneme Hakkı
    max_attempts            INTEGER,
    retry_delay_hours       INTEGER,
    
    -- Navigasyon
    allow_review            BOOLEAN DEFAULT true,
    allow_skip              BOOLEAN DEFAULT true,
    show_correct_answers    BOOLEAN DEFAULT false,
    show_explanation        BOOLEAN DEFAULT true,
    show_results_immediately BOOLEAN DEFAULT true,
    
    -- Randomize
    randomize_questions     BOOLEAN DEFAULT true,
    randomize_options       BOOLEAN DEFAULT true,
    
    -- Güvenlik
    require_proctoring      BOOLEAN DEFAULT false,
    browser_lockdown        BOOLEAN DEFAULT false,
    
    -- Planlama
    available_from          TIMESTAMP,
    available_until         TIMESTAMP,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'draft',
    -- draft, published, archived
    
    is_published            BOOLEAN DEFAULT false,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID
);

CREATE INDEX idx_exams_org ON exams(organization_id);
CREATE INDEX idx_exams_course ON exams(course_id);
CREATE INDEX idx_exams_status ON exams(status);
```

### 2.5 Exam Attempts (Sınav Denemeleri)

```sql
-- =============================================================================
-- EXAM_ATTEMPTS (Sınav Denemeleri)
-- =============================================================================
CREATE TABLE exam_attempts (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- İlişkiler
    exam_id                 UUID NOT NULL REFERENCES exams(id),
    user_id                 UUID NOT NULL,
    enrollment_id           UUID,  -- Varsa ilgili enrollment
    
    -- Deneme
    attempt_number          INTEGER NOT NULL DEFAULT 1,
    
    -- Zamanlar
    started_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    submitted_at            TIMESTAMP,
    completed_at            TIMESTAMP,
    
    time_spent_seconds      INTEGER,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'in_progress',
    -- in_progress, paused, submitted, completed, abandoned, invalidated
    
    -- Sorular (Sınav başladığında belirlenir)
    questions               JSONB NOT NULL DEFAULT '[]',
    -- [
    --   {"question_id": "uuid", "order": 1, "points": 1},
    --   ...
    -- ]
    
    -- Cevaplar
    answers                 JSONB DEFAULT '{}',
    -- {
    --   "question_id": {
    --     "selected": "a",
    --     "answered_at": "...",
    --     "time_spent": 45
    --   }
    -- }
    
    -- Puanlama
    total_points            INTEGER,
    earned_points           INTEGER,
    score_percentage        DECIMAL(5,2),
    
    -- Sonuçlar
    passed                  BOOLEAN,
    grade                   VARCHAR(10),  -- A, B, C, D, F
    
    -- Detaylı Sonuçlar
    results_by_category     JSONB DEFAULT '{}',
    -- {"air_law": {"correct": 8, "total": 10, "percentage": 80}}
    
    correct_count           INTEGER DEFAULT 0,
    incorrect_count         INTEGER DEFAULT 0,
    unanswered_count        INTEGER DEFAULT 0,
    
    -- IP ve Cihaz
    ip_address              INET,
    user_agent              TEXT,
    device_info             JSONB,
    
    -- Proctoring
    proctoring_data         JSONB,
    flagged_events          JSONB DEFAULT '[]',
    
    -- Review
    reviewed_by             UUID,
    reviewed_at             TIMESTAMP,
    review_notes            TEXT,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_attempts_exam ON exam_attempts(exam_id);
CREATE INDEX idx_attempts_user ON exam_attempts(user_id);
CREATE INDEX idx_attempts_status ON exam_attempts(status);
CREATE INDEX idx_attempts_started ON exam_attempts(started_at DESC);
```

### 2.6 Course Enrollments

```sql
-- =============================================================================
-- COURSE_ENROLLMENTS (Kurs Kayıtları)
-- =============================================================================
CREATE TABLE course_enrollments (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- İlişkiler
    course_id               UUID NOT NULL REFERENCES courses(id),
    user_id                 UUID NOT NULL,
    
    -- Tarihler
    enrolled_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at              TIMESTAMP,
    completed_at            TIMESTAMP,
    expires_at              TIMESTAMP,
    
    -- İlerleme
    progress_percentage     DECIMAL(5,2) DEFAULT 0,
    modules_completed       INTEGER DEFAULT 0,
    modules_total           INTEGER DEFAULT 0,
    
    -- Zaman
    total_time_spent        INTEGER DEFAULT 0,  -- saniye
    
    -- Sınav
    exam_attempts           INTEGER DEFAULT 0,
    best_score              DECIMAL(5,2),
    passed                  BOOLEAN DEFAULT false,
    passed_at               TIMESTAMP,
    
    -- Sertifika
    certificate_issued      BOOLEAN DEFAULT false,
    certificate_id          UUID,
    certificate_url         VARCHAR(500),
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'enrolled',
    -- enrolled, in_progress, completed, expired, suspended
    
    -- Son Aktivite
    last_accessed_at        TIMESTAMP,
    last_module_id          UUID,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_course_enrollment UNIQUE(course_id, user_id)
);

CREATE INDEX idx_course_enrollments_user ON course_enrollments(user_id);
CREATE INDEX idx_course_enrollments_course ON course_enrollments(course_id);
CREATE INDEX idx_course_enrollments_status ON course_enrollments(status);
```

---

## 3. DJANGO MODELS

```python
# apps/core/models/theory.py

import uuid
from django.db import models
from common.models import TenantModel


class Course(TenantModel):
    """Teori kursu modeli"""
    
    class Category(models.TextChoices):
        AIR_LAW = 'air_law', 'Hava Hukuku'
        METEOROLOGY = 'meteorology', 'Meteoroloji'
        NAVIGATION = 'navigation', 'Seyrüsefer'
        HUMAN_PERFORMANCE = 'human_performance', 'İnsan Performansı'
        FLIGHT_PLANNING = 'flight_planning', 'Uçuş Planlama'
        AIRCRAFT_GENERAL = 'aircraft_general', 'Genel Uçak Bilgisi'
        PRINCIPLES_OF_FLIGHT = 'principles_of_flight', 'Uçuş Prensipleri'
        OPERATIONAL_PROCEDURES = 'operational_procedures', 'Operasyonel Prosedürler'
        COMMUNICATIONS = 'communications', 'Haberleşme'
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Taslak'
        PUBLISHED = 'published', 'Yayında'
        ARCHIVED = 'archived', 'Arşivlendi'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    category = models.CharField(max_length=50, choices=Category.choices)
    program_type = models.CharField(max_length=50, blank=True, null=True)
    
    estimated_hours = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    
    min_score_to_pass = models.IntegerField(default=75)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    is_published = models.BooleanField(default=False)
    
    thumbnail_url = models.URLField(max_length=500, blank=True, null=True)
    
    enrolled_count = models.IntegerField(default=0)
    completion_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'courses'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code}: {self.name}"


class Question(TenantModel):
    """Soru modeli"""
    
    class QuestionType(models.TextChoices):
        MULTIPLE_CHOICE = 'multiple_choice', 'Çoktan Seçmeli'
        TRUE_FALSE = 'true_false', 'Doğru/Yanlış'
        MULTI_SELECT = 'multi_select', 'Çoklu Seçim'
        FILL_BLANK = 'fill_blank', 'Boşluk Doldurma'
    
    class Difficulty(models.TextChoices):
        EASY = 'easy', 'Kolay'
        MEDIUM = 'medium', 'Orta'
        HARD = 'hard', 'Zor'
        EXPERT = 'expert', 'Uzman'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    category = models.CharField(max_length=50)
    subcategory = models.CharField(max_length=100, blank=True, null=True)
    topic = models.CharField(max_length=255, blank=True, null=True)
    tags = models.JSONField(default=list)
    
    question_type = models.CharField(
        max_length=50,
        choices=QuestionType.choices,
        default=QuestionType.MULTIPLE_CHOICE
    )
    
    question_text = models.TextField()
    image_url = models.URLField(max_length=500, blank=True, null=True)
    
    options = models.JSONField(default=list)
    correct_answer = models.JSONField()
    
    explanation = models.TextField(blank=True, null=True)
    
    difficulty = models.CharField(
        max_length=20,
        choices=Difficulty.choices,
        default=Difficulty.MEDIUM
    )
    
    points = models.IntegerField(default=1)
    time_limit_seconds = models.IntegerField(blank=True, null=True)
    
    times_asked = models.IntegerField(default=0)
    times_correct = models.IntegerField(default=0)
    success_rate = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'questions'
    
    def __str__(self):
        return f"{self.category}: {self.question_text[:50]}..."
    
    def update_stats(self, is_correct: bool):
        """İstatistikleri güncelle"""
        self.times_asked += 1
        if is_correct:
            self.times_correct += 1
        self.success_rate = (self.times_correct / self.times_asked) * 100
        self.save()


class Exam(TenantModel):
    """Sınav modeli"""
    
    class ExamType(models.TextChoices):
        STANDARD = 'standard', 'Standart'
        PRACTICE = 'practice', 'Pratik'
        MOCK = 'mock', 'Deneme'
        FINAL = 'final', 'Final'
        PROGRESS_CHECK = 'progress_check', 'İlerleme Kontrolü'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exams'
    )
    
    code = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    instructions = models.TextField(blank=True, null=True)
    
    exam_type = models.CharField(
        max_length=50,
        choices=ExamType.choices,
        default=ExamType.STANDARD
    )
    
    question_selection = models.CharField(max_length=20, default='random')
    random_rules = models.JSONField(default=list)
    total_questions = models.IntegerField()
    
    time_limit_minutes = models.IntegerField(blank=True, null=True)
    passing_score = models.IntegerField(default=75)
    
    max_attempts = models.IntegerField(blank=True, null=True)
    
    allow_review = models.BooleanField(default=True)
    show_correct_answers = models.BooleanField(default=False)
    show_explanation = models.BooleanField(default=True)
    
    randomize_questions = models.BooleanField(default=True)
    randomize_options = models.BooleanField(default=True)
    
    status = models.CharField(max_length=20, default='draft')
    is_published = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'exams'
    
    def __str__(self):
        return self.name


class ExamAttempt(TenantModel):
    """Sınav denemesi modeli"""
    
    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'Devam Ediyor'
        PAUSED = 'paused', 'Duraklatıldı'
        SUBMITTED = 'submitted', 'Gönderildi'
        COMPLETED = 'completed', 'Tamamlandı'
        ABANDONED = 'abandoned', 'Terk Edildi'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    exam = models.ForeignKey(
        Exam,
        on_delete=models.PROTECT,
        related_name='attempts'
    )
    user_id = models.UUIDField(db_index=True)
    
    attempt_number = models.IntegerField(default=1)
    
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    time_spent_seconds = models.IntegerField(default=0)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS
    )
    
    questions = models.JSONField(default=list)
    answers = models.JSONField(default=dict)
    
    total_points = models.IntegerField(default=0)
    earned_points = models.IntegerField(default=0)
    score_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    
    passed = models.BooleanField(blank=True, null=True)
    
    correct_count = models.IntegerField(default=0)
    incorrect_count = models.IntegerField(default=0)
    unanswered_count = models.IntegerField(default=0)
    
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'exam_attempts'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.exam.name} - Attempt {self.attempt_number}"
```

---

## 4. API ENDPOINTS

```yaml
# =============================================================================
# THEORY API
# =============================================================================

# Courses
GET /api/v1/theory/courses:
  summary: Kurs listesi
  parameters:
    - name: category
    - name: status

GET /api/v1/theory/courses/{id}:
  summary: Kurs detayı

GET /api/v1/theory/courses/{id}/modules:
  summary: Kurs modülleri

# Course Enrollment
POST /api/v1/theory/courses/{id}/enroll:
  summary: Kursa kayıt ol

GET /api/v1/theory/courses/{id}/progress:
  summary: Kurs ilerlemesi

POST /api/v1/theory/courses/{id}/modules/{module_id}/complete:
  summary: Modülü tamamla

# Questions
GET /api/v1/theory/questions:
  summary: Soru listesi (admin)

POST /api/v1/theory/questions:
  summary: Soru oluştur

GET /api/v1/theory/questions/{id}:
  summary: Soru detayı

PUT /api/v1/theory/questions/{id}:
  summary: Soru güncelle

POST /api/v1/theory/questions/import:
  summary: Toplu soru import

# Exams
GET /api/v1/theory/exams:
  summary: Sınav listesi

GET /api/v1/theory/exams/{id}:
  summary: Sınav detayı

POST /api/v1/theory/exams/{id}/start:
  summary: Sınava başla
  responses:
    200:
      content:
        application/json:
          schema:
            type: object
            properties:
              attempt_id:
                type: string
              questions:
                type: array
              time_limit:
                type: integer

POST /api/v1/theory/exams/{id}/answer:
  summary: Cevap gönder
  requestBody:
    content:
      application/json:
        schema:
          type: object
          required:
            - attempt_id
            - question_id
            - answer
          properties:
            attempt_id:
              type: string
            question_id:
              type: string
            answer:
              type: object

POST /api/v1/theory/exams/{id}/submit:
  summary: Sınavı bitir

GET /api/v1/theory/exams/{id}/results/{attempt_id}:
  summary: Sınav sonuçları

# Practice
GET /api/v1/theory/practice/questions:
  summary: Pratik soruları getir
  parameters:
    - name: category
    - name: count
    - name: difficulty

# My Progress
GET /api/v1/theory/my/courses:
  summary: Kayıtlı kurslarım

GET /api/v1/theory/my/exams:
  summary: Sınav geçmişim

GET /api/v1/theory/my/statistics:
  summary: İstatistiklerim
```

---

## 5. SERVİS KATMANI

```python
# apps/core/services/theory_service.py

from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import random
from django.db import transaction
from django.utils import timezone

from apps.core.models import Course, Question, Exam, ExamAttempt, CourseEnrollment
from common.exceptions import ValidationError, NotFoundError
from common.events import EventBus


class TheoryService:
    def __init__(self):
        self.event_bus = EventBus()
    
    async def start_exam(
        self,
        exam_id: str,
        user_id: str,
        ip_address: str = None
    ) -> Dict[str, Any]:
        """Sınav başlat"""
        
        exam = await Exam.objects.aget(id=exam_id)
        
        # Yayında mı kontrol
        if not exam.is_published:
            raise ValidationError('Bu sınav henüz yayınlanmadı')
        
        # Deneme hakkı kontrolü
        if exam.max_attempts:
            attempts = await ExamAttempt.objects.filter(
                exam_id=exam_id,
                user_id=user_id,
                status__in=['completed', 'submitted']
            ).acount()
            
            if attempts >= exam.max_attempts:
                raise ValidationError('Maksimum deneme hakkını kullandınız')
        
        # Soruları seç
        questions = await self._select_questions(exam)
        
        # Sıralama
        if exam.randomize_questions:
            random.shuffle(questions)
        
        # Attempt oluştur
        attempt = await ExamAttempt.objects.acreate(
            organization_id=exam.organization_id,
            exam=exam,
            user_id=user_id,
            attempt_number=await ExamAttempt.objects.filter(
                exam_id=exam_id, user_id=user_id
            ).acount() + 1,
            questions=[{'question_id': str(q['id']), 'order': i+1} for i, q in enumerate(questions)],
            total_points=sum(q['points'] for q in questions),
            ip_address=ip_address
        )
        
        # Soruları formatla (cevapları gizle)
        formatted_questions = []
        for i, q in enumerate(questions):
            options = q['options']
            if exam.randomize_options:
                random.shuffle(options)
            
            formatted_questions.append({
                'order': i + 1,
                'question_id': str(q['id']),
                'type': q['question_type'],
                'text': q['question_text'],
                'image_url': q.get('image_url'),
                'options': [{'id': o['id'], 'text': o['text']} for o in options],
                'points': q['points']
            })
        
        return {
            'attempt_id': str(attempt.id),
            'exam_name': exam.name,
            'total_questions': len(formatted_questions),
            'time_limit_minutes': exam.time_limit_minutes,
            'questions': formatted_questions
        }
    
    async def submit_answer(
        self,
        attempt_id: str,
        question_id: str,
        answer: Any,
        time_spent: int = None
    ):
        """Cevap kaydet"""
        
        attempt = await ExamAttempt.objects.aget(id=attempt_id)
        
        if attempt.status != ExamAttempt.Status.IN_PROGRESS:
            raise ValidationError('Bu sınav devam etmiyor')
        
        # Zaman kontrolü
        if attempt.exam.time_limit_minutes:
            elapsed = (timezone.now() - attempt.started_at).total_seconds() / 60
            if elapsed > attempt.exam.time_limit_minutes:
                raise ValidationError('Sınav süresi doldu')
        
        # Cevabı kaydet
        answers = attempt.answers
        answers[question_id] = {
            'selected': answer,
            'answered_at': timezone.now().isoformat(),
            'time_spent': time_spent
        }
        attempt.answers = answers
        await attempt.asave()
    
    @transaction.atomic
    async def submit_exam(
        self,
        attempt_id: str
    ) -> Dict[str, Any]:
        """Sınavı bitir ve puanla"""
        
        attempt = await ExamAttempt.objects.select_related('exam').aget(id=attempt_id)
        
        if attempt.status == ExamAttempt.Status.COMPLETED:
            raise ValidationError('Bu sınav zaten tamamlanmış')
        
        # Puanlama
        results = await self._calculate_results(attempt)
        
        # Güncelle
        attempt.status = ExamAttempt.Status.COMPLETED
        attempt.submitted_at = timezone.now()
        attempt.completed_at = timezone.now()
        attempt.earned_points = results['earned_points']
        attempt.score_percentage = results['score_percentage']
        attempt.passed = results['passed']
        attempt.correct_count = results['correct_count']
        attempt.incorrect_count = results['incorrect_count']
        attempt.unanswered_count = results['unanswered_count']
        attempt.time_spent_seconds = int(
            (attempt.submitted_at - attempt.started_at).total_seconds()
        )
        await attempt.asave()
        
        # Soru istatistiklerini güncelle
        await self._update_question_stats(attempt, results)
        
        # Event
        self.event_bus.publish('theory.exam_completed', {
            'attempt_id': str(attempt.id),
            'user_id': str(attempt.user_id),
            'exam_id': str(attempt.exam_id),
            'passed': results['passed'],
            'score': float(results['score_percentage'])
        })
        
        return results
    
    async def get_exam_results(
        self,
        attempt_id: str,
        include_answers: bool = False
    ) -> Dict[str, Any]:
        """Sınav sonuçlarını getir"""
        
        attempt = await ExamAttempt.objects.select_related('exam').aget(id=attempt_id)
        
        result = {
            'attempt_id': str(attempt.id),
            'exam_name': attempt.exam.name,
            'status': attempt.status,
            'started_at': attempt.started_at.isoformat(),
            'completed_at': attempt.completed_at.isoformat() if attempt.completed_at else None,
            'time_spent_seconds': attempt.time_spent_seconds,
            'total_questions': len(attempt.questions),
            'correct_count': attempt.correct_count,
            'incorrect_count': attempt.incorrect_count,
            'unanswered_count': attempt.unanswered_count,
            'score_percentage': float(attempt.score_percentage) if attempt.score_percentage else 0,
            'passed': attempt.passed,
            'passing_score': attempt.exam.passing_score
        }
        
        if include_answers and attempt.exam.show_correct_answers:
            result['answers'] = await self._get_detailed_answers(attempt)
        
        return result
    
    async def get_practice_questions(
        self,
        organization_id: str,
        category: str = None,
        count: int = 10,
        difficulty: str = None
    ) -> List[Dict[str, Any]]:
        """Pratik soruları getir"""
        
        query = Question.objects.filter(
            organization_id=organization_id,
            is_active=True
        )
        
        if category:
            query = query.filter(category=category)
        
        if difficulty:
            query = query.filter(difficulty=difficulty)
        
        # Random seç
        questions = []
        all_questions = [q async for q in query]
        
        if len(all_questions) <= count:
            selected = all_questions
        else:
            selected = random.sample(all_questions, count)
        
        for q in selected:
            options = q.options.copy()
            random.shuffle(options)
            
            questions.append({
                'id': str(q.id),
                'type': q.question_type,
                'text': q.question_text,
                'image_url': q.image_url,
                'options': [{'id': o['id'], 'text': o['text']} for o in options],
                'category': q.category,
                'difficulty': q.difficulty
            })
        
        return questions
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    async def _select_questions(self, exam: Exam) -> List[Dict]:
        """Sınav için soruları seç"""
        
        questions = []
        
        if exam.question_selection == 'fixed':
            # Sabit sorular
            async for q in Question.objects.filter(
                id__in=exam.fixed_questions,
                is_active=True
            ):
                questions.append({
                    'id': q.id,
                    'question_type': q.question_type,
                    'question_text': q.question_text,
                    'image_url': q.image_url,
                    'options': q.options,
                    'correct_answer': q.correct_answer,
                    'points': q.points,
                    'explanation': q.explanation
                })
        else:
            # Random seçim
            for rule in exam.random_rules:
                query = Question.objects.filter(
                    organization_id=exam.organization_id,
                    category=rule['category'],
                    is_active=True
                )
                
                if 'difficulty' in rule:
                    query = query.filter(difficulty=rule['difficulty'])
                
                pool = [q async for q in query]
                selected = random.sample(pool, min(rule['count'], len(pool)))
                
                for q in selected:
                    questions.append({
                        'id': q.id,
                        'question_type': q.question_type,
                        'question_text': q.question_text,
                        'image_url': q.image_url,
                        'options': q.options,
                        'correct_answer': q.correct_answer,
                        'points': q.points,
                        'explanation': q.explanation
                    })
        
        return questions
    
    async def _calculate_results(self, attempt: ExamAttempt) -> Dict[str, Any]:
        """Sonuçları hesapla"""
        
        earned_points = 0
        correct_count = 0
        incorrect_count = 0
        
        question_ids = [q['question_id'] for q in attempt.questions]
        questions_map = {}
        
        async for q in Question.objects.filter(id__in=question_ids):
            questions_map[str(q.id)] = q
        
        for q_data in attempt.questions:
            q_id = q_data['question_id']
            question = questions_map.get(q_id)
            
            if not question:
                continue
            
            answer_data = attempt.answers.get(q_id)
            
            if answer_data:
                is_correct = self._check_answer(
                    question.correct_answer,
                    answer_data['selected'],
                    question.question_type
                )
                
                if is_correct:
                    earned_points += question.points
                    correct_count += 1
                else:
                    incorrect_count += 1
        
        unanswered = len(attempt.questions) - correct_count - incorrect_count
        score = (earned_points / attempt.total_points * 100) if attempt.total_points > 0 else 0
        
        return {
            'earned_points': earned_points,
            'total_points': attempt.total_points,
            'score_percentage': Decimal(str(round(score, 2))),
            'passed': score >= attempt.exam.passing_score,
            'correct_count': correct_count,
            'incorrect_count': incorrect_count,
            'unanswered_count': unanswered
        }
    
    def _check_answer(self, correct: Dict, given: Any, question_type: str) -> bool:
        """Cevabı kontrol et"""
        
        if question_type == 'multiple_choice':
            return given == correct.get('option_id')
        elif question_type == 'true_false':
            return given == correct.get('value')
        elif question_type == 'multi_select':
            correct_ids = set(correct.get('option_ids', []))
            given_ids = set(given if isinstance(given, list) else [])
            return correct_ids == given_ids
        
        return False
```

---

## 6. EVENTS

```python
# Theory Service Events

COURSE_ENROLLED = 'theory.course_enrolled'
MODULE_COMPLETED = 'theory.module_completed'
COURSE_COMPLETED = 'theory.course_completed'
EXAM_STARTED = 'theory.exam_started'
EXAM_COMPLETED = 'theory.exam_completed'
EXAM_PASSED = 'theory.exam_passed'
```

---

Bu doküman Theory Service'in tüm detaylarını içermektedir.