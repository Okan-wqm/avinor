# services/certificate-service/src/apps/core/tests/test_api.py
"""
Certificate Service API Tests

Tests for certificate service REST API endpoints.
"""

import pytest
from datetime import date, timedelta
from uuid import uuid4

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

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


@pytest.fixture
def api_client():
    """Create API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client):
    """Create authenticated API client."""
    # Mock authentication
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    api_client.force_authenticate(user=user)
    api_client.user = user
    return api_client


@pytest.fixture
def organization_id():
    """Generate organization ID."""
    return uuid4()


@pytest.mark.django_db
class TestCertificateAPI:
    """Tests for Certificate API endpoints."""

    def test_list_certificates(self, authenticated_client, organization_id):
        """Test listing certificates."""
        # Create certificates
        for i in range(3):
            Certificate.objects.create(
                organization_id=organization_id,
                user_id=uuid4(),
                certificate_type=CertificateType.PILOT_LICENSE,
                issuing_authority=IssuingAuthority.FAA,
                issue_date=date.today(),
                status=CertificateStatus.ACTIVE,
            )

        response = authenticated_client.get(
            '/api/v1/certificates/',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 3

    def test_create_certificate(self, authenticated_client, organization_id):
        """Test creating a certificate."""
        data = {
            'user_id': str(uuid4()),
            'certificate_type': CertificateType.PILOT_LICENSE,
            'certificate_subtype': 'ppl',
            'issuing_authority': IssuingAuthority.FAA,
            'issuing_country': 'US',
            'certificate_number': '1234567',
            'issue_date': str(date.today()),
            'expiry_date': str(date.today() + timedelta(days=365)),
        }

        response = authenticated_client.post(
            '/api/v1/certificates/',
            data=data,
            format='json',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['certificate_type'] == CertificateType.PILOT_LICENSE

    def test_retrieve_certificate(self, authenticated_client, organization_id):
        """Test retrieving a certificate."""
        cert = Certificate.objects.create(
            organization_id=organization_id,
            user_id=uuid4(),
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            status=CertificateStatus.ACTIVE,
        )

        response = authenticated_client.get(
            f'/api/v1/certificates/{cert.id}/',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(cert.id)

    def test_verify_certificate(self, authenticated_client, organization_id):
        """Test verifying a certificate."""
        cert = Certificate.objects.create(
            organization_id=organization_id,
            user_id=uuid4(),
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            status=CertificateStatus.ACTIVE,
        )

        data = {
            'verification_method': 'document_check',
            'notes': 'Verified original document',
        }

        response = authenticated_client.post(
            f'/api/v1/certificates/{cert.id}/verify/',
            data=data,
            format='json',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['verified'] is True

    def test_suspend_certificate(self, authenticated_client, organization_id):
        """Test suspending a certificate."""
        cert = Certificate.objects.create(
            organization_id=organization_id,
            user_id=uuid4(),
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            status=CertificateStatus.ACTIVE,
        )

        data = {
            'reason': 'Test suspension for review',
        }

        response = authenticated_client.post(
            f'/api/v1/certificates/{cert.id}/suspend/',
            data=data,
            format='json',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == CertificateStatus.SUSPENDED

    def test_get_expiring_certificates(self, authenticated_client, organization_id):
        """Test getting expiring certificates."""
        # Create expiring certificate
        Certificate.objects.create(
            organization_id=organization_id,
            user_id=uuid4(),
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=20),
            status=CertificateStatus.ACTIVE,
        )

        response = authenticated_client.get(
            '/api/v1/certificates/expiring/?days=30',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1


@pytest.mark.django_db
class TestMedicalAPI:
    """Tests for Medical Certificate API endpoints."""

    def test_list_medicals(self, authenticated_client, organization_id):
        """Test listing medical certificates."""
        for i in range(2):
            MedicalCertificate.objects.create(
                organization_id=organization_id,
                user_id=uuid4(),
                medical_class=MedicalClass.CLASS_2,
                issuing_authority='FAA',
                examination_date=date.today(),
                issue_date=date.today(),
                expiry_date=date.today() + timedelta(days=365),
                status=MedicalStatus.ACTIVE,
            )

        response = authenticated_client.get(
            '/api/v1/medicals/',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_create_medical(self, authenticated_client, organization_id):
        """Test creating a medical certificate."""
        data = {
            'user_id': str(uuid4()),
            'medical_class': MedicalClass.CLASS_2,
            'issuing_authority': 'FAA',
            'issuing_country': 'US',
            'examination_date': str(date.today()),
            'issue_date': str(date.today()),
            'expiry_date': str(date.today() + timedelta(days=365)),
        }

        response = authenticated_client.post(
            '/api/v1/medicals/',
            data=data,
            format='json',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['medical_class'] == MedicalClass.CLASS_2

    def test_check_medical_validity(self, authenticated_client, organization_id):
        """Test checking medical validity."""
        user_id = uuid4()
        MedicalCertificate.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            medical_class=MedicalClass.CLASS_2,
            issuing_authority='FAA',
            examination_date=date.today(),
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            status=MedicalStatus.ACTIVE,
        )

        data = {
            'user_id': str(user_id),
        }

        response = authenticated_client.post(
            '/api/v1/medicals/check-validity/',
            data=data,
            format='json',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_valid'] is True


@pytest.mark.django_db
class TestRatingAPI:
    """Tests for Rating API endpoints."""

    def test_list_ratings(self, authenticated_client, organization_id):
        """Test listing ratings."""
        for i in range(2):
            Rating.objects.create(
                organization_id=organization_id,
                user_id=uuid4(),
                rating_type=RatingType.AIRCRAFT_TYPE,
                rating_code=f'C17{i}',
                rating_name=f'Cessna 17{i}',
                issue_date=date.today(),
                status=RatingStatus.ACTIVE,
            )

        response = authenticated_client.get(
            '/api/v1/ratings/',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_create_rating(self, authenticated_client, organization_id):
        """Test creating a rating."""
        data = {
            'user_id': str(uuid4()),
            'rating_type': RatingType.AIRCRAFT_TYPE,
            'rating_code': 'C172',
            'rating_name': 'Cessna 172',
            'aircraft_icao': 'C172',
            'issue_date': str(date.today()),
        }

        response = authenticated_client.post(
            '/api/v1/ratings/',
            data=data,
            format='json',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['rating_type'] == RatingType.AIRCRAFT_TYPE

    def test_check_type_rating(self, authenticated_client, organization_id):
        """Test checking type rating."""
        user_id = uuid4()
        Rating.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            rating_type=RatingType.AIRCRAFT_TYPE,
            rating_code='C172',
            rating_name='Cessna 172',
            aircraft_icao='C172',
            issue_date=date.today(),
            status=RatingStatus.ACTIVE,
        )

        data = {
            'user_id': str(user_id),
            'aircraft_icao': 'C172',
        }

        response = authenticated_client.post(
            '/api/v1/ratings/check-type-rating/',
            data=data,
            format='json',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['has_rating'] is True


@pytest.mark.django_db
class TestEndorsementAPI:
    """Tests for Endorsement API endpoints."""

    def test_list_endorsements(self, authenticated_client, organization_id):
        """Test listing endorsements."""
        for i in range(2):
            Endorsement.objects.create(
                organization_id=organization_id,
                student_id=uuid4(),
                student_name=f'Student {i}',
                instructor_id=uuid4(),
                instructor_name='Instructor',
                endorsement_type=EndorsementType.SOLO,
                issue_date=date.today(),
                expiry_date=date.today() + timedelta(days=90),
                status=EndorsementStatus.ACTIVE,
            )

        response = authenticated_client.get(
            '/api/v1/endorsements/',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_create_endorsement(self, authenticated_client, organization_id):
        """Test creating an endorsement."""
        data = {
            'student_id': str(uuid4()),
            'student_name': 'Test Student',
            'instructor_id': str(uuid4()),
            'instructor_name': 'Test Instructor',
            'endorsement_type': EndorsementType.SOLO,
            'endorsement_code': '61.87(n)',
            'description': 'Solo flight endorsement',
            'issue_date': str(date.today()),
            'validity_days': 90,
        }

        response = authenticated_client.post(
            '/api/v1/endorsements/',
            data=data,
            format='json',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['endorsement_type'] == EndorsementType.SOLO

    def test_check_solo_authorization(self, authenticated_client, organization_id):
        """Test checking solo authorization."""
        student_id = uuid4()
        Endorsement.objects.create(
            organization_id=organization_id,
            student_id=student_id,
            student_name='Test Student',
            instructor_id=uuid4(),
            instructor_name='Test Instructor',
            endorsement_type=EndorsementType.SOLO,
            aircraft_type='C172',
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=90),
            instructor_signature={'signature': 'test'},
            signed_at=date.today(),
            status=EndorsementStatus.ACTIVE,
        )

        data = {
            'student_id': str(student_id),
            'aircraft_type': 'C172',
        }

        response = authenticated_client.post(
            '/api/v1/endorsements/check-solo/',
            data=data,
            format='json',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['authorized'] is True


@pytest.mark.django_db
class TestCurrencyAPI:
    """Tests for Currency API endpoints."""

    def test_list_currency_requirements(self, authenticated_client, organization_id):
        """Test listing currency requirements."""
        CurrencyRequirement.objects.create(
            organization_id=organization_id,
            currency_type=CurrencyType.TAKEOFF_LANDING,
            name='Day VFR Currency',
            required_takeoffs=3,
            required_landings=3,
            lookback_days=90,
        )

        response = authenticated_client.get(
            '/api/v1/currency/requirements/',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_check_currency(self, authenticated_client, organization_id):
        """Test checking currency status."""
        user_id = uuid4()
        requirement = CurrencyRequirement.objects.create(
            organization_id=organization_id,
            currency_type=CurrencyType.TAKEOFF_LANDING,
            name='Day VFR Currency',
            required_takeoffs=3,
            required_landings=3,
            lookback_days=90,
        )
        UserCurrencyStatus.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            requirement=requirement,
            current_takeoffs=5,
            current_landings=5,
            expiry_date=date.today() + timedelta(days=60),
            status=CurrencyStatus.CURRENT,
        )

        data = {
            'user_id': str(user_id),
            'currency_type': CurrencyType.TAKEOFF_LANDING,
        }

        response = authenticated_client.post(
            '/api/v1/currency/status/check/',
            data=data,
            format='json',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_current'] is True


@pytest.mark.django_db
class TestValidityAPI:
    """Tests for Validity API endpoints."""

    def test_validity_check(self, authenticated_client, organization_id):
        """Test comprehensive validity check."""
        user_id = uuid4()

        # Create valid certificate
        Certificate.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            status=CertificateStatus.ACTIVE,
        )

        # Create valid medical
        MedicalCertificate.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            medical_class=MedicalClass.CLASS_2,
            issuing_authority='FAA',
            examination_date=date.today(),
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            status=MedicalStatus.ACTIVE,
        )

        data = {
            'user_id': str(user_id),
            'check_currency': False,
        }

        response = authenticated_client.post(
            '/api/v1/validity/check/',
            data=data,
            format='json',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['certificate_valid'] is True
        assert response.data['medical_valid'] is True

    def test_can_fly_check(self, authenticated_client, organization_id):
        """Test simple can fly check."""
        user_id = uuid4()

        # Create valid certificate
        Certificate.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            status=CertificateStatus.ACTIVE,
        )

        # Create valid medical
        MedicalCertificate.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            medical_class=MedicalClass.CLASS_2,
            issuing_authority='FAA',
            examination_date=date.today(),
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            status=MedicalStatus.ACTIVE,
        )

        data = {
            'user_id': str(user_id),
        }

        response = authenticated_client.post(
            '/api/v1/validity/can-fly/',
            data=data,
            format='json',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['can_fly'] is True

    def test_user_summary(self, authenticated_client, organization_id):
        """Test getting user summary."""
        user_id = uuid4()

        Certificate.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            certificate_type=CertificateType.PILOT_LICENSE,
            issuing_authority=IssuingAuthority.FAA,
            issue_date=date.today(),
            status=CertificateStatus.ACTIVE,
        )

        response = authenticated_client.get(
            f'/api/v1/validity/summary/{user_id}/',
            HTTP_X_ORGANIZATION_ID=str(organization_id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'user_id' in response.data
