"""
training_mobile_money.py
========================
Entrainement du modele MOBILE MONEY (jeu PaySim), avec EXACTEMENT la meme methode
que le modele carte (training.py) :

1. Decoupage stratifie train 60 % / validation 20 % / test 20 % (random_state=42).
2. StandardScaler ajuste sur le TRAIN uniquement.
3. SMOTE DANS un imblearn.pipeline.Pipeline (jamais applique a la validation).
4. 3 modeles compares sur la VALIDATION (regression logistique, Random Forest,
   XGBoost optimise par RandomizedSearchCV note en PR-AUC).
5. UN SEUL seuil de decision, choisi sur la VALIDATION (rappel >= 85 %),
   jamais sur le test.
6. Metriques finales sur le TEST, utilisees une seule fois, avec intervalles de
   confiance a 95 % (bootstrap).
7. Comparaison avec une REGLE SIMPLE (type a risque + montant >= seuil, seuil
   choisi sur la validation avec la meme cible de rappel).
8. Export du .joblib (cle « famille » = mobile_money) + rapports.

Variables : voir preprocessing_mobile_money.py (type d'operation, montant,
heure). Les colonnes de soldes, les identifiants et isFlaggedFraud ne sont
meme pas lus dans le CSV.

Usage (depuis le dossier ml/src) :

    python training_mobile_money.py --data ../data/raw/PS_20174392719_1491204439457_log.csv

Memoire (8 Go de RAM) : PaySim compte ~6,36 millions de lignes. Option
--max-train N : le jeu d'ENTRAINEMENT est reduit a N lignes en gardant TOUTES
les fraudes et un echantillon aleatoire des transactions legitimes. La validation
et le test ne sont jamais reduits. Cette reduction est ecrite dans metriques.json.
"""

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import imblearn
import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.preprocessing import StandardScaler

try:  # execution directe : python training_mobile_money.py (depuis ml/src)
    from evaluation import choisir_seuil, evaluer, plot_confusion_matrix, intervalle_confiance_bootstrap
    from preprocessing_mobile_money import (
        COLONNES_MODELE, COLONNES_NUMERIQUES, COLONNES_PAYSIM_LUES, FAMILLE, TYPES_FR,
        construire_matrice, preparer_paysim,
    )
    from training import (
        GRAINE, RECALL_CIBLE, decouper, evaluer_configuration,
        meilleurs_parametres, pipeline_logistique, pipeline_random_forest,
        pipeline_xgboost, rechercher_hyperparametres,
    )
except ImportError:  # pragma: no cover - utilisation comme package
    from .evaluation import choisir_seuil, evaluer, plot_confusion_matrix, intervalle_confiance_bootstrap
    from .preprocessing_mobile_money import (
        COLONNES_MODELE, COLONNES_NUMERIQUES, COLONNES_PAYSIM_LUES, FAMILLE, TYPES_FR,
        construire_matrice, preparer_paysim,
    )
    from .training import (
        GRAINE, RECALL_CIBLE, decouper, evaluer_configuration,
        meilleurs_parametres, pipeline_logistique, pipeline_random_forest,
        pipeline_xgboost, rechercher_hyperparametres,
    )

NOM_JOBLIB = "fraudguard_mobile_money_pipeline.joblib"
MAX_TRAIN_DEFAUT = 500_000
TAUX_FRAUDE_SCENARIOS = [0.0005, 0.001, 0.005, 0.01]
CIBLES_TABLEAU = [0.30, 0.50, 0.60, 0.70, 0.85]


# --------------------------------------------------------------------------
# 1. Donnees
# --------------------------------------------------------------------------
def charger_paysim(chemin_csv: str) -> pd.DataFrame:
    """
    Lit UNIQUEMENT les colonnes autorisees (step, type, amount, isFraud) : les
    soldes, les identifiants et isFlaggedFraud ne sont jamais charges en memoire.
    """
    df = pd.read_csv(chemin_csv, usecols=COLONNES_PAYSIM_LUES)
    return preparer_paysim(df)


