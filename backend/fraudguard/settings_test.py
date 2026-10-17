"""
Reglages utilises uniquement pour lancer les tests automatiques :

    python manage.py test --settings=fraudguard.settings_test

- SQLite en memoire : pas besoin de PostgreSQL ni du droit CREATEDB.
- ML_MODELS_DIR / ML_SRC_DIR pointent directement vers le dossier ml/ du
  depot (backend/../ml), sans passer par les volumes Docker.
"""

from .settings import *  # noqa: F401,F403
from .settings import BASE_DIR

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

ML_MODELS_DIR = str(BASE_DIR.parent / "ml" / "models")
ML_SRC_DIR = str(BASE_DIR.parent / "ml" / "src")

# Hashage rapide des mots de passe : suffisant (et plus rapide) pour les tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Rapports générés dans un dossier temporaire pendant les tests.
import tempfile  # noqa: E402
from pathlib import Path  # noqa: E402

MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="fraudguard-tests-"))
REPORTS_DIR = MEDIA_ROOT / "reports"
