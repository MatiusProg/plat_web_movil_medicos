param(
    [string[]]$Caso = @(),
    # Borra el diagrama de tiempo del caso de uso y lo vuelve a generar.
    [switch]$Rehacer,
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx')
)

# =========================================================================
# CAPITULO 4 - Sprint 2 - 2.1.4.4 Diagrama de tiempo (procesos en general)
#
# ---- QUE DIBUJA (docs/diagramas/GUIA-DE-DIAGRAMAS.md, seccion 8) ----
#   Un escenario por caso de uso transaccional: la rama donde el reloj
#   manda. La linea de vida principal es la transaccion (Inactiva ->
#   Autenticando -> Validando -> Escribiendo -> Confirmada), y las demas son
#   los objetos cuyo estado cambia por el tiempo. La regla es relativa y lo
#   dice la nota; las restricciones salen del codigo.
#
# ---- COMO SE ARMA EN EA (GUIA-DIAGRAMAS-EA.md 7.14) ----
#   - La linea de vida es UN tipo: 'TimeLine'. 'StateLifeline' y
#     'ValueLifeline' no existen en la API.
#   - Partitions = las franjas del eje Y; StateTransitions = los escalones.
#     Ninguna de las dos tiene Update(): se guardan con el del elemento.
#   - AddNew persiste solo y Partitions.Count se relee en 0: correr dos veces
#     sobre el mismo elemento DUPLICA las franjas. Por eso el subpaquete del
#     diagrama se rehace entero.
#   - La regla va de 0 a 100 estirada al ancho: 1400 px (~14 px por unidad),
#     rotulos cortos, la ultima marca en 84 como mucho.
#   - La restriccion va SIN llaves: las pone EA.
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint2-comun.ps1')
trap { Salir-ConError $_ }

$X = 40; $ANCHO = 1400; $Y0 = -60; $FRANJA = 34; $CABEZA = 40; $SEPARACION = 50

# Siempre se rehace el paquete entero: las franjas (Partitions) no se pueden
# deduplicar, y correr dos veces sobre la misma linea de vida las duplica.
$sub = Get-PaqueteTipo 'Sprint 2 - 2.1.4.4 Tiempo' $true


foreach ($clave in (Claves-Casos $Caso)) {
    $c = $CASOS_SPRINT2[$clave]
    if (-not $c.tiempo) { Write-Output "  $($c.cu): no es transaccional, no lleva diagrama de tiempo"; continue }
    $nomDia = "2.1.4.4 Tiempo - $($c.cu) $($c.nombre)"
    $dia = $sub.Diagrams.AddNew($nomDia, 'Timing')
    [void]$dia.Update(); $sub.Diagrams.Refresh()

    $t = $Y0
    foreach ($l in $c.tiempo.lineas) {
        $el = $sub.Elements.AddNew($l.n, 'TimeLine')
        [void]$el.Update()
        foreach ($nom in $l.estados) {
            $part = $el.Partitions.AddNew($nom, '')
            $part.Name = $nom
            $part.Size = $FRANJA
        }
        foreach ($m in $l.marcas) {
            $tr = $el.StateTransitions.AddNew($m.e, '')
            $tr.TxState = $m.e
            $tr.TxTime  = $m.t
            if ($m.ev) { $tr.Event = $m.ev }
            if ($m.r)  { $tr.TimeConstraint = $m.r }
        }
        [void]$el.Update()
        # Minimo 170: el nombre va en vertical y, con dos franjas, se cortaba.
        $alto = [math]::Max(170, $CABEZA + $l.estados.Count * $FRANJA + 30)
        $do = $dia.DiagramObjects.AddNew("l=$X;r=$($X + $ANCHO);t=$t;b=$($t - $alto);", '')
        $do.ElementID = $el.ElementID
        [void]$do.Update()
        $t -= $alto + $SEPARACION
    }

    $nota = $sub.Elements.AddNew('', 'Note')
    $nota.Notes = "$($c.cu) · $($c.us). Escenario: $($c.tiempo.escenario). $($c.tiempo.nota)"
    [void]$nota.Update()
    $do = $dia.DiagramObjects.AddNew("l=$X;r=$($X + $ANCHO);t=$t;b=$($t - 70);", '')
    $do.ElementID = $nota.ElementID
    [void]$do.Update()

    $dia.DiagramObjects.Refresh()
    Write-Output ("  {0} : {1} líneas de vida" -f $nomDia, $c.tiempo.lineas.Count)
}

Cerrar-Modelo
Write-Output 'OK'
