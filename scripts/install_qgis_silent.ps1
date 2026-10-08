# Installation silencieuse de QGIS LTR (nécessite une validation UAC)
# Usage : powershell -ExecutionPolicy Bypass -File scripts\install_qgis_silent.ps1 [-MsiPath "C:\...\QGIS.msi"]

param(
    [string]$MsiPath = "$env:TEMP\QGIS-OSGeo4W-3.44.15-2.msi",
    [string]$LogPath = "$env:TEMP\qgis_install.log"
)

if (-not (Test-Path $MsiPath)) {
    Write-Output "ERREUR: introuvable : $MsiPath"
    exit 2
}

$msiArgs = "/i `"$MsiPath`" /qn /norestart /L*v `"$LogPath`""
try {
    $proc = Start-Process msiexec.exe -ArgumentList $msiArgs -Verb RunAs -Wait -PassThru
    Write-Output "code retour msiexec: $($proc.ExitCode)"
} catch {
    Write-Output "ERREUR: $($_.Exception.Message)"
    exit 3
}

$qgisDirs = @("C:\Program Files\QGIS 3.44", "C:\Program Files\QGIS 3.44.15") |
    Where-Object { Test-Path $_ }
if ($qgisDirs) {
    Write-Output "QGIS installe dans : $($qgisDirs[0])"
    exit 0
}
exit 1
