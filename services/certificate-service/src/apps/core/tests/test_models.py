# services/certificate-service/src/apps/core/tests/test_models.py
"""
Certificate Service Model Tests

Tests for certificate service data models.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from django.utils import timezone

from apps.core.models import (
    Certificate,
    CertificateType,
    CertificateSubtype,
    CertificateStatus,
    IssuingAuthority,
    MedicalCertificate,
    MedicalClass,
    MedicalStatus,
    Rating,
    RatingType,
    RatingStatus,
    Endorsement,
    EndorsementType,
    EndorsementStatus,
    CurrencyRequirement,
    CurrencyType,
    UserCurrencyStatus,
    CurrencyStatus,
    CertificateVerification,
)


@pytest.mark.django_db
class TestCertificateModel:
    """Tests for Certificate model."""

    def test_create_certificate(self):
        """Test creating a certificate."""
        cert = Certificate.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            certificate_type=CertificateType.PILOT_LICENSE,
            certificate_subtype=CertificateSubtype.PPL,
            issuing_authority=IssuingAuthority.FAA,
            issuing_country='US',
            certificate_number='1234567',
            issue_date=date.today() - timedelta(days=365),
            expiry_date=date.today() + timedelta(days=365),
            status=CertificateStatus.ACTIVE,
        )

        assert cert.id is not None
        assert cert.certificate_type == CertificateType.PILOT_LICENSE
        assert cert.status == CertificateStatus.ACTIVE

    def test_certificate_is_valid(self):
        """Test certificate validity check."""
        # Valid certificate
        valid_cert = Certificate.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=30),
            status=CertificateStatus.ACTIVE,
        )
        assert valid_cert.is_valid is True

        # Expired certificate
        expired_cert = Certificate.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today() - timedelta(days=365),
            expiry_date=date.today() - timedelta(days=1),
            status=CertificateStatus.ACTIVE,
        )
        assert expired_cert.is_valid is False
        assert expired_cert.is_expired is True

    def test_certificate_expiring_soon(self):
        """Test certificate expiring soon check."""
        cert = Certificate.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=15),
            status=CertificateStatus.ACTIVE,
        )
        assert cert.is_expiring_soon is True
        assert cert.days_until_expiry == 15

    def test_certificate_without_expiry(self):
        """Test certificate without expiry date."""
        cert = Certificate.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            status=CertificateStatus.ACTIVE,
        )
        assert cert.is_valid is True
        assert cert.is_expired is False
        assert cert.days_until_expiry is None

    def test_certificate_expiry_status(self):
        """Test certificate expiry status display."""
        # Valid
        valid_cert = Certificate.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=100),
            status=CertificateStatus.ACTIVE,
        )
        assert valid_cert.expiry_status == 'valid'

        # Warning
        warning_cert = Certificate.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=20),
            status=CertificateStatus.ACTIVE,
        )
        assert warning_cert.expiry_status == 'warning'

        # Critical
        critical_cert = Certificate.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=5),
            status=CertificateStatus.ACTIVE,
        )
        assert critical_cert.expiry_status == 'critical'


@pytest.mark.django_db
class TestMedicalCertificateModel:
    """Tests for MedicalCertificate model."""

    def test_create_medical(self):
        """Test creating a medical certificate."""
        medical = MedicalCertificate.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            medical_class=MedicalClass.CLASS_2,
            issuing_authority='FAA',
            issuing_country='US',
            examination_date=date.today() - timedelta(days=30),
            issue_date=date.today() - timedelta(days=28),
            expiry_date=date.today() + timedelta(days=337),
            status=MedicalStatus.ACTIVE,
        )

        assert medical.id is not None
        assert medical.medical_class == MedicalClass.CLASS_2
        assert medical.is_valid is True

    def test_medical_validity(self):
        """Test medical certificate validity."""
        # Valid medical
        valid_medical = MedicalCertificate.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            medical_class=MedicalClass.CLASS_2,
            issuing_authority='FAA',
            examination_date=date.today(),
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            status=MedicalStatus.ACTIVE,
        )
        assert valid_medical.is_valid is True

        # Expired medical
        expired_medical = MedicalCertificate.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            medical_class=MedicalClass.CLASS_2,
            issuing_authority='FAA',
            examination_date=date.today() - timedelta(days=400),
            issue_date=date.today() - timedelta(days=400),
            expiry_date=date.today() - timedelta(days=35),
            status=MedicalStatus.ACTIVE,
        )
        assert expired_medical.is_valid is False
        assert expired_medical.is_expired is True

    def test_medical_applicable_privileges(self):
        """Test medical applicable privileges."""
        # Class 1 medical
        class1_medical = MedicalCertificate.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            medical_class=MedicalClass.CLASS_1,
            issuing_authority='FAA',
            examination_date=date.today(),
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            status=MedicalStatus.ACTIVE,
        )
        privileges = class1_medical.get_applicable_privileges()
        assert 'ATPL' in privileges
        assert 'CPL' in privileges
        assert 'PPL' in privileges

        # Class 2 medical
        class2_medical = MedicalCertificate.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            medical_class=MedicalClass.CLASS_2,
            issuing_authority='FAA',
            examination_date=date.today(),
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            status=MedicalStatus.ACTIVE,
        )
        privileges = class2_medical.get_applicable_privileges()
        assert 'ATPL' not in privileges
        assert 'CPL' in privileges
        assert 'PPL' in privileges


@pytest.mark.django_db
class TestRatingModel:
    """Tests for Rating model."""

    def test_create_rating(self):
        """Test creating a rating."""
        rating = Rating.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            rating_type=RatingType.AIRCRAFT_TYPE,
            rating_code='C172',
            rating_name='Cessna 172 Type Rating',
            aircraft_icao='C172',
            issue_date=date.today() - timedelta(days=100),
            expiry_date=date.today() + timedelta(days=265),
            status=RatingStatus.ACTIVE,
        )

        assert rating.id is not None
        assert rating.rating_type == RatingType.AIRCRAFT_TYPE
        assert rating.is_valid is True

    def test_rating_proficiency_due(self):
        """Test rating proficiency check due."""
        # Proficiency due soon
        rating = Rating.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            rating_type=RatingType.INSTRUMENT,
            rating_code='IR',
            rating_name='Instrument Rating',
            issue_date=date.today() - timedelta(days=100),
            next_proficiency_date=date.today() + timedelta(days=20),
            status=RatingStatus.ACTIVE,
        )
        assert rating.is_proficiency_due is True
        assert rating.days_until_proficiency == 20

    def test_rating_validity(self):
        """Test rating validity check."""
        # Valid rating
        valid_rating = Rating.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            rating_type=RatingType.NIGHT,
            rating_code='NR',
            issue_date=date.today(),
            status=RatingStatus.ACTIVE,
        )
        assert valid_rating.is_valid is True

        # Suspended rating
        suspended_rating = Rating.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            rating_type=RatingType.NIGHT,
            rating_code='NR',
            issue_date=date.today(),
            status=RatingStatus.SUSPENDED,
        )
        assert suspended_rating.is_valid is False


@pytest.mark.django_db
class TestEndorsementModel:
    """Tests for Endorsement model."""

    def test_create_endorsement(self):
        """Test creating an endorsement."""
        endorsement = Endorsement.objects.create(
            organization_id=uuid4(),
            student_id=uuid4(),
            student_name='Test Student',
            instructor_id=uuid4(),
            instructor_name='Test Instructor',
            endorsement_type=EndorsementType.SOLO,
            endorsement_code='61.87(n)',
            description='Solo flight endorsement',
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=90),
            validity_days=90,
            status=EndorsementStatus.PENDING,
        )

        assert endorsement.id is not None
        assert endorsement.endorsement_type == EndorsementType.SOLO
        assert endorsement.is_signed is False

    def test_endorsement_validity(self):
        """Test endorsement validity."""
        # Valid and signed endorsement
        valid_endorsement = Endorsement.objects.create(
            organization_id=uuid4(),
            student_id=uuid4(),
            student_name='Test Student',
            instructor_id=uuid4(),
            instructor_name='Test Instructor',
            endorsement_type=EndorsementType.SOLO,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=90),
            instructor_signature={'signature': 'test'},
            signed_at=timezone.now(),
            status=EndorsementStatus.ACTIVE,
        )
        assert valid_endorsement.is_valid is True
        assert valid_endorsement.is_signed is True

        # Unsigned endorsement
        unsigned_endorsement = Endorsement.objects.create(
            organization_id=uuid4(),
            student_id=uuid4(),
            student_name='Test Student',
            instructor_id=uuid4(),
            instructor_name='Test Instructor',
            endorsement_type=EndorsementType.SOLO,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=90),
            status=EndorsementStatus.PENDING,
        )
        assert unsigned_endorsement.is_valid is False
        assert unsigned_endorsement.is_signed is False

    def test_permanent_endorsement(self):
        """Test permanent endorsement."""
        endorsement = Endorsement.objects.create(
            organization_id=uuid4(),
            student_id=uuid4(),
            student_name='Test Student',
            instructor_id=uuid4(),
            instructor_name='Test Instructor',
            endorsement_type=EndorsementType.KNOWLEDGE_TEST,
            issue_date=date.today(),
            is_permanent=True,
            instructor_signature={'signature': 'test'},
            signed_at=timezone.now(),
            status=EndorsementStatus.ACTIVE,
        )
        assert endorsement.is_valid is True
        assert endorsement.is_expired is False
        assert endorsement.days_until_expiry is None


@pytest.mark.django_db
class TestCurrencyModel:
    """Tests for Currency models."""

    def test_create_currency_requirement(self):
        """Test creating a currency requirement."""
        requirement = CurrencyRequirement.objects.create(
            organization_id=uuid4(),
            currency_type=CurrencyType.TAKEOFF_LANDING,
            name='Day VFR Currency',
            required_takeoffs=3,
            required_landings=3,
            lookback_days=90,
        )

        assert requirement.id is not None
        assert requirement.currency_type == CurrencyType.TAKEOFF_LANDING

    def test_user_currency_status(self):
        """Test user currency status."""
        requirement = CurrencyRequirement.objects.create(
            organization_id=uuid4(),
            currency_type=CurrencyType.TAKEOFF_LANDING,
            name='Day VFR Currency',
            required_takeoffs=3,
            required_landings=3,
            lookback_days=90,
        )

        # Current status
        current_status = UserCurrencyStatus.objects.create(
            organization_id=requirement.organization_id,
            user_id=uuid4(),
            requirement=requirement,
            current_takeoffs=5,
            current_landings=5,
            expiry_date=date.today() + timedelta(days=60),
            status=CurrencyStatus.CURRENT,
        )
        assert current_status.is_current is True

        # Expired status
        expired_status = UserCurrencyStatus.objects.create(
            organization_id=requirement.organization_id,
            user_id=uuid4(),
            requirement=requirement,
            current_takeoffs=2,
            current_landings=2,
            expiry_date=date.today() - timedelta(days=1),
            status=CurrencyStatus.EXPIRED,
        )
        assert expired_status.is_current is False

    def test_currency_completion_percentage(self):
        """Test currency completion percentage calculation."""
        requirement = CurrencyRequirement.objects.create(
            organization_id=uuid4(),
            currency_type=CurrencyType.TAKEOFF_LANDING,
            name='Day VFR Currency',
            required_takeoffs=3,
            required_landings=3,
            lookback_days=90,
        )

        status = UserCurrencyStatus.objects.create(
            organization_id=requirement.organization_id,
            user_id=uuid4(),
            requirement=requirement,
            current_takeoffs=2,
            current_landings=3,
            status=CurrencyStatus.NOT_CURRENT,
        )

        # Should be ~83% (5 of 6 requirements met)
        assert status.completion_percentage < 100
        assert status.completion_percentage > 50


@pytest.mark.django_db
class TestCertificateVerificationModel:
    """Tests for CertificateVerification model."""

    def test_create_verification(self):
        """Test creating a certificate verification."""
        cert = Certificate.objects.create(
            organization_id=uuid4(),
            user_id=uuid4(),
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            status=CertificateStatus.ACTIVE,
        )

        verification = CertificateVerification.objects.create(
            organization_id=cert.organization_id,
            certificate=cert,
            verification_method='document_check',
            verified_by=uuid4(),
            verification_status='verified',
            verification_date=date.today(),
        )

        assert verification.id is not None
        assert verification.verification_status == 'verified'
