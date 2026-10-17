"""
Tests des rapports PDF/CSV (CDC 5.5).

    python manage.py test reports --settings=fraudguard.settings_test
"""

from pathlib import Path

from django.conf import settings
from rest_framework.test import APITestCase

from authentication.models import User
from transactions.models import Transaction

from .models import Report

URL = "/api/reports/"


class ReportTests(APITestCase):
    def setUp(self):
        self.agent = User.objects.create_user(username="ag", password="x", role="agent")
        self.admin = User.objects.create_user(username="ad", password="x", role="admin")
        Transaction.objects.create(transaction_id="R1", amount=12_500, channel="card",
                                   timestamp="2026-10-05T10:00:00Z", status="legitimate")
        Transaction.objects.create(transaction_id="R2", amount=600_000, channel="online",
                                   timestamp="2026-10-20T23:00:00Z", status="fraudulent")

    def creer(self, type_, **periode):
        self.client.force_authenticate(self.agent)
        reponse = self.client.post(URL, {"title": "Rapport octobre", "type": type_, **periode}, format="json")
        self.assertEqual(reponse.status_code, 201, reponse.content)
        return reponse.json()

    def test_rapport_csv_genere_et_telechargeable(self):
        data = self.creer("csv", period_start="2026-10-01", period_end="2026-10-10")
        self.assertTrue(data["file_path"].endswith(".csv"))
        self.assertTrue((Path(settings.MEDIA_ROOT) / data["file_path"]).is_file())
        reponse = self.client.get(data["download_url"])
        self.assertEqual(reponse.status_code, 200)
        contenu = b"".join(reponse.streaming_content).decode("utf-8-sig")
        self.assertIn("R1", contenu)
        self.assertNotIn("R2", contenu)  # hors période

    def test_rapport_pdf_genere(self):
        data = self.creer("pdf")
        chemin = Path(settings.MEDIA_ROOT) / data["file_path"]
        self.assertTrue(chemin.read_bytes().startswith(b"%PDF"))

    def test_periode_invalide(self):
        self.client.force_authenticate(self.agent)
        reponse = self.client.post(URL, {"title": "x", "type": "csv", "period_start": "2026-10-10",
                                         "period_end": "2026-10-01"}, format="json")
        self.assertEqual(reponse.status_code, 400)

    def test_chacun_voit_ses_rapports_admin_voit_tout(self):
        self.creer("csv")
        autre = User.objects.create_user(username="ag2", password="x", role="agent")
        self.client.force_authenticate(autre)
        self.assertEqual(self.client.get(URL).json()["count"], 0)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(URL).json()["count"], 1)

    def test_suppression_reservee_a_ladmin_et_supprime_le_fichier(self):
        data = self.creer("csv")
        chemin = Path(settings.MEDIA_ROOT) / data["file_path"]
        self.assertEqual(self.client.delete(f"{URL}{data['id']}/").status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(f"{URL}{data['id']}/").status_code, 204)
        self.assertFalse(chemin.exists())
        self.assertFalse(Report.objects.exists())

    def test_pas_de_modification(self):
        data = self.creer("csv")
        self.assertEqual(self.client.patch(f"{URL}{data['id']}/", {"title": "y"}, format="json").status_code, 405)
