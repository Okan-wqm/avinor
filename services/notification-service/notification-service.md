# 🔔 MODÜL 14: BİLDİRİM SERVİSİ (Notification Service)

## 1. GENEL BAKIŞ

### 1.1 Servis Bilgileri

| Özellik | Değer |
|---------|-------|
| Servis Adı | notification-service |
| Port | 8013 |
| Veritabanı | notification_db |
| Message Queue | Redis/RabbitMQ |
| Prefix | /api/v1/notifications |

### 1.2 Sorumluluklar

- Push notification yönetimi
- Email gönderimi
- SMS gönderimi
- In-app bildirimler
- Bildirim şablonları
- Kullanıcı tercihleri
- Bildirim geçmişi
- Toplu bildirim

---

## 2. VERİTABANI ŞEMASI

### 2.1 Notifications (Bildirimler)

```sql
-- =============================================================================
-- NOTIFICATIONS (Bildirimler)
-- =============================================================================
CREATE TABLE notifications (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Alıcı
    user_id                 UUID NOT NULL,
    
    -- Tip ve Kategori
    notification_type       VARCHAR(50) NOT NULL,
    -- booking_reminder, booking_confirmed, booking_cancelled,
    -- flight_approved, certificate_expiring, payment_received,
    -- low_balance, lesson_completed, message, system
    
    category                VARCHAR(50) NOT NULL,
    -- booking, flight, training, finance, certificate, 
    -- maintenance, system, message
    
    -- Öncelik
    priority                VARCHAR(20) DEFAULT 'normal',
    -- low, normal, high, urgent
    
    -- İçerik
    title                   VARCHAR(255) NOT NULL,
    body                    TEXT NOT NULL,
    body_html               TEXT,
    
    -- Data
    data                    JSONB DEFAULT '{}',
    -- {"booking_id": "uuid", "action_url": "/bookings/123"}
    
    -- İlişkili Kayıt
    reference_type          VARCHAR(50),
    reference_id            UUID,
    
    -- Kanallar
    channels                TEXT[] NOT NULL,
    -- ['in_app', 'email', 'push', 'sms']
    
    -- Durum (Kanal bazlı)
    channel_status          JSONB DEFAULT '{}',
    -- {
    --   "in_app": {"status": "delivered", "at": "..."},
    --   "email": {"status": "sent", "message_id": "..."},
    --   "push": {"status": "delivered", "at": "..."}
    -- }
    
    -- Genel Durum
    status                  VARCHAR(20) DEFAULT 'pending',
    -- pending, sent, delivered, read, failed
    
    -- Okunma
    read_at                 TIMESTAMP,
    
    -- Zamanlama
    scheduled_at            TIMESTAMP,
    sent_at                 TIMESTAMP,
    expires_at              TIMESTAMP,
    
    -- Aksiyon
    action_url              VARCHAR(500),
    action_text             VARCHAR(100),
    
    -- Gruplandırma
    group_key               VARCHAR(100),
    is_grouped              BOOLEAN DEFAULT false,
    
    -- Metadata
    metadata                JSONB DEFAULT '{}',
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user ON notifications(user_id, created_at DESC);
CREATE INDEX idx_notifications_org ON notifications(organization_id);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_scheduled ON notifications(scheduled_at) 
    WHERE status = 'pending' AND scheduled_at IS NOT NULL;
CREATE INDEX idx_notifications_unread ON notifications(user_id) 
    WHERE read_at IS NULL AND status = 'delivered';
```

### 2.2 Notification Templates (Şablonlar)

