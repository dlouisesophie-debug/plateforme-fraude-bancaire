"""
Entrainement et comparaison des modeles ML (CDC 3.2, Phase 6).

Modeles a comparer : Regression logistique, Random Forest, XGBoost.
Rappel : dataset desequilibre -> utiliser Imbalanced-learn (SMOTE) et
prioriser le Recall sur la classe fraude plutot que l'accuracy seule.
"""

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

# from imblearn.over_sampling import SMOTE
# from xgboost import XGBClassifier


def train_logistic_regression(X_train, y_train):
    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(X_train, y_train)
    return model


def train_random_forest(X_train, y_train):
    model = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=42)
    model.fit(X_train, y_train)
    return model


def train_xgboost(X_train, y_train):
    """TODO Etudiant 2 : implementer avec XGBClassifier + scale_pos_weight."""
    raise NotImplementedError


def export_model(model, path: str):
    """Exporte le modele entraine au format Joblib (CDC 3.2)."""
    joblib.dump(model, path)


if __name__ == "__main__":
    # TODO : charger les donnees pretraitees, split train/test,
    # entrainer les 3 modeles, comparer, exporter le meilleur dans
    # /ml/models/ avec un nom versionne (ex. xgboost_v1.joblib)
    pass
