"""
preprocessing_mobile_money.py
=============================
Pretraitement du modele MOBILE MONEY (jeu PaySim). Module separe de
preprocessing.py (modele carte) : les deux modeles ne partagent ni variables
ni preprocesseur.

CONTRAT DE DONNEES (ce que l'agent saisit ET ce que le modele utilise) :

    type_operation     : Depot | Retrait | Transfert | Paiement | Debit
                         (ou le code PaySim : CASH_IN | CASH_OUT | TRANSFER | PAYMENT | DEBIT)
    montant            : nombre >= 0, en unite du simulateur (PAS des FCFA)
    heure_transaction  : entier de 0 a 23

A l'API, la transaction est un dict {"type": ..., "montant": ..., "heure": ...}
(les cles « type_operation » et « heure_transaction » sont aussi acceptees).

Colonnes INTERDITES (jamais lues, jamais utilisees) :
    - les 4 colonnes de soldes (oldbalanceOrg, newbalanceOrig, oldbalanceDest,
      newbalanceDest) : elles trahissent la fraude (faux score ~99 %) ;
    - les identifiants de compte (nameOrig, nameDest) ;
    - isFlaggedFraud : sortie d'une regle du simulateur, pas une information
      connue avant la decision ;
    - le `step` BRUT (indice de temps des 30 jours de simulation) : il est lu
      uniquement pour calculer l'heure du jour (heure = step modulo 24) et n'est
      jamais une variable du modele.
Le chargement (training_mobile_money.charger_paysim) ne lit meme pas ces
colonnes du CSV, et construire_matrice() refuse toute colonne hors contrat.
"""

import unicodedata

import numpy as np
import pandas as pd

FAMILLE = "mobile_money"

# Valeur PaySim -> libelle francais du contrat -> cle ASCII de colonne
TYPES_PAYSIM = {
    "CASH_IN": "Dépôt",
    "CASH_OUT": "Retrait",
    "TRANSFER": "Transfert",
    "PAYMENT": "Paiement",
    "DEBIT": "Débit",
}
TYPES_FR = list(TYPES_PAYSIM.values())


def _normaliser(texte: str) -> str:
    """'Dépôt ' -> 'depot' (sans accents, sans espaces, minuscules)."""
    t = unicodedata.normalize("NFKD", str(texte).strip())
    return "".join(c for c in t if not unicodedata.combining(c)).casefold()


CLE_TYPE = {_normaliser(fr): _normaliser(fr) for fr in TYPES_FR}  # 'depot', 'retrait'...

# Valeurs acceptees en plus des libelles francais : les valeurs internes (codes PaySim)
# et le libelle long du Debit (« Debit vers un compte bancaire », definition PaySim).
ALIAS_TYPES = {_normaliser(code): _normaliser(fr) for code, fr in TYPES_PAYSIM.items()}
ALIAS_TYPES[_normaliser("Débit vers un compte bancaire")] = _normaliser("Débit")
TYPES_CLES = list(CLE_TYPE.values())

COLONNES_NUMERIQUES = ["montant", "heure_transaction"]
COLONNES_MODELE = COLONNES_NUMERIQUES + [f"type_{c}" for c in TYPES_CLES]

# Colonnes autorisees en entree de construire_matrice (contrat + cible)
COLONNES_AUTORISEES = {"type_operation", "montant", "heure_transaction", "est_fraude"}

# Fragments de noms qui ne doivent apparaitre dans AUCUNE variable du modele
MOTS_INTERDITS = ("balance", "solde", "name", "orig", "dest", "flagged", "id_", "compte", "client", "step")

# Colonnes PaySim lues dans le CSV (jamais les soldes ni les identifiants)
COLONNES_PAYSIM_LUES = ["step", "type", "amount", "isFraud"]


def verifier_colonnes_autorisees(colonnes) -> None:
    """Leve ValueError si une colonne est hors contrat (soldes, identifiants...)."""
    en_trop = sorted(set(colonnes) - COLONNES_AUTORISEES)
    if en_trop:
        raise ValueError(
            f"Colonnes interdites ou hors contrat pour le modele mobile money : {en_trop}. "
            f"Autorisees : {sorted(COLONNES_AUTORISEES)}"
        )


def _cle_brute(valeur) -> str:
    """Normalise puis applique les alias (codes PaySim, libelle long du Debit)."""
    cle = _normaliser(valeur)
    return ALIAS_TYPES.get(cle, cle)


def cle_type_operation(valeur: str) -> str:
    """
    Valide un type d'operation et renvoie sa cle ('depot'...). Accepte le libelle
    francais (avec ou sans accent), la valeur interne PaySim (CASH_IN, CASH_OUT,
    TRANSFER, PAYMENT, DEBIT) et « Debit vers un compte bancaire ».
    """
    cle = _cle_brute(valeur)
    if cle not in CLE_TYPE:
        raise ValueError(
            f"Type d'operation inconnu : {valeur!r}. Valeurs : {TYPES_FR} "
            f"ou codes {list(TYPES_PAYSIM)}")
    return cle