```sql
-- =============================================================================
-- NOTIFICATION_TEMPLATES (Bildirim Şablonları)
-- =============================================================================
CREATE TABLE notification_templates (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID,  -- NULL ise sistem şablonu
    
    -- Tanımlama
    code                    VARCHAR(100) NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    description             TEXT,
    
    -- Tip
    notification_type       VARCHAR(50) NOT NULL,
    category                VARCHAR(50) NOT NULL,
    
    -- Varsayılan Kanallar
    default_channels        TEXT[] DEFAULT '{in_app}',
    
    -- İçerik Şablonları
    title_template          VARCHAR(500) NOT NULL,
    body_template           TEXT NOT NULL,
    body_html_template      TEXT,
    
    -- Email Spesifik
    email_subject_template  VARCHAR(500),
    email_body_template     TEXT,
    
    -- SMS Spesifik
    sms_template            VARCHAR(500),
    
    -- Push Spesifik
    push_title_template     VARCHAR(100),
    push_body_template      VARCHAR(255),
    push_image_url          VARCHAR(500),
    
    -- Değişkenler
    variables               JSONB DEFAULT '[]',
    -- [{"name": "student_name", "type": "string", "required": true}]
    
    -- Varsayılan Aksiyon
    default_action_url      VARCHAR(500),
    default_action_text     VARCHAR(100),
    
    -- Durum
    is_active               BOOLEAN DEFAULT true,
    is_system               BOOLEAN DEFAULT false,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_templates_code ON notification_templates(
    COALESCE(organization_id, '00000000-0000-0000-0000-000000000000'), 
    code
);
```

### 2.3 User Notification Preferences (Kullanıcı Tercihleri)

```sql
-- =============================================================================
-- USER_NOTIFICATION_PREFERENCES (Bildirim Tercihleri)
-- =============================================================================
CREATE TABLE user_notification_preferences (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    user_id                 UUID NOT NULL,
    
    -- Genel Tercihler
    email_enabled           BOOLEAN DEFAULT true,
    push_enabled            BOOLEAN DEFAULT true,
    sms_enabled             BOOLEAN DEFAULT false,
    in_app_enabled          BOOLEAN DEFAULT true,
    
    -- Sessiz Saatler
    quiet_hours_enabled     BOOLEAN DEFAULT false,
    quiet_hours_start       TIME,  -- 22:00
    quiet_hours_end         TIME,  -- 08:00
    quiet_hours_timezone    VARCHAR(50) DEFAULT 'UTC',
    
    -- Kategori Bazlı
    category_preferences    JSONB DEFAULT '{}',
    -- {
    --   "booking": {"email": true, "push": true, "sms": false},
    --   "finance": {"email": true, "push": false, "sms": false},
    --   "training": {"email": true, "push": true, "sms": false}
    -- }
    
    -- Email Tercihleri
    email_frequency         VARCHAR(20) DEFAULT 'immediate',
    -- immediate, daily_digest, weekly_digest
    
    digest_time             TIME DEFAULT '09:00',
    digest_timezone         VARCHAR(50) DEFAULT 'UTC',
    
    -- Marketing
    marketing_emails        BOOLEAN DEFAULT true,
    
    -- Dil
    language                VARCHAR(10) DEFAULT 'en',
    
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_user_prefs UNIQUE(user_id)
);

CREATE INDEX idx_prefs_user ON user_notification_preferences(user_id);
```

### 2.4 Device Tokens (Cihaz Token'ları)

```sql
-- =============================================================================
-- DEVICE_TOKENS (Push Notification Cihaz Token'ları)
-- =============================================================================
CREATE TABLE device_tokens (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    user_id                 UUID NOT NULL,
    
    -- Token
    token                   VARCHAR(500) NOT NULL,
    token_type              VARCHAR(50) NOT NULL,
    -- fcm, apns, web_push
    
    -- Cihaz Bilgisi
    device_id               VARCHAR(255),
    device_name             VARCHAR(255),
    device_model            VARCHAR(100),
    device_os               VARCHAR(50),
    device_os_version       VARCHAR(50),
    app_version             VARCHAR(50),
    
    -- Durum
    is_active               BOOLEAN DEFAULT true,
    last_used_at            TIMESTAMP,
    
    -- Hata
    failure_count           INTEGER DEFAULT 0,
    last_failure_at         TIMESTAMP,
    last_failure_reason     TEXT,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_device_token UNIQUE(token)
);

CREATE INDEX idx_tokens_user ON device_tokens(user_id);
CREATE INDEX idx_tokens_active ON device_tokens(user_id) WHERE is_active = true;
```

### 2.5 Email Queue (Email Kuyruğu)

