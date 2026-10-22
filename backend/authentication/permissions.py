"""
Permissions par rôle — CDC 5.1 : "Gestion des rôles (permissions DRF
différenciées par endpoint)".

Le superutilisateur Django est toujours traité comme un administrateur.
"""

from rest_framework.permissions import BasePermission


def _role(user):
    return getattr(user, "role", None)


def _is_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or _role(user) == "admin"))


class IsAdmin(BasePermission):
    """Admin métier (role="admin") ou superutilisateur Django."""

    def has_permission(self, request, view):
        return _is_admin(request.user)


class IsAnalyst(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and _role(request.user) == "analyst")


class IsAgent(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and _role(request.user) == "agent")


class IsAdminOrAnalyst(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return _is_admin(user) or bool(user and user.is_authenticated and _role(user) == "analyst")


class IsAdminOrAgent(BasePermission):
    """Saisie des transactions : Agent Financier ou Administrateur (CDC §4)."""

    def has_permission(self, request, view):
        user = request.user
        return _is_admin(user) or bool(user and user.is_authenticated and _role(user) == "agent")
