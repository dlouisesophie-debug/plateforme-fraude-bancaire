"""
Tests authentification : login JWT (avec rôle), /me, gestion des
utilisateurs réservée à l'admin, et journal d'audit (CDC 5.1).

    python manage.py test authentication --settings=fraudguard.settings_test
"""

from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from audit.models import AuditLog

from .models import User


class LoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="awa", password="MotDePasse!2026", role="analyst",
                                             first_name="Awa")

    def test_login_reussi_renvoie_tokens_role_et_journalise(self):
        reponse = self.client.post("/api/auth/login/", {"username": "awa", "password": "MotDePasse!2026"},
                                   format="json")
        self.assertEqual(reponse.status_code, 200)
        data = reponse.json()
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertEqual(data["user"]["role"], "analyst")
        self.assertEqual(data["user"]["role_label"], "Analyste Fraude")
        self.assertEqual(AccessToken(data["access"])["role"], "analyst")
        log = AuditLog.objects.get(action="LOGIN_SUCCESS")
        self.assertEqual(log.user, self.user)

    def test_login_echoue_est_journalise(self):
        reponse = self.client.post("/api/auth/login/", {"username": "awa", "password": "faux"}, format="json")
        self.assertEqual(reponse.status_code, 401)
        log = AuditLog.objects.get(action="LOGIN_FAILED")
        self.assertIsNone(log.user)
        self.assertEqual(log.details["username"], "awa")
        self.assertFalse(AuditLog.objects.filter(action="LOGIN_SUCCESS").exists())

    def test_refresh(self):
        refresh = self.client.post("/api/auth/login/", {"username": "awa", "password": "MotDePasse!2026"},
                                   format="json").json()["refresh"]
        reponse = self.client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("access", reponse.json())


class MeTests(APITestCase):
    def test_me_renvoie_le_profil(self):
        user = User.objects.create_user(username="moussa", password="x", role="agent")
        self.client.force_authenticate(user)
        data = self.client.get("/api/auth/me/").json()
        self.assertEqual(data["username"], "moussa")
        self.assertEqual(data["role"], "agent")
        self.assertEqual(data["role_label"], "Agent Financier")

    def test_me_sans_authentification(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)


class GestionUtilisateursTests(APITestCase):
    URL = "/api/auth/users/"

    def setUp(self):
        self.admin = User.objects.create_user(username="chef", password="x", role="admin")

    def test_non_admin_refuse(self):
        for role in ("analyst", "agent"):
            self.client.force_authenticate(User.objects.create_user(username=role, password="x", role=role))
            self.assertEqual(self.client.get(self.URL).status_code, 403)

    def test_crud_journalise(self):
        self.client.force_authenticate(self.admin)
        reponse = self.client.post(self.URL, {
            "username": "fatou", "password": "UnMotDePasse!1", "role": "agent", "email": "f@x.sn",
        }, format="json")
        self.assertEqual(reponse.status_code, 201)
        cible = User.objects.get(username="fatou")
        self.assertTrue(cible.check_password("UnMotDePasse!1"))

        self.client.patch(f"{self.URL}{cible.id}/", {"role": "analyst"}, format="json")
        self.client.delete(f"{self.URL}{cible.id}/")

        actions = list(AuditLog.objects.order_by("id").values_list("action", flat=True))
        self.assertEqual(actions, ["USER_CREATED", "USER_UPDATED", "USER_DELETED"])
        maj = AuditLog.objects.get(action="USER_UPDATED")
        self.assertEqual(maj.details["changes"]["role"], {"avant": "agent", "apres": "analyst"})
        self.assertEqual(maj.user, self.admin)
