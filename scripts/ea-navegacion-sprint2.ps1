param(
    # Casos de uso a generar (claves de $NAVEGACION_SPRINT2). Sin esto, todos.
    [string[]]$Caso = @(),
    [switch]$Rehacer,
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx')
)

# =========================================================================
# CAPITULO 4 - Sprint 2 - 2.1.4.5 Diagrama de navegacion
#
# ---- QUE DIBUJA (docs/diagramas/GUIA-DE-DIAGRAMAS.md, seccion 7) ----
#   UNO POR CASO DE USO, como la comunicacion, las clases y la secuencia:
#   solo las pantallas por las que pasa ese caso, desde el actor. NO es UML:
#   es la extension UWE, un diagrama de clases con estereotipos de
#   navegacion. Por eso el tipo de diagrama es 'Logical' y las cajas 'Class'.
#
# ---- REGLAS QUE SE CUMPLEN ACA ----
#   - Estereotipos navigationClass, formClass, controller y menu. 'view' y
#     'form' son reservados de EA: cambian la forma y DEJAN DE DIBUJAR los
#     atributos.
#   - La ruta va como ATRIBUTO ("ruta : /perfil"), no en el nombre.
#   - La guarda va en el NOMBRE del enlace, entre corchetes. El estereotipo
#     navigationLink se reserva para el enlace del actor al menu.
#   - Cadena, sin flechas de vuelta: con ida y vuelta entre las mismas dos
#     cajas, EA encima los rotulos ("sbuild:").
#   - Una pantalla a la que se llega desde otra lleva desde=<esa pantalla>,
#     y su build sale de ella, no del menu. Un elemento de forms con
#     tipo='navigationClass' es una pantalla que cuelga de otra sin ser
#     formulario (el historial, que se abre desde la agenda).
#   - Las pantallas publicas cuelgan del ACTOR, no del menu: no pasan por
#     RutaProtegida.
#   - Un archivo es UN elemento: Panel.tsx o accounts/views/profile.py
#     aparecen en varios casos de uso y se reutilizan por nombre, sumandoles
#     los atributos y operaciones que falten. En un mismo lienzo, un
#     controlador que atienden dos areas se dibuja una vez.
#   - El alto de cada caja se calcula del contenido: EA la agranda hacia
#     abajo sin avisar y se comeria la banda siguiente.
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint2-comun.ps1')
trap { Salir-ConError $_ }

$X_ACTOR = 40; $X_MENU = 300; $X_VISTA = 700; $X_FORM = 1150; $X_CTRL = 1650
$CAJA_W = 320; $CTRL_W = 380; $MENU_W = 220
$Y0 = -80; $SEP_BANDA = 80; $SEP_INTERNA = 50

function Alto($n) { return 50 + $n * 16 }

$pkg = Get-PaqueteTipo 'Sprint 2 - 2.1.4.5 Navegación' $Rehacer

$claves = if ($Caso.Count) { $Caso } else { @($NAVEGACION_SPRINT2.Keys) }

# El elemento del archivo: el que ya esta en el paquete con ese nombre y ese
# estereotipo, o uno nuevo. Devuelve su id y cuantas filas tiene.
function Elemento($nombre, $estereotipo, $ruta, $atr, $ops) {
    $e = $null
    foreach ($x in $pkg.Elements) { if ($x.Name -eq $nombre -and $x.Stereotype -eq $estereotipo) { $e = $x; break } }
    if (-not $e) {
        $e = $pkg.Elements.AddNew($nombre, 'Class')
        $e.Stereotype = $estereotipo; $e.StereotypeEx = $estereotipo
        [void]$e.Update(); $pkg.Elements.Refresh()
    }
    $tiene = @{}; foreach ($a in $e.Attributes) { $tiene["a|$($a.Name)"] = $true }
    foreach ($m in $e.Methods) { $tiene["o|$($m.Name)"] = $true }
    if ($ruta -and -not $tiene['a|ruta']) { $a = $e.Attributes.AddNew('ruta', $ruta); [void]$a.Update() }
    foreach ($x in @($atr)) { if ($x -and -not $tiene["a|$x"]) { $a = $e.Attributes.AddNew($x, ''); [void]$a.Update() } }
    foreach ($o in @($ops)) {
        if (-not $o) { continue }
        $nombreOp = $o; $params = @()
        if ($o -match '^([^(]+)\(([^()]*)\)$') { $nombreOp = $Matches[1]; $params = @($Matches[2] -split ',\s*' | Where-Object { $_ }) }
        if ($tiene["o|$nombreOp"]) { continue }
        $m = $e.Methods.AddNew($nombreOp, ''); [void]$m.Update()
        $pos = 0
        foreach ($par in $params) { $p = $m.Parameters.AddNew($par, $par); $p.Position = $pos; $pos++; [void]$p.Update() }
    }
    $e.Attributes.Refresh(); $e.Methods.Refresh()
    return @{ id = $e.ElementID; n = [int]$e.Attributes.Count + [int]$e.Methods.Count }
}

