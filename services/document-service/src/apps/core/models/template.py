# services/document-service/src/apps/core/models/template.py
"""
Document Template Model

Template system for generating standardized documents (certificates, forms, reports).
"""

import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField


class TemplateType(models.TextChoices):
    """Template type classifications."""
    CERTIFICATE = 'certificate', 'Certificate'
    ENDORSEMENT = 'endorsement', 'Endorsement'
    LICENSE = 'license', 'License'
    INVOICE = 'invoice', 'Invoice'
    REPORT = 'report', 'Report'
    LOGBOOK = 'logbook', 'Logbook Entry'
    CONTRACT = 'contract', 'Contract'
    FORM = 'form', 'Form'
    LETTER = 'letter', 'Letter'
    CHECKLIST = 'checklist', 'Checklist'
    RECEIPT = 'receipt', 'Receipt'
    STATEMENT = 'statement', 'Statement'
    PROGRESS_REPORT = 'progress_report', 'Progress Report'
    MEDICAL_FORM = 'medical_form', 'Medical Form'
    FLIGHT_PLAN = 'flight_plan', 'Flight Plan'


class OutputFormat(models.TextChoices):
    """Supported output formats."""
    PDF = 'pdf', 'PDF'
    DOCX = 'docx', 'Microsoft Word'
    HTML = 'html', 'HTML'
    PNG = 'png', 'PNG Image'


