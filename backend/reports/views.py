from rest_framework import viewsets

from .models import Report
from .serializers import ReportSerializer


class ReportViewSet(viewsets.ModelViewSet):
    """
    CDC 5.5 — Generation de rapports PDF/CSV.
    TODO Etudiant 1 : implementer perform_create() pour generer reellement
    le fichier (ex. reportlab pour PDF, csv module pour CSV) et remplir
    file_path.
    """

    queryset = Report.objects.all().order_by("-created_at")
    serializer_class = ReportSerializer

    def perform_create(self, serializer):
        serializer.save(generated_by=self.request.user)
