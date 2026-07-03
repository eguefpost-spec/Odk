# ODK – Générateur de PDF des codes QR (App Users)

Outil en ligne de commande qui se connecte à un serveur **ODK Central**,
récupère les **App Users** (utilisateurs mobiles) d'un projet, génère leur
**code QR de configuration ODK Collect**, et assemble le tout dans un **PDF
imprimable**.

Chaque code QR est construit au format exact attendu par ODK Collect — le même
que celui affiché par l'interface web d'ODK Central :
`base64( zlib_deflate( settings_json ) )`.

## Prérequis

```bash
pip install -r requirements.txt
```

> La machine qui exécute le script doit pouvoir joindre votre serveur ODK
> Central (ici `https://odk.adkoul.online`).

## Utilisation

```bash
# Le mot de passe est demandé de façon interactive (jamais stocké) :
python3 odk_qr_pdf.py \
    --url https://odk.adkoul.online \
    --project 6 \
    --email saminou@adkoul.org \
    --out codes_qr_projet6.pdf
```

Ou en passant le mot de passe par variable d'environnement (utile pour
l'automatisation) :

```bash
export ODK_PASSWORD='votreMotDePasse'
python3 odk_qr_pdf.py --url https://odk.adkoul.online --project 6 \
    --email saminou@adkoul.org --out codes_qr_projet6.pdf
```

## Options

| Option              | Description                                                              |
| ------------------- | ------------------------------------------------------------------------ |
| `--url`             | URL de base du serveur ODK Central (**obligatoire**)                     |
| `--project`         | Identifiant numérique du projet, ex. `6` (**obligatoire**)               |
| `--email`           | Email de connexion ODK Central (**obligatoire**)                         |
| `--out`             | Nom du fichier PDF généré (défaut : `codes_qr.pdf`)                       |
| `--legacy`          | QR « non managé » (sans `form_update_mode` / `autosend`)                  |
| `--include-revoked` | Inclure les App Users révoqués (ignorés par défaut car sans code QR)     |

## Sécurité

- Le **mot de passe n'est jamais écrit dans le code ni dans le dépôt** : il est
  demandé au lancement (`getpass`) ou lu depuis `ODK_PASSWORD`.
- Les codes QR contiennent les **jetons d'accès** des App Users : traitez le PDF
  généré comme un document sensible.

## Comment scanner

Sur le téléphone, dans **ODK Collect** : menu `⋮` → **Configurer via code QR** →
scanner le code de l'agent concerné.

---

# Déployer un formulaire dans tous les projets

`deploy_form_all_projects.py` copie un formulaire existant (ex. **« F4 -
Retour communautaire (feedback et plaintes) »** du projet DDC) vers **tous les
autres projets** du serveur : téléchargement de la définition (XLSForm ou XML)
et des pièces jointes, publication, et optionnellement attribution de l'accès
aux App Users.

```bash
export ODK_PASSWORD='votreMotDePasse'

# 1. Essai à blanc (montre ce qui serait fait, ne modifie rien) :
python3 deploy_form_all_projects.py \
    --url https://odk.adkoul.online \
    --email saminou@adkoul.org \
    --source-project DDC \
    --form F4 \
    --grant-app-users

# 2. Si le résultat convient, exécuter réellement :
python3 deploy_form_all_projects.py \
    --url https://odk.adkoul.online \
    --email saminou@adkoul.org \
    --source-project DDC \
    --form F4 \
    --grant-app-users \
    --apply
```

| Option              | Description                                                             |
| ------------------- | ----------------------------------------------------------------------- |
| `--source-project`  | Projet source : id ou partie du nom (ex. `DDC`)                          |
| `--form`            | Formulaire à copier : partie de l'id ou du nom (ex. `F4`)                |
| `--projects`        | Limiter aux projets cibles donnés ; défaut : tous sauf source/archivés  |
| `--update`          | Publier une nouvelle version là où le formulaire existe déjà            |
| `--grant-app-users` | Donner l'accès au formulaire aux App Users actifs de chaque projet      |
| `--apply`           | Exécuter réellement (sans ce drapeau : essai à blanc)                   |
