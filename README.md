# FraudGuard — Plateforme de Détection de Fraude Bancaire

Projet académique (Agile/Scrum) — équipe de 4 étudiants.

## Répartition des dossiers par membre

| Dossier | Responsable | Rôle |
|---|---|---|
| `backend/` | Étudiant 1 | Software Architect / Backend Lead |
| `ml/` | Étudiant 2 | Lead Data Scientist / ML Engineer |
| `frontend/` | Étudiant 3 | Senior React Developer / UX — **également responsable unique des fusions Git** |
| `docker-compose.yml`, `.github/workflows/` | Étudiant 4 | DevOps / QA / Integration |
| `docs/` | Tous | Documentation partagée (CDC, roadmap, UML, dictionnaire de données) |

Chaque dossier contient son propre `README.md` avec les instructions détaillées pour démarrer.

## Démarrage rapide

```bash
git clone <url-du-depot>
cd fraudguard
cp .env.example .env          # remplir les valeurs
docker compose up --build
```

- Backend disponible sur http://localhost:8000
- Frontend disponible sur http://localhost:3000
- Documentation API (Swagger) sur http://localhost:8000/api/docs/

## Stack technique

React.js (Bootstrap 5, Recharts) — Django REST Framework + Simple JWT — PostgreSQL — Scikit-Learn / XGBoost / Imbalanced-learn — Docker / Docker Compose / Render — Swagger/OpenAPI.

## Git — règle de fusion

Voir `docs/git/Guide_Git_GitHub_FraudGuard.docx`. Résumé : chaque membre travaille sur sa branche (`feature/backend`, `feature/ml`, `feature/frontend`, `feature/devops`), un autre membre valide, puis **Étudiant 3** effectue la fusion vers `develop` et `main`.

## Documentation complète

Voir `docs/conception/` pour le cahier des charges, la roadmap, les diagrammes UML et le dictionnaire de données.
