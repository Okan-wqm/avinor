# services/maintenance-service/src/apps/api/serializers/parts_inventory.py
"""
Parts Inventory Serializers
"""

from rest_framework import serializers

from apps.core.models import PartsInventory, PartTransaction


class PartsInventorySerializer(serializers.ModelSerializer):
    """Base serializer for PartsInventory."""

    condition_display = serializers.CharField(
        source='get_condition_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = PartsInventory
        fields = [
            'id', 'organization_id', 'location_id',
            'part_number', 'description', 'category', 'ata_chapter',
            'manufacturer', 'manufacturer_code',
            'condition', 'condition_display',
            'quantity_on_hand', 'quantity_reserved', 'quantity_available',
            'minimum_quantity', 'reorder_quantity',
            'unit_of_measure', 'bin_location', 'shelf',
            'unit_cost', 'average_cost', 'total_value',
            'status', 'status_display', 'is_low_stock',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'quantity_available', 'average_cost', 'total_value',
            'created_at', 'updated_at',
        ]

    def get_is_low_stock(self, obj):
        if obj.minimum_quantity:
            return obj.quantity_available <= obj.minimum_quantity
        return False


class PartsInventoryListSerializer(serializers.ModelSerializer):
    """List serializer with essential fields."""

    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = PartsInventory
        fields = [
            'id', 'part_number', 'description', 'category',
            'quantity_on_hand', 'quantity_available', 'minimum_quantity',
            'unit_cost', 'bin_location', 'status', 'is_low_stock',
        ]

    def get_is_low_stock(self, obj):
        if obj.minimum_quantity:
            return obj.quantity_available <= obj.minimum_quantity
        return False


class PartsInventoryDetailSerializer(PartsInventorySerializer):
    """Detail serializer with all fields."""

    class Meta(PartsInventorySerializer.Meta):
        fields = PartsInventorySerializer.Meta.fields + [
            'serial_number', 'batch_lot_number',
            'expiration_date', 'shelf_life_days',
            'alternate_part_numbers', 'superseded_by',
            'preferred_vendor_id', 'preferred_vendor_name',
            'vendor_part_number', 'lead_time_days',
            'last_received_date', 'last_received_quantity',
            'last_issued_date', 'last_count_date',
            'specification_url', 'notes',
        ]


class PartsInventoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating parts."""

    class Meta:
        model = PartsInventory
        fields = [
            'organization_id', 'location_id',
            'part_number', 'description', 'category', 'ata_chapter',
            'manufacturer', 'manufacturer_code',
            'condition', 'serial_number', 'batch_lot_number',
            'quantity_on_hand', 'minimum_quantity', 'reorder_quantity',
            'unit_of_measure', 'bin_location', 'shelf',
            'unit_cost', 'expiration_date', 'shelf_life_days',
            'alternate_part_numbers',
            'preferred_vendor_id', 'preferred_vendor_name',
            'vendor_part_number', 'lead_time_days',
            'specification_url', 'notes',
        ]

    def validate_part_number(self, value):
        """Ensure part number is uppercase."""
        return value.upper() if value else value


class PartsInventoryUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating parts."""

    class Meta:
        model = PartsInventory
        fields = [
            'description', 'category', 'ata_chapter',
            'manufacturer', 'manufacturer_code',
            'minimum_quantity', 'reorder_quantity',
            'unit_of_measure', 'bin_location', 'shelf',
            'unit_cost', 'expiration_date', 'shelf_life_days',
            'preferred_vendor_id', 'preferred_vendor_name',
            'vendor_part_number', 'lead_time_days',
            'specification_url', 'notes', 'status',
        ]


class PartTransactionSerializer(serializers.ModelSerializer):
    """Serializer for PartTransaction."""

    transaction_type_display = serializers.CharField(
        source='get_transaction_type_display',
        read_only=True
    )
    part_number = serializers.CharField(source='part.part_number', read_only=True)

    class Meta:
        model = PartTransaction
        fields = [
            'id', 'part_id', 'part_number', 'organization_id',
            'transaction_type', 'transaction_type_display',
            'quantity', 'unit_cost', 'total_cost', 'quantity_after',
            'work_order_id', 'aircraft_id',
            'reference', 'notes',
            'performed_by', 'performed_at',
        ]
        read_only_fields = ['id', 'total_cost', 'quantity_after', 'performed_at']


class PartReceiveSerializer(serializers.Serializer):
    """Serializer for receiving parts."""

    quantity = serializers.IntegerField(min_value=1)
    unit_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    received_by = serializers.UUIDField(required=False, allow_null=True)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class PartIssueSerializer(serializers.Serializer):
    """Serializer for issuing parts."""

    quantity = serializers.IntegerField(min_value=1)
    work_order_id = serializers.UUIDField(required=False, allow_null=True)
    aircraft_id = serializers.UUIDField(required=False, allow_null=True)
    issued_by = serializers.UUIDField(required=False, allow_null=True)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class PartAdjustSerializer(serializers.Serializer):
    """Serializer for adjusting inventory."""

    new_quantity = serializers.IntegerField(min_value=0)
    reason = serializers.CharField(max_length=500)
    adjusted_by = serializers.UUIDField(required=False, allow_null=True)


class PartReturnSerializer(serializers.Serializer):
    """Serializer for returning parts."""

    quantity = serializers.IntegerField(min_value=1)
    work_order_id = serializers.UUIDField(required=False, allow_null=True)
    returned_by = serializers.UUIDField(required=False, allow_null=True)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class PartReserveSerializer(serializers.Serializer):
    """Serializer for reserving parts."""

    quantity = serializers.IntegerField(min_value=1)
    work_order_id = serializers.UUIDField(required=False, allow_null=True)


class InventoryStatisticsSerializer(serializers.Serializer):
    """Serializer for inventory statistics."""

    total_line_items = serializers.IntegerField()
    total_quantity = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    low_stock_count = serializers.IntegerField()
