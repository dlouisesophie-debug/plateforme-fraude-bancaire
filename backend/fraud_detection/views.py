from rest_framework import viewsets
from authentication.permissions import IsAdmin

from .models import MLModel, Prediction
from .serializers import MLModelSerializer, PredictionSerializer


class MLModelViewSet(viewsets.ModelViewSet):
    """CDC 5.5 — Suivi des modeles ML deployes. Reserve a l'admin."""

    queryset = MLModel.objects.all().order_by("-trained_at")
    serializer_class = MLModelSerializer
    permission_classes = [IsAdmin]


class PredictionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Prediction.objects.all().order_by("-prediction_date")
    serializer_class = PredictionSerializer