```sql
-- =============================================================================
-- EMAIL_QUEUE (Email Gönderim Kuyruğu)
-- =============================================================================
CREATE TABLE email_queue (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    notification_id         UUID REFERENCES notifications(id),
    
    -- Alıcı
    to_email                VARCHAR(255) NOT NULL,
    to_name                 VARCHAR(255),
    
    -- Gönderen
    from_email              VARCHAR(255),
    from_name               VARCHAR(255),
    reply_to                VARCHAR(255),
    
    -- İçerik
    subject                 VARCHAR(500) NOT NULL,
    body_text               TEXT,
    body_html               TEXT,
    
    -- Ekler
    attachments             JSONB DEFAULT '[]',
    -- [{"filename": "invoice.pdf", "path": "...", "content_type": "application/pdf"}]
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'queued',
    -- queued, sending, sent, delivered, bounced, failed
    
    -- Zamanlama
    scheduled_at            TIMESTAMP,
    sent_at                 TIMESTAMP,
    
    -- Sonuç
    message_id              VARCHAR(255),
    error_message           TEXT,
    retry_count             INTEGER DEFAULT 0,
    max_retries             INTEGER DEFAULT 3,
    next_retry_at           TIMESTAMP,
    
    -- Tracking
    opened_at               TIMESTAMP,
    clicked_at              TIMESTAMP,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_email_queue_status ON email_queue(status, scheduled_at);
CREATE INDEX idx_email_queue_org ON email_queue(organization_id);
```

---

## 3. DJANGO MODELS

```python
# apps/core/models/notification.py

import uuid
from django.db import models
from django.utils import timezone
from common.models import TenantModel


class Notification(TenantModel):
    """Bildirim modeli"""
    
    class NotificationType(models.TextChoices):
        BOOKING_REMINDER = 'booking_reminder', 'Rezervasyon Hatırlatma'
        BOOKING_CONFIRMED = 'booking_confirmed', 'Rezervasyon Onayı'
        BOOKING_CANCELLED = 'booking_cancelled', 'Rezervasyon İptali'
        FLIGHT_APPROVED = 'flight_approved', 'Uçuş Onayı'
        CERTIFICATE_EXPIRING = 'certificate_expiring', 'Sertifika Uyarısı'
        PAYMENT_RECEIVED = 'payment_received', 'Ödeme Alındı'
        LOW_BALANCE = 'low_balance', 'Düşük Bakiye'
        LESSON_COMPLETED = 'lesson_completed', 'Ders Tamamlandı'
        MESSAGE = 'message', 'Mesaj'
        SYSTEM = 'system', 'Sistem'
    
    class Category(models.TextChoices):
        BOOKING = 'booking', 'Rezervasyon'
        FLIGHT = 'flight', 'Uçuş'
        TRAINING = 'training', 'Eğitim'
        FINANCE = 'finance', 'Finans'
        CERTIFICATE = 'certificate', 'Sertifika'
        MAINTENANCE = 'maintenance', 'Bakım'
        SYSTEM = 'system', 'Sistem'
        MESSAGE = 'message', 'Mesaj'
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Düşük'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'Yüksek'
        URGENT = 'urgent', 'Acil'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Beklemede'
        SENT = 'sent', 'Gönderildi'
        DELIVERED = 'delivered', 'İletildi'
        READ = 'read', 'Okundu'
        FAILED = 'failed', 'Başarısız'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices
    )
    category = models.CharField(max_length=50, choices=Category.choices)
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL
    )
    
    title = models.CharField(max_length=255)
    body = models.TextField()
    body_html = models.TextField(blank=True, null=True)
    
    data = models.JSONField(default=dict)
    
    reference_type = models.CharField(max_length=50, blank=True, null=True)
    reference_id = models.UUIDField(blank=True, null=True)
    
    channels = models.JSONField(default=list)
    channel_status = models.JSONField(default=dict)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    read_at = models.DateTimeField(blank=True, null=True)
    
    scheduled_at = models.DateTimeField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    
    action_url = models.URLField(max_length=500, blank=True, null=True)
    action_text = models.CharField(max_length=100, blank=True, null=True)
    
    group_key = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type}: {self.title}"
    
    @property
    def is_read(self) -> bool:
        return self.read_at is not None
    
    def mark_as_read(self):
        if not self.read_at:
            self.read_at = timezone.now()
            self.status = self.Status.READ
            self.save(update_fields=['read_at', 'status'])


class NotificationTemplate(models.Model):
    """Bildirim şablonu modeli"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(blank=True, null=True)
    
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    notification_type = models.CharField(max_length=50)
    category = models.CharField(max_length=50)
    
    default_channels = models.JSONField(default=lambda: ['in_app'])
    
    title_template = models.CharField(max_length=500)
    body_template = models.TextField()
    body_html_template = models.TextField(blank=True, null=True)
    
    email_subject_template = models.CharField(max_length=500, blank=True, null=True)
    email_body_template = models.TextField(blank=True, null=True)
    
    sms_template = models.CharField(max_length=500, blank=True, null=True)
    
    push_title_template = models.CharField(max_length=100, blank=True, null=True)
    push_body_template = models.CharField(max_length=255, blank=True, null=True)
    
    variables = models.JSONField(default=list)
    
    default_action_url = models.CharField(max_length=500, blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_templates'
    
    def __str__(self):
        return f"{self.code}: {self.name}"


class UserNotificationPreference(TenantModel):
    """Kullanıcı bildirim tercihi modeli"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(unique=True)
    
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    in_app_enabled = models.BooleanField(default=True)
    
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(blank=True, null=True)
    quiet_hours_end = models.TimeField(blank=True, null=True)
    quiet_hours_timezone = models.CharField(max_length=50, default='UTC')
    
    category_preferences = models.JSONField(default=dict)
    
    email_frequency = models.CharField(max_length=20, default='immediate')
    
    language = models.CharField(max_length=10, default='en')
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_notification_preferences'
    
    def __str__(self):
        return f"Preferences: {self.user_id}"


class DeviceToken(TenantModel):
    """Cihaz token modeli"""
    
    class TokenType(models.TextChoices):
        FCM = 'fcm', 'Firebase Cloud Messaging'
        APNS = 'apns', 'Apple Push Notification'
        WEB_PUSH = 'web_push', 'Web Push'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    
    token = models.CharField(max_length=500, unique=True)
    token_type = models.CharField(max_length=50, choices=TokenType.choices)
    
    device_id = models.CharField(max_length=255, blank=True, null=True)
    device_name = models.CharField(max_length=255, blank=True, null=True)
    device_model = models.CharField(max_length=100, blank=True, null=True)
    device_os = models.CharField(max_length=50, blank=True, null=True)
    device_os_version = models.CharField(max_length=50, blank=True, null=True)
    app_version = models.CharField(max_length=50, blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(blank=True, null=True)
    
    failure_count = models.IntegerField(default=0)
    last_failure_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'device_tokens'
    
    def __str__(self):
        return f"{self.token_type}: {self.device_name}"
```

