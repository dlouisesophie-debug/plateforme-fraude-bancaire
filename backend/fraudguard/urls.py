from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/auth/", include("authentication.urls")),
    path("api/transactions/", include("transactions.urls")),
    path("api/fraud-detection/", include("fraud_detection.urls")),
    path("api/alerts/", include("alerts.urls")),
    path("api/reports/", include("reports.urls")),
    path("api/audit/", include("audit.urls")),

    # Documentation Swagger / OpenAPI (CDC 5.3, section 7)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
