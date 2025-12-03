from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
# ViewSets will be registered here when created
# router.register(r'accounts', AccountViewSet, basename='account')
# router.register(r'invoices', InvoiceViewSet, basename='invoice')
# router.register(r'payments', PaymentViewSet, basename='payment')
# router.register(r'transactions', TransactionViewSet, basename='transaction')
# router.register(r'price-list', PriceListViewSet, basename='price-list')

urlpatterns = [
    path('', include(router.urls)),
]
