from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .permissions import IsAdmin
from .serializers import UserCreateSerializer, UserSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD des utilisateurs — reserve a l'Administrateur (CDC 5.1, 5.5).
    TODO Etudiant 1 : brancher AuditLog sur create/update/delete (voir app audit).
    """

    queryset = User.objects.all()
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer


# Reexport pour urls.py — Simple JWT fournit deja les vues de login/refresh
LoginView = TokenObtainPairView
RefreshView = TokenRefreshView
