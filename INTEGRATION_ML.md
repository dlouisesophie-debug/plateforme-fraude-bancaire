# Intégration ML — guide pour l'étudiant backend

Le pipeline ML (`ml/models/fraudguard_pipeline.joblib`) est branché sur le backend Django.
Tout ce qui est décrit ici a été exécuté et testé (voir « Tests automatiques »).

## En une phrase

Quand une transaction est créée via l'API (`POST /api/transactions/`), elle est scorée
automatiquement par le modèle actif. Une `Prediction` est enregistrée ; si le score dépasse
le seuil du modèle (0,1126), une `Alert` est créée et la transaction passe en `under_review`.

## Fichiers modifiés ou ajoutés

| Fichier | Rôle |
|---|---|
| `backend/transactions/models.py` + `migrations/0002_ml_scoring_fields.py` | 11 champs nécessaires au scoring sur `Transaction` |
| `backend/transactions/serializers.py` | La création accepte ces champs |
| `backend/transactions/views.py` | `perform_create` appelle `score_transaction()` ; un échec est écrit dans les logs et ne bloque jamais la création |
| `backend/fraud_detection/services.py` | Charge le pipeline (mis en cache), prétraite, prédit, crée Prediction et Alert |
| `backend/fraud_detection/apps.py` | Ajoute `ml/src` au `sys.path` |
| `backend/fraud_detection/management/commands/activer_modele_ml.py` | Enregistre et active un modèle |
| `ml/src/predict.py` | Chargement du pipeline et calcul de la probabilité |
| `backend/fraudguard/settings.py` | `ML_MODELS_DIR`, `ML_SRC_DIR` |
| `backend/fraudguard/settings_test.py` | Réglages des tests (SQLite) |
| `backend/*/tests.py`, `fraud_detection/sample_transactions.py` | 15 tests automatiques |
| `docker-compose.yml` | Volume `./ml/src:/app/ml_src` (manquait) |

`ml/src/preprocessing.py` n'a pas été touché : c'est la source de vérité du prétraitement.

## Valeurs acceptées par le modèle

Le modèle a été entraîné avec des valeurs précises. **Une valeur inconnue ne fait pas planter
le scoring, mais elle est ignorée et fausse le score** (un avertissement est écrit dans les logs).

- `category` : `achats`, `achats_en_ligne`, `auto_transport`, `courses`, `courses_en_ligne`,
  `divers`, `divers_en_ligne`, `divertissement`, `enfants_animaux`, `maison`, `restauration`,
  `sante_sport`, `soins_personnels`, `voyage`
- `customer_region` : `Dakar`, `Diourbel`, `Fatick`, `Kaolack`, `Kolda`, `Louga`, `Matam`,
  `Saint-Louis`, `Sédhiou`, `Tambacounda`, `Thiès`, `Ziguinchor`
- `customer_gender` : `F` ou `M`
- `merchant`, `customer_city`, `customer_profession` : texte libre, les valeurs connues du
  modèle donnent un meilleur score, les autres sont traitées comme « rares ».

Tous ces champs sont optionnels en base (rien ne casse sans eux) mais le frontend doit les envoyer.

## Mise en route avec Docker

```bash
docker compose up --build -d          # applique aussi les migrations
docker compose exec backend python manage.py activer_modele_ml fraudguard_pipeline.joblib --modele-version 1 --algorithm xgboost --precision 0.90 --recall 0.80 --f1 0.847 --auc 0.9933
```

## Mise en route en local (sans Docker)

Dans `backend/`, venv activé, PostgreSQL local démarré.

1. Créer `backend/.env` (jamais commité) :
```
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_DB=fraudguard
POSTGRES_USER=fraudguard
POSTGRES_PASSWORD=mot_de_passe_de_ta_base
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
FRAUD_ALERT_THRESHOLD=0.7
ML_MODELS_DIR=../ml/models
ML_SRC_DIR=../ml/src
```
`POSTGRES_HOST` vaut `localhost` en local (`db` est réservé à Docker). Les chemins `../ml/...`
supposent que les commandes sont lancées depuis `backend/`.

2. Commandes :
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py activer_modele_ml fraudguard_pipeline.joblib --modele-version 1 --algorithm xgboost --precision 0.90 --recall 0.80 --f1 0.847 --auc 0.9933
python manage.py runserver
```

Le chemin passé à `activer_modele_ml` est relatif à `ML_MODELS_DIR` (donc juste le nom du fichier).

## Tests automatiques

```bash
python manage.py test --settings=fraudguard.settings_test
```

15 tests, SQLite en mémoire (pas besoin de PostgreSQL ni du droit de créer une base). Ils
utilisent le vrai `fraudguard_pipeline.joblib` et vérifient notamment :
une transaction normale n'est pas flaggée ; une vraie fraude (score du modèle, valeur non forcée)
crée une alerte `critical` et passe en `under_review` ; le re-scoring ne crée pas de doublon ;
sans modèle actif la transaction est créée en `pending` et l'erreur est loguée ;
un seul modèle peut être actif ; la commande `activer_modele_ml` fonctionne.
Si le `.joblib` est absent, les tests de scoring sont ignorés.

## Vérifier que le ML est bien utilisé

1. Créer une transaction via **`POST /api/transactions/`** (Swagger : `/api/docs/`, après login
   sur `/api/auth/login/` et bouton Authorize).
2. Lire `GET /api/fraud-detection/predictions/` : la `fraud_probability` doit avoir de nombreuses
   décimales (ex. `8.17e-06`).

Une prédiction saisie à la main dans l'admin Django n'est **pas** scorée : elle contient ce qui a
été tapé. Seule la création par l'API déclenche le modèle.

## Problèmes fréquents

| Message | Cause | Solution |
|---|---|---|
| `la colonne transactions.customer_gender n'existe pas` | Migration non appliquée | `python manage.py migrate` |
| `la colonne « category » existe déjà` au `migrate` | Base issue d'un essai antérieur, non alignée sur les migrations | Recréer la base de développement, puis `migrate` |
| `Fichier introuvable : .../ml_models/...` | `ML_MODELS_DIR` non défini en local | Ajouter les lignes `ML_*` au `.env` |
| `Aucun modèle ML actif` dans les logs | Modèle non activé | `activer_modele_ml ...` |
| `catégorie ... inconnue du modèle` dans les logs | Valeur hors liste ci-dessus | Utiliser une catégorie connue |

## Points d'attention

- Le pipeline est mis en cache en mémoire ; changer de modèle actif le recharge automatiquement.
- Le seuil utilisé est `seuil_decision` du pipeline (≈ 0,1126, optimisé pour ~85 % de rappel),
  pas `FRAUD_ALERT_THRESHOLD`, qui ne sert que de valeur de secours.
- La gravité de l'alerte (`low`, `medium`, `high`, `critical`) vient de `services._gravite()` ;
  à ajuster selon vos règles métier.
- Le modèle a été entraîné avec scikit-learn 1.3.0 ; un avertissement de version peut s'afficher
  au chargement. Il est sans effet sur les résultats.
