# services/document-service/src/tests/conftest.py
"""
Pytest Configuration and Fixtures
"""

import uuid
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Return API test client."""
    return APIClient()


@pytest.fixture
def organization_id():
    """Return test organization ID."""
    return uuid.uuid4()


@pytest.fixture
def user_id():
    """Return test user ID."""
    return uuid.uuid4()


@pytest.fixture
def authenticated_client(api_client, organization_id, user_id):
    """Return authenticated API client with headers."""
    api_client.credentials(
        HTTP_X_ORGANIZATION_ID=str(organization_id),
        HTTP_X_USER_ID=str(user_id),
        HTTP_X_USER_NAME='Test User',
        HTTP_X_USER_EMAIL='test@example.com',
    )
    return api_client


@pytest.fixture
def request_factory():
    """Return request factory."""
    return RequestFactory()


@pytest.fixture
def mock_storage():
    """Mock storage service."""
    with patch('apps.core.services.storage_service.StorageService') as mock:
        instance = MagicMock()
        mock.return_value = instance

        # Mock upload
        instance.upload_file.return_value = {
            'key': 'test/document.pdf',
            'etag': '"abc123"',
            'size': 1024,
        }

        # Mock download
        instance.download_file.return_value = b'Test file content'

        # Mock presigned URL
        instance.get_presigned_url.return_value = 'https://storage.example.com/test/document.pdf?signed=1'

        yield instance


@pytest.fixture
def mock_pdf_service():
    """Mock PDF service."""
    with patch('apps.core.services.pdf_service.PDFService') as mock:
        instance = MagicMock()
        mock.return_value = instance

        instance.generate_pdf_from_html.return_value = b'%PDF-1.4 mock content'
        instance.generate_pdf_from_template.return_value = b'%PDF-1.4 mock content'
        instance.get_page_count.return_value = 1

        yield instance


@pytest.fixture
def mock_thumbnail_service():
    """Mock thumbnail service."""
    with patch('apps.core.services.thumbnail_service.ThumbnailService') as mock:
        instance = MagicMock()
        mock.return_value = instance

        instance.generate_thumbnail.return_value = b'\x89PNG mock thumbnail'
        instance.generate_preview.return_value = b'\x89PNG mock preview'

        yield instance


@pytest.fixture
def sample_document(organization_id, user_id):
    """Create sample document for testing."""
    from apps.core.models import Document, DocumentType, DocumentStatus

    return Document.objects.create(
        organization_id=organization_id,
        owner_id=user_id,
        title='Test Document',
        original_name='test.pdf',
        document_type=DocumentType.OTHER,
        status=DocumentStatus.ACTIVE,
        file_path='test/documents/test.pdf',
        file_extension='pdf',
        mime_type='application/pdf',
        file_size=1024,
        checksum='abc123',
        uploaded_by=user_id,
    )


@pytest.fixture
def sample_folder(organization_id, user_id):
    """Create sample folder for testing."""
    from apps.core.models import DocumentFolder

    return DocumentFolder.objects.create(
        organization_id=organization_id,
        owner_id=user_id,
        name='Test Folder',
        path='/Test Folder',
        depth=0,
    )


@pytest.fixture
def sample_template(organization_id, user_id):
    """Create sample template for testing."""
    from apps.core.models import DocumentTemplate, TemplateType

    return DocumentTemplate.objects.create(
        organization_id=organization_id,
        name='Test Template',
        template_type=TemplateType.CERTIFICATE,
        content='<html><body>{{ name }}</body></html>',
        variable_definitions=[
            {'name': 'name', 'type': 'string', 'required': True}
        ],
        created_by=user_id,
    )


@pytest.fixture
def sample_pdf_file():
    """Return sample PDF file content."""
    return b'%PDF-1.4 test content'


@pytest.fixture
def sample_image_file():
    """Return sample image file content."""
    # Minimal valid PNG
    return (
        b'\x89PNG\r\n\x1a\n'
        b'\x00\x00\x00\rIHDR'
        b'\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02'
        b'\x00\x00\x00\x90wS\xde'
        b'\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N'
        b'\x00\x00\x00\x00IEND\xaeB`\x82'
    )
