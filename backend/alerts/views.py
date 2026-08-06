from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from authentication.permissions import IsAdminOrAnalyst
from .models import Alert
from .serializers import AlertSerializer


class AlertViewSet(viewsets.ModelViewSet):
    """
    CDC — cas d'utilisation "Traiter une alerte" : consulter, statuer
    (confirmer/rejeter), annoter. Reserve a l'Analyste Fraude et l'Admin.
    """

    queryset = Alert.objects.all().order_by("-created_at")
    serializer_class = AlertSerializer
    permission_classes = [IsAdminOrAnalyst]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "severity"]

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        alert = self.get_object()
        alert.status = Alert.Status.CONFIRMED
        alert.resolved_at = timezone.now()
        alert.assigned_to = request.user
        alert.save()
        return Response(AlertSerializer(alert).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        alert = self.get_object()
        alert.status = Alert.Status.REJECTED
        alert.resolved_at = timezone.now()
        alert.assigned_to = request.user
        alert.save()
        return Response(AlertSerializer(alert).data)
