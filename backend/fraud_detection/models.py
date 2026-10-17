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

    version = models.CharField(max_length=50, unique=True)
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
                fields=["is_active"],
                condition=models.Q(is_active=True),
                name="single_active_model",
            )
        ]

    def __str__(self):
        return f"{self.algorithm} v{self.version}"


class Prediction(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name="prediction")
    ml_model = models.ForeignKey(MLModel, on_delete=models.PROTECT, related_name="predictions")
    fraud_probability = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    prediction = models.BooleanField(help_text="True = frauduleuse")
    prediction_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "predictions"
        indexes = [models.Index(fields=["fraud_probability"])]

    def __str__(self):
        return f"Prediction #{self.id} — {self.fraud_probability:.2%}"
