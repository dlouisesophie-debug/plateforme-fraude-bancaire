from django.contrib import admin

from .models import MLModel, Prediction


@admin.register(MLModel)
class MLModelAdmin(admin.ModelAdmin):
    list_display = ["version", "algorithm", "is_active", "trained_at", "f1_score", "auc_roc"]
    list_filter = ["algorithm", "is_active"]


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ["transaction", "ml_model", "fraud_probability", "prediction", "prediction_date"]
    list_filter = ["prediction"]
