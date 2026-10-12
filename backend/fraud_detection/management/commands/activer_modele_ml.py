"""
Commande de gestion : enregistre et active un modele ML (pipeline .joblib)
dans la table ml_models, en remplacement de l'ancien script ad-hoc
activer_modele_ml.py.

Usage (depuis le dossier backend/, conteneur ou venv) :

    python manage.py activer_modele_ml ml_models/fraudguard_pipeline.joblib \
        --modele-version v1 --algorithm xgboost \
        --precision 0.90 --recall 0.80 --f1 0.847 --auc 0.9933

Le chemin peut etre relatif a settings.ML_MODELS_DIR (recommande, c'est le
dossier monte par docker-compose, volume ./ml/models:/app/ml_models) ou
absolu.

Un seul modele peut etre actif a la fois (contrainte single_active_model
sur MLModel) : cette commande desactive automatiquement l'ancien modele
actif avant d'activer le nouveau.
"""

import os
from datetime import datetime, timezone

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from fraud_detection.models import MLModel


class Command(BaseCommand):
    help = "Enregistre un pipeline ML (.joblib) et l'active comme modele de scoring."

    def add_arguments(self, parser):
        parser.add_argument(
            "chemin_joblib",
            help="Chemin du fichier .joblib, relatif a ML_MODELS_DIR ou absolu.",
        )
        parser.add_argument(
            "--modele-version",
            dest="modele_version",
            default=None,
            help="Identifiant de version du modele (ex: v1). Auto-genere si omis. "
                 "(nomme --modele-version pour ne pas entrer en conflit avec --version de Django)",
        )
        parser.add_argument("--algorithm", default="xgboost", choices=["logistic_regression", "random_forest", "xgboost"])
        parser.add_argument("--precision", type=float, default=None)
        parser.add_argument("--recall", type=float, default=None)
        parser.add_argument("--f1", type=float, default=None)
        parser.add_argument("--auc", type=float, default=None)

    def handle(self, *args, **options):
        chemin_joblib = options["chemin_joblib"]

        # Verifie que le fichier existe reellement avant d'enregistrer quoi
        # que ce soit en base — eviter un MLModel actif pointant sur un
        # fichier introuvable.
        chemin_absolu = chemin_joblib
        if not os.path.isabs(chemin_absolu):
            chemin_absolu = os.path.join(settings.ML_MODELS_DIR, chemin_joblib)
        if not os.path.isfile(chemin_absolu):
            raise CommandError(f"Fichier introuvable : {chemin_absolu}")

        version = options["modele_version"] or datetime.now(timezone.utc).strftime("v%Y%m%d-%H%M%S")

        # Un seul modele actif a la fois (contrainte DB) : on desactive
        # l'ancien avant de creer/activer le nouveau.
        MLModel.objects.filter(is_active=True).update(is_active=False)

        modele, cree = MLModel.objects.update_or_create(
            version=version,
            defaults={
                "algorithm": options["algorithm"],
                "precision_score": options["precision"],
                "recall_score": options["recall"],
                "f1_score": options["f1"],
                "auc_roc": options["auc"],
                "trained_at": datetime.now(timezone.utc),
                "is_active": True,
                "artifact_path": chemin_joblib,
            },
        )

        action = "cree et active" if cree else "mis a jour et active"
        self.stdout.write(self.style.SUCCESS(
            f"Modele ML {action} : {modele.algorithm} {modele.version} "
            f"(artifact_path={modele.artifact_path})"
        ))
