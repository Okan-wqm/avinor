# services/user-service/src/apps/core/views/auth.py
"""
Authentication ViewSet - Comprehensive authentication API

Provides endpoints for:
- User registration and email verification
- Login with 2FA support
- Token management (refresh, revoke)
- Password management (change, forgot, reset)
- 2FA setup and management
- Session management
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.core.serializers import (
    # Registration
    RegisterSerializer,
    RegisterResponseSerializer,
    # Login
    LoginSerializer,
    TwoFactorVerifySerializer,
    TokenResponseSerializer,
    TwoFactorRequiredResponseSerializer,
    # Token management
    RefreshTokenSerializer,
    LogoutSerializer,
    TokenVerifySerializer,
    TokenVerifyResponseSerializer,
    # Password management
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    # Email verification
    EmailVerificationSerializer,
    ResendVerificationSerializer,
    # 2FA
    TwoFactorSetupSerializer,
    TwoFactorSetupResponseSerializer,
    TwoFactorConfirmSerializer,
    TwoFactorConfirmResponseSerializer,
    TwoFactorDisableSerializer,
    BackupCodesRegenerateSerializer,
    BackupCodesResponseSerializer,
    # Sessions
    SessionListSerializer,
    SessionTerminateSerializer,
)
from apps.core.services import (
    AuthService,
    AuthenticationError,
    InvalidCredentialsError,
    AccountLockedError,
    AccountInactiveError,
    TwoFactorRequiredError,
    InvalidTokenError,
    PasswordPolicyError,
)

logger = logging.getLogger(__name__)


class AuthViewSet(viewsets.ViewSet):
    """
    ViewSet for authentication operations.

    Endpoints:
    - POST /auth/register/ - Register new user
    - POST /auth/login/ - Login
    - POST /auth/verify-2fa/ - Verify 2FA code
    - POST /auth/refresh/ - Refresh access token
    - POST /auth/logout/ - Logout
    - POST /auth/verify-email/ - Verify email
    - POST /auth/resend-verification/ - Resend verification email
    - POST /auth/forgot-password/ - Request password reset
    - POST /auth/reset-password/ - Reset password
    - POST /auth/change-password/ - Change password (authenticated)
    - POST /auth/verify-token/ - Verify JWT token
    - GET /auth/sessions/ - List active sessions
    - POST /auth/sessions/terminate/ - Terminate session
    - POST /auth/2fa/setup/ - Setup 2FA
    - POST /auth/2fa/confirm/ - Confirm 2FA setup
    - POST /auth/2fa/disable/ - Disable 2FA
    - POST /auth/2fa/backup-codes/ - Regenerate backup codes
    """

    permission_classes = [AllowAny]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_service = AuthService()

    def _get_client_ip(self, request) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def _get_user_agent(self, request) -> str:
        """Extract user agent from request."""
        return request.META.get('HTTP_USER_AGENT', '')[:500]

    def _get_device_info(self, request) -> str:
        """Extract device info from request headers."""
        return request.META.get('HTTP_X_DEVICE_INFO', '')[:255]

    def _error_response(self, error: Exception, status_code: int = 400) -> Response:
        """Create standardized error response."""
        if isinstance(error, AuthenticationError):
            return Response({
                'success': False,
                'error': {
                    'code': error.code,
                    'message': error.message,
                    'details': error.details
                }
            }, status=status_code)

        return Response({
            'success': False,
            'error': {
                'code': 'error',
                'message': str(error)
            }
        }, status=status_code)

    # ==================== REGISTRATION ====================

    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register a new user account.

        Requires email verification before account is activated.
        """
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            data = serializer.validated_data
            user, verification_token = self.auth_service.register(
                email=data['email'],
                password=data['password'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                organization_id=data.get('organization_id'),
                phone=data.get('phone', ''),
            )

            # TODO: Send verification email via notification service

            return Response({
                'success': True,
                'data': {
                    'message': 'Registration successful. Please check your email to verify your account.',
                    'user_id': str(user.id),
                    'email': user.email,
                    'verification_required': True,
                },
                'message': 'Registration successful'
            }, status=status.HTTP_201_CREATED)

        except AuthenticationError as e:
            return self._error_response(e, status.HTTP_400_BAD_REQUEST)

    # ==================== LOGIN ====================

    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        User login endpoint.

        Returns access and refresh tokens, or 2FA requirement.
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = self.auth_service.login(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                ip_address=self._get_client_ip(request),
                user_agent=self._get_user_agent(request),
                device_info=self._get_device_info(request),
            )

            return Response({
                'success': True,
                'data': result,
                'message': 'Login successful'
            })

        except TwoFactorRequiredError as e:
            return Response({
                'success': True,
                'data': {
                    'requires_2fa': True,
                    'temp_token': e.details['temp_token'],
                    'available_methods': e.details['available_methods'],
                },
                'message': 'Two-factor authentication required'
            })

        except InvalidCredentialsError as e:
            return self._error_response(e, status.HTTP_401_UNAUTHORIZED)

        except AccountLockedError as e:
            return self._error_response(e, status.HTTP_423_LOCKED)

        except AccountInactiveError as e:
            return self._error_response(e, status.HTTP_403_FORBIDDEN)

        except AuthenticationError as e:
            return self._error_response(e, status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='verify-2fa')
    def verify_2fa(self, request):
        """
        Verify 2FA code during login.
        """
        serializer = TwoFactorVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = self.auth_service.verify_2fa(
                temp_token=serializer.validated_data['temp_token'],
                code=serializer.validated_data['code'],
                method=serializer.validated_data.get('method', 'totp'),
                ip_address=self._get_client_ip(request),
                user_agent=self._get_user_agent(request),
                device_info=self._get_device_info(request),
            )

            return Response({
                'success': True,
                'data': result,
                'message': 'Login successful'
            })

        except InvalidTokenError as e:
            return self._error_response(e, status.HTTP_401_UNAUTHORIZED)

        except AuthenticationError as e:
            return self._error_response(e, status.HTTP_400_BAD_REQUEST)

    # ==================== TOKEN MANAGEMENT ====================

    @action(detail=False, methods=['post'])
    def refresh(self, request):
        """
        Refresh access token using refresh token.
        """
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = self.auth_service.refresh_tokens(
                refresh_token=serializer.validated_data['refresh_token']
            )

            return Response({
                'success': True,
                'data': result
            })

        except InvalidTokenError as e:
            return self._error_response(e, status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """
        Logout user and revoke tokens.
        """
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.auth_service.logout(
            user=request.user,
            refresh_token=serializer.validated_data.get('refresh_token'),
            session_id=getattr(request, 'session_id', None),
            logout_all=serializer.validated_data.get('logout_all', False)
        )

        message = 'Logged out from all devices' if serializer.validated_data.get('logout_all') else 'Logged out successfully'

        return Response({
            'success': True,
            'message': message
        })

    @action(detail=False, methods=['post'], url_path='verify-token')
    def verify_token(self, request):
        """
        Verify if a JWT token is valid.
        Used by other services for token validation.
        """
        serializer = TokenVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = self.auth_service.verify_access_token(
                token=serializer.validated_data['token']
            )

            return Response({
                'success': True,
                'data': result
            })

        except InvalidTokenError as e:
            return self._error_response(e, status.HTTP_401_UNAUTHORIZED)

    # ==================== EMAIL VERIFICATION ====================

    @action(detail=False, methods=['post'], url_path='verify-email')
    def verify_email(self, request):
        """
        Verify email with token.
        """
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = self.auth_service.verify_email(
                token=serializer.validated_data['token']
            )

            return Response({
                'success': True,
                'data': {
                    'user_id': str(user.id),
                    'email': user.email,
                    'verified': True
                },
                'message': 'Email verified successfully'
            })

        except InvalidTokenError as e:
            return self._error_response(e, status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='resend-verification')
    def resend_verification(self, request):
        """
        Resend email verification.
        """
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = self.auth_service.resend_verification_email(
                email=serializer.validated_data['email']
            )

            # Don't reveal if email exists or if already verified
            return Response({
                'success': True,
                'message': 'If an unverified account exists with this email, a verification email has been sent.'
            })

        except AuthenticationError as e:
            return self._error_response(e, status.HTTP_400_BAD_REQUEST)

    # ==================== PASSWORD MANAGEMENT ====================

    @action(detail=False, methods=['post'], url_path='forgot-password')
    def forgot_password(self, request):
        """
        Request password reset email.
        """
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = self.auth_service.forgot_password(
                email=serializer.validated_data['email'],
                ip_address=self._get_client_ip(request)
            )

            # TODO: Send reset email via notification service

            # Always return success to prevent email enumeration
            return Response({
                'success': True,
                'message': 'If an account exists with this email, you will receive a password reset link.'
            })

        except AuthenticationError as e:
            # Rate limiting error
            return self._error_response(e, status.HTTP_429_TOO_MANY_REQUESTS)

    @action(detail=False, methods=['post'], url_path='reset-password')
    def reset_password(self, request):
        """
        Reset password with token.
        """
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = self.auth_service.reset_password(
                token=serializer.validated_data['token'],
                new_password=serializer.validated_data['new_password'],
                ip_address=self._get_client_ip(request)
            )

            return Response({
                'success': True,
                'message': 'Password reset successfully. Please login with your new password.'
            })

        except InvalidTokenError as e:
            return self._error_response(e, status.HTTP_400_BAD_REQUEST)

        except PasswordPolicyError as e:
            return self._error_response(e, status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='change-password', permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """
        Change password for authenticated user.
        """
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.auth_service.change_password(
                user=request.user,
                current_password=serializer.validated_data['current_password'],
                new_password=serializer.validated_data['new_password'],
                ip_address=self._get_client_ip(request)
            )

            return Response({
                'success': True,
                'message': 'Password changed successfully.'
            })

        except AuthenticationError as e:
            return self._error_response(e, status.HTTP_400_BAD_REQUEST)

        except PasswordPolicyError as e:
            return self._error_response(e, status.HTTP_400_BAD_REQUEST)

    # ==================== 2FA MANAGEMENT ====================

    @action(detail=False, methods=['post'], url_path='2fa/setup', permission_classes=[IsAuthenticated])
    def setup_2fa(self, request):
        """
        Initiate 2FA setup.
        """
        serializer = TwoFactorSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = self.auth_service.setup_2fa(
                user=request.user,
                method=serializer.validated_data.get('method', 'totp')
            )

            return Response({
                'success': True,
                'data': result,
                'message': 'Scan the QR code with your authenticator app'
            })

        except AuthenticationError as e:
            return self._error_response(e, status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='2fa/confirm', permission_classes=[IsAuthenticated])
    def confirm_2fa(self, request):
        """
        Confirm 2FA setup with verification code.
        """
        serializer = TwoFactorConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = self.auth_service.confirm_2fa_setup(
                user=request.user,
                code=serializer.validated_data['code']
            )

            return Response({
                'success': True,
                'data': result,
                'message': 'Two-factor authentication enabled. Save your backup codes!'
            })

        except AuthenticationError as e:
            return self._error_response(e, status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='2fa/disable', permission_classes=[IsAuthenticated])
    def disable_2fa(self, request):
        """
        Disable 2FA.
        """
        serializer = TwoFactorDisableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.auth_service.disable_2fa(
                user=request.user,
                password=serializer.validated_data['password']
            )

            return Response({
                'success': True,
                'message': 'Two-factor authentication disabled'
            })

        except AuthenticationError as e:
            return self._error_response(e, status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='2fa/backup-codes', permission_classes=[IsAuthenticated])
    def regenerate_backup_codes(self, request):
        """
        Regenerate 2FA backup codes.
        """
        serializer = BackupCodesRegenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            backup_codes = self.auth_service.regenerate_backup_codes(
                user=request.user,
                password=serializer.validated_data['password']
            )

            return Response({
                'success': True,
                'data': {
                    'backup_codes': backup_codes,
                    'message': 'Save these backup codes in a secure location. They will not be shown again.'
                }
            })

        except AuthenticationError as e:
            return self._error_response(e, status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='2fa/status', permission_classes=[IsAuthenticated])
    def get_2fa_status(self, request):
        """
        Get current 2FA status.
        """
        user = request.user
        return Response({
            'success': True,
            'data': {
                'enabled': user.two_factor_enabled,
                'method': user.two_factor_method if user.two_factor_enabled else None,
                'has_backup_codes': bool(user.two_factor_backup_codes),
                'backup_codes_count': len(user.two_factor_backup_codes) if user.two_factor_backup_codes else 0
            }
        })

    # ==================== SESSION MANAGEMENT ====================

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def sessions(self, request):
        """
        List active sessions.
        """
        sessions = self.auth_service.get_active_sessions(request.user)

        # Mark current session
        current_session_id = getattr(request, 'session_id', None)
        for session in sessions:
            session['is_current'] = str(session['id']) == str(current_session_id)

        return Response({
            'success': True,
            'data': sessions
        })

    @action(detail=False, methods=['post'], url_path='sessions/terminate', permission_classes=[IsAuthenticated])
    def terminate_session(self, request):
        """
        Terminate a specific session.
        """
        serializer = SessionTerminateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_id = str(serializer.validated_data['session_id'])
        current_session_id = str(getattr(request, 'session_id', ''))

        if session_id == current_session_id:
            return Response({
                'success': False,
                'error': {
                    'message': 'Cannot terminate current session. Use logout instead.'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        self.auth_service.terminate_session(
            user=request.user,
            session_id=session_id
        )

        return Response({
            'success': True,
            'message': 'Session terminated'
        })

    @action(detail=False, methods=['post'], url_path='sessions/terminate-others', permission_classes=[IsAuthenticated])
    def terminate_other_sessions(self, request):
        """
        Terminate all sessions except current.
        """
        current_session_id = getattr(request, 'session_id', None)

        if not current_session_id:
            return Response({
                'success': False,
                'error': {
                    'message': 'Current session not found'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        count = self.auth_service.terminate_all_other_sessions(
            user=request.user,
            current_session_id=str(current_session_id)
        )

        return Response({
            'success': True,
            'message': f'Terminated {count} session(s)'
        })
