"""
Données de démonstration pour la soutenance.

    python manage.py seed_demo                      # 3 comptes + 40 transactions scorées
    python manage.py seed_demo --nombre 80 --reset  # repart de zéro
    python manage.py seed_demo --simuler-decisions  # un analyste traite une partie des alertes

Chaque transaction passe par le VRAI scoring ML (fraud_detection.services),
exactement comme une saisie depuis l'API : statut, score et alertes sont
donc ceux que produit le modèle, rien n'est forcé. Il faut un modèle actif
(`python manage.py activer_modele_ml fraudguard_pipeline.joblib`).

Comptes créés (mot de passe commun, modifiable avec --mot-de-passe) :
    admin.demo / analyste.demo / agent.demo
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction
from django.utils import timezone

from alerts.models import Alert
from fraud_detection.models import MLModel
from fraud_detection.services import score_transaction
from transactions.models import Transaction

User = get_user_model()

PREFIXE = "DEMO-"

# Villes et régions connues du jeu d'entraînement (pipeline["regions_connues"]).
VILLES = [
    ("Dakar", "Dakar", 1_200_000, 14.6928, -17.4467),
    ("Thiès", "Thiès", 320_000, 14.7910, -16.9359),
    ("Saint-Louis", "Saint-Louis", 210_000, 16.0179, -16.4896),
    ("Kaolack", "Kaolack", 230_000, 14.1652, -16.0726),
    ("Ziguinchor", "Ziguinchor", 205_000, 12.5641, -16.2640),
    ("Touba", "Diourbel", 750_000, 14.8500, -15.8833),
    ("Tambacounda", "Tambacounda", 107_000, 13.7707, -13.6673),
    ("Louga", "Louga", 104_000, 15.6144, -16.2286),
]
PROFESSIONS = ["Commerçant", "Enseignante", "Ingénieur", "Infirmière", "Chauffeur", "Comptable"]
COMMERCANTS = ["Auchan Sénégal", "Orange Money", "Wave", "Total Énergies", "Jumia", "Pharmacie du Plateau"]

# Profil « habituel » : petits montants, en journée, catégories du quotidien.
CATEGORIES_HABITUELLES = ["restauration", "sante_sport", "maison", "soins_personnels", "divertissement"]
# Profil « à risque » observé à l'EDA : gros montants, la nuit, achats en ligne / courses.
CATEGORIES_A_RISQUE = ["achats_en_ligne", "courses", "divers_en_ligne", "courses_en_ligne"]


def _transaction_aleatoire(rng, numero, a_risque, jours):
    ville, region, population, lat, lon = rng.choice(VILLES)
    jour = timezone.localdate() - timedelta(days=rng.randrange(jours))
    if a_risque:
        heure = rng.choice([0, 1, 2, 3, 22, 23])
        montant = rng.randrange(250_000, 750_000, 5_000)
        categorie = rng.choice(CATEGORIES_A_RISQUE)
        ecart = rng.uniform(0.5, 1.2)  # commerçant éloigné du client
        canal = rng.choice(["online", "card", "transfer"])
    else:
        heure = rng.randrange(8, 20)
        montant = rng.randrange(2_000, 60_000, 500)
        categorie = rng.choice(CATEGORIES_HABITUELLES)
        ecart = rng.uniform(0.01, 0.2)
        canal = rng.choice(["card", "mobile_money", "mobile_money", "online"])
    horodatage = timezone.make_aware(
        timezone.datetime(jour.year, jour.month, jour.day, heure, rng.randrange(60))
    )
    return {
        "transaction_id": f"{PREFIXE}{numero:03d}",
        "amount": Decimal(montant),
        "merchant": rng.choice(COMMERCANTS),
        "device": rng.choice(["mobile", "web", "tpe"]),
        "location": ville,
        "channel": canal,
        "timestamp": horodatage,
        "category": categorie,
        "customer_gender": rng.choice(["F", "M"]),
        "customer_birth_date": date(rng.randrange(1955, 2004), rng.randrange(1, 13), rng.randrange(1, 28)),
        "customer_city": ville,
        "customer_region": region,
        "customer_city_population": population,
        "customer_profession": rng.choice(PROFESSIONS),
        "customer_latitude": lat,
        "customer_longitude": lon,
        "merchant_latitude": lat + rng.uniform(-ecart, ecart),
        "merchant_longitude": lon + rng.uniform(-ecart, ecart),
    }


class Command(BaseCommand):
    help = "Crée des comptes et des transactions de démonstration, scorées par le modèle ML actif."

    def add_arguments(self, parser):
        parser.add_argument("--nombre", type=int, default=40, help="Nombre de transactions (défaut : 40).")
        parser.add_argument("--part-a-risque", type=float, default=0.25,
                            help="Proportion de transactions au profil à risque (défaut : 0.25).")
        parser.add_argument("--jours", type=int, default=14, help="Étalement sur N jours (défaut : 14).")
        parser.add_argument("--mot-de-passe", default="FraudGuard2026!", help="Mot de passe des comptes démo.")
        parser.add_argument("--reset", action="store_true", help="Supprime d'abord les transactions DEMO-*.")
        parser.add_argument("--simuler-decisions", action="store_true",
                            help="L'analyste démo confirme ou rejette environ 2 alertes sur 3.")
        parser.add_argument("--graine", type=int, default=42, help="Graine aléatoire (reproductible).")

    def handle(self, *args, **options):
        if not MLModel.objects.filter(is_active=True).exists():
            raise CommandError(
                "Aucun modèle ML actif. Lancez d'abord : "
                "python manage.py activer_modele_ml fraudguard_pipeline.joblib"
            )

        comptes = self._creer_comptes(options["mot_de_passe"])

        if options["reset"]:
            supprimees, _ = Transaction.objects.filter(transaction_id__startswith=PREFIXE).delete()
            self.stdout.write(f"Anciennes données de démo supprimées ({supprimees} objets).")

        rng = random.Random(options["graine"])
        depart = Transaction.objects.filter(transaction_id__startswith=PREFIXE).count() + 1
        nb_alertes = 0
        for numero in range(depart, depart + options["nombre"]):
            donnees = _transaction_aleatoire(
                rng, numero, rng.random() < options["part_a_risque"], options["jours"],
            )
            with db_transaction.atomic():
                t = Transaction.objects.create(created_by=comptes["agent"], **donnees)
                prediction = score_transaction(t)
            nb_alertes += int(prediction.prediction)

        if options["simuler_decisions"]:
            self._simuler_decisions(rng, comptes["analyste"])

        self.stdout.write(self.style.SUCCESS(
            f"{options['nombre']} transactions de démo créées et scorées, dont {nb_alertes} signalées "
            f"par le modèle. Comptes : admin.demo / analyste.demo / agent.demo "
            f"(mot de passe : {options['mot_de_passe']})."
        ))

    def _creer_comptes(self, mot_de_passe):
        comptes = {}
        for cle, username, role, prenom in [
            ("admin", "admin.demo", "admin", "Admin"),
            ("analyste", "analyste.demo", "analyst", "Analyste"),
            ("agent", "agent.demo", "agent", "Agent"),
        ]:
            user, cree = User.objects.get_or_create(
                username=username,
                defaults={"role": role, "first_name": prenom, "last_name": "Démo",
                          "email": f"{username}@fraudguard.local"},
            )
            if cree:
                user.set_password(mot_de_passe)
                user.save()
            comptes[cle] = user
        return comptes

    def _simuler_decisions(self, rng, analyste):
        """
        Simule le travail d'un analyste pour que le dashboard (matrice de
        confusion) et la page Alertes aient des données variées. Les alertes
        à très forte probabilité sont plutôt confirmées, les autres plutôt
        rejetées ; une alerte sur trois reste ouverte pour la démo en direct.
        """
        ouvertes = Alert.objects.filter(
            status=Alert.Status.OPEN, prediction__transaction__transaction_id__startswith=PREFIXE,
        ).select_related("prediction__transaction")
        for alerte in ouvertes:
            if rng.random() < 1 / 3:
                continue
            fraude = rng.random() < alerte.prediction.fraud_probability
            alerte.status = Alert.Status.CONFIRMED if fraude else Alert.Status.REJECTED
            alerte.assigned_to = analyste
            alerte.resolved_at = timezone.now()
            alerte.comment = "Décision simulée (données de démonstration)."
            alerte.save()
            t = alerte.prediction.transaction
            t.status = Transaction.Status.FRAUDULENT if fraude else Transaction.Status.LEGITIMATE
            t.save(update_fields=["status"])
