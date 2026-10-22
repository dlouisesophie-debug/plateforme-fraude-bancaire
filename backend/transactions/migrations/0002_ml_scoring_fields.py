from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Ajoute les champs necessaires au scoring ML (pipeline
    ml/models/fraudguard_pipeline.joblib) sur Transaction.

    Tous les nouveaux champs sont optionnels (null=True / blank=True ou
    valeur par defaut vide) pour ne pas casser les lignes existantes.
    """

    dependencies = [
        ("transactions", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="category",
            field=models.CharField(
                blank=True,
                default="",
                max_length=100,
                help_text="Categorie du commercant, parmi celles connues du modele ML (ex: achats, achats_en_ligne, courses, restauration, voyage...). Une categorie inconnue n'est pas prise en compte par le modele.",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="transaction",
            name="customer_gender",
            field=models.CharField(
                blank=True,
                choices=[("F", "Femme"), ("M", "Homme")],
                default="",
                max_length=1,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="transaction",
            name="customer_birth_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="transaction",
            name="customer_city",
            field=models.CharField(blank=True, default="", max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="transaction",
            name="customer_region",
            field=models.CharField(blank=True, default="", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="transaction",
            name="customer_city_population",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="transaction",
            name="customer_profession",
            field=models.CharField(blank=True, default="", max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="transaction",
            name="customer_latitude",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="transaction",
            name="customer_longitude",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="transaction",
            name="merchant_latitude",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="transaction",
            name="merchant_longitude",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