---

## 4. API ENDPOINTS

```yaml
# =============================================================================
# NOTIFICATION API
# =============================================================================

# Notifications
GET /api/v1/notifications:
  summary: Bildirim listesi
  parameters:
    - name: category
    - name: status
    - name: unread_only
      type: boolean

GET /api/v1/notifications/unread-count:
  summary: Okunmamış bildirim sayısı

GET /api/v1/notifications/{id}:
  summary: Bildirim detayı

POST /api/v1/notifications/{id}/read:
  summary: Okundu olarak işaretle

POST /api/v1/notifications/read-all:
  summary: Tümünü okundu işaretle

DELETE /api/v1/notifications/{id}:
  summary: Bildirimi sil

# Send (Internal/Admin)
POST /api/v1/notifications/send:
  summary: Bildirim gönder
  requestBody:
    content:
      application/json:
        schema:
          type: object
          properties:
            user_id:
              type: string
            template_code:
              type: string
            variables:
              type: object
            channels:
              type: array

POST /api/v1/notifications/send-bulk:
  summary: Toplu bildirim gönder

# Preferences
GET /api/v1/notifications/preferences:
  summary: Bildirim tercihlerim

PUT /api/v1/notifications/preferences:
  summary: Tercihleri güncelle

# Device Tokens
POST /api/v1/notifications/devices:
  summary: Cihaz token kaydet

DELETE /api/v1/notifications/devices/{token}:
  summary: Cihaz token sil

# Templates (Admin)
GET /api/v1/notifications/templates:
  summary: Şablon listesi

POST /api/v1/notifications/templates:
  summary: Şablon oluştur

PUT /api/v1/notifications/templates/{id}:
  summary: Şablon güncelle

# WebSocket
WS /api/v1/notifications/ws:
  summary: Real-time bildirimler
```

---

## 5. SERVİS KATMANI

