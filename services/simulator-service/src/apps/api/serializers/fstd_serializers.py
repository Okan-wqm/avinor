# services/simulator-service/src/apps/api/serializers/fstd_serializers.py
"""
FSTD Device Serializers
"""

from rest_framework import serializers
from apps.core.models import FSTDevice


class FSTDeviceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""

    is_qualified = serializers.BooleanField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = FSTDevice
        fields = [
            'id',
            'device_id',
            'name',
            'fstd_type',
            'qualification_level',
            'aircraft_type_simulated',
            'status',
            'is_qualified',
            'is_available',
            'days_until_expiry',
            'hourly_rate',
            'currency',
            'location_name',
        ]


class FSTDeviceSerializer(serializers.ModelSerializer):
    """Full serializer for detail views"""

    is_qualified = serializers.BooleanField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    credit_rules = serializers.SerializerMethodField()

    class Meta:
        model = FSTDevice
        fields = '__all__'
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            'total_hours',
            'total_sessions',
            'hours_since_qualification',
        ]

    def get_credit_rules(self, obj):
        return obj.get_credit_rules()


class FSTDeviceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating FSTD devices"""

    class Meta:
        model = FSTDevice
        fields = [
            'device_id',
            'name',
            'manufacturer',
            'model',
            'serial_number',
            'fstd_type',
            'qualification_level',
            'aircraft_type_simulated',
            'aircraft_variant',
            'engine_type',
            'qualification_certificate_number',
            'qualification_authority',
            'qualification_date',
            'qualification_expiry',
            'location_id',
            'location_name',
            'capabilities',
            'motion_system',
            'visual_system',
            'ir_training_credit_hours',
            'type_rating_credit_hours',
            'zftt_eligible',
            'hourly_rate',
            'currency',
            'minimum_booking_hours',
            'operating_hours_start',
            'operating_hours_end',
            'timezone',
            'notes',
        ]

    def create(self, validated_data):
        # Add organization from request context
        request = self.context.get('request')
        if request and hasattr(request, 'organization_id'):
            validated_data['organization_id'] = request.organization_id
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user.id
        return super().create(validated_data)
