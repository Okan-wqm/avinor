# services/document-service/src/tests/test_services.py
"""
Service Tests
"""

import uuid
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.django_db


class TestStorageService:
    """Tests for StorageService."""

    def test_upload_file(self, mock_storage):
        """Test file upload."""
        result = mock_storage.upload_file(
            file_content=b'test content',
            key='test/document.pdf',
            content_type='application/pdf',
        )

        assert result['key'] == 'test/document.pdf'
        mock_storage.upload_file.assert_called_once()

    def test_download_file(self, mock_storage):
        """Test file download."""
        content = mock_storage.download_file('test/document.pdf')

        assert content == b'Test file content'
        mock_storage.download_file.assert_called_once_with('test/document.pdf')

    def test_get_presigned_url(self, mock_storage):
        """Test presigned URL generation."""
        url = mock_storage.get_presigned_url('test/document.pdf', expires_in=3600)

        assert 'storage.example.com' in url
        mock_storage.get_presigned_url.assert_called_once()


class TestDocumentService:
    """Tests for DocumentService."""

    @patch('apps.core.services.document_service.StorageService')
    def test_upload_document(self, mock_storage_class, organization_id, user_id):
        """Test document upload."""
        from apps.core.services import DocumentService
        from apps.core.models import DocumentType

        # Setup mock
        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage
        mock_storage.upload_file.return_value = {
            'key': 'test/document.pdf',
            'etag': '"abc123"',
            'size': 1024,
        }

        service = DocumentService()
        document = service.upload_document(
            organization_id=organization_id,
            owner_id=user_id,
            file_content=b'%PDF-1.4 test content',
            filename='test.pdf',
            document_type=DocumentType.OTHER,
            uploaded_by=user_id,
        )

        assert document.id is not None
        assert document.original_name == 'test.pdf'
        assert document.file_extension == 'pdf'

    @patch('apps.core.services.document_service.StorageService')
    def test_create_new_version(self, mock_storage_class, sample_document, user_id):
        """Test creating new document version."""
        from apps.core.services import DocumentService

        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage
        mock_storage.upload_file.return_value = {
            'key': 'test/document_v2.pdf',
            'etag': '"def456"',
            'size': 2048,
        }

        service = DocumentService()
        new_version = service.create_new_version(
            document_id=str(sample_document.id),
            user_id=user_id,
            file_content=b'%PDF-1.4 updated content',
            filename='test_v2.pdf',
        )

        assert new_version.version == 2
        assert new_version.is_latest_version is True
        assert new_version.parent_document_id == sample_document.id

        # Old version should no longer be latest
        sample_document.refresh_from_db()
        assert sample_document.is_latest_version is False

    @patch('apps.core.services.document_service.StorageService')
    def test_get_download_url(self, mock_storage_class, sample_document, user_id):
        """Test getting download URL."""
        from apps.core.services import DocumentService

        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage
        mock_storage.get_presigned_url.return_value = 'https://storage.example.com/signed'

        service = DocumentService()
        url = service.get_download_url(str(sample_document.id), user_id)

        assert 'storage.example.com' in url

    def test_search_documents(self, sample_document, organization_id, user_id):
        """Test document search."""
        from apps.core.services import DocumentService

        service = DocumentService()
        results = service.search_documents(
            organization_id=organization_id,
            user_id=user_id,
            query='Test',
        )

        assert sample_document in list(results)


class TestFolderService:
    """Tests for FolderService."""

    def test_create_folder(self, organization_id, user_id):
        """Test folder creation."""
        from apps.core.services import FolderService

        service = FolderService()
        folder = service.create_folder(
            organization_id=organization_id,
            owner_id=user_id,
            name='New Folder',
        )

        assert folder.id is not None
        assert folder.name == 'New Folder'
        assert folder.path == '/New Folder'
        assert folder.depth == 0

    def test_create_subfolder(self, sample_folder, organization_id, user_id):
        """Test subfolder creation."""
        from apps.core.services import FolderService

        service = FolderService()
        subfolder = service.create_folder(
            organization_id=organization_id,
            owner_id=user_id,
            name='Subfolder',
            parent_folder_id=sample_folder.id,
        )

        assert subfolder.parent_folder == sample_folder
        assert subfolder.depth == 1
        assert subfolder.path == f'{sample_folder.path}/Subfolder'

    def test_get_folder_tree(self, sample_folder, organization_id, user_id):
        """Test folder tree retrieval."""
        from apps.core.services import FolderService

        service = FolderService()

        # Create nested structure
        service.create_folder(
            organization_id=organization_id,
            owner_id=user_id,
            name='Child 1',
            parent_folder_id=sample_folder.id,
        )

        tree = service.get_folder_tree(organization_id)

        assert len(tree) >= 1

    def test_ensure_folder_path(self, organization_id, user_id):
        """Test folder path creation."""
        from apps.core.services import FolderService

        service = FolderService()
        folder = service.ensure_folder_path(
            organization_id=organization_id,
            path='/Level1/Level2/Level3',
            owner_id=user_id,
        )

        assert folder.name == 'Level3'
        assert folder.depth == 2

    def test_delete_empty_folder(self, sample_folder, user_id):
        """Test deleting empty folder."""
        from apps.core.services import FolderService

        service = FolderService()
        service.delete_folder(
            folder_id=str(sample_folder.id),
            user_id=user_id,
        )

        from apps.core.models import DocumentFolder
        assert not DocumentFolder.objects.filter(id=sample_folder.id).exists()

    def test_delete_non_empty_folder_fails(self, sample_folder, sample_document, user_id):
        """Test that deleting non-empty folder fails without recursive flag."""
        from apps.core.services import FolderService

        # Move document to folder
        sample_document.folder = sample_folder
        sample_document.save()

        service = FolderService()

        with pytest.raises(ValueError, match='not empty'):
            service.delete_folder(
                folder_id=str(sample_folder.id),
                user_id=user_id,
                recursive=False,
            )


