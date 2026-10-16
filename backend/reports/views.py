from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework import mixins, viewsets
from rest_framework.decorators import action

from authentication.permissions import IsAdmin
from .generation import generer_fichier
from .models import Report
from .serializers import ReportSerializer


def _est_admin(user):
    return user.is_superuser or getattr(user, "role", None) == "admin"


class ReportViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    CDC 5.5 — Rapports PDF/CSV.

    - POST /api/reports/ {"title", "type": "pdf"|"csv", "period_start", "period_end"}
      génère réellement le fichier (cas d'utilisation « Exporter des rapports »).
    - GET /api/reports/{id}/download/ télécharge le fichier.
    - L'administrateur voit tous les rapports (« Consulter tous les
      rapports ») ; les autres utilisateurs voient les leurs.
    - Suppression réservée à l'administrateur. Un rapport n'est pas
      modifiable : on en génère un nouveau.
    """

    serializer_class = ReportSerializer

    def get_queryset(self):
        qs = Report.objects.select_related("generated_by").order_by("-created_at")
        if getattr(self, "swagger_fake_view", False):  # génération du schéma Swagger
            return qs.none()
        if _est_admin(self.request.user):
            return qs
        return qs.filter(generated_by=self.request.user)

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        report = serializer.save(generated_by=self.request.user)
        generer_fichier(report)

    def perform_destroy(self, instance):
        if instance.file_path:
            (Path(settings.MEDIA_ROOT) / instance.file_path).unlink(missing_ok=True)
        instance.delete()

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        report = self.get_object()
        chemin = Path(settings.MEDIA_ROOT) / report.file_path if report.file_path else None
        if chemin is None or not chemin.is_file():
            raise Http404("Fichier du rapport introuvable.")
        content_type = "application/pdf" if report.type == Report.ReportType.PDF else "text/csv"
        return FileResponse(open(chemin, "rb"), as_attachment=True, filename=chemin.name,
                            content_type=content_type)
