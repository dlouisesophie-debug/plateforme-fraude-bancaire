"""
App transactions — CDC 5.2 : creer, consulter, filtrer, exporter les transactions.
"""

from django.conf import settings
from django.db import models


class Transaction(models.Model):
    class Channel(models.TextChoices):
        CARD = "card", "Carte"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        TRANSFER = "transfer", "Virement"
        ONLINE = "online", "Paiement en ligne"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        LEGITIMATE = "legitimate", "Légitime"
        FRAUDULENT = "fraudulent", "Frauduleuse"
        UNDER_REVIEW = "under_review", "En cours d'examen"

    class Gender(models.TextChoices):
        FEMALE = "F", "Femme"
        MALE = "M", "Homme"

    class OperationType(models.TextChoices):
        # Types d'opération mobile money du modèle (PaySim) : la valeur en
        # majuscules donne le type PaySim (cash_in -> CASH_IN, etc.).
        CASH_IN = "cash_in", "Dépôt"
        CASH_OUT = "cash_out", "Retrait"
        TRANSFER = "transfer", "Transfert"
        PAYMENT = "payment", "Paiement"
        DEBIT = "debit", "Débit vers un compte bancaire"

    transaction_id = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    merchant = models.CharField(max_length=255, blank=True)
    device = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=255, blank=True)
    channel = models.CharField(max_length=30, choices=Channel.choices)
    # Mobile money uniquement : variable du modèle mobile money (obligatoire à la saisie
    # pour ce canal, vide pour les autres canaux et pour les anciennes transactions).
    # db_default : l'ancien code, qui ne connaît pas ce champ, peut toujours écrire en base.
    operation_type = models.CharField(
        max_length=20, choices=OperationType.choices, blank=True, default="", db_default="",
    )
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

    # --- Champs necessaires au scoring ML (pipeline ml/models/fraudguard_pipeline.joblib) ---
    # Ces champs reproduisent les variables utilisees a l'entrainement
    # (voir ml/src/preprocessing.py). Sans eux, fraud_detection.services
    # ne peut pas construire les features attendues par le modele.
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Categorie du commercant, parmi celles connues du modele ML (ex: achats, achats_en_ligne, courses, restauration, voyage...). Une categorie inconnue n'est pas prise en compte par le modele.",
    )
    customer_gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    customer_birth_date = models.DateField(null=True, blank=True)
    customer_city = models.CharField(max_length=150, blank=True)
    customer_region = models.CharField(max_length=100, blank=True)
    customer_city_population = models.PositiveIntegerField(null=True, blank=True)
    customer_profession = models.CharField(max_length=150, blank=True)
    customer_latitude = models.FloatField(null=True, blank=True)
    customer_longitude = models.FloatField(null=True, blank=True)
    merchant_latitude = models.FloatField(null=True, blank=True)
    merchant_longitude = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "transactions"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["channel"]),
        ]

    def __str__(self):
        return self.transaction_id
