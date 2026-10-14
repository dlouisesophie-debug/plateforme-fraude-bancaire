from rest_framework import serializers

from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "status"]


class TransactionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer de saisie — utilise par l'Agent Financier (CDC 5.2).

    Les champs customer_*/merchant_*/category sont utilises par
    fraud_detection.services.score_transaction() pour construire les
    features attendues par le pipeline ML (voir ml/src/preprocessing.py).
    Ils sont optionnels au niveau du modele (retrocompatibilite), mais
    doivent etre fournis par le frontend/l'agent pour que le scoring soit
    fiable : une transaction sans ces donnees sera tout de meme scoree,
    avec des valeurs par defaut neutres (0 / vide) a la place des
    informations manquantes.
    """

    class Meta:
        model = Transaction
        fields = [
            "transaction_id", "amount", "merchant", "device",
            "location", "channel", "timestamp",
            "category",
            "customer_gender", "customer_birth_date", "customer_city",
            "customer_region", "customer_city_population", "customer_profession",
            "customer_latitude", "customer_longitude",
            "merchant_latitude", "merchant_longitude",
        ]
