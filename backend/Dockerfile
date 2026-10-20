# Image backend FraudGuard (Django REST + modèle ML), prête pour la production.
#
# Le contexte de build est la RACINE du dépôt (et non backend/) pour que
# l'image embarque aussi le modèle ML (ml/models) et son code (ml/src) :
# sur Render il n'y a pas de volume monté, l'image doit se suffire à elle-même.
#
#   docker build -f backend/Dockerfile -t fraudguard-backend .

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ML_MODELS_DIR=/app/ml_models \
    ML_SRC_DIR=/app/ml_src \
    DJANGO_MEDIA_ROOT=/app/media \
    PORT=8000

WORKDIR /app

# libgomp1 : requis par XGBoost à l'exécution (OpenMP).
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# Code Django, puis modèle ML et code de prétraitement partagé.
COPY backend/ /app/
COPY ml/models/ /app/ml_models/
COPY ml/src/ /app/ml_src/

# Fichiers statiques (admin Django, Swagger) servis par WhiteNoise.
# Clé factice : collectstatic n'a besoin d'aucun secret réel.
RUN DJANGO_SECRET_KEY=collectstatic-only DJANGO_DEBUG=False \
    python manage.py collectstatic --noinput

# Utilisateur non-root ; media/ est le dossier des rapports PDF/CSV générés.
RUN useradd --create-home --uid 1000 fraudguard \
    && mkdir -p /app/media \
    && chown -R fraudguard:fraudguard /app/media \
    && chmod +x /app/docker-entrypoint.sh
USER fraudguard

EXPOSE 8000

# Migrations + activation du modèle ML + données de démo, puis Gunicorn.
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["sh", "-c", "exec gunicorn fraudguard.wsgi:application --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-2} --threads 2 --timeout 120 --access-logfile -"]
