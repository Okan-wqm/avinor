# services/document-service/src/apps/core/services/thumbnail_service.py
"""
Thumbnail Service

Thumbnail and preview generation for documents.
Supports images, PDFs, and common document formats.
"""

import logging
from typing import Tuple, Optional
from io import BytesIO

# Pillow for image processing
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

# pdf2image for PDF rendering
try:
    from pdf2image import convert_from_bytes
    from pdf2image.exceptions import PDFPageCountError
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False


logger = logging.getLogger(__name__)


class ThumbnailError(Exception):
    """Thumbnail generation error."""
    pass


class ThumbnailService:
    """
    Service for generating thumbnails and previews.

    Supports:
    - Image formats (JPEG, PNG, GIF, WebP, BMP, TIFF)
    - PDF documents
    - Configurable thumbnail sizes
    - Preview images for PDFs
    """

    # Default thumbnail sizes
    THUMBNAIL_SIZE = (200, 200)
    PREVIEW_SIZE = (800, 800)
    SMALL_THUMBNAIL = (100, 100)
    LARGE_THUMBNAIL = (400, 400)

    # Supported formats
    IMAGE_FORMATS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff', 'tif'}
    PDF_FORMATS = {'pdf'}
    SUPPORTED_FORMATS = IMAGE_FORMATS | PDF_FORMATS

    def __init__(self):
        if not PILLOW_AVAILABLE:
            logger.warning("Pillow not available - image thumbnails disabled")
        if not PDF2IMAGE_AVAILABLE:
            logger.warning("pdf2image not available - PDF thumbnails disabled")

    # =========================================================================
    # THUMBNAIL GENERATION
    # =========================================================================

    def generate_thumbnail(
        self,
        file_content: bytes,
        file_extension: str,
        size: Tuple[int, int] = None,
        output_format: str = 'JPEG',
        quality: int = 85,
    ) -> bytes:
        """
        Generate a thumbnail from file content.

        Args:
            file_content: Raw file bytes
            file_extension: File extension (without dot)
            size: Thumbnail size (width, height)
            output_format: Output format (JPEG, PNG, WEBP)
            quality: JPEG/WebP quality (1-100)

        Returns:
            Thumbnail image bytes
        """
        ext = file_extension.lower().lstrip('.')
        size = size or self.THUMBNAIL_SIZE

        if ext in self.IMAGE_FORMATS:
            return self._thumbnail_from_image(
                file_content, size, output_format, quality
            )
        elif ext in self.PDF_FORMATS:
            return self._thumbnail_from_pdf(
                file_content, size, output_format, quality
            )
        else:
            raise ThumbnailError(f"Unsupported format: {ext}")

    def generate_preview(
        self,
        file_content: bytes,
        file_extension: str,
        size: Tuple[int, int] = None,
        output_format: str = 'JPEG',
        quality: int = 90,
        page: int = 1,
    ) -> bytes:
        """
        Generate a larger preview image.

        Args:
            file_content: Raw file bytes
            file_extension: File extension
            size: Preview size (width, height)
            output_format: Output format
            quality: Image quality
            page: Page number for PDFs (1-indexed)

        Returns:
            Preview image bytes
        """
        ext = file_extension.lower().lstrip('.')
        size = size or self.PREVIEW_SIZE

        if ext in self.IMAGE_FORMATS:
            return self._thumbnail_from_image(
                file_content, size, output_format, quality
            )
        elif ext in self.PDF_FORMATS:
            return self._preview_from_pdf(
                file_content, size, output_format, quality, page
            )
        else:
            raise ThumbnailError(f"Unsupported format: {ext}")

    # =========================================================================
    # IMAGE PROCESSING
    # =========================================================================

    def _thumbnail_from_image(
        self,
        file_content: bytes,
        size: Tuple[int, int],
        output_format: str,
        quality: int,
    ) -> bytes:
        """Generate thumbnail from image file."""
        if not PILLOW_AVAILABLE:
            raise ThumbnailError("Pillow not installed")

        try:
            # Open image
            image = Image.open(BytesIO(file_content))

            # Handle EXIF orientation
            image = self._fix_orientation(image)

            # Convert to RGB if necessary (for JPEG output)
            if output_format.upper() == 'JPEG' and image.mode in ('RGBA', 'P', 'LA'):
                # Create white background for transparent images
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif output_format.upper() == 'JPEG' and image.mode != 'RGB':
                image = image.convert('RGB')

            # Create thumbnail (maintains aspect ratio)
            image.thumbnail(size, Image.Resampling.LANCZOS)

            # Save to bytes
            output = BytesIO()
            save_kwargs = {'format': output_format}

            if output_format.upper() in ('JPEG', 'WEBP'):
                save_kwargs['quality'] = quality
                save_kwargs['optimize'] = True

            if output_format.upper() == 'PNG':
                save_kwargs['optimize'] = True

            image.save(output, **save_kwargs)

            return output.getvalue()

        except Exception as e:
            logger.error(f"Image thumbnail generation failed: {e}")
            raise ThumbnailError(f"Failed to generate thumbnail: {e}")

    def _fix_orientation(self, image: 'Image.Image') -> 'Image.Image':
        """Fix image orientation based on EXIF data."""
        try:
            exif = image.getexif()
            if exif:
                orientation = exif.get(0x0112)  # Orientation tag
                if orientation:
                    rotations = {
                        3: Image.Transpose.ROTATE_180,
                        6: Image.Transpose.ROTATE_270,
                        8: Image.Transpose.ROTATE_90,
                    }
                    if orientation in rotations:
                        image = image.transpose(rotations[orientation])
        except Exception:
            pass  # Ignore EXIF errors
        return image

    # =========================================================================
    # PDF PROCESSING
    # =========================================================================

    def _thumbnail_from_pdf(
        self,
        file_content: bytes,
        size: Tuple[int, int],
        output_format: str,
        quality: int,
    ) -> bytes:
        """Generate thumbnail from PDF (first page)."""
        if not PDF2IMAGE_AVAILABLE:
            raise ThumbnailError("pdf2image not installed")

        try:
            # Convert first page to image
            images = convert_from_bytes(
                file_content,
                first_page=1,
                last_page=1,
                dpi=72,  # Low DPI for thumbnail
                size=size,
            )

            if not images:
                raise ThumbnailError("No pages in PDF")

            # Process the image
            return self._process_pil_image(images[0], size, output_format, quality)

        except PDFPageCountError as e:
            logger.error(f"PDF page count error: {e}")
            raise ThumbnailError(f"Failed to read PDF: {e}")
        except Exception as e:
            logger.error(f"PDF thumbnail generation failed: {e}")
            raise ThumbnailError(f"Failed to generate PDF thumbnail: {e}")

    def _preview_from_pdf(
        self,
        file_content: bytes,
        size: Tuple[int, int],
        output_format: str,
        quality: int,
        page: int = 1,
    ) -> bytes:
        """Generate preview image from specific PDF page."""
        if not PDF2IMAGE_AVAILABLE:
            raise ThumbnailError("pdf2image not installed")

        try:
            # Convert specific page to image
            images = convert_from_bytes(
                file_content,
                first_page=page,
                last_page=page,
                dpi=150,  # Higher DPI for preview
            )

            if not images:
                raise ThumbnailError(f"Page {page} not found in PDF")

            # Process the image
            return self._process_pil_image(images[0], size, output_format, quality)

        except PDFPageCountError as e:
            logger.error(f"PDF page count error: {e}")
            raise ThumbnailError(f"Failed to read PDF: {e}")
        except Exception as e:
            logger.error(f"PDF preview generation failed: {e}")
            raise ThumbnailError(f"Failed to generate PDF preview: {e}")

    def _process_pil_image(
        self,
        image: 'Image.Image',
        size: Tuple[int, int],
        output_format: str,
        quality: int,
    ) -> bytes:
        """Process PIL Image to output bytes."""
        # Convert to RGB if necessary
        if output_format.upper() == 'JPEG' and image.mode != 'RGB':
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'RGBA':
                background.paste(image, mask=image.split()[-1])
            else:
                background.paste(image)
            image = background

        # Resize
        image.thumbnail(size, Image.Resampling.LANCZOS)

        # Save to bytes
        output = BytesIO()
        save_kwargs = {'format': output_format}

        if output_format.upper() in ('JPEG', 'WEBP'):
            save_kwargs['quality'] = quality
            save_kwargs['optimize'] = True

        image.save(output, **save_kwargs)

        return output.getvalue()

    # =========================================================================
    # BATCH PROCESSING
    # =========================================================================

    def generate_all_pdf_pages(
        self,
        file_content: bytes,
        size: Tuple[int, int] = None,
        output_format: str = 'JPEG',
        quality: int = 85,
        max_pages: int = 50,
    ) -> list:
        """
        Generate thumbnails for all pages of a PDF.

        Args:
            file_content: PDF bytes
            size: Thumbnail size
            output_format: Output format
            quality: Image quality
            max_pages: Maximum pages to process

        Returns:
            List of (page_number, image_bytes) tuples
        """
        if not PDF2IMAGE_AVAILABLE:
            raise ThumbnailError("pdf2image not installed")

        size = size or self.THUMBNAIL_SIZE

        try:
            images = convert_from_bytes(
                file_content,
                dpi=72,
                last_page=max_pages,
            )

            results = []
            for i, image in enumerate(images, 1):
                image_bytes = self._process_pil_image(
                    image, size, output_format, quality
                )
                results.append((i, image_bytes))

            return results

        except Exception as e:
            logger.error(f"PDF batch processing failed: {e}")
            raise ThumbnailError(f"Failed to process PDF pages: {e}")

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def can_generate_thumbnail(self, file_extension: str) -> bool:
        """
        Check if thumbnail can be generated for this file type.

        Args:
            file_extension: File extension (with or without dot)

        Returns:
            True if thumbnail generation is supported
        """
        ext = file_extension.lower().lstrip('.')
        return ext in self.SUPPORTED_FORMATS

    def get_image_info(self, file_content: bytes) -> dict:
        """
        Get information about an image file.

        Args:
            file_content: Image bytes

        Returns:
            Dict with width, height, format, mode
        """
        if not PILLOW_AVAILABLE:
            raise ThumbnailError("Pillow not installed")

        try:
            image = Image.open(BytesIO(file_content))
            return {
                'width': image.width,
                'height': image.height,
                'format': image.format,
                'mode': image.mode,
            }
        except Exception as e:
            raise ThumbnailError(f"Failed to read image: {e}")

    def resize_image(
        self,
        file_content: bytes,
        width: int = None,
        height: int = None,
        maintain_aspect: bool = True,
        output_format: str = None,
        quality: int = 90,
    ) -> bytes:
        """
        Resize an image to specific dimensions.

        Args:
            file_content: Image bytes
            width: Target width (None to calculate from height)
            height: Target height (None to calculate from width)
            maintain_aspect: Maintain aspect ratio
            output_format: Output format (None to keep original)
            quality: Output quality

        Returns:
            Resized image bytes
        """
        if not PILLOW_AVAILABLE:
            raise ThumbnailError("Pillow not installed")

        if not width and not height:
            raise ThumbnailError("Width or height must be specified")

        try:
            image = Image.open(BytesIO(file_content))
            image = self._fix_orientation(image)

            original_width, original_height = image.size

            if maintain_aspect:
                if width and not height:
                    ratio = width / original_width
                    height = int(original_height * ratio)
                elif height and not width:
                    ratio = height / original_height
                    width = int(original_width * ratio)
                else:
                    # Both specified - use the smaller ratio
                    ratio = min(width / original_width, height / original_height)
                    width = int(original_width * ratio)
                    height = int(original_height * ratio)

            # Resize
            image = image.resize((width, height), Image.Resampling.LANCZOS)

            # Determine output format
            out_format = output_format or image.format or 'JPEG'

            # Convert mode if necessary
            if out_format.upper() == 'JPEG' and image.mode != 'RGB':
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image)
                image = background

            # Save
            output = BytesIO()
            save_kwargs = {'format': out_format}
            if out_format.upper() in ('JPEG', 'WEBP'):
                save_kwargs['quality'] = quality

            image.save(output, **save_kwargs)

            return output.getvalue()

        except Exception as e:
            logger.error(f"Image resize failed: {e}")
            raise ThumbnailError(f"Failed to resize image: {e}")
