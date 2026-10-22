"""
Tests de l'API transactions, dont le declenchement du scoring ML.

    python manage.py test --settings=fraudguard.settings_test
"""

from unittest import skipUnless
from rest_framework.test import APITestCase

from alerts.models import Alert
from authentication.models import User
from fraud_detection.models import Prediction
from fraud_detection.sample_transactions import TRANSACTION_FRAUDE, TRANSACTION_NORMALE
from fraud_detection.tests import PIPELINE_PRESENT, activer_modele

from .models import Transaction

URL = "/api/transactions/"


class TransactionAPITests(APITestCase):
    def setUp(self):
        self.agent = User.objects.create_user(username="agent1", password="x", role="agent")
        self.client.force_authenticate(self.agent)

    def test_acces_refuse_sans_authentification(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(URL).status_code, 401)

    def test_creation_sans_modele_actif_reste_pending_et_est_loguee(self):
        with self.assertLogs("transactions.views", level="WARNING") as logs:
            reponse = self.client.post(URL, TRANSACTION_NORMALE, format="json")
        self.assertEqual(reponse.status_code, 201)
        t = Transaction.objects.get(transaction_id=TRANSACTION_NORMALE["transaction_id"])
        self.assertEqual(t.status, Transaction.Status.PENDING)
        self.assertEqual(t.created_by, self.agent)
        self.assertFalse(Prediction.objects.exists())
        self.assertIn("non scoree", logs.output[0])

    def test_montant_zero_ou_negatif_refuse(self):
        for montant in (0, -50):
            donnees = dict(TRANSACTION_NORMALE, transaction_id=f"T-MONTANT-{montant}", amount=montant)
            reponse = self.client.post(URL, donnees, format="json")
            self.assertEqual(reponse.status_code, 400)
            self.assertIn("amount", reponse.data)
        self.assertFalse(Transaction.objects.exists())

    def test_filtrage_par_statut(self):
        Transaction.objects.create(
            transaction_id="X1", amount=1, channel="card",
            timestamp="2026-10-11T10:00:00Z", status="fraudulent",
        )
        Transaction.objects.create(
            transaction_id="X2", amount=1, channel="card",
            timestamp="2026-10-11T10:00:00Z", status="pending",
        )
        reponse = self.client.get(URL, {"status": "fraudulent"})
        self.assertEqual(reponse.json()["count"], 1)


@skipUnless(PIPELINE_PRESENT, "fraudguard_pipeline.joblib introuvable dans ml/models")
class TransactionScoringAPITests(APITestCase):
    def setUp(self):
        self.client.force_authenticate(User.objects.create_user(username="agent2", password="x", role="agent"))
        activer_modele()

    def test_creation_declenche_le_scoring(self):
        reponse = self.client.post(URL, TRANSACTION_NORMALE, format="json")
        self.assertEqual(reponse.status_code, 201)
        prediction = Prediction.objects.get(transaction__transaction_id=TRANSACTION_NORMALE["transaction_id"])
        self.assertLess(prediction.fraud_probability, 0.01)
        self.assertFalse(prediction.prediction)

    def test_creation_dune_fraude_cree_une_alerte(self):
        reponse = self.client.post(URL, TRANSACTION_FRAUDE, format="json")
        self.assertEqual(reponse.status_code, 201)
        t = Transaction.objects.get(transaction_id=TRANSACTION_FRAUDE["transaction_id"])
        self.assertEqual(t.status, Transaction.Status.UNDER_REVIEW)
        self.assertTrue(Alert.objects.filter(prediction__transaction=t).exists())


