# services/certificate-service/src/apps/core/tests/conftest.py
"""
Pytest Configuration and Fixtures

Shared fixtures for certificate service tests.
"""

import pytest
from datetime import date, timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model


@pytest.fixture(scope='session')
def django_db_setup():
    """Configure Django test database."""
    pass


@pytest.fixture
def organization_id():
    """Generate a random organization ID."""
    return uuid4()


@pytest.fixture
def user_id():
    """Generate a random user ID."""
    return uuid4()


@pytest.fixture
def instructor_id():
    """Generate a random instructor ID."""
    return uuid4()


@pytest.fixture
def student_id():
    """Generate a random student ID."""
    return uuid4()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    User = get_user_model()
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def valid_certificate_data(organization_id, user_id):
    """Generate valid certificate test data."""
    from apps.core.models import CertificateType, IssuingAuthority

    return {
        'organization_id': organization_id,
        'user_id': user_id,
        'certificate_type': CertificateType.PILOT_LICENSE,
        'certificate_subtype': 'ppl',
        'issuing_authority': IssuingAuthority.FAA,
        'issuing_country': 'US',
        'certificate_number': '1234567',
        'issue_date': date.today(),
        'expiry_date': date.today() + timedelta(days=365),
    }


@pytest.fixture
def valid_medical_data(organization_id, user_id):
    """Generate valid medical certificate test data."""
    from apps.core.models import MedicalClass

    return {
        'organization_id': organization_id,
        'user_id': user_id,
        'medical_class': MedicalClass.CLASS_2,
        'issuing_authority': 'FAA',
        'issuing_country': 'US',
        'examination_date': date.today(),
        'issue_date': date.today(),
        'expiry_date': date.today() + timedelta(days=365),
    }


@pytest.fixture
def valid_rating_data(organization_id, user_id):
    """Generate valid rating test data."""
    from apps.core.models import RatingType

    return {
        'organization_id': organization_id,
        'user_id': user_id,
        'rating_type': RatingType.AIRCRAFT_TYPE,
        'rating_code': 'C172',
        'rating_name': 'Cessna 172 Type Rating',
        'aircraft_icao': 'C172',
        'issue_date': date.today(),
    }


@pytest.fixture
def valid_endorsement_data(organization_id, student_id, instructor_id):
    """Generate valid endorsement test data."""
    from apps.core.models import EndorsementType

    return {
        'organization_id': organization_id,
        'student_id': student_id,
        'student_name': 'Test Student',
        'instructor_id': instructor_id,
        'instructor_name': 'Test Instructor',
        'endorsement_type': EndorsementType.SOLO,
        'endorsement_code': '61.87(n)',
        'description': 'Solo flight endorsement',
        'issue_date': date.today(),
        'validity_days': 90,
    }


@pytest.fixture
def valid_currency_requirement_data(organization_id):
    """Generate valid currency requirement test data."""
    from apps.core.models import CurrencyType

    return {
        'organization_id': organization_id,
        'currency_type': CurrencyType.TAKEOFF_LANDING,
        'name': 'Day VFR Currency',
        'required_takeoffs': 3,
        'required_landings': 3,
        'lookback_days': 90,
    }


@pytest.fixture
def sample_certificate(db, valid_certificate_data):
    """Create a sample certificate."""
    from apps.core.models import Certificate, CertificateStatus

    return Certificate.objects.create(
        **valid_certificate_data,
        status=CertificateStatus.ACTIVE
    )


@pytest.fixture
def sample_medical(db, valid_medical_data):
    """Create a sample medical certificate."""
    from apps.core.models import MedicalCertificate, MedicalStatus

    return MedicalCertificate.objects.create(
        **valid_medical_data,
        status=MedicalStatus.ACTIVE
    )


@pytest.fixture
def sample_rating(db, valid_rating_data):
    """Create a sample rating."""
    from apps.core.models import Rating, RatingStatus

    return Rating.objects.create(
        **valid_rating_data,
        status=RatingStatus.ACTIVE
    )


@pytest.fixture
def sample_endorsement(db, valid_endorsement_data):
    """Create a sample endorsement."""
    from apps.core.models import Endorsement, EndorsementStatus

    return Endorsement.objects.create(
        **valid_endorsement_data,
        expiry_date=date.today() + timedelta(days=90),
        status=EndorsementStatus.PENDING
    )


@pytest.fixture
def sample_currency_requirement(db, valid_currency_requirement_data):
    """Create a sample currency requirement."""
    from apps.core.models import CurrencyRequirement

    return CurrencyRequirement.objects.create(**valid_currency_requirement_data)


@pytest.fixture
def fully_qualified_pilot(db, organization_id, user_id):
    """Create a fully qualified pilot with all requirements."""
    from apps.core.models import (
        Certificate, CertificateType, CertificateStatus, IssuingAuthority,
        MedicalCertificate, MedicalClass, MedicalStatus,
        Rating, RatingType, RatingStatus,
        CurrencyRequirement, CurrencyType, UserCurrencyStatus, CurrencyStatus,
    )

    # Certificate
    cert = Certificate.objects.create(
        organization_id=organization_id,
        user_id=user_id,
        certificate_type=CertificateType.PILOT_LICENSE,
        certificate_subtype='ppl',
        issuing_authority=IssuingAuthority.FAA,
        issue_date=date.today(),
        status=CertificateStatus.ACTIVE,
    )

    # Medical
    medical = MedicalCertificate.objects.create(
        organization_id=organization_id,
        user_id=user_id,
        medical_class=MedicalClass.CLASS_2,
        issuing_authority='FAA',
        examination_date=date.today(),
        issue_date=date.today(),
        expiry_date=date.today() + timedelta(days=365),
        status=MedicalStatus.ACTIVE,
    )

    # Rating
    rating = Rating.objects.create(
        organization_id=organization_id,
        user_id=user_id,
        rating_type=RatingType.AIRCRAFT_TYPE,
        rating_code='C172',
        aircraft_icao='C172',
        issue_date=date.today(),
        status=RatingStatus.ACTIVE,
    )

    # Currency requirement
    req = CurrencyRequirement.objects.create(
        organization_id=organization_id,
        currency_type=CurrencyType.TAKEOFF_LANDING,
        name='Day VFR Currency',
        required_takeoffs=3,
        required_landings=3,
        lookback_days=90,
    )

    # Currency status
    currency = UserCurrencyStatus.objects.create(
        organization_id=organization_id,
        user_id=user_id,
        requirement=req,
        current_takeoffs=5,
        current_landings=5,
        expiry_date=date.today() + timedelta(days=60),
        status=CurrencyStatus.CURRENT,
    )

    return {
        'certificate': cert,
        'medical': medical,
        'rating': rating,
        'currency_requirement': req,
        'currency_status': currency,
    }
