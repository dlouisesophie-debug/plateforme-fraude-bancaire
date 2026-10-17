from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from authentication.permissions import IsAdminOrAnalyst
from transactions.models import Transaction
from .models import Alert
from .serializers import AlertSerializer


class AlertViewSet(viewsets.ModelViewSet):
    """
    CDC — cas d'utilisation "Traiter une alerte" : consulter, statuer
    (confirmer/rejeter), annoter. Réservé à l'Analyste Fraude et à l'Admin.

    - POST /api/alerts/{id}/confirm/  {"comment": "..."} (commentaire facultatif)
    - POST /api/alerts/{id}/reject/   {"comment": "..."}
    - PATCH /api/alerts/{id}/         {"comment": "..."} pour annoter seulement
    """

    queryset = (
        Alert.objects.all()
        .select_related("prediction__transaction", "prediction__ml_model", "assigned_to")
        .order_by("-created_at")
    )
    serializer_class = AlertSerializer
    permission_classes = [IsAdminOrAnalyst]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "severity"]

    @staticmethod
    def _maj_transaction(alert, statut):
        """Repercute la decision de l'analyste sur la transaction (Dashboard)."""
        transaction = alert.prediction.transaction
        transaction.status = statut
        transaction.save(update_fields=["status"])

    def perform_update(self, serializer):
        """PATCH : statuer et/ou annoter (champ `comment`)."""
        alert = serializer.save()
        if alert.status in (Alert.Status.CONFIRMED, Alert.Status.REJECTED) and alert.resolved_at is None:
            alert.resolved_at = timezone.now()
            alert.assigned_to = alert.assigned_to or self.request.user
            alert.save(update_fields=["resolved_at", "assigned_to"])
        if alert.status == Alert.Status.CONFIRMED:
            self._maj_transaction(alert, Transaction.Status.FRAUDULENT)
        elif alert.status == Alert.Status.REJECTED:
            self._maj_transaction(alert, Transaction.Status.LEGITIMATE)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        alert = self.get_object()
        alert.status = Alert.Status.CONFIRMED
        alert.resolved_at = timezone.now()
        alert.assigned_to = request.user
        commentaire = request.data.get("comment")
        if commentaire:
            alert.comment = commentaire
        alert.save()
        self._maj_transaction(alert, Transaction.Status.FRAUDULENT)
        return Response(AlertSerializer(alert).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        alert = self.get_object()
        alert.status = Alert.Status.REJECTED
        alert.resolved_at = timezone.now()
        alert.assigned_to = request.user
        commentaire = request.data.get("comment")
        if commentaire:
            alert.comment = commentaire
        alert.save()
        self._maj_transaction(alert, Transaction.Status.LEGITIMATE)
        return Response(AlertSerializer(alert).data)
