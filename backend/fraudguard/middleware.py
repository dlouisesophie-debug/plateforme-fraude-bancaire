from django.db import connection
from django.http import JsonResponse

HEALTH_PATH = "/api/health/"


class HealthCheckMiddleware:
    """
    Contrôle de santé (Render, docker compose) : /api/health/.

    Placé en tête de MIDDLEWARE pour répondre AVANT la validation
    d'ALLOWED_HOSTS et la redirection HTTPS : la sonde de Render interroge
    le conteneur en HTTP, via son adresse interne, avec un en-tête Host qui
    n'est pas le nom public du service. Ne renvoie aucune donnée sensible.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == HEALTH_PATH and request.method in ("GET", "HEAD"):
            try:
                connection.ensure_connection()
            except Exception:
                return JsonResponse({"status": "erreur", "database": "injoignable"}, status=503)
            return JsonResponse({"status": "ok", "database": "ok"})
        return self.get_response(request)
