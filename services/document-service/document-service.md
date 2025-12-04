# 📁 MODÜL 12: DOKÜMAN SERVİSİ (Document Service)

## 1. GENEL BAKIŞ

### 1.1 Servis Bilgileri

| Özellik | Değer |
|---------|-------|
| Servis Adı | document-service |
| Port | 8011 |
| Veritabanı | document_db |
| Storage | MinIO / S3 |
| Prefix | /api/v1/documents |

### 1.2 Sorumluluklar

- Dosya yükleme ve depolama
- Doküman kategorilendirme
- Versiyon kontrolü
- Erişim kontrolü ve paylaşım
- Dijital imza yönetimi
- PDF oluşturma
- OCR ve metin çıkarma
- Doküman şablonları

---

## 2. VERİTABANI ŞEMASI

### 2.1 Documents (Dokümanlar)

```sql
-- =============================================================================
-- DOCUMENTS (Dokümanlar)
-- =============================================================================
CREATE TABLE documents (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Dosya Bilgisi
    file_name               VARCHAR(255) NOT NULL,
    original_name           VARCHAR(255) NOT NULL,
    file_path               VARCHAR(500) NOT NULL,
    file_size               BIGINT NOT NULL,
    mime_type               VARCHAR(100) NOT NULL,
    file_extension          VARCHAR(20),
    
    -- Kategorilendirme
    document_type           VARCHAR(50) NOT NULL,
    -- certificate, license, medical, training_record,
    -- flight_log, maintenance, insurance, manual,
    -- checklist, form, report, invoice, contract, other
    
    category                VARCHAR(100),
    subcategory             VARCHAR(100),
    tags                    TEXT[],
    
    -- İlişkiler
    owner_id                UUID NOT NULL,  -- Yükleyen
    owner_type              VARCHAR(20) DEFAULT 'user',
    
    related_entity_type     VARCHAR(50),
    -- user, aircraft, organization, flight, booking, training
    related_entity_id       UUID,
    
    -- Metadata
    title                   VARCHAR(255),
    description             TEXT,
    
    -- Tarihler
    document_date           DATE,
    expiry_date             DATE,
    
    -- Versiyon
    version                 INTEGER DEFAULT 1,
    parent_document_id      UUID REFERENCES documents(id),
    is_latest_version       BOOLEAN DEFAULT true,
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'active',
    -- active, archived, deleted, pending_review
    
    -- İşleme
    processing_status       VARCHAR(20) DEFAULT 'completed',
    -- pending, processing, completed, failed
    
    ocr_text                TEXT,
    ocr_completed           BOOLEAN DEFAULT false,
    
    -- Güvenlik
    is_confidential         BOOLEAN DEFAULT false,
    access_level            VARCHAR(20) DEFAULT 'organization',
    -- public, organization, private, restricted
    
    encryption_key_id       UUID,
    is_encrypted            BOOLEAN DEFAULT false,
    
    -- Doğrulama
    checksum                VARCHAR(64),  -- SHA-256
    virus_scanned           BOOLEAN DEFAULT false,
    virus_scan_result       VARCHAR(20),
    
    -- İmza
    is_signed               BOOLEAN DEFAULT false,
    signature_count         INTEGER DEFAULT 0,
    
    -- Görüntüleme
    thumbnail_path          VARCHAR(500),
    preview_path            VARCHAR(500),
    page_count              INTEGER,
    
    -- İstatistikler
    view_count              INTEGER DEFAULT 0,
    download_count          INTEGER DEFAULT 0,
    last_viewed_at          TIMESTAMP,
    last_downloaded_at      TIMESTAMP,
    
    -- Audit
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID,
    deleted_at              TIMESTAMP,
    deleted_by              UUID
);

CREATE INDEX idx_documents_org ON documents(organization_id);
CREATE INDEX idx_documents_owner ON documents(owner_id);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_entity ON documents(related_entity_type, related_entity_id);
CREATE INDEX idx_documents_expiry ON documents(expiry_date) WHERE expiry_date IS NOT NULL;
CREATE INDEX idx_documents_tags ON documents USING GIN(tags);
CREATE INDEX idx_documents_search ON documents 
    USING GIN(to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, '')));
```

### 2.2 Document Folders (Klasörler)

