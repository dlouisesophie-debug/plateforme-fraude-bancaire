"""
Pretraitement des donnees de transactions.

TODO Etudiant 2 (Phase 6 de la roadmap) :
- gerer les valeurs manquantes et aberrantes
- encoder les variables categorielles (channel, merchant, device...)
- normaliser/standardiser les variables numeriques (amount...)
- creer les features pertinentes (heure de la transaction, frequence
  par utilisateur, ecart au montant moyen, etc.)

IMPORTANT : ce module doit rester importable tel quel depuis le backend
Django (backend/fraud_detection/services.py) pour garantir que le
preprocessing applique en production est identique a celui de l'entrainement.
"""

import pandas as pd


def load_raw_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """TODO : valeurs manquantes, doublons, types de donnees."""
    df = df.drop_duplicates()
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """TODO : feature engineering (CDC 3.2, Phase 6)."""
    return df


def preprocess_transaction(transaction_dict: dict) -> dict:
    """
    Applique le meme pipeline qu'a l'entrainement a UNE transaction
    (utilise par le backend au moment du scoring en production).
    """
    # TODO : reutiliser build_features() sur un DataFrame a une ligne
    raise NotImplementedError
