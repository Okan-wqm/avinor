# services/document-service/src/tests/test_api.py
"""
API Tests
"""

import uuid
import json
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from io import BytesIO

from django.urls import reverse
from rest_framework import status

pytestmark = pytest.mark.django_db


class TestDocumentAPI:
    """Tests for Document API endpoints."""

    def test_list_documents(self, authenticated_client, sample_document):
        """Test listing documents."""
        response = authenticated_client.get('/api/v1/documents/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_get_document(self, authenticated_client, sample_document):
        """Test getting document details."""
        response = authenticated_client.get(f'/api/v1/documents/{sample_document.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(sample_document.id)
        assert response.data['title'] == sample_document.title

    @patch('apps.core.api.views.document_views.DocumentService')
    @patch('apps.core.api.views.document_views.process_document')
    def test_upload_document(
        self,
        mock_task,
        mock_service_class,
        authenticated_client,
        organization_id,
        user_id,
    ):
        """Test document upload."""
        from apps.core.models import Document, DocumentType, DocumentStatus

        # Create mock document
        mock_doc = Document(
            id=uuid.uuid4(),
            organization_id=organization_id,
            owner_id=user_id,
            title='Uploaded Document',
            original_name='upload.pdf',
            document_type=DocumentType.OTHER,
            status=DocumentStatus.ACTIVE,
            file_path='test/upload.pdf',
            file_extension='pdf',
            file_size=1024,
            uploaded_by=user_id,
        )

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.upload_document.return_value = mock_doc

        # Prepare file
        file_content = BytesIO(b'%PDF-1.4 test content')
        file_content.name = 'test.pdf'

        response = authenticated_client.post(
            '/api/v1/documents/',
            {
                'file': file_content,
                'document_type': 'other',
                'title': 'Test Upload',
            },
            format='multipart',
        )

        assert response.status_code == status.HTTP_201_CREATED
        mock_task.delay.assert_called_once()

    def test_update_document(self, authenticated_client, sample_document):
        """Test updating document."""
        response = authenticated_client.patch(
            f'/api/v1/documents/{sample_document.id}/',
            {'title': 'Updated Title'},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Updated Title'

    def test_delete_document(self, authenticated_client, sample_document):
        """Test soft deleting document."""
        response = authenticated_client.delete(
            f'/api/v1/documents/{sample_document.id}/'
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify soft deleted
        sample_document.refresh_from_db()
        from apps.core.models import DocumentStatus
        assert sample_document.status == DocumentStatus.DELETED

    @patch('apps.core.api.views.document_views.StorageService')
    def test_download_document(self, mock_storage_class, authenticated_client, sample_document):
        """Test document download."""
        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage
        mock_storage.download_file.return_value = b'%PDF-1.4 content'

        response = authenticated_client.get(
            f'/api/v1/documents/{sample_document.id}/download/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == sample_document.mime_type

    def test_search_documents(self, authenticated_client, sample_document):
        """Test document search."""
        response = authenticated_client.post(
            '/api/v1/documents/search/',
            {'query': 'Test'},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert response.data['total'] >= 1

    def test_archive_document(self, authenticated_client, sample_document):
        """Test archiving document."""
        response = authenticated_client.post(
            f'/api/v1/documents/{sample_document.id}/archive/'
        )

        assert response.status_code == status.HTTP_200_OK

        sample_document.refresh_from_db()
        from apps.core.models import DocumentStatus
        assert sample_document.status == DocumentStatus.ARCHIVED


class TestFolderAPI:
    """Tests for Folder API endpoints."""

    def test_list_folders(self, authenticated_client, sample_folder):
        """Test listing folders."""
        response = authenticated_client.get('/api/v1/folders/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_create_folder(self, authenticated_client, organization_id):
        """Test creating folder."""
        response = authenticated_client.post(
            '/api/v1/folders/',
            {'name': 'New Folder'},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Folder'

    def test_get_folder(self, authenticated_client, sample_folder):
        """Test getting folder details."""
        response = authenticated_client.get(f'/api/v1/folders/{sample_folder.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(sample_folder.id)

    def test_update_folder(self, authenticated_client, sample_folder):
        """Test updating folder."""
        response = authenticated_client.patch(
            f'/api/v1/folders/{sample_folder.id}/',
            {'name': 'Updated Folder'},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Folder'

    def test_delete_folder(self, authenticated_client, sample_folder):
        """Test deleting folder."""
        response = authenticated_client.delete(f'/api/v1/folders/{sample_folder.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_folder_tree(self, authenticated_client, sample_folder):
        """Test getting folder tree."""
        response = authenticated_client.get('/api/v1/folders/tree/')

        assert response.status_code == status.HTTP_200_OK

    def test_folder_contents(self, authenticated_client, sample_folder, sample_document):
        """Test getting folder contents."""
        # Move document to folder
        sample_document.folder = sample_folder
        sample_document.save()

        response = authenticated_client.get(
            f'/api/v1/folders/{sample_folder.id}/contents/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['documents']) == 1

    def test_create_nested_folder(self, authenticated_client, sample_folder):
        """Test creating nested folder."""
        response = authenticated_client.post(
            '/api/v1/folders/',
            {
                'name': 'Child Folder',
                'parent_folder_id': str(sample_folder.id),
            },
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['depth'] == 1


class TestSignatureAPI:
    """Tests for Signature API endpoints."""

    def test_list_signatures(self, authenticated_client, sample_document, user_id):
        """Test listing signatures."""
        from apps.core.models import DocumentSignature, SignatureType

        # Create signature
        DocumentSignature.objects.create(
            document=sample_document,
            signer_id=user_id,
            signer_name='Test Signer',
            signer_email='signer@example.com',
            signature_type=SignatureType.TYPED,
            signature_data='Test Signer',
            signature_hash='hash123',
        )

        response = authenticated_client.get('/api/v1/signatures/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    @patch('apps.core.api.views.signature_views.SignatureService')
    def test_create_signature(
        self,
        mock_service_class,
        authenticated_client,
        sample_document,
        user_id,
    ):
        """Test creating signature."""
        from apps.core.models import DocumentSignature, SignatureType, SignatureStatus

        mock_sig = DocumentSignature(
            id=uuid.uuid4(),
            document=sample_document,
            signer_id=user_id,
            signer_name='Test User',
            signer_email='test@example.com',
            signature_type=SignatureType.TYPED,
            signature_data='Test User',
            signature_hash='hash123',
            status=SignatureStatus.VALID,
        )

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.sign_document.return_value = mock_sig

        response = authenticated_client.post(
            '/api/v1/signatures/',
            {
                'document_id': str(sample_document.id),
                'signature_type': 'typed',
                'signature_data': 'Test User',
            },
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED


class TestTemplateAPI:
    """Tests for Template API endpoints."""

    def test_list_templates(self, authenticated_client, sample_template):
        """Test listing templates."""
        response = authenticated_client.get('/api/v1/templates/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_get_template(self, authenticated_client, sample_template):
        """Test getting template details."""
        response = authenticated_client.get(f'/api/v1/templates/{sample_template.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(sample_template.id)

    def test_create_template(self, authenticated_client):
        """Test creating template."""
        response = authenticated_client.post(
            '/api/v1/templates/',
            {
                'name': 'New Template',
                'template_type': 'certificate',
                'content': '<html><body>{{ content }}</body></html>',
            },
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED

    @patch('apps.core.api.views.template_views.TemplateService')
    @patch('apps.core.api.views.template_views.PDFService')
    def test_generate_from_template(
        self,
        mock_pdf_class,
        mock_service_class,
        authenticated_client,
        sample_template,
    ):
        """Test generating document from template."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.generate_document.return_value = b'%PDF-1.4 generated'

        response = authenticated_client.post(
            f'/api/v1/templates/{sample_template.id}/generate/',
            {
                'template_id': str(sample_template.id),
                'variables': {'name': 'John Doe'},
            },
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/pdf'


class TestShareAPI:
    """Tests for Share API endpoints."""

    def test_list_shares(self, authenticated_client, sample_document, user_id):
        """Test listing shares."""
        from apps.core.models import DocumentShare, ShareTargetType, SharePermission

        # Create share
        DocumentShare.objects.create(
            document=sample_document,
            shared_by=user_id,
            target_type=ShareTargetType.PUBLIC,
            permission=SharePermission.VIEW,
        )

        response = authenticated_client.get('/api/v1/shares/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_create_share(self, authenticated_client, sample_document):
        """Test creating share."""
        response = authenticated_client.post(
            '/api/v1/shares/',
            {
                'document_id': str(sample_document.id),
                'target_type': 'public',
                'permission': 'view',
            },
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['share_token'] is not None

    def test_revoke_share(self, authenticated_client, sample_document, user_id):
        """Test revoking share."""
        from apps.core.models import DocumentShare, ShareTargetType, SharePermission

        share = DocumentShare.objects.create(
            document=sample_document,
            shared_by=user_id,
            target_type=ShareTargetType.PUBLIC,
            permission=SharePermission.VIEW,
        )

        response = authenticated_client.delete(
            f'/api/v1/shares/{share.id}/',
            format='json',
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestPublicShareAPI:
    """Tests for Public Share endpoints."""

    def test_get_public_share_info(self, api_client, sample_document, user_id):
        """Test getting public share info."""
        from apps.core.models import DocumentShare, ShareTargetType, SharePermission

        share = DocumentShare.objects.create(
            document=sample_document,
            shared_by=user_id,
            target_type=ShareTargetType.PUBLIC,
            permission=SharePermission.VIEW,
            shared_by_name='Test Sharer',
        )

        response = api_client.get(f'/share/{share.share_token}/')

        assert response.status_code == status.HTTP_200_OK
        assert 'requires_password' in response.data

    def test_access_public_share(self, api_client, sample_document, user_id):
        """Test accessing public share."""
        from apps.core.models import DocumentShare, ShareTargetType, SharePermission

        share = DocumentShare.objects.create(
            document=sample_document,
            shared_by=user_id,
            target_type=ShareTargetType.PUBLIC,
            permission=SharePermission.VIEW,
        )

        response = api_client.post(
            f'/share/{share.share_token}/',
            {'token': share.share_token},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['type'] == 'document'

    def test_access_password_protected_share(self, api_client, sample_document, user_id):
        """Test accessing password protected share."""
        from apps.core.models import DocumentShare, ShareTargetType, SharePermission

        share = DocumentShare.objects.create(
            document=sample_document,
            shared_by=user_id,
            target_type=ShareTargetType.PUBLIC,
            permission=SharePermission.VIEW,
        )
        share.set_password('secret123')
        share.save()

        # Without password should fail
        response = api_client.post(
            f'/share/{share.share_token}/',
            {'token': share.share_token},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # With correct password should succeed
        response = api_client.post(
            f'/share/{share.share_token}/',
            {'token': share.share_token, 'password': 'secret123'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
