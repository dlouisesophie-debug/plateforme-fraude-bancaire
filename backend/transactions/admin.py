from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["transaction_id", "amount", "channel", "status", "timestamp"]
    list_filter = ["status", "channel"]
    search_fields = ["transaction_id", "merchant"]
