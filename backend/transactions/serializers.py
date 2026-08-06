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
    TODO Etudiant 1 : apres save(), appeler le service de scoring
    (app fraud_detection) pour generer automatiquement une Prediction.
    """

    class Meta:
        model = Transaction
        fields = [
            "transaction_id", "amount", "merchant", "device",
            "location", "channel", "timestamp",
        ]