def heure_depuis_step(step) -> int:
    """PaySim : 1 step = 1 heure de simulation ; heure du jour = step modulo 24."""
    return np.asarray(step, dtype=int) % 24


def preparer_paysim(df_brut: pd.DataFrame) -> pd.DataFrame:
    """
    PaySim brut (colonnes step, type, amount, isFraud) -> colonnes du contrat
    (type_operation en francais, montant, heure_transaction) + est_fraude.
    """
    manquantes = [c for c in COLONNES_PAYSIM_LUES if c not in df_brut.columns]
    if manquantes:
        raise ValueError(f"Colonnes PaySim absentes : {manquantes}")
    inconnus = sorted(set(df_brut["type"].unique()) - set(TYPES_PAYSIM))
    if inconnus:
        raise ValueError(f"Types PaySim inconnus : {inconnus}")
    if df_brut["isFraud"].isna().any():
        raise ValueError("La colonne isFraud contient des valeurs manquantes.")
    propre = pd.DataFrame({
        "type_operation": df_brut["type"].map(TYPES_PAYSIM),
        "montant": df_brut["amount"].astype(float),
        "heure_transaction": heure_depuis_step(df_brut["step"].values),
        "est_fraude": df_brut["isFraud"].astype(int),
    }, index=df_brut.index)
    return propre


def construire_matrice(df: pd.DataFrame, colonnes: list = None) -> pd.DataFrame:
    """
    Matrice de variables vectorisee (entrainement). Refuse toute colonne hors
    contrat : un test verrouille ce comportement.
    """
    verifier_colonnes_autorisees(df.columns)
    colonnes = colonnes or COLONNES_MODELE
    cles = df["type_operation"].map(_cle_brute)
    inconnus = sorted(set(cles.unique()) - set(TYPES_CLES))
    if inconnus:
        raise ValueError(f"Types d'operation inconnus : {inconnus}")
    X = pd.DataFrame(index=df.index)
    X["montant"] = df["montant"].astype(float)
    X["heure_transaction"] = df["heure_transaction"].astype(float)
    for c in TYPES_CLES:
        X[f"type_{c}"] = (cles == c).astype(float)
    return X[colonnes]


# Noms de cles acceptes pour la transaction saisie (le backend envoie « type » et « heure »)
CLES_TYPE = ("type_operation", "type")
CLES_HEURE = ("heure_transaction", "heure")


def _champ(transaction: dict, noms: tuple, libelle: str):
    for nom in noms:
        if nom in transaction:
            return transaction[nom]
    raise KeyError(f"Champ « {libelle} » manquant : cle attendue parmi {list(noms)}")


def construire_features(transaction: dict, colonnes_modele: list = None) -> dict:
    """
    UNE transaction saisie -> dict de variables, identique ligne a ligne a
    construire_matrice (verifie par un test). Cles acceptees :
        type    ou type_operation     : codes PaySim (CASH_IN, CASH_OUT, TRANSFER,
                                        PAYMENT, DEBIT) ou libelles francais
        montant                       : nombre >= 0 (unite du simulateur)
        heure   ou heure_transaction  : entier de 0 a 23 (heure locale ; Dakar = UTC+0)
    """
    colonnes_modele = colonnes_modele or COLONNES_MODELE
    cle = cle_type_operation(_champ(transaction, CLES_TYPE, "type"))
    montant = float(_champ(transaction, ("montant",), "montant"))
    if not np.isfinite(montant) or montant < 0:
        raise ValueError(f"Montant invalide : {transaction['montant']!r} (nombre >= 0 attendu)")
    heure = int(_champ(transaction, CLES_HEURE, "heure"))
    if not 0 <= heure <= 23:
        raise ValueError(f"Heure invalide : {heure} (0 a 23 attendu)")
    ligne = {col: 0.0 for col in colonnes_modele}
    ligne["montant"] = montant
    ligne["heure_transaction"] = float(heure)
    ligne[f"type_{cle}"] = 1.0
    return ligne


def preparer_dataframe(transaction: dict, colonnes_modele: list, colonnes_numeriques: list,
                       scaler) -> pd.DataFrame:
    """DataFrame pret pour model.predict_proba() : bon ordre de colonnes + standardisation."""
    ligne = construire_features(transaction, colonnes_modele)
    X = pd.DataFrame([ligne])[colonnes_modele]
    X[colonnes_numeriques] = scaler.transform(X[colonnes_numeriques])
    return X
