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
from authentication.models import User
from transactions.models import Transaction

from . import services
from .models import MLModel, Prediction
from .sample_transactions import (
    TRANSACTION_FRAUDE, TRANSACTION_MM_FRAUDE, TRANSACTION_MM_NORMALE, TRANSACTION_NORMALE,
)

PIPELINE_FILE = "fraudguard_pipeline.joblib"
PIPELINE_PRESENT = os.path.isfile(os.path.join(settings.ML_MODELS_DIR, PIPELINE_FILE))
PIPELINE_MM_FILE = "fraudguard_mobile_money_pipeline.joblib"
PIPELINE_MM_PRESENT = os.path.isfile(os.path.join(settings.ML_MODELS_DIR, PIPELINE_MM_FILE))


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
        self.assertEqual(t.status, Transaction.Status.LEGITIMATE)

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

    def test_date_d_entrainement_lue_dans_le_fichier(self):
        # « Entraîné le » : la date écrite par l'entraînement, pas celle de l'activation
        # (au démarrage d'un conteneur Docker, la commande est relancée).
        from predict import load_pipeline

        pipeline = load_pipeline(os.path.join(settings.ML_MODELS_DIR, PIPELINE_FILE))
        attendue = datetime.fromisoformat(pipeline["metriques"]["date_entrainement"])
        self.lancer("--modele-version", "1")
        self.lancer("--modele-version", "1")  # réactivation : la date ne bouge pas
        self.assertEqual(MLModel.objects.get(version="1").trained_at, attendue)

    def test_sans_date_dans_le_fichier_date_d_activation(self):
        import tempfile

        import joblib

        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "sans_date.joblib")
            joblib.dump({"famille": "carte"}, chemin)
            avant = datetime.now(timezone.utc)
            sortie = StringIO()
            call_command("activer_modele_ml", chemin, "--modele-version", "sans-date", stdout=sortie)
        self.assertGreaterEqual(MLModel.objects.get(version="sans-date").trained_at, avant)
        self.assertIn("absente du fichier", sortie.getvalue())


class PermissionsAdminTests(TestCase):
    """IsAdmin accepte le role admin ET le superuser ; refuse les autres."""

    def test_modeles_ml_reserves_a_ladmin(self):
        from rest_framework.test import APIClient
        cas = {
            "admin": User.objects.create_user(username="a", password="x", role="admin"),
            "superuser": User.objects.create_superuser(username="s", password="x"),
            "analyst": User.objects.create_user(username="n", password="x", role="analyst"),
            "agent": User.objects.create_user(username="g", password="x", role="agent"),
        }
        attendu = {"admin": 200, "superuser": 200, "analyst": 403, "agent": 403}
        for nom, utilisateur in cas.items():
            client = APIClient()
            client.force_authenticate(utilisateur)
            for url in ("/api/fraud-detection/models/", "/api/audit/"):
                self.assertEqual(client.get(url).status_code, attendu[nom], f"{nom} {url}")


class ScoringAvecFauxModeleTests(TestCase):
    """Logique de statut après scoring, testée sans le fichier .joblib."""

    def setUp(self):
        from .testing import activer_faux_modele
        activer_faux_modele()

    def test_score_sous_le_seuil_passe_la_transaction_en_legitime(self):
        from .testing import faux_modele
        t = creer_transaction(TRANSACTION_NORMALE)
        with faux_modele(0.02):
            prediction = services.score_transaction(t)
        t.refresh_from_db()
        self.assertFalse(prediction.prediction)
        self.assertEqual(t.status, Transaction.Status.LEGITIMATE)
        self.assertFalse(Alert.objects.exists())

    def test_score_au_dessus_du_seuil_met_en_examen_et_cree_une_alerte(self):
        from .testing import faux_modele
        t = creer_transaction(TRANSACTION_FRAUDE)
        with faux_modele(0.95):
            prediction = services.score_transaction(t)
        t.refresh_from_db()
        self.assertTrue(prediction.prediction)
        self.assertEqual(t.status, Transaction.Status.UNDER_REVIEW)
        self.assertEqual(Alert.objects.get(prediction=prediction).severity, "critical")


