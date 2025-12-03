# services/maintenance-service/src/apps/api/serializers/work_order.py
"""
Work Order Serializers
"""

from rest_framework import serializers

from apps.core.models import WorkOrder, WorkOrderTask


class WorkOrderTaskSerializer(serializers.ModelSerializer):
    """Serializer for WorkOrderTask."""

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    class Meta:
        model = WorkOrderTask
        fields = [
            'id', 'work_order_id', 'sequence', 'title', 'description',
            'instructions', 'maintenance_item_id',
            'status', 'status_display',
            'estimated_hours', 'actual_hours',
            'completed_at', 'completed_by', 'completion_notes',
            'signed_off_at', 'signed_off_by',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'work_order_id', 'completed_at', 'completed_by',
            'signed_off_at', 'signed_off_by', 'created_at', 'updated_at',
        ]


class WorkOrderTaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tasks."""

    class Meta:
        model = WorkOrderTask
        fields = [
            'sequence', 'title', 'description', 'instructions',
            'maintenance_item_id', 'estimated_hours',
        ]


class WorkOrderTaskCompleteSerializer(serializers.Serializer):
    """Serializer for completing a task."""

    completed_by = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True)
    hours = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )


class WorkOrderSerializer(serializers.ModelSerializer):
    """Base serializer for WorkOrder."""

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    priority_display = serializers.CharField(
        source='get_priority_display',
        read_only=True
    )
    work_order_type_display = serializers.CharField(
        source='get_work_order_type_display',
        read_only=True
    )
    task_count = serializers.SerializerMethodField()
    completed_task_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrder
        fields = [
            'id', 'organization_id', 'aircraft_id',
            'work_order_number', 'title', 'description',
            'work_order_type', 'work_order_type_display',
            'status', 'status_display',
            'priority', 'priority_display',
            'scheduled_start', 'scheduled_end',
            'actual_start', 'actual_end',
            'location_id', 'hangar',
            'assigned_to', 'assigned_to_name', 'assigned_team',
            'estimated_hours', 'actual_hours',
            'estimated_cost', 'actual_cost',
            'estimated_parts_cost', 'actual_parts_cost',
            'task_count', 'completed_task_count',
            'created_by', 'created_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'work_order_number', 'actual_start', 'actual_end',
            'created_at', 'updated_at',
        ]

    def get_task_count(self, obj):
        return obj.tasks.count()

    def get_completed_task_count(self, obj):
        return obj.tasks.filter(
            status__in=[WorkOrderTask.Status.COMPLETED, WorkOrderTask.Status.SKIPPED]
        ).count()


class WorkOrderListSerializer(serializers.ModelSerializer):
    """List serializer with essential fields."""

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    priority_display = serializers.CharField(
        source='get_priority_display',
        read_only=True
    )

    class Meta:
        model = WorkOrder
        fields = [
            'id', 'work_order_number', 'title',
            'work_order_type', 'status', 'status_display',
            'priority', 'priority_display',
            'aircraft_id', 'scheduled_start', 'scheduled_end',
            'assigned_to_name', 'created_at',
        ]


class WorkOrderDetailSerializer(WorkOrderSerializer):
    """Detail serializer with tasks."""

    tasks = WorkOrderTaskSerializer(many=True, read_only=True)

    class Meta(WorkOrderSerializer.Meta):
        fields = WorkOrderSerializer.Meta.fields + [
            'tasks', 'maintenance_items', 'squawk_ids',
            'approved_by', 'approved_by_name', 'approved_at', 'approval_notes',
            'completed_by', 'completed_by_name', 'completion_notes',
            'findings', 'aircraft_hours_start', 'aircraft_hours_end',
            'customer_approval_ref', 'hold_reason', 'cancellation_reason',
        ]


class WorkOrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating work orders."""

    maintenance_item_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        write_only=True
    )
    squawk_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list
    )

    class Meta:
        model = WorkOrder
        fields = [
            'organization_id', 'aircraft_id',
            'title', 'description',
            'work_order_type', 'priority',
            'scheduled_start', 'scheduled_end',
            'location_id', 'hangar',
            'assigned_to', 'assigned_to_name', 'assigned_team',
            'estimated_hours', 'estimated_cost', 'estimated_parts_cost',
            'created_by', 'created_by_name',
            'maintenance_item_ids', 'squawk_ids',
        ]


class WorkOrderUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating work orders."""

    class Meta:
        model = WorkOrder
        fields = [
            'title', 'description', 'priority',
            'scheduled_start', 'scheduled_end',
            'location_id', 'hangar',
            'assigned_to', 'assigned_to_name', 'assigned_team',
            'estimated_hours', 'estimated_cost', 'estimated_parts_cost',
            'approval_notes', 'customer_approval_ref',
        ]


class WorkOrderPlanSerializer(serializers.Serializer):
    """Serializer for planning a work order."""

    scheduled_start = serializers.DateTimeField()
    scheduled_end = serializers.DateTimeField(required=False, allow_null=True)


class WorkOrderApproveSerializer(serializers.Serializer):
    """Serializer for approving a work order."""

    approved_by = serializers.UUIDField()
    approved_by_name = serializers.CharField(max_length=255, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class WorkOrderStartSerializer(serializers.Serializer):
    """Serializer for starting a work order."""

    started_by = serializers.UUIDField(required=False, allow_null=True)
    aircraft_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )


class WorkOrderCompleteSerializer(serializers.Serializer):
    """Serializer for completing a work order."""

    completed_by = serializers.UUIDField()
    completed_by_name = serializers.CharField(max_length=255, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    findings = serializers.CharField(required=False, allow_blank=True)
    aircraft_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    actual_hours = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True
    )
    actual_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )


class WorkOrderHoldSerializer(serializers.Serializer):
    """Serializer for putting work order on hold."""

    reason = serializers.CharField(max_length=1000)


class WorkOrderCancelSerializer(serializers.Serializer):
    """Serializer for cancelling a work order."""

    reason = serializers.CharField(max_length=1000)
    cancelled_by = serializers.UUIDField(required=False, allow_null=True)
