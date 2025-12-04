# services/document-service/src/tests/test_models.py
"""
Model Tests
"""

import uuid
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

pytestmark = pytest.mark.django_db


class TestDocumentModel:
    """Tests for Document model."""

    def test_create_document(self, organization_id, user_id):
        """Test document creation."""
        from apps.core.models import Document, DocumentType, DocumentStatus

        document = Document.objects.create(
            organization_id=organization_id,
            owner_id=user_id,
            title='Test Document',
            original_name='test.pdf',
            document_type=DocumentType.LICENSE,
            file_path='test/documents/test.pdf',
            file_extension='pdf',
            mime_type='application/pdf',
            file_size=1024,
            checksum='abc123def456',
            uploaded_by=user_id,
        )

        assert document.id is not None
        assert document.title == 'Test Document'
        assert document.status == DocumentStatus.ACTIVE
        assert document.version == 1
        assert document.is_latest_version is True

    def test_document_is_expired(self, organization_id, user_id):
        """Test document expiry property."""
        from apps.core.models import Document, DocumentType

        # Expired document
        expired_doc = Document.objects.create(
            organization_id=organization_id,
            owner_id=user_id,
            original_name='expired.pdf',
            document_type=DocumentType.MEDICAL,
            file_path='test/expired.pdf',
            file_extension='pdf',
            file_size=1024,
            expiry_date=date.today() - timedelta(days=1),
            uploaded_by=user_id,
        )
        assert expired_doc.is_expired is True

        # Valid document
        valid_doc = Document.objects.create(
            organization_id=organization_id,
            owner_id=user_id,
            original_name='valid.pdf',
            document_type=DocumentType.MEDICAL,
            file_path='test/valid.pdf',
            file_extension='pdf',
            file_size=1024,
            expiry_date=date.today() + timedelta(days=30),
            uploaded_by=user_id,
        )
        assert valid_doc.is_expired is False

    def test_document_days_until_expiry(self, organization_id, user_id):
        """Test days until expiry calculation."""
        from apps.core.models import Document, DocumentType

        document = Document.objects.create(
            organization_id=organization_id,
            owner_id=user_id,
            original_name='test.pdf',
            document_type=DocumentType.CERTIFICATE,
            file_path='test/test.pdf',
            file_extension='pdf',
            file_size=1024,
            expiry_date=date.today() + timedelta(days=10),
            uploaded_by=user_id,
        )

        assert document.days_until_expiry == 10

    def test_document_soft_delete(self, sample_document, user_id):
        """Test soft delete functionality."""
        from apps.core.models import DocumentStatus

        sample_document.soft_delete(user_id)

        assert sample_document.status == DocumentStatus.DELETED
        assert sample_document.deleted_at is not None
        assert sample_document.deleted_by == user_id

    def test_document_restore(self, sample_document, user_id):
        """Test document restore."""
        from apps.core.models import DocumentStatus

        sample_document.soft_delete(user_id)
        sample_document.restore()

        assert sample_document.status == DocumentStatus.ACTIVE
        assert sample_document.deleted_at is None
        assert sample_document.deleted_by is None

    def test_document_archive(self, sample_document):
        """Test document archive."""
        from apps.core.models import DocumentStatus

        sample_document.archive()

        assert sample_document.status == DocumentStatus.ARCHIVED

    def test_document_record_view(self, sample_document, user_id):
        """Test view recording."""
        initial_count = sample_document.view_count

        sample_document.record_view(user_id)

        assert sample_document.view_count == initial_count + 1
        assert sample_document.last_accessed_at is not None
        assert sample_document.last_accessed_by == user_id

    def test_document_record_download(self, sample_document, user_id):
        """Test download recording."""
        initial_count = sample_document.download_count

        sample_document.record_download(user_id)

        assert sample_document.download_count == initial_count + 1

    def test_document_file_size_display(self, organization_id, user_id):
        """Test file size display formatting."""
        from apps.core.models import Document, DocumentType

        # Test various sizes
        sizes = [
            (500, '500.00 B'),
            (1024, '1.00 KB'),
            (1024 * 1024, '1.00 MB'),
            (1024 * 1024 * 1024, '1.00 GB'),
        ]

        for size, expected in sizes:
            doc = Document.objects.create(
                organization_id=organization_id,
                owner_id=user_id,
                original_name=f'test_{size}.pdf',
                document_type=DocumentType.OTHER,
                file_path=f'test/test_{size}.pdf',
                file_extension='pdf',
                file_size=size,
                uploaded_by=user_id,
            )
            assert doc.file_size_display == expected

    def test_document_is_pdf(self, organization_id, user_id):
        """Test is_pdf property."""
        from apps.core.models import Document, DocumentType

        pdf_doc = Document.objects.create(
            organization_id=organization_id,
            owner_id=user_id,
            original_name='test.pdf',
            document_type=DocumentType.OTHER,
            file_path='test/test.pdf',
            file_extension='pdf',
            file_size=1024,
            uploaded_by=user_id,
        )
        assert pdf_doc.is_pdf is True

        jpg_doc = Document.objects.create(
            organization_id=organization_id,
            owner_id=user_id,
            original_name='test.jpg',
            document_type=DocumentType.OTHER,
            file_path='test/test.jpg',
            file_extension='jpg',
            file_size=1024,
            uploaded_by=user_id,
        )
        assert jpg_doc.is_pdf is False

    def test_document_is_image(self, organization_id, user_id):
        """Test is_image property."""
        from apps.core.models import Document, DocumentType

        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']

        for ext in image_extensions:
            doc = Document.objects.create(
                organization_id=organization_id,
                owner_id=user_id,
                original_name=f'test.{ext}',
                document_type=DocumentType.OTHER,
                file_path=f'test/test.{ext}',
                file_extension=ext,
                file_size=1024,
                uploaded_by=user_id,
            )
            assert doc.is_image is True, f"Expected {ext} to be identified as image"