```python
# apps/core/services/notification_service.py

from typing import List, Dict, Any, Optional
from datetime import datetime, time
from django.db import transaction
from django.utils import timezone
from jinja2 import Template
import asyncio

from apps.core.models import (
    Notification, NotificationTemplate, 
    UserNotificationPreference, DeviceToken, EmailQueue
)
from common.events import EventBus
from common.providers import EmailProvider, PushProvider, SMSProvider


class NotificationService:
    def __init__(self):
        self.event_bus = EventBus()
        self.email_provider = EmailProvider()
        self.push_provider = PushProvider()
        self.sms_provider = SMSProvider()
    
    async def send_notification(
        self,
        organization_id: str,
        user_id: str,
        template_code: str,
        variables: Dict[str, Any] = None,
        channels: List[str] = None,
        priority: str = 'normal',
        scheduled_at: datetime = None,
        reference_type: str = None,
        reference_id: str = None
    ) -> Notification:
        """Şablondan bildirim gönder"""
        
        # Şablonu bul
        template = await self._get_template(organization_id, template_code)
        if not template:
            raise ValueError(f'Template not found: {template_code}')
        
        # Kullanıcı tercihlerini al
        preferences = await self._get_user_preferences(user_id)
        
        # Kanalları belirle
        effective_channels = await self._determine_channels(
            channels or template.default_channels,
            preferences,
            template.category
        )
        
        if not effective_channels:
            return None  # Kullanıcı tüm kanalları kapatmış
        
        # İçeriği render et
        content = self._render_template(template, variables or {})
        
        # Bildirim oluştur
        notification = await Notification.objects.acreate(
            organization_id=organization_id,
            user_id=user_id,
            notification_type=template.notification_type,
            category=template.category,
            priority=priority,
            title=content['title'],
            body=content['body'],
            body_html=content.get('body_html'),
            data=variables or {},
            reference_type=reference_type,
            reference_id=reference_id,
            channels=effective_channels,
            scheduled_at=scheduled_at,
            action_url=template.default_action_url
        )
        
        # Zamanlanmış değilse hemen gönder
        if not scheduled_at:
            await self._send_to_channels(notification, content, preferences)
        
        return notification
    
    async def send_to_user(
        self,
        organization_id: str,
        user_id: str,
        title: str,
        body: str,
        notification_type: str = 'system',
        category: str = 'system',
        channels: List[str] = None,
        **kwargs
    ) -> Notification:
        """Doğrudan bildirim gönder (şablonsuz)"""
        
        preferences = await self._get_user_preferences(user_id)
        
        effective_channels = await self._determine_channels(
            channels or ['in_app', 'push'],
            preferences,
            category
        )
        
        notification = await Notification.objects.acreate(
            organization_id=organization_id,
            user_id=user_id,
            notification_type=notification_type,
            category=category,
            title=title,
            body=body,
            channels=effective_channels,
            **kwargs
        )
        
        content = {'title': title, 'body': body}
        await self._send_to_channels(notification, content, preferences)
        
        return notification
    
    async def send_bulk(
        self,
        organization_id: str,
        user_ids: List[str],
        template_code: str,
        variables: Dict[str, Any] = None
    ) -> List[Notification]:
        """Toplu bildirim gönder"""
        
        notifications = []
        
        for user_id in user_ids:
            try:
                notification = await self.send_notification(
                    organization_id=organization_id,
                    user_id=user_id,
                    template_code=template_code,
                    variables=variables
                )
                if notification:
                    notifications.append(notification)
            except Exception as e:
                # Log error, continue with others
                pass
        
        return notifications
    
    async def get_user_notifications(
        self,
        user_id: str,
        category: str = None,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """Kullanıcı bildirimlerini getir"""
        
        queryset = Notification.objects.filter(user_id=user_id)
        
        if category:
            queryset = queryset.filter(category=category)
        
        if unread_only:
            queryset = queryset.filter(read_at__isnull=True)
        
        return [n async for n in queryset[offset:offset + limit]]
    
    async def get_unread_count(self, user_id: str) -> int:
        """Okunmamış bildirim sayısı"""
        return await Notification.objects.filter(
            user_id=user_id,
            read_at__isnull=True,
            status='delivered'
        ).acount()
    
    async def mark_as_read(self, notification_id: str, user_id: str):
        """Okundu olarak işaretle"""
        notification = await Notification.objects.aget(
            id=notification_id,
            user_id=user_id
        )
        notification.mark_as_read()
        
        # WebSocket ile bildir
        await self._notify_read(user_id, notification_id)
    
    async def mark_all_as_read(self, user_id: str):
        """Tümünü okundu işaretle"""
        await Notification.objects.filter(
            user_id=user_id,
            read_at__isnull=True
        ).aupdate(read_at=timezone.now(), status='read')
    
    async def register_device(
        self,
        organization_id: str,
        user_id: str,
        token: str,
        token_type: str,
        device_info: Dict[str, Any] = None
    ) -> DeviceToken:
        """Cihaz token kaydet"""
        
        device_info = device_info or {}
        
        device, created = await DeviceToken.objects.aupdate_or_create(
            token=token,
            defaults={
                'organization_id': organization_id,
                'user_id': user_id,
                'token_type': token_type,
                'device_id': device_info.get('device_id'),
                'device_name': device_info.get('device_name'),
                'device_model': device_info.get('device_model'),
                'device_os': device_info.get('device_os'),
                'device_os_version': device_info.get('device_os_version'),
                'app_version': device_info.get('app_version'),
                'is_active': True,
                'failure_count': 0
            }
        )
        
        return device
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    async def _send_to_channels(
        self,
        notification: Notification,
        content: Dict[str, Any],
        preferences: UserNotificationPreference
    ):
        """Tüm kanallara gönder"""
        
        channel_status = {}
        
        for channel in notification.channels:
            try:
                if channel == 'in_app':
                    channel_status['in_app'] = {
                        'status': 'delivered',
                        'at': timezone.now().isoformat()
                    }
                    # WebSocket ile bildir
                    await self._send_websocket(notification)
                
                elif channel == 'email':
                    result = await self._send_email(notification, content)
                    channel_status['email'] = result
                
                elif channel == 'push':
                    result = await self._send_push(notification, content)
                    channel_status['push'] = result
                
                elif channel == 'sms':
                    result = await self._send_sms(notification, content)
                    channel_status['sms'] = result
                    
            except Exception as e:
                channel_status[channel] = {
                    'status': 'failed',
                    'error': str(e)
                }
        
        # Durumu güncelle
        notification.channel_status = channel_status
        notification.status = 'delivered'
        notification.sent_at = timezone.now()
        await notification.asave()
    
    async def _send_email(
        self,
        notification: Notification,
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Email gönder"""
        
        # Email kuyruğuna ekle
        email = await EmailQueue.objects.acreate(
            organization_id=notification.organization_id,
            notification_id=notification.id,
            to_email=content.get('email'),  # User service'den alınmalı
            subject=content.get('email_subject', content['title']),
            body_text=content['body'],
            body_html=content.get('email_body', content.get('body_html'))
        )
        
        # Async gönder
        try:
            result = await self.email_provider.send(
                to=email.to_email,
                subject=email.subject,
                body_html=email.body_html,
                body_text=email.body_text
            )
            
            email.status = 'sent'
            email.message_id = result.get('message_id')
            email.sent_at = timezone.now()
            await email.asave()
            
            return {'status': 'sent', 'message_id': result.get('message_id')}
            
        except Exception as e:
            email.status = 'failed'
            email.error_message = str(e)
            await email.asave()
            raise
    
    async def _send_push(
        self,
        notification: Notification,
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Push notification gönder"""
        
        # Kullanıcının cihazlarını bul
        devices = [
            d async for d in DeviceToken.objects.filter(
                user_id=notification.user_id,
                is_active=True
            )
        ]
        
        if not devices:
            return {'status': 'skipped', 'reason': 'no_devices'}
        
        sent_count = 0
        
        for device in devices:
            try:
                await self.push_provider.send(
                    token=device.token,
                    token_type=device.token_type,
                    title=content.get('push_title', content['title']),
                    body=content.get('push_body', content['body']),
                    data=notification.data
                )
                sent_count += 1
                device.last_used_at = timezone.now()
                await device.asave()
                
            except Exception as e:
                device.failure_count += 1
                device.last_failure_at = timezone.now()
                device.last_failure_reason = str(e)
                
                if device.failure_count >= 5:
                    device.is_active = False
                
                await device.asave()
        
        return {'status': 'sent', 'sent_to': sent_count}
    
    async def _send_sms(
        self,
        notification: Notification,
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """SMS gönder"""
        
        phone = content.get('phone')  # User service'den alınmalı
        if not phone:
            return {'status': 'skipped', 'reason': 'no_phone'}
        
        message = content.get('sms', content['body'])[:160]  # SMS limiti
        
        result = await self.sms_provider.send(phone, message)
        
        return {'status': 'sent', 'message_id': result.get('message_id')}
    
    async def _send_websocket(self, notification: Notification):
        """WebSocket ile bildir"""
        # Redis pub/sub kullanarak WebSocket sunucusuna bildir
        self.event_bus.publish(
            f'ws:user:{notification.user_id}:notification',
            {
                'id': str(notification.id),
                'type': notification.notification_type,
                'title': notification.title,
                'body': notification.body,
                'data': notification.data,
                'created_at': notification.created_at.isoformat()
            }
        )
    
    def _render_template(
        self,
        template: NotificationTemplate,
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Şablonu render et"""
        
        def render(tmpl: str) -> str:
            if not tmpl:
                return None
            return Template(tmpl).render(**variables)
        
        return {
            'title': render(template.title_template),
            'body': render(template.body_template),
            'body_html': render(template.body_html_template),
            'email_subject': render(template.email_subject_template),
            'email_body': render(template.email_body_template),
            'sms': render(template.sms_template),
            'push_title': render(template.push_title_template),
            'push_body': render(template.push_body_template)
        }
    
    async def _get_template(
        self,
        organization_id: str,
        code: str
    ) -> Optional[NotificationTemplate]:
        """Şablonu bul (önce org, sonra sistem)"""
        
        template = await NotificationTemplate.objects.filter(
            organization_id=organization_id,
            code=code,
            is_active=True
        ).afirst()
        
        if not template:
            template = await NotificationTemplate.objects.filter(
                organization_id__isnull=True,
                code=code,
                is_active=True
            ).afirst()
        
        return template
    
    async def _get_user_preferences(
        self,
        user_id: str
    ) -> UserNotificationPreference:
        """Kullanıcı tercihlerini getir"""
        
        prefs = await UserNotificationPreference.objects.filter(
            user_id=user_id
        ).afirst()
        
        if not prefs:
            prefs = UserNotificationPreference(user_id=user_id)
        
        return prefs
    
    async def _determine_channels(
        self,
        requested_channels: List[str],
        preferences: UserNotificationPreference,
        category: str
    ) -> List[str]:
        """Etkin kanalları belirle"""
        
        enabled_channels = []
        category_prefs = preferences.category_preferences.get(category, {})
        
        for channel in requested_channels:
            # Genel tercih
            if channel == 'email' and not preferences.email_enabled:
                continue
            if channel == 'push' and not preferences.push_enabled:
                continue
            if channel == 'sms' and not preferences.sms_enabled:
                continue
            if channel == 'in_app' and not preferences.in_app_enabled:
                continue
            
            # Kategori tercihi
            if channel in category_prefs and not category_prefs[channel]:
                continue
            
            enabled_channels.append(channel)
        
        return enabled_channels
```

