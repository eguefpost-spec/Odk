# Script pour creer config.yaml - modifiez les valeurs ci-dessous puis lancez ce script

$email    = "saminoutassiou5@gmail.com"
$password = "CHANGEZ_VOTRE_MOT_DE_PASSE"   # changez ceci apres avoir reinitialise sur LinkedIn

$content = @"
linkedin:
  email: "$email"
  password: "$password"

search:
  keywords:
    - "Chef de projet humanitaire"
    - "MEAL Officer"
    - "Coordinateur RRM"
    - "Resilience Sahel"
    - "Geographe"
  location: "Niger"
  remote: true
  experience_levels:
    - mid_senior
    - associate
  date_posted: "week"
  easy_apply_only: true

auto_apply:
  enabled: false
  max_per_run: 10
  cover_letter: |
    Bonjour,
    Je vous contacte concernant votre offre. Mon profil correspond a vos besoins.
    Cordialement.

notifications:
  email:
    enabled: false
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    sender: "$email"
    password: "app_password_gmail"
    recipient: "$email"
  min_jobs_to_notify: 3

database:
  path: "data/jobs.db"
"@

$content | Out-File -FilePath "config.yaml" -Encoding UTF8
Write-Host "config.yaml cree avec succes !" -ForegroundColor Green
