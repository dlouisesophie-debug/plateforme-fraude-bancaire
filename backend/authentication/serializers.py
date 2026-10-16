from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "is_active"]
        read_only_fields = ["id"]


class UserCreateSerializer(serializers.ModelSerializer):
    """Inscription réservée à l'admin (CDC 5.1 : inscription par admin uniquement)."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "password"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class MeSerializer(serializers.ModelSerializer):
    """Profil de l'utilisateur connecté (GET /api/auth/me/)."""

    role_label = serializers.CharField(source="get_role_display", read_only=True)
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "full_name",
            "role", "role_label", "is_superuser", "last_login",
        ]
        read_only_fields = fields


class FraudGuardTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Login JWT : ajoute le nom et le rôle dans le token (claims) et renvoie
    le profil avec la réponse, pour que le frontend adapte le menu au rôle
    dès la connexion sans requête supplémentaire.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["role"] = "admin" if user.is_superuser and not user.role else user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = MeSerializer(self.user).data
        return data
