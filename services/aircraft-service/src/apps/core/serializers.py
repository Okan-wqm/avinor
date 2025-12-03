"""
Aircraft Service Serializers.
"""
from rest_framework import serializers
from .models import AircraftType, Aircraft, AircraftDocument, Squawk, FuelLog


class AircraftTypeSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = AircraftType
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_display_name(self, obj):
        return str(obj)


class AircraftTypeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AircraftType
        fields = ['id', 'manufacturer', 'model', 'category', 'icao_designator', 'is_active']


class AircraftSerializer(serializers.ModelSerializer):
    aircraft_type_details = AircraftTypeSerializer(source='aircraft_type', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    open_squawks_count = serializers.SerializerMethodField()

    class Meta:
        model = Aircraft
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_open_squawks_count(self, obj):
        return obj.squawks.filter(status__in=['open', 'in_progress']).count()


class AircraftListSerializer(serializers.ModelSerializer):
    aircraft_type_name = serializers.CharField(source='aircraft_type.__str__', read_only=True)

    class Meta:
        model = Aircraft
        fields = [
            'id', 'registration', 'name', 'aircraft_type', 'aircraft_type_name',
            'status', 'total_time_hours', 'hourly_rate', 'home_base_id'
        ]


class AircraftDocumentSerializer(serializers.ModelSerializer):
    aircraft_registration = serializers.CharField(source='aircraft.registration', read_only=True)

    class Meta:
        model = AircraftDocument
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class SquawkSerializer(serializers.ModelSerializer):
    aircraft_registration = serializers.CharField(source='aircraft.registration', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Squawk
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class SquawkListSerializer(serializers.ModelSerializer):
    aircraft_registration = serializers.CharField(source='aircraft.registration', read_only=True)

    class Meta:
        model = Squawk
        fields = [
            'id', 'aircraft', 'aircraft_registration', 'title',
            'severity', 'status', 'discovered_at', 'created_at'
        ]


class FuelLogSerializer(serializers.ModelSerializer):
    aircraft_registration = serializers.CharField(source='aircraft.registration', read_only=True)

    class Meta:
        model = FuelLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
