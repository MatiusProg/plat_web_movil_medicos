param(
    [string[]]$Caso = @(),
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx'),
    # Usa el EA que ya esta abierto (sin proyecto) en vez de levantar uno.
    [switch]$UsarEAAbierto,
    # Solo informa que agregaria, sin escribir.
    [switch]$Simular
)

# =========================================================================
# CAPITULO 4 - Sprint 3 - Diseno de clase con TODOS los metodos (01/11/26)
#
# Karen pidio que cada clase de diseno muestre todos sus metodos del codigo,
# no solo los mensajes que recibe. Este script:
#   1. Si el diagrama del caso de uso ya esta en el eapx (CU27 a CU34): le
#      agrega a cada clase los metodos que le faltan, de
#      ea-sprint3-metodos.ps1. NO rehace las clases: las lineas de vida de
#      las secuencias apuntan a ellas (ClassifierID) y se perderian.
#   2. Si no esta (CU24 rehecho, CU31 nuevo): lo crea igual que
#      ea-diseno-clases-sprint3.ps1 de Mateo, con los datos de
#      ea-sprint3-casos-us23-us30.ps1, que ya traen todos los metodos.
#   3. En los dos casos reacomoda las cajas: alto segun atributos y
#      operaciones, ancho segun el renglon mas largo, cada columna corrida
#      lo necesario para no pisar la siguiente y las cajas de una columna
#      apiladas sin encimarse. Las x relativas y el orden se conservan.
# Para regenerar CU24 primero se borran sus diagramas con
# .claude/herramientas/borrar-diagramas-ea.ps1 (o a mano en EA).
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint3-comun.ps1')
. (Join-Path $PSScriptRoot 'ea-sprint3-casos-us23-us30.ps1')
. (Join-Path $PSScriptRoot 'ea-sprint3-metodos.ps1')
trap { Salir-ConError $_ }

$COL_X = @(40, 360, 900, 1500, 2060)
$Y0 = -80; $FILA = 210; $SEP = 60; $GAP_COL = 80
$ANCHO = @{ boundary = 480; control = 500; entity = 360 }
$ESTEREOTIPO = @{ boundary = 'frontera'; control = 'controlador'; entity = 'entidad' }
$PX_LETRA = 6.6

function Rol($de, $a) {
    if ($de -eq 'actor') { return 'USA' }
    if ($a -eq 'entity') { return 'PERSISTE_EN' }
    if ($a -eq 'externo') { return 'INVOCA' }
    if ($de -eq 'boundary' -and $a -eq 'control') { return 'DELEGA_EN' }
    if ($a -eq 'boundary') { return 'RESPONDE_A' }
    return 'USA'
}

# La firma con la que se compara: nombre(param, param), sin espacios de mas.
function Firma($texto) { return (($texto -replace '\s+', ' ') -replace '\(\s*', '(' -replace '\s*\)', ')').Trim() }
function Firma-Metodo($m) {
    $ps = @(); foreach ($p in $m.Parameters) { $ps += $p }
    # Una op con parentesis anidados (aggregate(Sum(amount))) quedo con todo
    # en el nombre y sin parametros.
    if ($m.Name.Contains('(') -and $ps.Count -eq 0) { return Firma $m.Name }
    $ps = @($ps | Sort-Object { $_.Position } | ForEach-Object { $_.Name })
    return Firma ("{0}({1})" -f $m.Name, ($ps -join ', '))
}

# Todas las operaciones de un participante: los mensajes que recibe, las
# suyas y las de ea-sprint3-metodos.ps1, sin repetir la misma firma.
function Ops-Completas($c, $p) {
    $lista = New-Object System.Collections.ArrayList; $vistas = @{}
    $agregar = { param($o) if (-not $o) { return }; $f = Firma $o; if (-not $vistas.ContainsKey($f)) { $vistas[$f] = $true; [void]$lista.Add($o) } }
    foreach ($m in $c.mensajes) {
        if ($m.ret -or $m.a -ne $p.k) { continue }
        # Como el generador de Mateo: un mensaje cuyo NOMBRE ya es una op
        # propia no se agrega aparte.
        $nom = ($m.m -split '\(')[0]
        $ya = $false; foreach ($o in @($p.ops)) { if ($o -and (($o -split '\(')[0]) -eq $nom) { $ya = $true } }
        if (-not $ya) { & $agregar $m.m }
    }
    foreach ($o in @($p.ops)) { & $agregar $o }
    $extra = $null
    if ($METODOS_SPRINT3.ContainsKey($c.cu) -and $METODOS_SPRINT3[$c.cu].Contains($p.k)) { $extra = $METODOS_SPRINT3[$c.cu][$p.k] }
    foreach ($o in @($extra)) { & $agregar $o }
    return ,$lista.ToArray()
}