class DocumentTemplate(models.Model):
    """
    Template for generating standardized documents.

    Uses Jinja2/Handlebars-style templating with:
    - Variable substitution
    - Conditional sections
    - Loops for repeated content
    - Custom headers/footers
    - CSS styling
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(
        db_index=True,
        null=True,
        blank=True,
        help_text="Null for system-wide templates"
    )

    # =========================================================================
    # IDENTIFICATION
    # =========================================================================
    name = models.CharField(max_length=255)
    code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
        help_text="Unique code for programmatic access"
    )
    description = models.TextField(blank=True, null=True)

    # =========================================================================
    # TYPE & FORMAT
    # =========================================================================
    template_type = models.CharField(
        max_length=50,
        choices=TemplateType.choices,
        db_index=True
    )
    output_format = models.CharField(
        max_length=20,
        choices=OutputFormat.choices,
        default=OutputFormat.PDF
    )

    # =========================================================================
    # TEMPLATE CONTENT
    # =========================================================================
    template_content = models.TextField(
        help_text="HTML/Jinja2 template content"
    )
    template_file_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Path to template file in storage (alternative to inline content)"
    )

    # =========================================================================
    # TEMPLATE VARIABLES
    # =========================================================================
    variables = models.JSONField(
        default=list,
        blank=True,
        help_text="""
        Variable definitions for the template.
        Example: [
            {"name": "student_name", "type": "string", "required": true, "label": "Student Name"},
            {"name": "issue_date", "type": "date", "required": true, "label": "Issue Date"},
            {"name": "flight_hours", "type": "number", "required": false, "default": 0}
        ]
        """
    )

    # Sample data for preview
    sample_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Sample variable values for preview"
    )

    # =========================================================================
    # LAYOUT & STYLING
    # =========================================================================
    header_content = models.TextField(
        blank=True,
        null=True,
        help_text="HTML content for page header"
    )
    footer_content = models.TextField(
        blank=True,
        null=True,
        help_text="HTML content for page footer"
    )
    styles = models.TextField(
        blank=True,
        null=True,
        help_text="CSS styles for the template"
    )

    # Page settings
    page_size = models.CharField(
        max_length=20,
        default='A4',
        choices=[
            ('A4', 'A4'),
            ('A3', 'A3'),
            ('Letter', 'Letter'),
            ('Legal', 'Legal'),
            ('A5', 'A5'),
        ]
    )
    page_orientation = models.CharField(
        max_length=20,
        default='portrait',
        choices=[
            ('portrait', 'Portrait'),
            ('landscape', 'Landscape'),
        ]
    )
    margins = models.JSONField(
        default=dict,
        blank=True,
        help_text="Page margins in mm: {top, right, bottom, left}"
    )

    # =========================================================================
    # BRANDING
    # =========================================================================
    logo_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Path to organization logo"
    )
    watermark_text = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    watermark_image_path = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )

    # =========================================================================
    # SIGNATURE FIELDS
    # =========================================================================
    signature_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="""
        Signature field definitions.
        Example: [
            {"name": "instructor_signature", "label": "Instructor", "required": true, "page": 1, "x": 100, "y": 200},
            {"name": "student_signature", "label": "Student", "required": true, "page": 1, "x": 400, "y": 200}
        ]
        """
    )

    # =========================================================================
    # FLAGS
    # =========================================================================
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(
        default=False,
        help_text="System templates cannot be modified by organizations"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Default template for this type"
    )

    # =========================================================================
    # VERSIONING
    # =========================================================================
    version = models.PositiveIntegerField(default=1)
    previous_version = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='next_versions'
    )

    # =========================================================================
    # USAGE STATS
    # =========================================================================
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of documents generated from this template"
    )
    last_used_at = models.DateTimeField(null=True, blank=True)

    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'document_templates'
        ordering = ['template_type', 'name']
        indexes = [
            models.Index(fields=['organization_id', 'template_type']),
            models.Index(fields=['code']),
            models.Index(fields=['is_active', 'template_type']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'code'],
                name='unique_template_code_per_org',
                condition=models.Q(code__isnull=False)
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.template_type})"

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def is_organization_template(self) -> bool:
        """Check if this is an organization-specific template."""
        return self.organization_id is not None

    @property
    def required_variables(self) -> list:
        """Get list of required variable names."""
        return [
            v['name'] for v in self.variables
            if v.get('required', False)
        ]

    @property
    def default_margins(self) -> dict:
        """Get margins with defaults."""
        defaults = {'top': 20, 'right': 20, 'bottom': 20, 'left': 20}
        if self.margins:
            defaults.update(self.margins)
        return defaults

    # =========================================================================
    # METHODS
    # =========================================================================

    def validate_variables(self, data: dict) -> tuple[bool, list]:
        """
        Validate that all required variables are provided.

        Returns:
            Tuple of (is_valid, list of missing variables)
        """
        missing = []
        for var in self.variables:
            if var.get('required', False):
                if var['name'] not in data or data[var['name']] is None:
                    missing.append(var['name'])

        return len(missing) == 0, missing

    def record_usage(self) -> None:
        """Record template usage."""
        from django.utils import timezone
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])

    def create_new_version(self, updated_by: uuid.UUID = None) -> 'DocumentTemplate':
        """
        Create a new version of this template.

        Returns:
            New template instance
        """
        new_template = DocumentTemplate.objects.create(
            organization_id=self.organization_id,
            name=self.name,
            code=self.code,
            description=self.description,
            template_type=self.template_type,
            output_format=self.output_format,
            template_content=self.template_content,
            template_file_path=self.template_file_path,
            variables=self.variables,
            sample_data=self.sample_data,
            header_content=self.header_content,
            footer_content=self.footer_content,
            styles=self.styles,
            page_size=self.page_size,
            page_orientation=self.page_orientation,
            margins=self.margins,
            logo_path=self.logo_path,
            watermark_text=self.watermark_text,
            watermark_image_path=self.watermark_image_path,
            signature_fields=self.signature_fields,
            is_active=True,
            is_system=self.is_system,
            version=self.version + 1,
            previous_version=self,
            created_by=updated_by,
        )

        # Deactivate current version
        self.is_active = False
        self.save(update_fields=['is_active'])

        return new_template

    def duplicate(self, new_name: str, created_by: uuid.UUID = None) -> 'DocumentTemplate':
        """
        Create a copy of this template with a new name.

        Returns:
            New template instance
        """
        return DocumentTemplate.objects.create(
            organization_id=self.organization_id,
            name=new_name,
            code=None,  # Must be set manually
            description=self.description,
            template_type=self.template_type,
            output_format=self.output_format,
            template_content=self.template_content,
            variables=self.variables,
            sample_data=self.sample_data,
            header_content=self.header_content,
            footer_content=self.footer_content,
            styles=self.styles,
            page_size=self.page_size,
            page_orientation=self.page_orientation,
            margins=self.margins,
            logo_path=self.logo_path,
            watermark_text=self.watermark_text,
            signature_fields=self.signature_fields,
            is_active=True,
            is_system=False,
            version=1,
            created_by=created_by,
        )
