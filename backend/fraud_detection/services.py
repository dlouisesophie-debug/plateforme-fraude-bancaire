"""
Point d'integration entre le backend Django et le pipeline ML (dossier /ml).

Fonctionnement :
1. Le modele actif est recupere en base (MLModel.objects.get(is_active=True)),
   son fichier .joblib charge depuis le chemin indique par son champ
   `artifact_path` (relatif a settings.ML_MODELS_DIR), puis mis en cache en
   memoire pour ne pas re-charger le pipeline a chaque transaction.
2. Le meme pretraitement que celui utilise a l'entrainement est applique via
   ml/src/preprocessing.py (source de verite unique, voir ml/README.md) —
   jamais duplique ici.
3. Une Prediction est creee ; si fraud_probability depasse le seuil de
   decision du modele (ou settings.FRAUD_ALERT_THRESHOLD en secours), une
   Alert est creee automatiquement avec une gravite calculee a partir du
   score.

Pour activer un modele : `python manage.py activer_modele_ml ml_models/fraudguard_pipeline.joblib`
(voir fraud_detection/management/commands/activer_modele_ml.py).
"""

import logging
import os

from django.conf import settings
from django.utils import timezone as dj_timezone

from .models import MLModel, Prediction

logger = logging.getLogger(__name__)

# Cache en memoire du pipeline ML charge (evite de relire le .joblib a
# chaque requete). Cle : artifact_path du MLModel actif, pour recharger
# automatiquement si le modele actif change.
_PIPELINE_CACHE: dict = {"artifact_path": None, "pipeline": None}


def _charger_pipeline(active_model: MLModel) -> dict:
    """Charge (ou reutilise depuis le cache) le pipeline .joblib du modele actif."""
    if (
        _PIPELINE_CACHE["pipeline"] is not None
        and _PIPELINE_CACHE["artifact_path"] == active_model.artifact_path
    ):
        return _PIPELINE_CACHE["pipeline"]

    # predict.load_pipeline vient de ml/src, rendu importable par
    # fraud_detection/apps.py (sys.path.insert sur settings.ML_SRC_DIR).
    from predict import load_pipeline

    chemin = active_model.artifact_path
    if not os.path.isabs(chemin):
        chemin = os.path.join(settings.ML_MODELS_DIR, chemin)

    pipeline = load_pipeline(chemin)
    _PIPELINE_CACHE["artifact_path"] = active_model.artifact_path
    _PIPELINE_CACHE["pipeline"] = pipeline
    return pipeline


def _transaction_vers_dict(transaction) -> dict:
    """
    Convertit une instance Transaction (modele Django) en dict brut attendu
    par ml/src/preprocessing.construire_features — memes cles que celles
    utilisees a l'entrainement.
    """
    # Django stocke timestamp en UTC (USE_TZ=True) alors que
    # customer_birth_date est une date naive : preprocessing.py fait
    # `date_transaction - date_naissance`, ce qui leve une TypeError si
    # l'un est tz-aware et l'autre non. On convertit timestamp en heure
    # locale (TIME_ZONE = Africa/Dakar) puis on retire le fuseau, pour que
    # heure_transaction/jour_semaine refletent l'heure locale reelle, pas
    # l'heure UTC.
    timestamp_naif = dj_timezone.localtime(transaction.timestamp).replace(tzinfo=None)

    return {
        "montant_fcfa": float(transaction.amount),
        "genre": transaction.customer_gender,
        "population_ville": transaction.customer_city_population or 0,
        "date_transaction": timestamp_naif,
        "date_naissance": transaction.customer_birth_date,
        "latitude_client": transaction.customer_latitude or 0.0,
        "longitude_client": transaction.customer_longitude or 0.0,
        "latitude_commercant": transaction.merchant_latitude or 0.0,
        "longitude_commercant": transaction.merchant_longitude or 0.0,
        "commercant": transaction.merchant,
        "ville": transaction.customer_city,
        "profession": transaction.customer_profession,
        "categorie": transaction.category,
        "region": transaction.customer_region,
    }


def _gravite(fraud_probability: float) -> str:
    """Mappe une probabilite de fraude sur les niveaux de gravite d'Alert."""
    if fraud_probability >= 0.9:
        return "critical"
    if fraud_probability >= 0.75:
        return "high"
    if fraud_probability >= 0.5:
        return "medium"
    return "low"


def score_transaction(transaction):
    """
    Score une transaction avec le modele ML actif et cree la Prediction
    correspondante. Declenche une alerte si le score depasse le seuil de
    decision du modele.
    """
    active_model = MLModel.objects.filter(is_active=True).first()
    if active_model is None:
        raise RuntimeError(
            "Aucun modele ML actif — executez "
            "`python manage.py activer_modele_ml <chemin_du_joblib>`."
        )

    pipeline = _charger_pipeline(active_model)

    from predict import get_decision_threshold, predict_fraud_probability

    transaction_dict = _transaction_vers_dict(transaction)

    # Une categorie ou une region absente du jeu d'entrainement ne fait pas
    # planter le modele (elle est simplement ignoree) mais fausse le score :
    # on le signale dans les logs plutot que de le taire.
    if transaction_dict["categorie"] not in pipeline.get("categories_connues", []):
        logger.warning(
            "Transaction %s : categorie %r inconnue du modele (connues : %s).",
            transaction.transaction_id, transaction_dict["categorie"],
            ", ".join(pipeline.get("categories_connues", [])),
        )
    if transaction_dict["region"] not in pipeline.get("regions_connues", []):
        logger.warning(
            "Transaction %s : region %r inconnue du modele.",
            transaction.transaction_id, transaction_dict["region"],
        )
    fraud_probability = predict_fraud_probability(pipeline, transaction_dict)

    seuil = get_decision_threshold(pipeline, fallback=settings.FRAUD_ALERT_THRESHOLD)
    is_fraud = fraud_probability >= seuil

    # get_or_create plutot que create : evite une IntegrityError sur
    # OneToOneField si cette fonction est appelee plusieurs fois pour la
    # meme transaction (ex. re-run d'un test ou d'une commande manuelle).
    prediction, _ = Prediction.objects.update_or_create(
        transaction=transaction,
        defaults={
            "ml_model": active_model,
            "fraud_probability": fraud_probability,
            "prediction": is_fraud,
        },
    )

    if is_fraud:
        from alerts.models import Alert

        Alert.objects.get_or_create(
            prediction=prediction,
            defaults={"severity": _gravite(fraud_probability)},
        )
        # Marque la transaction comme suspecte, a confirmer/rejeter par
        # un analyste (voir app alerts).
        transaction.status = transaction.Status.UNDER_REVIEW
    else:
        # Score sous le seuil : la transaction est classee legitime
        # automatiquement (diagramme d'activite : "Fraude ? Non ->
        # Transaction normale"). Un analyste peut toujours la requalifier
        # en frauduleuse (faux negatif), ce qui alimente la matrice de
        # confusion du dashboard.
        transaction.status = transaction.Status.LEGITIMATE
    transaction.save(update_fields=["status"])

    return prediction
