param(
    # Carpeta donde dejar los PNG. Para VERIFICAR, una carpeta temporal: los
    # PNG que van al documento los exporta Luis a mano desde EA.
    [Parameter(Mandatory = $true)][string]$Destino,
    # Solo los diagramas cuyo nombre contenga este texto (ej. 'CU48').
    [string]$Filtro = '',
    [string]$Modelo = ''
)

# =========================================================================
# Exporta a PNG los diagramas de los paquetes del Sprint 4 (los que empiezan
# con «Sprint 4 - » en CAP. 4). Es ea-exportar-png.ps1 con destino y filtro
# como parametros, para mirar lo generado sin tocar docs/diagramas/png.
# PutDiagramImageToFile recibe el DiagramGUID (no el ID); 1 = PNG.
# =========================================================================

$ErrorActionPreference = 'Stop'
if (-not $Modelo) { $Modelo = Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx' }
$Modelo = [System.IO.Path]::GetFullPath($Modelo)
if (-not (Test-Path $Destino)) { New-Item -ItemType Directory -Path $Destino | Out-Null }

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($Modelo)) { throw "No se pudo abrir $Modelo" }
$prj = $ea.GetProjectInterface()
$n = 0
try {
    $cap = $null
    foreach ($p in $ea.Models.GetAt(0).Packages) { foreach ($q in $p.Packages) { if ($q.Name -eq 'CAP. 4 - Proceso de desarrollo') { $cap = $q } } }
    if (-not $cap) { throw 'No está CAP. 4 - Proceso de desarrollo' }
    foreach ($pkg in $cap.Packages) {
        if (-not $pkg.Name.StartsWith('Sprint 4 - ')) { continue }
        foreach ($d in $pkg.Diagrams) {
            if ($Filtro -and -not $d.Name.Contains($Filtro)) { continue }
            $archivo = ($d.Name -replace '[\\/:*?"<>|]', '-') + '.png'
            $ruta = Join-Path $Destino $archivo
            if ($prj.PutDiagramImageToFile($d.DiagramGUID, $ruta, 1)) {
                Write-Output "  OK  $archivo  ($($d.DiagramObjects.Count) objetos)"; $n++
            } else { Write-Output "  FALLO  $($d.Name)" }
        }
    }
} finally {
    $ea.CloseFile(); $ea.Exit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
Write-Output "$n diagrama(s) exportado(s) en $Destino"
