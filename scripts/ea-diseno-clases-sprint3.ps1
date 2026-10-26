param(
    [string[]]$Caso = @(),
    # Rehace el paquete entero.
    [switch]$Rehacer,
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx')
)

# =========================================================================
# CAPITULO 4 - Sprint 3 - Diagrama de DISENO de clase
#
# Desde el Sprint 3 el "analisis de clase" pasa a ser "diseno de clase" y va
# despues del diagrama de secuencia (antes de navegacion, estado y tiempo).
# Lo que cambia respecto de ea-clases-sprint2.ps1:
#   frontera    : los metodos y atributos de la pantalla. Cada mensaje que le
#                 llega en la comunicacion/secuencia es una operacion suya.
#   controlador : TODAS sus operaciones, y puede haber varios por caso de uso.
#                 Tambien aca, cada mensaje recibido es una operacion.
#   entidad     : la tabla con sus columnas, y las relaciones ENTRE entidades
#                 con su multiplicidad en los dos extremos (1, 0..1, 0..*,
#                 1..*), sacadas de las ForeignKey del modelo.
# Las uniones frontera/control/entidad son las del par que se habla en la
# comunicacion, como en el Sprint 2.
# Los datos estan en ea-sprint3-casos.ps1.
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint3-comun.ps1')
trap { Salir-ConError $_ }

$COL_X = @(40, 360, 900, 1500, 2060)
$Y0 = -80; $FILA = 210; $SEP = 60
$ANCHO = @{ boundary = 480; control = 500; entity = 360 }
$ESTEREOTIPO = @{ boundary = 'frontera'; control = 'controlador'; entity = 'entidad' }

function Rol($de, $a) {
    if ($de -eq 'actor') { return 'USA' }
    if ($a -eq 'entity') { return 'PERSISTE_EN' }
    if ($a -eq 'externo') { return 'INVOCA' }
    if ($de -eq 'boundary' -and $a -eq 'control') { return 'DELEGA_EN' }
    if ($a -eq 'boundary') { return 'RESPONDE_A' }
    return 'USA'
}

$pkg = Get-PaqueteTipo 'Sprint 3 - Diseño de clase' $Rehacer

foreach ($clave in (Claves-Casos $Caso)) {
    $c = $CASOS_SPRINT3[$clave]
    $nomDia = "Diseño de clase - $($c.cu) $($c.nombre)"
    if (Get-Diagrama $pkg $nomDia) { Write-Output "  $nomDia ya existe, no se toca"; continue }
    $dia = $pkg.Diagrams.AddNew($nomDia, 'Logical')
    [void]$dia.Update(); $pkg.Diagrams.Refresh()

    # ---- operaciones: las propias mas cada mensaje recibido ----------------
    $opsDe = @{}
    foreach ($p in $c.participantes) { $opsDe[$p.k] = New-Object System.Collections.ArrayList; foreach ($o in @($p.ops)) { if ($o) { [void]$opsDe[$p.k].Add($o) } } }
    foreach ($m in $c.mensajes) {
        if ($m.ret) { continue }
        $lista = $opsDe[$m.a]
        $nom = ($m.m -split '\(')[0]
        $ya = $false
        foreach ($o in $lista) { if ((($o -split '\(')[0]) -eq $nom) { $ya = $true } }
        if (-not $ya) { [void]$lista.Insert(0, $m.m) }
    }

    # ---- las cajas, apiladas por columna sin pisarse ----------------------
    $id = @{}; $rolDe = @{}; $piso = @{}
    foreach ($p in ($c.participantes | Sort-Object { $_.col }, { $_.f })) {
        $rolDe[$p.k] = $p.rol
        $x = $COL_X[$p.col]
        $t = [int]($Y0 - $p.f * $FILA)
        if ($piso.ContainsKey($p.col)) { $t = [math]::Min($t, $piso[$p.col] - $SEP) }
        if ($p.rol -eq 'actor' -or $p.rol -eq 'externo') {
            $eid = Get-Actor $p.n ($p.rol -eq 'externo'); $w = 60; $h = 90
        } else {
            $ops = @($opsDe[$p.k])
            $eid = Nueva-Clase $pkg $p.n $ESTEREOTIPO[$p.rol] $p.nota $p.atr $ops ($p.rol -eq 'entity')
            $el = $ea.GetElementByID($eid); $el.Alias = $c.cu; [void]$el.Update()
            $w = $ANCHO[$p.rol]
            $h = 70 + (@($p.atr | Where-Object { $_ }).Count + $ops.Count) * 15
        }
        Poner $dia $eid $x $t $w $h
        $piso[$p.col] = $t - $h
        $id[$p.k] = $eid
    }

    # ---- una asociacion por par que se habla (salvo entidad-entidad) ------
    $pares = @{}
    foreach ($m in $c.mensajes) {
        if ($m.d -eq $m.a) { continue }
        if ($rolDe[$m.d] -eq 'entity' -and $rolDe[$m.a] -eq 'entity') { continue }
        $k = (@($m.d, $m.a) | Sort-Object) -join '|'
        if ($pares.ContainsKey($k)) { continue }
        $pares[$k] = $true
        # La flecha va de quien llama a quien es llamado; una respuesta no
        # crea la union al reves.
        $de = $m.d; $a = $m.a
        if ($m.ret) { $de = $m.a; $a = $m.d }
        $con = $ea.GetElementByID($id[$de]).Connectors.AddNew((Rol $rolDe[$de] $rolDe[$a]), 'Association')
        $con.SupplierID = $id[$a]
        $con.Direction  = 'Source -> Destination'
        [void]$con.Update()
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

    $dia.DiagramObjects.Refresh()
    Write-Output ("  {0} : {1} clases, {2} asociaciones, {3} entre entidades" -f $nomDia, $dia.DiagramObjects.Count, $pares.Count, @($c.rel).Count)
}

Cerrar-Modelo
Write-Output 'OK'
