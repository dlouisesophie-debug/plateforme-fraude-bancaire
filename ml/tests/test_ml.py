"""
Tests du code ML (sans le vrai CSV : donnees synthetiques).

    cd ml
    python -m unittest discover -s tests -v
"""

import json
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.metrics import recall_score

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import evaluation  # noqa: E402
import predict  # noqa: E402
import preprocessing  # noqa: E402
import training  # noqa: E402

warnings.filterwarnings("ignore")

CATEGORIES = ["achats", "courses", "voyage", "sante_sport"]
REGIONS = ["Dakar", "Thiès", "Louga", "Matam"]


def donnees_synthetiques(n=6000, taux_fraude=0.06, graine=0) -> pd.DataFrame:
    """Petit jeu de donnees au meme format que fraudTest_senegal.csv, avec un vrai signal."""
    rng = np.random.default_rng(graine)
    fraude = (rng.random(n) < taux_fraude).astype(int)
    dates = pd.Timestamp("2020-06-21") + pd.to_timedelta(rng.integers(0, 60 * 24 * 3600, n), unit="s")
    lat = rng.uniform(14, 15, n)
    lon = rng.uniform(-17, -16, n)
    # les fraudes : montants plus eleves, commercants plus eloignes
    df = pd.DataFrame({
        "date_transaction": dates,
        "date_naissance": pd.Timestamp("1960-01-01") + pd.to_timedelta(rng.integers(0, 40 * 365, n), unit="D"),
        "montant_fcfa": np.where(fraude == 1, rng.normal(60000, 15000, n), rng.normal(15000, 8000, n)).clip(100),
        "genre": rng.choice(["F", "M"], n),
        "population_ville": rng.integers(1000, 500000, n),
        "latitude_client": lat, "longitude_client": lon,
        "latitude_commercant": lat + np.where(fraude == 1, rng.normal(0.6, 0.1, n), rng.normal(0.05, 0.03, n)),
        "longitude_commercant": lon + np.where(fraude == 1, rng.normal(0.6, 0.1, n), rng.normal(0.05, 0.03, n)),
        "commercant": rng.choice([f"fraud_M{i}" for i in range(20)], n),
        "ville": rng.choice([f"Ville{i}" for i in range(15)], n),
        "profession": rng.choice([f"Metier{i}" for i in range(10)], n),
        "categorie": rng.choice(CATEGORIES, n),
        "region": rng.choice(REGIONS, n),
        "est_fraude": fraude,
    })
    return df


class DecoupageTests(unittest.TestCase):
    def setUp(self):
        self.df = donnees_synthetiques()
        self.train, self.val, self.test = training.decouper(self.df)

    def test_proportions_60_20_20(self):
        n = len(self.df)
        self.assertAlmostEqual(len(self.train) / n, 0.6, delta=0.01)
        self.assertAlmostEqual(len(self.val) / n, 0.2, delta=0.01)
        self.assertAlmostEqual(len(self.test) / n, 0.2, delta=0.01)

    def test_les_trois_jeux_sont_disjoints_et_complets(self):
        a, b, c = set(self.train.index), set(self.val.index), set(self.test.index)
        self.assertFalse(a & b or a & c or b & c)
        self.assertEqual(len(a | b | c), len(self.df))

    def test_stratification_du_taux_de_fraude(self):
        taux = self.df.est_fraude.mean()
        for jeu in (self.train, self.val, self.test):
            self.assertAlmostEqual(jeu.est_fraude.mean(), taux, delta=0.005)


