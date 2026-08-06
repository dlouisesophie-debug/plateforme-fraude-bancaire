"""
Chargement du modele actif et prediction — appele indirectement par
backend/fraud_detection/services.py.
"""

import joblib


def load_model(path: str):
    return joblib.load(path)


def predict_fraud_probability(model, features) -> float:
    """Retourne la probabilite de fraude (classe positive) pour une transaction."""
    return float(model.predict_proba([features])[0][1])
