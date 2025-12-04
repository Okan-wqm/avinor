# services/document-service/src/apps/core/services/pdf_service.py
"""
PDF Service

PDF generation and manipulation using WeasyPrint.
Handles template rendering, PDF creation, and merging.
"""

import uuid
import logging
from typing import Dict, Any, Optional, List
from io import BytesIO

from django.template import Template, Context
from django.conf import settings

# WeasyPrint for PDF generation
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

# PyPDF2 for PDF manipulation
try:
    from PyPDF2 import PdfReader, PdfWriter, PdfMerger
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

# Jinja2 for templating
from jinja2 import Environment, BaseLoader, select_autoescape


logger = logging.getLogger(__name__)


class PDFError(Exception):
    """PDF generation error."""
    pass


class PDFService:
    """
    Service for PDF generation and manipulation.

    Provides:
    - HTML to PDF conversion
    - Template-based PDF generation
    - PDF merging and splitting
    - Page count extraction
    - PDF metadata
    """

    def __init__(self):
        if not WEASYPRINT_AVAILABLE:
            logger.warning("WeasyPrint not available - PDF generation disabled")

        # Jinja2 environment for template rendering
        self.jinja_env = Environment(
            loader=BaseLoader(),
            autoescape=select_autoescape(['html', 'xml']),
        )

        # Add custom filters
        self.jinja_env.filters['date'] = self._date_filter
        self.jinja_env.filters['datetime'] = self._datetime_filter
        self.jinja_env.filters['currency'] = self._currency_filter
        self.jinja_env.filters['hours'] = self._hours_filter

    # =========================================================================
    # PDF GENERATION
    # =========================================================================

    def generate_pdf_from_html(
        self,
        html_content: str,
        css_content: str = None,
        base_url: str = None,
    ) -> bytes:
        """
        Generate PDF from HTML content.

        Args:
            html_content: HTML string
            css_content: Optional CSS string
            base_url: Base URL for resolving relative paths

        Returns:
            PDF bytes
        """
        if not WEASYPRINT_AVAILABLE:
            raise PDFError("WeasyPrint not installed")

        try:
            font_config = FontConfiguration()

            html = HTML(
                string=html_content,
                base_url=base_url or settings.BASE_DIR,
            )

            stylesheets = []
            if css_content:
                stylesheets.append(CSS(string=css_content, font_config=font_config))

            # Generate PDF
            pdf_bytes = html.write_pdf(
                stylesheets=stylesheets,
                font_config=font_config,
            )

            logger.debug(f"Generated PDF: {len(pdf_bytes)} bytes")

            return pdf_bytes

        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            raise PDFError(f"Failed to generate PDF: {e}")

    def generate_pdf_from_template(
        self,
        template_content: str,
        variables: Dict[str, Any],
        css_content: str = None,
        header_content: str = None,
        footer_content: str = None,
        page_size: str = 'A4',
        orientation: str = 'portrait',
        margins: Dict[str, int] = None,
    ) -> bytes:
        """
        Generate PDF from a template with variable substitution.

        Args:
            template_content: Jinja2/HTML template string
            variables: Variables to substitute
            css_content: Optional CSS string
            header_content: Optional header HTML
            footer_content: Optional footer HTML
            page_size: Page size (A4, Letter, etc.)
            orientation: portrait or landscape
            margins: Margins in mm {top, right, bottom, left}

        Returns:
            PDF bytes
        """
        # Set default margins
        margins = margins or {'top': 20, 'right': 20, 'bottom': 20, 'left': 20}

        # Render template
        try:
            template = self.jinja_env.from_string(template_content)
            rendered_content = template.render(**variables)
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            raise PDFError(f"Failed to render template: {e}")

        # Build complete HTML document
        html = self._build_html_document(
            content=rendered_content,
            header=header_content,
            footer=footer_content,
            css=css_content,
            page_size=page_size,
            orientation=orientation,
            margins=margins,
        )

        return self.generate_pdf_from_html(html)

    def _build_html_document(
        self,
        content: str,
        header: str = None,
        footer: str = None,
        css: str = None,
        page_size: str = 'A4',
        orientation: str = 'portrait',
        margins: Dict[str, int] = None,
    ) -> str:
        """Build complete HTML document with headers/footers."""
        margins = margins or {'top': 20, 'right': 20, 'bottom': 20, 'left': 20}

        # Page CSS
        page_css = f"""
            @page {{
                size: {page_size} {orientation};
                margin: {margins['top']}mm {margins['right']}mm {margins['bottom']}mm {margins['left']}mm;
            }}
        """

        if header:
            page_css += f"""
                @page {{
                    @top-center {{
                        content: element(header);
                    }}
                }}
                #header {{
                    position: running(header);
                }}
            """

        if footer:
            page_css += f"""
                @page {{
                    @bottom-center {{
                        content: element(footer);
                    }}
                }}
                #footer {{
                    position: running(footer);
                }}
            """

        # Base CSS
        base_css = """
            * {
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 11pt;
                line-height: 1.5;
                color: #333;
            }
            h1 { font-size: 24pt; margin: 0 0 12pt 0; }
            h2 { font-size: 18pt; margin: 0 0 10pt 0; }
            h3 { font-size: 14pt; margin: 0 0 8pt 0; }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                padding: 8px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th {
                background-color: #f5f5f5;
                font-weight: 600;
            }
            .text-right { text-align: right; }
            .text-center { text-align: center; }
            .bold { font-weight: 600; }
            .page-break { page-break-after: always; }
        """

        # Combine CSS
        all_css = page_css + base_css
        if css:
            all_css += css

        # Build HTML
        header_html = f'<div id="header">{header}</div>' if header else ''
        footer_html = f'<div id="footer">{footer}</div>' if footer else ''

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>{all_css}</style>
        </head>
        <body>
            {header_html}
            {footer_html}
            <div id="content">
                {content}
            </div>
        </body>
        </html>
        """

    # =========================================================================
    # PDF MANIPULATION
    # =========================================================================

    def get_page_count(self, pdf_content: bytes) -> int:
        """
        Get page count from PDF.

        Args:
            pdf_content: PDF bytes

        Returns:
            Number of pages
        """
        if not PYPDF2_AVAILABLE:
            raise PDFError("PyPDF2 not installed")

        try:
            reader = PdfReader(BytesIO(pdf_content))
            return len(reader.pages)
        except Exception as e:
            logger.error(f"Failed to read PDF: {e}")
            raise PDFError(f"Failed to read PDF: {e}")

    def get_pdf_metadata(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        Get PDF metadata.

        Args:
            pdf_content: PDF bytes

        Returns:
            Dict with metadata
        """
        if not PYPDF2_AVAILABLE:
            raise PDFError("PyPDF2 not installed")

        try:
            reader = PdfReader(BytesIO(pdf_content))

            metadata = {
                'page_count': len(reader.pages),
                'title': reader.metadata.get('/Title', '') if reader.metadata else '',
                'author': reader.metadata.get('/Author', '') if reader.metadata else '',
                'subject': reader.metadata.get('/Subject', '') if reader.metadata else '',
                'creator': reader.metadata.get('/Creator', '') if reader.metadata else '',
            }

            # Get page sizes
            if reader.pages:
                first_page = reader.pages[0]
                box = first_page.mediabox
                metadata['width'] = float(box.width)
                metadata['height'] = float(box.height)

            return metadata

        except Exception as e:
            logger.error(f"Failed to read PDF metadata: {e}")
            raise PDFError(f"Failed to read PDF metadata: {e}")

    def merge_pdfs(self, pdf_contents: List[bytes]) -> bytes:
        """
        Merge multiple PDFs into one.

        Args:
            pdf_contents: List of PDF bytes

        Returns:
            Merged PDF bytes
        """
        if not PYPDF2_AVAILABLE:
            raise PDFError("PyPDF2 not installed")

        if not pdf_contents:
            raise PDFError("No PDFs to merge")

        try:
            merger = PdfMerger()

            for pdf_content in pdf_contents:
                merger.append(BytesIO(pdf_content))

            output = BytesIO()
            merger.write(output)
            merger.close()

            return output.getvalue()

        except Exception as e:
            logger.error(f"Failed to merge PDFs: {e}")
            raise PDFError(f"Failed to merge PDFs: {e}")

    def split_pdf(
        self,
        pdf_content: bytes,
        start_page: int = 1,
        end_page: int = None,
    ) -> bytes:
        """
        Extract pages from a PDF.

        Args:
            pdf_content: PDF bytes
            start_page: First page (1-indexed)
            end_page: Last page (inclusive, None for end)

        Returns:
            New PDF bytes with extracted pages
        """
        if not PYPDF2_AVAILABLE:
            raise PDFError("PyPDF2 not installed")

        try:
            reader = PdfReader(BytesIO(pdf_content))
            writer = PdfWriter()

            total_pages = len(reader.pages)
            start_idx = max(0, start_page - 1)
            end_idx = min(total_pages, end_page or total_pages)

            for i in range(start_idx, end_idx):
                writer.add_page(reader.pages[i])

            output = BytesIO()
            writer.write(output)

            return output.getvalue()

        except Exception as e:
            logger.error(f"Failed to split PDF: {e}")
            raise PDFError(f"Failed to split PDF: {e}")

    def extract_text(self, pdf_content: bytes) -> str:
        """
        Extract text from PDF.

        Args:
            pdf_content: PDF bytes

        Returns:
            Extracted text
        """
        if not PYPDF2_AVAILABLE:
            raise PDFError("PyPDF2 not installed")

        try:
            reader = PdfReader(BytesIO(pdf_content))
            text_parts = []

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            return '\n\n'.join(text_parts)

        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise PDFError(f"Failed to extract text: {e}")

    # =========================================================================
    # TEMPLATE FILTERS
    # =========================================================================

    @staticmethod
    def _date_filter(value, format_str='%B %d, %Y'):
        """Format date for templates."""
        if value is None:
            return ''
        try:
            if hasattr(value, 'strftime'):
                return value.strftime(format_str)
            return str(value)
        except Exception:
            return str(value)

    @staticmethod
    def _datetime_filter(value, format_str='%B %d, %Y %H:%M'):
        """Format datetime for templates."""
        if value is None:
            return ''
        try:
            if hasattr(value, 'strftime'):
                return value.strftime(format_str)
            return str(value)
        except Exception:
            return str(value)

    @staticmethod
    def _currency_filter(value, symbol='$'):
        """Format currency for templates."""
        try:
            return f"{symbol}{float(value):,.2f}"
        except (ValueError, TypeError):
            return f"{symbol}0.00"

    @staticmethod
    def _hours_filter(value, decimals=1):
        """Format hours for templates."""
        try:
            hours = float(value)
            return f"{hours:.{decimals}f} hrs"
        except (ValueError, TypeError):
            return "0.0 hrs"

    # =========================================================================
    # PREDEFINED TEMPLATES
    # =========================================================================

    def generate_certificate(
        self,
        organization_name: str,
        certificate_title: str,
        recipient_name: str,
        description: str,
        issue_date,
        certificate_number: str = None,
        instructor_name: str = None,
        logo_base64: str = None,
    ) -> bytes:
        """
        Generate a standard certificate PDF.

        Args:
            organization_name: Issuing organization
            certificate_title: Certificate title
            recipient_name: Recipient's name
            description: Certificate description
            issue_date: Date of issue
            certificate_number: Optional certificate number
            instructor_name: Optional instructor/issuer name
            logo_base64: Optional base64-encoded logo

        Returns:
            PDF bytes
        """
        template = """
        <div style="text-align: center; padding: 40px;">
            {% if logo %}
            <img src="data:image/png;base64,{{ logo }}" style="height: 60px; margin-bottom: 20px;">
            {% endif %}

            <h2 style="color: #666; font-weight: normal; margin-bottom: 5px;">{{ organization }}</h2>

            <div style="border-top: 2px solid #333; border-bottom: 2px solid #333; padding: 20px 0; margin: 30px 0;">
                <h1 style="font-size: 36pt; margin: 0; color: #1a5276;">{{ title }}</h1>
            </div>

            <p style="font-size: 14pt; color: #666; margin-bottom: 30px;">This certifies that</p>

            <h2 style="font-size: 28pt; font-family: Georgia, serif; color: #333; margin: 20px 0;">
                {{ recipient }}
            </h2>

            <p style="font-size: 14pt; max-width: 500px; margin: 30px auto; color: #444;">
                {{ description }}
            </p>

            {% if certificate_number %}
            <p style="font-size: 11pt; color: #888; margin-top: 40px;">
                Certificate No: {{ certificate_number }}
            </p>
            {% endif %}

            <div style="display: flex; justify-content: space-between; margin-top: 60px; padding: 0 50px;">
                <div style="text-align: center;">
                    <div style="border-top: 1px solid #333; width: 200px; padding-top: 10px;">
                        {{ issue_date|date }}
                    </div>
                    <p style="font-size: 10pt; color: #666;">Date</p>
                </div>

                {% if instructor %}
                <div style="text-align: center;">
                    <div style="border-top: 1px solid #333; width: 200px; padding-top: 10px;">
                        {{ instructor }}
                    </div>
                    <p style="font-size: 10pt; color: #666;">Instructor/Examiner</p>
                </div>
                {% endif %}
            </div>
        </div>
        """

        css = """
            body {
                background: linear-gradient(45deg, #f8f9fa, #ffffff);
            }
        """

        return self.generate_pdf_from_template(
            template_content=template,
            variables={
                'organization': organization_name,
                'title': certificate_title,
                'recipient': recipient_name,
                'description': description,
                'issue_date': issue_date,
                'certificate_number': certificate_number,
                'instructor': instructor_name,
                'logo': logo_base64,
            },
            css_content=css,
            orientation='landscape',
            margins={'top': 15, 'right': 15, 'bottom': 15, 'left': 15},
        )
