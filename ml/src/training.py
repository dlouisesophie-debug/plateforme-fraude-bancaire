"""
training.py
===========
Entrainement reproductible du modele FraudGuard (CDC 3.2, Phase 6).
Reproduit et corrige le notebook final (FraudGuard_ML_03_Pipeline_Final.ipynb).

Usage (depuis le dossier ml/src) :

    python training.py --data ../data/raw/fraudTest_senegal.csv

Ce que fait le script, dans l'ordre :

1. Decoupage stratifie en TROIS jeux : train (60 %) / validation (20 %) / test (20 %).
   Le jeu de test est exactement celui des notebooks precedents
   (test_size=0.2, random_state=42, stratify) : les resultats restent comparables.
2. Tables de frequence (commercant, ville, profession) et StandardScaler calcules
   sur le TRAIN uniquement.
3. SMOTE place DANS un imblearn.pipeline.Pipeline : il n'est applique qu'aux
   donnees d'entrainement de chaque pli de validation croisee, jamais aux donnees
   de validation. C'est ce qui supprime la fuite de donnees (SMOTE avant
   RandomizedSearchCV => rappel CV de 0,9998 irrealiste).
4. Comparaison de 3 modeles (regression logistique, Random Forest, XGBoost
   optimise par RandomizedSearchCV) sur le jeu de VALIDATION.
5. Seuil de decision choisi sur la VALIDATION (rappel cible 85 %), jamais sur le test.
6. Metriques finales annoncees sur le TEST, utilisees une seule fois.
7. Comparaison avec / sans la variable « genre » (RGPD, equite).
8. Export du .joblib (avec le dictionnaire « metriques ») + rapports (PNG, JSON, CSV).
"""

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
import imblearn
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

try:  # execution directe : python training.py (depuis ml/src)
    from evaluation import (
        choisir_seuil, evaluer, intervalle_confiance_bootstrap, plot_confusion_matrix,
    )
    from preprocessing import haversine_distance
except ImportError:  # pragma: no cover - utilisation comme package
    from .evaluation import (
        choisir_seuil, evaluer, intervalle_confiance_bootstrap, plot_confusion_matrix,
    )
    from .preprocessing import haversine_distance

GRAINE = 42
RECALL_CIBLE = 0.85
COLONNES_NUMERIQUES = [
    "montant_fcfa", "age_client", "distance_client_commercant_km",
    "population_ville", "commercant_freq", "ville_freq", "profession_freq",
]
COLONNES_BRUTES_REQUISES = [
    "date_transaction", "date_naissance", "montant_fcfa", "genre", "population_ville",
    "latitude_client", "longitude_client", "latitude_commercant", "longitude_commercant",
    "commercant", "ville", "profession", "categorie", "region", "est_fraude",
]
GRILLE_XGBOOST = {
    "clf__n_estimators": [100, 200, 300, 400],
    "clf__max_depth": [4, 6, 8, 10],
    "clf__learning_rate": [0.01, 0.05, 0.1, 0.2],
    "clf__subsample": [0.7, 0.8, 1.0],
    "clf__colsample_bytree": [0.7, 0.8, 1.0],
}


# --------------------------------------------------------------------------
# 1. Donnees
# --------------------------------------------------------------------------
def charger_donnees(chemin_csv: str) -> pd.DataFrame:
    df = pd.read_csv(chemin_csv)
    manquantes = [c for c in COLONNES_BRUTES_REQUISES if c not in df.columns]
    if manquantes:
        raise ValueError(f"Colonnes absentes du CSV : {manquantes}")
    if df["est_fraude"].isna().any():
        raise ValueError("La colonne est_fraude contient des valeurs manquantes.")
    df["date_transaction"] = pd.to_datetime(df["date_transaction"])
    df["date_naissance"] = pd.to_datetime(df["date_naissance"])
    return df


def decouper(df: pd.DataFrame):
    """Train 60 % / validation 20 % / test 20 %, stratifie sur est_fraude."""
    train_val, test = train_test_split(
        df, test_size=0.2, random_state=GRAINE, stratify=df["est_fraude"]
    )
    train, val = train_test_split(
        train_val, test_size=0.25, random_state=GRAINE, stratify=train_val["est_fraude"]
    )  # 0,8 x 0,25 = 0,20 du total
    return train, val, test


