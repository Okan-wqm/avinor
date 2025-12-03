# services/organization-service/src/apps/core/serializers/organization.py
"""
Organization Serializers

Serializers for organization management API endpoints.
"""

from rest_framework import serializers
from apps.core.models import Organization, OrganizationSetting


class OrganizationSerializer(serializers.ModelSerializer):
    """Full organization serializer with all details."""

    subscription_plan_name = serializers.CharField(
        source='subscription_plan.name',
        read_only=True
    )
    subscription_plan_code = serializers.CharField(
        source='subscription_plan.code',
        read_only=True
    )
    is_trial_expired = serializers.BooleanField(read_only=True)
    days_until_trial_end = serializers.IntegerField(read_only=True)
    full_address = serializers.CharField(read_only=True)
    location_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id',
            'name',
            'legal_name',
            'slug',
            'organization_type',
            'email',
            'phone',
            'fax',
            'website',
            'address_line1',
            'address_line2',
            'city',
            'state_province',
            'postal_code',
            'country_code',
            'latitude',
            'longitude',
            'full_address',
            'logo_url',
            'logo_dark_url',
            'favicon_url',
            'primary_color',
            'secondary_color',
            'accent_color',
            'custom_domain',
            'custom_domain_verified',
            'timezone',
            'date_format',
            'time_format',
            'currency_code',
            'language',
            'fiscal_year_start_month',
            'week_start_day',
            'default_booking_duration_minutes',
            'min_booking_notice_hours',
            'max_booking_advance_days',
            'cancellation_notice_hours',
            'late_cancellation_fee_percent',
            'no_show_fee_percent',
            'default_preflight_minutes',
            'default_postflight_minutes',
            'time_tracking_method',
            'auto_charge_flights',
            'require_positive_balance',
            'minimum_balance_warning',
            'payment_terms_days',
            'regulatory_authority',
            'ato_certificate_number',
            'ato_certificate_expiry',
            'ato_approval_type',
            'subscription_plan_name',
            'subscription_plan_code',
            'subscription_status',
            'subscription_started_at',
            'subscription_ends_at',
            'trial_ends_at',
            'is_trial_expired',
            'days_until_trial_end',
            'max_users',
            'max_aircraft',
            'max_students',
            'max_locations',
            'storage_limit_gb',
            'features',
            'status',
            'location_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'slug', 'subscription_status', 'subscription_started_at',
            'subscription_ends_at', 'trial_ends_at', 'max_users', 'max_aircraft',
            'max_students', 'max_locations', 'storage_limit_gb', 'features',
            'created_at', 'updated_at',
        ]

    def get_location_count(self, obj) -> int:
        return obj.locations.filter(is_active=True).count()


class OrganizationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for organization lists."""

    subscription_plan_name = serializers.CharField(
        source='subscription_plan.name',
        read_only=True
    )

    class Meta:
        model = Organization
        fields = [
            'id',
            'name',
            'slug',
            'organization_type',
            'email',
            'city',
            'country_code',
            'logo_url',
            'subscription_plan_name',
            'subscription_status',
            'status',
            'created_at',
        ]


class OrganizationCreateSerializer(serializers.Serializer):
    """Serializer for creating organizations."""

    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    country_code = serializers.CharField(max_length=2)
    organization_type = serializers.ChoiceField(
        choices=Organization.OrganizationType.choices,
        default='flight_school'
    )
    regulatory_authority = serializers.ChoiceField(
        choices=Organization.RegulatoryAuthority.choices,
        default='EASA'
    )
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    address_line1 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    timezone = serializers.CharField(max_length=50, default='UTC')
    currency_code = serializers.CharField(max_length=3, default='USD')
    language = serializers.CharField(max_length=10, default='en')

    def validate_country_code(self, value):
        if len(value) != 2 or not value.isalpha():
            raise serializers.ValidationError("Must be a 2-letter country code")
        return value.upper()


class OrganizationUpdateSerializer(serializers.Serializer):
    """Serializer for updating organizations."""

    name = serializers.CharField(max_length=255, required=False)
    legal_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    fax = serializers.CharField(max_length=50, required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    address_line1 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    address_line2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state_province = serializers.CharField(max_length=100, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    country_code = serializers.CharField(max_length=2, required=False)
    latitude = serializers.DecimalField(
        max_digits=10, decimal_places=8, required=False, allow_null=True
    )
    longitude = serializers.DecimalField(
        max_digits=11, decimal_places=8, required=False, allow_null=True
    )
    timezone = serializers.CharField(max_length=50, required=False)
    date_format = serializers.CharField(max_length=20, required=False)
    time_format = serializers.CharField(max_length=10, required=False)
    currency_code = serializers.CharField(max_length=3, required=False)
    language = serializers.CharField(max_length=10, required=False)
    fiscal_year_start_month = serializers.IntegerField(
        min_value=1, max_value=12, required=False
    )
    week_start_day = serializers.IntegerField(
        min_value=0, max_value=6, required=False
    )
    default_booking_duration_minutes = serializers.IntegerField(
        min_value=15, max_value=480, required=False
    )
    min_booking_notice_hours = serializers.IntegerField(
        min_value=0, required=False
    )
    max_booking_advance_days = serializers.IntegerField(
        min_value=1, max_value=365, required=False
    )
    cancellation_notice_hours = serializers.IntegerField(
        min_value=0, required=False
    )
    default_preflight_minutes = serializers.IntegerField(
        min_value=0, required=False
    )
    default_postflight_minutes = serializers.IntegerField(
        min_value=0, required=False
    )
    time_tracking_method = serializers.ChoiceField(
        choices=Organization.TimeTrackingMethod.choices,
        required=False
    )
    auto_charge_flights = serializers.BooleanField(required=False)
    require_positive_balance = serializers.BooleanField(required=False)
    minimum_balance_warning = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    payment_terms_days = serializers.IntegerField(min_value=0, required=False)
    regulatory_authority = serializers.ChoiceField(
        choices=Organization.RegulatoryAuthority.choices,
        required=False
    )
    ato_certificate_number = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    ato_certificate_expiry = serializers.DateField(required=False, allow_null=True)
    ato_approval_type = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )

    def validate_country_code(self, value):
        if value and (len(value) != 2 or not value.isalpha()):
            raise serializers.ValidationError("Must be a 2-letter country code")
        return value.upper() if value else value


class OrganizationBrandingSerializer(serializers.Serializer):
    """Serializer for organization branding updates."""

    logo_url = serializers.URLField(max_length=500, required=False, allow_blank=True)
    logo_dark_url = serializers.URLField(max_length=500, required=False, allow_blank=True)
    favicon_url = serializers.URLField(max_length=500, required=False, allow_blank=True)
    primary_color = serializers.RegexField(
        regex=r'^#[0-9A-Fa-f]{6}$',
        required=False,
        error_messages={'invalid': 'Must be a valid hex color (e.g., #3B82F6)'}
    )
    secondary_color = serializers.RegexField(
        regex=r'^#[0-9A-Fa-f]{6}$',
        required=False,
        error_messages={'invalid': 'Must be a valid hex color (e.g., #1E40AF)'}
    )
    accent_color = serializers.RegexField(
        regex=r'^#[0-9A-Fa-f]{6}$',
        required=False,
        error_messages={'invalid': 'Must be a valid hex color (e.g., #10B981)'}
    )


class OrganizationSettingSerializer(serializers.ModelSerializer):
    """Serializer for individual organization settings."""

    display_value = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationSetting
        fields = [
            'id',
            'category',
            'key',
            'value',
            'display_value',
            'description',
            'is_secret',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_display_value(self, obj):
        return obj.get_display_value()


class OrganizationSettingsSerializer(serializers.Serializer):
    """Serializer for bulk settings operations."""

    category = serializers.CharField(max_length=50)
    key = serializers.CharField(max_length=100)
    value = serializers.JSONField()
    description = serializers.CharField(required=False, allow_blank=True)
    is_secret = serializers.BooleanField(default=False)


class OrganizationUsageSerializer(serializers.Serializer):
    """Serializer for organization usage statistics."""

    users = serializers.DictField(read_only=True)
    aircraft = serializers.DictField(read_only=True)
    students = serializers.DictField(read_only=True)
    locations = serializers.DictField(read_only=True)
    storage = serializers.DictField(read_only=True)
