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
- les signaux les plus utilisés par le modèle (montant élevé, transaction de nuit, catégorie du
  commerçant) sont ceux du simulateur ; la distance client-commerçant, elle, ne distingue pas les
  fraudes des transactions légitimes (distance médiane d'environ 78 km dans les deux cas).

Ce que le projet démontre : une **chaîne complète et méthodologiquement propre** (découpage,
absence de fuite, seuil sur validation, évaluation honnête, intégration API, alertes), prête à
être réentraînée sur de vraies données de banque.

## 5. « Si le canal de paiement change (Mobile Money, carte…), le score change-t-il ? »

**Le canal choisit le modèle, mais n'est une variable d'aucun modèle.** Depuis le 16/11/2026
(pull requests #40 et #41), le backend garde un modèle actif par famille :
- une transaction **Mobile Money avec un type d'opération** est notée par le modèle Mobile Money (mm-v1) ;
- toutes les autres (carte, paiement en ligne, virement, Mobile Money sans type) par le modèle carte (v2).

À l'intérieur du modèle carte, le canal n'entre pas dans le calcul : le jeu d'entraînement n'a pas de
colonne « canal » (seules les variables de `ml/src/preprocessing.py` sont envoyées au modèle). Deux
transactions carte et paiement en ligne identiques par ailleurs ont donc le même score.
Ne pas prétendre que le modèle « tient compte du canal » : ce serait faux.

## 5 bis. « 36 % est une fraude pour la carte, mais 37 % ne l'est pas en Mobile Money : pourquoi ? »

Chaque modèle a **son propre seuil**, choisi sur la validation pour son objectif de rappel :
0,0652 pour le modèle carte (85 % de rappel visé), 0,9307 pour le modèle Mobile Money (50 % visé).
Les scores servent à classer les transactions ; ce ne sont pas des probabilités calibrées, et ils ne se
comparent pas d'un modèle à l'autre. Depuis le 23/11/2026, le seuil est enregistré avec chaque
prédiction et affiché à côté du score (fiche transaction et page Alertes).

## 6. « Pourquoi XGBoost ? »

Trois modèles ont été comparés (régression logistique, Random Forest, XGBoost), tous avec SMOTE
dans le pipeline, **sur le jeu de validation** ; le choix se fait sur la PR-AUC en validation :
**0,869** pour XGBoost, 0,631 pour Random Forest, 0,120 pour la régression logistique
(`ml/reports/comparaison_modeles.csv`, graphique `ml/reports/choix_modele_pr_auc_validation.png`).

Deux réserves à dire avant qu'on les relève : seul XGBoost a été optimisé (les deux autres sont des
références), et la comparaison a été faite **avec** la variable genre. Le modèle livré a été réentraîné
**sans** : d'où 63,3 % de précision au test dans le tableau de comparaison, contre 60,7 % pour le modèle
livré (rappel 86,9 %, seuil 0,0652).

## 7. Modèle Mobile Money (PaySim) — réponses préparées

Il y a **deux modèles séparés**, chacun avec son propre seuil de décision : le modèle carte
(`fraudguard_pipeline.joblib`) et le modèle Mobile Money (`fraudguard_mobile_money_pipeline.joblib`).
Ils ne partagent ni variables ni préprocesseur ; le backend choisit le fichier selon le canal, et
`predict.py` choisit la bonne préparation d'après la clé `famille` du fichier.

**« D'où viennent les données ? »** PaySim, un simulateur de transactions Mobile Money :
E. A. Lopez-Rojas, A. Elmir, S. Axelsson, « PaySim: a financial mobile money simulator for fraud
detection », Proceedings of EMSS 2016, p. 249-255 ; jeu publié sur Kaggle (`ealaxi/paysim1`).
Ce sont des données **simulées**, comme pour le modèle carte. **Licence : CC BY-SA 4.0** (page Kaggle du
jeu, consultée le 16/11/2026). BY : il faut citer l'auteur (Edgar Lopez-Rojas, article EMSS 2016 ci-dessus).
SA (partage dans les mêmes conditions) : si l'on redistribue le jeu ou une version adaptée, c'est sous la même
licence. Nous ne redistribuons pas les données (dossier `ml/data/raw/` non versionné) ; le dépôt ne contient
que le code, le modèle entraîné et les rapports. *Pas un avis juridique : en cas de doute sur le statut du
modèle entraîné, le dire au jury plutôt que l'affirmer.*

**« Pourquoi seulement trois variables ? »** Le contrat de données est : type d'opération, montant,
heure. Les colonnes écartées, et pourquoi :
- les **4 colonnes de soldes** (avant/après, expéditeur et destinataire) : la description du jeu
  indique qu'elles trahissent la fraude. Les utiliser donnerait un faux score proche de 99 % ;
- les **identifiants de compte** (`nameOrig`, `nameDest`) : aucune information généralisable ;
- **`isFlaggedFraud`** : sortie d'une règle du simulateur, pas une information connue avant la décision.
Ces colonnes ne sont même pas lues dans le CSV (`charger_paysim` ne demande que 4 colonnes) et un test
échoue si l'une d'elles entre dans le modèle.

**« Les montants sont-ils en FCFA ? »** Non : unité du simulateur, aucune conversion en FCFA n'est
faite (un taux de change inventé n'aurait aucune source).

**« L'heure vient d'où ? »** De `step` (1 pas = 1 heure de simulation) : heure = step modulo 24. Le
point d'origine du simulateur n'est pas documenté ; seul compte le fait que l'entraînement et l'API
appliquent la même règle.

**« Comment est choisi le seuil ? »** Un seul seuil, choisi sur la validation, jamais sur le test. Le point
retenu par l'équipe est celui à **50 % de rappel : 0,9307** (point initial à 85 % : 0,5133, conservé en
comparaison). Le test est utilisé une seule fois, avec des intervalles de confiance à 95 %.

**« Quels sont les résultats ? »** Sur le test (1 272 524 transactions dont 1 643 fraudes), seuil 0,9307 :
rappel **47,1 %** (IC 95 % : 44,7 – 49,6 %), précision **12,4 %**, F1 0,197, AUC-ROC 0,882 sur Transfert +
Retrait (0,949 sur toutes opérations). Soit 774 fraudes trouvées sur 1 643, 5 444 fausses alertes : environ
7 alertes pour une vraie fraude. À dire clairement : on rate plus d'une fraude sur deux. Cause : seulement
trois variables, les soldes étant exclus.

**« Pourquoi un rappel de 50 % ? »** C'est un compromis choisi sur la validation (tableau du README) : à 85 %
de rappel on aurait 100 alertes pour une fraude (précision 0,98 %), à 30 % la précision monte à 59 %. Le bon
point dépend du coût d'une fraude manquée et du coût d'une alerte traitée : décision métier.

**« Votre modèle fait-il mieux qu'une règle simple ? »** Oui. Règle : *Transfert ou Retrait et montant ≥
59 628* (types et seuil fixés sans le test). Au même rappel (47 %), précision 1,1 % pour la règle contre
12,4 % pour le modèle, PR-AUC 0,021 contre 0,341 en validation. Détail :
`ml/reports/mobile_money/comparaison_modeles_point_initial_85.csv`.

**« Le modèle ne signale jamais un dépôt, un paiement ou un débit : n'est-ce pas un biais ? »** C'est
une conséquence directe des données : dans PaySim, la fraude n'apparaît que dans les Transferts et les
Retraits (aucune fraude dans 718 804 opérations des trois autres types du jeu de test). Le modèle a
appris cette règle et ne lève aucune alerte sur ces types ; c'est correct *pour ces données*, mais cela
ne dit rien sur de vraies transactions. Pour ne pas gonfler les résultats, nous donnons aussi les
métriques sur Transfert + Retrait seuls : même rappel (47,1 %) et même précision (12,4 %), mais **0,99 %
des opérations légitimes de ces deux types sont signalées**, et l'AUC-ROC est de 0,882 (contre 0,949 sur
toutes les opérations).