def tables_de_reference(df_train: pd.DataFrame, df_complet: pd.DataFrame) -> dict:
    """
    Tables de frequence : calculees sur le TRAIN seul. Les listes de categories
    et de regions sont un simple vocabulaire (sans lien avec la cible).
    """
    return {
        "freq_commercant": df_train["commercant"].value_counts(normalize=True).to_dict(),
        "freq_ville": df_train["ville"].value_counts(normalize=True).to_dict(),
        "freq_profession": df_train["profession"].value_counts(normalize=True).to_dict(),
        "categories_connues": sorted(df_complet["categorie"].unique().tolist()),
        "regions_connues": sorted(df_complet["region"].unique().tolist()),
    }


def liste_colonnes(tables: dict, avec_genre: bool = True) -> list:
    """
    Ordre des colonnes identique au notebook (get_dummies drop_first=True :
    la premiere categorie / region, par ordre alphabetique, sert de reference).
    """
    colonnes = [
        "montant_fcfa", "genre", "population_ville", "age_client", "heure_transaction",
        "jour_semaine", "est_weekend", "distance_client_commercant_km",
    ]
    colonnes += [f"categorie_{c}" for c in tables["categories_connues"][1:]]
    colonnes += [f"region_{r}" for r in tables["regions_connues"][1:]]
    colonnes += ["commercant_freq", "ville_freq", "profession_freq"]
    if not avec_genre:
        colonnes.remove("genre")
    return colonnes


def construire_matrice(df: pd.DataFrame, tables: dict, colonnes: list) -> pd.DataFrame:
    """
    Version vectorisee de preprocessing.construire_features (meme logique,
    verifiee ligne par ligne dans les tests). Les valeurs inconnues des tables
    de frequence valent 0.0, comme au moment du scoring.
    """
    X = pd.DataFrame(index=df.index)
    X["montant_fcfa"] = df["montant_fcfa"].astype(float)
    X["genre"] = (df["genre"] == "F").astype(int)
    X["population_ville"] = df["population_ville"].astype(float)
    X["age_client"] = (df["date_transaction"] - df["date_naissance"]).dt.days // 365
    X["heure_transaction"] = df["date_transaction"].dt.hour
    X["jour_semaine"] = df["date_transaction"].dt.dayofweek
    X["est_weekend"] = X["jour_semaine"].isin([5, 6]).astype(int)
    X["distance_client_commercant_km"] = haversine_distance(
        df["latitude_client"], df["longitude_client"],
        df["latitude_commercant"], df["longitude_commercant"],
    )
    for c in tables["categories_connues"][1:]:
        X[f"categorie_{c}"] = (df["categorie"] == c).astype(int)
    for r in tables["regions_connues"][1:]:
        X[f"region_{r}"] = (df["region"] == r).astype(int)
    X["commercant_freq"] = df["commercant"].map(tables["freq_commercant"]).fillna(0.0)
    X["ville_freq"] = df["ville"].map(tables["freq_ville"]).fillna(0.0)
    X["profession_freq"] = df["profession"].map(tables["freq_profession"]).fillna(0.0)
    return X[colonnes].astype(float)


def standardiser(X_train, X_val, X_test, scaler=None):
    """Scaler ajuste sur le TRAIN uniquement."""
    scaler = scaler or StandardScaler().fit(X_train[COLONNES_NUMERIQUES])
    sorties = []
    for X in (X_train, X_val, X_test):
        X = X.copy()
        X[COLONNES_NUMERIQUES] = scaler.transform(X[COLONNES_NUMERIQUES])
        sorties.append(X)
    return (*sorties, scaler)


# --------------------------------------------------------------------------
# 2. Modeles (SMOTE toujours DANS le pipeline)
# --------------------------------------------------------------------------
def pipeline_xgboost(**params) -> ImbPipeline:
    clf = XGBClassifier(eval_metric="logloss", random_state=GRAINE, n_jobs=-1,
                        tree_method="hist", **params)
    return ImbPipeline([("smote", SMOTE(random_state=GRAINE)), ("clf", clf)])


def pipeline_logistique() -> ImbPipeline:
    return ImbPipeline([
        ("smote", SMOTE(random_state=GRAINE)),
        ("clf", LogisticRegression(max_iter=1000, random_state=GRAINE)),
    ])


