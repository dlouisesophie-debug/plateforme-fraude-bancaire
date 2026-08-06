"""
Evaluation des modeles — CDC 6 : Precision/Recall/F1/AUC-ROC (pas
seulement l'accuracy, dataset desequilibre).
"""

from sklearn.metrics import (
    ConfusionMatrixDisplay,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_model(model, X_test, y_test) -> dict:
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    return {
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1_score": f1_score(y_test, y_pred),
        "auc_roc": roc_auc_score(y_test, y_proba),
        "report": classification_report(y_test, y_pred),
    }


def plot_confusion_matrix(model, X_test, y_test):
    """TODO Etudiant 2 : sauvegarder la figure pour le rapport d'evaluation."""
    ConfusionMatrixDisplay.from_estimator(model, X_test, y_test)
