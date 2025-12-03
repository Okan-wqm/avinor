# services/certificate-service/src/apps/core/tests/test_services.py
"""
Certificate Service Service Layer Tests

Tests for certificate service business logic.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from django.utils import timezone

from apps.core.models import (
    Certificate,
    CertificateType,
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
)
from apps.core.services import (
    CertificateService,
    MedicalService,
    RatingService,
    EndorsementService,
    CurrencyService,
    ValidityService,
)


@pytest.mark.django_db
class TestCertificateService:
    """Tests for CertificateService."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = CertificateService()
        self.org_id = uuid4()
        self.user_id = uuid4()

    def test_create_certificate(self):
        """Test creating a certificate."""
        cert = self.service.create_certificate(
            organization_id=self.org_id,
            user_id=self.user_id,
            certificate_type=CertificateType.PILOT_LICENSE,
            certificate_subtype='ppl',
            issuing_authority=IssuingAuthority.FAA,
            issuing_country='US',
            certificate_number='1234567',
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
        )

        assert cert is not None
        assert cert.user_id == self.user_id
        assert cert.certificate_type == CertificateType.PILOT_LICENSE
        assert cert.status == CertificateStatus.ACTIVE

    def test_get_user_certificates(self):
        """Test getting user certificates."""
        # Create certificates
        for _ in range(3):
            Certificate.objects.create(
                organization_id=self.org_id,
                user_id=self.user_id,
                certificate_type=CertificateType.PILOT_LICENSE,
                issuing_authority=IssuingAuthority.FAA,
                issue_date=date.today(),
                status=CertificateStatus.ACTIVE,
            )

        certs = self.service.get_user_certificates(self.user_id)
        assert len(certs) == 3

    def test_verify_certificate(self):
        """Test verifying a certificate."""
        cert = Certificate.objects.create(
            organization_id=self.org_id,
            user_id=self.user_id,
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            status=CertificateStatus.ACTIVE,
        )

        verified_cert = self.service.verify_certificate(
            certificate_id=cert.id,
            verified_by=uuid4(),
            verification_method='document_check',
        )

        assert verified_cert.verified is True
        assert verified_cert.verified_at is not None

    def test_suspend_certificate(self):
        """Test suspending a certificate."""
        cert = Certificate.objects.create(
            organization_id=self.org_id,
            user_id=self.user_id,
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            status=CertificateStatus.ACTIVE,
        )

        suspended_cert = self.service.suspend_certificate(
            certificate_id=cert.id,
            reason='Test suspension',
            suspended_by=uuid4(),
        )

        assert suspended_cert.status == CertificateStatus.SUSPENDED

    def test_renew_certificate(self):
        """Test renewing a certificate."""
        cert = Certificate.objects.create(
            organization_id=self.org_id,
            user_id=self.user_id,
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today() - timedelta(days=365),
            expiry_date=date.today() + timedelta(days=30),
            status=CertificateStatus.ACTIVE,
        )

        new_expiry = date.today() + timedelta(days=365)
        renewed_cert = self.service.renew_certificate(
            certificate_id=cert.id,
            new_expiry_date=new_expiry,
            renewed_by=uuid4(),
        )

        assert renewed_cert.expiry_date == new_expiry

    def test_get_expiring_certificates(self):
        """Test getting expiring certificates."""
        # Create expiring certificate
        Certificate.objects.create(
            organization_id=self.org_id,
            user_id=self.user_id,
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=20),
            status=CertificateStatus.ACTIVE,
        )

        expiring = self.service.get_expiring_certificates(
            organization_id=self.org_id,
            days_ahead=30,
        )

        assert len(expiring) >= 1


