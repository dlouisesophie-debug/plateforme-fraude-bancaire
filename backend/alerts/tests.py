"""
Tests de l'API alertes : permissions et repercussion de la decision de
l'analyste sur le statut de la transaction.

    python manage.py test --settings=fraudguard.settings_test
"""

from datetime import datetime, timezone

from rest_framework.test import APITestCase

from authentication.models import User
from fraud_detection.models import MLModel, Prediction
from transactions.models import Transaction

from .models import Alert

URL = "/api/alerts/"


class AlertAPITests(APITestCase):
    def setUp(self):
        modele = MLModel.objects.create(
            version="t", algorithm="xgboost", is_active=True,
            trained_at=datetime.now(timezone.utc), artifact_path="x",
        )
        self.transaction = Transaction.objects.create(
            transaction_id="T-ALERTE-1", amount=100, merchant="m", device="d",
            location="l", channel="online", timestamp=datetime.now(timezone.utc),
            status=Transaction.Status.UNDER_REVIEW,
        )
        prediction = Prediction.objects.create(
            transaction=self.transaction, ml_model=modele, fraud_probability=0.9, prediction=True,
        )
        self.alert = Alert.objects.create(prediction=prediction)
        self.analyste = User.objects.create_user(username="ana", password="x", role="analyst")

    def test_agent_ne_peut_pas_acceder_aux_alertes(self):
        agent = User.objects.create_user(username="ag", password="x", role="agent")
        self.client.force_authenticate(agent)
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_superuser_sans_role_accede_aux_alertes(self):
        su = User.objects.create_superuser(username="su", password="x")
        self.client.force_authenticate(su)
        self.assertEqual(self.client.get(URL).status_code, 200)

    def test_confirm_marque_la_transaction_frauduleuse(self):
        self.client.force_authenticate(self.analyste)
        reponse = self.client.post(f"{URL}{self.alert.id}/confirm/")
        self.assertEqual(reponse.status_code, 200)
        self.alert.refresh_from_db()
        self.transaction.refresh_from_db()
        self.assertEqual(self.alert.status, Alert.Status.CONFIRMED)
        self.assertIsNotNone(self.alert.resolved_at)
        self.assertEqual(self.transaction.status, Transaction.Status.FRAUDULENT)

    def test_reject_marque_la_transaction_legitime(self):
        self.client.force_authenticate(self.analyste)
        reponse = self.client.post(f"{URL}{self.alert.id}/reject/")
        self.assertEqual(reponse.status_code, 200)
        self.alert.refresh_from_db()
        self.transaction.refresh_from_db()
        self.assertEqual(self.alert.status, Alert.Status.REJECTED)
        self.assertIsNotNone(self.alert.resolved_at)
        self.assertEqual(self.transaction.status, Transaction.Status.LEGITIMATE)

    def test_patch_statut_repercute_aussi_sur_la_transaction(self):
        self.client.force_authenticate(self.analyste)
        self.client.patch(f"{URL}{self.alert.id}/", {"status": "confirmed"}, format="json")
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, Transaction.Status.FRAUDULENT)
