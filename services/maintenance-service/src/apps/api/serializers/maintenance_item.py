# services/maintenance-service/src/apps/api/serializers/maintenance_item.py
"""
Maintenance Item Serializers
"""

from decimal import Decimal
from rest_framework import serializers

from apps.core.models import MaintenanceItem


class MaintenanceItemSerializer(serializers.ModelSerializer):
    """Base serializer for MaintenanceItem."""

    compliance_status_display = serializers.CharField(
        source='get_compliance_status_display',
        read_only=True
    )
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    item_type_display = serializers.CharField(
        source='get_item_type_display',
        read_only=True
    )

    class Meta:
        model = MaintenanceItem
        fields = [
            'id', 'organization_id', 'aircraft_id',
            'name', 'code', 'description',
            'category', 'category_display',
            'item_type', 'item_type_display',
            'ata_chapter', 'component_type',
            'is_mandatory', 'regulatory_reference',
            'interval_hours', 'interval_cycles', 'interval_days', 'interval_months',
            'warning_hours', 'warning_days', 'critical_hours', 'critical_days',
            'next_due_date', 'next_due_hours', 'next_due_cycles',
            'remaining_hours', 'remaining_days', 'remaining_cycles',
            'compliance_status', 'compliance_status_display',
            'last_done_date', 'last_done_hours', 'last_done_cycles',
            'estimated_labor_hours', 'estimated_cost',
            'status', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'compliance_status', 'remaining_hours', 'remaining_days',
            'remaining_cycles', 'created_at', 'updated_at',
        ]


class MaintenanceItemListSerializer(serializers.ModelSerializer):
    """List serializer with essential fields only."""

    compliance_status_display = serializers.CharField(
        source='get_compliance_status_display',
        read_only=True
    )

    class Meta:
        model = MaintenanceItem
        fields = [
            'id', 'name', 'code', 'category', 'item_type',
            'compliance_status', 'compliance_status_display',
            'is_mandatory', 'next_due_date', 'next_due_hours',
            'remaining_hours', 'remaining_days', 'status',
        ]


class MaintenanceItemDetailSerializer(MaintenanceItemSerializer):
    """Detail serializer with all fields."""

    class Meta(MaintenanceItemSerializer.Meta):
        fields = MaintenanceItemSerializer.Meta.fields + [
            'ad_number', 'sb_number', 'documentation_url',
            'notes', 'last_done_by', 'last_work_order_id',
            'is_template', 'template_id', 'deferred_to_date',
            'deferral_reason', 'deferral_approved_by',
        ]


class MaintenanceItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating maintenance items."""

    class Meta:
        model = MaintenanceItem
        fields = [
            'organization_id', 'aircraft_id',
            'name', 'code', 'description',
            'category', 'item_type', 'ata_chapter', 'component_type',
            'is_mandatory', 'regulatory_reference',
            'interval_hours', 'interval_cycles', 'interval_days', 'interval_months',
            'warning_hours', 'warning_days', 'critical_hours', 'critical_days',
            'next_due_date', 'next_due_hours', 'next_due_cycles',
            'estimated_labor_hours', 'estimated_cost',
            'ad_number', 'sb_number', 'documentation_url', 'notes',
            'is_template',
        ]

    def validate(self, data):
        """Validate at least one interval is set for recurring items."""
        item_type = data.get('item_type', MaintenanceItem.ItemType.RECURRING)

        if item_type == MaintenanceItem.ItemType.RECURRING:
            has_interval = any([
                data.get('interval_hours'),
                data.get('interval_cycles'),
                data.get('interval_days'),
                data.get('interval_months'),
            ])
            if not has_interval:
                raise serializers.ValidationError(
                    "Recurring items must have at least one interval defined."
                )

        return data


class MaintenanceItemUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating maintenance items."""

    class Meta:
        model = MaintenanceItem
        fields = [
            'name', 'code', 'description',
            'category', 'item_type', 'ata_chapter', 'component_type',
            'is_mandatory', 'regulatory_reference',
            'interval_hours', 'interval_cycles', 'interval_days', 'interval_months',
            'warning_hours', 'warning_days', 'critical_hours', 'critical_days',
            'estimated_labor_hours', 'estimated_cost',
            'documentation_url', 'notes', 'status',
        ]


class MaintenanceItemComplianceSerializer(serializers.Serializer):
    """Serializer for recording compliance."""

    performed_date = serializers.DateField()
    aircraft_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    aircraft_cycles = serializers.IntegerField(required=False, allow_null=True)
    performed_by = serializers.CharField(max_length=255, required=False, allow_blank=True)
    performed_by_id = serializers.UUIDField(required=False, allow_null=True)
    work_performed = serializers.CharField(required=False, allow_blank=True)
    work_order_id = serializers.UUIDField(required=False, allow_null=True)
    parts_used = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )
    labor_hours = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class MaintenanceItemDeferSerializer(serializers.Serializer):
    """Serializer for deferring maintenance."""

    deferred_to_date = serializers.DateField(required=False, allow_null=True)
    deferred_to_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    reason = serializers.CharField(max_length=1000)
    approved_by = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, data):
        """Validate at least one deferral target is set."""
        if not data.get('deferred_to_date') and not data.get('deferred_to_hours'):
            raise serializers.ValidationError(
                "Either deferred_to_date or deferred_to_hours must be specified."
            )
        return data


class MaintenanceStatusSerializer(serializers.Serializer):
    """Serializer for aircraft maintenance status response."""

    aircraft_id = serializers.UUIDField()
    current_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, allow_null=True
    )
    overdue = MaintenanceItemListSerializer(many=True)
    overdue_count = serializers.IntegerField()
    due = MaintenanceItemListSerializer(many=True)
    due_count = serializers.IntegerField()
    due_soon = MaintenanceItemListSerializer(many=True)
    due_soon_count = serializers.IntegerField()
    total_items = serializers.IntegerField()
    is_maintenance_required = serializers.BooleanField()
    is_grounding_maintenance = serializers.BooleanField()
