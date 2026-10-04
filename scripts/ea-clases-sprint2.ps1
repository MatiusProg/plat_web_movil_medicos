param(
    [string[]]$Caso = @(),
    # Rehace el paquete entero. OJO: las lineas de vida de la secuencia se
    # clasifican con estas clases; despues de -Rehacer, rehacer la secuencia.
    [switch]$Rehacer,
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx')
)

# =========================================================================
# CAPITULO 4 - Sprint 2 - 2.1.4.1 Diagrama de analisis de clase
#
# Armado como los 2.3 de VioletBoutique.eapx: las mismas clases del
# diagrama de comunicacion, con estereotipo frontera / controlador / entidad
# (EA las dibuja como tabla) y sus atributos y operaciones.
#   frontera    : las funciones de la pantalla y de la vista que la atiende;
#                 los endpoints como atributo.
#   controlador : las funciones reales, con su firma.
#   entidad     : la tabla, con sus columnas y su tipo de la base.
# El actor va en el diagrama. Las uniones son Association dirigidas, con rol
# en MAYUSCULAS y cardinalidad en los dos extremos, una por cada par que se
# habla en la comunicacion.
#
# Cada clase lleva el codigo del caso de uso en el ALIAS: es como la
# encuentra ea-secuencia-sprint2.ps1 para clasificar las lineas de vida.
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint2-comun.ps1')
trap { Salir-ConError $_ }

$COL_X = @(40, 380, 900, 1460, 1960)
$Y0 = -80; $FILA = 200; $SEP = 50
$ANCHO = @{ boundary = 460; control = 420; entity = 330 }
$ESTEREOTIPO = @{ boundary = 'frontera'; control = 'controlador'; entity = 'entidad' }

function Rol($de, $a) {
    if ($de -eq 'actor') { return 'USA' }
    if ($a -eq 'entity') { return 'PERSISTE_EN' }
    if ($de -eq 'boundary' -and $a -eq 'control') { return 'DELEGA_EN' }
    if ($a -eq 'boundary') { return 'RESPONDE_A' }
    return 'USA'
}
function Cardinalidad($rol) { if ($rol -eq 'entity') { return '0..*' } else { return '1' } }

$pkg = Get-PaqueteTipo 'Sprint 2 - 2.1.4.1 Clases de análisis' $Rehacer

foreach ($clave in (Claves-Casos $Caso)) {
    $c = $CASOS_SPRINT2[$clave]
    $nomDia = "2.1.4.1 Clases de análisis - $($c.cu) $($c.nombre)"
    if (Get-Diagrama $pkg $nomDia) { Write-Output "  $nomDia ya existe, no se toca"; continue }
    $dia = $pkg.Diagrams.AddNew($nomDia, 'Logical')
    [void]$dia.Update(); $pkg.Diagrams.Refresh()

    # ---- las cajas, apiladas por columna sin pisarse ----------------------
    $id = @{}; $rolDe = @{}; $piso = @{}
    foreach ($p in ($c.participantes | Sort-Object { $_.col }, { $_.f })) {
        $rolDe[$p.k] = $p.rol
        $x = $COL_X[$p.col]
        $t = [int]($Y0 - $p.f * $FILA)
        # El alto real crece con el contenido: si la de arriba es alta, esta
        # baja lo necesario para no quedar debajo de ella.
        if ($piso.ContainsKey($p.col)) { $t = [math]::Min($t, $piso[$p.col] - $SEP) }
        if ($p.rol -eq 'actor' -or $p.rol -eq 'externo') {
            $eid = Get-Actor $p.n ($p.rol -eq 'externo'); $w = 60; $h = 90
        } else {
            $eid = Nueva-Clase $pkg $p.n $ESTEREOTIPO[$p.rol] $p.nota $p.atr $p.ops ($p.rol -eq 'entity')
            $el = $ea.GetElementByID($eid); $el.Alias = $c.cu; [void]$el.Update()
            $w = $ANCHO[$p.rol]
            $h = 60 + (@($p.atr | Where-Object { $_ }).Count + @($p.ops | Where-Object { $_ }).Count) * 18
        }
        Poner $dia $eid $x $t $w $h
        $piso[$p.col] = $t - $h
        $id[$p.k] = $eid
    }

    # ---- una asociacion por par que se habla ------------------------------
    $pares = @{}
    foreach ($m in $c.mensajes) {
        if ($m.d -eq $m.a) { continue }
        $k = (@($m.d, $m.a) | Sort-Object) -join '|'
        if ($pares.ContainsKey($k)) { continue }
        $pares[$k] = $true
        $con = $ea.GetElementByID($id[$m.d]).Connectors.AddNew((Rol $rolDe[$m.d] $rolDe[$m.a]), 'Association')
        $con.SupplierID = $id[$m.a]
        $con.Direction  = 'Source -> Destination'
        [void]$con.Update()
        $con.ClientEnd.Cardinality = Cardinalidad $rolDe[$m.d]; [void]$con.ClientEnd.Update()
        $con.SupplierEnd.Cardinality = Cardinalidad $rolDe[$m.a]; [void]$con.SupplierEnd.Update()
    }

    $dia.DiagramObjects.Refresh()
    Write-Output ("  {0} : {1} clases, {2} asociaciones" -f $nomDia, $dia.DiagramObjects.Count, $pares.Count)
}

Cerrar-Modelo
Write-Output 'OK'
