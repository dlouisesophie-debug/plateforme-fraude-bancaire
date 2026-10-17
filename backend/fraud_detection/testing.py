"""
Outils de test : un « faux modèle » qui remplace le pipeline .joblib.

Le vrai fichier fraudguard_pipeline.joblib n'est pas versionné (trop
volumineux) : sans lui, les tests de scoring réels sont ignorés en CI.
`faux_modele(probabilite)` permet de tester toute la logique métier autour
du scoring (statuts, alertes, dashboard, seed...) sans le fichier, en
fixant la probabilité renvoyée par le modèle.
"""

import sys
import types
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest import mock

from .models import MLModel

SEUIL_TEST = 0.5


def activer_faux_modele(version="faux-1"):
    return MLModel.objects.create(
        version=version, algorithm="xgboost", trained_at=datetime.now(timezone.utc),
        is_active=True, artifact_path="faux.joblib",
        precision_score=0.78, recall_score=0.85, f1_score=0.81, auc_roc=0.99,
    )


@contextmanager
def faux_modele(probabilite):
    """
    Remplace le chargement du pipeline et la prédiction. `probabilite` est
    soit un nombre fixe, soit une fonction transaction_dict -> probabilité.
    """
    pipeline = {
        "seuil_decision": SEUIL_TEST,
        "categories_connues": ["achats", "achats_en_ligne", "courses", "restauration", "sante_sport",
                               "maison", "soins_personnels", "divertissement", "divers_en_ligne",
                               "courses_en_ligne"],
        "regions_connues": ["Dakar", "Thiès", "Saint-Louis", "Kaolack", "Ziguinchor", "Diourbel",
                            "Tambacounda", "Louga", "Fatick"],
    }
    calcul = probabilite if callable(probabilite) else (lambda _t: probabilite)

    # Faux module `predict` (normalement ml/src/predict.py) : fonctionne même
    # si ml/src n'est pas dans le chemin Python, comme dans la CI GitHub.
    faux_predict = types.ModuleType("predict")
    faux_predict.predict_fraud_probability = lambda _pipeline, transaction: calcul(transaction)
    faux_predict.get_decision_threshold = (
        lambda pipe, fallback=0.5: float(pipe.get("seuil_decision", fallback))
    )
    faux_predict.load_pipeline = lambda _chemin: pipeline

    with mock.patch.dict(sys.modules, {"predict": faux_predict}), \
            mock.patch("fraud_detection.services._charger_pipeline", return_value=pipeline):
        yield pipeline
