from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from audit.utils import log_action

from .permissions import IsAdmin
from .serializers import (
    FraudGuardTokenObtainPairSerializer,
    MeSerializer,
    UserCreateSerializer,
    UserSerializer,
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD des utilisateurs — réservé à l'Administrateur (CDC 5.1, 5.5).
    Chaque création, modification et suppression est journalisée (audit).
    """

    queryset = User.objects.all().order_by("username")
    permission_classes = [IsAdmin]
    filterset_fields = ["role", "is_active"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        cible = serializer.save()
        log_action(self.request, "USER_CREATED", details={
            "target_id": cible.id, "target_username": cible.username, "role": cible.role,
        })

    def perform_update(self, serializer):
        avant = {champ: getattr(serializer.instance, champ) for champ in serializer.validated_data}
        cible = serializer.save()
        changements = {
            champ: {"avant": avant[champ], "apres": getattr(cible, champ)}
            for champ in avant
            if avant[champ] != getattr(cible, champ)
        }
        log_action(self.request, "USER_UPDATED", details={
            "target_id": cible.id, "target_username": cible.username, "changes": changements,
        })

    def perform_destroy(self, instance):
        details = {"target_id": instance.id, "target_username": instance.username, "role": instance.role}
        instance.delete()
        log_action(self.request, "USER_DELETED", details=details)


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/ — connexion JWT (access + refresh).

    Historique de connexion (CDC 5.1) : chaque tentative est journalisée,
    LOGIN_SUCCESS avec l'utilisateur, LOGIN_FAILED avec le nom tenté.
    """

    serializer_class = FraudGuardTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        username = request.data.get("username", "")
        reponse = super().post(request, *args, **kwargs)
        # Les identifiants invalides lèvent une exception gérée par DRF :
        # on n'arrive ici qu'en cas de succès.
        utilisateur = User.objects.filter(username=username).first()
        log_action(request, "LOGIN_SUCCESS", user=utilisateur, details={"username": username})
        return reponse

    def handle_exception(self, exc):
        reponse = super().handle_exception(exc)
        if reponse.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED):
            username = self.request.data.get("username", "") if hasattr(self.request, "data") else ""
            log_action(self.request, "LOGIN_FAILED", details={
                "username": username, "status_code": reponse.status_code,
            })
        return reponse


RefreshView = TokenRefreshView


class MeView(APIView):
    """GET /api/auth/me/ — profil et rôle de l'utilisateur connecté."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=MeSerializer)
    def get(self, request):
        return Response(MeSerializer(request.user).data)
