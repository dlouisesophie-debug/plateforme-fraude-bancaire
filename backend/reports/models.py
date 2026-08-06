"""
App reports — CDC 5.5 : generation de rapports (PDF/CSV).
"""

from django.conf import settings
from django.db import models


class Report(models.Model):
    class ReportType(models.TextChoices):
        PDF = "pdf", "PDF"
        CSV = "csv", "CSV"

    title = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=ReportType.choices)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    file_path = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reports"

    def __str__(self):
        return self.title