def reduire_train(df_train: pd.DataFrame, max_train, graine: int = GRAINE):
    """
    Reduit le jeu d'ENTRAINEMENT (jamais validation / test) a max_train lignes :
    toutes les fraudes + un echantillon aleatoire de transactions legitimes.
    Renvoie (df_reduit, description) ; description vaut None si rien n'a ete reduit.
    """
    if max_train is None or len(df_train) <= max_train:
        return df_train, None
    fraudes = df_train[df_train["est_fraude"] == 1]
    legitimes = df_train[df_train["est_fraude"] == 0]
    n_legit = max(int(max_train) - len(fraudes), 0)
    legitimes = legitimes.sample(n=min(n_legit, len(legitimes)), random_state=graine)
    reduit = pd.concat([fraudes, legitimes]).sample(frac=1.0, random_state=graine)
    return reduit, {
        "applique": True,
        "lignes_train_avant": int(len(df_train)),
        "lignes_train_apres": int(len(reduit)),
        "fraudes_conservees": int(len(fraudes)),
        "legitimes_conservees": int(len(legitimes)),
        "validation_et_test_reduits": False,
    }


# --------------------------------------------------------------------------
# 2. Regle simple de comparaison et sensibilite au taux de fraude
# --------------------------------------------------------------------------
def types_avec_fraude(df_train: pd.DataFrame) -> list:
    """Types d'operation qui contiennent au moins une fraude, calcules sur le TRAIN."""
    return sorted(df_train.loc[df_train["est_fraude"] == 1, "type_operation"].unique().tolist())


def score_regle(df: pd.DataFrame, types_a_risque: list) -> np.ndarray:
    """Score de la regle simple : le montant si le type est a risque, sinon 0."""
    return df["montant"].where(df["type_operation"].isin(types_a_risque), 0.0).to_numpy(float)


def evaluer_regle_simple(df_train, df_val, df_test, recall_cible: float = RECALL_CIBLE) -> dict:
    """
    Regle : « operation d'un type a risque ET montant >= S ». Les types a risque
    viennent du train ; S est choisi sur la VALIDATION (meme cible de rappel que le
    modele). Metriques annoncees sur le test.
    """
    types = types_avec_fraude(df_train)
    s_val, s_test = score_regle(df_val, types), score_regle(df_test, types)
    y_val, y_test = df_val["est_fraude"].to_numpy(int), df_test["est_fraude"].to_numpy(int)
    seuil_montant = choisir_seuil(y_val, s_val, recall_cible)
    return {
        "description": f"type dans {types} et montant >= {seuil_montant:.2f} (unites du simulateur)",
        "types_a_risque": types,
        "seuil_montant": seuil_montant,
        "validation": evaluer(y_val, s_val, seuil_montant),
        "test": evaluer(y_test, s_test, seuil_montant),
    }


def evaluer_types_a_risque(df_test: pd.DataFrame, proba_test, seuil: float, types_a_risque: list) -> dict:
    """
    Memes predictions, meme seuil, mais en ne gardant du test que les operations des
    types ou la fraude existe (Transfert + Retrait). Le rappel est identique (aucune
    fraude hors de ces types) ; la precision et le taux de fausses alertes sont ceux
    d'une population SANS les types qui ne peuvent pas etre frauduleux : ils ne sont
    donc pas « artificiellement bas ». Le seuil n'est pas re-choisi.
    """
    masque = df_test["type_operation"].isin(types_a_risque).to_numpy()
    y = df_test["est_fraude"].to_numpy(int)[masque]
    m = evaluer(y, np.asarray(proba_test)[masque], seuil)
    m["types"] = list(types_a_risque)
    m["fraudes_hors_types"] = int(df_test["est_fraude"].to_numpy(int)[~masque].sum())
    return m


def precision_a_taux_de_fraude(recall: float, taux_faux_positifs: float, taux_fraude: float) -> float:
    """
    Precision attendue si le taux de fraude reel etait `taux_fraude`, pour un modele
    de meme rappel et de meme taux de faux positifs :
        precision = TP / (TP + FP), TP = rappel x pi, FP = FPR x (1 - pi).
    Le rappel et le FPR ne dependent pas du taux de fraude ; la precision, si.
    """
    tp = recall * taux_fraude
    fp = taux_faux_positifs * (1.0 - taux_fraude)
    return float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0


def sensibilite_precision(metriques_test: dict, scenarios=None) -> dict:
    (tn, fp), (fn, tp) = metriques_test["matrice_confusion"]
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    taux_observe = metriques_test["n_fraudes"] / metriques_test["n_echantillons"]
    resultat = {"taux_fraude_observe": taux_observe, "taux_faux_positifs": fpr,
                "recall": metriques_test["recall"], "precision_selon_taux": {}}
    for pi in [taux_observe] + list(scenarios or TAUX_FRAUDE_SCENARIOS):
        resultat["precision_selon_taux"][f"{pi:.5f}"] = precision_a_taux_de_fraude(
            metriques_test["recall"], fpr, pi)
    return resultat


