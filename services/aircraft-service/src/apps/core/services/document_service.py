# services/aircraft-service/src/apps/core/services/document_service.py
"""
Document Service

Manages aircraft documents, expiry tracking, and compliance.
"""

import uuid
import logging
from datetime import date, timedelta
from typing import Optional, Dict, Any, List

from django.db import transaction
from django.db.models import Q
from django.core.cache import cache
from django.utils import timezone

from apps.core.models import Aircraft, AircraftDocument

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Service for managing aircraft documents.

    Handles:
    - Document CRUD operations
    - Version control
    - Expiry tracking and reminders
    - Compliance checking
    """

    CACHE_TTL = 300  # 5 minutes

    # ==========================================================================
    # Document CRUD
    # ==========================================================================

    @transaction.atomic
    def add_document(
        self,
        aircraft_id: uuid.UUID,
        organization_id: uuid.UUID,
        document_type: str,
        title: str,
        file_url: str,
        file_name: str = None,
        file_size_bytes: int = None,
        file_type: str = 'pdf',
        mime_type: str = None,
        version: str = None,
        revision_date: date = None,
        effective_date: date = None,
        expiry_date: date = None,
        document_number: str = None,
        issuing_authority: str = None,
        is_required: bool = False,
        reminder_days: int = None,
        is_public: bool = False,
        description: str = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        created_by: uuid.UUID = None
    ) -> AircraftDocument:
        """Add a new document to an aircraft."""
        try:
            aircraft = Aircraft.objects.get(
                id=aircraft_id,
                deleted_at__isnull=True
            )
        except Aircraft.DoesNotExist:
            from . import AircraftNotFoundError
            raise AircraftNotFoundError(f"Aircraft {aircraft_id} not found")

        # Validate document type
        valid_types = [choice[0] for choice in AircraftDocument.DocumentType.choices]
        if document_type not in valid_types:
            from . import DocumentError
            raise DocumentError(f"Invalid document type: {document_type}")

        # Mark previous version as superseded if this is a current document
        previous = AircraftDocument.objects.filter(
            aircraft=aircraft,
            document_type=document_type,
            is_current=True
        ).first()

        document = AircraftDocument.objects.create(
            aircraft=aircraft,
            organization_id=organization_id,
            document_type=document_type,
            title=title,
            description=description,
            file_url=file_url,
            file_name=file_name,
            file_size_bytes=file_size_bytes,
            file_type=file_type,
            mime_type=mime_type,
            version=version,
            revision_date=revision_date,
            effective_date=effective_date,
            expiry_date=expiry_date,
            document_number=document_number,
            issuing_authority=issuing_authority,
            is_required=is_required,
            reminder_days=reminder_days,
            is_public=is_public,
            is_current=True,
            supersedes=previous,
            tags=tags or [],
            metadata=metadata or {},
            created_by=created_by,
        )

        # Mark previous as superseded
        if previous:
            previous.mark_as_superseded(document)

        self._invalidate_cache(aircraft_id)

        logger.info(
            f"Added document '{title}' ({document_type}) to aircraft {aircraft.registration}"
        )

        return document

    def get_document(self, document_id: uuid.UUID) -> AircraftDocument:
        """Get a document by ID."""
        try:
            return AircraftDocument.objects.select_related('aircraft').get(
                id=document_id
            )
        except AircraftDocument.DoesNotExist:
            from . import DocumentError
            raise DocumentError(f"Document {document_id} not found")

    def list_documents(
        self,
        aircraft_id: uuid.UUID,
        document_type: str = None,
        current_only: bool = True,
        include_expired: bool = True
    ) -> List[Dict[str, Any]]:
        """List documents for an aircraft."""
        queryset = AircraftDocument.objects.filter(aircraft_id=aircraft_id)

        if document_type:
            queryset = queryset.filter(document_type=document_type)

        if current_only:
            queryset = queryset.filter(is_current=True)

        if not include_expired:
            queryset = queryset.filter(
                Q(expiry_date__isnull=True) | Q(expiry_date__gte=date.today())
            )

        queryset = queryset.order_by('document_type', '-created_at')

        return [self._document_to_dict(doc) for doc in queryset]

    @transaction.atomic
    def update_document(
        self,
        document_id: uuid.UUID,
        updated_by: uuid.UUID = None,
        **kwargs
    ) -> AircraftDocument:
        """Update a document."""
        try:
            document = AircraftDocument.objects.select_for_update().get(
                id=document_id
            )
        except AircraftDocument.DoesNotExist:
            from . import DocumentError
            raise DocumentError(f"Document {document_id} not found")

        # Allowed update fields
        allowed_fields = [
            'title', 'description', 'version', 'revision_date',
            'effective_date', 'expiry_date', 'document_number',
            'issuing_authority', 'is_required', 'reminder_days',
            'is_public', 'is_downloadable', 'tags', 'metadata'
        ]

        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(document, field, value)

        # Reset reminder if expiry date changed
        if 'expiry_date' in kwargs:
            document.reset_reminder()

        document.updated_by = updated_by
        document.save()

        self._invalidate_cache(document.aircraft_id)

        return document

    @transaction.atomic
    def delete_document(self, document_id: uuid.UUID) -> None:
        """Delete a document."""
        try:
            document = AircraftDocument.objects.get(id=document_id)
            aircraft_id = document.aircraft_id
            document.delete()
            self._invalidate_cache(aircraft_id)
            logger.info(f"Deleted document {document_id}")
        except AircraftDocument.DoesNotExist:
            from . import DocumentError
            raise DocumentError(f"Document {document_id} not found")

    # ==========================================================================
    # Expiry Management
    # ==========================================================================

    def get_expiring_documents(
        self,
        organization_id: uuid.UUID = None,
        aircraft_id: uuid.UUID = None,
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """Get documents expiring within specified days."""
        queryset = AircraftDocument.get_expiring_documents(
            organization_id=organization_id,
            days_ahead=days_ahead
        )

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        return [
            {
                **self._document_to_dict(doc),
                'days_until_expiry': doc.days_until_expiry,
                'is_expiring_soon': doc.is_expiring_soon,
            }
            for doc in queryset
        ]

    def get_expired_documents(
        self,
        organization_id: uuid.UUID = None,
        aircraft_id: uuid.UUID = None
    ) -> List[Dict[str, Any]]:
        """Get expired documents still marked as current."""
        queryset = AircraftDocument.get_expired_documents(
            organization_id=organization_id
        )

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        return [self._document_to_dict(doc) for doc in queryset]

    def get_documents_needing_reminder(
        self,
        organization_id: uuid.UUID = None
    ) -> List[Dict[str, Any]]:
        """Get documents that need reminder to be sent."""
        queryset = AircraftDocument.objects.filter(
            is_current=True,
            expiry_date__isnull=False,
            reminder_days__isnull=False,
            reminder_sent=False
        ).select_related('aircraft')

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        return [
            self._document_to_dict(doc)
            for doc in queryset
            if doc.needs_reminder
        ]

    @transaction.atomic
    def mark_reminder_sent(self, document_id: uuid.UUID) -> None:
        """Mark a document reminder as sent."""
        try:
            document = AircraftDocument.objects.get(id=document_id)
            document.send_reminder()
            logger.info(f"Marked reminder sent for document {document_id}")
        except AircraftDocument.DoesNotExist:
            from . import DocumentError
            raise DocumentError(f"Document {document_id} not found")

    # ==========================================================================
    # Compliance Checking
    # ==========================================================================

    def check_compliance(self, aircraft_id: uuid.UUID) -> Dict[str, Any]:
        """Check document compliance for an aircraft."""
        cache_key = f"aircraft_doc_compliance:{aircraft_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            aircraft = Aircraft.objects.get(
                id=aircraft_id,
                deleted_at__isnull=True
            )
        except Aircraft.DoesNotExist:
            from . import AircraftNotFoundError
            raise AircraftNotFoundError(f"Aircraft {aircraft_id} not found")

        # Get missing required documents
        missing = AircraftDocument.get_missing_required_documents(aircraft_id)

        # Get expired documents
        expired = AircraftDocument.objects.filter(
            aircraft_id=aircraft_id,
            is_current=True,
            expiry_date__lt=date.today()
        )

        # Get expiring soon (30 days)
        expiring_date = date.today() + timedelta(days=30)
        expiring_soon = AircraftDocument.objects.filter(
            aircraft_id=aircraft_id,
            is_current=True,
            expiry_date__isnull=False,
            expiry_date__gte=date.today(),
            expiry_date__lte=expiring_date
        )

        is_compliant = len(missing) == 0 and expired.count() == 0

        result = {
            'aircraft_id': str(aircraft_id),
            'registration': aircraft.registration,
            'is_compliant': is_compliant,
            'missing_documents': [
                {
                    'type': doc_type,
                    'label': dict(AircraftDocument.DocumentType.choices).get(doc_type)
                }
                for doc_type in missing
            ],
            'expired_documents': [
                {
                    'id': str(doc.id),
                    'type': doc.document_type,
                    'title': doc.title,
                    'expiry_date': doc.expiry_date.isoformat(),
                    'days_expired': (date.today() - doc.expiry_date).days
                }
                for doc in expired
            ],
            'expiring_soon': [
                {
                    'id': str(doc.id),
                    'type': doc.document_type,
                    'title': doc.title,
                    'expiry_date': doc.expiry_date.isoformat(),
                    'days_until_expiry': doc.days_until_expiry
                }
                for doc in expiring_soon
            ],
            'checked_at': timezone.now().isoformat()
        }

        cache.set(cache_key, result, self.CACHE_TTL)
        return result

    def get_compliance_summary(
        self,
        organization_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get document compliance summary for an organization."""
        # Get all active aircraft
        aircraft_ids = Aircraft.objects.filter(
            organization_id=organization_id,
            deleted_at__isnull=True,
            status__in=[Aircraft.Status.ACTIVE, Aircraft.Status.MAINTENANCE]
        ).values_list('id', flat=True)

        total_aircraft = len(aircraft_ids)
        compliant_count = 0
        non_compliant_aircraft = []
        all_missing = []
        all_expired = []
        all_expiring = []

        for aircraft_id in aircraft_ids:
            compliance = self.check_compliance(aircraft_id)

            if compliance['is_compliant']:
                compliant_count += 1
            else:
                non_compliant_aircraft.append({
                    'aircraft_id': str(aircraft_id),
                    'registration': compliance['registration'],
                    'issues': len(compliance['missing_documents']) + len(compliance['expired_documents'])
                })

            all_missing.extend(compliance['missing_documents'])
            all_expired.extend(compliance['expired_documents'])
            all_expiring.extend(compliance['expiring_soon'])

        return {
            'organization_id': str(organization_id),
            'total_aircraft': total_aircraft,
            'compliant_count': compliant_count,
            'non_compliant_count': total_aircraft - compliant_count,
            'compliance_rate': round(compliant_count / total_aircraft * 100, 1) if total_aircraft > 0 else 100,
            'non_compliant_aircraft': non_compliant_aircraft,
            'total_missing': len(all_missing),
            'total_expired': len(all_expired),
            'total_expiring_soon': len(all_expiring),
            'checked_at': timezone.now().isoformat()
        }

    # ==========================================================================
    # Document History
    # ==========================================================================

    def get_document_history(
        self,
        aircraft_id: uuid.UUID,
        document_type: str
    ) -> List[Dict[str, Any]]:
        """Get version history for a document type."""
        documents = AircraftDocument.objects.filter(
            aircraft_id=aircraft_id,
            document_type=document_type
        ).order_by('-created_at')

        return [
            {
                **self._document_to_dict(doc),
                'is_current': doc.is_current,
                'supersedes_id': str(doc.supersedes_id) if doc.supersedes_id else None,
            }
            for doc in documents
        ]

    # ==========================================================================
    # Bulk Operations
    # ==========================================================================

    def get_documents_by_type(
        self,
        organization_id: uuid.UUID,
        document_type: str,
        current_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all documents of a type across the organization."""
        queryset = AircraftDocument.objects.filter(
            organization_id=organization_id,
            document_type=document_type
        ).select_related('aircraft')

        if current_only:
            queryset = queryset.filter(is_current=True)

        return [
            {
                **self._document_to_dict(doc),
                'aircraft_registration': doc.aircraft.registration,
            }
            for doc in queryset.order_by('aircraft__registration')
        ]

    def check_all_reminders(
        self,
        organization_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Check all documents for reminders and return those needing action."""
        documents = self.get_documents_needing_reminder(organization_id)

        return {
            'documents_needing_reminder': len(documents),
            'documents': documents
        }

    # ==========================================================================
    # Helper Methods
    # ==========================================================================

    def _document_to_dict(self, doc: AircraftDocument) -> Dict[str, Any]:
        """Convert document to dictionary."""
        return {
            'id': str(doc.id),
            'aircraft_id': str(doc.aircraft_id),
            'document_type': doc.document_type,
            'document_type_display': doc.get_document_type_display(),
            'title': doc.title,
            'description': doc.description,
            'file_url': doc.file_url,
            'file_name': doc.file_name,
            'file_size': doc.file_size_display,
            'file_type': doc.file_type,
            'version': doc.version,
            'revision_date': doc.revision_date.isoformat() if doc.revision_date else None,
            'effective_date': doc.effective_date.isoformat() if doc.effective_date else None,
            'expiry_date': doc.expiry_date.isoformat() if doc.expiry_date else None,
            'document_number': doc.document_number,
            'issuing_authority': doc.issuing_authority,
            'is_current': doc.is_current,
            'is_required': doc.is_required,
            'is_expired': doc.is_expired,
            'is_public': doc.is_public,
            'is_downloadable': doc.is_downloadable,
            'tags': doc.tags,
            'created_at': doc.created_at.isoformat(),
            'updated_at': doc.updated_at.isoformat(),
        }

    def _invalidate_cache(self, aircraft_id: uuid.UUID) -> None:
        """Invalidate document cache for an aircraft."""
        cache.delete(f"aircraft_doc_compliance:{aircraft_id}")
        cache.delete(f"aircraft:{aircraft_id}")
        cache.delete(f"aircraft_status:{aircraft_id}")