function Agregar-Metodo($el, $o) {
    $nom = $o; $params = @()
    # La misma regla que Nueva-Clase: con parentesis anidados o una cadena
    # (filter(...).delete()), todo va en el nombre.
    if ($o -match '^([^(]+)\(([^()]*)\)$') { $nom = $Matches[1]; $params = @($Matches[2] -split ',\s*' | Where-Object { $_ }) }
    $m = $el.Methods.AddNew($nom.Trim(), ''); [void]$m.Update()
    $pos = 0
    foreach ($par in $params) { $pp = $m.Parameters.AddNew($par, $par); $pp.Position = $pos; $pos++; [void]$pp.Update() }
}

# ---- el acomodo de un diagrama ------------------------------------------------
function Medida($el) {
    # Alto: el del generador de Mateo. Ancho: el renglon mas largo; EA
    # escribe "+ nombre(tipo, tipo)" y el tipo del parametro es su nombre.
    $n = $el.Attributes.Count + $el.Methods.Count
    $largo = $el.Name.Length + 14
    foreach ($a in $el.Attributes) { $largo = [math]::Max($largo, $a.Name.Length + $a.Type.Length + 6) }
    foreach ($m in $el.Methods) { $largo = [math]::Max($largo, (Firma-Metodo $m).Length + 6) }
    return @{ h = 70 + $n * 15; w = [int]($largo * $PX_LETRA + 24) }
}
function Reacomodar($dia) {
    $objs = @()
    foreach ($do in $dia.DiagramObjects) {
        $el = $ea.GetElementByID($do.ElementID)
        $o = @{ do = $do; l = $do.left; t = $do.top; w = $do.right - $do.left; h = $do.top - $do.bottom; clase = ($el.Type -eq 'Class') }
        if ($o.clase) { $med = Medida $el; $o.h = $med.h; $o.w = [math]::Max($o.w, $med.w) }
        $objs += $o
    }
    # Columnas: las cajas cuya x izquierda difiere en menos de 150 px son de
    # la misma columna (por si alguna se movio a mano); la columna se
    # identifica por la x de su caja mas a la izquierda.
    $ant = $null; $base = $null
    foreach ($o in ($objs | Sort-Object { $_.l })) {
        if ($null -eq $ant -or $o.l - $ant -gt 150) { $base = $o.l }
        $o.col = $base; $o.dx = $o.l - $base; $ant = $o.l
    }
    foreach ($o in $objs) { $o.l = $o.col }
    $cols = @($objs | ForEach-Object { $_.l } | Sort-Object -Unique)
    # Cada columna se corre lo mismo que la anterior y, si aun asi pisa a la
    # anterior (que se ensancho), un poco mas.
    $nuevaX = @{}; $corrido = 0; $finAnterior = $null
    foreach ($cx in $cols) {
        $deCol = @($objs | Where-Object { $_.l -eq $cx })
        $x = $cx + $corrido
        if ($null -ne $finAnterior) { $x = [math]::Max($x, $finAnterior + $GAP_COL) }
        $corrido = $x - $cx
        $nuevaX[$cx] = $x
        $finAnterior = $x + (($deCol | ForEach-Object { $_.dx + $_.w }) | Measure-Object -Maximum).Maximum
    }
    foreach ($cx in $cols) {
        $piso = $null
        foreach ($o in @($objs | Where-Object { $_.l -eq $cx } | Sort-Object { - $_.t })) {
            $t = $o.t
            if ($null -ne $piso) { $t = [math]::Min($t, $piso - $SEP) }
            $l = $nuevaX[$cx] + $o.dx
            $o.do.left = $l; $o.do.right = $l + $o.w; $o.do.top = $t; $o.do.bottom = $t - $o.h
            if (-not $Simular) { [void]$o.do.Update() }
            $piso = $t - $o.h
        }
    }
}

