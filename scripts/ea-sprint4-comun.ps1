# =========================================================================
# Funciones comunes de los generadores de EA del Sprint 4. Se cargan con
# dot-sourcing despues de definir $Modelo:
#     . (Join-Path $PSScriptRoot 'ea-sprint4-comun.ps1')
#
# Es el mismo esquema del Sprint 3 (ea-sprint3-comun.ps1), con dos cambios:
#
# ---- LA ORGANIZACION DEL MODELO ----
#   Un paquete por tipo de diagrama, con los diagramas y sus elementos juntos
#   adentro, sin subcarpetas por caso de uso (como en el Sprint 3):
#     CAP. 4 - Proceso de desarrollo
#       Sprint 4 - 2.1.3 Comunicación
#       Sprint 4 - Secuencia
#       Sprint 4 - Diseño de clase
#   -Rehacer borra y rehace SOLO el paquete del Sprint 4 de su generador. La
#   funcion se niega a borrar un paquete que no empiece con «Sprint 4 - »:
#   los de los Sprints 1 a 3 los acomodo Luis a mano.
#
# ---- UN SOLO GUION POR CASO DE USO ----
#   En el Sprint 3 la comunicacion y el diseno de clase leian la lista de
#   mensajes de ea-sprint3-casos.ps1 y la secuencia un guion aparte
#   (ea-sprint3-dinamica.ps1), que habia que mantener a mano con la misma
#   numeracion. Aca hay un guion solo, en ea-sprint4-casos.ps1: cada mensaje
#   lleva su grupo (g) y Mensajes-Del-Guion lo numera <grupo>.<orden> por
#   orden de aparicion. Los tres diagramas salen de la misma lista, asi que
#   el rastreo comunicacion -> secuencia -> operacion de la clase no se puede
#   desarmar.
#
# Actores: se usan los del modelo (Sprint 3, Sprint 2 o 3.10, en ese orden).
# Uno que no este en ninguno se crea en el paquete de comunicacion del
# Sprint 4, nunca en un paquete de los sprints anteriores.
# =========================================================================

$ErrorActionPreference = 'Stop'
. ([scriptblock]::Create([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'ea-sprint4-casos.ps1'), [Text.Encoding]::UTF8)))

$PREFIJO_SPRINT = 'Sprint 4 - '
$PAQ_COMUNICACION = 'Sprint 4 - 2.1.3 Comunicación'
$PAQ_SECUENCIA    = 'Sprint 4 - Secuencia'
$PAQ_CLASES       = 'Sprint 4 - Diseño de clase'

