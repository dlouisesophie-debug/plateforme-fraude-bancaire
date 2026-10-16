"""
Permissions par role — CDC 5.1 : "Gestion des roles (permissions DRF
differenciees par endpoint)".
"""

from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Admin metier (role="admin") ou superutilisateur Django."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.role == "admin")
        )


class IsAnalyst(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "analyst")


class IsAgent(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "agent")


class IsAdminOrAnalyst(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.role in ("admin", "analyst"))
        )
