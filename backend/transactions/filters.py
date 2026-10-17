"""
Filtres de l'API transactions (CDC 5.2 / 5.4) : statut, canal et période.

    /api/transactions/?status=fraudulent&channel=card
    /api/transactions/?date_after=2026-10-01&date_before=2026-10-31
"""

import django_filters

from .models import Transaction


class TransactionFilter(django_filters.FilterSet):
    date_after = django_filters.DateFilter(
        field_name="timestamp", lookup_expr="date__gte",
        label="Transactions à partir de cette date (AAAA-MM-JJ)",
    )
    date_before = django_filters.DateFilter(
        field_name="timestamp", lookup_expr="date__lte",
        label="Transactions jusqu'à cette date incluse (AAAA-MM-JJ)",
    )
    min_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    max_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")

    class Meta:
        model = Transaction
        fields = ["status", "channel", "date_after", "date_before", "min_amount", "max_amount"]
