import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from authentication.permissions import IsAdminOrAnalyst
from .models import Transaction
from .serializers import TransactionCreateSerializer, TransactionSerializer

logger = logging.getLogger(__name__)


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

        # Scoring ML automatique (CDC 5.3) — voir fraud_detection/services.py.
        # Le scoring ne doit jamais empecher l'enregistrement de la
        # transaction : en cas d'echec, on la laisse en statut "pending"
        # et on ecrit la cause dans les logs pour pouvoir la rescorer.
        from fraud_detection.services import score_transaction

        try:
            score_transaction(transaction)
        except RuntimeError as exc:
            # Cas attendu : aucun modele ML actif (voir `activer_modele_ml`).
            logger.warning(
                "Transaction %s creee mais non scoree : %s",
                transaction.transaction_id, exc,
            )
        except Exception:
            # Cas inattendu (fichier .joblib introuvable, feature manquante...).
            logger.exception(
                "Echec du scoring ML pour la transaction %s ; elle reste en 'pending'.",
                transaction.transaction_id,
            )
