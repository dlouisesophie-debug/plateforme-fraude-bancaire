"""
Outils d'audit réutilisables (CDC §5.1 historique de connexion, §6 logs
d'audit des accès aux données sensibles).
"""

from .models import AuditLog


def get_client_ip(request):
    """Adresse IP du client, en tenant compte d'un proxy (Render, nginx)."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_action(request, action, user=None, details=None):
    """
    Enregistre un événement métier dans le journal d'audit.

    `user` est facultatif : pour une connexion échouée, il n'y a pas
    d'utilisateur authentifié (le nom tenté est alors mis dans `details`).
    """
    if user is None:
        candidat = getattr(request, "user", None)
        if candidat is not None and candidat.is_authenticated:
            user = candidat
    return AuditLog.objects.create(
        user=user,
        action=action,
        ip_address=get_client_ip(request),
        details=details or {},
    )