@pytest.mark.django_db
class TestMedicalService:
    """Tests for MedicalService."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = MedicalService()
        self.org_id = uuid4()
        self.user_id = uuid4()

    def test_create_medical(self):
        """Test creating a medical certificate."""
        medical = self.service.create_medical(
            organization_id=self.org_id,
            user_id=self.user_id,
            medical_class=MedicalClass.CLASS_2,
            issuing_authority='FAA',
            issuing_country='US',
            examination_date=date.today(),
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
        )

        assert medical is not None
        assert medical.medical_class == MedicalClass.CLASS_2
        assert medical.status == MedicalStatus.ACTIVE

    def test_get_current_medical(self):
        """Test getting current valid medical."""
        # Create medical
        MedicalCertificate.objects.create(
            organization_id=self.org_id,
            user_id=self.user_id,
            medical_class=MedicalClass.CLASS_2,
            issuing_authority='FAA',
            examination_date=date.today(),
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            status=MedicalStatus.ACTIVE,
        )

        medical = self.service.get_current_medical(self.user_id)
        assert medical is not None
        assert medical.is_valid is True

    def test_check_medical_validity(self):
        """Test checking medical validity."""
        MedicalCertificate.objects.create(
            organization_id=self.org_id,
            user_id=self.user_id,
            medical_class=MedicalClass.CLASS_2,
            issuing_authority='FAA',
            examination_date=date.today(),
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            status=MedicalStatus.ACTIVE,
        )

        result = self.service.check_medical_validity(self.user_id)
        assert result['is_valid'] is True


@pytest.mark.django_db
class TestRatingService:
    """Tests for RatingService."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = RatingService()
        self.org_id = uuid4()
        self.user_id = uuid4()

    def test_create_rating(self):
        """Test creating a rating."""
        rating = self.service.create_rating(
            organization_id=self.org_id,
            user_id=self.user_id,
            rating_type=RatingType.AIRCRAFT_TYPE,
            rating_code='C172',
            rating_name='Cessna 172',
            aircraft_icao='C172',
            issue_date=date.today(),
        )

        assert rating is not None
        assert rating.rating_type == RatingType.AIRCRAFT_TYPE
        assert rating.status == RatingStatus.ACTIVE

    def test_record_proficiency_check(self):
        """Test recording a proficiency check."""
        rating = Rating.objects.create(
            organization_id=self.org_id,
            user_id=self.user_id,
            rating_type=RatingType.INSTRUMENT,
            rating_code='IR',
            rating_name='Instrument Rating',
            issue_date=date.today() - timedelta(days=365),
            next_proficiency_date=date.today() - timedelta(days=30),
            status=RatingStatus.ACTIVE,
        )

        updated_rating = self.service.record_proficiency_check(
            rating_id=rating.id,
            check_date=date.today(),
            examiner_id=uuid4(),
            examiner_name='Test Examiner',
            passed=True,
        )

        assert updated_rating.last_proficiency_date == date.today()
        assert updated_rating.next_proficiency_date > date.today()

    def test_check_type_rating(self):
        """Test checking type rating."""
        Rating.objects.create(
            organization_id=self.org_id,
            user_id=self.user_id,
            rating_type=RatingType.AIRCRAFT_TYPE,
            rating_code='C172',
            rating_name='Cessna 172',
            aircraft_icao='C172',
            issue_date=date.today(),
            status=RatingStatus.ACTIVE,
        )

        result = self.service.check_type_rating(
            user_id=self.user_id,
            aircraft_icao='C172',
        )

        assert result['has_rating'] is True
        assert result['is_valid'] is True


