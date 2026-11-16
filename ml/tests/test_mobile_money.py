"""
Tests du modele MOBILE MONEY (sans le vrai CSV PaySim : donnees synthetiques
au meme format).

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
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import evaluation  # noqa: E402
import predict  # noqa: E402
import preprocessing_mobile_money as pmm  # noqa: E402
import training  # noqa: E402
import training_mobile_money as tmm  # noqa: E402

warnings.filterwarnings("ignore")

COLONNES_PAYSIM_COMPLET = [
    "step", "type", "amount", "nameOrig", "oldbalanceOrg", "newbalanceOrig",
    "nameDest", "oldbalanceDest", "newbalanceDest", "isFraud", "isFlaggedFraud",
]


def paysim_synthetique(n=30000, taux_fraude=0.02, graine=0) -> pd.DataFrame:
    """
    Jeu au format PaySim COMPLET (11 colonnes, soldes compris) avec les
    caracteristiques connues de PaySim : les fraudes n'existent que dans TRANSFER
    et CASH_OUT, avec des montants eleves.
    """
    rng = np.random.default_rng(graine)
    types = rng.choice(["PAYMENT", "CASH_IN", "CASH_OUT", "TRANSFER", "DEBIT"], n,
                       p=[0.34, 0.22, 0.35, 0.08, 0.01])
    fraude = ((rng.random(n) < taux_fraude / 0.43) & np.isin(types, ["TRANSFER", "CASH_OUT"])).astype(int)
    montant = np.where(fraude == 1, rng.lognormal(12.0, 1.0, n), rng.lognormal(9.5, 1.3, n))
    solde = rng.lognormal(10, 1.5, n)
    return pd.DataFrame({
        "step": rng.integers(1, 744, n),
        "type": types,
        "amount": montant,
        "nameOrig": [f"C{i}" for i in range(n)],
        "oldbalanceOrg": solde,
        "newbalanceOrig": np.where(fraude == 1, 0.0, solde - montant * 0.1),  # fuite typique
        "nameDest": [f"C{i + n}" for i in range(n)],
        "oldbalanceDest": rng.lognormal(9, 1.5, n),
        "newbalanceDest": rng.lognormal(9, 1.5, n),
        "isFraud": fraude,
        "isFlaggedFraud": 0,
    })


class ContratEtColonnesInterditesTests(unittest.TestCase):
    def test_les_variables_du_modele_sont_exactement_celles_du_contrat(self):
        self.assertEqual(
            pmm.COLONNES_MODELE,
            ["montant", "heure_transaction", "type_depot", "type_retrait", "type_transfert",
             "type_paiement", "type_debit"],
        )

    def test_aucune_variable_du_modele_ne_ressemble_a_un_solde_ou_un_identifiant(self):
        for col in pmm.COLONNES_MODELE:
            for mot in pmm.MOTS_INTERDITS:
                self.assertNotIn(mot, col.lower(), f"{col} contient le fragment interdit {mot!r}")

    def test_une_colonne_de_solde_fait_echouer_la_construction_des_variables(self):
        propre = pmm.preparer_paysim(paysim_synthetique(200)[pmm.COLONNES_PAYSIM_LUES])
        for interdite in ["oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest",
                          "nameOrig", "nameDest", "isFlaggedFraud", "step"]:
            avec = propre.copy()
            avec[interdite] = 1.0
            with self.assertRaises(ValueError, msg=interdite):
                pmm.construire_matrice(avec)

    def test_le_chargement_ne_lit_que_les_colonnes_autorisees(self):
        with tempfile.TemporaryDirectory() as d:
            chemin = Path(d) / "paysim.csv"
            paysim_synthetique(500)[COLONNES_PAYSIM_COMPLET].to_csv(chemin, index=False)
            df = tmm.charger_paysim(str(chemin))
        self.assertEqual(set(df.columns), pmm.COLONNES_AUTORISEES)

    def test_le_modele_exporte_n_a_aucune_colonne_interdite(self):
        with tempfile.TemporaryDirectory() as d:
            p = _entrainer_petit_modele(d)
        self.assertEqual(p["colonnes_modele"], pmm.COLONNES_MODELE)
        self.assertEqual(set(p["model"].get_booster().feature_names or pmm.COLONNES_MODELE)
                         - set(pmm.COLONNES_MODELE), set())


class PretraitementTests(unittest.TestCase):
    def test_correspondance_des_types_en_francais(self):
        self.assertEqual(pmm.TYPES_PAYSIM, {"CASH_IN": "Dépôt", "CASH_OUT": "Retrait",
                                            "TRANSFER": "Transfert", "PAYMENT": "Paiement",
                                            "DEBIT": "Débit"})

    def test_heure_depuis_step(self):
        self.assertEqual(pmm.heure_depuis_step([1, 24, 25, 743]).tolist(), [1, 0, 1, 23])

    def test_matrice_vectorisee_identique_au_pretraitement_ligne_par_ligne(self):
        propre = pmm.preparer_paysim(paysim_synthetique(300)[pmm.COLONNES_PAYSIM_LUES])
        X = pmm.construire_matrice(propre)
        for i in range(0, 300, 7):
            ligne = propre.iloc[i]
            attendu = pmm.construire_features({
                "type_operation": ligne["type_operation"], "montant": ligne["montant"],
                "heure_transaction": ligne["heure_transaction"],
            })
            self.assertEqual(list(X.iloc[i].index), list(attendu))
            np.testing.assert_allclose(X.iloc[i].to_numpy(float), np.array(list(attendu.values())))

    def test_la_saisie_accepte_les_libelles_avec_ou_sans_accent(self):
        for saisie, cle in [("Dépôt", "depot"), ("depot", "depot"), (" Débit ", "debit"),
                            ("RETRAIT", "retrait"), ("Transfert", "transfert")]:
            self.assertEqual(pmm.cle_type_operation(saisie), cle)

    def test_les_codes_paysim_et_le_libelle_long_du_debit_sont_acceptes(self):
        for saisie, cle in [("CASH_IN", "depot"), ("CASH_OUT", "retrait"), ("TRANSFER", "transfert"),
                            ("PAYMENT", "paiement"), ("DEBIT", "debit"),
                            ("Débit vers un compte bancaire", "debit"),
                            ("debit vers un compte bancaire", "debit")]:
            self.assertEqual(pmm.cle_type_operation(saisie), cle)
        # meme ligne de variables quelle que soit la forme de la saisie
        base = {"montant": 1000.0, "heure_transaction": 5}
        self.assertEqual(pmm.construire_features({**base, "type_operation": "CASH_OUT"}),
                         pmm.construire_features({**base, "type_operation": "Retrait"}))

    def test_le_step_brut_n_est_pas_une_variable_du_modele(self):
        self.assertNotIn("step", pmm.COLONNES_MODELE)
        self.assertNotIn("step", pmm.COLONNES_AUTORISEES)
        propre = pmm.preparer_paysim(paysim_synthetique(100)[pmm.COLONNES_PAYSIM_LUES])
        self.assertNotIn("step", propre.columns)

    def test_saisies_invalides_refusees(self):
        base = {"type_operation": "Retrait", "montant": 100.0, "heure_transaction": 10}
        for modif in ({"type_operation": "Virement"}, {"montant": -5}, {"montant": float("nan")},
                      {"heure_transaction": 24}, {"heure_transaction": -1}):
            with self.assertRaises(ValueError, msg=str(modif)):
                pmm.construire_features({**base, **modif})


class AbsenceDeFuiteTests(unittest.TestCase):
    def test_smote_est_dans_le_pipeline_pour_les_trois_modeles(self):
        for fabrique in (training.pipeline_logistique, training.pipeline_random_forest,
                         training.pipeline_xgboost):
            p = fabrique()
            self.assertIsInstance(p, ImbPipeline)
            self.assertIsInstance(p.steps[0][1], SMOTE)

    def test_decoupage_60_20_20_stratifie_et_disjoint(self):
        df = pmm.preparer_paysim(paysim_synthetique(20000)[pmm.COLONNES_PAYSIM_LUES])
        train, val, test = training.decouper(df)
        n = len(df)
        self.assertAlmostEqual(len(train) / n, 0.6, places=2)
        self.assertAlmostEqual(len(val) / n, 0.2, places=2)
        self.assertAlmostEqual(len(test) / n, 0.2, places=2)
        self.assertFalse(set(train.index) & set(val.index))
        self.assertFalse(set(train.index) & set(test.index))
        self.assertFalse(set(val.index) & set(test.index))
        for d in (train, val, test):
            self.assertAlmostEqual(d["est_fraude"].mean(), df["est_fraude"].mean(), places=3)

    def test_la_reduction_ne_touche_que_le_train_et_garde_toutes_les_fraudes(self):
        df = pmm.preparer_paysim(paysim_synthetique(20000)[pmm.COLONNES_PAYSIM_LUES])
        train, _, _ = training.decouper(df)
        reduit, info = tmm.reduire_train(train, 3000)
        self.assertEqual(len(reduit), 3000)
        self.assertEqual(int(reduit["est_fraude"].sum()), int(train["est_fraude"].sum()))
        self.assertTrue(set(reduit.index) <= set(train.index))
        self.assertTrue(info["applique"])
        self.assertFalse(info["validation_et_test_reduits"])
        # pas de reduction si le jeu est deja assez petit
        self.assertEqual(tmm.reduire_train(train, None), (train, None))
        self.assertEqual(tmm.reduire_train(train, len(train) + 1)[1], None)


class RegleSimpleEtTauxDeFraudeTests(unittest.TestCase):
    def test_la_regle_simple_est_choisie_sur_la_validation(self):
        df = pmm.preparer_paysim(paysim_synthetique(20000)[pmm.COLONNES_PAYSIM_LUES])
        train, val, test = training.decouper(df)
        regle = tmm.evaluer_regle_simple(train, val, test, 0.85)
        self.assertGreaterEqual(regle["validation"]["recall"], 0.85)
        self.assertEqual(set(regle["types_a_risque"]), {"Transfert", "Retrait"})

    def test_evaluation_sur_les_types_a_risque_garde_le_rappel_et_le_seuil(self):
        df = pmm.preparer_paysim(paysim_synthetique(20000)[pmm.COLONNES_PAYSIM_LUES])
        rng = np.random.default_rng(3)
        proba = np.clip(df["est_fraude"].to_numpy() * 0.6 + rng.random(len(df)) * 0.5, 0, 1)
        complet = evaluation.evaluer(df["est_fraude"], proba, 0.5)
        reduit = tmm.evaluer_types_a_risque(df, proba, 0.5, ["Transfert", "Retrait"])
        self.assertEqual(reduit["fraudes_hors_types"], 0)
        self.assertEqual(reduit["n_fraudes"], complet["n_fraudes"])
        self.assertAlmostEqual(reduit["recall"], complet["recall"], places=9)
        self.assertEqual(reduit["seuil"], 0.5)
        self.assertLess(reduit["n_echantillons"], complet["n_echantillons"])
        # moins de faux positifs possibles -> precision au moins aussi bonne
        self.assertGreaterEqual(reduit["precision"], complet["precision"])

    def test_precision_selon_le_taux_de_fraude(self):
        # rappel 90 %, FPR 1 % : a 1 % de fraude -> 0,009 / (0,009 + 0,0099) = 47,6 %
        self.assertAlmostEqual(tmm.precision_a_taux_de_fraude(0.9, 0.01, 0.01), 0.4762, places=3)
        # un taux de fraude plus faible -> une precision plus faible, a rappel et FPR egaux
        self.assertLess(tmm.precision_a_taux_de_fraude(0.9, 0.01, 0.001),
                        tmm.precision_a_taux_de_fraude(0.9, 0.01, 0.01))
        self.assertEqual(tmm.precision_a_taux_de_fraude(0.0, 0.0, 0.01), 0.0)


def _entrainer_petit_modele(dossier, n=12000):
    """Entrainement complet rapide sur donnees synthetiques ; renvoie le dict exporte."""
    chemin = Path(dossier) / "paysim.csv"
    paysim_synthetique(n)[COLONNES_PAYSIM_COMPLET].to_csv(chemin, index=False)
    return tmm.entrainer(str(chemin), str(Path(dossier) / "models"), str(Path(dossier) / "reports"),
                         n_iter=2, cv=2, max_train=6000)


class EntrainementDeBoutEnBoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dossier = Path(cls.tmp.name)
        cls.pipeline = _entrainer_petit_modele(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_fichiers_produits(self):
        self.assertTrue((self.dossier / "models" / tmm.NOM_JOBLIB).exists())
        for f in ("metriques.json", "comparaison_modeles.csv", "hyperparametres.json",
                  "matrice_confusion_test.png", "regle_simple.json"):
            self.assertTrue((self.dossier / "reports" / f).exists(), f)

    def test_le_modele_carte_n_est_pas_touche(self):
        self.assertFalse((self.dossier / "models" / "fraudguard_pipeline.joblib").exists())

    def test_famille_et_contenu_du_joblib(self):
        p = joblib.load(self.dossier / "models" / tmm.NOM_JOBLIB)
        self.assertEqual(p["famille"], "mobile_money")
        for cle in ("model", "scaler", "colonnes_modele", "colonnes_numeriques",
                    "seuil_decision", "metriques"):
            self.assertIn(cle, p)
        m = p["metriques"]
        self.assertEqual(m["famille"], "mobile_money")
        self.assertEqual(m["seuil_choisi_sur"], "validation")
        self.assertEqual(m["jeu_evaluation"], "test")
        self.assertTrue(m["reduction_train"]["applique"])
        self.assertIn("sensibilite_precision_au_taux_de_fraude", m)
        self.assertIn("regle_simple", m)
        self.assertIn("evaluation_transfert_retrait", m)

    def test_un_seul_seuil_choisi_sur_la_validation(self):
        """Recalcule le seuil depuis les probabilites de VALIDATION : doit etre celui exporte."""
        p = self.pipeline
        df = pmm.preparer_paysim(paysim_synthetique(12000)[pmm.COLONNES_PAYSIM_LUES])
        _, val, _ = training.decouper(df)
        X = pmm.construire_matrice(val)
        X[p["colonnes_numeriques"]] = p["scaler"].transform(X[p["colonnes_numeriques"]])
        proba = p["model"].predict_proba(X)[:, 1]
        seuil = evaluation.choisir_seuil(val["est_fraude"].to_numpy(int), proba, 0.85)
        self.assertAlmostEqual(seuil, p["seuil_decision"], places=6)

    def test_le_scaler_est_ajuste_sur_le_train_et_non_sur_tout_le_jeu(self):
        p = self.pipeline
        df = pmm.preparer_paysim(paysim_synthetique(12000)[pmm.COLONNES_PAYSIM_LUES])
        train, _, _ = training.decouper(df)
        moyenne_train = pmm.construire_matrice(train)["montant"].mean()
        self.assertAlmostEqual(p["scaler"].mean_[0], moyenne_train, places=3)

    def test_predict_py_utilise_la_preparation_mobile_money(self):
        p = self.pipeline
        proba = predict.predict_fraud_probability(
            p, {"type_operation": "Transfert", "montant": 500000.0, "heure_transaction": 3})
        self.assertGreaterEqual(proba, 0.0)
        self.assertLessEqual(proba, 1.0)
        self.assertEqual(predict.get_family(p), "mobile_money")
        self.assertEqual(predict.get_decision_threshold(p), p["seuil_decision"])
        # un gros transfert est plus suspect qu'un petit paiement (signal du jeu synthetique)
        petit = predict.predict_fraud_probability(
            p, {"type_operation": "Paiement", "montant": 500.0, "heure_transaction": 12})
        self.assertGreater(proba, petit)
        # une saisie hors contrat est refusee, pas devinee
        with self.assertRaises(ValueError):
            predict.predict_fraud_probability(
                p, {"type_operation": "Virement", "montant": 10.0, "heure_transaction": 1})

    def test_matrice_de_confusion_du_json_coherente(self):
        with open(self.dossier / "reports" / "metriques.json", encoding="utf-8") as f:
            m = json.load(f)
        (tn, fp), (fn, tp) = m["matrice_confusion"]
        self.assertAlmostEqual(tp / (tp + fn), m["recall_score"], places=6)
        self.assertAlmostEqual(tp / (tp + fp), m["precision_score"], places=6)


class CleDEntreeEtPointDeFonctionnementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dossier = Path(cls.tmp.name)
        cls.pipeline = _entrainer_petit_modele(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_le_backend_peut_envoyer_type_montant_heure(self):
        p = self.pipeline
        a = predict.predict_fraud_probability(p, {"type": "TRANSFER", "montant": 250000.0, "heure": 23})
        b = predict.predict_fraud_probability(
            p, {"type_operation": "Transfert", "montant": 250000.0, "heure_transaction": 23})
        self.assertEqual(a, b)
        for code in ("CASH_IN", "CASH_OUT", "TRANSFER", "PAYMENT", "DEBIT"):
            self.assertTrue(0.0 <= predict.predict_fraud_probability(
                p, {"type": code, "montant": 100.0, "heure": 0}) <= 1.0)

    def test_cle_manquante_ou_valeur_hors_contrat_refusee(self):
        p = self.pipeline
        with self.assertRaises(KeyError):
            predict.predict_fraud_probability(p, {"montant": 1.0, "heure": 3})
        with self.assertRaises(KeyError):
            predict.predict_fraud_probability(p, {"type": "TRANSFER", "heure": 3})
        with self.assertRaises(ValueError):
            predict.predict_fraud_probability(p, {"type": "transfer", "montant": 1.0, "heure": 24})
        with self.assertRaises(ValueError):
            predict.predict_fraud_probability(p, {"type": "VIREMENT", "montant": 1.0, "heure": 3})

    def test_changer_le_point_de_fonctionnement_sans_reentrainer(self):
        csv = self.dossier / "paysim.csv"
        joblib_src = self.dossier / "models" / tmm.NOM_JOBLIB
        avant = joblib.load(joblib_src)
        sortie = self.dossier / "nouveau" / tmm.NOM_JOBLIB
        sortie.parent.mkdir()
        apres = tmm.changer_point_de_fonctionnement(
            str(joblib_src), str(csv), str(self.dossier / "rapports2"), 0.50, chemin_sortie=str(sortie))
        # le seuil est celui de la VALIDATION pour un rappel >= 50 %
        df = pmm.preparer_paysim(paysim_synthetique(12000)[pmm.COLONNES_PAYSIM_LUES])
        _, val, _ = training.decouper(df)
        pv = tmm._probabilites(avant, val)
        attendu = evaluation.choisir_seuil(val["est_fraude"].to_numpy(int), pv, 0.50)
        self.assertAlmostEqual(apres["seuil_decision"], attendu, places=9)
        self.assertEqual(apres["metriques"]["seuil_decision"], apres["seuil_decision"])
        self.assertGreaterEqual(apres["metriques"]["validation"]["recall"], 0.50)
        # le modele (poids) n'a pas change : memes probabilites
        np.testing.assert_allclose(tmm._probabilites(joblib.load(sortie), val), pv)
        # contenu du .joblib
        m = joblib.load(sortie)["metriques"]
        self.assertEqual(joblib.load(sortie)["famille"], "mobile_money")
        self.assertEqual(m["recall_cible_validation"], 0.50)
        self.assertEqual(m["seuil_choisi_sur"], "validation")
        self.assertEqual(m["auc_roc"], m["evaluation_transfert_retrait"]["auc_roc"])
        self.assertEqual(m["auc_roc_perimetre"], "Transfert + Retrait")
        self.assertIn("auc_roc_toutes_operations", m)
        self.assertEqual(m["point_initial"]["recall_cible_validation"], avant["metriques"]["recall_cible_validation"])
        self.assertEqual(len(m["tableau_compromis_validation"]), len(tmm.CIBLES_TABLEAU))
        (tn, fp), (fn, tp) = m["matrice_confusion"]
        self.assertAlmostEqual(tp / (tp + fn), m["recall_score"], places=9)
        self.assertAlmostEqual(tp / (tp + fp), m["precision_score"], places=9)
        for f in ("metriques.json", "regle_simple.json", "compromis_validation.csv",
                  "matrice_confusion_test.png"):
            self.assertTrue((self.dossier / "rapports2" / f).exists(), f)


class AiguillageParFamilleTests(unittest.TestCase):
    def test_un_pipeline_sans_cle_famille_est_traite_comme_carte(self):
        self.assertEqual(predict.get_family({"model": None}), "carte")

    def test_famille_inconnue_refusee(self):
        with self.assertRaises(ValueError):
            predict.predict_fraud_probability({"famille": "virement"}, {})

    def test_le_modele_carte_livre_passe_toujours_par_son_propre_pretraitement(self):
        chemin = Path(__file__).resolve().parents[1] / "models" / "fraudguard_pipeline.joblib"
        if not chemin.exists():
            self.skipTest("fraudguard_pipeline.joblib absent")
        p = predict.load_pipeline(str(chemin))
        self.assertEqual(predict.get_family(p), "carte")
        proba = predict.predict_fraud_probability(p, {
            "montant_fcfa": 250000.0, "genre": "F", "population_ville": 50000,
            "date_transaction": "2020-08-10 02:30:00", "date_naissance": "1985-03-02",
            "latitude_client": 14.7, "longitude_client": -17.4,
            "latitude_commercant": 14.8, "longitude_commercant": -17.3,
            "commercant": "fraud_Inconnu", "ville": "Dakar", "profession": "Inconnue",
            "categorie": "achats_en_ligne", "region": "Dakar",
        })
        self.assertTrue(0.0 <= proba <= 1.0)
        # une transaction mobile money envoyee au modele carte est refusee (cles manquantes)
        with self.assertRaises(KeyError):
            predict.predict_fraud_probability(
                p, {"type_operation": "Transfert", "montant": 1.0, "heure_transaction": 1})


class JoblibMobileMoneyLivreTests(unittest.TestCase):
    def test_joblib_du_depot(self):
        chemin = Path(__file__).resolve().parents[1] / "models" / tmm.NOM_JOBLIB
        if not chemin.exists():
            self.skipTest("fraudguard_mobile_money_pipeline.joblib absent")
        p = predict.load_pipeline(str(chemin))
        self.assertEqual(predict.get_family(p), "mobile_money")
        self.assertEqual(p["colonnes_modele"], pmm.COLONNES_MODELE)
        m = p["metriques"]
        self.assertEqual(m["seuil_choisi_sur"], "validation")
        self.assertAlmostEqual(m["seuil_decision"], p["seuil_decision"])
        self.assertTrue(0.0 <= predict.predict_fraud_probability(
            p, {"type_operation": "Transfert", "montant": 400000.0, "heure_transaction": 3}) <= 1.0)


if __name__ == "__main__":
    unittest.main()
