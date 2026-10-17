"""
Calcul des indicateurs du tableau de bord (CDC 5.4).

Tout est calculé en base (agrégations SQL) en un seul appel, au lieu des
7 requêtes ou plus que le frontend envoyait pour reconstituer les KPIs.
Ces fonctions sont aussi utilisées par la génération des rapports
(app reports), pour que dashboard et rapports affichent les mêmes chiffres.
"""

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate

from alerts.models import Alert
from fraud_detection.models import MLModel
from transactions.models import Transaction


def filtrer_transactions(date_after=None, date_before=None, channel=None):
    """Transactions de la période (bornes incluses) et du canal demandés."""
    qs = Transaction.objects.all()
    if date_after:
        qs = qs.filter(timestamp__date__gte=date_after)
    if date_before:
        qs = qs.filter(timestamp__date__lte=date_before)
    if channel:
        qs = qs.filter(channel=channel)
    return qs


def _ratio(numerateur, denominateur):
    return round(numerateur / denominateur, 4) if denominateur else None


def matrice_de_confusion(qs):
    """
    Matrice de confusion « en production » : prédiction du modèle comparée
    au statut final de la transaction.

    - Vérité « fraude » : transaction au statut frauduleux (alerte confirmée
      par un analyste, ou requalification manuelle d'une transaction que le
      modèle n'avait pas signalée = faux négatif).
    - Vérité « légitime » : transaction au statut légitime (alerte rejetée,
      ou transaction sous le seuil non contestée).
    Les transactions en attente ou en cours d'examen ne sont pas comptées :
    leur vérité n'est pas encore connue.
    """
    tranchees = qs.filter(
        prediction__isnull=False,
        status__in=[Transaction.Status.FRAUDULENT, Transaction.Status.LEGITIMATE],
    )
    agg = tranchees.aggregate(
        vp=Count("id", filter=Q(prediction__prediction=True, status=Transaction.Status.FRAUDULENT)),
        fp=Count("id", filter=Q(prediction__prediction=True, status=Transaction.Status.LEGITIMATE)),
        fn=Count("id", filter=Q(prediction__prediction=False, status=Transaction.Status.FRAUDULENT)),
        vn=Count("id", filter=Q(prediction__prediction=False, status=Transaction.Status.LEGITIMATE)),
    )
    vp, fp, fn, vn = agg["vp"], agg["fp"], agg["fn"], agg["vn"]
    return {
        "true_positive": vp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": vn,
        "evaluated": vp + fp + fn + vn,
        "precision": _ratio(vp, vp + fp),
        "recall": _ratio(vp, vp + fn),
    }


def modele_actif():
    modele = MLModel.objects.filter(is_active=True).first()
    if modele is None:
        return None
    return {
        "version": modele.version,
        "algorithm": modele.algorithm,
        "algorithm_label": modele.get_algorithm_display(),
        "precision": modele.precision_score,
        "recall": modele.recall_score,
        "f1_score": modele.f1_score,
        "auc_roc": modele.auc_roc,
        "trained_at": modele.trained_at.isoformat() if modele.trained_at else None,
    }


def calculer_statistiques(date_after=None, date_before=None, channel=None):
    qs = filtrer_transactions(date_after, date_before, channel)

    total = qs.count()
    par_statut_brut = {
        ligne["status"]: ligne["n"]
        for ligne in qs.values("status").annotate(n=Count("id")).order_by()
    }
    nb_fraudes = par_statut_brut.get(Transaction.Status.FRAUDULENT, 0)

    montant_a_risque = qs.filter(
        status__in=[Transaction.Status.FRAUDULENT, Transaction.Status.UNDER_REVIEW]
    ).aggregate(s=Sum("amount"))["s"] or 0

    alertes_actives = Alert.objects.filter(
        status=Alert.Status.OPEN, prediction__transaction__in=qs,
    ).count()

    par_statut = [
        {"status": valeur, "label": libelle, "count": par_statut_brut.get(valeur, 0)}
        for valeur, libelle in Transaction.Status.choices
    ]

    canaux = {
        ligne["channel"]: ligne
        for ligne in qs.values("channel").annotate(
            total=Count("id"),
            fraudulent=Count("id", filter=Q(status=Transaction.Status.FRAUDULENT)),
            amount=Sum("amount"),
        )
    }
    par_canal = [
        {
            "channel": valeur,
            "label": libelle,
            "total": canaux.get(valeur, {}).get("total", 0),
            "fraudulent": canaux.get(valeur, {}).get("fraudulent", 0),
            "amount": float(canaux.get(valeur, {}).get("amount") or 0),
        }
        for valeur, libelle in Transaction.Channel.choices
    ]

    par_jour = [
        {
            "date": ligne["jour"].isoformat(),
            "total": ligne["total"],
            "fraudulent": ligne["fraudulent"],
            "flagged": ligne["flagged"],
        }
        for ligne in qs.annotate(jour=TruncDate("timestamp"))
        .values("jour")
        .annotate(
            total=Count("id"),
            fraudulent=Count("id", filter=Q(status=Transaction.Status.FRAUDULENT)),
            flagged=Count("id", filter=Q(prediction__prediction=True)),
        )
        .order_by("jour")
    ]

    return {
        "filters": {
            "date_after": date_after.isoformat() if date_after else None,
            "date_before": date_before.isoformat() if date_before else None,
            "channel": channel or None,
        },
        "kpis": {
            "total_transactions": total,
            "fraudulent_transactions": nb_fraudes,
            "fraud_rate": round(nb_fraudes / total * 100, 2) if total else 0.0,
            "amount_at_risk": float(montant_a_risque),
            "active_alerts": alertes_actives,
        },
        "by_status": par_statut,
        "by_channel": par_canal,
        "daily": par_jour,
        "confusion_matrix": matrice_de_confusion(qs),
        "active_model": modele_actif(),
    }
