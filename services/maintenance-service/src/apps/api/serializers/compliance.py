# services/maintenance-service/src/apps/api/serializers/compliance.py
"""
AD/SB Compliance Serializers
"""

from rest_framework import serializers

from apps.core.models import ADSBTracking


class ADSBTrackingSerializer(serializers.ModelSerializer):
    """Base serializer for ADSBTracking."""

    directive_type_display = serializers.CharField(
        source='get_directive_type_display',
        read_only=True
    )
    compliance_status_display = serializers.CharField(
        source='get_compliance_status_display',
        read_only=True
    )
    issuing_authority_display = serializers.CharField(
        source='get_issuing_authority_display',
        read_only=True
    )

    class Meta:
        model = ADSBTracking
        fields = [
            'id', 'organization_id', 'aircraft_id',
            'directive_type', 'directive_type_display',
            'directive_number', 'revision', 'title', 'description',
            'issuing_authority', 'issuing_authority_display',
            'effective_date', 'applicability',
            'is_applicable', 'not_applicable_reason',
            'compliance_status', 'compliance_status_display',
            'compliance_method', 'compliance_required',
            'initial_compliance_date', 'initial_compliance_hours',
            'is_recurring', 'recurring_interval_days', 'recurring_interval_hours',
            'last_compliance_date', 'last_compliance_hours',
            'next_due_date', 'next_due_hours',
            'remaining_days', 'remaining_hours',
            'is_overdue', 'is_terminating',
            'maintenance_item_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'remaining_days', 'remaining_hours', 'is_overdue',
            'maintenance_item_id', 'created_at', 'updated_at',
        ]


class ADSBTrackingListSerializer(serializers.ModelSerializer):
    """List serializer with essential fields."""

    directive_type_display = serializers.CharField(
        source='get_directive_type_display',
        read_only=True
    )
    compliance_status_display = serializers.CharField(
        source='get_compliance_status_display',
        read_only=True
    )

    class Meta:
        model = ADSBTracking
        fields = [
            'id', 'directive_type', 'directive_type_display',
            'directive_number', 'title',
            'compliance_status', 'compliance_status_display',
            'is_applicable', 'is_recurring',
            'next_due_date', 'next_due_hours',
            'remaining_days', 'remaining_hours', 'is_overdue',
        ]


class ADSBTrackingDetailSerializer(ADSBTrackingSerializer):
    """Detail serializer with all fields."""

    class Meta(ADSBTrackingSerializer.Meta):
        fields = ADSBTrackingSerializer.Meta.fields + [
            'affected_serial_numbers', 'compliance_instructions',
            'terminating_action',
            'last_compliance_cycles', 'next_due_cycles', 'remaining_cycles',
            'last_compliance_notes', 'last_work_order_id',
            'directive_document_url', 'compliance_document_url',
            'notes',
        ]


class ADSBTrackingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating AD/SB tracking records."""

    class Meta:
        model = ADSBTracking
        fields = [
            'organization_id', 'aircraft_id',
            'directive_type', 'directive_number', 'revision',
            'title', 'description',
            'issuing_authority', 'effective_date',
            'applicability', 'affected_serial_numbers',
            'is_applicable', 'not_applicable_reason',
            'compliance_method', 'compliance_instructions', 'compliance_required',
            'initial_compliance_date', 'initial_compliance_hours',
            'is_recurring', 'recurring_interval_days', 'recurring_interval_hours',
            'is_terminating', 'terminating_action',
            'directive_document_url', 'compliance_document_url',
            'notes',
        ]

    def validate_directive_number(self, value):
        """Ensure directive number is uppercase."""
        return value.upper() if value else value

    def validate(self, data):
        """Validate directive data."""
        # If applicable, compliance method is required
        if data.get('is_applicable', True) and data.get('compliance_required', True):
            if not data.get('compliance_method'):
                raise serializers.ValidationError({
                    'compliance_method': 'Compliance method is required for applicable directives.'
                })

        # Recurring requires intervals
        if data.get('is_recurring'):
            if not data.get('recurring_interval_days') and not data.get('recurring_interval_hours'):
                raise serializers.ValidationError(
                    'Recurring directives must have interval_days or interval_hours set.'
                )

        return data


class ADSBTrackingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating AD/SB records."""

    class Meta:
        model = ADSBTracking
        fields = [
            'revision', 'title', 'description',
            'applicability', 'affected_serial_numbers',
            'is_applicable', 'not_applicable_reason',
            'compliance_method', 'compliance_instructions',
            'is_terminating', 'terminating_action',
            'initial_compliance_date', 'initial_compliance_hours',
            'is_recurring', 'recurring_interval_days', 'recurring_interval_hours',
            'directive_document_url', 'compliance_document_url',
            'notes',
        ]


class ADSBTrackingComplianceSerializer(serializers.Serializer):
    """Serializer for recording compliance."""

    compliance_date = serializers.DateField()
    compliance_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    compliance_cycles = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    work_order_id = serializers.UUIDField(required=False, allow_null=True)
    performed_by = serializers.CharField(max_length=255, required=False, allow_blank=True)


class ADSBNotApplicableSerializer(serializers.Serializer):
    """Serializer for marking directive as not applicable."""

    reason = serializers.CharField(max_length=1000)


class AircraftComplianceStatusSerializer(serializers.Serializer):
    """Serializer for aircraft compliance status response."""

    aircraft_id = serializers.UUIDField()
    total_directives = serializers.IntegerField()
    status_summary = serializers.DictField()
    by_type = serializers.DictField()
    non_compliant = serializers.ListField()
    upcoming = serializers.ListField()
    is_compliant = serializers.BooleanField()


class ComplianceStatisticsSerializer(serializers.Serializer):
    """Serializer for compliance statistics."""

    total_directives = serializers.IntegerField()
    compliant = serializers.IntegerField()
    non_compliant = serializers.IntegerField()
    compliance_rate = serializers.FloatField()
    by_status = serializers.DictField()
    by_type = serializers.DictField()
