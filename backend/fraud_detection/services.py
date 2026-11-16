"""
Point d'integration entre le backend Django et le pipeline ML (dossier /ml).

Fonctionnement :
1. Le modele actif de la bonne famille est recupere en base : famille
   « mobile_money » pour une transaction du canal mobile money qui a un type
   d'operation, famille « carte » pour tout le reste (comme avant). Sans
   modele mobile money actif, on revient au modele carte. Son fichier .joblib
   est charge depuis `artifact_path` (relatif a settings.ML_MODELS_DIR), puis
   mis en cache en memoire (un pipeline par fichier).
2. Le meme pretraitement que celui utilise a l'entrainement est applique via
   ml/src (preprocessing.py, predict.py ; source de verite unique, voir
   ml/README.md) — jamais duplique ici.
3. Une Prediction est creee ; si fraud_probability depasse le seuil de
   decision du modele (ou settings.FRAUD_ALERT_THRESHOLD en secours), une
   Alert est creee automatiquement avec une gravite calculee a partir du
   score. Chaque modele a son seuil unique : fraude ou non fraude.

Pour activer un modele : `python manage.py activer_modele_ml ml_models/fraudguard_pipeline.joblib`
(voir fraud_detection/management/commands/activer_modele_ml.py).
"""

import logging
import os

from django.conf import settings
from django.utils import timezone as dj_timezone

from .models import MLModel, Prediction

logger = logging.getLogger(__name__)

# Cache en memoire des pipelines ML charges (evite de relire le .joblib a
# chaque requete). Cle : artifact_path du MLModel, pour que les modeles carte
# et mobile money restent tous les deux en memoire.
_PIPELINE_CACHE: dict = {}


def _charger_pipeline(active_model: MLModel) -> dict:
    """Charge (ou reutilise depuis le cache) le pipeline .joblib d'un modele actif."""
    if active_model.artifact_path in _PIPELINE_CACHE:
        return _PIPELINE_CACHE[active_model.artifact_path]

    # predict.load_pipeline vient de ml/src, rendu importable par
    # fraud_detection/apps.py (sys.path.insert sur settings.ML_SRC_DIR).
    from predict import load_pipeline

    chemin = active_model.artifact_path
    if not os.path.isabs(chemin):
        chemin = os.path.join(settings.ML_MODELS_DIR, chemin)

    pipeline = load_pipeline(chemin)
    _PIPELINE_CACHE[active_model.artifact_path] = pipeline
    return pipeline


def _famille_de(transaction) -> str:
    """Famille de modele a utiliser : mobile money seulement si le canal et le type d'operation le permettent."""
    if transaction.channel == transaction.Channel.MOBILE_MONEY and transaction.operation_type:
        return MLModel.Famille.MOBILE_MONEY
    return MLModel.Famille.CARTE


def _modele_actif(famille: str):
    """
    Modele actif de la famille demandee. Sans modele mobile money actif, la
    transaction est scoree comme avant, par le modele carte (avec un message
    dans les logs), pour ne jamais bloquer le scoring.
    """
    modele = MLModel.objects.filter(is_active=True, famille=famille).first()
    if modele is None and famille != MLModel.Famille.CARTE:
        logger.warning("Aucun modele %s actif : scoring par le modele carte.", famille)
        modele = MLModel.objects.filter(is_active=True, famille=MLModel.Famille.CARTE).first()
    return modele


def _transaction_vers_dict_mobile_money(transaction) -> dict:
    """
    Variables du modele mobile money (contrat de donnees ML-4) : type
    d'operation PaySim, montant tel que saisi (unite du simulateur, pas des
    FCFA) et heure locale de la transaction (Dakar = UTC+0).
    """
    return {
        "type": transaction.operation_type.upper(),
        "montant": float(transaction.amount),
        "heure": dj_timezone.localtime(transaction.timestamp).hour,
    }


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
    active_model = _modele_actif(_famille_de(transaction))
    if active_model is None:
        raise RuntimeError(
            "Aucun modele ML actif — executez "
            "`python manage.py activer_modele_ml <chemin_du_joblib>`."
        )

    pipeline = _charger_pipeline(active_model)

    from predict import get_decision_threshold, predict_fraud_probability

    if active_model.famille == MLModel.Famille.MOBILE_MONEY:
        transaction_dict = _transaction_vers_dict_mobile_money(transaction)
    else:
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
