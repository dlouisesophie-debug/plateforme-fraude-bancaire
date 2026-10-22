import io
import logging

from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action

from authentication.permissions import IsAdmin, IsAdminOrAgent, IsAdminOrAnalyst
from .exports import ecrire_csv
from .filters import TransactionFilter
from .models import Transaction
from .serializers import (
    TransactionCreateSerializer,
    TransactionSerializer,
    TransactionStatusSerializer,
)

logger = logging.getLogger(__name__)


class TransactionViewSet(viewsets.ModelViewSet):
    """
    CDC 5.2 — Transactions : saisie (Agent/Admin) avec scoring ML
    automatique, consultation paginée, filtres (statut, canal, période,
    montant), recherche, tri et export CSV.

    Permissions (CDC §4) :
    - lecture et export : tout utilisateur authentifié ;
    - création : Agent Financier ou Administrateur ;
    - modification : Analyste ou Administrateur, statut uniquement ;
    - suppression : Administrateur uniquement.
    """

    queryset = (
        Transaction.objects.all()
        .select_related("prediction__ml_model", "prediction__alert")
        .order_by("-timestamp")
    )
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TransactionFilter
    search_fields = ["transaction_id", "merchant", "location", "customer_city"]
    ordering_fields = ["timestamp", "amount", "prediction__fraud_probability"]

    def get_serializer_class(self):
        if self.action == "create":
            return TransactionCreateSerializer
        if self.action in ("update", "partial_update"):
            return TransactionStatusSerializer
        return TransactionSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAdminOrAgent()]
        if self.action in ("update", "partial_update"):
            return [IsAdminOrAnalyst()]
        if self.action == "destroy":
            return [IsAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        transaction = serializer.save(created_by=self.request.user)

        # Scoring ML automatique (CDC 5.3) — voir fraud_detection/services.py.
        # Le scoring ne doit jamais empêcher l'enregistrement de la
        # transaction : en cas d'échec, on la laisse en statut "pending"
        # et on écrit la cause dans les logs pour pouvoir la rescorer.
        from fraud_detection.services import score_transaction

        try:
            score_transaction(transaction)
        except RuntimeError as exc:
            # Cas attendu : aucun modèle ML actif (voir `activer_modele_ml`).
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

    def perform_update(self, serializer):
        """
        Requalification manuelle par un analyste. Si une alerte est encore
        ouverte sur cette transaction, elle est clôturée dans le même sens
        pour que transaction et alerte restent cohérentes.
        """
        transaction = serializer.save()
        alerte = getattr(getattr(transaction, "prediction", None), "alert", None)
        if alerte is None or alerte.status != alerte.Status.OPEN:
            return
        if transaction.status == Transaction.Status.FRAUDULENT:
            alerte.status = alerte.Status.CONFIRMED
        elif transaction.status == Transaction.Status.LEGITIMATE:
            alerte.status = alerte.Status.REJECTED
        else:
            return
        alerte.resolved_at = timezone.now()
        alerte.assigned_to = self.request.user
        alerte.save(update_fields=["status", "resolved_at", "assigned_to"])

    @action(detail=False, methods=["get"], url_path="export")
    def export_csv(self, request):
        """
        Export CSV des transactions filtrées (mêmes paramètres que la liste :
        status, channel, date_after, date_before, search...).
        """
        queryset = self.filter_queryset(self.get_queryset())
        tampon = io.StringIO()
        ecrire_csv(queryset, tampon)
        nom = f"transactions_{timezone.localdate():%Y%m%d}.csv"
        reponse = HttpResponse(tampon.getvalue(), content_type="text/csv; charset=utf-8")
        reponse["Content-Disposition"] = f'attachment; filename="{nom}"'
        return reponse
