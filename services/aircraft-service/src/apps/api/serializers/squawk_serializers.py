# services/aircraft-service/src/apps/api/serializers/squawk_serializers.py
"""
Squawk Serializers

Serializers for aircraft squawk/discrepancy management.
"""

from rest_framework import serializers

from apps.core.models import AircraftSquawk


class SquawkListSerializer(serializers.ModelSerializer):
    """Serializer for squawk list view."""

    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    days_open = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = AircraftSquawk
        fields = [
            'id', 'squawk_number', 'aircraft', 'title',
            'category', 'category_display',
            'severity', 'severity_display',
            'priority', 'priority_display',
            'status', 'status_display',
            'is_grounding', 'is_mel_item', 'mel_category',
            'is_open', 'days_open', 'is_overdue',
            'reported_by', 'reported_by_name', 'reported_at',
            'resolved_at',
        ]


class SquawkDetailSerializer(serializers.ModelSerializer):
    """Serializer for squawk detail view."""

    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    mel_category_display = serializers.CharField(
        source='get_mel_category_display', read_only=True, allow_null=True
    )
    is_open = serializers.BooleanField(read_only=True)
    days_open = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    mel_expiry_date = serializers.DateField(read_only=True)
    mel_time_limit_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = AircraftSquawk
        fields = [
            'id', 'organization_id', 'aircraft', 'squawk_number',

            # Details
            'title', 'description', 'category', 'category_display',
            'ata_chapter', 'system_component',

            # Severity
            'severity', 'severity_display',
            'priority', 'priority_display',
            'is_grounding', 'affects_dispatch',

            # MEL/CDL
            'is_mel_item', 'is_cdl_item',
            'mel_category', 'mel_category_display',
            'mel_reference', 'mel_expiry_date', 'mel_time_limit_days',
            'operational_restrictions',

            # Status
            'status', 'status_display',
            'is_open', 'days_open', 'is_overdue',
            'due_date',

            # Reporter
            'reported_by', 'reported_by_name', 'reported_at',
            'flight_id', 'flight_phase',

            # Aircraft state
            'aircraft_hours_at', 'aircraft_cycles_at',

            # Work
            'work_started_at', 'work_started_by', 'work_started_by_name',
            'work_order_id', 'work_order_number',

            # Resolution
            'resolution', 'corrective_action',
            'parts_used', 'labor_hours',
            'resolved_by', 'resolved_by_name', 'resolved_at',

            # Closure
            'closed_by', 'closed_by_name', 'closed_at', 'closure_notes',

            # Attachments
            'photos', 'documents',

            # Recurrence
            'is_recurring', 'recurrence_count', 'original_squawk_id',

            # Timestamps
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization_id', 'squawk_number',
            'is_open', 'days_open', 'is_overdue',
            'mel_expiry_date', 'mel_time_limit_days',
            'created_at', 'updated_at',
        ]


class SquawkCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a squawk."""

    class Meta:
        model = AircraftSquawk
        fields = [
            'title', 'description', 'category',
            'ata_chapter', 'system_component',
            'severity', 'priority',
            'is_grounding', 'affects_dispatch',
            'is_mel_item', 'is_cdl_item',
            'mel_category', 'mel_reference', 'operational_restrictions',
            'flight_id', 'flight_phase',
            'aircraft_hours_at', 'aircraft_cycles_at',
            'due_date',
            'photos',
        ]

    def validate_title(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Title must be at least 5 characters"
            )
        return value.strip()

    def validate_description(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Description must be at least 10 characters"
            )
        return value.strip()

    def validate(self, attrs):
        """Validate squawk data."""
        # MEL items must have MEL category
        if attrs.get('is_mel_item') and not attrs.get('mel_category'):
            raise serializers.ValidationError({
                'mel_category': "MEL category is required for MEL items"
            })

        # Severity validation for grounding
        severity = attrs.get('severity')
        is_grounding = attrs.get('is_grounding')

        if severity in ['grounding', 'aog'] and not is_grounding:
            attrs['is_grounding'] = True

        return attrs


class SquawkUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a squawk."""

    class Meta:
        model = AircraftSquawk
        fields = [
            'title', 'description', 'category',
            'ata_chapter', 'system_component',
            'severity', 'priority',
            'is_grounding', 'affects_dispatch',
            'is_mel_item', 'is_cdl_item',
            'mel_category', 'mel_reference', 'operational_restrictions',
            'due_date',
        ]


class SquawkResolveSerializer(serializers.Serializer):
    """Serializer for resolving a squawk."""

    resolution = serializers.CharField(
        required=True,
        min_length=10,
        max_length=5000,
        help_text="Description of how the squawk was resolved"
    )
    corrective_action = serializers.CharField(
        required=False,
        max_length=5000,
        allow_blank=True
    )
    parts_used = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )
    labor_hours = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        required=False
    )
    work_order_number = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )


class SquawkDeferSerializer(serializers.Serializer):
    """Serializer for deferring a squawk."""

    mel_category = serializers.ChoiceField(
        choices=AircraftSquawk.MELCategory.choices,
        required=True,
        help_text="MEL category for deferral"
    )
    mel_reference = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )
    operational_restrictions = serializers.CharField(
        max_length=2000,
        required=False,
        allow_blank=True
    )
    reason = serializers.CharField(
        max_length=1000,
        required=True,
        help_text="Reason for deferring"
    )

    def validate_reason(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Deferral reason must be at least 10 characters"
            )
        return value.strip()


class SquawkStatisticsSerializer(serializers.Serializer):
    """Serializer for squawk statistics response."""

    total = serializers.IntegerField()
    open = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    deferred = serializers.IntegerField()
    resolved = serializers.IntegerField()
    closed = serializers.IntegerField()

    by_severity = serializers.DictField()
    by_category = serializers.DictField()

    grounding_count = serializers.IntegerField()
    mel_count = serializers.IntegerField()
    overdue_count = serializers.IntegerField()

    avg_resolution_days = serializers.FloatField(allow_null=True)
