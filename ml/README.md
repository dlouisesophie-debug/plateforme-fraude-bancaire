# ML — Pipeline de détection de fraude

Responsable : Étudiant 2 (Lead Data Scientist / ML Engineer)

> Branche de travail ML : `feature/ml` (et non `mas-code-gtb`).

## Structure

```
notebooks/    Notebooks d'exploration (historiques : voir la note en tête de chaque notebook)
data/raw/     Données brutes (non versionnées, voir .gitignore) — fraudTest_senegal.csv à placer ici
src/          Code réutilisable : preprocessing, training, evaluation, predict
models/       fraudguard_pipeline.joblib — versionné dans Git (≈ 1 Mo), nécessaire à la CI
reports/      matrice_confusion_test.png, metriques.json, comparaison_modeles.csv, comparaison_genre.json, hyperparametres.json
tests/        Tests du code ML (données synthétiques, aucun CSV requis)
NOTES_SOUTENANCE.md   Réponses préparées aux questions du jury
```

## Données — source et limites (à citer telles quelles dans le mémoire)

Le jeu `fraudTest_senegal.csv` (555 719 transactions, 2 145 fraudes, soit 0,39 %) est **synthétique**,
pas issu d'une vraie banque : les commerçants sont tous préfixés `fraud_`, les adresses et coordonnées GPS
sont américaines (latitudes 20 à 66, longitudes −166 à −68), et les transactions s'étalent du 21 juin au
31 décembre 2020. Les libellés (catégories, régions, prénoms, montants en FCFA) ont été adaptés au Sénégal.
Sa taille correspond au fichier `fraudTest.csv` du jeu Kaggle « Credit Card Transactions Fraud Detection
Dataset » (données simulées avec le générateur Sparkov) : **vérifier et citer précisément cette source
(auteur, URL, licence) avant de la mentionner**. Les performances ci-dessous prouvent que la chaîne ML
fonctionne ; elles ne prouvent pas la performance sur de vraies transactions sénégalaises.

## Méthode

1. **Découpage stratifié** train 60 % / validation 20 % / test 20 % (333 431 / 111 144 / 111 144 lignes).
   Le jeu de test est celui des notebooks précédents (`test_size=0.2, random_state=42`).
2. **Tables de fréquence et StandardScaler** calculés sur le train seul.
3. **SMOTE dans un `imblearn.pipeline.Pipeline`** : jamais appliqué aux données de validation ni de test.
   L'ancienne version l'appliquait avant `RandomizedSearchCV` (fuite de données : rappel CV de 0,9998
   contre 0,80 sur le test). Recherche notée en PR-AUC (15 combinaisons × 3 plis) :
   **PR-AUC en validation croisée = 0,8823**, cohérente avec la validation.
4. **3 modèles comparés sur la validation** (régression logistique, Random Forest, XGBoost) ; retenu :
   XGBoost (meilleure PR-AUC en validation).
5. **Seuil de décision choisi sur la validation** (plus haut seuil gardant un rappel ≥ 85,0 %),
   jamais sur le test. Seuil retenu : **0,0652**.
6. **Métriques finales sur le test**, utilisées une seule fois. Intervalles de confiance à 95 % par bootstrap.

## Résultats (jeu de test, 111 144 transactions dont 429 fraudes)

| Métrique | Valeur | IC 95 % |
|---|---|---|
| Rappel (recall) | **86,9 %** | 83,8 % – 89,9 % |
| Précision | **60,7 %** | 57,0 % – 64,7 % |
| F1 | 0,715 | |
| AUC-ROC | 0,9945 | |
| PR-AUC | 0,8777 | |

Matrice de confusion (voir `reports/matrice_confusion_test.png`) :
373 fraudes détectées, 56 manquées, 241 fausses alertes sur 110 715 transactions légitimes.

### Comparaison des modèles (sélection sur la validation ; test donné à titre indicatif)