# ---- crear un diagrama nuevo (la logica de ea-diseno-clases-sprint3.ps1) -----
function Crear-Diagrama($pkg, $c, $nomDia) {
    $dia = $pkg.Diagrams.AddNew($nomDia, 'Logical')
    [void]$dia.Update(); $pkg.Diagrams.Refresh()
    $id = @{}; $rolDe = @{}; $piso = @{}
    foreach ($p in ($c.participantes | Sort-Object { $_.col }, { $_.f })) {
        $rolDe[$p.k] = $p.rol
        $x = $COL_X[$p.col]
        $t = [int]($Y0 - $p.f * $FILA)
        if ($piso.ContainsKey($p.col)) { $t = [math]::Min($t, $piso[$p.col] - $SEP) }
        if ($p.rol -eq 'actor' -or $p.rol -eq 'externo') {
            $eid = Get-Actor $p.n ($p.rol -eq 'externo'); $w = 60; $h = 90
        } else {
            $ops = Ops-Completas $c $p
            $eid = Nueva-Clase $pkg $p.n $ESTEREOTIPO[$p.rol] $p.nota $p.atr $ops ($p.rol -eq 'entity')
            $el = $ea.GetElementByID($eid); $el.Alias = $c.cu; [void]$el.Update()
            $w = $ANCHO[$p.rol]
            $h = 70 + (@($p.atr | Where-Object { $_ }).Count + $ops.Count) * 15
        }
        Poner $dia $eid $x $t $w $h
        $piso[$p.col] = $t - $h
        $id[$p.k] = $eid
    }
    $pares = @{}
    foreach ($m in $c.mensajes) {
        if ($m.d -eq $m.a) { continue }
        if ($rolDe[$m.d] -eq 'entity' -and $rolDe[$m.a] -eq 'entity') { continue }
        $k = (@($m.d, $m.a) | Sort-Object) -join '|'
        if ($pares.ContainsKey($k)) { continue }
        $pares[$k] = $true
        $de = $m.d; $a = $m.a
        if ($m.ret) { $de = $m.a; $a = $m.d }
        $con = $ea.GetElementByID($id[$de]).Connectors.AddNew((Rol $rolDe[$de] $rolDe[$a]), 'Association')
        $con.SupplierID = $id[$a]
        $con.Direction  = 'Source -> Destination'
        [void]$con.Update()
        $con.ClientEnd.Cardinality = '1'; [void]$con.ClientEnd.Update()
        $con.SupplierEnd.Cardinality = $(if ($rolDe[$a] -eq 'entity') { '0..*' } else { '1' }); [void]$con.SupplierEnd.Update()
    }
    foreach ($r in @($c.rel)) {
        if (-not $r) { continue }
        $con = $ea.GetElementByID($id[$r.d]).Connectors.AddNew($r.r, 'Association')
        $con.SupplierID = $id[$r.a]
        [void]$con.Update()
        $con.ClientEnd.Cardinality = $r.cd; [void]$con.ClientEnd.Update()
        $con.SupplierEnd.Cardinality = $r.ca; [void]$con.SupplierEnd.Update()
    }
    $dia.DiagramObjects.Refresh()
    return $dia
}

$pkg = Get-PaqueteTipo 'Sprint 3 - Diseño de clase' $false

foreach ($clave in (Claves-Casos $Caso)) {
    $c = $CASOS_SPRINT3[$clave]
    $nomDia = "Diseño de clase - $($c.cu) $($c.nombre)"
    $dia = Get-Diagrama $pkg $nomDia
    if (-not $dia) {
        if ($Simular) { Write-Output "  $nomDia : se crearía"; continue }
        $dia = Crear-Diagrama $pkg $c $nomDia
        Reacomodar $dia
        [void]$dia.Update()
        Write-Output "  $nomDia : creado con todos los métodos"
        continue
    }
    # ---- completar las clases que ya estan ---------------------------------
    $total = 0
    foreach ($p in $c.participantes) {
        if ($p.rol -in 'actor', 'externo') { continue }
        $el = $null
        foreach ($e in $pkg.Elements) { if ($e.Type -eq 'Class' -and $e.Alias -eq $c.cu -and $e.Name -eq $p.n) { $el = $e } }
        if (-not $el) { Write-Output "  $($c.cu): no está la clase $($p.n)"; continue }
        $tiene = @{}; foreach ($m in $el.Methods) { $tiene[(Firma-Metodo $m)] = $true }
        $todas = Ops-Completas $c $p
        $nuevas = @($todas | Where-Object { -not $tiene.ContainsKey((Firma $_)) })
        if ($nuevas.Count -eq 0) { continue }
        Write-Output ("    {0}.{1}: +{2} ({3})" -f $c.cu, $p.n, $nuevas.Count, ($nuevas -join '; '))
        $total += $nuevas.Count
        if ($Simular) { continue }
        foreach ($o in $nuevas) { Agregar-Metodo $el $o }
        $el.Methods.Refresh(); [void]$el.Update()
    }
    if (-not $Simular) { $dia.DiagramObjects.Refresh(); Reacomodar $dia; [void]$dia.Update() }
    Write-Output "  $nomDia : $total métodos agregados"
}

Cerrar-Modelo
Write-Output 'OK'
