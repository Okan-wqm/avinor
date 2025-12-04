# services/finance-service/src/apps/core/api/views/account_views.py
"""
Account Views

DRF viewset for account management.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from ...models.account import Account
from ...services.account_service import (
    AccountService,
    AccountServiceError,
    AccountNotFoundError,
    InsufficientBalanceError,
    AccountSuspendedError,
)
from ..serializers.account_serializers import (
    AccountSerializer,
    AccountListSerializer,
    AccountDetailSerializer,
    AccountCreateSerializer,
    AccountUpdateSerializer,
    AccountSummarySerializer,
    ChargeAccountSerializer,
    CreditAccountSerializer,
    TransferBalanceSerializer,
    SuspendAccountSerializer,
    CloseAccountSerializer,
    UpdateCreditLimitSerializer,
)

logger = logging.getLogger(__name__)


class AccountViewSet(viewsets.ViewSet):
    """
    ViewSet for managing financial accounts.

    Provides CRUD operations plus balance management actions.
    """

    permission_classes = [IsAuthenticated]

    def get_organization_id(self, request):
        """Get organization ID from request."""
        return request.headers.get('X-Organization-ID') or request.user.organization_id

    def list(self, request):
        """
        List accounts with filtering.

        GET /api/v1/finance/accounts/
        """
        organization_id = self.get_organization_id(request)

        result = AccountService.list_accounts(
            organization_id=organization_id,
            account_type=request.query_params.get('account_type'),
            status=request.query_params.get('status'),
            is_overdrawn=request.query_params.get('is_overdrawn'),
            search=request.query_params.get('search'),
            order_by=request.query_params.get('order_by', '-created_at'),
            limit=int(request.query_params.get('limit', 50)),
            offset=int(request.query_params.get('offset', 0)),
        )

        return Response(result)

    def retrieve(self, request, pk=None):
        """
        Get account details.

        GET /api/v1/finance/accounts/{id}/
        """
        try:
            organization_id = self.get_organization_id(request)
            account = AccountService.get_account(pk, organization_id)
            serializer = AccountDetailSerializer(account)
            return Response(serializer.data)
        except AccountNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    def create(self, request):
        """
        Create a new account.

        POST /api/v1/finance/accounts/
        """
        serializer = AccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            account = AccountService.create_account(
                organization_id=organization_id,
                **serializer.validated_data
            )

            return Response(
                AccountDetailSerializer(account).data,
                status=status.HTTP_201_CREATED
            )
        except AccountServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def partial_update(self, request, pk=None):
        """
        Update account details.

        PATCH /api/v1/finance/accounts/{id}/
        """
        serializer = AccountUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            account = AccountService.update_account(
                account_id=pk,
                organization_id=organization_id,
                **serializer.validated_data
            )

            return Response(AccountDetailSerializer(account).data)
        except AccountNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except AccountServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """
        Get account summary.

        GET /api/v1/finance/accounts/{id}/summary/
        """
        try:
            organization_id = self.get_organization_id(request)
            summary = AccountService.get_account_summary(pk, organization_id)
            return Response(summary)
        except AccountNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def by_owner(self, request):
        """
        Get account by owner.

        GET /api/v1/finance/accounts/by_owner/?owner_id=...&owner_type=user
        """
        organization_id = self.get_organization_id(request)
        owner_id = request.query_params.get('owner_id')
        owner_type = request.query_params.get('owner_type', 'user')

        if not owner_id:
            return Response(
                {'error': 'owner_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        account = AccountService.get_account_by_owner(
            organization_id=organization_id,
            owner_id=owner_id,
            owner_type=owner_type
        )

        if not account:
            return Response(
                {'error': 'Account not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(AccountDetailSerializer(account).data)

    @action(detail=True, methods=['post'])
    def charge(self, request, pk=None):
        """
        Charge an amount to the account.

        POST /api/v1/finance/accounts/{id}/charge/
        """
        serializer = ChargeAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = AccountService.charge_account(
                account_id=pk,
                created_by=request.user.id,
                **serializer.validated_data
            )
            return Response(result)
        except AccountNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except InsufficientBalanceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except AccountSuspendedError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )

    @action(detail=True, methods=['post'])
    def credit(self, request, pk=None):
        """
        Credit an amount to the account.

        POST /api/v1/finance/accounts/{id}/credit/
        """
        serializer = CreditAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = AccountService.credit_account(
                account_id=pk,
                created_by=request.user.id,
                **serializer.validated_data
            )
            return Response(result)
        except AccountNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def transfer(self, request, pk=None):
        """
        Transfer balance to another account.

        POST /api/v1/finance/accounts/{id}/transfer/
        """
        serializer = TransferBalanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = AccountService.transfer_balance(
                from_account_id=pk,
                to_account_id=serializer.validated_data['to_account_id'],
                amount=serializer.validated_data['amount'],
                description=serializer.validated_data.get('description'),
                created_by=request.user.id
            )
            return Response(result)
        except AccountNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except InsufficientBalanceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """
        Suspend an account.

        POST /api/v1/finance/accounts/{id}/suspend/
        """
        serializer = SuspendAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            account = AccountService.suspend_account(
                account_id=pk,
                reason=serializer.validated_data['reason'],
                suspended_by=request.user.id
            )
            return Response(AccountDetailSerializer(account).data)
        except AccountNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        """
        Reactivate a suspended account.

        POST /api/v1/finance/accounts/{id}/reactivate/
        """
        try:
            account = AccountService.reactivate_account(
                account_id=pk,
                reactivated_by=request.user.id
            )
            return Response(AccountDetailSerializer(account).data)
        except AccountNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except AccountServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """
        Close an account.

        POST /api/v1/finance/accounts/{id}/close/
        """
        serializer = CloseAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            account = AccountService.close_account(
                account_id=pk,
                reason=serializer.validated_data.get('reason'),
                closed_by=request.user.id
            )
            return Response(AccountDetailSerializer(account).data)
        except AccountNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except AccountServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def update_credit_limit(self, request, pk=None):
        """
        Update account credit limit.

        POST /api/v1/finance/accounts/{id}/update_credit_limit/
        """
        serializer = UpdateCreditLimitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            account = AccountService.update_credit_limit(
                account_id=pk,
                new_limit=serializer.validated_data['credit_limit'],
                reason=serializer.validated_data.get('reason'),
                updated_by=request.user.id
            )
            return Response(AccountDetailSerializer(account).data)
        except AccountNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """
        Get accounts with overdue balances.

        GET /api/v1/finance/accounts/overdue/?days_overdue=30
        """
        organization_id = self.get_organization_id(request)
        days_overdue = int(request.query_params.get('days_overdue', 30))

        accounts = AccountService.get_overdue_accounts(
            organization_id=organization_id,
            days_overdue=days_overdue
        )

        return Response({
            'accounts': AccountListSerializer(accounts, many=True).data,
            'count': len(accounts),
        })

    @action(detail=False, methods=['get'])
    def low_balance(self, request):
        """
        Get accounts with low balance.

        GET /api/v1/finance/accounts/low_balance/?threshold=100
        """
        organization_id = self.get_organization_id(request)
        threshold = request.query_params.get('threshold')

        if threshold:
            from decimal import Decimal
            threshold = Decimal(threshold)

        accounts = AccountService.get_low_balance_accounts(
            organization_id=organization_id,
            threshold=threshold
        )

        return Response({
            'accounts': AccountListSerializer(accounts, many=True).data,
            'count': len(accounts),
        })

    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """
        Recalculate account totals from transactions.

        POST /api/v1/finance/accounts/{id}/recalculate/
        """
        try:
            account = AccountService.recalculate_totals(pk)
            return Response(AccountDetailSerializer(account).data)
        except AccountNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
