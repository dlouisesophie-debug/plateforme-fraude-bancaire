"""
App transactions — CDC 5.2 : creer, consulter, filtrer, exporter les transactions.
"""

from django.conf import settings
from django.db import models


class Customer(models.Model):
    class Gender(models.TextChoices):
        FEMALE = "F", "Femme"
        MALE = "M", "Homme"

    full_name = models.CharField(max_length=255, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices)
    date_of_birth = models.DateField()
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    city_population = models.IntegerField(null=True, blank=True)
    profession = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        db_table = "customers"

    def __str__(self):
        return self.full_name or f"Customer #{self.pk}"


class Transaction(models.Model):
    class Channel(models.TextChoices):
        CARD = "card", "Carte"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        TRANSFER = "transfer", "Virement"
        ONLINE = "online", "Paiement en ligne"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        LEGITIMATE = "legitimate", "Legitime"
        FRAUDULENT = "fraudulent", "Frauduleuse"
        UNDER_REVIEW = "under_review", "En cours d'examen"

    transaction_id = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    merchant = models.CharField(max_length=255, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="transactions", null=True, blank=True)
    merchant_latitude = models.FloatField(null=True, blank=True)
    merchant_longitude = models.FloatField(null=True, blank=True)
    category = models.CharField(max_length=100, blank=True)
    device = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=255, blank=True)
    channel = models.CharField(max_length=30, choices=Channel.choices)
    timestamp = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transactions"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["channel"]),
        ]

    def __str__(self):
        return self.transaction_id
