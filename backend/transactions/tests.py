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
