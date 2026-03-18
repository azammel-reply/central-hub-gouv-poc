# 📊 Création du Dashboard Power BI (Version WEB / Mac)

Puisque tu es sur Mac et que tu utilises la version en ligne (**Power BI Service** à l'adresse app.powerbi.com), la méthode est un peu différente de l'application Desktop (Windows). 

Sur la version Web gratuite, croiser deux fichiers CSV est complexe sans base de données unifiée. On va donc créer l'essentiel du tableau de bord global avec le fichier principal `scores.csv`.

---

## 🏗️ Étape 1 : Importer les données dans ton Espace de travail

1. Sur [app.powerbi.com](https://app.powerbi.com), va dans **Mon espace de travail** (le menu à gauche).
2. Clique sur le gros bouton rouge/vert **+ Nouveau rapport** (en haut à gauche).
3. Choisis l'option **Coller ou entrer manuellement des données**.
   - Ouvre le fichier `results/scores.csv` généré par le POC sur ton Mac (avec TextEdit ou Excel).
   - Copie tout le texte (les données).
   - Colle tout dans la fenêtre Power BI qui vient de s'ouvrir.
   - Clique sur le bouton en bas **"Créer un rapport vierge"** (ou "Créer un rapport automatiquement" si tu veux une version aléatoire pour commencer).

*(Power BI Web va directement générer un "Modèle sémantique" en cloud à partir de ton fichier CSV collé).*

---

## 🎨 Étape 2 : Créer les visuels du Dashboard

Une fois sur la page de création de rapport vierge (la toile blanche), tu as tes champs (les colonnes du CSV) sur la droite de l'écran dans le panneau "Données".

### 1️⃣ Les KPI Cards (Cartes en haut)
Dans le panneau des Visualisations, choisis l'icône **Carte (Card - avec les chiffres 123)**.
*   **Total APIs** : Coche le champ `service_name`, clique sur la petite flèche à côté dans la zone des valeurs, et choisis l'agrégation "Nombre" ou "Count" (pas "Première").
*   **Average Score** : Coche le champ `numerical_score` et choisis "Moyenne" (Average).

### 2️⃣ API Compliance Breakdown (Graphique en barres)
Ajoute un visuel **Graphique à colonnes groupées (Clustered column chart)** :
*   **Axe X** : Glisse la colonne `grade` (A, B, C, D, E).
*   **Axe Y** : Glisse la colonne `service_name` et assure-toi que l'agrégation est "Nombre (Count)".
*   *Bonus de Design :* Clique sur le petit rouleau de peinture rouge (Modifier la mise en forme) > "Colonnes". Tu pourras attribuer manuellement le Vert au A, Jaune au C, Rouge au E.

### 3️⃣ Top / Bottom APIs (Le grand tableau récapitulatif)
Ajoute un visuel **Table (Tableau)** ou **Matrice** :
*   **Colonnes** : Coche tes champs de données dans cet ordre précis :
    `service_name`, `version`, `domain`, `region`, `numerical_score`, `grade`, `total_issues`, `operations_count`, `rank`
*   Clique sur l'en-tête de la colonne `numerical_score` pour trier de la meilleure API à la pire (ou l'inverse).
*   *Astuce Web* : Dans les options de formatage visuel du tableau (le pinceau rouge), cherche "Mise en forme conditionnelle" : tu pourras ajouter une couleur de fond automatique pour la colonne Grade, comme sur notre HTML !

---

### 🚨 Différences et Limitations de la version Web (POC local vs Enterprise)

Contrairement à la version "Enterprise" branchée sur un Cloud Azure ou à la version "Desktop" sur Windows :
- **Fichier des Violations (`violations_flat.csv`)** : Tu ne peux pas simplement lier un deuxième CSV au premier sur le web en "drag & drop". Pour voir le tableau des règles les plus violées dans Power BI Web, tu devras faire la même méthode de copier/coller dans une nouvelle source de données de ce même rapport, et créer un deuxième visuel "Tableau".
- **Visualisation automatique et rafraîchissement** : L'avantage énorme de la méthode entreprise (ou même de notre Dashboard HTML !), c'est que c'est mis à jour à 100% automatiquement. Ici sur Power BI Web, si le POC crée de nouveaux CSV ce soir, tu devras retourner sur la plateforme et les re-coller dans ton modèle sémantique manuellement pour actualiser les graphiques. C'est l'essence même du POC !
