"""
predict.py
==========
Chargement d'un pipeline ML entraine (.joblib) et scoring d'une transaction.
Appele par backend/fraud_detection/services.py — jamais directement par le
frontend.

Il existe DEUX familles de modeles, entrainees separement, chacune avec son
propre seuil :

    "carte"         ml/models/fraudguard_pipeline.joblib
                    (preprocessing.py ; variables : montant, heure, categorie du
                    commercant, ville, ...). Les anciens .joblib n'ont pas de cle
                    « famille » : ils sont traites comme « carte ».
    "mobile_money"  ml/models/fraudguard_mobile_money_pipeline.joblib
                    (preprocessing_mobile_money.py ; variables : type d'operation,
                    montant, heure).

Chaque .joblib est un dict unique : le modele, le scaler, l'ordre des colonnes,
le seuil de decision (« seuil_decision », propre a ce modele : voir son champ
« metriques ») et, pour le modele carte, les tables de frequence.
predict_fraud_probability() choisit la bonne preparation des donnees d'apres la
famille du modele ; c'est au backend de choisir le fichier .joblib a charger.
"""

import joblib

try:
    # Imports relatifs au dossier ml/src (ajoute a sys.path par
    # fraud_detection/apps.py cote backend ; fonctionne aussi en standalone
    # si predict.py est execute depuis ml/src).
    from preprocessing import preparer_dataframe
    from preprocessing_mobile_money import preparer_dataframe as preparer_dataframe_mobile_money
except ImportError:  # pragma: no cover - selon le contexte d'execution
    from .preprocessing import preparer_dataframe
    from .preprocessing_mobile_money import preparer_dataframe as preparer_dataframe_mobile_money

FAMILLE_CARTE = "carte"
FAMILLE_MOBILE_MONEY = "mobile_money"


def load_pipeline(path: str) -> dict:
    """
    Charge le pipeline complet depuis le fichier .joblib. Leve FileNotFoundError
    si le chemin est invalide — a laisser remonter tel quel, c'est plus clair
    qu'un echec silencieux sur un modele manquant.
    """
    return joblib.load(path)


def get_family(pipeline: dict) -> str:
    """Famille du modele ; « carte » pour les .joblib qui n'ont pas la cle."""
    return pipeline.get("famille", FAMILLE_CARTE)


def get_decision_threshold(pipeline: dict, fallback: float = 0.5) -> float:
    """Seuil de decision stocke dans le pipeline, ou valeur par defaut."""
    return float(pipeline.get("seuil_decision", fallback))


def predict_fraud_probability(pipeline: dict, transaction: dict) -> float:
    """
    Calcule la probabilite de fraude (0.0 a 1.0) pour une transaction brute.

    Famille « carte » : `transaction` a les cles de preprocessing.construire_features
    (montant_fcfa, genre, population_ville, date_transaction, date_naissance,
    latitude_client, longitude_client, latitude_commercant, longitude_commercant,
    commercant, ville, profession, categorie, region).

    Famille « mobile_money » : `transaction` est de la forme
    {"type": "TRANSFER", "montant": 250000.0, "heure": 23}
    (type : CASH_IN | CASH_OUT | TRANSFER | PAYMENT | DEBIT, ou le libelle francais ;
    montant : nombre >= 0, en unite du simulateur ; heure : entier de 0 a 23, heure
    locale). Les cles « type_operation » et « heure_transaction » sont aussi acceptees.
    """
    famille = get_family(pipeline)
    if famille == FAMILLE_MOBILE_MONEY:
        X = preparer_dataframe_mobile_money(
            transaction,
            colonnes_modele=pipeline["colonnes_modele"],
            colonnes_numeriques=pipeline["colonnes_numeriques"],
            scaler=pipeline["scaler"],
        )
    elif famille == FAMILLE_CARTE:
        X = preparer_dataframe(
            transaction,
            colonnes_modele=pipeline["colonnes_modele"],
            colonnes_numeriques=pipeline["colonnes_numeriques"],
            freq_commercant=pipeline["freq_commercant"],
            freq_ville=pipeline["freq_ville"],
            freq_profession=pipeline["freq_profession"],
            scaler=pipeline["scaler"],
        )
    else:
        raise ValueError(f"Famille de modele inconnue : {famille!r}")
    return float(pipeline["model"].predict_proba(X)[0][1])