```sql
-- =============================================================================
-- DOCUMENT_FOLDERS (Klasörler)
-- =============================================================================
CREATE TABLE document_folders (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Hiyerarşi
    parent_folder_id        UUID REFERENCES document_folders(id),
    path                    TEXT NOT NULL,  -- /root/folder1/folder2
    depth                   INTEGER DEFAULT 0,
    
    -- Tanımlama
    name                    VARCHAR(255) NOT NULL,
    description             TEXT,
    
    -- Sahiplik
    owner_id                UUID NOT NULL,
    owner_type              VARCHAR(20) DEFAULT 'user',
    
    -- Durum
    is_system_folder        BOOLEAN DEFAULT false,
    is_shared               BOOLEAN DEFAULT false,
    
    -- İstatistikler
    document_count          INTEGER DEFAULT 0,
    total_size_bytes        BIGINT DEFAULT 0,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_folders_org ON document_folders(organization_id);
CREATE INDEX idx_folders_parent ON document_folders(parent_folder_id);
CREATE INDEX idx_folders_path ON document_folders(path);
```

### 2.3 Document Signatures (İmzalar)

```sql
-- =============================================================================
-- DOCUMENT_SIGNATURES (Dijital İmzalar)
-- =============================================================================
CREATE TABLE document_signatures (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    document_id             UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- İmzalayan
    signer_id               UUID NOT NULL,
    signer_name             VARCHAR(255) NOT NULL,
    signer_email            VARCHAR(255),
    signer_role             VARCHAR(100),
    
    -- İmza Verisi
    signature_type          VARCHAR(50) NOT NULL,
    -- drawn, typed, uploaded, certificate
    
    signature_data          TEXT,  -- Base64 veya reference
    signature_hash          VARCHAR(64),
    
    -- Konum
    page_number             INTEGER,
    position_x              DECIMAL(10,2),
    position_y              DECIMAL(10,2),
    width                   DECIMAL(10,2),
    height                  DECIMAL(10,2),
    
    -- Sertifika (PKI)
    certificate_serial      VARCHAR(255),
    certificate_issuer      VARCHAR(255),
    certificate_valid_from  TIMESTAMP,
    certificate_valid_to    TIMESTAMP,
    
    -- Doğrulama
    ip_address              INET,
    user_agent              TEXT,
    geolocation             JSONB,
    
    -- Zaman Damgası
    signed_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    timestamp_token         TEXT,  -- RFC 3161 timestamp
    
    -- Durum
    status                  VARCHAR(20) DEFAULT 'valid',
    -- valid, revoked, expired
    
    verification_status     VARCHAR(20),
    verification_message    TEXT
);

CREATE INDEX idx_signatures_document ON document_signatures(document_id);
CREATE INDEX idx_signatures_signer ON document_signatures(signer_id);
```

### 2.4 Document Templates (Şablonlar)

```sql
-- =============================================================================
-- DOCUMENT_TEMPLATES (Doküman Şablonları)
-- =============================================================================
CREATE TABLE document_templates (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Tanımlama
    name                    VARCHAR(255) NOT NULL,
    code                    VARCHAR(50),
    description             TEXT,
    
    -- Tip
    template_type           VARCHAR(50) NOT NULL,
    -- certificate, endorsement, invoice, report,
    -- logbook, contract, form, letter
    
    -- Format
    output_format           VARCHAR(20) DEFAULT 'pdf',
    -- pdf, docx, html
    
    -- İçerik
    template_content        TEXT,  -- HTML/Handlebars template
    template_file_path      VARCHAR(500),
    
    -- Değişkenler
    variables               JSONB DEFAULT '[]',
    -- [{"name": "student_name", "type": "string", "required": true}]
    
    -- Stil
    header_content          TEXT,
    footer_content          TEXT,
    styles                  TEXT,  -- CSS
    
    -- Sayfa Ayarları
    page_size               VARCHAR(20) DEFAULT 'A4',
    page_orientation        VARCHAR(20) DEFAULT 'portrait',
    margins                 JSONB DEFAULT '{"top": 20, "right": 20, "bottom": 20, "left": 20}',
    
    -- Durum
    is_active               BOOLEAN DEFAULT true,
    is_system               BOOLEAN DEFAULT false,
    
    -- Versiyon
    version                 INTEGER DEFAULT 1,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID
);

CREATE INDEX idx_templates_org ON document_templates(organization_id);
CREATE INDEX idx_templates_type ON document_templates(template_type);
```

### 2.5 Document Shares (Paylaşımlar)

