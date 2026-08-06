"""
Middleware d'audit automatique — journalise les requetes sur les endpoints
sensibles (ecriture sur users, transactions, alerts).

TODO Etudiant 1 (Phase 7) : affiner la liste des chemins/actions a auditer
et eviter de journaliser les requetes en lecture seule (GET) pour ne pas
saturer la table.
"""

from django.utils.deprecation import MiddlewareMixin


class AuditLogMiddleware(MiddlewareMixin):
    SENSITIVE_METHODS = ("POST", "PUT", "PATCH", "DELETE")

    def process_response(self, request, response):
        if request.path.startswith("/api/") and request.method in self.SENSITIVE_METHODS:
            if getattr(request, "user", None) and request.user.is_authenticated:
                from .models import AuditLog

                AuditLog.objects.create(
                    user=request.user,
                    action=f"{request.method} {request.path}",
                    ip_address=request.META.get("REMOTE_ADDR"),
                    details={"status_code": response.status_code},
                )
        return response
