"""
Export CSV des transactions (CDC 5.2 « exporter », 5.5 « rapports CSV »).

Séparateur « ; » et encodage UTF-8 avec BOM : le fichier s'ouvre
directement dans Excel en français, accents compris.
"""

import csv

EN_TETES = [
    "ID transaction", "Date", "Montant (FCFA)", "Canal", "Commerçant",
    "Catégorie", "Ville client", "Région client", "Statut",
    "Probabilité de fraude (%)", "Prédiction modèle", "Version modèle",
]


def lignes_transactions(queryset):
    """Génère une ligne (liste de valeurs) par transaction, score inclus."""
    for t in queryset.select_related("prediction__ml_model"):
        # Relation inverse OneToOne absente -> RelatedObjectDoesNotExist
        # (sous-classe d'AttributeError), donc getattr renvoie None.
        prediction = getattr(t, "prediction", None)
        yield [
            t.transaction_id,
            t.timestamp.strftime("%Y-%m-%d %H:%M"),
            f"{t.amount:.2f}".replace(".", ","),
            t.get_channel_display(),
            t.merchant,
            t.category,
            t.customer_city,
            t.customer_region,
            t.get_status_display(),
            f"{prediction.fraud_probability * 100:.2f}".replace(".", ",") if prediction else "",
            ("Fraude" if prediction.prediction else "Normale") if prediction else "Non scorée",
            prediction.ml_model.version if prediction else "",
        ]


def ecrire_csv(queryset, fichier):
    """Écrit le CSV des transactions dans un objet fichier texte ouvert."""
    fichier.write("﻿")  # BOM UTF-8 pour Excel
    writer = csv.writer(fichier, delimiter=";")
    writer.writerow(EN_TETES)
    for ligne in lignes_transactions(queryset):
        writer.writerow(ligne)