def pipeline_random_forest() -> ImbPipeline:
    return ImbPipeline([
        ("smote", SMOTE(random_state=GRAINE)),
        ("clf", RandomForestClassifier(n_estimators=200, max_depth=12, class_weight="balanced",
                                       random_state=GRAINE, n_jobs=-1)),
    ])


def rechercher_hyperparametres(X_train, y_train, n_iter: int = 15, cv: int = 3):
    """
    RandomizedSearchCV sur un Pipeline [SMOTE -> XGBoost] : a chaque pli, SMOTE
    est ajuste sur les seuls plis d'entrainement. Score = PR-AUC (average
    precision), adapte au desequilibre et independant du seuil : un score de
    rappel a seuil 0,5 recompenserait un modele qui declare tout « fraude ».
    """
    recherche = RandomizedSearchCV(
        pipeline_xgboost(),
        param_distributions=GRILLE_XGBOOST,
        n_iter=n_iter,
        scoring="average_precision",
        cv=StratifiedKFold(n_splits=cv, shuffle=True, random_state=GRAINE),
        random_state=GRAINE,
        n_jobs=1,  # XGBoost / RandomForest utilisent deja tous les coeurs
        refit=True,
        error_score="raise",
        verbose=1,
    )
    recherche.fit(X_train, y_train)
    return recherche


def meilleurs_parametres(recherche) -> dict:
    return {k.replace("clf__", ""): v for k, v in recherche.best_params_.items()}


# --------------------------------------------------------------------------
# 3. Evaluation d'une configuration
# --------------------------------------------------------------------------
def evaluer_configuration(pipeline, X_val, y_val, X_test, y_test, recall_cible) -> dict:
    """Seuil choisi sur la validation ; metriques validation et test a ce seuil."""
    proba_val = pipeline.predict_proba(X_val)[:, 1]
    proba_test = pipeline.predict_proba(X_test)[:, 1]
    seuil = choisir_seuil(y_val, proba_val, recall_cible)
    return {
        "seuil": seuil,
        "validation": evaluer(y_val, proba_val, seuil),
        "test": evaluer(y_test, proba_test, seuil),
        "test_ic95": intervalle_confiance_bootstrap(y_test, proba_test, seuil),
        "_proba_test": proba_test,
    }


def part_importance(classifieur, colonnes, nom: str):
    """Part (en %) du gain total attribuee a une variable (arbres uniquement)."""
    if not hasattr(classifieur, "get_booster"):
        return None
    gains = classifieur.get_booster().get_score(importance_type="gain")
    total = sum(gains.values())
    # xgboost nomme les variables f0, f1... si on lui passe un tableau numpy
    return float(100 * gains.get(nom, 0.0) / total) if total else None


