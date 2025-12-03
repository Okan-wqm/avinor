from django.contrib import admin
from .models import Account, Invoice, Payment, Transaction, PriceList


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['account_number', 'account_name', 'account_type', 'balance', 'status']
    list_filter = ['account_type', 'status']
    search_fields = ['account_number', 'account_name', 'account_holder_id']
    ordering = ['account_number']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'account', 'invoice_date', 'due_date', 'total_amount', 'amount_due', 'status']
    list_filter = ['status']
    search_fields = ['invoice_number']
    ordering = ['-invoice_date']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_number', 'account', 'payment_date', 'amount', 'payment_method', 'status']
    list_filter = ['payment_method', 'status']
    search_fields = ['payment_number', 'transaction_reference']
    ordering = ['-payment_date']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_number', 'account', 'transaction_date', 'transaction_type', 'amount', 'balance_after']
    list_filter = ['transaction_type']
    search_fields = ['transaction_number', 'description']
    ordering = ['-transaction_date']


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ['item_code', 'item_name', 'item_type', 'unit_price', 'unit', 'is_active', 'effective_date']
    list_filter = ['item_type', 'is_active', 'taxable']
    search_fields = ['item_code', 'item_name']
    ordering = ['item_code']
