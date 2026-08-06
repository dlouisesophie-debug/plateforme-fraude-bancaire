# Backend — FraudGuard API

Responsable : Étudiant 1 (Software Architect / Backend Lead)

## Structure des apps Django

Chaque app correspond a un module du diagramme de packages corrige :

| App | Contenu |
|---|---|
| `authentication/` | Modele User personnalise, JWT, permissions par role |
| `transactions/` | Modele Transaction, endpoints CRUD |
| `fraud_detection/` | Modeles MLModel et Prediction, integration avec `ml/` |
| `alerts/` | Modele Alert, endpoints de traitement des alertes |
| `reports/` | Modele Report, generation PDF/CSV |
| `audit/` | Modele AuditLog, tracabilite |

## Demarrage local (sans Docker)

```bash
python -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env        # si pas deja fait a la racine
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Demarrage avec Docker (recommande, coordonner avec Etudiant 4)

Depuis la racine du projet :
```bash
docker compose up --build
```

## A faire (Sprint 1-3, voir roadmap)

- [ ] Ajuster `settings.py` (SECRET_KEY, ALLOWED_HOSTS en prod)
- [ ] Implementer les serializers et views de chaque app (stubs deja en place)
- [ ] Brancher les permissions par role (`authentication/permissions.py`)
- [ ] Configurer Swagger sur `/api/docs/` (deja cable dans `fraudguard/urls.py`, verifier le rendu)
- [ ] Ecrire les tests unitaires (`tests.py` dans chaque app)
- [ ] Copier le modele ML entraine par Etudiant 2 dans `ml_models/` (volume Docker) et brancher `fraud_detection/views.py`
