from django.utils import timezone
from transactions.models import Customer, Transaction
from fraud_detection.models import Prediction
from fraud_detection.services import score_transaction

customer, created = Customer.objects.get_or_create(
    full_name="Client Test",
    defaults=dict(
        gender="F", date_of_birth="1990-03-19", city="Dakar", region="Dakar",
        city_population=1200000, profession="Sales professional, IT",
        latitude=14.7167, longitude=-17.4677,
    ),
)
print("Customer:", customer)

transaction, created = Transaction.objects.get_or_create(
    transaction_id="TEST-0001",
    defaults=dict(
        amount=45000, merchant="fraud_Kirlin and Sons", customer=customer,
        merchant_latitude=14.75, merchant_longitude=-17.5,
        category="achats_en_ligne", channel="online", timestamp=timezone.now(),
    ),
)
print("Transaction:", transaction)

# Supprime l'ancienne prediction pour pouvoir relancer ce test plusieurs fois
Prediction.objects.filter(transaction=transaction).delete()

resultat = score_transaction(transaction)
print("RESULTAT:", resultat.prediction, resultat.fraud_probability)