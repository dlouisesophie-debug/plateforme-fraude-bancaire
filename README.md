# FraudGuard — Plateforme de Détection de Fraude Bancaire

Projet académique (Agile/Scrum) — équipe de 4 étudiants.

**Application en ligne (Render)** :
- Frontend : https://fraudguard-web.onrender.com
- API : https://fraudguard-api.onrender.com/api — Swagger : https://fraudguard-api.onrender.com/api/docs/

> Offre gratuite de Render : un service inactif depuis 15 minutes est mis en veille.
> Ouvrir les deux URL **quelques minutes avant la démonstration** (premier chargement ≈ 1 minute).

## Répartition des dossiers par membre

| Dossier | Responsable | Rôle |
|---|---|---|
| `backend/` | Étudiant 1 | Software Architect / Backend Lead |
| `ml/` | Étudiant 2 | Lead Data Scientist / ML Engineer |
| `frontend/` | Étudiant 3 | Senior React Developer / UX — **également responsable unique des fusions Git** |
| `docker-compose.yml`, `render.yaml`, `*/Dockerfile`, `.github/workflows/` | Étudiant 4 | DevOps / QA / Integration |
| `docs/` | Tous | Documentation partagée (CDC, roadmap, UML, dictionnaire de données) |

Chaque dossier contient son propre `README.md` avec les instructions détaillées.

## Comptes de démonstration

Créés automatiquement au premier démarrage (commande `seed_demo`, avec 40 transactions
scorées par le vrai modèle ML et des alertes en partie traitées) :

| Compte | Rôle | Peut notamment |
|---|---|---|
| `admin.demo` | Administrateur | Gérer les utilisateurs, superviser le modèle ML, voir tous les rapports |
| `analyste.demo` | Analyste fraude | Traiter les alertes (confirmer / rejeter), consulter les transactions |
| `agent.demo` | Agent bancaire | Saisir et consulter des transactions, exporter des rapports |

Mot de passe :
- **en local (Docker ou non)** : `FraudGuard2026!`
- **sur Render** : celui choisi dans la variable `DEMO_PASSWORD` du service `fraudguard-api`
  (communiqué au jury séparément, jamais écrit dans le dépôt).

## Lancement avec Docker (recommandé pour la démo)

Prérequis : Docker Desktop (Compose v2.24 ou plus récent).

```bash
git clone https://github.com/dlouisesophie-debug/plateforme-fraude-bancaire.git
cd plateforme-fraude-bancaire
docker compose up --build
```

Aucun fichier `.env` n'est nécessaire : des valeurs de démonstration sont prévues.
Au démarrage, le backend exécute automatiquement (`backend/docker-entrypoint.sh`) :

1. `python manage.py migrate`
2. `python manage.py activer_modele_ml fraudguard_pipeline.joblib --modele-version v1 ...`
3. `python manage.py seed_demo --simuler-decisions` (seulement si aucune donnée de démo n'existe)
4. Gunicorn (serveur de production)

| Service | URL |
|---|---|
| Frontend (build React servi par Nginx) | http://localhost:3000 |
| API | http://localhost:8000/api |
| Swagger / OpenAPI | http://localhost:8000/api/docs/ |
| Administration Django | http://localhost:8000/admin/ |
| Contrôle de santé | http://localhost:8000/api/health/ |

Les données PostgreSQL et les rapports PDF/CSV générés (`/app/media`) sont conservés dans
des volumes Docker (`postgres_data`, `media_data`). Pour repartir de zéro :
`docker compose down -v`.

## Lancement en local sans Docker (développement)

Prérequis : Python 3.12, Node.js 20, PostgreSQL 16 avec une base `fraudguard`.

```bash
cp .env.example .env               # puis renseigner POSTGRES_PASSWORD

# Backend (terminal 1)
cd backend
python -m venv venv
source venv/bin/activate           # Windows : venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py activer_modele_ml fraudguard_pipeline.joblib --modele-version v1
python manage.py seed_demo --simuler-decisions
python manage.py runserver         # http://localhost:8000

# Frontend (terminal 2)
cd frontend
npm install
cp .env.example .env               # REACT_APP_USE_MOCKS=false pour utiliser le vrai backend
npm start                          # http://localhost:3000
```

## Tests

```bash
cd backend
python manage.py test --settings=fraudguard.settings_test   # SQLite, sans PostgreSQL
```

La CI GitHub Actions (`.github/workflows/ci.yml`) exécute à chaque push / pull request
sur `develop` et `main` :
- les tests Django sur PostgreSQL **avec le vrai modèle ML** (la CI échoue si un test
  de scoring est ignoré) et le rapport de couverture (résumé de l'exécution + artefact
  `couverture-backend`) ;
- `manage.py check --deploy` en configuration de production ;
- le build de production du frontend ;
- la construction des deux images Docker et un démarrage complet avec `docker compose`.

## Déploiement sur Render

Le fichier `render.yaml` (Blueprint) décrit les 3 ressources :

| Ressource Render | Type | Contenu |
|---|---|---|
| `fraudguard-db` | PostgreSQL 16 | Base de données |
| `fraudguard-api` | Web Service (Docker, `backend/Dockerfile`) | Django + Gunicorn + modèle ML |
| `fraudguard-web` | Web Service (Docker, `frontend/Dockerfile`) | Build React servi par Nginx |

Déploiement initial : Render → **New → Blueprint** → choisir ce dépôt (branche `main`)
→ saisir `DEMO_PASSWORD` → **Apply**. Chaque fusion sur `main` redéploie automatiquement.

Variables principales (définies dans `render.yaml`) : `DJANGO_DEBUG=False`,
`DJANGO_SECRET_KEY` (générée par Render), `DATABASE_URL` (fournie par la base),
`DJANGO_ALLOWED_HOSTS`, `DJANGO_CORS_ALLOWED_ORIGINS` (URL du frontend),
`REACT_APP_API_URL` (URL de l'API) et `REACT_APP_USE_MOCKS=false`.
En production, HTTPS est imposé (redirection, cookies sécurisés, HSTS).

Limites de l'offre gratuite à connaître : mise en veille après 15 minutes d'inactivité,
base PostgreSQL gratuite limitée dans le temps, et disque non persistant (les rapports
PDF/CSV générés disparaissent à chaque redéploiement ; ils peuvent être régénérés).

## Stack technique

React.js (Tailwind CSS, Recharts) — Django REST Framework + Simple JWT — PostgreSQL —
Scikit-Learn / XGBoost / Imbalanced-learn — Docker / Docker Compose / Gunicorn / Nginx / Render —
Swagger/OpenAPI — GitHub Actions.

## Git — règle de fusion

Voir `docs/git/Guide_Git_GitHub_FraudGuard.docx`. Résumé : chaque membre travaille sur sa
branche (`backend`, `feature/ml`, `feature/frontend-ui`, `feature/devops`) **et commite avec son
propre compte GitHub**, un autre membre valide la pull request, puis **Étudiant 3** effectue
la fusion vers `develop` et `main`. La branche `main` est protégée (pull request + CI verte
obligatoires).

## Documentation complète

Voir `docs/conception/` pour le cahier des charges, la roadmap, les diagrammes UML et le
dictionnaire de données.