# --------------------------------------------------------------------------
# 2 bis. Changer le point de fonctionnement (sans reentrainer)
# --------------------------------------------------------------------------
def _probabilites(pipeline: dict, df: pd.DataFrame) -> np.ndarray:
    """Probabilites de fraude du modele exporte (memes variables que l'entrainement)."""
    X = construire_matrice(df[["type_operation", "montant", "heure_transaction", "est_fraude"]]).copy()
    X[pipeline["colonnes_numeriques"]] = pipeline["scaler"].transform(X[pipeline["colonnes_numeriques"]])
    return pipeline["model"].predict_proba(X[pipeline["colonnes_modele"]])[:, 1]


def tableau_compromis_validation(y_val, p_val, risque_val, cibles=None) -> list:
    """
    Pour plusieurs rappels vises, le seuil choisi SUR LA VALIDATION et ses effets
    mesures sur la validation : c'est ce tableau qui sert a choisir un point, jamais le test.
    """
    y_val = np.asarray(y_val).ravel()
    lignes = []
    for cible in cibles or CIBLES_TABLEAU:
        seuil = choisir_seuil(y_val, p_val, cible)
        pred = np.asarray(p_val) >= seuil
        tp = int((pred & (y_val == 1)).sum())
        fp = int((pred & (y_val == 0)).sum())
        fn = int(((~pred) & (y_val == 1)).sum())
        lignes.append({
            "rappel_vise": cible, "seuil": float(seuil),
            "rappel": tp / (tp + fn) if (tp + fn) else 0.0,
            "precision": tp / (tp + fp) if (tp + fp) else 0.0,
            "fraudes_trouvees": tp, "fausses_alertes": fp, "fraudes_manquees": fn,
            "part_operations_alertees": float(pred.mean()),
            "part_transferts_retraits_alertes": float(pred[np.asarray(risque_val)].mean()),
        })
    return lignes


