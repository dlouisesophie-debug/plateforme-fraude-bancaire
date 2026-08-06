"""
Point d'integration entre le backend Django et le pipeline ML (dossier /ml).

TODO Etudiant 1 + Etudiant 2 (Phase 9 — Integration complete) :
1. Charger le modele actif (MLModel.objects.get(is_active=True)) via joblib
   depuis le chemin monte dans le conteneur (voir volume ./ml/models dans
   docker-compose.yml).
2. Appliquer le meme preprocessing que celui utilise a l'entrainement
   (reutiliser ml/src/preprocessing.py pour eviter toute divergence).
3. Creer la Prediction, puis si fraud_probability > settings.FRAUD_ALERT_THRESHOLD,
   creer automatiquement une Alert (voir app alerts).
"""

from django.conf import settings

from .models import MLModel, Prediction


def score_transaction(transaction):
    """
    Score une transaction avec le modele ML actif et cree la Prediction
    correspondante. Declenche une alerte si le score depasse le seuil.
    """
    active_model = MLModel.objects.filter(is_active=True).first()
    if active_model is None:
        raise RuntimeError("Aucun modele ML actif — voir MLModel.is_active")

    # TODO : remplacer par le vrai appel au modele charge en memoire
    fraud_probability = 0.0
    is_fraud = fraud_probability > settings.FRAUD_ALERT_THRESHOLD

    prediction = Prediction.objects.create(
        transaction=transaction,
        ml_model=active_model,
        fraud_probability=fraud_probability,
        prediction=is_fraud,
    )

    if is_fraud:
        from alerts.models import Alert

        Alert.objects.create(prediction=prediction, severity="medium")

    return prediction
