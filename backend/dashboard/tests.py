"""
Tests de GET /api/dashboard/stats/ (CDC 5.4).

    python manage.py test dashboard --settings=fraudguard.settings_test
"""

from datetime import datetime, timezone

from rest_framework.test import APITestCase

from alerts.models import Alert
from authentication.models import User
from fraud_detection.models import Prediction
from fraud_detection.testing import activer_faux_modele
from transactions.models import Transaction

URL = "/api/dashboard/stats/"


class DashboardStatsTests(APITestCase):
    def setUp(self):
        self.modele = activer_faux_modele()
        self.client.force_authenticate(User.objects.create_user(username="ag", password="x", role="agent"))
        # (id, montant, canal, jour, statut final, prédiction du modèle)
        jeu = [
            ("T1", 10_000, "card", 1, "legitimate", False),            # vrai négatif
            ("T2", 20_000, "mobile_money", 1, "legitimate", False),    # vrai négatif
            ("T3", 500_000, "online", 2, "fraudulent", True),          # vrai positif
            ("T4", 300_000, "online", 2, "legitimate", True),          # faux positif (alerte rejetée)
            ("T5", 400_000, "card", 3, "fraudulent", False),           # faux négatif (requalifiée)
            ("T6", 250_000, "transfer", 3, "under_review", True),      # alerte ouverte
            ("T7", 5_000, "card", 3, "pending", None),                 # non scorée
        ]
        for tid, montant, canal, jour, statut, predit in jeu:
            t = Transaction.objects.create(
                transaction_id=tid, amount=montant, channel=canal, status=statut,
                timestamp=datetime(2026, 10, jour, 12, 0, tzinfo=timezone.utc),
            )
            if predit is None:
                continue
            p = Prediction.objects.create(
                transaction=t, ml_model=self.modele, prediction=predit,
                fraud_probability=0.95 if predit else 0.02,
            )
            if predit:
                statut_alerte = {"fraudulent": "confirmed", "legitimate": "rejected"}.get(statut, "open")
                Alert.objects.create(prediction=p, status=statut_alerte, severity="critical")

    def test_acces_refuse_sans_authentification(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(URL).status_code, 401)

    def test_kpis(self):
        kpis = self.client.get(URL).json()["kpis"]
        self.assertEqual(kpis["total_transactions"], 7)
        self.assertEqual(kpis["fraudulent_transactions"], 2)
        self.assertAlmostEqual(kpis["fraud_rate"], 28.57)
        self.assertEqual(kpis["amount_at_risk"], 500_000 + 400_000 + 250_000)
        self.assertEqual(kpis["active_alerts"], 1)

    def test_repartitions(self):
        data = self.client.get(URL).json()
        statuts = {s["status"]: s["count"] for s in data["by_status"]}
        self.assertEqual(statuts, {"pending": 1, "legitimate": 3, "fraudulent": 2, "under_review": 1})
        canaux = {c["channel"]: c for c in data["by_channel"]}
        self.assertEqual(canaux["online"]["total"], 2)
        self.assertEqual(canaux["online"]["fraudulent"], 1)
        self.assertEqual(canaux["card"]["amount"], 415_000)
        self.assertEqual(canaux["mobile_money"]["label"], "Mobile Money")
        jours = {j["date"]: j for j in data["daily"]}
        self.assertEqual(jours["2026-10-02"]["total"], 2)
        self.assertEqual(jours["2026-10-02"]["flagged"], 2)
        self.assertEqual(jours["2026-10-03"]["fraudulent"], 1)

    def test_matrice_de_confusion(self):
        m = self.client.get(URL).json()["confusion_matrix"]
        self.assertEqual(
            (m["true_positive"], m["false_positive"], m["false_negative"], m["true_negative"]),
            (1, 1, 1, 2),
        )
        self.assertEqual(m["evaluated"], 5)
        self.assertEqual(m["precision"], 0.5)
        self.assertEqual(m["recall"], 0.5)

    def test_modele_actif(self):
        modele = self.client.get(URL).json()["active_model"]
        self.assertEqual(modele["version"], "faux-1")
        self.assertEqual(modele["recall"], 0.85)

    def test_filtres_periode_et_canal(self):
        data = self.client.get(URL, {"date_after": "2026-10-02", "date_before": "2026-10-02"}).json()
        self.assertEqual(data["kpis"]["total_transactions"], 2)
        data = self.client.get(URL, {"channel": "card"}).json()
        self.assertEqual(data["kpis"]["total_transactions"], 3)
        self.assertEqual(data["filters"]["channel"], "card")

    def test_parametres_invalides(self):
        self.assertEqual(self.client.get(URL, {"date_after": "16/10/2026"}).status_code, 400)
        self.assertEqual(self.client.get(URL, {"channel": "bitcoin"}).status_code, 400)
        self.assertEqual(
            self.client.get(URL, {"date_after": "2026-10-10", "date_before": "2026-10-01"}).status_code, 400,
        )

    def test_base_vide(self):
        Transaction.objects.all().delete()
        data = self.client.get(URL).json()
        self.assertEqual(data["kpis"]["fraud_rate"], 0.0)
        self.assertIsNone(data["confusion_matrix"]["precision"])