---

## 6. EVENTS

```python
# Notification Service Events

# Consumed Events (Diğer servislerden)
BOOKING_CREATED = 'booking.created'
# Handler: Rezervasyon onay bildirimi gönder

BOOKING_REMINDER = 'booking.reminder_due'
# Handler: Hatırlatma bildirimi gönder

BOOKING_CANCELLED = 'booking.cancelled'
# Handler: İptal bildirimi gönder

FLIGHT_APPROVED = 'flight.approved'
# Handler: Uçuş onay bildirimi gönder

CERTIFICATE_EXPIRING = 'certificate.expiring_soon'
# Handler: Sertifika uyarı bildirimi gönder

PAYMENT_RECEIVED = 'finance.payment_received'
# Handler: Ödeme bildirimi gönder

LOW_BALANCE = 'finance.low_balance_alert'
# Handler: Düşük bakiye uyarısı gönder

LESSON_COMPLETED = 'training.lesson_completed'
# Handler: Ders tamamlama bildirimi gönder

# Published Events
NOTIFICATION_SENT = 'notification.sent'
NOTIFICATION_DELIVERED = 'notification.delivered'
NOTIFICATION_READ = 'notification.read'
EMAIL_BOUNCED = 'notification.email_bounced'
```

---

Bu doküman Notification Service'in tüm detaylarını içermektedir.