"""
Génération des fichiers de rapport (CDC 5.5) : CSV et PDF.

Les chiffres du rapport viennent de dashboard.services : un rapport et le
dashboard filtré sur la même période affichent exactement les mêmes valeurs.
"""

from pathlib import Path

from django.conf import settings
from django.utils import timezone

from dashboard.services import calculer_statistiques, filtrer_transactions
from transactions.exports import EN_TETES, ecrire_csv, lignes_transactions

# Nombre maximal de transactions détaillées dans le PDF (le CSV, lui, est complet).
MAX_LIGNES_PDF = 200


def _format_fcfa(valeur):
    return f"{valeur:,.0f}".replace(",", " ") + " FCFA"


def _format_pct(valeur):
    return "—" if valeur is None else f"{valeur * 100:.1f} %"


def _chemin_rapport(report):
    dossier = Path(settings.REPORTS_DIR)
    dossier.mkdir(parents=True, exist_ok=True)
    horodatage = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    return dossier / f"rapport_{report.id}_{horodatage}.{report.type}"


def generer_csv(report, chemin):
    qs = filtrer_transactions(report.period_start, report.period_end).order_by("-timestamp")
    with open(chemin, "w", encoding="utf-8", newline="") as fichier:
        ecrire_csv(qs, fichier)


def generer_pdf(report, chemin):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    stats = calculer_statistiques(report.period_start, report.period_end)
    kpis = stats["kpis"]
    matrice = stats["confusion_matrix"]
    styles = getSampleStyleSheet()
    bleu_nuit = colors.HexColor("#0F1B33")

    def tableau(donnees, largeurs=None, entete=True):
        t = Table(donnees, colWidths=largeurs, repeatRows=1 if entete else 0, hAlign="LEFT")
        style = [
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9CED6")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
        if entete:
            style += [
                ("BACKGROUND", (0, 0), (-1, 0), bleu_nuit),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        t.setStyle(TableStyle(style))
        return t

    periode = "Toutes les transactions"
    if report.period_start or report.period_end:
        debut = report.period_start.strftime("%d/%m/%Y") if report.period_start else "…"
        fin = report.period_end.strftime("%d/%m/%Y") if report.period_end else "…"
        periode = f"Période du {debut} au {fin}"
    auteur = report.generated_by.get_full_name() or report.generated_by.username if report.generated_by else "—"

    elements = [
        Paragraph(f"FraudGuard — {report.title}", styles["Title"]),
        Paragraph(
            f"{periode} · généré le {timezone.localtime():%d/%m/%Y à %H:%M} par {auteur}",
            styles["Normal"],
        ),
        Spacer(1, 0.5 * cm),
        Paragraph("Indicateurs clés", styles["Heading2"]),
        tableau([
            ["Volume total", "Transactions frauduleuses", "Taux de fraude", "Montant à risque", "Alertes actives"],
            [
                str(kpis["total_transactions"]), str(kpis["fraudulent_transactions"]),
                f"{kpis['fraud_rate']:.2f} %", _format_fcfa(kpis["amount_at_risk"]),
                str(kpis["active_alerts"]),
            ],
        ]),
        Spacer(1, 0.4 * cm),
        Paragraph("Répartition par canal", styles["Heading2"]),
        tableau(
            [["Canal", "Transactions", "Frauduleuses", "Montant"]]
            + [
                [c["label"], str(c["total"]), str(c["fraudulent"]), _format_fcfa(c["amount"])]
                for c in stats["by_channel"]
            ]
        ),
        Spacer(1, 0.4 * cm),
        Paragraph("Performance du modèle en production (matrice de confusion)", styles["Heading2"]),
        tableau([
            ["", "Prédit fraude", "Prédit normal"],
            ["Fraude réelle", str(matrice["true_positive"]), str(matrice["false_negative"])],
            ["Légitime réelle", str(matrice["false_positive"]), str(matrice["true_negative"])],
        ]),
        Paragraph(
            f"Précision : {_format_pct(matrice['precision'])} · Rappel : {_format_pct(matrice['recall'])} "
            f"· {matrice['evaluated']} transactions tranchées",
            styles["Normal"],
        ),
        Spacer(1, 0.4 * cm),
    ]

    lignes = list(lignes_transactions(
        filtrer_transactions(report.period_start, report.period_end).order_by("-timestamp")[:MAX_LIGNES_PDF]
    ))
    elements.append(Paragraph(
        f"Détail des transactions ({len(lignes)} plus récentes, maximum {MAX_LIGNES_PDF})",
        styles["Heading2"],
    ))
    colonnes = [0, 1, 2, 3, 4, 8, 9, 10]  # sous-ensemble lisible en A4 paysage
    elements.append(tableau(
        [[EN_TETES[i] for i in colonnes]] + [[str(ligne[i]) for i in colonnes] for ligne in lignes]
    ) if lignes else Paragraph("Aucune transaction sur la période.", styles["Normal"]))

    document = SimpleDocTemplate(
        str(chemin), pagesize=landscape(A4),
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title=report.title, author="FraudGuard",
    )
    document.build(elements)


def generer_fichier(report):
    """Génère le fichier du rapport, renseigne `file_path` et le renvoie."""
    chemin = _chemin_rapport(report)
    if report.type == report.ReportType.CSV:
        generer_csv(report, chemin)
    else:
        generer_pdf(report, chemin)
    report.file_path = str(chemin.relative_to(settings.MEDIA_ROOT))
    report.save(update_fields=["file_path"])
    return chemin
