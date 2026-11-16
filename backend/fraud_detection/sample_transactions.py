"""
Transactions d'exemple pour les tests (valeurs valides pour le modele :
categories et regions connues, cf. pipeline["categories_connues"]).

- TRANSACTION_NORMALE : achat de 15 000 FCFA en journee -> score ~ 0.
- TRANSACTION_FRAUDE  : 600 000 FCFA a 23h30, categorie "courses" -> le
  modele la classe frauduleuse (probabilite ~ 1.0, seuil = 0.0652). Elle a
  ete trouvee en interrogeant le vrai pipeline, pas en forcant le score.
"""

TRANSACTION_NORMALE = {
    "transaction_id": "T-NORMALE-001",
    "amount": "15000",
    "merchant": "fraud_Kilback LLC",
    "device": "mobile",
    "location": "Dakar",
    "channel": "card",
    "timestamp": "2026-10-11T14:30:00Z",
    "category": "achats",
    "customer_gender": "F",
    "customer_birth_date": "1995-03-20",
    "customer_city": "Dakar",
    "customer_region": "Dakar",
    "customer_city_population": 1200000,
    "customer_profession": "Ingenieure",
    "customer_latitude": 14.6928,
    "customer_longitude": -17.4467,
    "merchant_latitude": 14.7167,
    "merchant_longitude": -17.4677,
}

TRANSACTION_FRAUDE = {
    "transaction_id": "T-FRAUDE-001",
    "amount": "600000",
    "merchant": "fraud_Wilkinson LLC",
    "device": "web",
    "location": "Richard-Toll",
    "channel": "online",
    "timestamp": "2026-10-11T23:30:00Z",
    "category": "courses",
    "customer_gender": "M",
    "customer_birth_date": "1963-05-02",
    "customer_city": "Richard-Toll",
    "customer_region": "Fatick",
    "customer_city_population": 50000,
    "customer_profession": "Geoscientist",
    "customer_latitude": 15.51034618905701,
    "customer_longitude": -13.76961263585134,
    "merchant_latitude": 14.898403094975828,
    "merchant_longitude": -14.017604647296018,
}

# Mobile money (modele PaySim, seuil 0.9307 ; montants en unite du simulateur,
# pas des FCFA). Trouves en interrogeant le vrai pipeline
# ml/models/fraudguard_mobile_money_pipeline.joblib, sans forcer le score :
# - retrait de 50 000 a 14 h  -> score ~ 0.37 : non fraude ;
# - transfert de 1 000 000 a 3 h -> score ~ 0.998 : fraude.
TRANSACTION_MM_NORMALE = {
    "transaction_id": "T-MM-NORMALE-001",
    "amount": "50000",
    "channel": "mobile_money",
    "operation_type": "cash_out",
    "timestamp": "2026-10-11T14:00:00Z",
}

TRANSACTION_MM_FRAUDE = {
    "transaction_id": "T-MM-FRAUDE-001",
    "amount": "1000000",
    "channel": "mobile_money",
    "operation_type": "transfer",
    "timestamp": "2026-10-11T03:00:00Z",
}
