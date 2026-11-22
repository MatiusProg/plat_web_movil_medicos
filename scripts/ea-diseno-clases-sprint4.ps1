param(
    [string[]]$Caso = @(),
    # Rehace el paquete «Sprint 4 - Diseño de clase» entero. OJO: las lineas
    # de vida de la secuencia apuntan a estas clases; despues de -Rehacer hay
    # que rehacer tambien la secuencia (ea-secuencia-sprint4.ps1 -Rehacer).
    [switch]$Rehacer,
    [string]$Modelo = '',
    [switch]$UsarEAAbierto
)

# =========================================================================
# CAPITULO 4 - Sprint 4 - Diagrama de DISENO de clase
#
# Lo mismo que ea-diseno-clases-sprint3.ps1 mas ea-diseno-clases-completo-
# sprint3.ps1, en una pasada:
#   frontera    : endpoints y estado de la pantalla, y sus metodos.
#   controlador : TODOS sus metodos del codigo (pedido de Karen del 01/11),
#                 y cada mensaje que recibe en el guion, si faltaba.
#   entidad     : la tabla con sus columnas, privadas, y las relaciones entre
#                 entidades con su multiplicidad (de las ForeignKey).
#   Uniones frontera/control/entidad: las del par que se habla en el guion,
#   de quien llama a quien es llamado (una respuesta no crea la union).
#   Cada clase lleva el codigo del caso de uso en el alias: asi la encuentra
#   ea-secuencia-sprint4.ps1 para clasificar sus lineas de vida.
# El acomodo es el de Reacomodar del Sprint 3: alto segun atributos y
# operaciones, ancho segun el renglon mas largo, columnas sin pisarse.
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint4-comun.ps1')
trap { Salir-ConError $_ }

$COL_X = @(40, 360, 900, 1500, 2060)
$Y0 = -80; $FILA = 210; $SEP = 60; $GAP_COL = 80
$ESTEREOTIPO = @{ boundary = 'frontera'; control = 'controlador'; entity = 'entidad' }
$PX_LETRA = 6.6

function Rol($de, $a) {
    if ($de -eq 'actor') { return 'USA' }
    if ($a -eq 'entity') { return 'PERSISTE_EN' }
    if ($a -eq 'externo') { return 'INVOCA' }
    if ($de -eq 'boundary' -and $a -eq 'control') { return 'DELEGA_EN' }
    if ($a -eq 'boundary') { return 'RESPONDE_A' }
    if ($a -eq 'actor') { return 'NOTIFICA_A' }
    return 'USA'
}
function Firma($texto) { return (($texto -replace '\s+', ' ') -replace '\(\s*', '(' -replace '\s*\)', ')').Trim() }

# Las operaciones de un participante: los mensajes que recibe (si su nombre no
# es ya una operacion propia) y las suyas, sin repetir firma.
function Ops-Completas($msgs, $p) {
    $lista = New-Object System.Collections.ArrayList; $vistas = @{}
    $nombres = @{}; foreach ($o in @($p.ops)) { if ($o) { $nombres[(($o -split '\(')[0]).Trim()] = $true } }
    foreach ($m in $msgs) {
        if ($m.ret -or $m.d -ne $p.k) { continue }
        $nom = (($m.m -split '\(')[0]).Trim()
        if ($nombres.ContainsKey($nom)) { continue }
        $f = Firma $m.m
        if (-not $vistas.ContainsKey($f)) { $vistas[$f] = $true; $nombres[$nom] = $true; [void]$lista.Add($m.m) }
    }
    foreach ($o in @($p.ops)) {
        if (-not $o) { continue }
        $f = Firma $o
        if (-not $vistas.ContainsKey($f)) { $vistas[$f] = $true; [void]$lista.Add($o) }
    }
    return ,$lista.ToArray()
}

