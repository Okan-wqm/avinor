# services/document-service/src/apps/core/api/serializers/template_serializers.py
"""
Template Serializers
"""

from rest_framework import serializers

from ...models import (
    DocumentTemplate,
    TemplateType,
    OutputFormat,
)


class TemplateSerializer(serializers.ModelSerializer):
    """Base template serializer."""

    template_type_display = serializers.CharField(
        source='get_template_type_display',
        read_only=True
    )
    output_format_display = serializers.CharField(
        source='get_output_format_display',
        read_only=True
    )

    class Meta:
        model = DocumentTemplate
        fields = [
            'id',
            'organization_id',
            'name',
            'description',
            'template_type',
            'template_type_display',
            'output_format',
            'output_format_display',
            'version',
            'is_active',
            'is_system',
            'category',
            'tags',
            'variable_definitions',
            'page_size',
            'page_orientation',
            'usage_count',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'version',
            'is_system',
            'usage_count',
            'created_by',
            'created_at',
            'updated_at',
        ]


class TemplateListSerializer(serializers.ModelSerializer):
    """Lightweight template list serializer."""

    template_type_display = serializers.CharField(
        source='get_template_type_display',
        read_only=True
    )

    class Meta:
        model = DocumentTemplate
        fields = [
            'id',
            'name',
            'description',
            'template_type',
            'template_type_display',
            'output_format',
            'is_active',
            'is_system',
            'category',
            'usage_count',
        ]


class TemplateDetailSerializer(TemplateSerializer):
    """Full template details including content."""

    class Meta(TemplateSerializer.Meta):
        fields = TemplateSerializer.Meta.fields + [
            'content',
            'header_content',
            'footer_content',
            'css_styles',
            'margin_top',
            'margin_bottom',
            'margin_left',
            'margin_right',
            'signature_fields',
            'metadata',
        ]


class TemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating templates."""

    class Meta:
        model = DocumentTemplate
        fields = [
            'name',
            'description',
            'template_type',
            'output_format',
            'content',
            'header_content',
            'footer_content',
            'css_styles',
            'category',
            'tags',
            'variable_definitions',
            'page_size',
            'page_orientation',
            'margin_top',
            'margin_bottom',
            'margin_left',
            'margin_right',
            'signature_fields',
            'metadata',
        ]

    def validate_content(self, value):
        """Validate template content."""
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Template content is required and must be meaningful"
            )

        # Check for basic HTML structure
        if '<html>' not in value.lower() and '<body>' not in value.lower():
            # Allow fragments, but warn
            pass

        return value

    def validate_variable_definitions(self, value):
        """Validate variable definitions schema."""
        if not value:
            return value

        required_keys = {'name', 'type'}
        valid_types = {'string', 'number', 'date', 'boolean', 'list', 'object'}

        for var in value:
            if not isinstance(var, dict):
                raise serializers.ValidationError(
                    "Each variable definition must be an object"
                )

            missing = required_keys - set(var.keys())
            if missing:
                raise serializers.ValidationError(
                    f"Variable definition missing: {missing}"
                )

            if var['type'] not in valid_types:
                raise serializers.ValidationError(
                    f"Invalid variable type: {var['type']}"
                )

        return value

    def validate_name(self, value):
        """Validate template name uniqueness."""
        organization_id = self.context.get('organization_id')

        exists = DocumentTemplate.objects.filter(
            organization_id=organization_id,
            name=value,
            is_active=True,
        ).exists()

        if exists:
            raise serializers.ValidationError(
                f"Template '{value}' already exists"
            )

        return value


class TemplateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating templates."""

    class Meta:
        model = DocumentTemplate
        fields = [
            'name',
            'description',
            'content',
            'header_content',
            'footer_content',
            'css_styles',
            'category',
            'tags',
            'variable_definitions',
            'page_size',
            'page_orientation',
            'margin_top',
            'margin_bottom',
            'margin_left',
            'margin_right',
            'signature_fields',
            'is_active',
            'metadata',
        ]

    def validate(self, data):
        """Validate template update."""
        instance = self.instance

        if instance and instance.is_system:
            # Only allow certain fields to be updated on system templates
            allowed_fields = {'is_active', 'metadata'}
            provided_fields = set(data.keys())

            if provided_fields - allowed_fields:
                raise serializers.ValidationError(
                    "System templates can only have is_active and metadata modified"
                )

        return data


class TemplateGenerateSerializer(serializers.Serializer):
    """Serializer for generating documents from templates."""

    template_id = serializers.UUIDField(required=True)
    variables = serializers.DictField(required=True)
    output_filename = serializers.CharField(
        max_length=255,
        required=False,
        help_text="Output filename (without extension)"
    )
    save_as_document = serializers.BooleanField(
        default=False,
        help_text="Save generated document to storage"
    )
    folder_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Folder to save document in (if save_as_document=True)"
    )
    document_type = serializers.CharField(
        max_length=50,
        required=False,
        help_text="Document type for saved document"
    )

    def validate(self, data):
        """Validate generation request."""
        template_id = data.get('template_id')
        organization_id = self.context.get('organization_id')

        # Check template exists and belongs to org
        try:
            template = DocumentTemplate.objects.get(
                id=template_id,
                is_active=True,
            )

            # System templates are available to all
            if not template.is_system:
                if str(template.organization_id) != str(organization_id):
                    raise serializers.ValidationError({
                        'template_id': "Template not found"
                    })

            # Validate required variables
            variables = data.get('variables', {})
            for var_def in template.variable_definitions:
                if var_def.get('required', False):
                    if var_def['name'] not in variables:
                        raise serializers.ValidationError({
                            'variables': f"Missing required variable: {var_def['name']}"
                        })

            data['_template'] = template

        except DocumentTemplate.DoesNotExist:
            raise serializers.ValidationError({
                'template_id': "Template not found or inactive"
            })

        return data


class TemplatePreviewSerializer(serializers.Serializer):
    """Serializer for template preview."""

    content = serializers.CharField(required=True)
    css_styles = serializers.CharField(required=False, allow_blank=True)
    variables = serializers.DictField(required=False, default=dict)
    output_format = serializers.ChoiceField(
        choices=[(f.value, f.name) for f in OutputFormat],
        default=OutputFormat.PDF.value
    )


class TemplateCloneSerializer(serializers.Serializer):
    """Serializer for cloning templates."""

    name = serializers.CharField(max_length=255, required=True)
    description = serializers.CharField(required=False, allow_blank=True)

    def validate_name(self, value):
        """Validate new template name."""
        organization_id = self.context.get('organization_id')

        exists = DocumentTemplate.objects.filter(
            organization_id=organization_id,
            name=value,
            is_active=True,
        ).exists()

        if exists:
            raise serializers.ValidationError(
                f"Template '{value}' already exists"
            )

        return value
