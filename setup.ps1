# ODK — Script d'installation automatique
# Lancez : powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"

Write-Host "`n=== ODK — Installation ===" -ForegroundColor Cyan

# 1. Trouver Python
$py = $null
foreach ($cmd in @("py", "python", "python3")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3") {
            $py = $cmd
            Write-Host "Python trouve : $ver ($cmd)" -ForegroundColor Green
            break
        }
    } catch {}
}

if (-not $py) {
    Write-Host "Python 3 introuvable. Installez-le depuis https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "Cochez 'Add Python to PATH' lors de l'installation." -ForegroundColor Yellow
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}

# 2. Desactiver l'alias Windows Store si necessaire
$storeAlias = "$env:LOCALAPPDATA\Microsoft\WindowsApps\python.exe"
if (Test-Path $storeAlias) {
    Write-Host "Alias Windows Store detecte — utilisez 'py' a la place de 'python'" -ForegroundColor Yellow
}

# 3. Installer les dependances pip
Write-Host "`nInstallation des dependances..." -ForegroundColor Cyan
& $py -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "Erreur pip install" -ForegroundColor Red; exit 1
}
Write-Host "Dependances installees" -ForegroundColor Green

# 4. Installer Playwright + Chromium
Write-Host "`nInstallation de Chromium (Playwright)..." -ForegroundColor Cyan
& $py -m playwright install chromium
if ($LASTEXITCODE -ne 0) {
    Write-Host "Erreur playwright install" -ForegroundColor Red; exit 1
}
Write-Host "Chromium installe" -ForegroundColor Green

# 5. Creer config.yaml si absent
if (-not (Test-Path "config.yaml")) {
    Copy-Item "config.yaml.example" "config.yaml"
    Write-Host "`nconfig.yaml cree depuis l'exemple" -ForegroundColor Green
} else {
    Write-Host "`nconfig.yaml existe deja" -ForegroundColor Yellow
}

# 6. Ouvrir config.yaml dans le Bloc-notes
Write-Host "`nOuverture de config.yaml pour configuration..." -ForegroundColor Cyan
Write-Host "Remplissez votre email LinkedIn, mot de passe et mots-cles de recherche." -ForegroundColor Yellow
Start-Process notepad "config.yaml" -Wait

Write-Host "`n=== Installation terminee ===" -ForegroundColor Green
Write-Host "Lancez ensuite : " -NoNewline
Write-Host ".\run.ps1" -ForegroundColor Cyan
Read-Host "`nAppuyez sur Entree pour quitter"
