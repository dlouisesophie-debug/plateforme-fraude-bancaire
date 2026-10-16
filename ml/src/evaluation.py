"""
evaluation.py
=============
Evaluation des modeles — CDC 6 : Precision / Recall / F1 / AUC-ROC (pas
seulement l'accuracy, le dataset est tres desequilibre : ~0,4 % de fraudes).

Toutes les fonctions prennent des PROBABILITES (y_proba) et un SEUIL
explicite : le seuil de decision n'est jamais choisi ici sur le jeu de test
(voir training.py : il est choisi sur le jeu de VALIDATION).
"""

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)


def choisir_seuil(y_val, proba_val, recall_cible: float = 0.85) -> float:
    """
    Choisit le seuil de decision SUR LE JEU DE VALIDATION.

    On prend le seuil le plus eleve (donc la meilleure precision) qui
    garantit encore un rappel >= recall_cible sur la validation.
    Si aucun seuil n'atteint la cible, on prend le seuil au rappel maximal.
    """
    precisions, recalls, seuils = precision_recall_curve(y_val, proba_val)
    # recalls[:-1] et seuils ont la meme longueur ; recalls decroit quand le seuil monte
    ok = np.where(recalls[:-1] >= recall_cible)[0]
    idx = ok[-1] if len(ok) else 0
    return float(seuils[idx])


def evaluer(y_true, y_proba, seuil: float) -> dict:
    """Metriques completes pour un seuil donne."""
    y_true = np.asarray(y_true).ravel()
    y_pred = (np.asarray(y_proba) >= seuil).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "seuil": float(seuil),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred)),
        "f1_score": float(f1_score(y_true, y_pred)),
        "auc_roc": float(roc_auc_score(y_true, y_proba)),
        "pr_auc": float(average_precision_score(y_true, y_proba)),
        # format [[vrais negatifs, faux positifs], [faux negatifs, vrais positifs]]
        "matrice_confusion": [[int(tn), int(fp)], [int(fn), int(tp)]],
        "n_echantillons": int(len(y_true)),
        "n_fraudes": int(y_true.sum()),
    }


def evaluate_model(model, X_test, y_test, seuil: float = 0.5) -> dict:
    """
    Evalue un modele deja entraine (API conservee). Ajoute `report`, le
    classification_report texte, aux metriques de `evaluer`.
    """
    y_proba = model.predict_proba(X_test)[:, 1]
    resultat = evaluer(y_test, y_proba, seuil)
    y_pred = (y_proba >= seuil).astype(int)
    resultat["report"] = classification_report(
        y_test, y_pred, target_names=["Legitime", "Fraude"], digits=3, zero_division=0
    )
    return resultat


def intervalle_confiance_bootstrap(y_true, y_proba, seuil, n_boot: int = 1000,
                                   graine: int = 42) -> dict:
    """
    Intervalle de confiance a 95 % (bootstrap) du rappel et de la precision.
    Utile car le test ne contient qu'environ 430 fraudes : une difference de
    quelques points entre deux modeles peut n'etre que du bruit.
    """
    rng = np.random.default_rng(graine)
    y_true = np.asarray(y_true).ravel()
    y_pred = (np.asarray(y_proba) >= seuil).astype(int)
    n = len(y_true)
    recalls, precisions = [], []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        yt, yp = y_true[idx], y_pred[idx]
        if yt.sum() == 0:
            continue
        recalls.append(recall_score(yt, yp))
        precisions.append(precision_score(yt, yp, zero_division=0))
    return {
        "recall_ic95": [float(np.percentile(recalls, 2.5)), float(np.percentile(recalls, 97.5))],
        "precision_ic95": [float(np.percentile(precisions, 2.5)), float(np.percentile(precisions, 97.5))],
    }


def plot_confusion_matrix(y_true, y_proba, seuil: float, chemin_png: str,
                          titre: str = "Matrice de confusion (jeu de test)") -> str:
    """
    Sauvegarde la matrice de confusion en PNG (pour le rapport/memoire) et
    renvoie le chemin du fichier. Deux panneaux : effectifs et pourcentages
    par ligne (la ligne « Fraude » donne directement le rappel).
    """
    import matplotlib

    matplotlib.use("Agg")  # pas d'ecran necessaire (serveur, CI)
    import matplotlib.pyplot as plt

    y_true = np.asarray(y_true).ravel()
    y_pred = (np.asarray(y_proba) >= seuil).astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    cm_pct = cm / cm.sum(axis=1, keepdims=True) * 100
    etiquettes = ["Legitime", "Fraude"]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    for ax, donnees, fmt, sous_titre in (
        (axes[0], cm, "{:,}", "Effectifs"),
        (axes[1], cm_pct, "{:.1f} %", "% par classe reelle"),
    ):
        im = ax.imshow(donnees, cmap="Blues")
        ax.set_xticks([0, 1], labels=etiquettes)
        ax.set_yticks([0, 1], labels=etiquettes)
        ax.set_xlabel("Classe predite")
        ax.set_ylabel("Classe reelle")
        ax.set_title(sous_titre)
        seuil_couleur = donnees.max() / 2
        for i in range(2):
            for j in range(2):
                ax.text(j, i, fmt.format(donnees[i, j]).replace(",", " "), ha="center", va="center",
                        color="white" if donnees[i, j] > seuil_couleur else "black", fontsize=12)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle(f"{titre} — seuil = {seuil:.4f}")
    fig.tight_layout()
    fig.savefig(chemin_png, dpi=150)
    plt.close(fig)
    return chemin_png
