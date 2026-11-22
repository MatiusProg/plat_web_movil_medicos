param(
    [string[]]$Caso = @(),
    # Solo: rehace el paquete entero. Con -Caso: solo esos casos.
    [switch]$Rehacer,
    [string]$Modelo = '',
    # Usa el EA que ya esta abierto (sin proyecto) en vez de levantar uno.
    [switch]$UsarEAAbierto
)

# =========================================================================
# CAPITULO 4 - Sprint 4 - Diagrama de tiempo (procesos en general)
#
# El generador del Sprint 3 (ea-tiempo-sprint3.ps1), sin cambios de dibujo,
# sobre los datos del Sprint 4 (ea-sprint4-dinamica.ps1, clave 'tiempo').
# Un escenario por caso de uso: la rama donde el reloj manda. La regla es
# relativa (0 a 100) y la nota dice de donde sale cada restriccion.
#
# EA (GUIA-DIAGRAMAS-EA 7.14): la linea de vida es 'TimeLine'; Partitions y
# StateTransitions se guardan con el Update() del elemento; correr dos veces
# sobre el mismo elemento DUPLICA las franjas, por eso un diagrama que ya
# existe no se toca (salvo -Rehacer -Caso, que lo borra con sus lineas).
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint4-comun.ps1')
. ([scriptblock]::Create([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'ea-sprint4-dinamica.ps1'), [Text.Encoding]::UTF8)))
trap { Salir-ConError $_ }

$X = 40; $ANCHO = 1400; $Y0 = -60; $FRANJA = 34; $CABEZA = 40; $SEPARACION = 50

# -Rehacer solo: el paquete entero. -Rehacer -Caso: solo esos casos.
$sub = Get-PaqueteTipo 'Sprint 4 - Tiempo' ($Rehacer -and -not $Caso.Count)

foreach ($clave in (Claves-Casos $Caso)) {
    $c = $CASOS_SPRINT4[$clave]
    $dn = $DINAMICA_SPRINT4[$clave]
    if (-not $dn -or -not $dn.tiempo) { Write-Output "  $($c.cu): no es transaccional, no lleva diagrama de tiempo"; continue }
    $nomDia = "Tiempo - $($c.cu) $($c.nombre)"
    if (-not (Preparar-Diagrama $sub $nomDia)) { continue }

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