```sql
-- =============================================================================
-- DOCUMENT_SHARES (Paylaşımlar)
-- =============================================================================
CREATE TABLE document_shares (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL,
    
    -- Kaynak
    document_id             UUID REFERENCES documents(id) ON DELETE CASCADE,
    folder_id               UUID REFERENCES document_folders(id) ON DELETE CASCADE,
    
    -- Hedef
    shared_with_type        VARCHAR(20) NOT NULL,
    -- user, role, organization, public
    shared_with_id          UUID,  -- user_id veya role_id
    
    -- İzinler
    permission              VARCHAR(20) DEFAULT 'view',
    -- view, download, edit, manage
    
    -- Geçerlilik
    expires_at              TIMESTAMP,
    
    -- Erişim Linki
    share_token             VARCHAR(100) UNIQUE,
    share_url               VARCHAR(500),
    
    -- Güvenlik
    password_protected      BOOLEAN DEFAULT false,
    password_hash           VARCHAR(255),
    max_downloads           INTEGER,
    download_count          INTEGER DEFAULT 0,
    
    -- Durum
    is_active               BOOLEAN DEFAULT true,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by              UUID
);

CREATE INDEX idx_shares_document ON document_shares(document_id);
CREATE INDEX idx_shares_folder ON document_shares(folder_id);
CREATE INDEX idx_shares_token ON document_shares(share_token);
```

---

## 3. DJANGO MODELS

```python
# apps/core/models/document.py

import uuid
import hashlib
from django.db import models
from django.utils import timezone
from common.models import TenantModel


class Document(TenantModel):
    """Doküman modeli"""
    
    class DocumentType(models.TextChoices):
        CERTIFICATE = 'certificate', 'Sertifika'
        LICENSE = 'license', 'Lisans'
        MEDICAL = 'medical', 'Sağlık'
        TRAINING_RECORD = 'training_record', 'Eğitim Kaydı'
        FLIGHT_LOG = 'flight_log', 'Uçuş Logu'
        MAINTENANCE = 'maintenance', 'Bakım'
        INSURANCE = 'insurance', 'Sigorta'
        MANUAL = 'manual', 'El Kitabı'
        CHECKLIST = 'checklist', 'Kontrol Listesi'
        FORM = 'form', 'Form'
        REPORT = 'report', 'Rapor'
        INVOICE = 'invoice', 'Fatura'
        CONTRACT = 'contract', 'Sözleşme'
        OTHER = 'other', 'Diğer'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Aktif'
        ARCHIVED = 'archived', 'Arşivlenmiş'
        DELETED = 'deleted', 'Silinmiş'
        PENDING_REVIEW = 'pending_review', 'İnceleme Bekliyor'
    
    class AccessLevel(models.TextChoices):
        PUBLIC = 'public', 'Herkese Açık'
        ORGANIZATION = 'organization', 'Organizasyon'
        PRIVATE = 'private', 'Özel'
        RESTRICTED = 'restricted', 'Kısıtlı'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Dosya bilgisi
    file_name = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.BigIntegerField()
    mime_type = models.CharField(max_length=100)
    file_extension = models.CharField(max_length=20, blank=True, null=True)
    
    # Kategorilendirme
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices
    )
    category = models.CharField(max_length=100, blank=True, null=True)
    tags = models.JSONField(default=list)
    
    # Sahiplik
    owner_id = models.UUIDField(db_index=True)
    owner_type = models.CharField(max_length=20, default='user')
    
    folder = models.ForeignKey(
        'DocumentFolder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )
    
    # İlişki
    related_entity_type = models.CharField(max_length=50, blank=True, null=True)
    related_entity_id = models.UUIDField(blank=True, null=True)
    
    # Metadata
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    document_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    
    # Versiyon
    version = models.IntegerField(default=1)
    parent_document = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versions'
    )
    is_latest_version = models.BooleanField(default=True)
    
    # Durum
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    
    # OCR
    ocr_text = models.TextField(blank=True, null=True)
    ocr_completed = models.BooleanField(default=False)
    
    # Güvenlik
    is_confidential = models.BooleanField(default=False)
    access_level = models.CharField(
        max_length=20,
        choices=AccessLevel.choices,
        default=AccessLevel.ORGANIZATION
    )
    
    # Doğrulama
    checksum = models.CharField(max_length=64, blank=True, null=True)
    
    # İmza
    is_signed = models.BooleanField(default=False)
    signature_count = models.IntegerField(default=0)
    
    # Görüntüleme
    thumbnail_path = models.CharField(max_length=500, blank=True, null=True)
    page_count = models.IntegerField(blank=True, null=True)
    
    # İstatistikler
    view_count = models.IntegerField(default=0)
    download_count = models.IntegerField(default=0)
    last_viewed_at = models.DateTimeField(blank=True, null=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title or self.original_name
    
    @property
    def is_expired(self) -> bool:
        if not self.expiry_date:
            return False
        from datetime import date
        return self.expiry_date < date.today()
    
    @property
    def file_size_display(self) -> str:
        """Dosya boyutunu okunabilir formatta döndür"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def record_view(self):
        """Görüntüleme kaydet"""
        self.view_count += 1
        self.last_viewed_at = timezone.now()
        self.save(update_fields=['view_count', 'last_viewed_at'])
    
    def record_download(self):
        """İndirme kaydet"""
        self.download_count += 1
        self.save(update_fields=['download_count'])


class DocumentFolder(TenantModel):
    """Klasör modeli"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    parent_folder = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subfolders'
    )
    path = models.TextField()
    depth = models.IntegerField(default=0)
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    owner_id = models.UUIDField()
    owner_type = models.CharField(max_length=20, default='user')
    
    is_system_folder = models.BooleanField(default=False)
    is_shared = models.BooleanField(default=False)
    
    document_count = models.IntegerField(default=0)
    total_size_bytes = models.BigIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'document_folders'
        ordering = ['name']
    
    def __str__(self):
        return self.path


class DocumentSignature(TenantModel):
    """Dijital imza modeli"""
    
    class SignatureType(models.TextChoices):
        DRAWN = 'drawn', 'Çizilmiş'
        TYPED = 'typed', 'Yazılmış'
        UPLOADED = 'uploaded', 'Yüklenmiş'
        CERTIFICATE = 'certificate', 'Sertifikalı'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='signatures'
    )
    
    signer_id = models.UUIDField()
    signer_name = models.CharField(max_length=255)
    signer_email = models.EmailField(blank=True, null=True)
    signer_role = models.CharField(max_length=100, blank=True, null=True)
    
    signature_type = models.CharField(
        max_length=50,
        choices=SignatureType.choices
    )
    signature_data = models.TextField(blank=True, null=True)
    signature_hash = models.CharField(max_length=64, blank=True, null=True)
    
    page_number = models.IntegerField(blank=True, null=True)
    position_x = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    position_y = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    signed_at = models.DateTimeField(default=timezone.now)
    
    status = models.CharField(max_length=20, default='valid')
    
    class Meta:
        db_table = 'document_signatures'
        ordering = ['signed_at']
    
    def __str__(self):
        return f"{self.signer_name} - {self.signed_at}"
```

