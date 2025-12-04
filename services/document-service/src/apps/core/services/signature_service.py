# services/document-service/src/apps/core/services/signature_service.py
"""
Signature Service

Digital signature operations for documents.
"""

import uuid
import hashlib
import logging
from typing import List, Optional

from django.db import transaction
from django.utils import timezone

from ..models import (
    Document,
    DocumentSignature,
    SignatureType,
    SignatureStatus,
)
from ..models.signature import SignatureRequest


logger = logging.getLogger(__name__)


class SignatureError(Exception):
    """Signature operation error."""
    pass


class SignatureService:
    """
    Service for document signature operations.

    Handles:
    - Creating digital signatures
    - Signature verification
    - Signature requests
    - Audit trail management
    """

    # =========================================================================
    # SIGN DOCUMENT
    # =========================================================================

    @transaction.atomic
    def sign_document(
        self,
        document_id: uuid.UUID,
        signer_id: uuid.UUID,
        signer_name: str,
        signature_type: str,
        signature_data: str,
        signer_email: str = None,
        signer_title: str = None,
        signer_role: str = None,
        page_number: int = None,
        position_x: float = None,
        position_y: float = None,
        width: float = None,
        height: float = None,
        ip_address: str = None,
        user_agent: str = None,
        geolocation: dict = None,
        request_id: uuid.UUID = None,
    ) -> DocumentSignature:
        """
        Sign a document.

        Args:
            document_id: Document UUID
            signer_id: Signer's user UUID
            signer_name: Signer's full name
            signature_type: Type of signature (drawn, typed, etc.)
            signature_data: Signature data (base64 image or text)
            signer_email: Signer's email
            signer_title: Signer's title/position
            signer_role: Role in context of document
            page_number: Page where signature is placed
            position_x: X position on page
            position_y: Y position on page
            width: Signature width
            height: Signature height
            ip_address: IP address of signer
            user_agent: Browser/client info
            geolocation: Location data
            request_id: Related signature request UUID

        Returns:
            Created DocumentSignature instance
        """
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            raise SignatureError(f"Document not found: {document_id}")

        # Generate signature hash
        signature_hash = self._generate_signature_hash(
            document_id=document_id,
            signer_id=signer_id,
            signature_data=signature_data,
        )

        # Create signature
        signature = DocumentSignature.objects.create(
            organization_id=document.organization_id,
            document=document,
            signer_id=signer_id,
            signer_name=signer_name,
            signer_email=signer_email,
            signer_title=signer_title,
            signer_role=signer_role,
            signature_type=signature_type,
            signature_data=signature_data,
            signature_hash=signature_hash,
            page_number=page_number,
            position_x=position_x,
            position_y=position_y,
            width=width,
            height=height,
            ip_address=ip_address,
            user_agent=user_agent,
            geolocation=geolocation or {},
            signed_at=timezone.now(),
            status=SignatureStatus.VALID,
            request_id=request_id,
        )

        # Update document
        document.is_signed = True
        document.signature_count += 1
        document.save(update_fields=['is_signed', 'signature_count'])

        # Update signature request if exists
        if request_id:
            try:
                request = SignatureRequest.objects.get(id=request_id)
                request.mark_signed(signature)
            except SignatureRequest.DoesNotExist:
                pass

        logger.info(
            f"Document {document_id} signed by {signer_name} ({signature.id})"
        )

        return signature

    # =========================================================================
    # SIGNATURE REQUESTS
    # =========================================================================

    @transaction.atomic
    def request_signature(
        self,
        document_id: uuid.UUID,
        requested_by: uuid.UUID,
        requested_by_name: str,
        signer_id: uuid.UUID,
        signer_email: str,
        signer_name: str,
        signer_role: str = None,
        message: str = None,
        deadline=None,
        page_number: int = None,
        position_x: float = None,
        position_y: float = None,
    ) -> SignatureRequest:
        """
        Create a signature request.

        Args:
            document_id: Document UUID
            requested_by: Requester's user UUID
            requested_by_name: Requester's name
            signer_id: Target signer's user UUID
            signer_email: Target signer's email
            signer_name: Target signer's name
            signer_role: Expected role of signer
            message: Message to signer
            deadline: Signature deadline
            page_number: Suggested page for signature
            position_x: Suggested X position
            position_y: Suggested Y position

        Returns:
            Created SignatureRequest instance
        """
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            raise SignatureError(f"Document not found: {document_id}")

        # Check for existing pending request
        existing = SignatureRequest.objects.filter(
            document_id=document_id,
            signer_id=signer_id,
            status='pending',
        ).exists()

        if existing:
            raise SignatureError(
                f"Pending signature request already exists for this user"
            )

        request = SignatureRequest.objects.create(
            organization_id=document.organization_id,
            document=document,
            requested_by=requested_by,
            requested_by_name=requested_by_name,
            signer_id=signer_id,
            signer_email=signer_email,
            signer_name=signer_name,
            signer_role=signer_role,
            message=message,
            deadline=deadline,
            page_number=page_number,
            position_x=position_x,
            position_y=position_y,
        )

        # Update document flag
        document.requires_signature = True
        if deadline and (not document.signature_deadline or deadline < document.signature_deadline):
            document.signature_deadline = deadline
        document.save(update_fields=['requires_signature', 'signature_deadline'])

        logger.info(
            f"Signature request created for {signer_name} on document {document_id}"
        )

        return request

    def get_pending_requests(
        self,
        signer_id: uuid.UUID,
        organization_id: uuid.UUID = None,
    ) -> List[SignatureRequest]:
        """
        Get pending signature requests for a user.

        Args:
            signer_id: User UUID
            organization_id: Optional organization filter

        Returns:
            List of SignatureRequest instances
        """
        queryset = SignatureRequest.objects.filter(
            signer_id=signer_id,
            status='pending',
        ).select_related('document')

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        return list(queryset.order_by('-created_at'))

    def decline_signature_request(
        self,
        request_id: uuid.UUID,
        signer_id: uuid.UUID,
        reason: str = None,
    ) -> SignatureRequest:
        """
        Decline a signature request.

        Args:
            request_id: Request UUID
            signer_id: Signer's UUID (for verification)
            reason: Reason for declining

        Returns:
            Updated SignatureRequest instance
        """
        try:
            request = SignatureRequest.objects.get(
                id=request_id,
                signer_id=signer_id,
            )
        except SignatureRequest.DoesNotExist:
            raise SignatureError(f"Signature request not found: {request_id}")

        if request.status != 'pending':
            raise SignatureError(
                f"Cannot decline request with status: {request.status}"
            )

        request.decline(reason)

        logger.info(f"Signature request {request_id} declined")

        return request

    def cancel_signature_request(
        self,
        request_id: uuid.UUID,
        cancelled_by: uuid.UUID,
    ) -> SignatureRequest:
        """
        Cancel a signature request (by requester).

        Args:
            request_id: Request UUID
            cancelled_by: User cancelling (must be requester)

        Returns:
            Updated SignatureRequest instance
        """
        try:
            request = SignatureRequest.objects.get(
                id=request_id,
                requested_by=cancelled_by,
            )
        except SignatureRequest.DoesNotExist:
            raise SignatureError(f"Signature request not found: {request_id}")

        if request.status != 'pending':
            raise SignatureError(
                f"Cannot cancel request with status: {request.status}"
            )

        request.cancel()

        logger.info(f"Signature request {request_id} cancelled")

        return request

    # =========================================================================
    # VERIFICATION
    # =========================================================================

    def verify_signature(
        self,
        signature_id: uuid.UUID,
    ) -> tuple[bool, str]:
        """
        Verify a signature's validity.

        Args:
            signature_id: Signature UUID

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            signature = DocumentSignature.objects.get(id=signature_id)
        except DocumentSignature.DoesNotExist:
            return False, "Signature not found"

        return signature.verify()

    def verify_all_signatures(
        self,
        document_id: uuid.UUID,
    ) -> dict:
        """
        Verify all signatures on a document.

        Args:
            document_id: Document UUID

        Returns:
            Dict with verification results
        """
        signatures = DocumentSignature.objects.filter(document_id=document_id)

        results = {
            'total': signatures.count(),
            'valid': 0,
            'invalid': 0,
            'signatures': [],
        }

        for sig in signatures:
            is_valid, message = sig.verify()
            results['signatures'].append({
                'id': str(sig.id),
                'signer_name': sig.signer_name,
                'signed_at': sig.signed_at.isoformat(),
                'is_valid': is_valid,
                'message': message,
            })
            if is_valid:
                results['valid'] += 1
            else:
                results['invalid'] += 1

        results['all_valid'] = results['invalid'] == 0

        return results

    # =========================================================================
    # RETRIEVAL
    # =========================================================================

    def get_document_signatures(
        self,
        document_id: uuid.UUID,
    ) -> List[DocumentSignature]:
        """
        Get all signatures for a document.

        Args:
            document_id: Document UUID

        Returns:
            List of DocumentSignature instances
        """
        return list(
            DocumentSignature.objects.filter(
                document_id=document_id
            ).order_by('signed_at')
        )

    def get_user_signatures(
        self,
        signer_id: uuid.UUID,
        organization_id: uuid.UUID = None,
        limit: int = 100,
    ) -> List[DocumentSignature]:
        """
        Get signatures by a user.

        Args:
            signer_id: Signer's UUID
            organization_id: Optional organization filter
            limit: Maximum results

        Returns:
            List of DocumentSignature instances
        """
        queryset = DocumentSignature.objects.filter(
            signer_id=signer_id
        ).select_related('document')

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        return list(queryset.order_by('-signed_at')[:limit])

    # =========================================================================
    # REVOCATION
    # =========================================================================

    @transaction.atomic
    def revoke_signature(
        self,
        signature_id: uuid.UUID,
        revoked_by: uuid.UUID,
        reason: str,
    ) -> DocumentSignature:
        """
        Revoke a signature.

        Args:
            signature_id: Signature UUID
            revoked_by: User revoking
            reason: Reason for revocation

        Returns:
            Updated DocumentSignature instance
        """
        try:
            signature = DocumentSignature.objects.get(id=signature_id)
        except DocumentSignature.DoesNotExist:
            raise SignatureError(f"Signature not found: {signature_id}")

        if signature.status == SignatureStatus.REVOKED:
            raise SignatureError("Signature already revoked")

        signature.revoke(revoked_by, reason)

        # Update document signature count
        document = signature.document
        valid_count = DocumentSignature.objects.filter(
            document=document,
            status=SignatureStatus.VALID,
        ).count()

        document.signature_count = valid_count
        document.is_signed = valid_count > 0
        document.save(update_fields=['signature_count', 'is_signed'])

        logger.info(f"Signature {signature_id} revoked")

        return signature

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _generate_signature_hash(
        self,
        document_id: uuid.UUID,
        signer_id: uuid.UUID,
        signature_data: str,
    ) -> str:
        """Generate a hash for signature verification."""
        content = f"{document_id}{signer_id}{signature_data}{timezone.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()