def _sans_proba(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


# --------------------------------------------------------------------------
# 4. Programme principal
# --------------------------------------------------------------------------
def entrainer(chemin_csv: str, dossier_modeles: str, dossier_rapports: str, n_iter: int = 15,
              cv: int = 3, recall_cible: float = RECALL_CIBLE, genre: str = "avec",
              reutiliser_params: str = None) -> dict:
    debut = time.time()
    dossier_modeles, dossier_rapports = Path(dossier_modeles), Path(dossier_rapports)
    dossier_modeles.mkdir(parents=True, exist_ok=True)
    dossier_rapports.mkdir(parents=True, exist_ok=True)

    print(f"[1/7] Chargement de {chemin_csv}")
    df = charger_donnees(chemin_csv)
    df_train, df_val, df_test = decouper(df)
    print(f"      train={len(df_train)} val={len(df_val)} test={len(df_test)} | "
          f"fraudes : {int(df_train.est_fraude.sum())} / {int(df_val.est_fraude.sum())} / "
          f"{int(df_test.est_fraude.sum())}")

    tables = tables_de_reference(df_train, df)
    colonnes = liste_colonnes(tables, avec_genre=True)
    X_train, X_val, X_test = (construire_matrice(d, tables, colonnes) for d in (df_train, df_val, df_test))
    X_train, X_val, X_test, scaler = standardiser(X_train, X_val, X_test)
    y_train, y_val, y_test = (d["est_fraude"].astype(int).values for d in (df_train, df_val, df_test))

    if reutiliser_params:
        # Pas de nouvelle recherche : on reprend les hyperparametres d'un entrainement precedent
        print(f"[2/7] Hyperparametres repris de {reutiliser_params} (pas de nouvelle recherche)")
        with open(reutiliser_params, encoding="utf-8") as f:
            sauvegarde = json.load(f)
        params = sauvegarde["hyperparametres"]
        score_cv = sauvegarde.get("pr_auc_cv")
        xgb_final = pipeline_xgboost(**params).fit(X_train, y_train)
    else:
        print(f"[2/7] Recherche d'hyperparametres XGBoost (SMOTE dans le pipeline, "
              f"{n_iter} combinaisons x {cv} plis)")
        recherche = rechercher_hyperparametres(X_train, y_train, n_iter=n_iter, cv=cv)
        params = meilleurs_parametres(recherche)
        score_cv = float(recherche.best_score_)
        xgb_final = recherche.best_estimator_
        with open(dossier_rapports / "hyperparametres.json", "w", encoding="utf-8") as f:
            json.dump({"hyperparametres": params, "pr_auc_cv": score_cv,
                       "n_iter": n_iter, "cv": cv}, f, indent=2)
    print(f"      hyperparametres : {params}")
    if score_cv is not None:
        print(f"      PR-AUC en validation croisee (SMOTE dans les plis) : {score_cv:.4f}")

    print("[3/7] Comparaison des 3 modeles sur la VALIDATION")
    candidats = {
        "Regression logistique": pipeline_logistique().fit(X_train, y_train),
        "Random Forest": pipeline_random_forest().fit(X_train, y_train),
        "XGBoost": xgb_final,
    }
    resultats = {nom: evaluer_configuration(p, X_val, y_val, X_test, y_test, recall_cible)
                 for nom, p in candidats.items()}
    tableau = pd.DataFrame([
        {
            "modele": nom,
            "pr_auc_validation": r["validation"]["pr_auc"],
            "auc_roc_validation": r["validation"]["auc_roc"],
            "seuil_choisi_validation": r["seuil"],
            "recall_validation": r["validation"]["recall"],
            "precision_validation": r["validation"]["precision"],
            "recall_test": r["test"]["recall"],
            "precision_test": r["test"]["precision"],
            "f1_test": r["test"]["f1_score"],
            "auc_roc_test": r["test"]["auc_roc"],
        }
        for nom, r in resultats.items()
    ])
    tableau.to_csv(dossier_rapports / "comparaison_modeles.csv", index=False)
    print(tableau.round(4).to_string(index=False))
    # Selection sur la VALIDATION uniquement (le test ne sert qu'a annoncer)
    nom_retenu = max(resultats, key=lambda n: resultats[n]["validation"]["pr_auc"])
    print(f"      modele retenu (meilleure PR-AUC en validation) : {nom_retenu}")

    print("[4/7] Comparaison avec / sans la variable « genre »")
    pipeline_avec = candidats[nom_retenu]
    importance_genre = part_importance(pipeline_avec.named_steps["clf"], colonnes, "genre")
    colonnes_sg = liste_colonnes(tables, avec_genre=False)
    Xtr_sg, Xva_sg, Xte_sg = X_train[colonnes_sg], X_val[colonnes_sg], X_test[colonnes_sg]
    pipeline_sans = clone(pipeline_avec).fit(Xtr_sg, y_train)
    res_sans = evaluer_configuration(pipeline_sans, Xva_sg, y_val, Xte_sg, y_test, recall_cible)
    res_avec = resultats[nom_retenu]
    comparaison_genre = {
        "modele": nom_retenu,
        "avec_genre": _sans_proba(res_avec),
        "sans_genre": _sans_proba(res_sans),
        "part_importance_genre_pct": importance_genre,
    }
    with open(dossier_rapports / "comparaison_genre.json", "w", encoding="utf-8") as f:
        json.dump(comparaison_genre, f, indent=2, ensure_ascii=False)
    for etiquette, r in (("avec genre", res_avec), ("sans genre", res_sans)):
        t = r["test"]
        print(f"      {etiquette:10s} | test : recall={t['recall']:.3f} precision={t['precision']:.3f} "
              f"f1={t['f1_score']:.3f} auc={t['auc_roc']:.4f} pr_auc={t['pr_auc']:.4f}")

    print(f"[5/7] Configuration exportee : {genre} genre")
    if genre == "sans":
        pipeline_final, colonnes_final, res_final = pipeline_sans, colonnes_sg, res_sans
    else:
        pipeline_final, colonnes_final, res_final = pipeline_avec, colonnes, res_avec
    modele = pipeline_final.named_steps["clf"]  # SMOTE n'intervient qu'a l'entrainement

    print("[6/7] Rapports (matrice de confusion PNG, metriques JSON)")
    png = plot_confusion_matrix(
        y_test, res_final["_proba_test"], res_final["seuil"],
        str(dossier_rapports / "matrice_confusion_test.png"),
        titre=f"{nom_retenu} — matrice de confusion (jeu de test)",
    )
    t = res_final["test"]
    metriques = {
        # Noms alignes sur les champs du modele Django MLModel
        "precision_score": t["precision"],
        "recall_score": t["recall"],
        "f1_score": t["f1_score"],
        "auc_roc": t["auc_roc"],
        "pr_auc": t["pr_auc"],
        "matrice_confusion": t["matrice_confusion"],  # [[TN, FP], [FN, TP]]
        "seuil_decision": res_final["seuil"],
        "date_entrainement": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "jeu_evaluation": "test",
        "seuil_choisi_sur": "validation",
        "recall_cible_validation": recall_cible,
        "intervalle_confiance_95": res_final["test_ic95"],
        "validation": res_final["validation"],
        "algorithme": nom_retenu,
        "variable_genre_utilisee": genre == "avec",
        "hyperparametres": params,
        "pr_auc_validation_croisee": score_cv,
        "effectifs": {"train": len(df_train), "validation": len(df_val), "test": len(df_test)},
        "versions": {
            "python": platform.python_version(), "scikit-learn": sklearn.__version__,
            "xgboost": xgboost.__version__, "imbalanced-learn": imblearn.__version__,
            "pandas": pd.__version__, "numpy": np.__version__,
        },
    }
    with open(dossier_rapports / "metriques.json", "w", encoding="utf-8") as f:
        json.dump(metriques, f, indent=2, ensure_ascii=False)

    print("[7/7] Export du .joblib")
    pipeline_complet = {
        "model": modele,
        "scaler": scaler,
        "colonnes_modele": colonnes_final,
        "colonnes_numeriques": COLONNES_NUMERIQUES,
        "seuil_decision": res_final["seuil"],
        "freq_commercant": tables["freq_commercant"],
        "freq_ville": tables["freq_ville"],
        "freq_profession": tables["freq_profession"],
        "categories_connues": tables["categories_connues"],
        "regions_connues": tables["regions_connues"],
        "metriques": metriques,
    }
    chemin_joblib = dossier_modeles / "fraudguard_pipeline.joblib"
    joblib.dump(pipeline_complet, chemin_joblib)
    print(f"      {chemin_joblib} ({chemin_joblib.stat().st_size / 1e6:.1f} Mo) | "
          f"{png} | duree totale {(time.time() - debut) / 60:.1f} min")
    return pipeline_complet


def export_model(model, path: str):
    """Exporte un objet au format Joblib (API conservee)."""
    joblib.dump(model, path)


def main(argv=None):
    ici = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description="Entrainement FraudGuard")
    p.add_argument("--data", default=str(ici.parent / "data" / "raw" / "fraudTest_senegal.csv"))
    p.add_argument("--sortie-modeles", default=str(ici.parent / "models"))
    p.add_argument("--sortie-rapports", default=str(ici.parent / "reports"))
    p.add_argument("--n-iter", type=int, default=15, help="combinaisons testees par RandomizedSearchCV")
    p.add_argument("--cv", type=int, default=3)
    p.add_argument("--recall-cible", type=float, default=RECALL_CIBLE)
    p.add_argument("--reutiliser-params", default=None,
                   help="fichier hyperparametres.json d'un entrainement precedent (saute la recherche)")
    p.add_argument("--genre", choices=["avec", "sans"], default="avec",
                   help="variable genre dans le modele exporte")
    a = p.parse_args(argv)
    if not Path(a.data).exists():
        sys.exit(f"CSV introuvable : {a.data}\nUtilise --data chemin/vers/fraudTest_senegal.csv")
    entrainer(a.data, a.sortie_modeles, a.sortie_rapports, a.n_iter, a.cv, a.recall_cible, a.genre,
              a.reutiliser_params)


if __name__ == "__main__":
    main()
