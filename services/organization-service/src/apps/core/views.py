"""
Organization Service Views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from shared.common.permissions import IsAdmin, IsOrganizationAdmin
from .models import Organization, OrganizationMember, Location, OrganizationSettings
from .serializers import (
    OrganizationSerializer,
    OrganizationListSerializer,
    OrganizationMemberSerializer,
    LocationSerializer,
    LocationListSerializer,
    OrganizationSettingsSerializer,
)


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing organizations.
    """
    queryset = Organization.objects.filter(is_deleted=False)
    serializer_class = OrganizationSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization_type', 'country', 'is_active', 'is_verified']
    search_fields = ['name', 'city', 'caa_approval_number']
    ordering_fields = ['name', 'created_at', 'city']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return OrganizationListSerializer
        return OrganizationSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return super().get_permissions()

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get all members of an organization."""
        organization = self.get_object()
        members = organization.members.filter(is_active=True)
        serializer = OrganizationMemberSerializer(members, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def locations(self, request, pk=None):
        """Get all locations of an organization."""
        organization = self.get_object()
        locations = organization.locations.filter(is_active=True)
        serializer = LocationListSerializer(locations, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'put', 'patch'])
    def settings(self, request, pk=None):
        """Get or update organization settings."""
        organization = self.get_object()
        settings, created = OrganizationSettings.objects.get_or_create(
            organization=organization
        )

        if request.method == 'GET':
            serializer = OrganizationSettingsSerializer(settings)
            return Response(serializer.data)

        serializer = OrganizationSettingsSerializer(
            settings,
            data=request.data,
            partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class OrganizationMemberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing organization members.
    """
    queryset = OrganizationMember.objects.all()
    serializer_class = OrganizationMemberSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'role', 'is_active']
    ordering_fields = ['joined_at', 'role']
    ordering = ['-joined_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset

    @action(detail=False, methods=['get'])
    def my_organizations(self, request):
        """Get organizations for the current user."""
        user_id = request.user.id
        memberships = self.queryset.filter(user_id=user_id, is_active=True)
        serializer = self.get_serializer(memberships, many=True)
        return Response(serializer.data)


class LocationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing locations.
    """
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'location_type', 'is_active', 'is_primary']
    search_fields = ['name', 'icao_code', 'iata_code', 'address']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return LocationListSerializer
        return LocationSerializer

    @action(detail=False, methods=['get'])
    def airports(self, request):
        """Get all airport locations."""
        airports = self.queryset.filter(
            location_type=Location.LocationType.AIRPORT,
            is_active=True
        )
        serializer = LocationListSerializer(airports, many=True)
        return Response(serializer.data)
