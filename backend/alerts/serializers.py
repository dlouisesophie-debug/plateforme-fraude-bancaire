from rest_framework import serializers

from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    """
    Alerte + informations utiles à l'analyste pour statuer sans ouvrir la
    transaction (cas d'utilisation « Consulter les alertes » / « Examiner une
    transaction scorée »). Seuls `status`, `assigned_to` et `comment`
    (annotation) sont modifiables.
    """

    transaction = serializers.IntegerField(source="prediction.transaction.id", read_only=True)
    transaction_id = serializers.CharField(source="prediction.transaction.transaction_id", read_only=True)
    amount = serializers.DecimalField(
        source="prediction.transaction.amount", max_digits=12, decimal_places=2, read_only=True,
    )
    channel = serializers.CharField(source="prediction.transaction.channel", read_only=True)
    channel_label = serializers.CharField(
        source="prediction.transaction.get_channel_display", read_only=True,
    )
    timestamp = serializers.DateTimeField(source="prediction.transaction.timestamp", read_only=True)
    transaction_status = serializers.CharField(source="prediction.transaction.status", read_only=True)
    fraud_probability = serializers.FloatField(source="prediction.fraud_probability", read_only=True)
    model_version = serializers.CharField(source="prediction.ml_model.version", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    severity_label = serializers.CharField(source="get_severity_display", read_only=True)
    assigned_to_username = serializers.CharField(
        source="assigned_to.username", read_only=True, default=None,
    )

    class Meta:
        model = Alert
        fields = "__all__"
        read_only_fields = ["id", "prediction", "severity", "created_at", "resolved_at"]
