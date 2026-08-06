"""
FraudGuard — Modèles Django
Traduction du MCD/MLD PostgreSQL en modèles Django ORM.
Compatible Django + Django REST Framework + Simple JWT.
"""

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class User(models.Model):
    """
    Remplace/étend AbstractUser si utilisé avec Django auth natif.
    Ici représenté en modèle autonome pour refléter fidèlement le MCD ;
    en pratique, hériter de AbstractBaseUser + PermissionsMixin est recommandé.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrateur"
        ANALYST = "analyst", "Analyste Fraude"
        AGENT = "agent", "Agent Financier"

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"


class MLModel(models.Model):
    """Suivi des modèles ML déployés — métriques et traçabilité (CDC 5.3/5.5)."""

    class Algorithm(models.TextChoices):
        LOGISTIC_REGRESSION = "logistic_regression", "Régression logistique"
        RANDOM_FOREST = "random_forest", "Random Forest"
        XGBOOST = "xgboost", "XGBoost"

    version = models.CharField(max_length=50, unique=True)
    algorithm = models.CharField(max_length=50, choices=Algorithm.choices)
    precision_score = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    recall_score = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    f1_score = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    auc_roc = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
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


class Transaction(models.Model):
    """CDC 5.2 — Gestion des transactions."""

    class Channel(models.TextChoices):
        CARD = "card", "Carte"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        TRANSFER = "transfer", "Virement"
        ONLINE = "online", "Paiement en ligne"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        LEGITIMATE = "legitimate", "Légitime"
        FRAUDULENT = "fraudulent", "Frauduleuse"
        UNDER_REVIEW = "under_review", "En cours d'examen"

    transaction_id = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    merchant = models.CharField(max_length=255, blank=True)
    device = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=255, blank=True)
    channel = models.CharField(max_length=30, choices=Channel.choices)
    timestamp = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transactions"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["channel"]),
        ]

    def __str__(self):
        return self.transaction_id


class Prediction(models.Model):
    """CDC 5.3 — Scoring automatique de chaque transaction."""

    transaction = models.OneToOneField(
        Transaction, on_delete=models.CASCADE, related_name="prediction"
    )
    ml_model = models.ForeignKey(
        MLModel, on_delete=models.PROTECT, related_name="predictions"
    )
    fraud_probability = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    prediction = models.BooleanField(help_text="True = frauduleuse")
    prediction_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "predictions"
        indexes = [
            models.Index(fields=["fraud_probability"]),
        ]

    def __str__(self):
        return f"Prediction #{self.id} — {self.fraud_probability:.2%}"


class Alert(models.Model):
    """CDC 5.3/5.4 — Alerte déclenchée si score > seuil configurable."""

    class Status(models.TextChoices):
        OPEN = "open", "Ouverte"
        CONFIRMED = "confirmed", "Fraude confirmée"
        REJECTED = "rejected", "Rejetée"
        RESOLVED = "resolved", "Résolue"

    class Severity(models.TextChoices):
        LOW = "low", "Faible"
        MEDIUM = "medium", "Moyenne"
        HIGH = "high", "Élevée"
        CRITICAL = "critical", "Critique"

    prediction = models.OneToOneField(
        Prediction, on_delete=models.CASCADE, related_name="alert"
    )
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_alerts",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "alerts"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["severity"]),
        ]

    def __str__(self):
        return f"Alert #{self.id} ({self.status})"


class Report(models.Model):
    """CDC 5.5 — Génération de rapports (PDF/CSV)."""

    class ReportType(models.TextChoices):
        PDF = "pdf", "PDF"
        CSV = "csv", "CSV"

    title = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=ReportType.choices)
    generated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reports",
    )
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    file_path = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reports"

    def __str__(self):
        return self.title


class AuditLog(models.Model):
    """CDC section 6 — Traçabilité des accès aux données sensibles."""

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.action} — {self.created_at}"
