"""
predict.py
==========
Chargement du pipeline ML entraine (fraudguard_pipeline.joblib) et scoring
d'une transaction. Appele par backend/fraud_detection/services.py — jamais
directement par le frontend.

Le fichier .joblib contient un dict unique avec tout ce qu'il faut pour
reproduire le pretraitement et la prediction, exactement comme a
l'entrainement (voir ml/notebooks/FraudGuard_ML_03_Pipeline_Final.ipynb) :
    {
        "model": ...,                  # modele XGBoost entraine
        "scaler": ...,                 # StandardScaler fit sur le train
        "colonnes_modele": [...],      # ordre exact des colonnes attendues
        "colonnes_numeriques": [...],  # colonnes a standardiser
        "seuil_decision": 0.1126,      # seuil de decision optimise (recall ~85%)
        "freq_commercant": {...},
        "freq_ville": {...},
        "freq_profession": {...},
        "categories_connues": [...],
        "regions_connues": [...],
    }
"""

import joblib

try:
    # Import relatif au dossier ml/src (ajoute a sys.path par
    # fraud_detection/apps.py cote backend ; fonctionne aussi en standalone
    # si predict.py est execute depuis ml/src).
    from preprocessing import preparer_dataframe
except ImportError:  # pragma: no cover - selon le contexte d'execution
    from .preprocessing import preparer_dataframe


def load_pipeline(path: str) -> dict:
    """
    Charge le pipeline complet depuis le fichier .joblib. Leve FileNotFoundError
    si le chemin est invalide — a laisser remonter tel quel, c'est plus clair
    qu'un echec silencieux sur un modele manquant.
    """
    return joblib.load(path)


def get_decision_threshold(pipeline: dict, fallback: float = 0.5) -> float:
    """Seuil de decision stocke dans le pipeline, ou valeur par defaut."""
    return float(pipeline.get("seuil_decision", fallback))


def predict_fraud_probability(pipeline: dict, transaction: dict) -> float:
    """
    Calcule la probabilite de fraude (0.0 a 1.0) pour une transaction brute.

    `transaction` est un dict avec les memes cles que celles utilisees a
    l'entrainement (voir preprocessing.construire_features) :
    montant_fcfa, genre, population_ville, date_transaction, date_naissance,
    latitude_client, longitude_client, latitude_commercant,
    longitude_commercant, commercant, ville, profession, categorie, region.
    """
    X = preparer_dataframe(
        transaction,
        colonnes_modele=pipeline["colonnes_modele"],
        colonnes_numeriques=pipeline["colonnes_numeriques"],
        freq_commercant=pipeline["freq_commercant"],
        freq_ville=pipeline["freq_ville"],
        freq_profession=pipeline["freq_profession"],
        scaler=pipeline["scaler"],
    )
    proba = pipeline["model"].predict_proba(X)[0][1]
    return float(proba)
