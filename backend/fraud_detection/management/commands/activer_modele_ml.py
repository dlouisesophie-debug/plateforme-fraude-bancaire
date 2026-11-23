"""
Commande de gestion : enregistre et active un modele ML (pipeline .joblib)
dans la table ml_models, en remplacement de l'ancien script ad-hoc
activer_modele_ml.py.

Usage (depuis le dossier backend/, conteneur ou venv) :

    python manage.py activer_modele_ml fraudguard_pipeline.joblib \
        --modele-version v2 --algorithm xgboost \
        --precision 0.607492 --recall 0.869464 --f1 0.715244 --auc 0.994488

Le chemin peut etre relatif a settings.ML_MODELS_DIR (recommande, c'est le
dossier monte par docker-compose, volume ./ml/models:/app/ml_models) ou
absolu.

Un seul modele peut etre actif par famille (contrainte
single_active_model_per_family sur MLModel) : cette commande desactive
automatiquement l'ancien modele actif de la MEME famille avant d'activer le
nouveau. La famille (carte ou mobile_money) est lue dans le fichier (cle
"famille", absente = carte), ou imposee avec --famille :

    python manage.py activer_modele_ml fraudguard_mobile_money_pipeline.joblib \
        --modele-version mm-v1 --famille mobile_money
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
        parser.add_argument(
            "--famille", default=None, choices=MLModel.Famille.values,
            help="Famille du modele. Par defaut : cle \"famille\" du fichier (absente = carte).",
        )

    @staticmethod
    def _lire_fichier(chemin_absolu):
        """
        Famille et date d'entrainement enregistrees dans le pipeline. La date vient de
        metriques["date_entrainement"] (ecrite par ml/src/training*.py) ; None si absente ou
        illisible.
        """
        from predict import load_pipeline  # ml/src, ajoute au chemin par fraud_detection/apps.py

        pipeline = load_pipeline(chemin_absolu)
        if not isinstance(pipeline, dict):
            return MLModel.Famille.CARTE, None
        famille = pipeline.get("famille", MLModel.Famille.CARTE)
        date_entrainement = None
        texte = (pipeline.get("metriques") or {}).get("date_entrainement")
        if texte:
            try:
                date_entrainement = datetime.fromisoformat(str(texte))
            except ValueError:
                date_entrainement = None
            if date_entrainement is not None and date_entrainement.tzinfo is None:
                date_entrainement = date_entrainement.replace(tzinfo=timezone.utc)
        return famille, date_entrainement

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
        famille_du_fichier, date_entrainement = self._lire_fichier(chemin_absolu)
        famille = options["famille"] or famille_du_fichier
        if famille not in MLModel.Famille.values:
            raise CommandError(f"Famille inconnue dans le fichier : {famille!r} (attendu : {MLModel.Famille.values}).")

        # Un seul modele actif par famille (contrainte DB) : on desactive
        # l'ancien de la meme famille avant de creer/activer le nouveau.
        MLModel.objects.filter(is_active=True, famille=famille).exclude(version=version).update(is_active=False)

        modele, cree = MLModel.objects.update_or_create(
            version=version,
            defaults={
                "famille": famille,
                "algorithm": options["algorithm"],
                "precision_score": options["precision"],
                "recall_score": options["recall"],
                "f1_score": options["f1"],
                "auc_roc": options["auc"],
                # Vraie date d'entrainement si le fichier la contient ; sinon, date d'activation.
                "trained_at": date_entrainement or datetime.now(timezone.utc),
                "is_active": True,
                "artifact_path": chemin_joblib,
            },
        )

        action = "cree et active" if cree else "mis a jour et active"
        self.stdout.write(self.style.SUCCESS(
            f"Modele ML {action} : {modele.algorithm} {modele.version}, famille {modele.famille} "
            f"(artifact_path={modele.artifact_path})"
        ))
        if date_entrainement:
            self.stdout.write(f"Date d'entrainement lue dans le fichier : {date_entrainement.isoformat()}")
        else:
            self.stdout.write(self.style.WARNING(
                "Date d'entrainement absente du fichier : la date d'activation est enregistree a la place."
            ))
