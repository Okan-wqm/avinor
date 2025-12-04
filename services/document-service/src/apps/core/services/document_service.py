# services/document-service/src/apps/core/services/document_service.py
"""
Document Service

Core business logic for document operations including upload, versioning,
access control, and metadata management.
"""

import uuid
import hashlib
import logging
from typing import Optional, BinaryIO, List
from datetime import date

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ..models import (
    Document,
    DocumentType,
    DocumentStatus,
    AccessLevel,
    ProcessingStatus,
    DocumentFolder,
)
from .storage_service import StorageService, StorageError


logger = logging.getLogger(__name__)


class DocumentNotFoundError(Exception):
    """Document not found."""
    pass


class DocumentAccessDeniedError(Exception):
    """Access to document denied."""
    pass


class DocumentProcessingError(Exception):
    """Error during document processing."""
    pass


class DocumentService:
    """
    Service for document management operations.

    Handles:
    - Document upload with file processing
    - Version control
    - Access control validation
    - Search and filtering
    - Document lifecycle management
    """

    def __init__(self):
        self.storage = StorageService()

    # =========================================================================
    # DOCUMENT UPLOAD
    # =========================================================================

    @transaction.atomic
    def upload_document(
        self,
        organization_id: uuid.UUID,
        owner_id: uuid.UUID,
        file_content: bytes,
        filename: str,
        document_type: str,
        title: str = None,
        description: str = None,
        folder_id: uuid.UUID = None,
        related_entity_type: str = None,
        related_entity_id: uuid.UUID = None,
        document_date: date = None,
        expiry_date: date = None,
        category: str = None,
        tags: list = None,
        is_confidential: bool = False,
        access_level: str = AccessLevel.ORGANIZATION,
        created_by: uuid.UUID = None,
        **kwargs
    ) -> Document:
        """
        Upload a new document.

        Args:
            organization_id: Organization UUID
            owner_id: User UUID who owns the document
            file_content: Raw file bytes
            filename: Original filename
            document_type: Type classification
            title: Optional title (defaults to filename)
            description: Optional description
            folder_id: Optional folder UUID
            related_entity_type: Related entity type (user, aircraft, etc.)
            related_entity_id: Related entity UUID
            document_date: Date on the document
            expiry_date: Expiration date
            category: Custom category
            tags: List of searchable tags
            is_confidential: Confidentiality flag
            access_level: Access level setting
            created_by: User who is uploading

        Returns:
            Created Document instance
        """
        # Extract file info
        file_extension = self._get_file_extension(filename)
        mime_type = self.storage.get_content_type(filename)
        file_size = len(file_content)

        # Calculate checksum
        checksum = hashlib.sha256(file_content).hexdigest()

        # Check for duplicate (same org, same checksum)
        existing = Document.objects.filter(
            organization_id=organization_id,
            checksum=checksum,
            status=DocumentStatus.ACTIVE,
        ).first()

        if existing:
            logger.warning(
                f"Duplicate document detected: {existing.id} "
                f"(checksum: {checksum[:16]}...)"
            )
            # Could raise error or return existing based on policy
            # For now, we allow duplicates with warning

        # Generate storage key
        storage_key = self.storage.generate_key(
            organization_id=str(organization_id),
            document_type=document_type,
            filename=filename,
        )

        # Upload to storage
        try:
            upload_result = self.storage.upload_file(
                file_content=file_content,
                key=storage_key,
                content_type=mime_type,
                metadata={
                    'organization_id': str(organization_id),
                    'owner_id': str(owner_id),
                    'document_type': document_type,
                }
            )
        except StorageError as e:
            logger.error(f"Storage upload failed: {e}")
            raise DocumentProcessingError(f"Failed to upload file: {e}")

        # Create document record
        document = Document.objects.create(
            organization_id=organization_id,
            # File info
            file_name=storage_key.split('/')[-1],
            original_name=filename,
            file_path=storage_key,
            file_size=file_size,
            mime_type=mime_type,
            file_extension=file_extension,
            # Categorization
            document_type=document_type,
            category=category,
            tags=tags or [],
            # Ownership
            owner_id=owner_id,
            folder_id=folder_id,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            # Metadata
            title=title or filename,
            description=description,
            document_date=document_date,
            expiry_date=expiry_date,
            # Security
            is_confidential=is_confidential,
            access_level=access_level,
            checksum=checksum,
            # Status
            status=DocumentStatus.ACTIVE,
            processing_status=ProcessingStatus.PENDING,
            # Audit
            created_by=created_by or owner_id,
        )

        # Update folder statistics
        if folder_id:
            self._update_folder_stats(folder_id)

        # Publish event for async processing
        self._publish_document_uploaded(document)

        logger.info(
            f"Document uploaded: {document.id} "
            f"({document.original_name}, {document.file_size_display})"
        )

        return document

    def upload_from_fileobj(
        self,
        organization_id: uuid.UUID,
        owner_id: uuid.UUID,
        file_obj: BinaryIO,
        filename: str,
        document_type: str,
        **kwargs
    ) -> Document:
        """
        Upload document from a file object.

        Args:
            organization_id: Organization UUID
            owner_id: User UUID
            file_obj: File-like object
            filename: Original filename
            document_type: Type classification
            **kwargs: Additional document attributes

        Returns:
            Created Document instance
        """
        file_content = file_obj.read()
        return self.upload_document(
            organization_id=organization_id,
            owner_id=owner_id,
            file_content=file_content,
            filename=filename,
            document_type=document_type,
            **kwargs
        )

    # =========================================================================
    # VERSION CONTROL
    # =========================================================================

    @transaction.atomic
    def create_new_version(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        file_content: bytes,
        filename: str = None,
        version_notes: str = None,
    ) -> Document:
        """
        Create a new version of an existing document.

        Args:
            document_id: Original document UUID
            user_id: User creating the version
            file_content: New file content
            filename: Optional new filename
            version_notes: Notes about this version

        Returns:
            New Document instance
        """
        original = self.get_document(document_id)

        if not self._can_modify(original, user_id):
            raise DocumentAccessDeniedError("Cannot create version")

        # Mark original as not latest
        original.is_latest_version = False
        original.save(update_fields=['is_latest_version'])

        # Get root document for version chain
        root_document = original
        while root_document.parent_document:
            root_document = root_document.parent_document

        # Create new version
        new_doc = self.upload_document(
            organization_id=original.organization_id,
            owner_id=user_id,
            file_content=file_content,
            filename=filename or original.original_name,
            document_type=original.document_type,
            title=original.title,
            description=original.description,
            folder_id=original.folder_id,
            related_entity_type=original.related_entity_type,
            related_entity_id=original.related_entity_id,
            category=original.category,
            tags=original.tags,
            is_confidential=original.is_confidential,
            access_level=original.access_level,
            document_date=original.document_date,
            expiry_date=original.expiry_date,
            created_by=user_id,
        )

        # Set version info
        new_doc.version = original.version + 1
        new_doc.parent_document = root_document
        new_doc.version_notes = version_notes
        new_doc.is_latest_version = True
        new_doc.save(update_fields=[
            'version', 'parent_document', 'version_notes', 'is_latest_version'
        ])

        logger.info(
            f"Created version {new_doc.version} of document {root_document.id}"
        )

        return new_doc

    def get_version_history(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> List[Document]:
        """
        Get all versions of a document.

        Args:
            document_id: Any document in the version chain
            user_id: User requesting history

        Returns:
            List of Document instances ordered by version
        """
        document = self.get_document(document_id)

        if not self._can_view(document, user_id):
            raise DocumentAccessDeniedError("Cannot view document")

        # Find root document
        root = document
        while root.parent_document:
            root = root.parent_document

        # Get all versions
        versions = list(Document.objects.filter(
            Q(id=root.id) | Q(parent_document=root)
        ).order_by('version'))

        return versions

    def restore_version(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Document:
        """
        Restore an older version as the latest version.

        Args:
            document_id: Version to restore
            user_id: User performing restore

        Returns:
            New Document instance (copy of old version)
        """
        old_version = self.get_document(document_id)

        if not self._can_modify(old_version, user_id):
            raise DocumentAccessDeniedError("Cannot restore version")

        # Download old version content
        file_content = self.storage.download_file(old_version.file_path)

        # Create as new version
        return self.create_new_version(
            document_id=document_id,
            user_id=user_id,
            file_content=file_content,
            filename=old_version.original_name,
            version_notes=f"Restored from version {old_version.version}",
        )

    # =========================================================================
    # RETRIEVAL
    # =========================================================================

    def get_document(
        self,
        document_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Document:
        """
        Get a document by ID.

        Args:
            document_id: Document UUID
            include_deleted: Include soft-deleted documents

        Returns:
            Document instance

        Raises:
            DocumentNotFoundError: If document not found
        """
        queryset = Document.objects.all()

        if not include_deleted:
            queryset = queryset.exclude(status=DocumentStatus.DELETED)

        try:
            return queryset.get(id=document_id)
        except Document.DoesNotExist:
            raise DocumentNotFoundError(f"Document not found: {document_id}")

    def get_documents(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        document_type: str = None,
        folder_id: uuid.UUID = None,
        owner_id: uuid.UUID = None,
        related_entity_type: str = None,
        related_entity_id: uuid.UUID = None,
        tags: list = None,
        status: str = None,
        expiring_within_days: int = None,
        only_latest_version: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Get documents with filtering.

        Args:
            organization_id: Organization UUID
            user_id: User requesting documents
            document_type: Filter by type
            folder_id: Filter by folder
            owner_id: Filter by owner
            related_entity_type: Filter by related entity type
            related_entity_id: Filter by related entity ID
            tags: Filter by tags (any match)
            status: Filter by status
            expiring_within_days: Filter by expiry
            only_latest_version: Only latest versions
            limit: Max results
            offset: Pagination offset

        Returns:
            Dict with documents list, count, and pagination info
        """
        queryset = Document.objects.filter(
            organization_id=organization_id
        ).exclude(
            status=DocumentStatus.DELETED
        )

        # Apply filters
        if document_type:
            queryset = queryset.filter(document_type=document_type)

        if folder_id:
            queryset = queryset.filter(folder_id=folder_id)

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        if related_entity_type:
            queryset = queryset.filter(related_entity_type=related_entity_type)

        if related_entity_id:
            queryset = queryset.filter(related_entity_id=related_entity_id)

        if tags:
            queryset = queryset.filter(tags__overlap=tags)

        if status:
            queryset = queryset.filter(status=status)

        if expiring_within_days is not None:
            expiry_cutoff = date.today()
            from datetime import timedelta
            expiry_limit = expiry_cutoff + timedelta(days=expiring_within_days)
            queryset = queryset.filter(
                expiry_date__isnull=False,
                expiry_date__lte=expiry_limit,
                expiry_date__gte=expiry_cutoff,
            )

        if only_latest_version:
            queryset = queryset.filter(is_latest_version=True)

        # Apply access control
        queryset = self._apply_access_filter(queryset, user_id)

        # Get total count before pagination
        total_count = queryset.count()

        # Apply pagination
        documents = list(queryset.order_by('-created_at')[offset:offset + limit])

        return {
            'documents': documents,
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total_count,
        }

    def search_documents(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        query: str,
        document_type: str = None,
        date_from: date = None,
        date_to: date = None,
        include_ocr: bool = True,
        limit: int = 100,
    ) -> List[Document]:
        """
        Search documents by text query.

        Args:
            organization_id: Organization UUID
            user_id: User searching
            query: Search query string
            document_type: Filter by type
            date_from: Filter by date range start
            date_to: Filter by date range end
            include_ocr: Include OCR text in search
            limit: Max results

        Returns:
            List of matching Document instances
        """
        queryset = Document.objects.filter(
            organization_id=organization_id,
            status=DocumentStatus.ACTIVE,
            is_latest_version=True,
        )

        # Text search
        search_q = Q(title__icontains=query) | Q(description__icontains=query)
        search_q |= Q(original_name__icontains=query)
        search_q |= Q(tags__contains=[query])

        if include_ocr:
            search_q |= Q(ocr_text__icontains=query)

        queryset = queryset.filter(search_q)

        # Additional filters
        if document_type:
            queryset = queryset.filter(document_type=document_type)

        if date_from:
            queryset = queryset.filter(document_date__gte=date_from)

        if date_to:
            queryset = queryset.filter(document_date__lte=date_to)

        # Access control
        queryset = self._apply_access_filter(queryset, user_id)

        return list(queryset.order_by('-created_at')[:limit])

    # =========================================================================
    # FILE ACCESS
    # =========================================================================

    def get_download_url(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        expires_in: int = 3600,
        as_attachment: bool = True,
    ) -> str:
        """
        Get a presigned URL for downloading a document.

        Args:
            document_id: Document UUID
            user_id: User requesting download
            expires_in: URL validity in seconds
            as_attachment: Force download vs inline display

        Returns:
            Presigned URL string
        """
        document = self.get_document(document_id)

        if not self._can_download(document, user_id):
            raise DocumentAccessDeniedError("Cannot download document")

        disposition = None
        if as_attachment:
            disposition = f'attachment; filename="{document.original_name}"'

        url = self.storage.get_presigned_url(
            key=document.file_path,
            expires_in=expires_in,
            response_content_type=document.mime_type,
            response_content_disposition=disposition,
        )

        # Record download
        document.record_download(user_id)

        return url

    def get_preview_url(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        expires_in: int = 3600,
    ) -> str:
        """
        Get a presigned URL for previewing a document.

        Args:
            document_id: Document UUID
            user_id: User requesting preview
            expires_in: URL validity in seconds

        Returns:
            Presigned URL string (or thumbnail URL for non-viewable files)
        """
        document = self.get_document(document_id)

        if not self._can_view(document, user_id):
            raise DocumentAccessDeniedError("Cannot view document")

        # Use preview/thumbnail if available
        if document.preview_path:
            path = document.preview_path
        elif document.thumbnail_path:
            path = document.thumbnail_path
        elif document.is_viewable:
            path = document.file_path
        else:
            # Return thumbnail or generate one
            path = document.thumbnail_path or document.file_path

        url = self.storage.get_presigned_url(
            key=path,
            expires_in=expires_in,
        )

        # Record view
        document.record_view(user_id)

        return url

    def download_content(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> tuple[bytes, str, str]:
        """
        Download document content directly.

        Args:
            document_id: Document UUID
            user_id: User downloading

        Returns:
            Tuple of (content bytes, filename, mime_type)
        """
        document = self.get_document(document_id)

        if not self._can_download(document, user_id):
            raise DocumentAccessDeniedError("Cannot download document")

        content = self.storage.download_file(document.file_path)
        document.record_download(user_id)

        return content, document.original_name, document.mime_type

    # =========================================================================
    # UPDATE & DELETE
    # =========================================================================

    @transaction.atomic
    def update_document(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        **updates
    ) -> Document:
        """
        Update document metadata.

        Args:
            document_id: Document UUID
            user_id: User updating
            **updates: Fields to update

        Returns:
            Updated Document instance
        """
        document = self.get_document(document_id)

        if not self._can_modify(document, user_id):
            raise DocumentAccessDeniedError("Cannot modify document")

        # Fields that can be updated
        allowed_fields = {
            'title', 'description', 'category', 'tags', 'document_date',
            'expiry_date', 'is_confidential', 'access_level', 'folder_id',
            'related_entity_type', 'related_entity_id', 'status',
        }

        for field, value in updates.items():
            if field in allowed_fields:
                setattr(document, field, value)

        document.updated_by = user_id
        document.save()

        logger.info(f"Updated document: {document_id}")

        return document

    @transaction.atomic
    def delete_document(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        hard_delete: bool = False,
    ) -> bool:
        """
        Delete a document.

        Args:
            document_id: Document UUID
            user_id: User deleting
            hard_delete: If True, permanently delete file

        Returns:
            True if deleted
        """
        document = self.get_document(document_id, include_deleted=True)

        if not self._can_delete(document, user_id):
            raise DocumentAccessDeniedError("Cannot delete document")

        old_folder_id = document.folder_id

        if hard_delete:
            # Delete from storage
            try:
                self.storage.delete_file(document.file_path)
                if document.thumbnail_path:
                    self.storage.delete_file(document.thumbnail_path)
                if document.preview_path:
                    self.storage.delete_file(document.preview_path)
            except StorageError as e:
                logger.warning(f"Failed to delete files from storage: {e}")

            document.delete()
            logger.info(f"Hard deleted document: {document_id}")
        else:
            document.soft_delete(deleted_by=user_id)
            logger.info(f"Soft deleted document: {document_id}")

        # Update folder stats
        if old_folder_id:
            self._update_folder_stats(old_folder_id)

        return True

    def move_document(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        folder_id: uuid.UUID = None,
    ) -> Document:
        """
        Move document to a different folder.

        Args:
            document_id: Document UUID
            user_id: User moving document
            folder_id: Target folder UUID (None for root)

        Returns:
            Updated Document instance
        """
        document = self.get_document(document_id)

        if not self._can_modify(document, user_id):
            raise DocumentAccessDeniedError("Cannot move document")

        old_folder_id = document.folder_id

        document.folder_id = folder_id
        document.updated_by = user_id
        document.save(update_fields=['folder_id', 'updated_by', 'updated_at'])

        # Update folder statistics
        if old_folder_id:
            self._update_folder_stats(old_folder_id)
        if folder_id:
            self._update_folder_stats(folder_id)

        return document

    # =========================================================================
    # PROCESSING STATUS
    # =========================================================================

    def update_processing_status(
        self,
        document_id: uuid.UUID,
        status: str,
        error: str = None,
    ) -> Document:
        """
        Update document processing status.

        Args:
            document_id: Document UUID
            status: New ProcessingStatus value
            error: Optional error message

        Returns:
            Updated Document instance
        """
        document = Document.objects.get(id=document_id)
        document.processing_status = status
        document.processing_error = error
        document.save(update_fields=['processing_status', 'processing_error'])

        return document

    def update_ocr_result(
        self,
        document_id: uuid.UUID,
        ocr_text: str,
        confidence: float = None,
        language: str = None,
    ) -> Document:
        """
        Update OCR processing results.

        Args:
            document_id: Document UUID
            ocr_text: Extracted text
            confidence: OCR confidence score (0-100)
            language: Detected/used language

        Returns:
            Updated Document instance
        """
        document = Document.objects.get(id=document_id)
        document.ocr_text = ocr_text
        document.ocr_completed = True
        if confidence is not None:
            document.ocr_confidence = confidence
        if language:
            document.ocr_language = language

        document.save(update_fields=[
            'ocr_text', 'ocr_completed', 'ocr_confidence', 'ocr_language'
        ])

        return document

    def update_virus_scan_result(
        self,
        document_id: uuid.UUID,
        result: str,
        details: str = None,
    ) -> Document:
        """
        Update virus scan results.

        Args:
            document_id: Document UUID
            result: 'clean', 'infected', or 'error'
            details: Additional scan details

        Returns:
            Updated Document instance
        """
        document = Document.objects.get(id=document_id)
        document.virus_scanned = True
        document.virus_scan_result = result
        document.virus_scan_details = details
        document.virus_scanned_at = timezone.now()

        document.save(update_fields=[
            'virus_scanned', 'virus_scan_result', 'virus_scan_details',
            'virus_scanned_at'
        ])

        # If infected, quarantine the document
        if result == 'infected':
            document.status = DocumentStatus.DELETED
            document.save(update_fields=['status'])
            logger.warning(f"Document {document_id} quarantined: virus detected")

        return document

    def update_thumbnail(
        self,
        document_id: uuid.UUID,
        thumbnail_path: str,
        preview_path: str = None,
        page_count: int = None,
    ) -> Document:
        """
        Update document thumbnail and preview paths.

        Args:
            document_id: Document UUID
            thumbnail_path: Path to thumbnail in storage
            preview_path: Path to preview image/PDF
            page_count: Number of pages (for PDFs)

        Returns:
            Updated Document instance
        """
        document = Document.objects.get(id=document_id)
        document.thumbnail_path = thumbnail_path

        if preview_path:
            document.preview_path = preview_path
        if page_count is not None:
            document.page_count = page_count

        document.save(update_fields=[
            'thumbnail_path', 'preview_path', 'page_count'
        ])

        return document

    # =========================================================================
    # ACCESS CONTROL HELPERS
    # =========================================================================

    def _can_view(self, document: Document, user_id: uuid.UUID) -> bool:
        """Check if user can view document."""
        # Owner can always view
        if document.owner_id == user_id:
            return True

        # Check access level
        if document.access_level == AccessLevel.PUBLIC:
            return True

        if document.access_level == AccessLevel.PRIVATE:
            return document.owner_id == user_id

        # Organization level - would check org membership in production
        if document.access_level == AccessLevel.ORGANIZATION:
            return True  # Simplified for now

        # Restricted - would check share permissions
        return False

    def _can_download(self, document: Document, user_id: uuid.UUID) -> bool:
        """Check if user can download document."""
        return self._can_view(document, user_id)

    def _can_modify(self, document: Document, user_id: uuid.UUID) -> bool:
        """Check if user can modify document."""
        # Only owner can modify
        return document.owner_id == user_id

    def _can_delete(self, document: Document, user_id: uuid.UUID) -> bool:
        """Check if user can delete document."""
        return document.owner_id == user_id

    def _apply_access_filter(self, queryset, user_id: uuid.UUID):
        """Apply access control filter to queryset."""
        return queryset.filter(
            Q(owner_id=user_id) |
            Q(access_level=AccessLevel.PUBLIC) |
            Q(access_level=AccessLevel.ORGANIZATION)
        )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        if '.' in filename:
            return filename.rsplit('.', 1)[-1].lower()
        return ''

    def _update_folder_stats(self, folder_id: uuid.UUID) -> None:
        """Update folder statistics asynchronously."""
        try:
            folder = DocumentFolder.objects.get(id=folder_id)
            folder.recalculate_statistics()
        except DocumentFolder.DoesNotExist:
            pass

    def _publish_document_uploaded(self, document: Document) -> None:
        """Publish document uploaded event for async processing."""
        # Would publish to Redis/RabbitMQ for Celery workers
        # For now, just log
        logger.debug(f"Document uploaded event: {document.id}")