function Medida($el) {
    $n = $el.Attributes.Count + $el.Methods.Count
    $largo = $el.Name.Length + 16
    foreach ($a in $el.Attributes) { $largo = [math]::Max($largo, $a.Name.Length + $a.Type.Length + 6) }
    foreach ($m in $el.Methods) {
        $ps = @(); foreach ($pp in $m.Parameters) { $ps += $pp.Name }
        $largo = [math]::Max($largo, $m.Name.Length + ($ps -join ', ').Length + 6)
    }
    return @{ h = 70 + $n * 15; w = [int]($largo * $PX_LETRA + 24) }
}

# -Rehacer solo: el paquete entero. -Rehacer -Caso: solo esos casos.
$pkg = Get-PaqueteTipo $PAQ_CLASES ($Rehacer -and -not $Caso.Count)

foreach ($clave in (Claves-Casos $Caso)) {
    $c = $CASOS_SPRINT4[$clave]
    $errores = @(Revisar-Caso $c)
    if ($errores.Count) { $errores | ForEach-Object { Write-Output "  $($c.cu): $_" }; throw "Los datos de $($c.cu) no cuadran." }
    $nomDia = "Diseño de clase - $($c.cu) $($c.nombre)"
    if (-not (Preparar-Diagrama $pkg $nomDia)) { continue }
    $dia = $pkg.Diagrams.AddNew($nomDia, 'Logical')
    [void]$dia.Update(); $pkg.Diagrams.Refresh()
    $msgs = Mensajes-Del-Guion $c

    # ---- las clases y su medida ---------------------------------------------
    $id = @{}; $rolDe = @{}; $caja = @{}
    foreach ($p in $c.participantes) {
        $rolDe[$p.k] = $p.rol
        if ($p.rol -eq 'actor' -or $p.rol -eq 'externo') {
            $eid = Get-ActorDe $pkg $p $c.cu; $w = 60; $h = 90
        } else {
            $ops = Ops-Completas $msgs $p
            $eid = Nueva-Clase $pkg $p.n $ESTEREOTIPO[$p.rol] $p.nota $p.atr $ops ($p.rol -eq 'entity')
            $el = $ea.GetElementByID($eid); $el.Alias = $c.cu; [void]$el.Update()
            $el.Attributes.Refresh(); $el.Methods.Refresh()
            $med = Medida $el; $w = $med.w; $h = $med.h
        }
        $id[$p.k] = $eid
        $caja[$p.k] = @{ p = $p; w = $w; h = $h }
    }

    # ---- acomodo: columnas sin pisarse, cajas apiladas ----------------------
    # Los sistemas externos van al pie de la columna de las entidades: en
    # una columna propia, a la derecha, la linea INVOCA cruzaba las tablas.
    # Con tres o mas controladores, en zigzag: la linea entre el primero y
    # el tercero atravesaba la caja del medio.
    $colDe = @{}; $filaDe = @{}
    $maxEnt = ($c.participantes | Where-Object { [int]$_.col -eq 3 } | ForEach-Object { [double]$_.f } | Measure-Object -Maximum).Maximum
    if ($null -eq $maxEnt) { $maxEnt = 0 }
    $extra = 1
    foreach ($p in $c.participantes) {
        $colDe[$p.k] = [int]$p.col; $filaDe[$p.k] = [double]$p.f
        if ($p.rol -eq 'externo') { $colDe[$p.k] = 3; $filaDe[$p.k] = $maxEnt + $extra; $extra++ }
    }
    # Un actor que no le habla a ninguna pantalla (el Sistema que lanza un
    # comando) va al pie de la columna de las pantallas: desde la columna 0
    # sus lineas a los controladores atravesaban la caja de la frontera.
    $maxPant = ($c.participantes | Where-Object { [int]$_.col -eq 1 } | ForEach-Object { [double]$_.f } | Measure-Object -Maximum).Maximum
    if ($null -eq $maxPant) { $maxPant = 0 }
    foreach ($p in $c.participantes) {
        if ($p.rol -ne 'actor') { continue }
        $aPantalla = @($msgs | Where-Object { ($_.o -eq $p.k -and $rolDe[$_.d] -eq 'boundary') -or ($_.d -eq $p.k -and $rolDe[$_.o] -eq 'boundary') }).Count
        if ($aPantalla -eq 0 -and @($c.participantes | Where-Object { [int]$_.col -eq 1 }).Count -gt 0) { $colDe[$p.k] = 1; $filaDe[$p.k] = $maxPant + 2.5 }
    }
    $cols = @($c.participantes | ForEach-Object { $colDe[$_.k] } | Sort-Object -Unique)
    $x = $COL_X[0]; $primera = $true
    foreach ($col in $cols) {
        $deCol = @($c.participantes | Where-Object { $colDe[$_.k] -eq $col } | Sort-Object { $filaDe[$_.k] })
        $zig = ($col -eq 2 -and $deCol.Count -ge 3)
        if (-not $primera) { $x = [math]::Max($x, $COL_X[$col]) }
        $ancho = 0; $piso = $null; $i = 0
        foreach ($p in $deCol) {
            $b = $caja[$p.k]
            $dx = $(if ($zig -and ($i % 2)) { 280 } else { 0 }); $i++
            $t = [int]($Y0 - $filaDe[$p.k] * $FILA)
            if ($null -ne $piso) { $t = [math]::Min($t, $piso - $SEP) }
            Poner $dia $id[$p.k] ($x + $dx) $t $b.w $b.h
            $piso = $t - $b.h
            $ancho = [math]::Max($ancho, $dx + $b.w)
        }
        $x = $x + $ancho + $GAP_COL; $primera = $false
    }

    # ---- una asociacion por par que se habla (salvo entidad-entidad) ------
    $pares = @{}
    foreach ($m in $msgs) {
        if ($m.o -eq $m.d) { continue }
        if ($rolDe[$m.o] -eq 'entity' -and $rolDe[$m.d] -eq 'entity') { continue }
        $k = (@($m.o, $m.d) | Sort-Object) -join '|'
        if ($pares.ContainsKey($k)) { continue }
        $pares[$k] = $true
        $de = $m.o; $a = $m.d
        if ($m.ret) { $de = $m.d; $a = $m.o }
        $con = $ea.GetElementByID($id[$de]).Connectors.AddNew((Rol $rolDe[$de] $rolDe[$a]), 'Association')
        $con.SupplierID = $id[$a]
        $con.Direction  = 'Source -> Destination'
        if (-not $con.Update()) { throw "EA no guardó la asociación $de -> $a de $($c.cu): $($con.GetLastError())" }
        $con.ClientEnd.Cardinality = '1'; [void]$con.ClientEnd.Update()
        $con.SupplierEnd.Cardinality = $(if ($rolDe[$a] -eq 'entity') { '0..*' } else { '1' }); [void]$con.SupplierEnd.Update()
    }

    # ---- relaciones entre entidades, con su multiplicidad -------------------
    foreach ($r in @($c.rel)) {
        if (-not $r) { continue }
        $con = $ea.GetElementByID($id[$r.d]).Connectors.AddNew($r.r, 'Association')
        $con.SupplierID = $id[$r.a]
        [void]$con.Update()
        $con.ClientEnd.Cardinality = $r.cd; [void]$con.ClientEnd.Update()
        $con.SupplierEnd.Cardinality = $r.ca; [void]$con.SupplierEnd.Update()
    }

    # Relaciones entre actores que vienen de otros diagramas: ocultas.
    $dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()
    foreach ($l in $dia.DiagramLinks) {
        $cn2 = $ea.GetConnectorByID($l.ConnectorID)
        if ($cn2.Type -ne 'Association') { $l.IsHidden = $true; [void]$l.Update() }
    }

    Write-Output ("  {0} : {1} clases, {2} asociaciones, {3} entre entidades" -f $nomDia, $dia.DiagramObjects.Count, $pares.Count, @($c.rel | Where-Object { $_ }).Count)
}

Cerrar-Modelo
Write-Output 'OK'
