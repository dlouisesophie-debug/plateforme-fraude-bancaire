"""
Middleware d'audit automatique — journalise, pour les utilisateurs authentifiés :

- les requêtes d'écriture sur l'API (POST, PUT, PATCH, DELETE) ;
- les lectures sensibles : la fiche d'une transaction (données personnelles du
  client : date de naissance, profession, coordonnées GPS), l'export CSV et le
  téléchargement d'un rapport (données qui sortent de la plateforme).

Les autres lectures (listes, tableau de bord, actualisées en continu) ne sont
pas journalisées : elles noieraient le journal sans apporter de traçabilité.

Les routes /api/auth/ sont exclues : la connexion (réussie ou échouée) et
la gestion des utilisateurs sont journalisées explicitement, avec plus de
détails, dans authentication/views.py (actions LOGIN_SUCCESS,
LOGIN_FAILED, USER_CREATED, USER_UPDATED, USER_DELETED).
"""

import re

from django.utils.deprecation import MiddlewareMixin

from .utils import get_client_ip


class AuditLogMiddleware(MiddlewareMixin):
    SENSITIVE_METHODS = ("POST", "PUT", "PATCH", "DELETE")
    EXCLUDED_PREFIXES = ("/api/auth/",)
    AUDITED_READS = (
        re.compile(r"^/api/transactions/\d+/$"),       # fiche transaction
        re.compile(r"^/api/transactions/export/$"),    # export CSV
        re.compile(r"^/api/reports/\d+/download/$"),   # téléchargement d'un rapport
    )

    def _a_journaliser(self, request):
        if not request.path.startswith("/api/") or request.path.startswith(self.EXCLUDED_PREFIXES):
            return False
        if request.method in self.SENSITIVE_METHODS:
            return True
        return request.method == "GET" and any(motif.match(request.path) for motif in self.AUDITED_READS)

    def process_response(self, request, response):
        if self._a_journaliser(request):
            if getattr(request, "user", None) and request.user.is_authenticated:
                from .models import AuditLog

                details = {"status_code": response.status_code}
                if request.method == "GET" and request.GET:
                    # Filtres de l'export : savoir QUELLES données sont sorties.
                    details["query"] = request.GET.dict()
                AuditLog.objects.create(
                    user=request.user,
                    action=f"{request.method} {request.path}",
                    ip_address=get_client_ip(request),
                    details=details,
                )
        return response