class TestDocumentFolderModel:
    """Tests for DocumentFolder model."""

    def test_create_folder(self, organization_id, user_id):
        """Test folder creation."""
        from apps.core.models import DocumentFolder

        folder = DocumentFolder.objects.create(
            organization_id=organization_id,
            owner_id=user_id,
            name='Test Folder',
            path='/Test Folder',
            depth=0,
        )

        assert folder.id is not None
        assert folder.name == 'Test Folder'
        assert folder.depth == 0

    def test_folder_hierarchy(self, organization_id, user_id):
        """Test folder hierarchy."""
        from apps.core.models import DocumentFolder

        parent = DocumentFolder.objects.create(
            organization_id=organization_id,
            owner_id=user_id,
            name='Parent',
            path='/Parent',
            depth=0,
        )

        child = DocumentFolder.objects.create(
            organization_id=organization_id,
            owner_id=user_id,
            name='Child',
            parent_folder=parent,
            path='/Parent/Child',
            depth=1,
        )

        assert child.parent_folder == parent
        assert child.depth == 1
        assert parent in list(child.get_ancestors())

    def test_folder_recalculate_statistics(self, sample_folder, sample_document):
        """Test folder statistics recalculation."""
        # Move document to folder
        sample_document.folder = sample_folder
        sample_document.save()

        # Recalculate
        sample_folder.recalculate_statistics()

        assert sample_folder.document_count == 1
        assert sample_folder.total_size_bytes == sample_document.file_size


