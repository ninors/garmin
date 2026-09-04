# 🚴‍♂️ Garmin GPX & FIT Auto-Exporter & Hub Web

Ce dépôt vous permet d'extraire automatiquement vos **parcours**, **planifications/entraînements** et **activités** enregistrées sur votre compte Garmin Connect aux formats **.GPX** et **.FIT**, et de les rendre accessibles sur une page web interactive `index.html` avec téléchargement en 1-clic et export `.ZIP`.

---

## ⚡ Guide Rapide : Installation en 3 minutes

### 1️⃣ Glisser-déposer les fichiers sur GitHub
1. Créez un nouveau dépôt sur [GitHub.com](https://github.com/new) (Public ou Privé).
2. Glissez-déposez **tous les fichiers** de ce projet dans votre dépôt :
   - `.github/workflows/garmin_sync.yml`
   - `fetch_garmin.py`
   - `requirements.txt`
   - `index.html`
   - `styles.css`
   - `app.js`
   - `README.md`

---

### 2️⃣ Enregistrer vos identifiants Garmin en Secret
Pour que GitHub puisse télécharger vos fichiers en toute sécurité sans exposer votre mot de passe au public :

1. Allez dans les **Settings** (Paramètres) de votre dépôt GitHub.
2. Dans le menu de gauche, cliquez sur **Secrets and variables** > **Actions**.
3. Cliquez sur **New repository secret** et ajoutez :
   - **Nom :** `GARMIN_EMAIL` | **Valeur :** Votre adresse email Garmin Connect.
   - **Nom :** `GARMIN_PASSWORD` | **Valeur :** Votre mot de passe Garmin Connect.

---

### 3️⃣ Activer GitHub Pages
1. Toujours dans **Settings** > **Pages**.
2. Sous **Build and deployment** :
   - **Source :** `Deploy from a branch`
   - **Branch :** `main` (ou `master`) / `/ (root)`
3. Cliquez sur **Save**.

---

### 4️⃣ Lancer la première synchronisation
1. Cliquez sur l'onglet **Actions** en haut de votre dépôt.
2. Dans la colonne de gauche, sélectionnez le workflow **Garmin Sync & Export**.
3. Cliquez sur le bouton **Run workflow** à droite.

> ⏱️ **En moins d'une minute**, le script télécharge vos fichiers GPX/FIT, met à jour `data/data.json` et publie votre site sur GitHub Pages !

---

## 🛠️ Fonctionnalités & Roues de Secours (Fallbacks)

- 🔒 **Sécurité totale** : Les identifiants restent chiffrés sur les serveurs GitHub.
- 🛟 **Reprise de Session (Tokens)** : Réutilise les jetons de session Garmin pour éviter tout blocage ou limite de requêtes.
- 📁 **Export multi-format** : Parcours enregistrés en **GPX** et **FIT**.
- 📦 **Tout Télécharger (.ZIP)** : Export de l'ensemble de votre bibliothèque en 1 clic grâce à `JSZip`.
- 🔄 **Synchro automatique** : Tourne chaque semaine automatiquement et à chaque modification.
