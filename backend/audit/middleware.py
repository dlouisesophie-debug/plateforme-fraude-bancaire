"""
Middleware d'audit automatique — journalise les requêtes d'écriture sur
l'API (POST, PUT, PATCH, DELETE) des utilisateurs authentifiés.

Les routes /api/auth/ sont exclues : la connexion (réussie ou échouée) et
la gestion des utilisateurs sont journalisées explicitement, avec plus de
détails, dans authentication/views.py (actions LOGIN_SUCCESS,
LOGIN_FAILED, USER_CREATED, USER_UPDATED, USER_DELETED).
"""

from django.utils.deprecation import MiddlewareMixin

from .utils import get_client_ip


class AuditLogMiddleware(MiddlewareMixin):
    SENSITIVE_METHODS = ("POST", "PUT", "PATCH", "DELETE")
    EXCLUDED_PREFIXES = ("/api/auth/",)

    def process_response(self, request, response):
        if (
            request.path.startswith("/api/")
            and not request.path.startswith(self.EXCLUDED_PREFIXES)
            and request.method in self.SENSITIVE_METHODS
        ):
            if getattr(request, "user", None) and request.user.is_authenticated:
                from .models import AuditLog

                AuditLog.objects.create(
                    user=request.user,
                    action=f"{request.method} {request.path}",
                    ip_address=get_client_ip(request),
                    details={"status_code": response.status_code},
                )
        return response
