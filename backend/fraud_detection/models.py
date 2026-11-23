"""
App fraud_detection — CDC 5.3 : scoring automatique + suivi des modeles ML.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from transactions.models import Transaction


class MLModel(models.Model):
    """Suivi des modeles ML deployes (CDC 5.3 / 5.5)."""

    class Algorithm(models.TextChoices):
        LOGISTIC_REGRESSION = "logistic_regression", "Régression logistique"
        RANDOM_FOREST = "random_forest", "Random Forest"
        XGBOOST = "xgboost", "XGBoost"

    class Famille(models.TextChoices):
        # Chaque famille a son propre modèle fraude / non fraude et son seuil.
        CARTE = "carte", "Carte (et autres canaux)"
        MOBILE_MONEY = "mobile_money", "Mobile Money"

    version = models.CharField(max_length=50, unique=True)
    famille = models.CharField(
        # db_default : l'ancien code, qui ne connaît pas ce champ, peut toujours écrire en base.
        max_length=20, choices=Famille.choices, default=Famille.CARTE, db_default=Famille.CARTE,
        help_text="Un seul modèle actif par famille. Mobile Money : transactions du canal mobile money "
                  "avec un type d'opération ; carte : tous les autres cas.",
    )
    algorithm = models.CharField(max_length=50, choices=Algorithm.choices)
    precision_score = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    recall_score = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    f1_score = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    auc_roc = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    trained_at = models.DateTimeField()
    is_active = models.BooleanField(default=False)
    artifact_path = models.CharField(max_length=255, help_text="Chemin du fichier Joblib")

    class Meta:
        db_table = "ml_models"
        constraints = [
            models.UniqueConstraint(
                fields=["famille"],
                condition=models.Q(is_active=True),
                name="single_active_model_per_family",
            )
        ]

    def __str__(self):
        return f"{self.algorithm} v{self.version} ({self.famille})"


class Prediction(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name="prediction")
    ml_model = models.ForeignKey(MLModel, on_delete=models.PROTECT, related_name="predictions")
    fraud_probability = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    prediction = models.BooleanField(help_text="True = frauduleuse")
    # Seuil du modèle au moment du scoring : chaque famille a le sien (0,0652 carte,
    # 0,9307 mobile money), un score seul ne dit donc pas si la transaction est suspecte.
    decision_threshold = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Seuil de décision du modèle appliqué à ce score (vide pour les prédictions "
                  "antérieures à ce champ).",
    )
    prediction_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "predictions"
        indexes = [models.Index(fields=["fraud_probability"])]

    def __str__(self):
        return f"Prediction #{self.id} — {self.fraud_probability:.2%}"
