param(
    [string[]]$Caso = @(),
    # Rehace el paquete entero: todos los diagramas de estado del Sprint 3.
    [switch]$Rehacer,
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx'),
    # Usa el EA que ya esta abierto (sin proyecto) en vez de levantar uno.
    [switch]$UsarEAAbierto
)

# =========================================================================
# CAPITULO 4 - Sprint 3 - Diagrama de estados (procesos y transacciones)
#
# El mismo generador del Sprint 2 (ea-estado-sprint2.ps1), sobre los datos
# del Sprint 3 (ea-sprint3-dinamica.ps1, clave 'estado' de cada caso).
#
# ---- QUE DIBUJA (docs/diagramas/GUIA-DE-DIAGRAMAS.md, seccion 6) ----
#   NO el ciclo de vida de un objeto: el FLUJO DE UNA TRANSACCION, uno por
#   caso de uso transaccional. Un caso que solo lee y no es de IA, pago ni
#   historia clinica (CU30, los indicadores) no lleva este diagrama.
#
# ---- COMO SE DIBUJA ----
#   - Cinco columnas: autenticacion, menu, operaciones, validacion, cierre.
#   - Todos los rechazos van a un sumidero unico ("Informar error"), y de
#     ahi sale UNA sola flecha de vuelta: con ida y vuelta entre las mismas
#     dos cajas, EA encima los dos rotulos sin dar error.
#   - Puede haber varios estados finales.
#   - Inicial y final son StateNode con Subtype 100 y 101: son los unicos
#     (con el 102) que EA 15 dibuja.
#   Cada estado declara su columna y su fila (se admiten medias filas): no se
#   escriben coordenadas.
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint3-comun.ps1')
. (Join-Path $PSScriptRoot 'ea-sprint3-dinamica.ps1')
trap { Salir-ConError $_ }

$COL_X = @(40, 560, 1180, 1660, 2160)
$Y0 = -80; $FILA = 90
$EST_W = 210; $EST_H = 60; $NODO = 24

$sub = Get-PaqueteTipo 'Sprint 3 - Estado' $Rehacer

foreach ($clave in (Claves-Casos $Caso)) {
    $c = $CASOS_SPRINT3[$clave]
    $dn = $DINAMICA_SPRINT3[$clave]
    if (-not $dn -or -not $dn.estado) { Write-Output "  $($c.cu): no es transaccional, no lleva diagrama de estado"; continue }
    $nomDia = "Estado - $($c.cu) $($c.nombre)"
    if (Get-Diagrama $sub $nomDia) { Write-Output "  $nomDia ya existe, no se toca"; continue }

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