class SeedDemoTests(TestCase):
    def test_sans_modele_actif_la_commande_echoue(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", "--nombre", "3", stdout=StringIO())

    def test_cree_les_comptes_et_des_transactions_scorees(self):
        from .testing import activer_faux_modele, faux_modele
        activer_faux_modele()
        # Le faux modèle signale les montants >= 250 000 FCFA.
        with faux_modele(lambda t: 0.97 if t["montant_fcfa"] >= 250_000 else 0.01):
            call_command("seed_demo", "--nombre", "20", "--simuler-decisions", stdout=StringIO())
        self.assertEqual(Transaction.objects.filter(transaction_id__startswith="DEMO-").count(), 20)
        self.assertEqual(
            set(User.objects.filter(username__endswith=".demo").values_list("role", flat=True)),
            {"admin", "analyst", "agent"},
        )
        self.assertFalse(Transaction.objects.filter(status=Transaction.Status.PENDING).exists())
        self.assertEqual(Prediction.objects.count(), 20)
        self.assertTrue(Alert.objects.exists())

    def test_reset_repart_de_zero(self):
        from .testing import activer_faux_modele, faux_modele
        activer_faux_modele()
        with faux_modele(0.01):
            call_command("seed_demo", "--nombre", "5", stdout=StringIO())
            call_command("seed_demo", "--nombre", "5", "--reset", stdout=StringIO())
        self.assertEqual(Transaction.objects.filter(transaction_id__startswith="DEMO-").count(), 5)


class ModeleParFamilleTests(TestCase):
    """Mobile money : un modèle actif par famille, et choix du modèle selon le canal."""

    def setUp(self):
        from .testing import activer_faux_modele
        self.carte = activer_faux_modele("carte-1")
        self.mm = MLModel.objects.create(
            version="mm-1", famille=MLModel.Famille.MOBILE_MONEY, algorithm="xgboost",
            trained_at=datetime.now(timezone.utc), is_active=True, artifact_path="faux-mm.joblib",
        )

    def mobile_money(self, operation_type="transfer"):
        return creer_transaction(dict(
            TRANSACTION_NORMALE, transaction_id="MM-1", channel="mobile_money",
            operation_type=operation_type, amount=250000, timestamp="2026-10-11T23:30:00Z",
        ))

    def scorer(self, transaction, probabilite=0.97):
        """Score avec le faux modèle et renvoie (prédiction, variables reçues par le modèle)."""
        from .testing import faux_modele
        recues = []
        with faux_modele(lambda d: recues.append(d) or probabilite):
            prediction = services.score_transaction(transaction)
        return prediction, recues

    def test_un_modele_actif_par_famille(self):
        self.assertEqual(MLModel.objects.filter(is_active=True).count(), 2)
        with self.assertRaises(IntegrityError), db_transaction.atomic():
            MLModel.objects.create(
                version="mm-2", famille=MLModel.Famille.MOBILE_MONEY, algorithm="xgboost",
                trained_at=datetime.now(timezone.utc), is_active=True, artifact_path="autre.joblib",
            )

    def test_mobile_money_avec_type_utilise_le_modele_mobile_money(self):
        prediction, recues = self.scorer(self.mobile_money())
        self.assertEqual(prediction.ml_model, self.mm)
        # Contrat de données : type PaySim, montant tel que saisi, heure locale (Dakar = UTC+0).
        self.assertEqual(recues, [{"type": "TRANSFER", "montant": 250000.0, "heure": 23}])
        self.assertTrue(prediction.prediction)
        self.assertTrue(Alert.objects.filter(prediction=prediction).exists())

    def test_mobile_money_sans_type_reste_sur_le_modele_carte(self):
        prediction, recues = self.scorer(self.mobile_money(operation_type=""))
        self.assertEqual(prediction.ml_model, self.carte)
        self.assertIn("categorie", recues[0])

    def test_sans_modele_mobile_money_actif_retour_au_modele_carte(self):
        self.mm.is_active = False
        self.mm.save()
        prediction, _ = self.scorer(self.mobile_money())
        self.assertEqual(prediction.ml_model, self.carte)

    def test_carte_utilise_le_modele_carte(self):
        prediction, _ = self.scorer(creer_transaction(TRANSACTION_NORMALE), probabilite=0.01)
        self.assertEqual(prediction.ml_model, self.carte)
        self.assertFalse(prediction.prediction)

    def test_saisie_api_du_type_doperation(self):
        from rest_framework.test import APIClient
        from .testing import faux_modele
        client = APIClient()
        client.force_authenticate(User.objects.create_user(username="ag", password="x", role="agent"))
        donnees = dict(TRANSACTION_NORMALE, transaction_id="MM-API", channel="mobile_money", operation_type="cash_out")
        with faux_modele(0.01):
            reponse = client.post("/api/transactions/", donnees, format="json")
        self.assertEqual(reponse.status_code, 201, reponse.content)
        self.assertEqual(reponse.json()["operation_type"], "cash_out")
        self.assertEqual(reponse.json()["operation_type_label"], "Retrait")
        self.assertEqual(reponse.json()["model_version"], "mm-1")

        # Le type d'opération n'a pas de sens pour un autre canal.
        refus = client.post("/api/transactions/", dict(donnees, transaction_id="CARTE-API", channel="card"),
                            format="json")
        self.assertEqual(refus.status_code, 400)
        self.assertIn("operation_type", refus.json())


@skipUnless(PIPELINE_PRESENT, "fraudguard_pipeline.joblib introuvable dans ml/models")
class CommandeActiverParFamilleTests(TestCase):
    def lancer(self, *args):
        call_command("activer_modele_ml", PIPELINE_FILE, *args, stdout=StringIO())

    def test_famille_lue_dans_le_fichier_carte(self):
        self.lancer("--modele-version", "1")  # fichier carte : pas de clé « famille »
        self.assertEqual(MLModel.objects.get(version="1").famille, MLModel.Famille.CARTE)

    def test_activer_un_modele_mobile_money_garde_le_modele_carte(self):
        self.lancer("--modele-version", "1")
        self.lancer("--modele-version", "mm-1", "--famille", "mobile_money")
        actifs = dict(MLModel.objects.filter(is_active=True).values_list("famille", "version"))
        self.assertEqual(actifs, {"carte": "1", "mobile_money": "mm-1"})


@skipUnless(PIPELINE_PRESENT and PIPELINE_MM_PRESENT, "pipelines carte et mobile money requis dans ml/models")
class ScoringMobileMoneyReelTests(TestCase):
    """Scoring avec le VRAI modèle mobile money (PaySim), à côté du vrai modèle carte."""

    def setUp(self):
        call_command("activer_modele_ml", PIPELINE_FILE, "--modele-version", "carte-1", stdout=StringIO())
        # Famille lue dans le fichier (clé « famille » = mobile_money), sans --famille.
        call_command("activer_modele_ml", PIPELINE_MM_FILE, "--modele-version", "mm-1", stdout=StringIO())

    def scorer(self, donnees):
        t = Transaction.objects.create(**dict(donnees, timestamp=parse_datetime(donnees["timestamp"])))
        return t, services.score_transaction(t)

    def test_la_famille_est_lue_dans_le_fichier(self):
        self.assertEqual(MLModel.objects.get(version="mm-1").famille, MLModel.Famille.MOBILE_MONEY)
        self.assertEqual(MLModel.objects.filter(is_active=True).count(), 2)

    def test_retrait_en_journee_non_fraude(self):
        t, prediction = self.scorer(TRANSACTION_MM_NORMALE)
        t.refresh_from_db()
        self.assertEqual(prediction.ml_model.version, "mm-1")
        self.assertFalse(prediction.prediction)
        self.assertEqual(t.status, Transaction.Status.LEGITIMATE)

    def test_gros_transfert_de_nuit_fraude_et_suspendu(self):
        t, prediction = self.scorer(TRANSACTION_MM_FRAUDE)
        t.refresh_from_db()
        self.assertEqual(prediction.ml_model.version, "mm-1")
        self.assertTrue(prediction.prediction)
        self.assertGreaterEqual(prediction.fraud_probability, 0.9307)
        self.assertEqual(t.status, Transaction.Status.UNDER_REVIEW)
        self.assertTrue(Alert.objects.filter(prediction=prediction).exists())

    def test_le_modele_carte_reste_utilise_pour_la_carte(self):
        _, prediction = self.scorer(dict(TRANSACTION_FRAUDE, customer_birth_date=parse_date("1963-05-02")))
        self.assertEqual(prediction.ml_model.version, "carte-1")
        self.assertTrue(prediction.prediction)
