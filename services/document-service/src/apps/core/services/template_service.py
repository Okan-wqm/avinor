# services/document-service/src/apps/core/services/template_service.py
"""
Template Service

Document template management and PDF generation from templates.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import date

from django.db import transaction

from ..models import Document, DocumentTemplate, TemplateType, OutputFormat
from .pdf_service import PDFService, PDFError
from .storage_service import StorageService


logger = logging.getLogger(__name__)


class TemplateError(Exception):
    """Template operation error."""
    pass


class TemplateService:
    """
    Service for document template operations.

    Handles:
    - Template CRUD operations
    - Document generation from templates
    - Variable validation
    - Preview generation
    """

    def __init__(self):
        self.pdf_service = PDFService()
        self.storage = StorageService()

    # =========================================================================
    # CREATE
    # =========================================================================

    @transaction.atomic
    def create_template(
        self,
        organization_id: uuid.UUID,
        name: str,
        template_type: str,
        template_content: str,
        code: str = None,
        description: str = None,
        output_format: str = OutputFormat.PDF,
        variables: list = None,
        sample_data: dict = None,
        header_content: str = None,
        footer_content: str = None,
        styles: str = None,
        page_size: str = 'A4',
        page_orientation: str = 'portrait',
        margins: dict = None,
        logo_path: str = None,
        signature_fields: list = None,
        is_system: bool = False,
        created_by: uuid.UUID = None,
    ) -> DocumentTemplate:
        """
        Create a new document template.

        Args:
            organization_id: Organization UUID (None for system templates)
            name: Template name
            template_type: Type of template
            template_content: HTML/Jinja2 template content
            code: Unique code for programmatic access
            description: Template description
            output_format: Output format (PDF, DOCX, HTML)
            variables: Variable definitions list
            sample_data: Sample data for preview
            header_content: Header HTML
            footer_content: Footer HTML
            styles: CSS styles
            page_size: Page size (A4, Letter, etc.)
            page_orientation: portrait or landscape
            margins: Page margins dict
            logo_path: Path to logo in storage
            signature_fields: Signature field definitions
            is_system: Whether this is a system template
            created_by: Creator's UUID

        Returns:
            Created DocumentTemplate instance
        """
        # Check for duplicate code
        if code:
            existing = DocumentTemplate.objects.filter(
                organization_id=organization_id,
                code=code,
                is_active=True,
            ).exists()
            if existing:
                raise TemplateError(f"Template with code '{code}' already exists")

        template = DocumentTemplate.objects.create(
            organization_id=organization_id,
            name=name,
            code=code,
            description=description,
            template_type=template_type,
            output_format=output_format,
            template_content=template_content,
            variables=variables or [],
            sample_data=sample_data or {},
            header_content=header_content,
            footer_content=footer_content,
            styles=styles,
            page_size=page_size,
            page_orientation=page_orientation,
            margins=margins or {},
            logo_path=logo_path,
            signature_fields=signature_fields or [],
            is_system=is_system,
            is_active=True,
            created_by=created_by,
        )

        logger.info(f"Created template: {template.name} ({template.id})")

        return template

    # =========================================================================
    # RETRIEVE
    # =========================================================================

    def get_template(
        self,
        template_id: uuid.UUID,
    ) -> DocumentTemplate:
        """
        Get a template by ID.

        Args:
            template_id: Template UUID

        Returns:
            DocumentTemplate instance
        """
        try:
            return DocumentTemplate.objects.get(id=template_id)
        except DocumentTemplate.DoesNotExist:
            raise TemplateError(f"Template not found: {template_id}")

    def get_template_by_code(
        self,
        code: str,
        organization_id: uuid.UUID = None,
    ) -> DocumentTemplate:
        """
        Get a template by code.

        Args:
            code: Template code
            organization_id: Organization UUID (also checks system templates)

        Returns:
            DocumentTemplate instance
        """
        # Try organization-specific first
        if organization_id:
            template = DocumentTemplate.objects.filter(
                code=code,
                organization_id=organization_id,
                is_active=True,
            ).first()
            if template:
                return template

        # Fall back to system template
        template = DocumentTemplate.objects.filter(
            code=code,
            is_system=True,
            is_active=True,
        ).first()

        if not template:
            raise TemplateError(f"Template not found: {code}")

        return template

    def get_templates(
        self,
        organization_id: uuid.UUID,
        template_type: str = None,
        include_system: bool = True,
        active_only: bool = True,
    ) -> List[DocumentTemplate]:
        """
        Get templates for an organization.

        Args:
            organization_id: Organization UUID
            template_type: Filter by type
            include_system: Include system-wide templates
            active_only: Only active templates

        Returns:
            List of DocumentTemplate instances
        """
        from django.db.models import Q

        queryset = DocumentTemplate.objects.all()

        if include_system:
            queryset = queryset.filter(
                Q(organization_id=organization_id) | Q(is_system=True)
            )
        else:
            queryset = queryset.filter(organization_id=organization_id)

        if template_type:
            queryset = queryset.filter(template_type=template_type)

        if active_only:
            queryset = queryset.filter(is_active=True)

        return list(queryset.order_by('template_type', 'name'))

    # =========================================================================
    # UPDATE
    # =========================================================================

    @transaction.atomic
    def update_template(
        self,
        template_id: uuid.UUID,
        updated_by: uuid.UUID,
        **updates
    ) -> DocumentTemplate:
        """
        Update a template.

        Args:
            template_id: Template UUID
            updated_by: User updating
            **updates: Fields to update

        Returns:
            Updated DocumentTemplate instance
        """
        template = self.get_template(template_id)

        if template.is_system:
            raise TemplateError("System templates cannot be modified")

        allowed_fields = {
            'name', 'description', 'template_content', 'variables',
            'sample_data', 'header_content', 'footer_content', 'styles',
            'page_size', 'page_orientation', 'margins', 'logo_path',
            'watermark_text', 'watermark_image_path', 'signature_fields',
            'is_active', 'is_default',
        }

        for field, value in updates.items():
            if field in allowed_fields:
                setattr(template, field, value)

        template.updated_by = updated_by
        template.save()

        logger.info(f"Updated template: {template_id}")

        return template

    # =========================================================================
    # DELETE
    # =========================================================================

    def delete_template(
        self,
        template_id: uuid.UUID,
        deleted_by: uuid.UUID,
    ) -> bool:
        """
        Delete (deactivate) a template.

        Args:
            template_id: Template UUID
            deleted_by: User deleting

        Returns:
            True if deleted
        """
        template = self.get_template(template_id)

        if template.is_system:
            raise TemplateError("System templates cannot be deleted")

        template.is_active = False
        template.updated_by = deleted_by
        template.save(update_fields=['is_active', 'updated_by', 'updated_at'])

        logger.info(f"Deleted template: {template_id}")

        return True

    # =========================================================================
    # DOCUMENT GENERATION
    # =========================================================================

    def generate_document(
        self,
        template_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        variables: Dict[str, Any],
        output_name: str = None,
        save_document: bool = True,
        folder_id: uuid.UUID = None,
        related_entity_type: str = None,
        related_entity_id: uuid.UUID = None,
    ) -> tuple[bytes, Optional[Document]]:
        """
        Generate a document from a template.

        Args:
            template_id: Template UUID
            organization_id: Organization UUID
            user_id: User generating
            variables: Variable values
            output_name: Output filename (auto-generated if not provided)
            save_document: Whether to save as Document record
            folder_id: Folder to save in
            related_entity_type: Related entity type
            related_entity_id: Related entity UUID

        Returns:
            Tuple of (PDF bytes, Document instance or None)
        """
        template = self.get_template(template_id)

        # Validate variables
        is_valid, missing = template.validate_variables(variables)
        if not is_valid:
            raise TemplateError(f"Missing required variables: {', '.join(missing)}")

        # Generate PDF
        try:
            pdf_content = self.pdf_service.generate_pdf_from_template(
                template_content=template.template_content,
                variables=variables,
                css_content=template.styles,
                header_content=template.header_content,
                footer_content=template.footer_content,
                page_size=template.page_size,
                orientation=template.page_orientation,
                margins=template.default_margins,
            )
        except PDFError as e:
            logger.error(f"PDF generation failed: {e}")
            raise TemplateError(f"Failed to generate document: {e}")

        # Record usage
        template.record_usage()

        document = None
        if save_document:
            # Generate filename
            if not output_name:
                output_name = f"{template.name}_{date.today().isoformat()}.pdf"
            elif not output_name.endswith('.pdf'):
                output_name += '.pdf'

            # Save document
            from .document_service import DocumentService
            doc_service = DocumentService()

            document = doc_service.upload_document(
                organization_id=organization_id,
                owner_id=user_id,
                file_content=pdf_content,
                filename=output_name,
                document_type=template.template_type,
                title=output_name.rsplit('.', 1)[0],
                folder_id=folder_id,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id,
                created_by=user_id,
            )

            logger.info(
                f"Generated document from template {template_id}: {document.id}"
            )

        return pdf_content, document

    def generate_preview(
        self,
        template_id: uuid.UUID,
        variables: Dict[str, Any] = None,
    ) -> bytes:
        """
        Generate a preview of template with sample data.

        Args:
            template_id: Template UUID
            variables: Optional custom variables (uses sample_data if not provided)

        Returns:
            PDF bytes
        """
        template = self.get_template(template_id)

        # Use provided variables or sample data
        data = variables or template.sample_data

        try:
            return self.pdf_service.generate_pdf_from_template(
                template_content=template.template_content,
                variables=data,
                css_content=template.styles,
                header_content=template.header_content,
                footer_content=template.footer_content,
                page_size=template.page_size,
                orientation=template.page_orientation,
                margins=template.default_margins,
            )
        except PDFError as e:
            raise TemplateError(f"Failed to generate preview: {e}")

    # =========================================================================
    # VERSIONING
    # =========================================================================

    def create_new_version(
        self,
        template_id: uuid.UUID,
        updated_by: uuid.UUID,
        **updates
    ) -> DocumentTemplate:
        """
        Create a new version of a template.

        Args:
            template_id: Original template UUID
            updated_by: User creating version
            **updates: Fields to update in new version

        Returns:
            New DocumentTemplate instance
        """
        template = self.get_template(template_id)

        if template.is_system:
            raise TemplateError("Cannot version system templates")

        # Apply updates to new version
        for field, value in updates.items():
            if hasattr(template, field):
                setattr(template, field, value)

        new_version = template.create_new_version(updated_by)

        logger.info(
            f"Created template version {new_version.version} "
            f"from {template_id}"
        )

        return new_version

    def duplicate_template(
        self,
        template_id: uuid.UUID,
        new_name: str,
        organization_id: uuid.UUID = None,
        created_by: uuid.UUID = None,
    ) -> DocumentTemplate:
        """
        Duplicate a template.

        Args:
            template_id: Source template UUID
            new_name: Name for new template
            organization_id: Organization for new template (None to keep same)
            created_by: Creator's UUID

        Returns:
            New DocumentTemplate instance
        """
        template = self.get_template(template_id)

        new_template = template.duplicate(new_name, created_by)

        if organization_id:
            new_template.organization_id = organization_id
            new_template.save(update_fields=['organization_id'])

        logger.info(f"Duplicated template {template_id} as {new_template.id}")

        return new_template

    # =========================================================================
    # SYSTEM TEMPLATES
    # =========================================================================

    def create_default_templates(self) -> List[DocumentTemplate]:
        """
        Create default system templates.

        Returns:
            List of created templates
        """
        templates = []

        # Flight Certificate Template
        flight_cert = self._create_flight_certificate_template()
        templates.append(flight_cert)

        # Endorsement Template
        endorsement = self._create_endorsement_template()
        templates.append(endorsement)

        # Training Progress Report
        progress = self._create_progress_report_template()
        templates.append(progress)

        logger.info(f"Created {len(templates)} default templates")

        return templates

    def _create_flight_certificate_template(self) -> DocumentTemplate:
        """Create flight training certificate template."""
        content = """
        <div style="text-align: center; padding: 40px 20px;">
            <h2 style="color: #1a5276; margin-bottom: 40px;">
                {{ organization_name }}
            </h2>

            <h1 style="font-size: 32pt; color: #333; border-top: 2px solid #1a5276;
                       border-bottom: 2px solid #1a5276; padding: 20px 0; margin: 20px 0;">
                Certificate of Completion
            </h1>

            <p style="font-size: 14pt; color: #666; margin: 30px 0;">
                This is to certify that
            </p>

            <h2 style="font-size: 24pt; font-family: Georgia, serif; margin: 20px 0;">
                {{ student_name }}
            </h2>

            <p style="font-size: 14pt; color: #444; max-width: 600px; margin: 30px auto;">
                has successfully completed the <strong>{{ course_name }}</strong>
                training program with a total of <strong>{{ total_hours }} flight hours</strong>.
            </p>

            {% if rating %}
            <p style="font-size: 14pt; color: #444;">
                Rating: <strong>{{ rating }}</strong>
            </p>
            {% endif %}

            <div style="display: flex; justify-content: space-around; margin-top: 60px;">
                <div style="text-align: center;">
                    <p style="border-top: 1px solid #333; width: 200px; padding-top: 10px;">
                        {{ completion_date|date }}
                    </p>
                    <p style="font-size: 10pt; color: #666;">Date of Completion</p>
                </div>

                <div style="text-align: center;">
                    <p style="border-top: 1px solid #333; width: 200px; padding-top: 10px;">
                        {{ instructor_name }}
                    </p>
                    <p style="font-size: 10pt; color: #666;">Chief Flight Instructor</p>
                </div>
            </div>

            <p style="font-size: 9pt; color: #999; margin-top: 40px;">
                Certificate No: {{ certificate_number }}
            </p>
        </div>
        """

        return DocumentTemplate.objects.create(
            organization_id=None,
            name='Flight Training Certificate',
            code='FLIGHT_CERT',
            description='Certificate for flight training completion',
            template_type=TemplateType.CERTIFICATE,
            output_format=OutputFormat.PDF,
            template_content=content,
            variables=[
                {'name': 'organization_name', 'type': 'string', 'required': True},
                {'name': 'student_name', 'type': 'string', 'required': True},
                {'name': 'course_name', 'type': 'string', 'required': True},
                {'name': 'total_hours', 'type': 'number', 'required': True},
                {'name': 'rating', 'type': 'string', 'required': False},
                {'name': 'completion_date', 'type': 'date', 'required': True},
                {'name': 'instructor_name', 'type': 'string', 'required': True},
                {'name': 'certificate_number', 'type': 'string', 'required': True},
            ],
            sample_data={
                'organization_name': 'Aviation Training Academy',
                'student_name': 'John Smith',
                'course_name': 'Private Pilot License (PPL)',
                'total_hours': 45.5,
                'rating': 'Excellent',
                'completion_date': date.today(),
                'instructor_name': 'Michael Johnson',
                'certificate_number': 'CERT-2024-00001',
            },
            page_orientation='landscape',
            is_system=True,
            is_active=True,
        )

    def _create_endorsement_template(self) -> DocumentTemplate:
        """Create instructor endorsement template."""
        content = """
        <div style="padding: 30px;">
            <h2 style="text-align: center; color: #333;">FLIGHT INSTRUCTOR ENDORSEMENT</h2>

            <div style="margin: 30px 0;">
                <p><strong>Student:</strong> {{ student_name }}</p>
                <p><strong>Student Certificate Number:</strong> {{ student_cert_number }}</p>
            </div>

            <div style="border: 1px solid #ddd; padding: 20px; margin: 20px 0;">
                <h3>{{ endorsement_type }}</h3>
                <p>{{ endorsement_text }}</p>
            </div>

            <div style="margin-top: 40px;">
                <p>I certify that I have given the above-named student the required training
                and find them competent to perform the activities described above.</p>
            </div>

            <div style="margin-top: 50px; display: flex; justify-content: space-between;">
                <div>
                    <p style="border-top: 1px solid #333; width: 250px; padding-top: 5px;">
                        Instructor Signature
                    </p>
                </div>
                <div style="text-align: right;">
                    <p><strong>{{ instructor_name }}</strong></p>
                    <p>CFI No: {{ instructor_cert_number }}</p>
                    <p>Exp: {{ instructor_cert_expiry|date }}</p>
                </div>
            </div>

            <p style="text-align: right; margin-top: 30px;">
                Date: {{ endorsement_date|date }}
            </p>
        </div>
        """

        return DocumentTemplate.objects.create(
            organization_id=None,
            name='Flight Instructor Endorsement',
            code='ENDORSEMENT',
            description='Standard instructor endorsement form',
            template_type=TemplateType.ENDORSEMENT,
            output_format=OutputFormat.PDF,
            template_content=content,
            variables=[
                {'name': 'student_name', 'type': 'string', 'required': True},
                {'name': 'student_cert_number', 'type': 'string', 'required': True},
                {'name': 'endorsement_type', 'type': 'string', 'required': True},
                {'name': 'endorsement_text', 'type': 'string', 'required': True},
                {'name': 'instructor_name', 'type': 'string', 'required': True},
                {'name': 'instructor_cert_number', 'type': 'string', 'required': True},
                {'name': 'instructor_cert_expiry', 'type': 'date', 'required': True},
                {'name': 'endorsement_date', 'type': 'date', 'required': True},
            ],
            sample_data={
                'student_name': 'Jane Doe',
                'student_cert_number': '123456789',
                'endorsement_type': 'Solo Flight Endorsement',
                'endorsement_text': 'I certify that I have given this student the required '
                                   'training in the make and model aircraft and find them '
                                   'competent to make solo flights.',
                'instructor_name': 'Robert Williams',
                'instructor_cert_number': 'CFI-987654',
                'instructor_cert_expiry': date.today(),
                'endorsement_date': date.today(),
            },
            is_system=True,
            is_active=True,
        )

    def _create_progress_report_template(self) -> DocumentTemplate:
        """Create training progress report template."""
        content = """
        <div style="padding: 20px;">
            <h1 style="text-align: center; color: #1a5276;">Training Progress Report</h1>

            <table style="width: 100%; margin: 20px 0;">
                <tr>
                    <td><strong>Student:</strong> {{ student_name }}</td>
                    <td><strong>Report Date:</strong> {{ report_date|date }}</td>
                </tr>
                <tr>
                    <td><strong>Program:</strong> {{ program_name }}</td>
                    <td><strong>Start Date:</strong> {{ start_date|date }}</td>
                </tr>
            </table>

            <h2>Flight Hours Summary</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #f5f5f5;">
                        <th style="padding: 10px; border: 1px solid #ddd;">Category</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">Completed</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">Required</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">Progress</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in hours_breakdown %}
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;">{{ item.category }}</td>
                        <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">
                            {{ item.completed|hours }}
                        </td>
                        <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">
                            {{ item.required|hours }}
                        </td>
                        <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">
                            {{ item.percentage }}%
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>

            <h2>Instructor Notes</h2>
            <div style="border: 1px solid #ddd; padding: 15px; min-height: 100px;">
                {{ instructor_notes }}
            </div>

            <div style="margin-top: 40px;">
                <p><strong>Overall Progress:</strong> {{ overall_progress }}%</p>
                <p><strong>Instructor:</strong> {{ instructor_name }}</p>
            </div>
        </div>
        """

        return DocumentTemplate.objects.create(
            organization_id=None,
            name='Training Progress Report',
            code='PROGRESS_REPORT',
            description='Student training progress report',
            template_type=TemplateType.PROGRESS_REPORT,
            output_format=OutputFormat.PDF,
            template_content=content,
            variables=[
                {'name': 'student_name', 'type': 'string', 'required': True},
                {'name': 'program_name', 'type': 'string', 'required': True},
                {'name': 'report_date', 'type': 'date', 'required': True},
                {'name': 'start_date', 'type': 'date', 'required': True},
                {'name': 'hours_breakdown', 'type': 'array', 'required': True},
                {'name': 'instructor_notes', 'type': 'string', 'required': False},
                {'name': 'overall_progress', 'type': 'number', 'required': True},
                {'name': 'instructor_name', 'type': 'string', 'required': True},
            ],
            sample_data={
                'student_name': 'Alex Johnson',
                'program_name': 'Private Pilot License',
                'report_date': date.today(),
                'start_date': date.today(),
                'hours_breakdown': [
                    {'category': 'Dual Instruction', 'completed': 20, 'required': 25, 'percentage': 80},
                    {'category': 'Solo', 'completed': 8, 'required': 10, 'percentage': 80},
                    {'category': 'Cross Country', 'completed': 3, 'required': 5, 'percentage': 60},
                    {'category': 'Night', 'completed': 2, 'required': 3, 'percentage': 67},
                ],
                'instructor_notes': 'Student is making excellent progress.',
                'overall_progress': 75,
                'instructor_name': 'Sarah Miller',
            },
            is_system=True,
            is_active=True,
        )