class TransactionCorrectionsTests(APITestCase):
    """Permissions par rôle, score dans l'API, filtres, recherche et export CSV."""

    def setUp(self):
        from fraud_detection.testing import activer_faux_modele
        activer_faux_modele()
        self.agent = User.objects.create_user(username="ag", password="x", role="agent")
        self.analyste = User.objects.create_user(username="an", password="x", role="analyst")
        self.admin = User.objects.create_user(username="ad", password="x", role="admin")

    def creer(self, probabilite, **surcharges):
        from fraud_detection.testing import faux_modele
        donnees = dict(TRANSACTION_NORMALE, **surcharges)
        self.client.force_authenticate(self.agent)
        with faux_modele(probabilite):
            reponse = self.client.post(URL, donnees, format="json")
        self.assertEqual(reponse.status_code, 201, reponse.content)
        return reponse

    def test_creation_reservee_agent_et_admin(self):
        from fraud_detection.testing import faux_modele
        self.client.force_authenticate(self.analyste)
        self.assertEqual(self.client.post(URL, TRANSACTION_NORMALE, format="json").status_code, 403)
        self.client.force_authenticate(self.admin)
        with faux_modele(0.01):
            reponse = self.client.post(URL, dict(TRANSACTION_NORMALE, transaction_id="T-ADMIN"), format="json")
        self.assertEqual(reponse.status_code, 201)

    def test_reponse_de_creation_contient_le_score_et_le_statut(self):
        reponse = self.creer(0.02).json()
        self.assertEqual(reponse["status"], "legitimate")
        self.assertEqual(reponse["status_label"], "Légitime")
        self.assertAlmostEqual(reponse["fraud_probability"], 0.02)
        self.assertFalse(reponse["is_fraud_predicted"])
        self.assertIsNone(reponse["alert_id"])

    def test_liste_contient_le_score_et_lalerte(self):
        self.creer(0.97, transaction_id="T-FRAUDE")
        self.client.force_authenticate(self.analyste)
        ligne = self.client.get(URL).json()["results"][0]
        self.assertAlmostEqual(ligne["fraud_probability"], 0.97)
        self.assertTrue(ligne["is_fraud_predicted"])
        self.assertIsNotNone(ligne["alert_id"])
        self.assertEqual(ligne["alert_status"], "open")
        self.assertEqual(ligne["status"], "under_review")

    def test_transaction_non_scoree_a_un_score_nul(self):
        Transaction.objects.create(transaction_id="X", amount=1, channel="card", timestamp="2026-10-11T10:00:00Z")
        self.client.force_authenticate(self.agent)
        ligne = self.client.get(URL).json()["results"][0]
        self.assertIsNone(ligne["fraud_probability"])

    def test_analyste_ne_peut_modifier_que_le_statut(self):
        t_id = self.creer(0.97, transaction_id="T-PATCH").json()["id"]
        self.client.force_authenticate(self.analyste)
        reponse = self.client.patch(f"{URL}{t_id}/", {"amount": "1", "status": "fraudulent"}, format="json")
        self.assertEqual(reponse.status_code, 200)
        t = Transaction.objects.get(pk=t_id)
        self.assertEqual(t.amount, 15000)  # montant inchangé
        self.assertEqual(t.status, Transaction.Status.FRAUDULENT)
        # L'alerte ouverte est clôturée dans le même sens.
        self.assertEqual(Alert.objects.get(prediction__transaction=t).status, Alert.Status.CONFIRMED)

    def test_agent_ne_peut_pas_modifier(self):
        t_id = self.creer(0.01).json()["id"]
        self.assertEqual(self.client.patch(f"{URL}{t_id}/", {"status": "fraudulent"}, format="json").status_code, 403)

    def test_suppression_reservee_a_ladmin(self):
        t_id = self.creer(0.01).json()["id"]
        self.client.force_authenticate(self.analyste)
        self.assertEqual(self.client.delete(f"{URL}{t_id}/").status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(f"{URL}{t_id}/").status_code, 204)

    def test_filtre_par_periode_et_recherche(self):
        self.creer(0.01, transaction_id="T-OCT01", timestamp="2026-10-01T10:00:00Z", merchant="Auchan")
        self.creer(0.01, transaction_id="T-OCT10", timestamp="2026-10-10T10:00:00Z", merchant="Wave")
        self.client.force_authenticate(self.analyste)
        r = self.client.get(URL, {"date_after": "2026-10-05"}).json()
        self.assertEqual([t["transaction_id"] for t in r["results"]], ["T-OCT10"])
        r = self.client.get(URL, {"date_before": "2026-10-05"}).json()
        self.assertEqual([t["transaction_id"] for t in r["results"]], ["T-OCT01"])
        r = self.client.get(URL, {"search": "auchan"}).json()
        self.assertEqual([t["transaction_id"] for t in r["results"]], ["T-OCT01"])

    def test_export_csv(self):
        self.creer(0.97, transaction_id="T-CSV-1")
        self.creer(0.01, transaction_id="T-CSV-2", channel="mobile_money")
        self.client.force_authenticate(self.agent)
        reponse = self.client.get(f"{URL}export/", {"channel": "mobile_money"})
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("text/csv", reponse["Content-Type"])
        self.assertIn("attachment", reponse["Content-Disposition"])
        lignes = reponse.content.decode("utf-8-sig").strip().splitlines()
        self.assertTrue(lignes[0].startswith("ID transaction;"))
        self.assertEqual(len(lignes), 2)  # en-tête + 1 transaction mobile money
        self.assertIn("T-CSV-2", lignes[1])
        self.assertIn("Légitime", lignes[1])