---

## 4. API ENDPOINTS

```yaml
# =============================================================================
# DOCUMENT API
# =============================================================================

# Documents
GET /api/v1/documents:
  summary: Doküman listesi
  parameters:
    - name: type
    - name: category
    - name: folder_id
    - name: entity_type
    - name: entity_id

POST /api/v1/documents:
  summary: Doküman yükle
  requestBody:
    content:
      multipart/form-data:
        schema:
          type: object
          properties:
            file:
              type: string
              format: binary
            document_type:
              type: string
            title:
              type: string
            folder_id:
              type: string

GET /api/v1/documents/{id}:
  summary: Doküman detayı

PUT /api/v1/documents/{id}:
  summary: Doküman güncelle

DELETE /api/v1/documents/{id}:
  summary: Doküman sil

GET /api/v1/documents/{id}/download:
  summary: Doküman indir

GET /api/v1/documents/{id}/preview:
  summary: Önizleme

POST /api/v1/documents/{id}/version:
  summary: Yeni versiyon yükle

GET /api/v1/documents/{id}/versions:
  summary: Versiyon geçmişi

# Folders
GET /api/v1/documents/folders:
  summary: Klasör listesi

POST /api/v1/documents/folders:
  summary: Klasör oluştur

GET /api/v1/documents/folders/{id}:
  summary: Klasör detayı

PUT /api/v1/documents/folders/{id}:
  summary: Klasör güncelle

DELETE /api/v1/documents/folders/{id}:
  summary: Klasör sil

# Signatures
POST /api/v1/documents/{id}/sign:
  summary: Dokümanı imzala

GET /api/v1/documents/{id}/signatures:
  summary: İmza listesi

POST /api/v1/documents/{id}/request-signature:
  summary: İmza talep et

# Sharing
POST /api/v1/documents/{id}/share:
  summary: Paylaş

GET /api/v1/documents/shared/with-me:
  summary: Benimle paylaşılanlar

GET /api/v1/documents/share/{token}:
  summary: Paylaşım linkinden erişim

# Templates
GET /api/v1/documents/templates:
  summary: Şablon listesi

POST /api/v1/documents/templates/{id}/generate:
  summary: Şablondan doküman oluştur

# Search
GET /api/v1/documents/search:
  summary: Doküman ara
  parameters:
    - name: q
    - name: type
    - name: date_from
    - name: date_to
```

