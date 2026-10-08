# Installe TerangaGIS dans le profil QGIS courant (développement).
# Le plugin est copié sous le nom `terangagis` avec les paquets embarqués
# `common` et `mcp`, afin que les imports fonctionnent dans QGIS.
#
# Usage :
#   powershell -ExecutionPolicy Bypass -File scripts/install_plugin.ps1
#
param(
    [string]$Profile = "$env:APPDATA\QGIS\QGIS3\profiles\default",
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"

$dest = Join-Path $Profile "python\plugins\terangagis"
Write-Host "Destination : $dest"

if (Test-Path $dest) {
    Remove-Item -Recurse -Force $dest
}

New-Item -ItemType Directory -Force -Path $dest | Out-Null

# Contenu du plugin (hors __pycache__)
Get-ChildItem -Path (Join-Path $RepoRoot "plugin") -Exclude "__pycache__" | ForEach-Object {
    Copy-Item -Recurse -Force $_.FullName (Join-Path $dest $_.Name)
}

# Paquets embarqués requis
foreach ($pkg in @("common", "mcp")) {
    $src = Join-Path $RepoRoot $pkg
    if (Test-Path $src) {
        $target = Join-Path $dest $pkg
        New-Item -ItemType Directory -Force -Path $target | Out-Null
        Copy-Item -Recurse -Force (Join-Path $src "*") $target
    }
}

# Nettoyage des caches
Get-ChildItem -Path $dest -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

Write-Host "TerangaGIS installé. Redémarrez QGIS puis activez l'extension."
