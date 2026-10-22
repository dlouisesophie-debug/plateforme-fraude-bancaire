# Guide de déploiement — FraudGuard (Étudiant 4, DevOps)

Exigence couverte : CDC §11 « L'application est déployée et accessible publiquement
(Render) via Docker », §6 « HTTPS obligatoire, protection CSRF/CORS configurée ».

## 1. Architecture finale (pour les diagrammes de composants et de déploiement)

### Environnement local — `docker compose up --build`

```
Navigateur
  │  http://localhost:3000                 http://localhost:8000/api
  ▼                                        ▼
┌──────────────────────┐   appels REST   ┌──────────────────────────────────────┐
│ frontend             │ ──────────────▶ │ backend                              │
│ nginx:1.27-alpine    │   (navigateur)  │ python:3.12-slim                     │
│ build React (static) │                 │ Gunicorn → Django REST + Simple JWT  │
│ port 80 → 3000       │                 │ + pipeline ML (XGBoost, .joblib)     │
└──────────────────────┘                 │ port 8000                            │
                                         │ volume media_data → /app/media       │
                                         └──────────────┬───────────────────────┘
                                                        │ PostgreSQL (5432)
                                                        ▼
                                         ┌──────────────────────────────────────┐
                                         │ db — postgres:16                     │
                                         │ volume postgres_data                 │
                                         └──────────────────────────────────────┘
```

### Production — Render (Blueprint `render.yaml`, région Frankfurt)

| Nœud Render | Type | Image / artefact | Port | Rôle |
|---|---|---|---|---|
| `fraudguard-web` | Web Service, runtime Docker | `frontend/Dockerfile` : build Node 20 → Nginx 1.27 | `$PORT` (Render) | Sert l'application React (SPA) en HTTPS |
| `fraudguard-api` | Web Service, runtime Docker | `backend/Dockerfile` : Python 3.12, Gunicorn, Django, `ml_models/fraudguard_pipeline.joblib`, `ml_src/` | `$PORT` (Render) | API REST, JWT, scoring ML, rapports PDF/CSV, Swagger |
| `fraudguard-db` | PostgreSQL 16 managé | — | 5432 (réseau privé Render) | Base de données |

Flux :
1. Le navigateur charge `https://fraudguard-web.onrender.com` (HTML/JS/CSS servis par Nginx).
2. Le JavaScript appelle `https://fraudguard-api.onrender.com/api/...` avec un jeton JWT (CORS limité à l'URL du frontend).
3. Le proxy de Render termine le TLS (HTTPS) et transmet au conteneur Gunicorn (`X-Forwarded-Proto: https`).
4. Django lit/écrit dans `fraudguard-db` via `DATABASE_URL` ; à la saisie d'une transaction, `fraud_detection.services` charge le pipeline `.joblib` (en cache) et produit la probabilité de fraude, puis l'alerte si le seuil est dépassé.
5. Render interroge `/api/health/` (application + base) pour décider si le service est prêt.

Démarrage du conteneur backend (`backend/docker-entrypoint.sh`) : attente de la base →
`migrate` → `activer_modele_ml fraudguard_pipeline.joblib --modele-version v1` →
`seed_demo` (une seule fois) → Gunicorn.

## 2. Mettre le travail dans le dépôt (avec TON compte GitHub)

Le CDC §9 exige une répartition claire et le jury lit l'historique Git : le commit doit
apparaître sous ton propre compte.

```bash
# Vérifier l'identité Git (e-mail = celui de TON compte GitHub)
git config user.name  "Ton nom"
git config user.email "ton-email@exemple.com"

git fetch origin
git checkout -b feature/deploiement origin/develop
# copier les fichiers livrés (ou : git apply fraudguard-deploiement.patch)
git add -A
git commit -m "feat(devops): déploiement Render (Docker, Gunicorn, Nginx, HTTPS, CI)"
git push -u origin feature/deploiement
```

Puis ouvrir une pull request `feature/deploiement` → `develop`, la faire valider par un
camarade et laisser Étudiant 3 fusionner. Render déploie depuis `main` : Étudiant 3 doit
ensuite fusionner `develop` → `main`.

## 3. Déployer sur Render (une seule fois)

1. Créer un compte sur render.com en se connectant **avec GitHub**. Le dépôt appartient à
   `dlouisesophie-debug` : soit cette personne fait le déploiement, soit elle autorise
   l'application Render sur le dépôt.
2. **New → Blueprint** → choisir `plateforme-fraude-bancaire`, branche `main`.
3. Render lit `render.yaml` et propose 3 ressources. Saisir `DEMO_PASSWORD`
   (mot de passe des comptes démo, à garder pour le jury) → **Apply**.
4. Attendre la fin des builds (≈ 10 min la première fois). Dans les journaux de
   `fraudguard-api`, on doit voir : `Modele ML ... active`, `40 transactions de démo créées`,
   `Listening at: http://0.0.0.0:...`.
5. **Vérifier les URL** réellement attribuées. Si Render a ajouté un suffixe (ex.
   `fraudguard-api-x7k2.onrender.com`) :
   - `fraudguard-api` → Environment → `DJANGO_ALLOWED_HOSTS` et `DJANGO_CORS_ALLOWED_ORIGINS` ;
   - `fraudguard-web` → Environment → `REACT_APP_API_URL`, puis **Manual Deploy**
     (l'URL est intégrée au moment du build) ;
   - corriger aussi `render.yaml` et le README dans le dépôt.

### Recette après déploiement (à faire et noter avant la soutenance)

| # | Vérification | Résultat attendu |
|---|---|---|
| 1 | `https://<api>/api/health/` | `{"status": "ok", "database": "ok"}` |
| 2 | `http://<api>/api/transactions/` (sans s) | redirection 301 vers https |
| 3 | Connexion `analyste.demo` sur le frontend | tableau de bord avec données |
| 4 | Saisie d'une transaction par `agent.demo` | score affiché, alerte si risque |
| 5 | Rafraîchir le navigateur sur `/transactions` | la page s'affiche (pas de 404) |
| 6 | Génération d'un rapport PDF puis téléchargement | fichier PDF lisible |
| 7 | `https://<api>/api/docs/` | Swagger affiché |

## 4. Protéger la branche `main` (propriétaire du dépôt)

GitHub → dépôt → **Settings → Branches → Add branch ruleset** (ou *Add rule*) pour `main` :
- *Require a pull request before merging* (1 approbation) ;
- *Require status checks to pass* : `Tests backend (Django + vrai modèle ML) et couverture`,
  `Build de production du frontend`, `Construction des images Docker` ;
- *Block force pushes*.
Ne peut être fait que par le propriétaire (`dlouisesophie-debug`) ou un administrateur.

## 5. Limites connues (offre gratuite Render)

- Mise en veille après 15 min sans trafic : ouvrir les deux URL quelques minutes avant la démo.
- Disque non persistant : les rapports PDF/CSV générés disparaissent au redéploiement
  (les données en base sont conservées). Solution payante : disque Render monté sur `/app/media`,
  ou stockage objet.
- PostgreSQL gratuit limité dans le temps : vérifier la date d'expiration dans le tableau de bord.
- 512 Mo de RAM : un seul worker Gunicorn (`WEB_CONCURRENCY=1`) ; mesuré ≈ 240 Mo avec le modèle chargé.
- Le premier scoring après démarrage charge le modèle (≈ 1 s) ; les suivants ≈ 30 ms
  (exigence CDC < 500 ms).
