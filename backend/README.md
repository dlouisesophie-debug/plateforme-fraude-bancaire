# Backend — FraudGuard API

Responsable : Étudiant 1 (Software Architect / Backend Lead)

## Structure des apps Django

Chaque app correspond à un module du diagramme de packages corrigé :

| App | Contenu |
|---|---|
| `authentication/` | Modèle User personnalisé, JWT (rôle dans le token), `/me`, permissions par rôle |
| `transactions/` | Modèle Transaction, saisie avec scoring automatique, filtres, recherche, export CSV |
| `fraud_detection/` | Modèles MLModel et Prediction, intégration avec `ml/`, commandes `activer_modele_ml` et `seed_demo` |
| `alerts/` | Modèle Alert, traitement des alertes (confirmer, rejeter, annoter) |
| `dashboard/` | Indicateurs du tableau de bord (`/api/dashboard/stats/`) |
| `reports/` | Modèle Report, génération réelle des fichiers PDF/CSV |
| `audit/` | Modèle AuditLog : connexions, gestion des utilisateurs, écritures sur l'API |

## Démarrage local (sans Docker)

```bash
python -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env        # si pas déjà fait à la racine
python manage.py migrate
python manage.py activer_modele_ml fraudguard_pipeline.joblib --modele-version v1 \
    --algorithm xgboost --precision 0.782 --recall 0.851 --f1 0.815 --auc 0.9933
python manage.py seed_demo --simuler-decisions   # comptes + 40 transactions scorées
python manage.py runserver
```

Comptes créés par `seed_demo` (mot de passe `FraudGuard2026!`, modifiable avec
`--mot-de-passe`) : `admin.demo`, `analyste.demo`, `agent.demo`.
Le fichier `fraudguard_pipeline.joblib` doit être dans `ML_MODELS_DIR`
(par défaut `backend/ml_models/`, ou `ml/models/` monté par Docker).

## Tests

```bash
python manage.py test --settings=fraudguard.settings_test   # SQLite en mémoire, sans PostgreSQL
python manage.py test                                        # PostgreSQL (comme la CI)
```

Les tests du scoring réel sont ignorés si le `.joblib` est absent ; la logique
métier autour du scoring est testée dans tous les cas grâce à
`fraud_detection/testing.py` (faux modèle).

## Référence de l'API (pour le frontend)

Documentation interactive complète : `/api/docs/` (Swagger).

### Authentification

| Méthode | URL | Rôle | Description |
|---|---|---|---|
| POST | `/api/auth/login/` | tous | `{username, password}` → `{access, refresh, user: {username, role, role_label, …}}` |
| POST | `/api/auth/refresh/` | tous | `{refresh}` → nouveau `access` |
| GET | `/api/auth/me/` | connecté | Profil et rôle de l'utilisateur connecté |
| CRUD | `/api/auth/users/` | admin | Gestion des utilisateurs (journalisée) |

### Transactions

| Méthode | URL | Rôle | Description |
|---|---|---|---|
| GET | `/api/transactions/` | connecté | Liste paginée (20 par page) |
| POST | `/api/transactions/` | agent, admin | Saisie : scoring ML immédiat, la réponse contient le score |
| GET | `/api/transactions/{id}/` | connecté | Détail |
| PATCH | `/api/transactions/{id}/` | analyste, admin | `{status}` uniquement (requalification) |
| DELETE | `/api/transactions/{id}/` | admin | Suppression |
| GET | `/api/transactions/export/` | connecté | Export CSV (mêmes filtres que la liste) |

Filtres de la liste et de l'export : `status`, `channel`, `date_after`,
`date_before` (AAAA-MM-JJ), `min_amount`, `max_amount`, `search` (ID,
commerçant, lieu, ville), `ordering` (`timestamp`, `amount`,
`prediction__fraud_probability`, préfixe `-` pour décroissant).

Champs ajoutés à chaque transaction : `fraud_probability` (0 à 1, `null` si
non scorée), `is_fraud_predicted`, `model_version`, `alert_id`,
`alert_status`, `status_label`, `channel_label`.

Statut après scoring : `legitimate` si le score est sous le seuil,
`under_review` + alerte sinon. `pending` = transaction non scorée (aucun
modèle actif).

### Alertes (analyste, admin)

| Méthode | URL | Description |
|---|---|---|
| GET | `/api/alerts/?status=&severity=` | Liste avec `transaction_id`, `amount`, `channel`, `timestamp`, `fraud_probability`, libellés |
| POST | `/api/alerts/{id}/confirm/` | `{comment?}` → alerte confirmée, transaction frauduleuse |
| POST | `/api/alerts/{id}/reject/` | `{comment?}` → alerte rejetée, transaction légitime |
| PATCH | `/api/alerts/{id}/` | `{comment}` pour annoter sans statuer |

### Tableau de bord (connecté)

`GET /api/dashboard/stats/?date_after=&date_before=&channel=` renvoie :
`kpis` (volume, fraudes, taux, montant à risque, alertes actives),
`by_status`, `by_channel`, `daily` (évolution par jour), `confusion_matrix`
(vrais/faux positifs/négatifs, précision, rappel en production) et
`active_model` (version et métriques du modèle actif).

### Rapports

| Méthode | URL | Rôle | Description |
|---|---|---|---|
| POST | `/api/reports/` | connecté | `{title, type: "pdf"\|"csv", period_start?, period_end?}` → génère le fichier |
| GET | `/api/reports/` | connecté | Ses rapports (l'admin voit tous les rapports) |
| GET | `/api/reports/{id}/download/` | connecté | Téléchargement |
| DELETE | `/api/reports/{id}/` | admin | Supprime le rapport et son fichier |

### Autres

- `/api/fraud-detection/models/` (admin) : modèles ML, version, métriques.
- `/api/fraud-detection/predictions/` (connecté) : prédictions.
- `/api/audit/?action=&user=` (admin) : journal d'audit (`LOGIN_SUCCESS`,
  `LOGIN_FAILED`, `USER_CREATED`, `USER_UPDATED`, `USER_DELETED`, écritures API).

## Variables d'environnement utiles

| Variable | Défaut | Rôle |
|---|---|---|
| `DJANGO_CORS_ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:3001` | Origines du frontend autorisées |
| `DJANGO_MEDIA_ROOT` | `backend/media` | Dossier des rapports générés |
| `ML_MODELS_DIR` / `ML_SRC_DIR` | `backend/ml_models` / `backend/ml_src` | Pipeline ML et code `ml/src` |
| `FRAUD_ALERT_THRESHOLD` | `0.7` | Seuil de secours si le pipeline n'en fournit pas |
