# services/finance-service/src/apps/core/api/urls.py
"""
Finance Service API URLs

URL routing for all finance API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AccountViewSet,
    TransactionViewSet,
    InvoiceViewSet,
    PricingRuleViewSet,
    CreditPackageViewSet,
    UserPackageViewSet,
    PaymentMethodViewSet,
    PaymentViewSet,
)

app_name = 'finance'

# Create router
router = DefaultRouter()

# Register viewsets
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'pricing-rules', PricingRuleViewSet, basename='pricing-rule')
router.register(r'packages', CreditPackageViewSet, basename='package')
router.register(r'user-packages', UserPackageViewSet, basename='user-package')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
]