| Modèle | PR-AUC validation | AUC validation | Rappel test | Précision test | F1 test | AUC test |
|---|---|---|---|---|---|---|
| Regression logistique | 0,120 | 0,9026 | 85,8 % | 1,1 % | 0,021 | 0,9096 |
| Random Forest | 0,631 | 0,9784 | 85,8 % | 16,6 % | 0,279 | 0,9864 |
| XGBoost | 0,869 | 0,9931 | 87,6 % | 63,3 % | 0,735 | 0,9946 |

## La variable « genre » (RGPD / équité)

Même modèle, mêmes hyperparamètres, seuil choisi par la même méthode (sur la validation).
Part du gain total de XGBoost attribuée à `genre` dans la version « avec » : **4,9 %**.

| Configuration | Seuil | Rappel test (IC 95 %) | Précision test (IC 95 %) | F1 | AUC-ROC | PR-AUC |
|---|---|---|---|---|---|---|
| Avec genre | 0,0583 | 87,6 % (84,7 % – 90,6 %) | 63,3 % (59,3 % – 67,2 %) | 0,735 | 0,9946 | 0,8911 |
| Sans genre | 0,0652 | 86,9 % (83,8 % – 89,9 %) | 60,7 % (57,0 % – 64,7 %) | 0,715 | 0,9945 | 0,8777 |

**Décision : le modèle livré n'utilise PAS la variable `genre`.** Les intervalles de confiance du rappel et de la précision se chevauchent et l'écart d'AUC-ROC est de 0,0001 : la différence n'est pas statistiquement établie. On évite ainsi d'utiliser le sexe du client pour décider d'une alerte (RGPD, équité).

## Limites connues

- **Données synthétiques** (voir plus haut).
- **Le canal de paiement (carte, Mobile Money, virement, en ligne) n'est pas une variable du modèle** :
  le jeu de données n'a pas de colonne « canal », et `preprocessing.py` n'utilise aucune information de canal.
  Changer le canal ne change donc pas le score. Piste : collecter des données par canal,
  l'ajouter dans `preprocessing.py`, réentraîner.
- Un seul découpage train/validation/test : avec ~430 fraudes en test, des écarts de quelques points
  sont dans le bruit (voir les intervalles de confiance).
- Le modèle exporté est entraîné sur le train seul (pas de réentraînement sur train + validation) pour
  que le seuil reste valide.

## Réentraîner

Utiliser les versions de `requirements.txt` (Python 3.12), identiques à celles du backend Docker :
un `.joblib` produit avec d'autres versions peut déclencher des erreurs de chargement dans le backend.

```bash
cd ml
python -m venv venv
venv\Scripts\activate            # Linux/macOS : source venv/bin/activate
pip install -r requirements.txt
cd src
python training.py --data ../data/raw/fraudTest_senegal.csv          # ≈ 25 min (recherche complète)
python training.py --data ../data/raw/fraudTest_senegal.csv --reutiliser-params ../reports/hyperparametres.json --genre sans   # ≈ 10 min
```

Le script écrit `models/fraudguard_pipeline.joblib` (avec le dictionnaire `metriques`) et les fichiers de
`reports/`. Environnement du dernier entraînement : Python 3.12.3, scikit-learn 1.4.2,
xgboost 2.0.3, imbalanced-learn 0.12.2, pandas 2.2.2, numpy 1.26.4.
Date d'entraînement : 2026-10-16T14:12:32+00:00.

## Tests

```bash
cd ml
python -m unittest discover -s tests -v
```

## Lien avec le backend

`src/preprocessing.py` est la **seule** source de vérité du prétraitement : le backend
(`backend/fraud_detection/services.py`) l'importe, `training.py` en utilise `haversine_distance` et un test
vérifie que la version vectorisée de l'entraînement donne exactement les mêmes variables que le scoring.

Après un nouvel entraînement : commiter `models/fraudguard_pipeline.joblib` et `reports/`, puis réactiver le modèle
côté backend avec `python manage.py activer_modele_ml fraudguard_pipeline.joblib --modele-version <n>`.
Le `.joblib` contient un dictionnaire `metriques` (précision, rappel, F1, AUC, matrice de confusion, seuil,
date d'entraînement) destiné à la page « Modèle IA » ; le backend actuel ignore cette clé sans erreur.