def changer_point_de_fonctionnement(chemin_joblib: str, chemin_csv: str, dossier_rapports: str,
                                    recall_cible: float, chemin_sortie: str = None,
                                    df_precharge: pd.DataFrame = None) -> dict:
    """
    Re-choisit le seuil d'un modele DEJA entraine pour un autre rappel vise, SANS le
    reentrainer (les poids ne changent pas) :
      1. le seuil est choisi sur la VALIDATION (choisir_seuil, rappel >= recall_cible) ;
      2. le TEST est mesure une seule fois, pour ce seuil ;
      3. le .joblib (seuil_decision + metriques) et les rapports sont reecrits.
    L'ancien point est conserve dans metriques["point_initial"].
    """
    pipeline = joblib.load(chemin_joblib)
    if pipeline.get("famille") != FAMILLE:
        raise ValueError(f"{chemin_joblib} n'est pas un modele {FAMILLE!r}")
    dossier_rapports = Path(dossier_rapports)
    dossier_rapports.mkdir(parents=True, exist_ok=True)

    df = df_precharge if df_precharge is not None else charger_paysim(chemin_csv)
    df_train, df_val, df_test = decouper(df)
    p_val, p_test = _probabilites(pipeline, df_val), _probabilites(pipeline, df_test)
    y_val, y_test = df_val["est_fraude"].to_numpy(int), df_test["est_fraude"].to_numpy(int)

    seuil = choisir_seuil(y_val, p_val, recall_cible)           # 1. sur la validation
    val_m = evaluer(y_val, p_val, seuil)
    test_m = evaluer(y_test, p_test, seuil)                      # 2. test : une seule fois
    ic = intervalle_confiance_bootstrap(y_test, p_test, seuil)
    regle = evaluer_regle_simple(df_train, df_val, df_test, recall_cible)
    types = regle["types_a_risque"]
    ev_tr = evaluer_types_a_risque(df_test, p_test, seuil, types)
    risque_val = df_val["type_operation"].isin(types).to_numpy()

    ancien = pipeline["metriques"]
    m = dict(ancien)
    m.setdefault("point_initial", {
        "recall_cible_validation": ancien["recall_cible_validation"],
        "seuil_decision": ancien["seuil_decision"],
        "test": {"precision": ancien["precision_score"], "recall": ancien["recall_score"],
                 "f1_score": ancien["f1_score"], "auc_roc_toutes_operations": ancien["auc_roc"],
                 "matrice_confusion": ancien["matrice_confusion"]},
    })
    m.update({
        "seuil_decision": float(seuil),
        "recall_cible_validation": recall_cible,
        "seuil_choisi_sur": "validation",
        "jeu_evaluation": "test",
        "precision_score": test_m["precision"],
        "recall_score": test_m["recall"],
        "f1_score": test_m["f1_score"],
        # AUC affichee dans l'application : celle des operations ou la fraude existe
        "auc_roc": ev_tr["auc_roc"],
        "auc_roc_perimetre": "Transfert + Retrait",
        "auc_roc_toutes_operations": test_m["auc_roc"],
        "pr_auc": test_m["pr_auc"],
        "matrice_confusion": test_m["matrice_confusion"],  # [[TN, FP], [FN, TP]], toutes operations
        "intervalle_confiance_95": ic,
        "validation": val_m,
        "regle_simple": {k: v for k, v in regle.items() if k != "validation"},
        "sensibilite_precision_au_taux_de_fraude": sensibilite_precision(test_m),
        "evaluation_transfert_retrait": ev_tr,
        "tableau_compromis_validation": tableau_compromis_validation(y_val, p_val, risque_val),
        "date_choix_du_seuil": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    pipeline["seuil_decision"] = float(seuil)
    pipeline["metriques"] = m

    sortie = chemin_sortie or chemin_joblib
    joblib.dump(pipeline, sortie)
    with open(dossier_rapports / "metriques.json", "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2, ensure_ascii=False)
    with open(dossier_rapports / "regle_simple.json", "w", encoding="utf-8") as f:
        json.dump(regle, f, indent=2, ensure_ascii=False)
    pd.DataFrame(m["tableau_compromis_validation"]).to_csv(
        dossier_rapports / "compromis_validation.csv", index=False)
    plot_confusion_matrix(
        y_test, p_test, seuil, str(dossier_rapports / "matrice_confusion_test.png"),
        titre=f"Mobile Money - {m['algorithme']} - matrice de confusion (jeu de test)")
    print(f"Point de fonctionnement : rappel vise {recall_cible:.0%} (validation) -> seuil {seuil:.4f} | "
          f"test : rappel {test_m['recall']:.1%}, precision {test_m['precision']:.1%} | "
          f"AUC Transfert+Retrait {ev_tr['auc_roc']:.3f} | ecrit dans {sortie}")
    return pipeline


# --------------------------------------------------------------------------
# 3. Programme principal
# --------------------------------------------------------------------------
def entrainer(chemin_csv: str, dossier_modeles: str, dossier_rapports: str, n_iter: int = 15,
              cv: int = 3, recall_cible: float = RECALL_CIBLE, max_train=MAX_TRAIN_DEFAUT,
              reutiliser_params: str = None, df_precharge: pd.DataFrame = None) -> dict:
    debut = time.time()
    dossier_modeles, dossier_rapports = Path(dossier_modeles), Path(dossier_rapports)
    dossier_modeles.mkdir(parents=True, exist_ok=True)
    dossier_rapports.mkdir(parents=True, exist_ok=True)

    print(f"[1/6] Chargement de {chemin_csv} (colonnes lues : {COLONNES_PAYSIM_LUES})")
    df = df_precharge if df_precharge is not None else charger_paysim(chemin_csv)
    df_train_complet, df_val, df_test = decouper(df)
    print(f"      train={len(df_train_complet)} val={len(df_val)} test={len(df_test)} | fraudes : "
          f"{int(df_train_complet.est_fraude.sum())} / {int(df_val.est_fraude.sum())} / "
          f"{int(df_test.est_fraude.sum())}")
    fraudes_par_type = (df_train_complet.groupby("type_operation")["est_fraude"].sum()
                        .astype(int).to_dict())
    print(f"      fraudes par type (train) : {fraudes_par_type}")

    # Scaler ajuste sur le TRAIN COMPLET (distribution reelle), puis reduction du train
    X_train_complet = construire_matrice(df_train_complet[["type_operation", "montant",
                                                           "heure_transaction", "est_fraude"]])
    scaler = StandardScaler().fit(X_train_complet[COLONNES_NUMERIQUES])
    df_train, reduction = reduire_train(df_train_complet, max_train)
    if reduction:
        print(f"      train reduit : {reduction['lignes_train_avant']} -> "
              f"{reduction['lignes_train_apres']} lignes (toutes les fraudes gardees)")

    def matrice(d):
        X = construire_matrice(d[["type_operation", "montant", "heure_transaction", "est_fraude"]])
        X = X.copy()
        X[COLONNES_NUMERIQUES] = scaler.transform(X[COLONNES_NUMERIQUES])
        return X

    X_train, X_val, X_test = matrice(df_train), matrice(df_val), matrice(df_test)
    y_train, y_val, y_test = (d["est_fraude"].astype(int).to_numpy()
                              for d in (df_train, df_val, df_test))

    if reutiliser_params:
        print(f"[2/6] Hyperparametres repris de {reutiliser_params} (pas de nouvelle recherche)")
        with open(reutiliser_params, encoding="utf-8") as f:
            sauvegarde = json.load(f)
        params = sauvegarde["hyperparametres"]
        score_cv = sauvegarde.get("pr_auc_cv")
        xgb_final = pipeline_xgboost(**params).fit(X_train, y_train)
    else:
        print(f"[2/6] Recherche d'hyperparametres XGBoost (SMOTE dans le pipeline, "
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

    print("[3/6] Comparaison des 3 modeles + regle simple sur la VALIDATION")
    candidats = {
        "Regression logistique": pipeline_logistique().fit(X_train, y_train),
        "Random Forest": pipeline_random_forest().fit(X_train, y_train),
        "XGBoost": xgb_final,
    }
    resultats = {nom: evaluer_configuration(p, X_val, y_val, X_test, y_test, recall_cible)
                 for nom, p in candidats.items()}
    regle = evaluer_regle_simple(df_train_complet, df_val, df_test, recall_cible)
    lignes = [{
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
    } for nom, r in resultats.items()]
    lignes.append({
        "modele": "Regle simple (type a risque + montant)",
        "pr_auc_validation": regle["validation"]["pr_auc"],
        "auc_roc_validation": regle["validation"]["auc_roc"],
        "seuil_choisi_validation": regle["seuil_montant"],
        "recall_validation": regle["validation"]["recall"],
        "precision_validation": regle["validation"]["precision"],
        "recall_test": regle["test"]["recall"],
        "precision_test": regle["test"]["precision"],
        "f1_test": regle["test"]["f1_score"],
        "auc_roc_test": regle["test"]["auc_roc"],
    })
    tableau = pd.DataFrame(lignes)
    tableau.to_csv(dossier_rapports / "comparaison_modeles.csv", index=False)
    print(tableau.round(4).to_string(index=False))
    with open(dossier_rapports / "regle_simple.json", "w", encoding="utf-8") as f:
        json.dump(regle, f, indent=2, ensure_ascii=False)

    # Selection sur la VALIDATION uniquement (le test ne sert qu'a annoncer)
    nom_retenu = max(resultats, key=lambda n: resultats[n]["validation"]["pr_auc"])
    res = resultats[nom_retenu]
    pipeline_final = candidats[nom_retenu]
    modele = pipeline_final.named_steps["clf"]  # SMOTE n'intervient qu'a l'entrainement
    print(f"      modele retenu (meilleure PR-AUC en validation) : {nom_retenu}")

    print("[4/6] Rapports (matrice de confusion PNG, metriques JSON)")
    png = plot_confusion_matrix(
        y_test, res["_proba_test"], res["seuil"],
        str(dossier_rapports / "matrice_confusion_test.png"),
        titre=f"Mobile Money - {nom_retenu} - matrice de confusion (jeu de test)",
    )
    t = res["test"]
    sensibilite = sensibilite_precision(t)
    metriques = {
        "famille": FAMILLE,
        # Noms alignes sur les champs du modele Django MLModel
        "precision_score": t["precision"],
        "recall_score": t["recall"],
        "f1_score": t["f1_score"],
        "auc_roc": t["auc_roc"],
        "pr_auc": t["pr_auc"],
        "matrice_confusion": t["matrice_confusion"],  # [[TN, FP], [FN, TP]]
        "seuil_decision": res["seuil"],
        "date_entrainement": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "jeu_evaluation": "test",
        "seuil_choisi_sur": "validation",
        "recall_cible_validation": recall_cible,
        "intervalle_confiance_95": res["test_ic95"],
        "validation": res["validation"],
        "algorithme": nom_retenu,
        "hyperparametres": params,
        "pr_auc_validation_croisee": score_cv,
        "variables": COLONNES_MODELE,
        "colonnes_non_lues": ["nameOrig", "nameDest", "oldbalanceOrg", "newbalanceOrig",
                              "oldbalanceDest", "newbalanceDest", "isFlaggedFraud"],
        "colonne_lue_non_utilisee_comme_variable": {
            "step": "indice de temps brut ; sert uniquement a calculer l'heure (step modulo 24)"},
        "fraudes_par_type_train": fraudes_par_type,
        "regle_simple": {k: v for k, v in regle.items() if k != "validation"},
        "sensibilite_precision_au_taux_de_fraude": sensibilite,
        "evaluation_transfert_retrait": evaluer_types_a_risque(
            df_test, res["_proba_test"], res["seuil"], regle["types_a_risque"]),
        "reduction_train": reduction or {"applique": False},
        "source_donnees": "PaySim (Lopez-Rojas, Elmir, Axelsson, EMSS 2016) - Kaggle ealaxi/paysim1",
        "montants_en_unite_simulateur": True,
        "effectifs": {"train_complet": len(df_train_complet), "train_utilise": len(df_train),
                      "validation": len(df_val), "test": len(df_test)},
        "versions": {
            "python": platform.python_version(), "scikit-learn": sklearn.__version__,
            "xgboost": xgboost.__version__, "imbalanced-learn": imblearn.__version__,
            "pandas": pd.__version__, "numpy": np.__version__,
        },
    }
    with open(dossier_rapports / "metriques.json", "w", encoding="utf-8") as f:
        json.dump(metriques, f, indent=2, ensure_ascii=False)

    print("[5/6] Export du .joblib")
    pipeline_complet = {
        "famille": FAMILLE,
        "model": modele,
        "scaler": scaler,
        "colonnes_modele": COLONNES_MODELE,
        "colonnes_numeriques": COLONNES_NUMERIQUES,
        "seuil_decision": res["seuil"],
        "types_connus": TYPES_FR,
        "metriques": metriques,
    }
    chemin_joblib = dossier_modeles / NOM_JOBLIB
    joblib.dump(pipeline_complet, chemin_joblib)
    print(f"[6/6] {chemin_joblib} ({chemin_joblib.stat().st_size / 1e6:.1f} Mo) | {png} | "
          f"duree totale {(time.time() - debut) / 60:.1f} min")
    return pipeline_complet


def main(argv=None):
    ici = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description="Entrainement FraudGuard - modele Mobile Money (PaySim)")
    p.add_argument("--data", default=str(ici.parent / "data" / "raw" / "PS_20174392719_1491204439457_log.csv"))
    p.add_argument("--sortie-modeles", default=str(ici.parent / "models"))
    p.add_argument("--sortie-rapports", default=str(ici.parent / "reports" / "mobile_money"))
    p.add_argument("--n-iter", type=int, default=15, help="combinaisons testees par RandomizedSearchCV")
    p.add_argument("--cv", type=int, default=3)
    p.add_argument("--recall-cible", type=float, default=RECALL_CIBLE)
    p.add_argument("--max-train", type=int, default=MAX_TRAIN_DEFAUT,
                   help="taille max du jeu d'ENTRAINEMENT (toutes les fraudes gardees ; "
                        "validation et test jamais reduits). 0 = pas de reduction.")
    p.add_argument("--rechoisir-seuil", type=float, default=None, metavar="RAPPEL",
                   help="NE REENTRAINE PAS : re-choisit sur la validation le seuil du modele deja exporte "
                        "pour ce rappel vise (ex. 0.5), mesure le test une fois et reecrit .joblib + rapports")
    p.add_argument("--reutiliser-params", default=None,
                   help="fichier hyperparametres.json d'un entrainement precedent (saute la recherche)")
    a = p.parse_args(argv)
    if not Path(a.data).exists():
        sys.exit(f"CSV introuvable : {a.data}\nUtilise --data chemin/vers/le_fichier_paysim.csv")
    if a.rechoisir_seuil is not None:
        changer_point_de_fonctionnement(str(Path(a.sortie_modeles) / NOM_JOBLIB), a.data,
                                        a.sortie_rapports, a.rechoisir_seuil)
        return
    entrainer(a.data, a.sortie_modeles, a.sortie_rapports, a.n_iter, a.cv, a.recall_cible,
              a.max_train or None, a.reutiliser_params)


if __name__ == "__main__":
    main()