class PretraitementTests(unittest.TestCase):
    def setUp(self):
        self.df = donnees_synthetiques(n=2000)
        self.train, self.val, _ = training.decouper(self.df)
        self.tables = training.tables_de_reference(self.train, self.df)

    def test_tables_de_frequence_calculees_sur_le_train_seul(self):
        inconnu = self.val.copy()
        inconnu["commercant"] = "fraud_Jamais_Vu"
        X = training.construire_matrice(inconnu, self.tables, training.liste_colonnes(self.tables))
        self.assertTrue((X["commercant_freq"] == 0.0).all())  # inconnu => 0.0, comme au scoring
        total = sum(self.tables["freq_commercant"].values())
        self.assertAlmostEqual(total, 1.0, places=6)

    def test_matrice_vectorisee_identique_au_pretraitement_ligne_par_ligne(self):
        """training.py et le backend (preprocessing.construire_features) donnent les memes features."""
        colonnes = training.liste_colonnes(self.tables)
        X = training.construire_matrice(self.val, self.tables, colonnes)
        for i in range(0, len(self.val), 37):
            ligne = self.val.iloc[i]
            transaction = {c: ligne[c] for c in self.val.columns if c != "est_fraude"}
            attendu = preprocessing.construire_features(
                transaction, colonnes, self.tables["freq_commercant"],
                self.tables["freq_ville"], self.tables["freq_profession"],
            )
            obtenu = X.iloc[i].to_dict()
            for col in colonnes:
                self.assertAlmostEqual(float(attendu[col]), float(obtenu[col]), places=6, msg=col)

    def test_sans_genre_retire_la_colonne(self):
        avec = training.liste_colonnes(self.tables, avec_genre=True)
        sans = training.liste_colonnes(self.tables, avec_genre=False)
        self.assertIn("genre", avec)
        self.assertNotIn("genre", sans)
        self.assertEqual([c for c in avec if c != "genre"], sans)


class AbsenceDeFuiteTests(unittest.TestCase):
    def test_smote_est_dans_le_pipeline_pour_les_trois_modeles(self):
        for fabrique in (training.pipeline_xgboost, training.pipeline_logistique, training.pipeline_random_forest):
            p = fabrique()
            self.assertIsInstance(p, ImbPipeline)
            self.assertEqual([nom for nom, _ in p.steps], ["smote", "clf"])

    def test_la_recherche_d_hyperparametres_utilise_le_pipeline_avec_smote(self):
        df = donnees_synthetiques()
        train, _, _ = training.decouper(df)
        tables = training.tables_de_reference(train, df)
        X = training.construire_matrice(train, tables, training.liste_colonnes(tables))
        recherche = training.rechercher_hyperparametres(X, train.est_fraude.values, n_iter=1, cv=2)
        self.assertEqual([n for n, _ in recherche.estimator.steps], ["smote", "clf"])
        self.assertEqual(recherche.scoring, "average_precision")

    def test_la_prediction_ne_reechantillonne_pas(self):
        """SMOTE ne s'applique qu'a fit : predict garde exactement le nombre de lignes."""
        df = donnees_synthetiques()
        train, val, _ = training.decouper(df)
        tables = training.tables_de_reference(train, df)
        col = training.liste_colonnes(tables)
        Xtr, Xva = (training.construire_matrice(d, tables, col) for d in (train, val))
        p = training.pipeline_logistique().fit(Xtr, train.est_fraude.values)
        self.assertEqual(len(p.predict_proba(Xva)), len(Xva))


class EvaluationTests(unittest.TestCase):
    def test_seuil_choisi_sur_la_validation_atteint_le_rappel_cible(self):
        rng = np.random.default_rng(1)
        y = (rng.random(5000) < 0.05).astype(int)
        proba = np.clip(0.5 * y + rng.normal(0.2, 0.15, 5000), 0, 1)
        seuil = evaluation.choisir_seuil(y, proba, recall_cible=0.85)
        self.assertGreaterEqual(recall_score(y, (proba >= seuil).astype(int)), 0.85)

    def test_matrice_de_confusion_coherente(self):
        y = np.array([0, 0, 0, 1, 1, 0, 1, 0])
        proba = np.array([0.1, 0.2, 0.7, 0.9, 0.3, 0.1, 0.8, 0.2])
        m = evaluation.evaluer(y, proba, 0.5)
        self.assertEqual(m["matrice_confusion"], [[4, 1], [1, 2]])
        self.assertAlmostEqual(m["recall"], 2 / 3)
        self.assertAlmostEqual(m["precision"], 2 / 3)

    def test_png_de_la_matrice_de_confusion(self):
        y = np.array([0, 0, 1, 1, 0, 1])
        proba = np.array([0.1, 0.6, 0.9, 0.4, 0.2, 0.8])
        with tempfile.TemporaryDirectory() as d:
            chemin = evaluation.plot_confusion_matrix(y, proba, 0.5, str(Path(d) / "cm.png"))
            octets = Path(chemin).read_bytes()
        self.assertTrue(octets.startswith(b"\x89PNG"))
        self.assertGreater(len(octets), 5000)


