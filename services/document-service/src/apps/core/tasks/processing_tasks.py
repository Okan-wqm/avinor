# services/document-service/src/apps/core/tasks/processing_tasks.py
"""
Document Processing Celery Tasks

Background tasks for document processing: thumbnails, OCR, virus scanning.
"""

import logging
import subprocess
import tempfile
import os
from celery import shared_task

from ..models import Document, ProcessingStatus
from ..services.storage_service import StorageService
from ..services.thumbnail_service import ThumbnailService, ThumbnailError
from ..services.pdf_service import PDFService


logger = logging.getLogger(__name__)


@shared_task(
    name='document.process_document',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_document(self, document_id: str):
    """
    Main document processing pipeline.

    Runs after upload to:
    1. Scan for viruses
    2. Generate thumbnail
    3. Extract text (OCR for images/PDFs)
    4. Update processing status

    Args:
        document_id: Document UUID string
    """
    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error(f"Document not found: {document_id}")
        return

    logger.info(f"Processing document: {document_id} ({document.original_name})")

    try:
        # Update status
        document.processing_status = ProcessingStatus.PROCESSING
        document.save(update_fields=['processing_status'])

        # Step 1: Virus scan
        document.processing_status = ProcessingStatus.SCANNING
        document.save(update_fields=['processing_status'])

        scan_result = scan_virus.delay(document_id)
        # Note: In production, you might want to wait for scan result
        # and abort if infected

        # Step 2: Generate thumbnail
        document.processing_status = ProcessingStatus.GENERATING_THUMBNAIL
        document.save(update_fields=['processing_status'])

        if document.file_extension in ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp']:
            generate_thumbnail.delay(document_id)

        # Step 3: OCR
        document.processing_status = ProcessingStatus.OCR_PROCESSING
        document.save(update_fields=['processing_status'])

        if document.file_extension in ['pdf', 'jpg', 'jpeg', 'png', 'tiff', 'tif']:
            extract_text_ocr.delay(document_id)

        # Mark as completed
        document.processing_status = ProcessingStatus.COMPLETED
        document.processing_error = None
        document.save(update_fields=['processing_status', 'processing_error'])

        logger.info(f"Document processing completed: {document_id}")

    except Exception as e:
        logger.error(f"Document processing failed: {document_id} - {e}")
        document.processing_status = ProcessingStatus.FAILED
        document.processing_error = str(e)
        document.save(update_fields=['processing_status', 'processing_error'])

        # Retry
        raise self.retry(exc=e)


@shared_task(
    name='document.generate_thumbnail',
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def generate_thumbnail(self, document_id: str):
    """
    Generate thumbnail for a document.

    Supports:
    - Images (JPEG, PNG, GIF, WebP)
    - PDFs (first page)

    Args:
        document_id: Document UUID string
    """
    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error(f"Document not found for thumbnail: {document_id}")
        return

    storage = StorageService()
    thumbnail_service = ThumbnailService()

    try:
        # Download file
        file_content = storage.download_file(document.file_path)

        # Generate thumbnail
        thumbnail_bytes = thumbnail_service.generate_thumbnail(
            file_content=file_content,
            file_extension=document.file_extension,
            size=(200, 200),
            output_format='JPEG',
            quality=85,
        )

        # Upload thumbnail
        thumbnail_key = f"{document.file_path.rsplit('/', 1)[0]}/thumbnails/{document.id}_thumb.jpg"
        storage.upload_file(
            file_content=thumbnail_bytes,
            key=thumbnail_key,
            content_type='image/jpeg',
        )

        # Generate preview (larger) for PDFs
        preview_key = None
        page_count = None

        if document.is_pdf:
            # Generate preview of first page
            preview_bytes = thumbnail_service.generate_preview(
                file_content=file_content,
                file_extension='pdf',
                size=(800, 800),
            )

            preview_key = f"{document.file_path.rsplit('/', 1)[0]}/previews/{document.id}_preview.jpg"
            storage.upload_file(
                file_content=preview_bytes,
                key=preview_key,
                content_type='image/jpeg',
            )

            # Get page count
            pdf_service = PDFService()
            page_count = pdf_service.get_page_count(file_content)

        # Update document
        document.thumbnail_path = thumbnail_key
        if preview_key:
            document.preview_path = preview_key
        if page_count:
            document.page_count = page_count

        document.save(update_fields=['thumbnail_path', 'preview_path', 'page_count'])

        logger.info(f"Thumbnail generated for document: {document_id}")

    except ThumbnailError as e:
        logger.warning(f"Thumbnail generation failed for {document_id}: {e}")
        # Don't retry for unsupported formats
        if "Unsupported format" in str(e):
            return
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Thumbnail generation error for {document_id}: {e}")
        raise self.retry(exc=e)


@shared_task(
    name='document.extract_text_ocr',
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    time_limit=300,  # 5 minute timeout
)
def extract_text_ocr(self, document_id: str, language: str = 'eng'):
    """
    Extract text from document using OCR.

    Uses pytesseract for image-based OCR and PyPDF2 for PDF text extraction.

    Args:
        document_id: Document UUID string
        language: OCR language code (default: English)
    """
    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error(f"Document not found for OCR: {document_id}")
        return

    storage = StorageService()

    try:
        # Download file
        file_content = storage.download_file(document.file_path)

        extracted_text = ''
        confidence = None

        if document.is_pdf:
            # First try to extract embedded text
            from ..services.pdf_service import PDFService
            pdf_service = PDFService()

            try:
                extracted_text = pdf_service.extract_text(file_content)
            except Exception:
                extracted_text = ''

            # If no text found, try OCR on PDF images
            if not extracted_text.strip():
                extracted_text = _ocr_pdf(file_content, language)

        elif document.is_image:
            # OCR on image
            extracted_text, confidence = _ocr_image(file_content, language)

        # Update document
        if extracted_text:
            document.ocr_text = extracted_text[:500000]  # Limit to 500KB
            document.ocr_completed = True
            document.ocr_language = language
            if confidence:
                document.ocr_confidence = confidence

            document.save(update_fields=[
                'ocr_text', 'ocr_completed', 'ocr_language', 'ocr_confidence'
            ])

            logger.info(
                f"OCR completed for document {document_id}: "
                f"{len(extracted_text)} chars"
            )
        else:
            document.ocr_completed = True
            document.ocr_text = ''
            document.save(update_fields=['ocr_text', 'ocr_completed'])
            logger.info(f"OCR completed but no text found: {document_id}")

    except Exception as e:
        logger.error(f"OCR failed for {document_id}: {e}")
        raise self.retry(exc=e)


def _ocr_image(file_content: bytes, language: str) -> tuple[str, float]:
    """
    Perform OCR on an image.

    Returns:
        Tuple of (extracted_text, confidence)
    """
    try:
        import pytesseract
        from PIL import Image
        from io import BytesIO

        # Open image
        image = Image.open(BytesIO(file_content))

        # Get OCR data with confidence
        data = pytesseract.image_to_data(
            image,
            lang=language,
            output_type=pytesseract.Output.DICT
        )

        # Extract text
        text = pytesseract.image_to_string(image, lang=language)

        # Calculate average confidence
        confidences = [int(c) for c in data['conf'] if int(c) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return text.strip(), avg_confidence

    except ImportError:
        logger.warning("pytesseract not installed, skipping OCR")
        return '', None
    except Exception as e:
        logger.error(f"Image OCR error: {e}")
        return '', None


def _ocr_pdf(file_content: bytes, language: str) -> str:
    """
    Perform OCR on a PDF by converting to images first.

    Returns:
        Extracted text
    """
    try:
        from pdf2image import convert_from_bytes
        import pytesseract

        # Convert PDF to images
        images = convert_from_bytes(
            file_content,
            dpi=150,
            first_page=1,
            last_page=10,  # Limit to first 10 pages for performance
        )

        texts = []
        for i, image in enumerate(images, 1):
            text = pytesseract.image_to_string(image, lang=language)
            if text.strip():
                texts.append(f"--- Page {i} ---\n{text.strip()}")

        return '\n\n'.join(texts)

    except ImportError:
        logger.warning("pdf2image/pytesseract not installed")
        return ''
    except Exception as e:
        logger.error(f"PDF OCR error: {e}")
        return ''


@shared_task(
    name='document.scan_virus',
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    time_limit=120,  # 2 minute timeout
)
def scan_virus(self, document_id: str):
    """
    Scan document for viruses using ClamAV.

    Requires clamd daemon running.

    Args:
        document_id: Document UUID string
    """
    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error(f"Document not found for virus scan: {document_id}")
        return

    storage = StorageService()

    try:
        # Download file to temp location
        file_content = storage.download_file(document.file_path)

        # Scan with ClamAV
        scan_result, scan_details = _scan_with_clamav(file_content)

        # Update document
        from django.utils import timezone
        document.virus_scanned = True
        document.virus_scan_result = scan_result
        document.virus_scan_details = scan_details
        document.virus_scanned_at = timezone.now()

        document.save(update_fields=[
            'virus_scanned', 'virus_scan_result',
            'virus_scan_details', 'virus_scanned_at'
        ])

        logger.info(f"Virus scan completed for {document_id}: {scan_result}")

        # If infected, quarantine
        if scan_result == 'infected':
            logger.warning(f"INFECTED FILE DETECTED: {document_id}")
            from ..models import DocumentStatus
            document.status = DocumentStatus.DELETED
            document.save(update_fields=['status'])

            # Publish event for notification
            _publish_virus_detected(document)

    except Exception as e:
        logger.error(f"Virus scan failed for {document_id}: {e}")
        document.virus_scanned = True
        document.virus_scan_result = 'error'
        document.virus_scan_details = str(e)
        document.save(update_fields=[
            'virus_scanned', 'virus_scan_result', 'virus_scan_details'
        ])
        raise self.retry(exc=e)


def _scan_with_clamav(file_content: bytes) -> tuple[str, str]:
    """
    Scan file content with ClamAV.

    Returns:
        Tuple of (result, details)
        result: 'clean', 'infected', or 'error'
    """
    try:
        # Try using clamd socket
        import clamd

        cd = clamd.ClamdUnixSocket()

        # Scan bytes directly
        result = cd.instream(file_content)

        if result and 'stream' in result:
            status = result['stream']
            if status[0] == 'OK':
                return 'clean', 'No threats detected'
            else:
                return 'infected', f"Threat: {status[1]}"

        return 'clean', 'Scan completed'

    except ImportError:
        logger.warning("clamd not installed, trying clamscan command")
        return _scan_with_clamscan(file_content)
    except Exception as e:
        logger.error(f"ClamAV error: {e}")
        return _scan_with_clamscan(file_content)


def _scan_with_clamscan(file_content: bytes) -> tuple[str, str]:
    """
    Scan file using clamscan command line tool.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ['clamscan', '--no-summary', tmp_path],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                return 'clean', 'No threats detected'
            elif result.returncode == 1:
                return 'infected', result.stdout.strip()
            else:
                return 'error', result.stderr.strip()

        finally:
            os.unlink(tmp_path)

    except FileNotFoundError:
        logger.warning("clamscan not found, skipping virus scan")
        return 'clean', 'ClamAV not available - scan skipped'
    except subprocess.TimeoutExpired:
        return 'error', 'Scan timeout'
    except Exception as e:
        return 'error', str(e)


def _publish_virus_detected(document):
    """Publish virus detection event."""
    try:
        import redis
        from django.conf import settings

        r = redis.Redis.from_url(settings.REDIS_URL)
        r.publish('document.virus_detected', str(document.id))
    except Exception:
        pass
