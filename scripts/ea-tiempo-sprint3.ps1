param(
    [string[]]$Caso = @(),
    # Rehace el paquete entero: todos los diagramas de tiempo del Sprint 3.
    [switch]$Rehacer,
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx'),
    # Usa el EA que ya esta abierto (sin proyecto) en vez de levantar uno.
    [switch]$UsarEAAbierto
)

# =========================================================================
# CAPITULO 4 - Sprint 3 - Diagrama de tiempo (procesos en general)
#
# El mismo generador del Sprint 2 (ea-tiempo-sprint2.ps1), sobre los datos
# del Sprint 3 (ea-sprint3-dinamica.ps1, clave 'tiempo' de cada caso).
#
# ---- QUE DIBUJA (docs/diagramas/GUIA-DE-DIAGRAMAS.md, seccion 8) ----
#   Un escenario por caso de uso transaccional: la rama donde el reloj
#   manda. La linea de vida principal es la transaccion (Inactiva ->
#   Autenticando -> Validando -> Escribiendo -> Confirmada), y las demas son
#   los objetos cuyo estado cambia por el tiempo. La regla es relativa y lo
#   dice la nota; las restricciones salen del codigo.
#
# ---- COMO SE ARMA EN EA (GUIA-DIAGRAMAS-EA.md 7.14) ----
#   - La linea de vida es UN tipo: 'TimeLine'.
#   - Partitions = las franjas del eje Y; StateTransitions = los escalones.
#     Ninguna de las dos tiene Update(): se guardan con el del elemento.
#   - AddNew persiste solo y Partitions.Count se relee en 0: correr dos veces
#     sobre el mismo elemento DUPLICA las franjas. Por eso un diagrama que ya
#     existe no se toca y cada diagrama nuevo crea sus propias lineas.
#   - La regla va de 0 a 100 estirada al ancho: 1400 px, rotulos cortos, la
#     ultima marca en 84 como mucho.
#   - La restriccion va SIN llaves: las pone EA.
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint3-comun.ps1')
. (Join-Path $PSScriptRoot 'ea-sprint3-dinamica.ps1')
trap { Salir-ConError $_ }

$X = 40; $ANCHO = 1400; $Y0 = -60; $FRANJA = 34; $CABEZA = 40; $SEPARACION = 50

$sub = Get-PaqueteTipo 'Sprint 3 - Tiempo' $Rehacer

foreach ($clave in (Claves-Casos $Caso)) {
    $c = $CASOS_SPRINT3[$clave]
    $dn = $DINAMICA_SPRINT3[$clave]
    if (-not $dn -or -not $dn.tiempo) { Write-Output "  $($c.cu): no es transaccional, no lleva diagrama de tiempo"; continue }
    $nomDia = "Tiempo - $($c.cu) $($c.nombre)"
    if (Get-Diagrama $sub $nomDia) { Write-Output "  $nomDia ya existe, no se toca"; continue }

    foreach ($l in $dn.tiempo.lineas) {
        foreach ($m in $l.marcas) {
            if ($l.estados -notcontains $m.e) { throw "$($c.cu): la marca '$($m.e)' de '$($l.n)' no es una de sus franjas" }
            if ($m.t -gt 84) { throw "$($c.cu): la marca en $($m.t) de '$($l.n)' se sale del marco (máximo 84)" }
            if ($m.r -and $m.r -match '[{}]') { throw "$($c.cu): la restricción '$($m.r)' va sin llaves" }
        }
    }

    $dia = $sub.Diagrams.AddNew($nomDia, 'Timing')
    [void]$dia.Update(); $sub.Diagrams.Refresh()

    $t = $Y0
    foreach ($l in $dn.tiempo.lineas) {
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
    $nota.Notes = "$($c.cu) · $($c.us). Escenario: $($dn.tiempo.escenario). $($dn.tiempo.nota)"
    [void]$nota.Update()
    $do = $dia.DiagramObjects.AddNew("l=$X;r=$($X + $ANCHO);t=$t;b=$($t - 70);", '')
    $do.ElementID = $nota.ElementID
    [void]$do.Update()

    $dia.DiagramObjects.Refresh()
    Write-Output ("  {0} : {1} líneas de vida" -f $nomDia, $dn.tiempo.lineas.Count)
}

Cerrar-Modelo
Write-Output 'OK'
