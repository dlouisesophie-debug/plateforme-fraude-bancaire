# Frontend — FraudGuard Dashboard

Responsable : Étudiant 3 (Senior React Developer / UX)
Également responsable unique des fusions Git — voir `docs/git/Guide_Git_GitHub_FraudGuard.docx`.

## Structure

```
src/
├── pages/         Une page par route (Login, Dashboard, Transactions, Alerts)
├── components/    Composants reutilisables (tables, cartes KPI, graphiques)
├── services/      Appels API (axios) — api.js deja configure avec le token JWT
└── hooks/         Hooks personnalises (ex. useAuth deja fourni)
```

## Demarrage local (sans Docker)

```bash
npm install
cp .env.example .env
npm start
```

## Demarrage avec Docker (coordonner avec Etudiant 4)

Depuis la racine du projet :
```bash
docker compose up --build
```

## A faire (Sprint 4, voir roadmap)

- [ ] Page de login (JWT) — utiliser `services/api.js` et `hooks/useAuth.js` deja en place
- [ ] Dashboard : KPIs (volume, taux de fraude, alertes actives) + graphiques Recharts
- [ ] Page Transactions : liste paginee, filtres par statut/canal
- [ ] Page Alertes : liste, actions confirmer/rejeter (endpoints `/api/alerts/{id}/confirm/` et `/reject/`)
- [ ] Rendre l'ensemble responsive (Bootstrap 5)
- [ ] Gerer les etats de chargement et d'erreur sur chaque appel API