foreach ($clave in $claves) {
    $nv = $NAVEGACION_SPRINT2[$clave]
    $c = $CASOS_SPRINT2[$clave]
    $nomDia = "2.1.4.5 Navegación - $($c.cu) $($c.nombre)"
    if (Get-Diagrama $pkg $nomDia) { Write-Output "  $nomDia ya existe, no se toca"; continue }

    $dia = $pkg.Diagrams.AddNew($nomDia, 'Logical')
    [void]$dia.Update(); $pkg.Diagrams.Refresh()

    function Caja($nombre, $estereotipo, $ruta, $atr, $ops, $l, $t, $w) {
        $el = Elemento $nombre $estereotipo $ruta $atr $ops
        $h = Alto $el.n
        $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l + $w);t=$t;b=$($t - $h);", '')
        $do.ElementID = $el.id
        [void]$do.Update()
        return @{ id = $el.id; h = $h }
    }
    function Enlace($de, $a, $nombre, $estereotipo) {
        $src = $ea.GetElementByID($de)
        $con = $src.Connectors.AddNew($nombre, 'Association')
        $con.SupplierID = $a
        $con.Direction  = 'Source -> Destination'
        if ($estereotipo) { $con.Stereotype = $estereotipo }
        [void]$con.Update()
    }

    # ---- las bandas ----------------------------------------------------------
    # Tres columnas: la pantalla arriba a la izquierda, sus formularios
    # apilados en la columna del medio empezando debajo de ella, y el
    # controlador arriba a la derecha. Asi pantalla -submit-> controlador va
    # por encima de los formularios y los build salen en abanico hacia abajo:
    # ninguna flecha atraviesa una caja.
    $t = $Y0
    $bandas = @(); $ctrl = @{}
    foreach ($ar in $nv.areas) {
        $tBanda = $t; $fondo = $t
        $b = @{ guarda = $ar.guarda; vistaCtrl = $ar.vistaCtrl; desde = $ar.desde; forms = @() }
        $tf = $t
        if ($ar.vista) {
            $b.vistaNombre = $ar.vista.n
            $b.vista = Caja $ar.vista.n 'navigationClass' $ar.vista.ruta $ar.vista.atr @() $X_VISTA $t $CAJA_W
            $tf = $t - $b.vista.h - $SEP_INTERNA
            $fondo = $t - $b.vista.h
        }
        foreach ($f in @($ar.forms)) {
            if (-not $f) { continue }
            $tipo = if ($f.tipo) { $f.tipo } else { 'formClass' }
            $caja = Caja $f.n $tipo $f.ruta $f.atr @() $X_FORM $tf $CAJA_W
            $b.forms += @{ caja = $caja; ctrl = $f.ctrl }
            $fondo = [math]::Min($fondo, $tf - $caja.h)
            $tf -= $caja.h + $SEP_INTERNA
        }
        # Uno que ya se dibujo en otra banda no se repite.
        $tc = $tBanda
        $usados = @(@($ar.vistaCtrl) + @($ar.forms | ForEach-Object { $_.ctrl }) | Where-Object { $_ } | Select-Object -Unique)
        foreach ($k in $usados) {
            if ($ctrl.ContainsKey($k)) { continue }
            $def = $nv.controladores[$k]
            $ctrl[$k] = Caja $def.n 'controller' $null @() $def.ops $X_CTRL $tc $CTRL_W
            $fondo = [math]::Min($fondo, $tc - $ctrl[$k].h)
            $tc -= $ctrl[$k].h + $SEP_INTERNA
        }
        $t = $fondo - $SEP_BANDA
        $bandas += $b
    }
    # ---- actor, menu y pantallas publicas ---------------------------------
    $yMedio = [int](($Y0 + $t) / 2)
    $actor = Get-Actor $nv.actor $false
    $do = $dia.DiagramObjects.AddNew("l=$X_ACTOR;r=$($X_ACTOR + 60);t=$($yMedio + 45);b=$($yMedio - 45);", '')
    $do.ElementID = $actor; [void]$do.Update()
    $menu = Caja $nv.menu.n 'menu' $nv.menu.ruta @() @() $X_MENU ($yMedio + 30) $MENU_W
    Enlace $actor $menu.id '[sesión]' 'navigationLink'

    # Las publicas, en una fila sobre el actor: no pasan por RutaProtegida.
    $xp = $X_ACTOR
    foreach ($p in @($nv.publicas)) {
        if (-not $p) { continue }
        $pub = Caja $p.n 'navigationClass' $p.ruta @() @() $xp ($Y0 + 200) 220
        Enlace $actor $pub.id '[sin sesión]' $null
        $xp += 240
    }

    # ---- la cadena -----------------------------------------------------------
    # Una pantalla a la que se llega desde otra (desde = el nombre de esa
    # pantalla) no cuelga del menu: la flecha sale de la otra pantalla.
    $vistaDe = @{}; foreach ($b in $bandas) { if ($b.vista) { $vistaDe[$b.vistaNombre] = $b.vista.id } }
    foreach ($b in $bandas) {
        $origen = $menu.id; $rotulo = "build $($b.guarda)"
        if ($b.desde) {
            $origen = $vistaDe[$b.desde]
            if (-not $origen) { throw "desde: no hay una pantalla '$($b.desde)' en $clave" }
        }
        if ($b.vista) {
            Enlace $origen $b.vista.id $rotulo $null
            if ($b.vistaCtrl) { Enlace $b.vista.id $ctrl[$b.vistaCtrl].id 'submit' $null }
            $origen = $b.vista.id; $rotulo = 'build'
        }
        foreach ($f in $b.forms) {
            Enlace $origen $f.caja.id $rotulo $null
            if ($f.ctrl) { Enlace $f.caja.id $ctrl[$f.ctrl].id 'submit' $null }
        }
    }

    $nota = $pkg.Elements.AddNew('', 'Note')
    $nota.Notes = $nv.nota
    [void]$nota.Update()
    $do = $dia.DiagramObjects.AddNew("l=$X_MENU;r=$($X_CTRL + $CTRL_W);t=$($t - 20);b=$($t - 100);", '')
    $do.ElementID = $nota.ElementID; [void]$do.Update()

    $dia.DiagramObjects.Refresh()
    Write-Output ("  {0} : {1} elementos, {2} áreas" -f $nomDia, $dia.DiagramObjects.Count, $nv.areas.Count)
}

Cerrar-Modelo
Write-Output 'OK'