class EntrainementDeBoutEnBoutTests(unittest.TestCase):
    """Lance training.entrainer sur des donnees synthetiques, puis score avec predict.py."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        racine = Path(cls.tmp.name)
        cls.df = donnees_synthetiques()
        cls.csv = racine / "donnees.csv"
        cls.df.to_csv(cls.csv, index=False)
        cls.pipeline = training.entrainer(
            str(cls.csv), str(racine / "models"), str(racine / "rapports"), n_iter=1, cv=2, genre="sans",
        )
        cls.racine = racine

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_fichiers_produits(self):
        for nom in ("models/fraudguard_pipeline.joblib", "rapports/matrice_confusion_test.png",
                    "rapports/metriques.json", "rapports/comparaison_modeles.csv",
                    "rapports/comparaison_genre.json", "rapports/hyperparametres.json"):
            self.assertTrue((self.racine / nom).is_file(), nom)

    def test_dictionnaire_metriques_dans_le_joblib(self):
        p = joblib.load(self.racine / "models" / "fraudguard_pipeline.joblib")
        m = p["metriques"]
        for cle in ("precision_score", "recall_score", "f1_score", "auc_roc", "matrice_confusion",
                    "seuil_decision", "date_entrainement"):
            self.assertIn(cle, m)
        self.assertEqual(m["seuil_decision"], p["seuil_decision"])
        self.assertEqual(m["jeu_evaluation"], "test")
        self.assertEqual(m["seuil_choisi_sur"], "validation")
        (tn, fp), (fn, tp) = m["matrice_confusion"]
        self.assertEqual(tn + fp + fn + tp, m["effectifs"]["test"])
        json.dumps(m)  # serialisable (le backend le stocke en JSON)

    def test_export_sans_genre(self):
        self.assertNotIn("genre", self.pipeline["colonnes_modele"])
        self.assertFalse(self.pipeline["metriques"]["variable_genre_utilisee"])

    def test_le_pipeline_exporte_est_utilisable_par_predict_py(self):
        ligne = self.df[self.df.est_fraude == 1].iloc[0]
        transaction = {c: ligne[c] for c in self.df.columns if c != "est_fraude"}
        proba = predict.predict_fraud_probability(self.pipeline, transaction)
        self.assertTrue(0.0 <= proba <= 1.0)
        self.assertEqual(predict.get_decision_threshold(self.pipeline), self.pipeline["seuil_decision"])


class JoblibLivreTests(unittest.TestCase):
    """Le .joblib commite dans le depot doit contenir les metriques."""

    def test_joblib_du_depot(self):
        chemin = Path(__file__).resolve().parents[1] / "models" / "fraudguard_pipeline.joblib"
        if not chemin.is_file():
            self.skipTest("fraudguard_pipeline.joblib absent")
        p = joblib.load(chemin)
        self.assertIn("metriques", p, "ancien .joblib : relancer training.py")
        m = p["metriques"]
        for cle in ("precision_score", "recall_score", "f1_score", "auc_roc", "matrice_confusion",
                    "seuil_decision", "date_entrainement"):
            self.assertIn(cle, m)
        self.assertEqual(m["seuil_choisi_sur"], "validation")


if __name__ == "__main__":
    unittest.main()
