# ML — Pipeline de détection de fraude

Responsable : Étudiant 2 (Lead Data Scientist / ML Engineer)

> Branche de travail ML : `feature/ml` (et non `mas-code-gtb`).

## Structure

```
notebooks/    Notebooks d'exploration (historiques : la version de référence est src/training.py)
data/raw/     Données brutes (non versionnées, voir .gitignore) — fraudTest_senegal.csv à placer ici
src/          Code réutilisable : preprocessing, training, evaluation, predict (+ modèle Mobile Money)
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

## Modèle Mobile Money (PaySim)

Deuxième modèle, entraîné **séparément** du modèle carte, avec la même méthode (voir « Méthode »)
mais ses propres fichiers, variables et seuil. Le modèle carte n'est pas modifié.

| | |
|---|---|
| Données | PaySim, simulateur de transactions Mobile Money (Lopez-Rojas, Elmir, Axelsson, EMSS 2016) ; Kaggle `ealaxi/paysim1`. **Licence : CC BY-SA 4.0** (indiquée sur la page Kaggle du jeu, consultée le 16/11/2026). Auteur sur Kaggle : Edgar Lopez-Rojas. Les données brutes ne sont pas versionnées (`ml/data/raw/`) et ne sont pas redistribuées dans ce dépôt. Données simulées, montants en unité du simulateur (pas des FCFA). |
| Variables (contrat de données) | type d'opération (Dépôt, Retrait, Transfert, Paiement, Débit), montant, heure (0 à 23) |
| Colonnes jamais lues | les 4 colonnes de soldes, `nameOrig`, `nameDest`, `isFlaggedFraud` |
| Colonne lue mais pas utilisée comme variable | `step` brut (indice de temps des 30 jours de simulation) : sert uniquement à calculer l'heure, heure = `step` modulo 24 |
| Code | `src/preprocessing_mobile_money.py`, `src/training_mobile_money.py`, `src/predict.py` (clé `famille`) |
| Fichier modèle | `models/fraudguard_mobile_money_pipeline.joblib` (clé `famille` = `mobile_money`) |
| Valeurs acceptées pour le type d'opération | libellés français (Dépôt, Retrait, Transfert, Paiement, Débit — ou « Débit vers un compte bancaire »), ou valeurs internes PaySim (CASH_IN, CASH_OUT, TRANSFER, PAYMENT, DEBIT) |
| Rapports | `reports/mobile_money/` (métriques, matrice de confusion, comparaison avec une règle simple) |
| Tests | `tests/test_mobile_money.py` |

Entraîner (depuis `ml/src`, avec le CSV PaySim placé dans `data/raw/`) :

```
python training_mobile_money.py --data ../data/raw/PS_20174392719_1491204439457_log.csv
```

Option `--max-train N` (500 000 par défaut) : réduit **uniquement** le jeu d'entraînement (toutes les
fraudes gardées, échantillon des transactions légitimes) pour tenir dans 8 Go de RAM ; la validation et
le test ne sont jamais réduits. La réduction appliquée est écrite dans `metriques.json`.

### Résultats (jeu de test : 1 272 524 transactions dont 1 643 fraudes, soit 0,13 %)

Modèle retenu : **XGBoost** (meilleure PR-AUC en validation). Un seul seuil, choisi sur la validation au
**point à 50 % de rappel : 0,9307** (décision de l'équipe après lecture du tableau des compromis ci-dessous).
Entraînement sur 500 000 lignes (toutes les fraudes + un échantillon de transactions légitimes) ;
validation et test intacts. Le point initial (rappel ≥ 85 %, seuil 0,5133) est conservé comme comparaison.

| Test, seuil 0,9307 | Valeur | IC 95 % |
|---|---|---|
| Rappel | 47,1 % | 44,7 – 49,6 % |
| Précision | 12,5 % | 11,7 – 13,3 % |
| F1 | 0,197 | |
| AUC-ROC (Transfert + Retrait) | 0,882 | |
| AUC-ROC (toutes opérations) | 0,949 | |
| PR-AUC | 0,323 | |

Matrice de confusion : 1 265 437 vrais négatifs, **5 444 faux positifs**, 869 faux négatifs, 774 vrais
positifs. À ce seuil, environ **7 alertes pour une vraie fraude** (contre 100 au point à 85 %). Le rappel
mesuré sur le test (47,1 %) est un peu sous la cible de 50 % fixée sur la validation : c'est normal.
Point initial à 85 % (seuil 0,5133) : rappel 84,9 %, précision 0,98 %, 140 523 fausses alertes.

Comparaison (validation, sélection sur la PR-AUC) : régression logistique 0,022 ; Random Forest 0,336 ;
**XGBoost 0,341** ; règle simple (type Transfert ou Retrait et montant ≥ 59 628) 0,021.
Le modèle fait bien mieux que la règle simple (précision 0,98 % contre 0,31 % au même rappel).

Compromis rappel / précision (`reports/mobile_money/compromis_validation.csv`). **Calculé sur la VALIDATION** (1 272 524 opérations, 1 642 fraudes), car
c'est sur la validation qu'on choisit un point de fonctionnement ; le test n'est mesuré qu'une fois, pour le
point retenu (tableau ci-dessus) :

| Rappel visé | Seuil | Rappel | Précision | Fraudes trouvées | Fausses alertes | Opérations alertées | Transferts + retraits alertés |
|---|---|---|---|---|---|---|---|
| 30 % | 0,9950 | 30,1 % | 59,4 % | 494 | 338 | 0,07 % | 0,15 % |
| **50 % (retenu)** | **0,9307** | **50,0 %** | **12,8 %** | **821** | **5 588** | **0,50 %** | **1,15 %** |
| 60 % | 0,8559 | 60,1 % | 4,7 % | 987 | 20 205 | 1,67 % | 3,82 % |
| 70 % | 0,7472 | 70,0 % | 2,3 % | 1 150 | 49 234 | 3,96 % | 9,08 % |
| 85 % (point initial) | 0,5133 | 85,0 % | 0,98 % | 1 396 | 140 469 | 11,15 % | 25,56 % |

Changer de point de fonctionnement = choisir une autre ligne **sur la validation**, puis mesurer le test
une seule fois pour ce point. Les résultats du test ne servent jamais à choisir. (Transparence : dans une version précédente du document, des chiffres de test avaient été affichés pour plusieurs points ; le tableau ci-dessus est désormais calculé sur la validation uniquement.)

La précision est faible parce que le contrat de données ne retient que trois variables (type, montant,
heure) : les colonnes de soldes, qui trahissent la fraude dans PaySim, sont volontairement exclues. Un
rappel plus bas donne une précision bien meilleure ; le choix du point de fonctionnement est une décision
métier, pas seulement technique.

**Sur les seules opérations où la fraude existe (Transfert + Retrait).** Aucune fraude n'existe dans
les Dépôts, Paiements et Débits, et le modèle n'y déclenche **aucune alerte** (0 sur 718 804 opérations).
Ces opérations gonflent donc artificiellement la part de transactions « bien classées ». Même seuil
(0,9307), test restreint à Transfert + Retrait (552 077 + 1 643 = 553 720 opérations) :

| | Toutes opérations | Transfert + Retrait seuls |
|---|---|---|
| Rappel | 47,1 % | 47,1 % (identique) |
| Précision | 12,5 % | 12,5 % (identique) |
| Légitimes signalées à tort | 0,43 % | **0,99 %** |
| AUC-ROC | 0,949 | **0,882** |

C'est l'AUC de la seconde colonne (0,882) qui est affichée sur la page « Modèle IA ». Détails :
`reports/mobile_money/metriques.json`, clé `evaluation_transfert_retrait`.

Constats d'exploration : la fraude n'existe que dans les opérations **Transfert** (0,77 % des transferts)
et **Retrait** (0,18 %) ; aucun Dépôt, Paiement ni Débit n'est frauduleux. Les fraudes ont des montants
plus élevés (médiane 441 423 contre 74 685) et sont réparties **uniformément sur les 24 heures**, alors
que l'activité légitime du simulateur se concentre entre 9 h et 21 h (quasi nulle entre 2 h et 8 h) :
c'est une propriété du simulateur, pas un comportement de fraudeur réel.

## Limites connues

- **Données synthétiques** (voir plus haut).
- **Le canal de paiement (carte, Mobile Money, virement, en ligne) n'est pas une variable du modèle** :
  le jeu de données n'a pas de colonne « canal », et `preprocessing.py` n'utilise aucune information de canal.
  Changer le canal ne change donc pas le score *d'un même modèle*. Avec le modèle Mobile Money, le canal peut
  en revanche servir à **choisir le modèle** à appeler (carte ou Mobile Money) : ce choix est à brancher côté backend.
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
**Deux modèles, deux fichiers.** `predict.py` lit la clé `famille` du `.joblib` (absente = `carte`) pour appliquer la
bonne préparation des données ; c'est au backend de choisir quel fichier charger selon le canal. Attention : la
table `MLModel` n'autorise aujourd'hui **qu'un seul modèle actif** (contrainte `single_active_model`) et
`services.py` ne charge que celui-là : pour scorer les deux familles en production, il faudra adapter le backend
(un modèle actif par famille). Ce n'est pas fait.

Le `.joblib` contient un dictionnaire `metriques` (précision, rappel, F1, AUC, matrice de confusion, seuil,
date d'entraînement) destiné à la page « Modèle IA » ; le backend actuel ignore cette clé sans erreur.
