"""
Tests du scoring ML et de l'enregistrement du modele actif.

    python manage.py test --settings=fraudguard.settings_test

Ils utilisent le VRAI pipeline (ml/models/fraudguard_pipeline.joblib) :
si le fichier est absent, les tests de scoring sont ignores (skip).
"""

import os
from datetime import datetime, timezone
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction as db_transaction
from unittest import skipUnless

from django.test import TestCase
from django.utils.dateparse import parse_date, parse_datetime

from alerts.models import Alert
from transactions.models import Transaction

from . import services
from .models import MLModel, Prediction
from .sample_transactions import TRANSACTION_FRAUDE, TRANSACTION_NORMALE

PIPELINE_FILE = "fraudguard_pipeline.joblib"
PIPELINE_PRESENT = os.path.isfile(os.path.join(settings.ML_MODELS_DIR, PIPELINE_FILE))


def creer_transaction(donnees):
    """Cree une Transaction a partir d'un exemple (memes cles que l'API)."""
    d = dict(donnees)
    d["amount"] = d["amount"]
    d["timestamp"] = parse_datetime(d["timestamp"])
    d["customer_birth_date"] = parse_date(d["customer_birth_date"])
    return Transaction.objects.create(**d)


def activer_modele(version="test-1"):
    return MLModel.objects.create(
        version=version, algorithm="xgboost", trained_at=datetime.now(timezone.utc),
        is_active=True, artifact_path=PIPELINE_FILE,
    )


@skipUnless(PIPELINE_PRESENT, "fraudguard_pipeline.joblib introuvable dans ml/models")
class ScoringTests(TestCase):
    def setUp(self):
        self.modele = activer_modele()

    def test_transaction_normale_non_flaggee(self):
        t = creer_transaction(TRANSACTION_NORMALE)
        prediction = services.score_transaction(t)
        self.assertLess(prediction.fraud_probability, 0.01)
        self.assertFalse(prediction.prediction)
        self.assertFalse(Alert.objects.exists())
        t.refresh_from_db()
        self.assertEqual(t.status, Transaction.Status.PENDING)

    def test_transaction_frauduleuse_declenche_alerte(self):
        """Vraie fraude (score du modele, pas de valeur forcee)."""
        t = creer_transaction(TRANSACTION_FRAUDE)
        prediction = services.score_transaction(t)
        self.assertTrue(prediction.prediction)
        self.assertGreaterEqual(prediction.fraud_probability, 0.9)
        alerte = Alert.objects.get(prediction=prediction)
        self.assertEqual(alerte.severity, "critical")
        t.refresh_from_db()
        self.assertEqual(t.status, Transaction.Status.UNDER_REVIEW)

    def test_rescoring_sans_doublon(self):
        t = creer_transaction(TRANSACTION_FRAUDE)
        services.score_transaction(t)
        services.score_transaction(t)  # ne doit pas lever d'IntegrityError
        self.assertEqual(Prediction.objects.filter(transaction=t).count(), 1)
        self.assertEqual(Alert.objects.filter(prediction__transaction=t).count(), 1)

    def test_categorie_inconnue_est_signalee_dans_les_logs(self):
        donnees = dict(TRANSACTION_NORMALE, transaction_id="T-CAT-INCONNUE", category="shopping_net")
        t = creer_transaction(donnees)
        with self.assertLogs("fraud_detection.services", level="WARNING") as logs:
            services.score_transaction(t)
        self.assertIn("shopping_net", logs.output[0])


class ServicesSansPipelineTests(TestCase):
    def test_sans_modele_actif_leve_runtime_error(self):
        t = creer_transaction(TRANSACTION_NORMALE)
        with self.assertRaises(RuntimeError):
            services.score_transaction(t)

    def test_gravite_selon_la_probabilite(self):
        self.assertEqual(services._gravite(0.95), "critical")
        self.assertEqual(services._gravite(0.80), "high")
        self.assertEqual(services._gravite(0.60), "medium")
        self.assertEqual(services._gravite(0.20), "low")


class MLModelTests(TestCase):
    def test_un_seul_modele_actif_a_la_fois(self):
        activer_modele("v-a")
        with self.assertRaises(IntegrityError), db_transaction.atomic():
            activer_modele("v-b")


@skipUnless(PIPELINE_PRESENT, "fraudguard_pipeline.joblib introuvable dans ml/models")
class CommandeActiverModeleTests(TestCase):
    def lancer(self, *args):
        call_command("activer_modele_ml", PIPELINE_FILE, *args, stdout=StringIO())

    def test_cree_et_active_le_modele(self):
        self.lancer("--modele-version", "1", "--algorithm", "xgboost")
        modele = MLModel.objects.get(is_active=True)
        self.assertEqual(modele.version, "1")
        self.assertEqual(modele.artifact_path, PIPELINE_FILE)

    def test_nouvelle_version_desactive_lancienne(self):
        self.lancer("--modele-version", "1")
        self.lancer("--modele-version", "2")
        self.assertEqual(MLModel.objects.filter(is_active=True).count(), 1)
        self.assertEqual(MLModel.objects.get(is_active=True).version, "2")

    def test_fichier_introuvable(self):
        with self.assertRaises(CommandError):
            call_command("activer_modele_ml", "inexistant.joblib", stdout=StringIO())
        self.assertFalse(MLModel.objects.exists())
