"""
Point d'integration entre le backend Django et le pipeline ML (dossier /ml).
"""
import os
import threading
import logging

import numpy as np
import pandas as pd

from django.conf import settings
from .models import MLModel, Prediction

logger = logging.getLogger(__name__)

_PIPELINE = None
_LOCK = threading.Lock()


def _charger_pipeline():
    global _PIPELINE
    if _PIPELINE is not None:
        return _PIPELINE
    with _LOCK:
        if _PIPELINE is not None:
            return _PIPELINE
        import joblib
        chemin = os.path.join(settings.ML_MODELS_DIR, settings.ML_ACTIVE_MODEL_FILE)
        if not os.path.isfile(chemin):
            raise RuntimeError(f"Pipeline ML introuvable : {chemin}")
        _PIPELINE = joblib.load(chemin)
        logger.info("Pipeline ML charge depuis %s", chemin)
        return _PIPELINE


def _haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * np.arcsin(np.sqrt(a)) * 6371


def score_transaction(transaction):
    """
    Score une transaction avec le modele ML actif et cree la Prediction
    correspondante. Declenche une alerte si le score depasse le seuil.
    """
    active_model = MLModel.objects.filter(is_active=True).first()
    if active_model is None:
        raise RuntimeError("Aucun modele ML actif - voir MLModel.is_active")

    if transaction.customer is None:
        raise RuntimeError(
            "Cette transaction n'a pas de client associe - impossible de scorer "
            "(le pipeline ML a besoin des donnees client)."
        )

    p = _charger_pipeline()
    c = transaction.customer

    date_transaction = pd.to_datetime(transaction.timestamp).tz_localize(None)
    date_naissance = pd.to_datetime(c.date_of_birth)
    age_client = (date_transaction - date_naissance).days // 365
    heure_transaction = date_transaction.hour
    jour_semaine = date_transaction.dayofweek
    est_weekend = int(jour_semaine in [5, 6])
    distance_km = _haversine(
        c.latitude, c.longitude,
        transaction.merchant_latitude, transaction.merchant_longitude,
    )
    genre_encode = 1 if c.gender == "F" else 0

    commercant_freq = p["freq_commercant"].get(transaction.merchant, 0.0)
    ville_freq = p["freq_ville"].get(c.city, 0.0)
    profession_freq = p["freq_profession"].get(c.profession, 0.0)

    ligne = {col: 0 for col in p["colonnes_modele"]}
    valeurs = {
        "montant_fcfa": float(transaction.amount), "genre": genre_encode,
        "population_ville": c.city_population or 0, "age_client": age_client,
        "heure_transaction": heure_transaction, "jour_semaine": jour_semaine,
        "est_weekend": est_weekend, "distance_client_commercant_km": distance_km,
        "commercant_freq": commercant_freq, "ville_freq": ville_freq,
        "profession_freq": profession_freq,
    }
    for col, val in valeurs.items():
        if col in ligne:
            ligne[col] = val

    col_cat = f"categorie_{transaction.category}"
    if col_cat in ligne:
        ligne[col_cat] = 1
    col_reg = f"region_{c.region}"
    if col_reg in ligne:
        ligne[col_reg] = 1

    X = pd.DataFrame([ligne])[p["colonnes_modele"]]
    X[p["colonnes_numeriques"]] = p["scaler"].transform(X[p["colonnes_numeriques"]])

    fraud_probability = float(p["model"].predict_proba(X)[:, 1][0])
    is_fraud = fraud_probability >= float(p["seuil_decision"])

    prediction = Prediction.objects.create(
        transaction=transaction,
        ml_model=active_model,
        fraud_probability=round(fraud_probability, 4),
        prediction=is_fraud,
    )

    if is_fraud:
        from alerts.models import Alert
        Alert.objects.create(prediction=prediction, severity="medium")

    return prediction

