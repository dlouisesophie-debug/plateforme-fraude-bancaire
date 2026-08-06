# ML — Pipeline de detection de fraude

Responsable : Étudiant 2 (Lead Data Scientist / ML Engineer)

## Structure

```
notebooks/    Notebooks d'exploration (EDA, comparaison de modeles)
data/raw/         Donnees brutes (non versionnees, voir .gitignore)
data/processed/   Donnees pretraitees (non versionnees)
src/          Code Python reutilisable (preprocessing, training, evaluation, predict)
models/       Modeles entraines exportes en .joblib (non versionnes, trop volumineux pour Git)
```

## Demarrage local

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
jupyter notebook notebooks/
```

## Important — lien avec le backend

Le fichier `src/preprocessing.py` doit rester la SEULE source de verite pour
le pretraitement. Le backend Django (`backend/fraud_detection/services.py`)
importera ce module directement (ou une copie synchronisee) pour garantir
que le scoring en production utilise exactement le meme pipeline qu'a
l'entrainement.

Une fois un modele entraine et exporte dans `models/`, informez Étudiant 1
pour qu'il l'enregistre dans la table `MLModel` (voir modele Django
`fraud_detection.models.MLModel`) et l'active (`is_active=True`).

## A faire (Sprint 1-2, voir roadmap)

- [ ] EDA complete dans `notebooks/01_eda.ipynb` (valeurs manquantes, desequilibre fraude/non-fraude)
- [ ] Implementer `src/preprocessing.py` (nettoyage + feature engineering)
- [ ] Entrainer et comparer les 3 modeles (`src/training.py`)
- [ ] Evaluer avec Precision/Recall/F1/AUC-ROC + matrice de confusion (`src/evaluation.py`)
- [ ] Choisir le seuil metier (coordonner avec Etudiant 1 — `FRAUD_ALERT_THRESHOLD` dans `.env`)
- [ ] Exporter le meilleur modele dans `models/` au format Joblib, versionne
