param(
    [string[]]$Caso = @(),
    # Solo: rehace el paquete entero. Con -Caso: solo esos casos.
    [switch]$Rehacer,
    [string]$Modelo = '',
    # Usa el EA que ya esta abierto (sin proyecto) en vez de levantar uno.
    [switch]$UsarEAAbierto
)

# =========================================================================
# CAPITULO 4 - Sprint 4 - Diagrama de estados (procesos y transacciones)
#
# El generador del Sprint 3 (ea-estado-sprint3.ps1), sin cambios de dibujo,
# sobre los datos del Sprint 4 (ea-sprint4-dinamica.ps1, clave 'estado').
#
#   Como en el Sprint 3, NO es el ciclo de vida de un objeto: es el FLUJO DE
#   UNA TRANSACCION, uno por caso de uso. Los estados reales de las tablas
#   (draft/approved/discarded, waiting/offered/booked/expired,
#   candidate/active/rejected...) aparecen en los estados y en las guardas.
#   - Cinco columnas: autenticacion, menu, operaciones, validacion, cierre.
#   - Todos los rechazos van al sumidero «Informar error», con UNA sola
#     flecha de vuelta (ortogonal, por debajo de todo).
#   - Inicial y final son StateNode con Subtype 100 y 101.
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint4-comun.ps1')
. ([scriptblock]::Create([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'ea-sprint4-dinamica.ps1'), [Text.Encoding]::UTF8)))
trap { Salir-ConError $_ }

$COL_X = @(40, 560, 1180, 1660, 2160)
$Y0 = -80; $FILA = 90
$EST_W = 210; $EST_H = 60; $NODO = 24

# -Rehacer solo: el paquete entero. -Rehacer -Caso: solo esos casos.
$sub = Get-PaqueteTipo 'Sprint 4 - Estado' ($Rehacer -and -not $Caso.Count)

foreach ($clave in (Claves-Casos $Caso)) {
    $c = $CASOS_SPRINT4[$clave]
    $dn = $DINAMICA_SPRINT4[$clave]
    if (-not $dn -or -not $dn.estado) { Write-Output "  $($c.cu): no es transaccional, no lleva diagrama de estado"; continue }
    $nomDia = "Estado - $($c.cu) $($c.nombre)"
    if (-not (Preparar-Diagrama $sub $nomDia)) { continue }

    $dia = $sub.Diagrams.AddNew($nomDia, 'Statechart')
    [void]$dia.Update(); $sub.Diagrams.Refresh()

    $id = @{}; $centro = @{}
    foreach ($e in $dn.estado.estados) {
        $x = $COL_X[$e.col]; $t = [int]($Y0 - $e.f * $FILA)
        if ($e.tipo) {
            $el = $sub.Elements.AddNew('', 'StateNode')
            $el.Subtype = $(if ($e.tipo -eq 'inicial') { 100 } else { 101 })
            [void]$el.Update()
            # Centrado sobre la columna de los estados.
            $xl = $x + [int](($EST_W - $NODO) / 2); $tt = $t - [int](($EST_H - $NODO) / 2)
            $pos = "l=$xl;r=$($xl + $NODO);t=$tt;b=$($tt - $NODO);"
        } else {
            $el = $sub.Elements.AddNew($e.n, 'State')
            [void]$el.Update()
            $pos = "l=$x;r=$($x + $EST_W);t=$t;b=$($t - $EST_H);"
        }
        $do = $dia.DiagramObjects.AddNew($pos, '')
        $do.ElementID = $el.ElementID
        [void]$do.Update()
        $id[$e.k] = $el.ElementID
        $centro[$e.k] = $x + [int]($EST_W / 2)
    }
    $maxF  = ($dn.estado.estados | ForEach-Object { $_.f } | Measure-Object -Maximum).Maximum
    $yBajo = [int]($Y0 - ($maxF + 1.4) * $FILA)

    foreach ($tr in $dn.estado.transiciones) {
        if (-not $id.ContainsKey($tr.de) -or -not $id.ContainsKey($tr.a)) { throw "$($c.cu): transición $($tr.de) -> $($tr.a) con un estado que no existe" }
        $src = $ea.GetElementByID($id[$tr.de])
        $con = $src.Connectors.AddNew($(if ($tr.r) { $tr.r } else { '' }), 'StateFlow')
        $con.SupplierID = $id[$tr.a]
        [void]$con.Update()
        if ($tr.ortogonal) {
            # El rodeo se dibuja con quiebres explicitos: baja desde el
            # sumidero, corre por DEBAJO de todo el diagrama y sube hasta el
            # destino. Con la linea ortogonal automatica, EA tomaba el camino
            # corto y cruzaba por encima de las operaciones.
            $lnk = $dia.DiagramLinks.AddNew('', '')
            $lnk.ConnectorID = $con.ConnectorID
            $lnk.Path = "$($centro[$tr.de]):${yBajo};$($centro[$tr.a]):${yBajo};"
            [void]$lnk.Update()
        }
    }

    $dia.DiagramObjects.Refresh()
    Write-Output ("  {0} : {1} estados, {2} transiciones" -f $nomDia, $dia.DiagramObjects.Count, $dn.estado.transiciones.Count)
}

Cerrar-Modelo
Write-Output 'OK'