class TestDocumentTemplateModel:
    """Tests for DocumentTemplate model."""

    def test_create_template(self, organization_id, user_id):
        """Test template creation."""
        from apps.core.models import DocumentTemplate, TemplateType

        template = DocumentTemplate.objects.create(
            organization_id=organization_id,
            name='Test Template',
            template_type=TemplateType.CERTIFICATE,
            content='<html><body>{{ content }}</body></html>',
            created_by=user_id,
        )

        assert template.id is not None
        assert template.is_active is True
        assert template.version == 1

    def test_template_variable_definitions(self, organization_id, user_id):
        """Test template variable definitions."""
        from apps.core.models import DocumentTemplate, TemplateType

        template = DocumentTemplate.objects.create(
            organization_id=organization_id,
            name='Test Template',
            template_type=TemplateType.CERTIFICATE,
            content='<html><body>{{ name }} - {{ date }}</body></html>',
            variable_definitions=[
                {'name': 'name', 'type': 'string', 'required': True},
                {'name': 'date', 'type': 'date', 'required': True},
            ],
            created_by=user_id,
        )

        assert len(template.variable_definitions) == 2


class TestDocumentShareModel:
    """Tests for DocumentShare model."""

    def test_create_share(self, sample_document, user_id):
        """Test share creation."""
        from apps.core.models import DocumentShare, ShareTargetType, SharePermission

        share = DocumentShare.objects.create(
            document=sample_document,
            shared_by=user_id,
            target_type=ShareTargetType.PUBLIC,
            permission=SharePermission.VIEW,
        )

        assert share.id is not None
        assert share.share_token is not None
        assert len(share.share_token) == 64

    def test_share_is_active(self, sample_document, user_id):
        """Test share active status."""
        from apps.core.models import DocumentShare, ShareTargetType, SharePermission

        # Active share
        active_share = DocumentShare.objects.create(
            document=sample_document,
            shared_by=user_id,
            target_type=ShareTargetType.PUBLIC,
            permission=SharePermission.VIEW,
        )
        assert active_share.is_active is True

        # Expired share
        expired_share = DocumentShare.objects.create(
            document=sample_document,
            shared_by=user_id,
            target_type=ShareTargetType.PUBLIC,
            permission=SharePermission.VIEW,
            expires_at=timezone.now() - timedelta(days=1),
        )
        assert expired_share.is_active is False

    def test_share_password(self, sample_document, user_id):
        """Test share password protection."""
        from apps.core.models import DocumentShare, ShareTargetType, SharePermission

        share = DocumentShare.objects.create(
            document=sample_document,
            shared_by=user_id,
            target_type=ShareTargetType.PUBLIC,
            permission=SharePermission.VIEW,
        )

        share.set_password('secret123')

        assert share.has_password is True
        assert share.check_password('secret123') is True
        assert share.check_password('wrong') is False


class TestSignatureModel:
    """Tests for DocumentSignature model."""

    def test_create_signature(self, sample_document, user_id):
        """Test signature creation."""
        from apps.core.models import DocumentSignature, SignatureType, SignatureStatus

        signature = DocumentSignature.objects.create(
            document=sample_document,
            signer_id=user_id,
            signer_name='Test Signer',
            signer_email='signer@example.com',
            signature_type=SignatureType.DRAWN,
            signature_data='base64encodeddata',
            signature_hash='hash123',
        )

        assert signature.id is not None
        assert signature.status == SignatureStatus.VALID
        assert signature.verification_token is not None

    def test_signature_is_valid(self, sample_document, user_id):
        """Test signature validity."""
        from apps.core.models import DocumentSignature, SignatureType, SignatureStatus

        valid_sig = DocumentSignature.objects.create(
            document=sample_document,
            signer_id=user_id,
            signer_name='Test Signer',
            signer_email='signer@example.com',
            signature_type=SignatureType.TYPED,
            signature_data='John Doe',
            signature_hash='hash123',
        )
        assert valid_sig.is_valid is True

        revoked_sig = DocumentSignature.objects.create(
            document=sample_document,
            signer_id=user_id,
            signer_name='Test Signer 2',
            signer_email='signer2@example.com',
            signature_type=SignatureType.TYPED,
            signature_data='Jane Doe',
            signature_hash='hash456',
            status=SignatureStatus.REVOKED,
        )
        assert revoked_sig.is_valid is False
