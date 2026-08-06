from rest_framework.routers import DefaultRouter

from .views import MLModelViewSet, PredictionViewSet

router = DefaultRouter()
router.register("models", MLModelViewSet, basename="mlmodel")
router.register("predictions", PredictionViewSet, basename="prediction")

urlpatterns = router.urls