if (-not $Modelo) { $Modelo = Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx' }
$Modelo = [System.IO.Path]::GetFullPath($Modelo)
if (-not (Test-Path $Modelo)) { throw "No existe $Modelo" }

# ---- LA SEMILLA DE LOS AUTONUMERICOS (21/11/26) ----
#   En el .eapx que dejo el Sprint 3, la semilla de t_connector.Connector_ID
#   era igual al ID mas alto (las segundas pasadas por OLEDB la dejaron
#   atras). El primer conector que EA intenta crear choca con la clave
#   primaria, Update() devuelve False sin error y el conector no existe (se
#   perdia la asociacion actor -> pantalla del primer caso). Antes de abrir
#   EA, cada semilla se pone en max + 1 (ALTER ... COUNTER). No cambia ningun
#   dato: solo el proximo numero que da Access.
function Ajustar-Semillas($archivo) {
    # Sin el pool de OLE DB (OLE DB Services=-4): con el pool la conexion
    # queda abierta y EA, que abre el archivo despues en este mismo proceso,
    # se queda colgado esperandolo.
    $cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;OLE DB Services=-4;Data Source=$archivo;")
    $cn.Open()
    try {
        foreach ($t in @(@('t_object', 'Object_ID'), @('t_connector', 'Connector_ID'), @('t_diagram', 'Diagram_ID'),
                         @('t_attribute', 'ID'), @('t_operation', 'OperationID'), @('t_diagramobjects', 'Instance_ID'),
                         @('t_diagramlinks', 'Instance_ID'))) {
            $cmd = $cn.CreateCommand(); $cmd.CommandText = "SELECT MAX([$($t[1])]) FROM [$($t[0])]"
            $max = $cmd.ExecuteScalar()
            if ($max -is [DBNull]) { continue }
            $cmd = $cn.CreateCommand(); $cmd.CommandText = "ALTER TABLE [$($t[0])] ALTER COLUMN [$($t[1])] COUNTER($([int]$max + 1),1)"
            [void]$cmd.ExecuteNonQuery()
        }
    } finally { $cn.Close(); $cn.Dispose(); [System.Data.OleDb.OleDbConnection]::ReleaseObjectPool() }
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
Ajustar-Semillas $Modelo
if ($UsarEAAbierto) {
    $ea = ([System.Runtime.InteropServices.Marshal]::GetActiveObject('EA.App')).Repository
} else {
    $ea = New-Object -ComObject EA.Repository
}
if (-not $ea.OpenFile($Modelo)) { throw "No se pudo abrir $Modelo" }

# Cada generador declara en SU cuerpo «trap { Salir-ConError $_ }» (un trap
# solo cubre el bloque donde se escribe).
function Salir-ConError($err) {
    Write-Host "ERROR: $($err.Exception.Message)  [$($err.InvocationInfo.ScriptName):$($err.InvocationInfo.ScriptLineNumber)]"
    try { $ea.CloseFile(); if (-not $UsarEAAbierto) { $ea.Exit() } } catch { }
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
function Get-PaqueteTipo($nombre, $rehacer) {
    if (-not $nombre.StartsWith($PREFIJO_SPRINT)) { throw "Paquete '$nombre' fuera del Sprint 4: no se toca." }
    $cap = Get-Capitulo4
    if ($rehacer) {
        for ($i = $cap.Packages.Count - 1; $i -ge 0; $i--) {
            if ($cap.Packages.GetAt($i).Name -eq $nombre) { $cap.Packages.DeleteAt($i, $false) }
        }
        $cap.Packages.Refresh()
    }
    return Get-OCrearPaquete $cap $nombre
}
# -Rehacer con -Caso: borra solo el diagrama de ese caso y los elementos de
# ESTE paquete que estan en el (clases, lineas de vida, notas, fragmentos,
# externos del caso). Los actores de los paquetes de casos de uso no se
# tocan; sus conectores con lo borrado se van con lo borrado.
function Quitar-Diagrama($pkg, $dia) {
    # La coleccion queda vieja despues de crear el caso anterior en la misma
    # corrida: sin el Refresh, GetAt devolvia null (22/11/26).
    $pkg.Elements.Refresh(); $pkg.Diagrams.Refresh()
    $propios = @{}
    foreach ($do in $dia.DiagramObjects) {
        $el = $ea.GetElementByID($do.ElementID)
        if ($el.PackageID -eq $pkg.PackageID) { $propios[[int]$el.ElementID] = $true }
    }
    for ($i = $pkg.Diagrams.Count - 1; $i -ge 0; $i--) {
        if ($pkg.Diagrams.GetAt($i).DiagramID -eq $dia.DiagramID) { $pkg.Diagrams.DeleteAt($i, $false) }
    }
    $pkg.Diagrams.Refresh()
    # Uno por uno, buscando su posicion de nuevo cada vez: GetAt con la
    # coleccion recien agrandada por AddNew tiraba «referencia a objeto no
    # establecida» en el segundo caso de una misma corrida (22/11/26).
    foreach ($id in @($propios.Keys)) {
        $pkg.Elements.Refresh()
        $i = 0; $pos = -1
        foreach ($x in $pkg.Elements) { if ([int]$x.ElementID -eq $id) { $pos = $i; break }; $i++ }
        if ($pos -ge 0) { $pkg.Elements.DeleteAt($pos, $true) }
    }
    $pkg.Elements.Refresh()
}
# El paquete del generador y, si el diagrama del caso ya esta, lo quita (con
# -Rehacer -Caso) o avisa que no lo toca. Devuelve $true si hay que crearlo.
function Preparar-Diagrama($pkg, $nomDia) {
    $d = Get-Diagrama $pkg $nomDia
    if (-not $d) { return $true }
    if ($Rehacer -and $Caso.Count) { Quitar-Diagrama $pkg $d; Write-Host "  $nomDia : quitado para rehacerlo"; return $true }
    Write-Host "  $nomDia ya existe, no se toca"
    return $false
}

function Get-Diagrama($pkg, $nombre) {
    foreach ($d in $pkg.Diagrams) { if ($d.Name -eq $nombre) { return $d } }
    return $null
}

$ORDEN_PAQ_ACTORES = @('Sprint 3 - Casos de Uso', 'Sprint 2 - Casos de Uso', '3.10 Paquetes y casos de uso', 'Sprint 1 - Casos de Uso', $PAQ_COMUNICACION)
$cacheActor = @{}
function Get-Actor($nombre) {
    if ($cacheActor.ContainsKey($nombre)) { return $cacheActor[$nombre] }
    foreach ($paq in $ORDEN_PAQ_ACTORES) {
        $xml = $ea.SQLQuery("SELECT o.Object_ID FROM t_object o INNER JOIN t_package p ON o.Package_ID = p.Package_ID WHERE o.Object_Type = 'Actor' AND p.Name = '$paq' AND o.Name = '$nombre'")
        $doc = New-Object System.Xml.XmlDocument; $doc.LoadXml($xml)
        $fila = $doc.SelectSingleNode('//Row')
        if ($fila) { $cacheActor[$nombre] = [int]$fila.Object_ID; return $cacheActor[$nombre] }
    }
    $pCom = Get-PaqueteTipo $PAQ_COMUNICACION $false
    $a = $pCom.Elements.AddNew($nombre, 'Actor'); [void]$a.Update(); $pCom.Elements.Refresh()
    Write-Output "  (actor nuevo '$nombre' en $PAQ_COMUNICACION)" | Out-Host
    $cacheActor[$nombre] = $a.ElementID
    return $a.ElementID
}

# El actor de un participante. Los actores del sistema (Paciente, Médico...)
# son los del modelo. Los EXTERNOS (Servicio de IA, Firebase Cloud
# Messaging...) se crean uno por diagrama, en el paquete del diagrama y con el
# codigo del caso en el alias: un mensaje entre dos actores compartidos
# (FCM -> Paciente) es un conector entre elementos que estan en muchos
# diagramas, y EA lo dibujaria en todos, tambien en los del Sprint 3.
function Get-ActorDe($pkg, $p, $cu) {
    if ($p.rol -ne 'externo') { return Get-Actor $p.n }
    foreach ($e in $pkg.Elements) { if ($e.Type -eq 'Actor' -and $e.Name -eq $p.n -and $e.Alias -eq $cu) { return $e.ElementID } }
    $a = $pkg.Elements.AddNew($p.n, 'Actor'); $a.Alias = $cu
    $a.Notes = "Sistema externo, propio de $cu (ver ea-sprint4-comun.ps1, Get-ActorDe)."
    [void]$a.Update(); $pkg.Elements.Refresh()
    return $a.ElementID
}

function Poner($dia, $eid, $l, $t, $w, $h) {
    $do = $dia.DiagramObjects.AddNew("l=$([int]$l);r=$([int]($l + $w));t=$([int]$t);b=$([int]($t - $h));", '')
    $do.ElementID = $eid
    [void]$do.Update()
}

function Cerrar-Modelo {
    $ea.CloseFile(); if (-not $UsarEAAbierto) { $ea.Exit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
    Start-Sleep -Milliseconds 1500
}

function Claves-Casos($caso) {
    if ($caso.Count) { return $caso } else { return @($CASOS_SPRINT4.Keys | Sort-Object { [int]($_ -replace '\D', '') }) }
}

# El texto de un mensaje tal como se dibuja. EA le agrega «()» a todo
# mensaje que no tiene la forma nombre(...): una respuesta como «True»,
# «404», «{status, text_id}» o «(crudo, "gemini")» se escribe return(...).
function Rotulo-Mensaje($it) {
    $m = [string]$it.m
    if ($m -match '^[^\s(){}]+\(.*\)(\[[^\]]*\])?$') { return $m }
    # Una llamada con su corte de QuerySet (filter(...)[:30]) se deja como esta.
    if (-not $it.ret -and $m.Contains('(')) { return $m }
    if ($m -match '^\((.*)\)$') { return "return($($Matches[1]))" }
    return "return($m)"
}

# Los mensajes del guion, numerados <grupo>.<orden> por orden de aparicion.
# Devuelve objetos con g, num ("g.i"), o, d, m, src, ret.
function Mensajes-Del-Guion($c) {
    $orden = @{}; $lista = New-Object System.Collections.ArrayList
    foreach ($it in $c.guion) {
        if ($it.t -ne 'msg') { continue }
        $g = [int]$it.g
        if (-not $orden.ContainsKey($g)) { $orden[$g] = 0 }
        $orden[$g]++
        [void]$lista.Add(@{ g = $g; num = "$g.$($orden[$g])"; o = $it.o; d = $it.d; m = (Rotulo-Mensaje $it); src = $it.src; ret = [bool]$it.ret })
    }
    return ,$lista.ToArray()
}

# Lo que el guion tiene que cumplir para dibujarse. Devuelve los errores.
function Revisar-Caso($c) {
    $err = @()
    $k = @{}
    foreach ($p in $c.participantes) {
        if ($k.ContainsKey($p.k)) { $err += "clave repetida '$($p.k)'" }
        $k[$p.k] = $p
    }
    $usados = @{}
    foreach ($m in (Mensajes-Del-Guion $c)) {
        foreach ($x in @($m.o, $m.d)) {
            if (-not $k.ContainsKey($x)) { $err += "participante desconocido '$x' en «$($m.num): $($m.m)»" } else { $usados[$x] = $true }
        }
        if (-not $c.grupos.Contains($m.g)) { $err += "grupo $($m.g) sin nombre en «$($m.num): $($m.m)»" }
    }
    foreach ($p in $c.participantes) { if (-not $usados.ContainsKey($p.k)) { $err += "participante '$($p.k)' sin mensajes" } }
    # Dos actores del modelo no se hablan directo: el conector apareceria en
    # todos los diagramas donde esten los dos.
    foreach ($m in (Mensajes-Del-Guion $c)) {
        if ($k.ContainsKey($m.o) -and $k.ContainsKey($m.d) -and $k[$m.o].rol -eq 'actor' -and $k[$m.d].rol -eq 'actor') { $err += "mensaje entre dos actores «$($m.num): $($m.m)»" }
    }
    foreach ($r in @($c.rel)) { if ($r -and (-not $k.ContainsKey($r.d) -or -not $k.ContainsKey($r.a))) { $err += "rel con clave desconocida $($r.d)->$($r.a)" } }
    $hondo = 0
    foreach ($it in $c.guion) {
        if ($it.t -in 'alt', 'loop') { $hondo++ }
        if ($it.t -eq 'fin') { $hondo-- }
        if ($hondo -lt 0) { $err += 'un fin sin su alt o loop'; $hondo = 0 }
    }
    if ($hondo -ne 0) { $err += "quedan $hondo fragmentos sin cerrar" }
    return $err
}

# Una clase con sus atributos y operaciones (la de ea-sprint3-comun.ps1).
# Los parametros se crean con el mismo texto en nombre y tipo y la posicion
# fijada: EA imprime el TIPO, y sin la posicion los ordena alfabeticamente.
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
