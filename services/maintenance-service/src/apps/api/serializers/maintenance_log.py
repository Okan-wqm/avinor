# services/maintenance-service/src/apps/api/serializers/maintenance_log.py
"""
Maintenance Log Serializers
"""

from rest_framework import serializers

from apps.core.models import MaintenanceLog


class MaintenanceLogSerializer(serializers.ModelSerializer):
    """Base serializer for MaintenanceLog."""

    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    maintenance_type_display = serializers.CharField(
        source='get_maintenance_type_display',
        read_only=True
    )

    class Meta:
        model = MaintenanceLog
        fields = [
            'id', 'organization_id', 'aircraft_id',
            'log_number', 'title', 'work_performed',
            'category', 'category_display',
            'maintenance_type', 'maintenance_type_display',
            'performed_date', 'aircraft_hours', 'aircraft_cycles',
            'performed_by', 'performed_by_id',
            'maintenance_item_id', 'work_order_id',
            'labor_hours', 'labor_cost', 'parts_cost', 'other_cost', 'total_cost',
            'next_due_date', 'next_due_hours', 'next_due_cycles',
            'status', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'log_number', 'total_cost', 'created_at', 'updated_at',
        ]


class MaintenanceLogListSerializer(serializers.ModelSerializer):
    """List serializer with essential fields."""

    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )

    class Meta:
        model = MaintenanceLog
        fields = [
            'id', 'log_number', 'title', 'category', 'category_display',
            'performed_date', 'aircraft_hours', 'performed_by',
            'aircraft_id', 'total_cost', 'status',
        ]


class MaintenanceLogDetailSerializer(MaintenanceLogSerializer):
    """Detail serializer with all fields."""

    class Meta(MaintenanceLogSerializer.Meta):
        fields = MaintenanceLogSerializer.Meta.fields + [
            'parts_used', 'parts_removed',
            'ata_chapter', 'component_serial', 'component_part_number',
            'removed_serial', 'removed_part_number',
            'removal_reason', 'serviceable_tag_number',
            'approved_by', 'approved_by_id', 'approved_at',
            'signature_data', 'notes', 'created_by',
        ]


class MaintenanceLogCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating maintenance logs."""

    class Meta:
        model = MaintenanceLog
        fields = [
            'organization_id', 'aircraft_id',
            'title', 'work_performed',
            'category', 'maintenance_type',
            'performed_date', 'aircraft_hours', 'aircraft_cycles',
            'performed_by', 'performed_by_id',
            'maintenance_item_id', 'work_order_id',
            'parts_used', 'parts_removed',
            'labor_hours', 'labor_cost', 'parts_cost', 'other_cost',
            'next_due_date', 'next_due_hours', 'next_due_cycles',
            'ata_chapter', 'component_serial', 'component_part_number',
            'removed_serial', 'removed_part_number', 'removal_reason',
            'notes', 'created_by',
        ]

    def validate(self, data):
        """Validate required fields."""
        if not data.get('performed_date'):
            raise serializers.ValidationError({
                'performed_date': 'Performed date is required.'
            })
        return data


class MaintenanceLogApproveSerializer(serializers.Serializer):
    """Serializer for approving a maintenance log."""

    approved_by = serializers.CharField(max_length=255)
    approved_by_id = serializers.UUIDField()
    signature_data = serializers.JSONField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class MaintenanceHistorySerializer(serializers.Serializer):
    """Serializer for maintenance history response."""

    id = serializers.UUIDField()
    log_number = serializers.CharField()
    title = serializers.CharField()
    category = serializers.CharField()
    performed_date = serializers.DateField()
    aircraft_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, allow_null=True
    )
    performed_by = serializers.CharField()
    total_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True
    )
