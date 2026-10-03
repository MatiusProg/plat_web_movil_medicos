param(
    [string[]]$Caso = @(),
    # Borra el diagrama de estado del caso de uso y lo vuelve a generar.
    [switch]$Rehacer,
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx')
)

# =========================================================================
# CAPITULO 4 - Sprint 2 - 2.1.4.3 Diagrama de estados (procesos y
# transacciones)
#
# ---- QUE DIBUJA (docs/diagramas/GUIA-DE-DIAGRAMAS.md, seccion 6) ----
#   NO el ciclo de vida de un objeto: el FLUJO DE UNA TRANSACCION, uno por
#   caso de uso transaccional, como el CU1 del ejemplo de catedra. Los
#   estados son actividades (autenticar, seleccionar, capturar, validar,
#   informar) y el sumidero es "Transaccion completada".
#
# ---- COMO SE DIBUJA ----
#   - Cinco columnas: autenticacion, menu, operaciones, validacion, cierre.
#     El hueco entre el menu y las operaciones es ANCHO: por ahi salen las
#     flechas del menu con sus rotulos, que son largos.
#   - Todos los rechazos van a un sumidero unico ("Informar error"), y de
#     ahi sale UNA sola flecha de vuelta al menu: con ida y vuelta entre las
#     mismas dos cajas, EA encima los dos rotulos sin dar error.
#   - Puede haber varios estados finales: el rechazo de autorizacion muere
#     en el suyo, al lado de la autenticacion.
#   - Inicial y final son StateNode con Subtype 100 y 101: son los unicos
#     (con el 102) que EA 15 dibuja.
#
# Cada estado declara su columna y su fila (se admiten medias filas): no se
# escriben coordenadas. Los datos estan en ea-sprint2-casos.ps1, en la clave
# 'estado' de cada caso.
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint2-comun.ps1')
trap { Salir-ConError $_ }

$COL_X = @(40, 560, 1180, 1660, 2160)
$Y0 = -80; $FILA = 90
$EST_W = 210; $EST_H = 60; $NODO = 24

$sub = Get-PaqueteTipo 'Sprint 2 - 2.1.4.3 Estado' $Rehacer


foreach ($clave in (Claves-Casos $Caso)) {
    $c = $CASOS_SPRINT2[$clave]
    if (-not $c.estado) { Write-Output "  $($c.cu): no es transaccional, no lleva diagrama de estado"; continue }
    $nomDia = "2.1.4.3 Estado - $($c.cu) $($c.nombre)"
    if (Get-Diagrama $sub $nomDia) { Write-Output "  $nomDia ya existe, no se toca"; continue }

    $dia = $sub.Diagrams.AddNew($nomDia, 'Statechart')
    [void]$dia.Update(); $sub.Diagrams.Refresh()

    $id = @{}; $centro = @{}
    foreach ($e in $c.estado.estados) {
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
    $maxF  = ($c.estado.estados | ForEach-Object { $_.f } | Measure-Object -Maximum).Maximum
    $yBajo = [int]($Y0 - ($maxF + 1.4) * $FILA)

    foreach ($tr in $c.estado.transiciones) {
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
    Write-Output ("  {0} : {1} estados, {2} transiciones" -f $nomDia, $dia.DiagramObjects.Count, $c.estado.transiciones.Count)
}

Cerrar-Modelo
Write-Output 'OK'
