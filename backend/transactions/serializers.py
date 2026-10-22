from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Transaction


def _prediction_de(transaction):
    """Prediction liée à la transaction, ou None si elle n'a pas été scorée."""
    try:
        return transaction.prediction
    except Transaction.prediction.RelatedObjectDoesNotExist:
        return None


def _alerte_de(prediction):
    if prediction is None:
        return None
    try:
        return prediction.alert
    except prediction.__class__.alert.RelatedObjectDoesNotExist:
        return None


class TransactionSerializer(serializers.ModelSerializer):
    """
    Lecture d'une transaction (liste et détail, CDC 5.2) avec son score de
    fraude et l'alerte éventuellement déclenchée — `fields="__all__"` ne
    renvoie pas les relations inverses (prediction, alert), d'où les champs
    calculés ci-dessous.
    """

    status_label = serializers.CharField(source="get_status_display", read_only=True)
    channel_label = serializers.CharField(source="get_channel_display", read_only=True)
    fraud_probability = serializers.SerializerMethodField()
    is_fraud_predicted = serializers.SerializerMethodField()
    model_version = serializers.SerializerMethodField()
    alert_id = serializers.SerializerMethodField()
    alert_status = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "status"]

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_fraud_probability(self, obj):
        prediction = _prediction_de(obj)
        return round(prediction.fraud_probability, 4) if prediction else None

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_fraud_predicted(self, obj):
        prediction = _prediction_de(obj)
        return prediction.prediction if prediction else None

    @extend_schema_field(OpenApiTypes.STR)
    def get_model_version(self, obj):
        prediction = _prediction_de(obj)
        return prediction.ml_model.version if prediction else None

    @extend_schema_field(OpenApiTypes.INT)
    def get_alert_id(self, obj):
        alerte = _alerte_de(_prediction_de(obj))
        return alerte.id if alerte else None

    @extend_schema_field(OpenApiTypes.STR)
    def get_alert_status(self, obj):
        alerte = _alerte_de(_prediction_de(obj))
        return alerte.status if alerte else None


class TransactionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer de saisie — utilisé par l'Agent Financier (CDC 5.2).

    Les champs customer_*/merchant_*/category sont utilisés par
    fraud_detection.services.score_transaction() pour construire les
    features attendues par le pipeline ML (voir ml/src/preprocessing.py).
    Ils sont optionnels au niveau du modèle (rétrocompatibilité), mais
    doivent être fournis par le frontend/l'agent pour que le scoring soit
    fiable : une transaction sans ces données sera tout de même scorée,
    avec des valeurs par défaut neutres (0 / vide) à la place des
    informations manquantes.
    """

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être strictement supérieur à 0.")
        return value

    def to_representation(self, instance):
        # La réponse à la création renvoie la transaction complète, score
        # inclus, pour que le frontend affiche le résultat du scoring.
        instance.refresh_from_db()
        return TransactionSerializer(instance, context=self.context).data

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


class TransactionStatusSerializer(serializers.ModelSerializer):
    """
    Modification d'une transaction existante (PATCH/PUT) : seul le statut
    peut changer. Le montant, le canal et les données client sont figés
    après la saisie (intégrité et traçabilité, CDC §6) — sinon le score
    calculé ne correspondrait plus aux données enregistrées.
    """

    class Meta:
        model = Transaction
        fields = ["status"]

    def to_representation(self, instance):
        return TransactionSerializer(instance, context=self.context).data
