"""
preprocessing.py
=================
Source de verite unique pour le pretraitement des transactions FraudGuard.
Reproduit exactement les etapes utilisees a l'entrainement (voir notebooks/)
et doit rester synchronise avec ce que le backend utilise pour scorer une
transaction en production.
"""

import numpy as np
import pandas as pd


def haversine_distance(lat1, lon1, lat2, lon2):
    """Distance en km entre deux points GPS (client et commercant)."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * np.arcsin(np.sqrt(a)) * 6371


def construire_features(transaction: dict, colonnes_modele: list, freq_commercant: dict,
                         freq_ville: dict, freq_profession: dict) -> dict:
    """
    Transforme une transaction brute (dict) en dictionnaire de features,
    dans le meme format que celui utilise a l'entrainement.
    """
    date_transaction = pd.to_datetime(transaction["date_transaction"])
    date_naissance = pd.to_datetime(transaction["date_naissance"])

    age_client = (date_transaction - date_naissance).days // 365
    heure_transaction = date_transaction.hour
    jour_semaine = date_transaction.dayofweek
    est_weekend = int(jour_semaine in [5, 6])

    distance_km = haversine_distance(
        transaction["latitude_client"], transaction["longitude_client"],
        transaction["latitude_commercant"], transaction["longitude_commercant"],
    )

    genre_encode = 1 if transaction["genre"] == "F" else 0

    commercant_freq = freq_commercant.get(transaction["commercant"], 0.0)
    ville_freq = freq_ville.get(transaction["ville"], 0.0)
    profession_freq = freq_profession.get(transaction["profession"], 0.0)

    ligne = {col: 0 for col in colonnes_modele}
    valeurs = {
        "montant_fcfa": transaction["montant_fcfa"], "genre": genre_encode,
        "population_ville": transaction["population_ville"], "age_client": age_client,
        "heure_transaction": heure_transaction, "jour_semaine": jour_semaine,
        "est_weekend": est_weekend, "distance_client_commercant_km": distance_km,
        "commercant_freq": commercant_freq, "ville_freq": ville_freq,
        "profession_freq": profession_freq,
    }
    for col, val in valeurs.items():
        if col in ligne:
            ligne[col] = val

    col_categorie = f"categorie_{transaction['categorie']}"
    if col_categorie in ligne:
        ligne[col_categorie] = 1
    col_region = f"region_{transaction['region']}"
    if col_region in ligne:
        ligne[col_region] = 1

    return ligne


def preparer_dataframe(transaction: dict, colonnes_modele: list, colonnes_numeriques: list,
                        freq_commercant: dict, freq_ville: dict, freq_profession: dict,
                        scaler) -> pd.DataFrame:
    """
    Construit le DataFrame pret pour model.predict(), colonnes dans le bon
    ordre et standardisation appliquee.
    """
    ligne = construire_features(transaction, colonnes_modele, freq_commercant,
                                 freq_ville, freq_profession)
    X = pd.DataFrame([ligne])[colonnes_modele]
    X[colonnes_numeriques] = scaler.transform(X[colonnes_numeriques])
    return X