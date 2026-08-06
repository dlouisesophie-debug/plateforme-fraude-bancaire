from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from authentication.permissions import IsAdminOrAnalyst
from .models import Transaction
from .serializers import TransactionCreateSerializer, TransactionSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    """
    CDC 5.2 — CRUD transactions, filtrage par statut/canal/periode,
    export (a implementer, cf. app reports).
    """

    queryset = Transaction.objects.all().order_by("-timestamp")
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "channel"]

    def get_serializer_class(self):
        if self.action == "create":
            return TransactionCreateSerializer
        return TransactionSerializer

    def get_permissions(self):
        # Lecture ouverte aux roles authentifies, ecriture reservee
        # a l'agent (saisie) — a affiner selon vos besoins exacts.
        if self.action in ("update", "partial_update", "destroy"):
            return [IsAdminOrAnalyst()]
        return super().get_permissions()

    def perform_create(self, serializer):
        transaction = serializer.save(created_by=self.request.user)
        # TODO Etudiant 1 + Etudiant 2 : declencher le scoring ML ici
        # from fraud_detection.services import score_transaction
        # score_transaction(transaction)
