"""
Tests du journal d'audit (CDC §6).

    python manage.py test audit --settings=fraudguard.settings_test
"""

from rest_framework.test import APITestCase

from authentication.models import User

from .models import AuditLog


class AuditMiddlewareTests(APITestCase):
    def test_ecriture_api_journalisee_avec_ip(self):
        admin = User.objects.create_user(username="ad", password="x", role="admin")
        self.client.force_authenticate(admin)
        self.client.post("/api/reports/", {"title": "t", "type": "csv"}, format="json",
                         HTTP_X_FORWARDED_FOR="41.82.10.5, 10.0.0.1")
        log = AuditLog.objects.get(action="POST /api/reports/")
        self.assertEqual(log.user, admin)
        self.assertEqual(log.ip_address, "41.82.10.5")
        self.assertEqual(log.details["status_code"], 201)

    def test_lecture_non_journalisee(self):
        self.client.force_authenticate(User.objects.create_user(username="ag", password="x", role="agent"))
        self.client.get("/api/transactions/")
        self.assertFalse(AuditLog.objects.exists())

    def test_consultation_reservee_admin_et_filtrable(self):
        admin = User.objects.create_user(username="ad", password="x", role="admin")
        AuditLog.objects.create(user=admin, action="LOGIN_SUCCESS")
        AuditLog.objects.create(user=None, action="LOGIN_FAILED")
        self.client.force_authenticate(User.objects.create_user(username="an", password="x", role="analyst"))
        self.assertEqual(self.client.get("/api/audit/").status_code, 403)
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.get("/api/audit/", {"action": "LOGIN_FAILED"}).json()["count"], 1)
