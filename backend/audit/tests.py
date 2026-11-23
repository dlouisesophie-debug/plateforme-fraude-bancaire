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

    def test_lecture_de_liste_non_journalisee(self):
        self.client.force_authenticate(User.objects.create_user(username="ag", password="x", role="agent"))
        self.client.get("/api/transactions/")
        self.client.get("/api/dashboard/stats/")
        self.assertFalse(AuditLog.objects.exists())

    def test_fiche_transaction_et_export_journalises(self):
        from datetime import datetime, timezone
        from transactions.models import Transaction
        t = Transaction.objects.create(
            transaction_id="T-AUDIT", amount=10_000, channel="card",
            timestamp=datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc),
        )
        analyste = User.objects.create_user(username="an", password="x", role="analyst")
        self.client.force_authenticate(analyste)
        self.assertEqual(self.client.get(f"/api/transactions/{t.id}/").status_code, 200)
        self.assertEqual(self.client.get("/api/transactions/export/", {"status": "fraudulent"}).status_code, 200)

        fiche = AuditLog.objects.get(action=f"GET /api/transactions/{t.id}/")
        self.assertEqual(fiche.user, analyste)
        export = AuditLog.objects.get(action="GET /api/transactions/export/")
        self.assertEqual(export.details["query"], {"status": "fraudulent"})

    def test_consultation_reservee_admin_et_filtrable(self):
        admin = User.objects.create_user(username="ad", password="x", role="admin")
        AuditLog.objects.create(user=admin, action="LOGIN_SUCCESS")
        AuditLog.objects.create(user=None, action="LOGIN_FAILED")
        self.client.force_authenticate(User.objects.create_user(username="an", password="x", role="analyst"))
        self.assertEqual(self.client.get("/api/audit/").status_code, 403)
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.get("/api/audit/", {"action": "LOGIN_FAILED"}).json()["count"], 1)
