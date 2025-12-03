"""
Organization Service Serializers.
"""
from rest_framework import serializers
from .models import Organization, OrganizationMember, Location, OrganizationSettings


class OrganizationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationSettings
        exclude = ['organization']


class OrganizationSerializer(serializers.ModelSerializer):
    settings = OrganizationSettingsSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'slug']

    def get_member_count(self, obj):
        return obj.members.filter(is_active=True).count()


class OrganizationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'organization_type',
            'city', 'country', 'is_active', 'is_verified'
        ]


class OrganizationMemberSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = OrganizationMember
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'joined_at']


class LocationSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = Location
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class LocationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    class Meta:
        model = Location
        fields = [
            'id', 'name', 'location_type', 'icao_code',
            'city', 'is_active', 'is_primary'
        ]
