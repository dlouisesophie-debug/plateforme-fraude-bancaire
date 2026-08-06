"""
App audit — CDC section 6 : logs d'audit des acces aux donnees sensibles
(conformite RGPD).
"""

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        indexes = [models.Index(fields=["created_at"]), models.Index(fields=["action"])]

    def __str__(self):
        return f"{self.action} — {self.created_at}"
