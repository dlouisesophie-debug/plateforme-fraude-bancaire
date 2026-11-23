"""
Mesure des exigences de performance du CDC : scoring d'une transaction en
moins de 500 ms, tableau de bord en moins de 2 s.

    python manage.py mesurer_performances                  # 50 saisies, 20 tableaux de bord
    python manage.py mesurer_performances --volume 10000   # tableau de bord avec 10 000 transactions de plus

Les requêtes passent par toute la pile Django (middlewares, authentification,
permissions, sérialisation, base, modèle ML), comme une saisie depuis l'API,
mais sans le réseau ni Gunicorn : ce sont des temps « côté serveur ».

Rien n'est conservé : tout se déroule dans une transaction de base annulée à
la fin (transactions saisies, alertes, journal d'audit, volume ajouté).
"""

import statistics
import time
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction
from django.test.utils import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from authentication.models import User
from fraud_detection.models import MLModel
from fraud_detection.sample_transactions import (
    TRANSACTION_FRAUDE, TRANSACTION_MM_FRAUDE, TRANSACTION_MM_NORMALE, TRANSACTION_NORMALE,
)
from transactions.models import Transaction

SEUIL_SCORING_MS = 500
SEUIL_DASHBOARD_MS = 2000


class _Annulation(Exception):
    """Levée en fin de mesure pour annuler la transaction de base."""


def _resume(durees_ms):
    triees = sorted(durees_ms)
    p95 = triees[max(0, round(0.95 * len(triees)) - 1)]
    return {"médiane": statistics.median(triees), "p95": p95, "max": triees[-1]}


class Command(BaseCommand):
    help = "Mesure le temps de scoring (saisie API) et du tableau de bord, sans rien conserver en base."

    def add_arguments(self, parser):
        parser.add_argument("--saisies", type=int, default=50, help="Nombre de saisies mesurées (défaut : 50).")
        parser.add_argument("--dashboards", type=int, default=20,
                            help="Nombre d'appels au tableau de bord mesurés (défaut : 20).")
        parser.add_argument("--volume", type=int, default=0,
                            help="Transactions ajoutées (sans scoring) avant de mesurer le tableau de bord.")

    def handle(self, *args, **options):
        if not MLModel.objects.filter(is_active=True, famille=MLModel.Famille.CARTE).exists():
            raise CommandError("Aucun modèle carte actif : lancez d'abord activer_modele_ml.")
        mm_actif = MLModel.objects.filter(is_active=True, famille=MLModel.Famille.MOBILE_MONEY).exists()

        resultats = {}
        try:
            # testserver + pas de redirection HTTPS : requêtes internes au processus.
            with override_settings(ALLOWED_HOSTS=["testserver"], SECURE_SSL_REDIRECT=False), \
                    db_transaction.atomic():
                resultats = self._mesurer(options, mm_actif)
                raise _Annulation
        except _Annulation:
            pass

        self._afficher(resultats, options)

    def _mesurer(self, options, mm_actif):
        agent = User.objects.create_user(username="mesure.perf.agent", password=None, role="agent")
        client = APIClient()
        client.force_authenticate(agent)

        exemples = [TRANSACTION_NORMALE, TRANSACTION_FRAUDE]
        if mm_actif:
            exemples += [TRANSACTION_MM_NORMALE, TRANSACTION_MM_FRAUDE]

        durees = []
        for i in range(options["saisies"] + 1):  # +1 : premier appel (chargement du modèle) à part
            donnees = dict(exemples[i % len(exemples)], transaction_id=f"PERF-{i:05d}")
            debut = time.perf_counter()
            reponse = client.post("/api/transactions/", donnees, format="json")
            durees.append((time.perf_counter() - debut) * 1000)
            if reponse.status_code != 201:
                raise CommandError(f"Saisie refusée ({reponse.status_code}) : {reponse.content[:300]!r}")
            if reponse.json().get("fraud_probability") is None:
                raise CommandError("Transaction non scorée : le modèle ML n'a pas répondu.")

        if options["volume"]:
            self._ajouter_volume(options["volume"])

        nb_transactions = Transaction.objects.count()
        durees_dashboard = []
        for _ in range(options["dashboards"]):
            debut = time.perf_counter()
            reponse = client.get("/api/dashboard/stats/")
            durees_dashboard.append((time.perf_counter() - debut) * 1000)
            if reponse.status_code != 200:
                raise CommandError(f"Tableau de bord en erreur ({reponse.status_code}).")

        return {
            "premier_scoring": durees[0],
            "scoring": _resume(durees[1:]),
            "dashboard": _resume(durees_dashboard),
            "nb_transactions": nb_transactions,
        }

    def _ajouter_volume(self, nombre):
        maintenant = timezone.now()
        canaux = [c for c, _ in Transaction.Channel.choices]
        statuts = [s for s, _ in Transaction.Status.choices]
        Transaction.objects.bulk_create(
            [
                Transaction(
                    transaction_id=f"PERF-VOL-{i:07d}", amount=Decimal(5_000 + (i % 400) * 1_000),
                    channel=canaux[i % len(canaux)], status=statuts[i % len(statuts)],
                    timestamp=maintenant - timedelta(minutes=17 * i),
                )
                for i in range(nombre)
            ],
            batch_size=2_000,
        )

    def _afficher(self, r, options):
        def ligne(nom, valeurs, seuil):
            verdict = "OK" if valeurs["p95"] < seuil else "AU-DESSUS DU SEUIL"
            self.stdout.write(
                f"{nom} : médiane {valeurs['médiane']:.0f} ms · p95 {valeurs['p95']:.0f} ms · "
                f"max {valeurs['max']:.0f} ms (exigence < {seuil} ms) → {verdict}"
            )

        self.stdout.write(f"Premier scoring (chargement du modèle compris) : {r['premier_scoring']:.0f} ms")
        ligne(f"Scoring, {options['saisies']} saisies via l'API", r["scoring"], SEUIL_SCORING_MS)
        ligne(
            f"Tableau de bord, {options['dashboards']} appels sur {r['nb_transactions']} transactions",
            r["dashboard"], SEUIL_DASHBOARD_MS,
        )
        self.stdout.write("Mesures côté serveur (sans réseau). Aucune donnée conservée en base.")
