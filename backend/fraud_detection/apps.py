import sys

from django.apps import AppConfig
from django.conf import settings


class FraudDetectionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fraud_detection"
    verbose_name = "Detection de fraude (ML)"

    def ready(self):
        # Rend ml/src (preprocessing.py, predict.py) importable depuis le
        # backend, sans dupliquer le code ML dans le projet Django — le
        # dossier ml/src est monte dans le conteneur via docker-compose
        # (volume ./ml/src:/app/ml_src, voir settings.ML_SRC_DIR).
        ml_src_dir = getattr(settings, "ML_SRC_DIR", None)
        if ml_src_dir and ml_src_dir not in sys.path:
            sys.path.insert(0, ml_src_dir)
