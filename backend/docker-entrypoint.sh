#!/bin/sh
# Démarrage du conteneur backend FraudGuard (docker compose ET Render).
#
#   1. migrate                         : schéma PostgreSQL à jour
#   2. activer_modele_ml               : enregistre/active le pipeline ML
#   3. seed_demo                       : comptes + transactions de démo (une seule fois)
#   4. exec "$@"                       : lance Gunicorn (CMD du Dockerfile)
#
# Les étapes 2 et 3 sont idempotentes : redémarrer le conteneur ne crée ni
# doublon de modèle ni nouvelles transactions.
#
# Variables optionnelles :
#   ML_MODEL_FILE    (défaut fraudguard_pipeline.joblib)
#   ML_MODEL_VERSION (défaut v1)
#   SEED_DEMO        (défaut true ; false pour ne pas créer de données de démo)
#   DEMO_PASSWORD    (mot de passe des comptes démo ; défaut celui de seed_demo)
set -e

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-fraudguard.settings}"
ML_MODEL_FILE="${ML_MODEL_FILE:-fraudguard_pipeline.joblib}"
ML_MODEL_VERSION="${ML_MODEL_VERSION:-v1}"

echo "[entrypoint] Attente de la base de données..."
python - <<'EOF'
import sys, time
import django
from django.db import connection
django.setup()
for tentative in range(30):
    try:
        connection.ensure_connection()
        sys.exit(0)
    except Exception as exc:  # base pas encore prête
        print(f"  base indisponible ({exc.__class__.__name__}), nouvel essai dans 2 s")
        time.sleep(2)
sys.exit("Base de données injoignable après 60 s")
EOF

echo "[entrypoint] Migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Activation du modèle ML ($ML_MODEL_FILE, $ML_MODEL_VERSION)..."
# Métriques mesurées sur le jeu de TEST (ml/reports/metriques.json).
python manage.py activer_modele_ml "$ML_MODEL_FILE" \
    --modele-version "$ML_MODEL_VERSION" --algorithm xgboost \
    --precision 0.6075 --recall 0.8695 --f1 0.7152 --auc 0.9945

if [ "${SEED_DEMO:-true}" = "true" ]; then
    if python manage.py shell -c "from transactions.models import Transaction; import sys; sys.exit(0 if Transaction.objects.filter(transaction_id__startswith='DEMO-').exists() else 1)"; then
        echo "[entrypoint] Données de démo déjà présentes, rien à faire."
    else
        echo "[entrypoint] Création des données de démo..."
        if [ -n "$DEMO_PASSWORD" ]; then
            python manage.py seed_demo --simuler-decisions --mot-de-passe "$DEMO_PASSWORD"
        else
            python manage.py seed_demo --simuler-decisions
        fi
    fi
fi

echo "[entrypoint] Démarrage : $*"
exec "$@"
