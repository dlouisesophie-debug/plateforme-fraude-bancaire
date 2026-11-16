# Notes de soutenance — partie Machine Learning

Questions que le jury est susceptible de poser, avec la réponse honnête et ce qui a été fait
dans le code. Les chiffres viennent de `ml/reports/metriques.json` (régénérés à chaque
entraînement par `ml/src/training.py`).

## 1. « Votre rappel en validation croisée est de 0,9998 et de 0,80 sur le test. Pourquoi ? »

**Cause : fuite de données.** Dans la première version, SMOTE était appliqué à tout le jeu
d'entraînement *avant* `RandomizedSearchCV`. SMOTE fabrique des fraudes synthétiques en
interpolant entre fraudes voisines ; les plis de validation contenaient donc des fraudes
« clones » de fraudes vues à l'entraînement. Le score de CV mesurait la mémorisation, pas la
généralisation.

**Correction.** SMOTE est maintenant la première étape d'un `imblearn.pipeline.Pipeline`
(`SMOTE → classifieur`). À chaque pli, il est ajusté sur les seuls plis d'entraînement ; les
données de validation ne sont jamais rééchantillonnées. La recherche est notée en PR-AUC
(*average precision*) : adaptée à un jeu à 0,39 % de fraudes et indépendante du seuil.
Le test `test_la_recherche_d_hyperparametres_utilise_le_pipeline_avec_smote` (ml/tests) verrouille
cette architecture.

## 2. « Comment avez-vous choisi le seuil de décision ? »

Dans la première version, sur le **jeu de test** : les métriques annoncées étaient donc
optimistes (le test avait servi à régler le modèle).

Maintenant : découpage **train 60 % / validation 20 % / test 20 %** (stratifié). Le seuil est
choisi **sur la validation** (le plus haut seuil qui garde un rappel ≥ 85 %). Le test n'est
utilisé qu'une fois, à la fin, pour annoncer les métriques. Le modèle exporté est celui entraîné
sur le train seul : le seuil reste valide (pas de réentraînement sur train+validation qui
décalerait les probabilités).

Les tables de fréquence (commerçant, ville, profession) et le `StandardScaler` sont, eux aussi,
calculés sur le train seul.

## 3. « Pourquoi le sexe du client sert-il à détecter la fraude ? » (RGPD, équité)

On a comparé le modèle avec et sans la variable `genre`, mêmes hyperparamètres, même seuil
méthode : résultats dans `ml/reports/comparaison_genre.json` et dans le README.
Le fichier donne aussi la part de l'importance (gain) attribuée à `genre` par le modèle.
Argument à retenir : *si retirer `genre` ne dégrade pas de façon significative les métriques
(voir les intervalles de confiance à 95 % : le test ne contient que 429 fraudes, quelques points
d'écart peuvent n'être que du bruit), il n'y a aucune raison de garder une donnée personnelle
sensible dans un modèle qui décide d'alerter sur un client.* Voir la décision retenue dans
`ml/README.md`.

## 4. « Votre dataset est-il réel ? »

**Non, et on le dit clairement.** Les données sont **synthétiques** : commerçants préfixés
`fraud_`, adresses américaines (rues, coordonnées GPS des États-Unis : latitudes 20 à 66, longitudes
−166 à −68), transactions datées du 21 juin au 31 décembre 2020, adaptées au Sénégal par traduction/remplacement des libellés (catégories, régions,
prénoms, montants en FCFA). Le fichier a la même taille (555 719 lignes, 2 145 fraudes) que
`fraudTest.csv` du jeu Kaggle « Credit Card Transactions Fraud Detection Dataset » (données
simulées par le générateur Sparkov) — **à vérifier et à citer précisément (auteur, URL, licence)
avant de l'écrire dans le mémoire**. Conséquences à assumer :

- les métriques ne prouvent pas la performance sur de vraies transactions sénégalaises ;
- les motifs de fraude sont ceux du simulateur, pas ceux d'un fraudeur réel ;
- la distance client-commerçant, très discriminante ici, dépend de la façon dont le simulateur
  génère les coordonnées.

Ce que le projet démontre : une **chaîne complète et méthodologiquement propre** (découpage,
absence de fuite, seuil sur validation, évaluation honnête, intégration API, alertes), prête à
être réentraînée sur de vraies données de banque.

## 5. « Si le canal de paiement change (Mobile Money, carte…), le score change-t-il ? »

**Non.** Le canal (`channel`) est enregistré avec la transaction et sert à filtrer et à afficher,
mais il n'est **pas** une variable du modèle : le jeu d'entraînement n'a pas de colonne « canal ».
On l'a vérifié dans le code : seules les variables listées dans `ml/src/preprocessing.py` sont envoyées au modèle.

Réponse recommandée : l'assumer comme **limite connue**. *« Le dataset disponible ne contient pas
le canal ; l'ajouter demande des données étiquetées par canal. Le backend stocke déjà le canal :
dès qu'on dispose de telles données, il suffit de l'ajouter dans `preprocessing.py`, de
réentraîner avec `training.py` et de réactiver le modèle. »*
Ne pas prétendre que le modèle « tient compte du canal » : ce serait faux.

## 6. « Pourquoi XGBoost ? »

Trois modèles ont été comparés (régression logistique, Random Forest, XGBoost), tous avec SMOTE
dans le pipeline, **sur le jeu de validation** ; le choix se fait sur la PR-AUC en validation.
Le tableau est dans `ml/reports/comparaison_modeles.csv`.
