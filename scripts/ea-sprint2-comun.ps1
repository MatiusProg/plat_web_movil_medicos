# =========================================================================
# Funciones comunes de los generadores de EA del Sprint 2. Se cargan con
# dot-sourcing despues de definir $Modelo:
#     . (Join-Path $PSScriptRoot 'ea-sprint2-comun.ps1')
#
# ---- LA ORGANIZACION DEL MODELO ----
#   Como en VioletBoutique.eapx: UN paquete por tipo de diagrama, con los
#   diagramas Y sus elementos juntos adentro, sin subcarpetas por caso de
#   uso. Asi se encuentra un diagrama sin abrir cinco niveles de carpetas, y
#   el diagrama y sus elementos estan en el mismo paquete (si no, EA escribe
#   "(from <paquete>)" debajo de cada uno).
#
#   CAP. 4 - Proceso de desarrollo
#     Sprint 2 - Casos de Uso                    1.3
#     Sprint 2 - 2.1.3 Comunicación              2.1.3
#     Sprint 2 - 2.1.4.1 Clases de análisis      2.1.4.1
#     Sprint 2 - 2.1.4.2 Secuencia               2.1.4.2
#     Sprint 2 - 2.1.4.3 Estado                  2.1.4.3
#     Sprint 2 - 2.1.4.4 Tiempo                  2.1.4.4
#     Sprint 2 - 2.1.4.5 Navegación              2.1.4.5
#
#   Cada generador rehace SU paquete entero con -Rehacer: los datos son la
#   fuente y regenerar todos los casos de uso tarda segundos.
# =========================================================================

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'ea-sprint2-casos.ps1')

$Modelo = [System.IO.Path]::GetFullPath($Modelo)
if (-not (Test-Path $Modelo)) { throw "No existe $Modelo" }
$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($Modelo)) { throw "No se pudo abrir $Modelo" }

# Si algo falla a mitad de camino, EA queda abierto en segundo plano, sin
# ventana, reteniendo el archivo. Cada generador declara, en SU cuerpo,
#     trap { Salir-ConError $_ }
# porque un trap solo cubre el bloque donde se escribe: definido aca, dentro
# del archivo que se carga con dot-sourcing, no protege al generador.
function Salir-ConError($err) {
    Write-Host "ERROR: $($err.Exception.Message)  [$($err.InvocationInfo.ScriptName):$($err.InvocationInfo.ScriptLineNumber)]"
    try { $ea.CloseFile(); $ea.Exit() } catch { }
    try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null } catch { }
    exit 1
}
function Get-OCrearPaquete($padre, $nombre) {
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update()
    $padre.Packages.Refresh(); return $p
}

function Get-Capitulo4 {
    $root  = $ea.Models.GetAt(0)
    $pRaiz = Get-OCrearPaquete $root 'Plataforma Médica Multi-Inquilino'
    return Get-OCrearPaquete $pRaiz 'CAP. 4 - Proceso de desarrollo'
}

# El paquete plano de un tipo de diagrama. Con $rehacer lo borra entero y lo
# crea de nuevo: diagramas, elementos y conectores.
function Get-PaqueteTipo($nombre, $rehacer) {
    $cap = Get-Capitulo4
    if ($rehacer) {
        for ($i = $cap.Packages.Count - 1; $i -ge 0; $i--) {
            if ($cap.Packages.GetAt($i).Name -eq $nombre) { $cap.Packages.DeleteAt($i, $false) }
        }
        $cap.Packages.Refresh()
    }
    return Get-OCrearPaquete $cap $nombre
}

function Get-Diagrama($pkg, $nombre) {
    foreach ($d in $pkg.Diagrams) { if ($d.Name -eq $nombre) { return $d } }
    return $null
}

# Un actor del paquete de casos de uso del Sprint 2. Con $crear, si no
# existe lo agrega ahi (los sistemas externos -el Servicio de IA, la
# Pasarela de Pago- no estan en el diagrama 1.3 pero son lineas de vida).
function Get-Actor($nombre, $crear) {
    $xml = $ea.SQLQuery("SELECT o.Object_ID FROM t_object o INNER JOIN t_package p ON o.Package_ID = p.Package_ID WHERE o.Object_Type = 'Actor' AND p.Name = 'Sprint 2 - Casos de Uso' AND o.Name = '$nombre'")
    $doc = New-Object System.Xml.XmlDocument; $doc.LoadXml($xml)
    $fila = $doc.SelectSingleNode('//Row')
    if ($fila) { return [int]$fila.Object_ID }
    if (-not $crear) { throw "No está el actor '$nombre'. Corré antes ea-cu-modelo-sprint2.ps1." }
    $pCu = Get-OCrearPaquete (Get-Capitulo4) 'Sprint 2 - Casos de Uso'
    $a = $pCu.Elements.AddNew($nombre, 'Actor'); [void]$a.Update(); $pCu.Elements.Refresh()
    return $a.ElementID
}

function Poner($dia, $eid, $l, $t, $w, $h) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l + $w);t=$t;b=$($t - $h);", '')
    $do.ElementID = $eid
    [void]$do.Update()
}

function Cerrar-Modelo {
    $ea.CloseFile(); $ea.Exit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
    Start-Sleep -Milliseconds 1500
}

function Claves-Casos($caso) {
    if ($caso.Count) { return $caso } else { return @($CASOS_SPRINT2.Keys) }
}

# Una clase de analisis con sus atributos y operaciones. Las operaciones se
# crean con su nombre y los parametros aparte, con el mismo texto en nombre y
# tipo y la posicion fijada: EA imprime el TIPO del parametro, y sin la
# posicion los ordena alfabeticamente (GUIA-DIAGRAMAS-EA 7.4).
function Nueva-Clase($pkg, $nombre, $estereotipo, $nota, $atr, $ops, $privados) {
    $e = $pkg.Elements.AddNew($nombre, 'Class')
    $e.Stereotype = $estereotipo; $e.StereotypeEx = $estereotipo
    if ($nota) { $e.Notes = $nota }
    [void]$e.Update()
    foreach ($a in @($atr)) {
        if (-not $a) { continue }
        $partes = $a -split ' : ', 2
        $at = $e.Attributes.AddNew($partes[0], $(if ($partes.Count -gt 1) { $partes[1] } else { '' }))
        $at.Visibility = $(if ($privados) { 'Private' } else { 'Public' })
        [void]$at.Update()
    }
    foreach ($o in @($ops)) {
        if (-not $o) { continue }
        $nom = $o; $params = @()
        if ($o -match '^([^(]+)\(([^()]*)\)$') { $nom = $Matches[1]; $params = @($Matches[2] -split ',\s*' | Where-Object { $_ }) }
        $m = $e.Methods.AddNew($nom.Trim(), ''); [void]$m.Update()
        $pos = 0
        foreach ($par in $params) { $p = $m.Parameters.AddNew($par, $par); $p.Position = $pos; $pos++; [void]$p.Update() }
    }
    return $e.ElementID
}
