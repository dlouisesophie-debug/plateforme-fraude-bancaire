"""
App alerts — CDC 5.3/5.4 : seuils configurables declenchant une alerte,
cas d'utilisation "Traiter une alerte" (Analyste Fraude).
"""

from django.conf import settings
from django.db import models

from fraud_detection.models import Prediction


class Alert(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Ouverte"
        CONFIRMED = "confirmed", "Fraude confirmée"
        REJECTED = "rejected", "Rejetée"
        RESOLVED = "resolved", "Résolue"

    class Severity(models.TextChoices):
        LOW = "low", "Faible"
        MEDIUM = "medium", "Moyenne"
        HIGH = "high", "Élevée"
        CRITICAL = "critical", "Critique"

    prediction = models.OneToOneField(Prediction, on_delete=models.CASCADE, related_name="alert")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_alerts",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "alerts"
        indexes = [models.Index(fields=["status"]), models.Index(fields=["severity"])]

    def __str__(self):
        return f"Alert #{self.id} ({self.status})"
