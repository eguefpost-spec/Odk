# ODK — Lancer la recherche d'emploi
# Usage : .\run.ps1            -> scanner les nouvelles offres
#         .\run.ps1 apply      -> scanner + postuler automatiquement
#         .\run.ps1 list       -> voir toutes les offres
#         .\run.ps1 stats      -> tableau de bord

$py = $null
foreach ($cmd in @("py", "python", "python3")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3") { $py = $cmd; break }
    } catch {}
}

if (-not $py) {
    Write-Host "Python introuvable. Lancez setup.ps1 d'abord." -ForegroundColor Red
    exit 1
}

switch ($args[0]) {
    "apply"  { & $py main.py scan --apply }
    "list"   { & $py main.py list-jobs }
    "stats"  { & $py main.py stats }
    default  { & $py main.py scan }
}