class TestTemplateService:
    """Tests for TemplateService."""

    def test_create_template(self, organization_id, user_id):
        """Test template creation."""
        from apps.core.services import TemplateService
        from apps.core.models import TemplateType

        service = TemplateService()
        template = service.create_template(
            organization_id=organization_id,
            name='Test Template',
            template_type=TemplateType.CERTIFICATE,
            content='<html><body>{{ name }}</body></html>',
            created_by=user_id,
        )

        assert template.id is not None
        assert template.name == 'Test Template'

    @patch('apps.core.services.template_service.PDFService')
    def test_generate_document(self, mock_pdf_class, sample_template, organization_id, user_id):
        """Test document generation from template."""
        from apps.core.services import TemplateService

        mock_pdf = MagicMock()
        mock_pdf_class.return_value = mock_pdf
        mock_pdf.generate_pdf_from_html.return_value = b'%PDF-1.4 generated'

        service = TemplateService()
        result = service.generate_document(
            template_id=str(sample_template.id),
            variables={'name': 'John Doe'},
            organization_id=organization_id,
            user_id=user_id,
        )

        assert result == b'%PDF-1.4 generated'
        mock_pdf.generate_pdf_from_html.assert_called_once()


class TestSignatureService:
    """Tests for SignatureService."""

    def test_sign_document(self, sample_document, user_id):
        """Test document signing."""
        from apps.core.services import SignatureService
        from apps.core.models import SignatureType

        service = SignatureService()
        signature = service.sign_document(
            document=sample_document,
            signer_id=user_id,
            signer_name='John Doe',
            signer_email='john@example.com',
            signature_type=SignatureType.TYPED,
            signature_data='John Doe',
        )

        assert signature.id is not None
        assert signature.signer_name == 'John Doe'
        assert signature.is_valid is True

    def test_verify_signature(self, sample_document, user_id):
        """Test signature verification."""
        from apps.core.services import SignatureService
        from apps.core.models import SignatureType

        service = SignatureService()

        # Create signature
        signature = service.sign_document(
            document=sample_document,
            signer_id=user_id,
            signer_name='John Doe',
            signer_email='john@example.com',
            signature_type=SignatureType.TYPED,
            signature_data='John Doe',
        )

        # Verify
        result = service.verify_signature(signature)

        assert result['is_valid'] is True

    def test_revoke_signature(self, sample_document, user_id):
        """Test signature revocation."""
        from apps.core.services import SignatureService
        from apps.core.models import SignatureType, SignatureStatus

        service = SignatureService()

        # Create signature
        signature = service.sign_document(
            document=sample_document,
            signer_id=user_id,
            signer_name='John Doe',
            signer_email='john@example.com',
            signature_type=SignatureType.TYPED,
            signature_data='John Doe',
        )

        # Revoke
        service.revoke_signature(
            signature=signature,
            revoked_by=user_id,
            reason='Test revocation',
        )

        signature.refresh_from_db()
        assert signature.status == SignatureStatus.REVOKED
        assert signature.is_valid is False


class TestShareService:
    """Tests for ShareService."""

    def test_create_document_share(self, sample_document, user_id):
        """Test document share creation."""
        from apps.core.services import ShareService
        from apps.core.models import ShareTargetType, SharePermission

        service = ShareService()
        share = service.create_share(
            document=sample_document,
            shared_by=user_id,
            target_type=ShareTargetType.PUBLIC,
            permission=SharePermission.VIEW,
        )

        assert share.id is not None
        assert share.share_token is not None
        assert share.is_active is True

    def test_create_password_protected_share(self, sample_document, user_id):
        """Test password protected share."""
        from apps.core.services import ShareService
        from apps.core.models import ShareTargetType, SharePermission

        service = ShareService()
        share = service.create_share(
            document=sample_document,
            shared_by=user_id,
            target_type=ShareTargetType.PUBLIC,
            permission=SharePermission.DOWNLOAD,
            password='secret123',
        )

        assert share.has_password is True
        assert share.check_password('secret123') is True

    def test_revoke_share(self, sample_document, user_id):
        """Test share revocation."""
        from apps.core.services import ShareService
        from apps.core.models import ShareTargetType, SharePermission

        service = ShareService()
        share = service.create_share(
            document=sample_document,
            shared_by=user_id,
            target_type=ShareTargetType.PUBLIC,
            permission=SharePermission.VIEW,
        )

        service.revoke_share(share, reason='No longer needed')

        share.refresh_from_db()
        assert share.revoked_at is not None
        assert share.is_active is False

    def test_log_access(self, sample_document, user_id):
        """Test access logging."""
        from apps.core.services import ShareService
        from apps.core.models import ShareTargetType, SharePermission, ShareAccessLog

        service = ShareService()
        share = service.create_share(
            document=sample_document,
            shared_by=user_id,
            target_type=ShareTargetType.PUBLIC,
            permission=SharePermission.VIEW,
        )

        service.log_access(
            share=share,
            access_type='view',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
        )

        log = ShareAccessLog.objects.filter(share=share).first()
        assert log is not None
        assert log.ip_address == '192.168.1.1'
