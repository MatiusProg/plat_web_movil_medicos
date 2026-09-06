param(
    # Nombre exacto del diagrama a exportar. Sin esto, exporta todos.
    [string]$Diagrama = ''
)

# =========================================================================
# Exporta a PNG los diagramas del modelo.
#
# El tercer parametro de PutDiagramImageToFile es el formato: 1 = PNG. Se le
# pasa el DiagramGUID, NO el DiagramID; con el ID devuelve falso sin explicar
# nada.
#
# OJO con la marca de agua: EA 15 Trial mete a veces
# "EA 15.0 Unregistered Trial Version" en la imagen, y no siempre. Hay que
# MIRAR cada PNG antes de pegarlo en el documento; si sale marcado, exportarlo
# a mano desde EA (Diagram > Save Image to File) suele salir limpio.
# =========================================================================

$ErrorActionPreference = 'Stop'

$modelo  = 'D:\UNI\Si2\PROYECTO_MEDICOS\docs\diagramas\PlataformaMedica.eapx'
$destino = 'D:\UNI\Si2\PROYECTO_MEDICOS\docs\diagramas\png'

if (-not (Test-Path $modelo))  { throw "No existe $modelo" }
if (-not (Test-Path $destino)) { New-Item -ItemType Directory -Path $destino | Out-Null }

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }
$prj = $ea.GetProjectInterface()

function Recolectar($pkg, $acc) {
    foreach ($d in $pkg.Diagrams) { [void]$acc.Add($d) }
    foreach ($s in $pkg.Packages) { Recolectar $s $acc }
}

$todos = New-Object System.Collections.ArrayList
foreach ($m in $ea.Models) { Recolectar $m $todos }

$n = 0
foreach ($d in $todos) {
    if ($Diagrama -and $d.Name -ne $Diagrama) { continue }

    # Nombre de archivo sin caracteres que Windows no admite.
    $archivo = ($d.Name -replace '[\\/:*?"<>|]', '-') + '.png'
    $ruta    = Join-Path $destino $archivo

    $ok = $prj.PutDiagramImageToFile($d.DiagramGUID, $ruta, 1)
    $visibles = 0
    foreach ($l in $d.DiagramLinks) { if (-not $l.IsHidden) { $visibles++ } }

    if ($ok) {
        $kb = [math]::Round((Get-Item $ruta).Length / 1KB, 0)
        Write-Output "  OK  $archivo  ($($d.DiagramObjects.Count) objetos, $visibles relaciones visibles, $kb KB)"
        $n++
    } else {
        Write-Output "  FALLO al exportar '$($d.Name)'"
    }
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()

Write-Output "$n diagrama(s) exportado(s) en $destino"