@pytest.mark.django_db
class TestEndorsementService:
    """Tests for EndorsementService."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = EndorsementService()
        self.org_id = uuid4()
        self.student_id = uuid4()
        self.instructor_id = uuid4()

    def test_create_endorsement(self):
        """Test creating an endorsement."""
        endorsement = self.service.create_endorsement(
            organization_id=self.org_id,
            student_id=self.student_id,
            student_name='Test Student',
            instructor_id=self.instructor_id,
            instructor_name='Test Instructor',
            endorsement_type=EndorsementType.SOLO,
            endorsement_code='61.87(n)',
            description='Solo flight endorsement',
            issue_date=date.today(),
            validity_days=90,
        )

        assert endorsement is not None
        assert endorsement.endorsement_type == EndorsementType.SOLO
        assert endorsement.status == EndorsementStatus.PENDING

    def test_sign_endorsement(self):
        """Test signing an endorsement."""
        endorsement = Endorsement.objects.create(
            organization_id=self.org_id,
            student_id=self.student_id,
            student_name='Test Student',
            instructor_id=self.instructor_id,
            instructor_name='Test Instructor',
            endorsement_type=EndorsementType.SOLO,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=90),
            status=EndorsementStatus.PENDING,
        )

        signed_endorsement = self.service.sign_endorsement(
            endorsement_id=endorsement.id,
            instructor_id=self.instructor_id,
            signature_data={'signature': 'test_signature_data'},
        )

        assert signed_endorsement.is_signed is True
        assert signed_endorsement.status == EndorsementStatus.ACTIVE

    def test_check_solo_authorization(self):
        """Test checking solo authorization."""
        # Create signed solo endorsement
        Endorsement.objects.create(
            organization_id=self.org_id,
            student_id=self.student_id,
            student_name='Test Student',
            instructor_id=self.instructor_id,
            instructor_name='Test Instructor',
            endorsement_type=EndorsementType.SOLO,
            aircraft_type='C172',
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=90),
            instructor_signature={'signature': 'test'},
            signed_at=timezone.now(),
            status=EndorsementStatus.ACTIVE,
        )

        result = self.service.check_solo_authorization(
            student_id=self.student_id,
            aircraft_type='C172',
        )

        assert result['authorized'] is True


@pytest.mark.django_db
class TestCurrencyService:
    """Tests for CurrencyService."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = CurrencyService()
        self.org_id = uuid4()
        self.user_id = uuid4()

    def test_create_requirement(self):
        """Test creating a currency requirement."""
        requirement = self.service.create_requirement(
            organization_id=self.org_id,
            currency_type=CurrencyType.TAKEOFF_LANDING,
            name='Day VFR Currency',
            required_takeoffs=3,
            required_landings=3,
            lookback_days=90,
        )

        assert requirement is not None
        assert requirement.currency_type == CurrencyType.TAKEOFF_LANDING

    def test_update_currency_from_flight(self):
        """Test updating currency from a flight."""
        # Create requirement
        requirement = CurrencyRequirement.objects.create(
            organization_id=self.org_id,
            currency_type=CurrencyType.TAKEOFF_LANDING,
            name='Day VFR Currency',
            required_takeoffs=3,
            required_landings=3,
            lookback_days=90,
        )

        # Update from flight
        statuses = self.service.update_currency_from_flight(
            organization_id=self.org_id,
            user_id=self.user_id,
            flight_id=uuid4(),
            flight_date=date.today(),
            aircraft_type='C172',
            takeoffs=3,
            landings=3,
        )

        assert len(statuses) > 0

    def test_check_currency(self):
        """Test checking currency status."""
        requirement = CurrencyRequirement.objects.create(
            organization_id=self.org_id,
            currency_type=CurrencyType.TAKEOFF_LANDING,
            name='Day VFR Currency',
            required_takeoffs=3,
            required_landings=3,
            lookback_days=90,
        )

        UserCurrencyStatus.objects.create(
            organization_id=self.org_id,
            user_id=self.user_id,
            requirement=requirement,
            current_takeoffs=5,
            current_landings=5,
            expiry_date=date.today() + timedelta(days=60),
            status=CurrencyStatus.CURRENT,
        )

        result = self.service.check_currency(
            user_id=self.user_id,
            currency_type=CurrencyType.TAKEOFF_LANDING,
        )

        assert result['is_current'] is True


@pytest.mark.django_db
class TestValidityService:
    """Tests for ValidityService."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = ValidityService()
        self.org_id = uuid4()
        self.user_id = uuid4()

    def test_check_validity(self):
        """Test comprehensive validity check."""
        # Create valid certificate
        Certificate.objects.create(
            organization_id=self.org_id,
            user_id=self.user_id,
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            status=CertificateStatus.ACTIVE,
        )

        # Create valid medical
        MedicalCertificate.objects.create(
            organization_id=self.org_id,
            user_id=self.user_id,
            medical_class=MedicalClass.CLASS_2,
            issuing_authority='FAA',
            examination_date=date.today(),
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            status=MedicalStatus.ACTIVE,
        )

        result = self.service.check_validity(
            user_id=self.user_id,
            check_currency=False,  # Skip currency for this test
        )

        assert result['certificate_valid'] is True
        assert result['medical_valid'] is True

    def test_can_fly(self):
        """Test simple can fly check."""
        # Create valid certificate
        Certificate.objects.create(
            organization_id=self.org_id,
            user_id=self.user_id,
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            status=CertificateStatus.ACTIVE,
        )

        # Create valid medical
        MedicalCertificate.objects.create(
            organization_id=self.org_id,
            user_id=self.user_id,
            medical_class=MedicalClass.CLASS_2,
            issuing_authority='FAA',
            examination_date=date.today(),
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            status=MedicalStatus.ACTIVE,
        )

        result = self.service.can_fly(self.user_id)
        assert result['can_fly'] is True

    def test_get_user_summary(self):
        """Test getting user summary."""
        # Create some certificates and medicals
        Certificate.objects.create(
            organization_id=self.org_id,
            user_id=self.user_id,
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            status=CertificateStatus.ACTIVE,
        )

        summary = self.service.get_user_summary(self.user_id)

        assert summary is not None
        assert 'user_id' in summary
        assert 'overall_valid' in summary
