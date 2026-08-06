"""
App authentication — gere les utilisateurs et les roles (CDC 5.1).
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Etend le modele utilisateur natif de Django (login, mot de passe hashe,
    permissions Django deja geres par AbstractUser) et ajoute le role metier.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrateur"
        ANALYST = "analyst", "Analyste Fraude"
        AGENT = "agent", "Agent Financier"

    role = models.CharField(max_length=20, choices=Role.choices)

    class Meta:
        db_table = "users"
        indexes = [models.Index(fields=["role"])]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"
