(
echo from django.utils import timezone
echo from transactions.models import Customer, Transaction
echo from fraud_detection.services import score_transaction
echo.
echo customer, created = Customer.objects.get_or_create^(full_name="Client Test", defaults=dict^(gender="F", date_of_birth="1990-03-19", city="Dakar", region="Dakar", city_population=1200000, profession="Sales professional, IT", latitude=14.7167, longitude=-17.4677^)^)
echo print^("Customer:", customer^)
echo.
echo transaction, created = Transaction.objects.get_or_create^(transaction_id="TEST-0001", defaults=dict^(amount=45000, merchant="fraud_Kirlin and Sons", customer=customer, merchant_latitude=14.75, merchant_longitude=-17.5, category="achats_en_ligne", channel="online", timestamp=timezone.now^(^)^)^)
echo print^("Transaction:", transaction^)
echo.
echo resultat = score_transaction^(transaction^)
echo print^("RESULTAT:", resultat.prediction, resultat.fraud_probability^)
) > test_scoring.py