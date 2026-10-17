from django.utils.dateparse import parse_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from transactions.models import Transaction

from .services import calculer_statistiques


def lire_date(params, nom):
    valeur = params.get(nom)
    if not valeur:
        return None
    date = parse_date(valeur)
    if date is None:
        raise ValidationError({nom: "Format attendu : AAAA-MM-JJ."})
    return date


class DashboardStatsView(APIView):
    """
    GET /api/dashboard/stats/ — indicateurs du tableau de bord (CDC 5.4) :
    KPIs, répartition par statut et par canal, évolution par jour, matrice
    de confusion du modèle en production et modèle actif.

    Accessible à tout utilisateur authentifié (les trois rôles consultent
    le dashboard, cf. diagramme de cas d'utilisation).
    """

    @extend_schema(
        parameters=[
            OpenApiParameter("date_after", OpenApiTypes.DATE, description="Début de période (inclus)"),
            OpenApiParameter("date_before", OpenApiTypes.DATE, description="Fin de période (incluse)"),
            OpenApiParameter("channel", OpenApiTypes.STR, enum=Transaction.Channel.values),
        ],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        date_after = lire_date(request.query_params, "date_after")
        date_before = lire_date(request.query_params, "date_before")
        channel = request.query_params.get("channel") or None
        if channel and channel not in Transaction.Channel.values:
            raise ValidationError({"channel": f"Valeurs possibles : {', '.join(Transaction.Channel.values)}."})
        if date_after and date_before and date_after > date_before:
            raise ValidationError({"date_before": "La fin de période doit être après le début."})
        return Response(calculer_statistiques(date_after, date_before, channel))
