# ODK — Automatisation de recherche d'emploi LinkedIn

Outil Python pour automatiser la veille d'offres LinkedIn, le suivi des candidatures et l'envoi de candidatures Easy Apply.

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## Configuration

Éditez `config.yaml` :

```yaml
linkedin:
  email: "votre@email.com"
  password: "votre_mot_de_passe"

search:
  keywords:
    - "Développeur Python"
  location: "Paris, France"
  remote: true
  easy_apply_only: true
  date_posted: "week"      # day / week / month / any

auto_apply:
  enabled: false           # true = postuler automatiquement
  max_per_run: 10

notifications:
  email:
    enabled: false
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    sender: "votre@email.com"
    password: "app_password_gmail"
    recipient: "votre@email.com"
```

## Utilisation

### Scanner les offres

```bash
python main.py scan
```

Avec envoi automatique des candidatures Easy Apply :

```bash
python main.py scan --apply
```

En mode headless (sans fenêtre de navigateur) :

```bash
python main.py scan --headless --apply
```

### Consulter les offres

```bash
python main.py list-jobs                    # toutes les offres
python main.py list-jobs --status new       # nouvelles offres
python main.py list-jobs --status applied   # candidatures envoyées
```

### Mettre à jour un statut

```bash
python main.py update <JOB_ID> interview --notes "Entretien RH prévu lundi"
python main.py update <JOB_ID> rejected
python main.py update <JOB_ID> offer --notes "Offre reçue, à décider avant vendredi"
```

Statuts disponibles : `new`, `applied`, `rejected`, `interview`, `offer`, `ignored`

### Statistiques

```bash
python main.py stats
```

## Automatisation planifiée (cron)

Scanner chaque matin à 8h :

```
0 8 * * 1-5 cd /chemin/vers/Odk && python main.py scan --headless
```

## Notes importantes

- **Sécurité** : Ne commitez jamais `config.yaml` avec vos identifiants. Utilisez `.gitignore`.
- **Easy Apply** : Fonctionne uniquement pour les offres avec le bouton Easy Apply simple. Les formulaires complexes nécessitent une intervention manuelle.
- **Limite** : LinkedIn peut détecter l'automatisation. Utilisez des délais raisonnables et ne dépassez pas ~20 candidatures/jour.
- **Gmail** : Pour les notifications email, générez un [App Password](https://myaccount.google.com/apppasswords) au lieu d'utiliser votre mot de passe principal.