**« À quoi sert le champ `step` ? »** Il n'est pas une variable du modèle : il est lu uniquement pour
calculer l'heure du jour (heure = step modulo 24) ; le step brut est exclu comme les soldes et les
identifiants. Dakar étant en UTC+0, l'heure saisie dans l'application correspond directement.

**« Qu'est-ce qui distingue une fraude, dans ces données ? »** Les fraudes n'existent que dans les
Transferts (0,77 %) et les Retraits (0,18 %) ; aucun Dépôt, Paiement ni Débit n'est frauduleux. Les montants
sont plus élevés (médiane 441 423 contre 74 685). Les fraudes sont réparties **uniformément sur 24 h**,
alors que l'activité légitime se concentre entre 9 h et 21 h : l'heure est un signal parce que le
simulateur l'a construit ainsi, pas parce que les vrais fraudeurs agissent la nuit.

**« Pourquoi la précision serait-elle plus faible dans la réalité ? »** Le rappel et le taux de faux
positifs ne dépendent pas de la fréquence de la fraude, mais la précision, si : précision =
TP / (TP + FP), avec TP = rappel × π et FP = taux de faux positifs × (1 − π), π étant la part de
fraudes. Si la vraie fraude est plus rare que dans PaySim, la précision baisse. Le tableau
`sensibilite_precision_au_taux_de_fraude` de `metriques.json` donne la précision pour plusieurs
valeurs de π.

**« Le jeu est énorme, comment l'avez-vous entraîné sur 8 Go de RAM ? »** Le jeu d'entraînement a été
réduit (toutes les fraudes conservées, échantillon aléatoire des transactions légitimes). La
validation et le test n'ont **jamais** été réduits. La réduction exacte est écrite dans
`metriques.json` (`reduction_train`).

**Limites à assumer :** données simulées ; trois variables seulement ; le comportement d'un vrai
fraudeur Mobile Money (ou d'un client réel d'un opérateur sénégalais) peut être très différent ;
les résultats montrent que la chaîne fonctionne, pas la performance en production.