---

## 5. SERVİS KATMANI

```python
# apps/core/services/document_service.py

import uuid
import hashlib
from typing import List, Dict, Any, Optional, BinaryIO
from datetime import date
from django.db import transaction
from django.core.files.storage import default_storage

from apps.core.models import Document, DocumentFolder, DocumentSignature, DocumentTemplate
from common.events import EventBus
from common.storage import StorageService


class DocumentService:
    def __init__(self):
        self.event_bus = EventBus()
        self.storage = StorageService()
    
    @transaction.atomic
    async def upload_document(
        self,
        organization_id: str,
        owner_id: str,
        file: BinaryIO,
        file_name: str,
        document_type: str,
        title: str = None,
        folder_id: str = None,
        related_entity_type: str = None,
        related_entity_id: str = None,
        **kwargs
    ) -> Document:
        """Doküman yükle"""
        
        # Dosya bilgileri
        file_content = file.read()
        file_size = len(file_content)
        
        # Checksum hesapla
        checksum = hashlib.sha256(file_content).hexdigest()
        
        # Dosya uzantısı ve MIME type
        extension = file_name.split('.')[-1].lower() if '.' in file_name else ''
        mime_type = self._get_mime_type(extension)
        
        # Storage'a kaydet
        storage_path = f"{organization_id}/{document_type}/{uuid.uuid4()}.{extension}"
        await self.storage.save(storage_path, file_content)
        
        # Doküman oluştur
        document = await Document.objects.acreate(
            organization_id=organization_id,
            owner_id=owner_id,
            file_name=storage_path.split('/')[-1],
            original_name=file_name,
            file_path=storage_path,
            file_size=file_size,
            mime_type=mime_type,
            file_extension=extension,
            document_type=document_type,
            title=title or file_name,
            checksum=checksum,
            folder_id=folder_id,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            created_by=owner_id,
            **kwargs
        )
        
        # Thumbnail oluştur (PDF/resim için)
        if extension in ['pdf', 'jpg', 'jpeg', 'png']:
            await self._generate_thumbnail(document)
        
        # PDF sayfa sayısı
        if extension == 'pdf':
            document.page_count = await self._get_pdf_page_count(file_content)
            await document.asave()
        
        # OCR başlat (opsiyonel)
        if extension in ['pdf', 'jpg', 'jpeg', 'png']:
            self.event_bus.publish('document.ocr_requested', {
                'document_id': str(document.id)
            })
        
        # Event
        self.event_bus.publish('document.uploaded', {
            'document_id': str(document.id),
            'organization_id': organization_id,
            'owner_id': owner_id,
            'document_type': document_type
        })
        
        return document
    
    async def get_download_url(
        self,
        document_id: str,
        user_id: str,
        expires_in: int = 3600
    ) -> str:
        """İndirme URL'i oluştur"""
        
        document = await Document.objects.aget(id=document_id)
        
        # Erişim kontrolü
        await self._check_access(document, user_id, 'download')
        
        # İndirme sayacı
        document.record_download()
        
        # Pre-signed URL oluştur
        url = await self.storage.get_presigned_url(
            document.file_path,
            expires_in=expires_in
        )
        
        return url
    
    @transaction.atomic
    async def create_new_version(
        self,
        document_id: str,
        user_id: str,
        file: BinaryIO,
        file_name: str
    ) -> Document:
        """Yeni versiyon oluştur"""
        
        original = await Document.objects.aget(id=document_id)
        
        # Eski versiyonu güncelle
        original.is_latest_version = False
        await original.asave()
        
        # Yeni versiyon yükle
        new_doc = await self.upload_document(
            organization_id=original.organization_id,
            owner_id=user_id,
            file=file,
            file_name=file_name,
            document_type=original.document_type,
            title=original.title,
            folder_id=str(original.folder_id) if original.folder_id else None,
            related_entity_type=original.related_entity_type,
            related_entity_id=str(original.related_entity_id) if original.related_entity_id else None,
            category=original.category,
            tags=original.tags
        )
        
        new_doc.version = original.version + 1
        new_doc.parent_document = original
        await new_doc.asave()
        
        return new_doc
    
    @transaction.atomic
    async def sign_document(
        self,
        document_id: str,
        signer_id: str,
        signer_name: str,
        signature_type: str,
        signature_data: str,
        ip_address: str = None,
        **kwargs
    ) -> DocumentSignature:
        """Dokümanı imzala"""
        
        document = await Document.objects.aget(id=document_id)
        
        # İmza hash'i
        signature_hash = hashlib.sha256(
            f"{signature_data}{signer_id}{document_id}".encode()
        ).hexdigest()
        
        signature = await DocumentSignature.objects.acreate(
            organization_id=document.organization_id,
            document=document,
            signer_id=signer_id,
            signer_name=signer_name,
            signature_type=signature_type,
            signature_data=signature_data,
            signature_hash=signature_hash,
            ip_address=ip_address,
            **kwargs
        )
        
        # Dokümanı güncelle
        document.is_signed = True
        document.signature_count += 1
        await document.asave()
        
        # Event
        self.event_bus.publish('document.signed', {
            'document_id': str(document.id),
            'signature_id': str(signature.id),
            'signer_id': signer_id
        })
        
        return signature
    
    async def generate_from_template(
        self,
        template_id: str,
        organization_id: str,
        user_id: str,
        variables: Dict[str, Any],
        output_name: str = None
    ) -> Document:
        """Şablondan doküman oluştur"""
        
        template = await DocumentTemplate.objects.aget(id=template_id)
        
        # Değişkenleri uygula
        content = self._apply_template_variables(
            template.template_content,
            variables
        )
        
        # PDF oluştur
        pdf_content = await self._generate_pdf(
            content,
            template.header_content,
            template.footer_content,
            template.styles,
            {
                'page_size': template.page_size,
                'orientation': template.page_orientation,
                'margins': template.margins
            }
        )
        
        # Doküman olarak kaydet
        file_name = output_name or f"{template.name}_{date.today().isoformat()}.pdf"
        
        from io import BytesIO
        file = BytesIO(pdf_content)
        
        document = await self.upload_document(
            organization_id=organization_id,
            owner_id=user_id,
            file=file,
            file_name=file_name,
            document_type=template.template_type,
            title=output_name or template.name
        )
        
        return document
    
    async def search_documents(
        self,
        organization_id: str,
        query: str = None,
        document_type: str = None,
        date_from: date = None,
        date_to: date = None,
        tags: List[str] = None,
        owner_id: str = None
    ) -> List[Document]:
        """Doküman ara"""
        
        queryset = Document.objects.filter(
            organization_id=organization_id,
            status='active'
        )
        
        if query:
            queryset = queryset.filter(
                models.Q(title__icontains=query) |
                models.Q(description__icontains=query) |
                models.Q(ocr_text__icontains=query)
            )
        
        if document_type:
            queryset = queryset.filter(document_type=document_type)
        
        if date_from:
            queryset = queryset.filter(document_date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(document_date__lte=date_to)
        
        if tags:
            queryset = queryset.filter(tags__overlap=tags)
        
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)
        
        return [doc async for doc in queryset.order_by('-created_at')[:100]]
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    def _get_mime_type(self, extension: str) -> str:
        mime_types = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'txt': 'text/plain',
            'csv': 'text/csv'
        }
        return mime_types.get(extension, 'application/octet-stream')
    
    def _apply_template_variables(
        self,
        template: str,
        variables: Dict[str, Any]
    ) -> str:
        """Şablona değişkenleri uygula"""
        from jinja2 import Template
        
        t = Template(template)
        return t.render(**variables)
```

---

## 6. EVENTS

```python
# Document Service Events

DOCUMENT_UPLOADED = 'document.uploaded'
DOCUMENT_UPDATED = 'document.updated'
DOCUMENT_DELETED = 'document.deleted'
DOCUMENT_DOWNLOADED = 'document.downloaded'
DOCUMENT_VIEWED = 'document.viewed'

DOCUMENT_SIGNED = 'document.signed'
SIGNATURE_REQUESTED = 'document.signature_requested'

DOCUMENT_SHARED = 'document.shared'

DOCUMENT_EXPIRING = 'document.expiring'
DOCUMENT_EXPIRED = 'document.expired'

OCR_REQUESTED = 'document.ocr_requested'
OCR_COMPLETED = 'document.ocr_completed'
```

---

Bu doküman Document Service'in tüm detaylarını içermektedir.