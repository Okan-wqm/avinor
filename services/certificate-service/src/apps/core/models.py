"""
Certificate Service Models.
"""
from django.db import models
from django.core.validators import MinValueValidator
from shared.common.mixins import UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class License(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Pilot licenses (PPL, CPL, ATPL, etc.).
    """
    class LicenseType(models.TextChoices):
        SPL = 'spl', 'Student Pilot License'
        PPL = 'ppl', 'Private Pilot License'
        CPL = 'cpl', 'Commercial Pilot License'
        ATPL = 'atpl', 'Airline Transport Pilot License'
        RPL = 'rpl', 'Recreational Pilot License'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'
        REVOKED = 'revoked', 'Revoked'
        EXPIRED = 'expired', 'Expired'

    pilot_id = models.UUIDField()
    organization_id = models.UUIDField()

    # License details
    license_number = models.CharField(max_length=50, unique=True)
    license_type = models.CharField(max_length=10, choices=LicenseType.choices)
    issuing_authority = models.CharField(max_length=100)
    issuing_country = models.CharField(max_length=3)  # ISO 3166-1 alpha-3

    # Dates
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    # Document
    document_url = models.URLField(blank=True)

    # Notes
    notes = models.TextField(blank=True)
    restrictions = models.TextField(blank=True)

    class Meta:
        db_table = 'licenses'
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['license_number']),
            models.Index(fields=['pilot_id']),
            models.Index(fields=['status']),
            models.Index(fields=['expiry_date']),
        ]

    def __str__(self):
        return f"{self.license_number} - {self.get_license_type_display()}"


class Rating(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Pilot ratings and endorsements (IR, MEP, etc.).
    """
    class RatingType(models.TextChoices):
        IR = 'ir', 'Instrument Rating'
        MEP = 'mep', 'Multi-Engine Piston'
        MET = 'met', 'Multi-Engine Turbine'
        SEAPLANE = 'seaplane', 'Seaplane'
        TAILWHEEL = 'tailwheel', 'Tailwheel'
        HIGH_PERFORMANCE = 'high_performance', 'High Performance'
        COMPLEX = 'complex', 'Complex Aircraft'
        CFI = 'cfi', 'Certified Flight Instructor'
        CFII = 'cfii', 'Certified Flight Instructor - Instrument'
        MEI = 'mei', 'Multi-Engine Instructor'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        EXPIRED = 'expired', 'Expired'
        SUSPENDED = 'suspended', 'Suspended'

    pilot_id = models.UUIDField()
    license = models.ForeignKey(
        License,
        on_delete=models.CASCADE,
        related_name='ratings',
        null=True,
        blank=True
    )

    # Rating details
    rating_type = models.CharField(max_length=30, choices=RatingType.choices)
    rating_number = models.CharField(max_length=50, blank=True)

    # Dates
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    # Training
    training_completed_date = models.DateField(null=True, blank=True)
    checkride_date = models.DateField(null=True, blank=True)
    examiner_id = models.UUIDField(null=True, blank=True)

    # Documentation
    document_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'ratings'
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['pilot_id']),
            models.Index(fields=['rating_type']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.get_rating_type_display()} - {self.issue_date}"


class MedicalCertificate(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Aviation medical certificates.
    """
    class CertificateClass(models.TextChoices):
        CLASS_1 = '1', 'Class 1 (ATPL)'
        CLASS_2 = '2', 'Class 2 (CPL/PPL)'
        CLASS_3 = '3', 'Class 3 (PPL)'
        BASIC_MED = 'basic', 'BasicMed'
        LAPL = 'lapl', 'LAPL Medical'

    class Status(models.TextChoices):
        VALID = 'valid', 'Valid'
        EXPIRED = 'expired', 'Expired'
        SUSPENDED = 'suspended', 'Suspended'
        DEFERRED = 'deferred', 'Deferred'

    pilot_id = models.UUIDField()

    # Certificate details
    certificate_number = models.CharField(max_length=50)
    certificate_class = models.CharField(max_length=10, choices=CertificateClass.choices)

    # Medical examiner
    examiner_name = models.CharField(max_length=255)
    examiner_number = models.CharField(max_length=50, blank=True)
    examination_date = models.DateField()

    # Validity
    issue_date = models.DateField()
    expiry_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.VALID)

    # Limitations
    has_limitations = models.BooleanField(default=False)
    limitations = models.TextField(blank=True)
    corrective_lenses_required = models.BooleanField(default=False)

    # Documentation
    document_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'medical_certificates'
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['pilot_id']),
            models.Index(fields=['certificate_number']),
            models.Index(fields=['status']),
            models.Index(fields=['expiry_date']),
        ]

    def __str__(self):
        return f"Class {self.certificate_class} - Expires: {self.expiry_date}"


class TypeRating(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Aircraft type ratings for specific aircraft models.
    """
    class Status(models.TextChoices):
        VALID = 'valid', 'Valid'
        EXPIRED = 'expired', 'Expired'
        IN_TRAINING = 'in_training', 'In Training'

    pilot_id = models.UUIDField()
    aircraft_type_id = models.UUIDField()  # Reference to Aircraft Type

    # Type rating details
    type_rating_number = models.CharField(max_length=50, blank=True)
    aircraft_make_model = models.CharField(max_length=255)

    # Dates
    checkride_date = models.DateField()
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)  # Some type ratings don't expire

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.VALID)

    # Training
    training_organization_id = models.UUIDField(null=True, blank=True)
    instructor_id = models.UUIDField(null=True, blank=True)
    examiner_id = models.UUIDField(null=True, blank=True)
    ground_training_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    simulator_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    aircraft_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Documentation
    document_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'type_ratings'
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['pilot_id']),
            models.Index(fields=['aircraft_type_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.aircraft_make_model} - {self.issue_date}"


class Endorsement(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Flight instructor endorsements and special authorizations.
    """
    class EndorsementType(models.TextChoices):
        SOLO = 'solo', 'Solo Flight'
        CROSS_COUNTRY = 'cross_country', 'Solo Cross Country'
        NIGHT = 'night', 'Night Flight'
        CLASS_B = 'class_b', 'Class B Airspace'
        HIGH_ALTITUDE = 'high_altitude', 'High Altitude'
        SPIN = 'spin', 'Spin Training'
        CHECKRIDE = 'checkride', 'Checkride Recommendation'
        CUSTOM = 'custom', 'Custom Endorsement'

    pilot_id = models.UUIDField()
    instructor_id = models.UUIDField()

    # Endorsement details
    endorsement_type = models.CharField(max_length=30, choices=EndorsementType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField()

    # Dates
    endorsement_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)

    # Reference
    regulation_reference = models.CharField(max_length=100, blank=True)  # e.g., FAR 61.87(n)

    # Limitations
    limitations = models.TextField(blank=True)

    # Documentation
    document_url = models.URLField(blank=True)
    logbook_entry = models.TextField(blank=True)

    class Meta:
        db_table = 'endorsements'
        ordering = ['-endorsement_date']
        indexes = [
            models.Index(fields=['pilot_id']),
            models.Index(fields=['instructor_id']),
            models.Index(fields=['endorsement_type']),
        ]

    def __str__(self):
        return f"{self.get_endorsement_type_display()} - {self.endorsement_date}"
