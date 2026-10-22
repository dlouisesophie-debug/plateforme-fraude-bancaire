"""
Tests de la configuration de déploiement (Étudiant 4 — DevOps) :
contrôle de santé et redirection HTTPS de production.
"""

from django.test import TestCase, override_settings


class HealthCheckTests(TestCase):
    def test_health_repond_ok_sans_authentification(self):
        reponse = self.client.get("/api/health/")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.json(), {"status": "ok", "database": "ok"})


@override_settings(SECURE_SSL_REDIRECT=True)
class HttpsProductionTests(TestCase):
    def test_http_redirige_vers_https(self):
        reponse = self.client.get("/api/transactions/")
        self.assertEqual(reponse.status_code, 301)
        self.assertTrue(reponse["Location"].startswith("https://"))

    def test_https_derriere_proxy_render_non_redirige(self):
        # Render termine le TLS et transmet X-Forwarded-Proto: https.
        reponse = self.client.get("/api/transactions/", HTTP_X_FORWARDED_PROTO="https")
        self.assertEqual(reponse.status_code, 401)  # atteint l'API (JWT requis)

    def test_health_exempte_de_redirection(self):
        reponse = self.client.get("/api/health/")
        self.assertEqual(reponse.status_code, 200)

    @override_settings(ALLOWED_HOSTS=["fraudguard-api.onrender.com"])
    def test_health_repond_a_la_sonde_interne_de_render(self):
        # La sonde Render utilise l'adresse interne du conteneur comme Host.
        reponse = self.client.get("/api/health/", HTTP_HOST="10.201.3.7:10000")
        self.assertEqual(reponse.status_code, 200)

    @override_settings(ALLOWED_HOSTS=["fraudguard-api.onrender.com"])
    def test_api_refuse_un_hote_inconnu(self):
        reponse = self.client.get("/api/transactions/", HTTP_HOST="pirate.example",
                                  HTTP_X_FORWARDED_PROTO="https")
        self.assertEqual(reponse.status_code, 400)
