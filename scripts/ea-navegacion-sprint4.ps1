param(
    # Diagramas a generar (claves de $NAVEGACION_SPRINT4). Sin esto, todos.
    [string[]]$Caso = @(),
    # Rehace el paquete «Sprint 4 - Navegación» entero. Conviene generar
    # SIEMPRE todos juntos: los elementos se comparten entre diagramas y cada
    # uno oculta los enlaces ajenos que existen al generarse.
    [switch]$Rehacer,
    [string]$Modelo = '',
    # Usa el EA que ya esta abierto (sin proyecto) en vez de levantar uno.
    [switch]$UsarEAAbierto
)

# =========================================================================
# CAPITULO 4 - Sprint 4 - Diagrama de navegacion
#
# El generador del Sprint 3 (ea-navegacion-sprint3.ps1), sin cambios de
# dibujo, sobre los datos de ea-sprint4-navegacion-datos.ps1. Dos niveles,
# con la web y el movil JUNTOS (decision de Karen, 26/10/2026):
#   - SISTEMA: el mapa de todas las pantallas con codigo al cierre del
#     Sprint 4, una columna por subsistema (P1 a P10). Solo pantallas y rutas.
#   - SUBSISTEMA: lo NUEVO del Sprint 4 en P5, P6 y P7, y los subsistemas que
#     estrenan pantallas (P9 y P10), con formularios y controladores.
#   Es la extension UWE: tipo 'Logical', cajas 'Class' con estereotipos
#   navigationClass, formClass, controller y menu. La ruta va como atributo y
#   la guarda en el nombre del enlace. Cada archivo es UN elemento del
#   paquete, compartido por los diagramas; cada diagrama oculta al final los
#   enlaces que no son suyos.
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint4-comun.ps1')
. ([scriptblock]::Create([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'ea-sprint4-navegacion-datos.ps1'), [Text.Encoding]::UTF8)))
trap { Salir-ConError $_ }

$X_ACTOR = 40; $X_MENU = 300; $X_TITULO = 600; $X_VISTA = 860; $X_FORM = 1300; $X_CTRL = 1760
$CAJA_W = 340; $CTRL_W = 440; $MENU_W = 240; $TITULO_W = 200
$Y0 = -80; $SEP_BANDA = 70; $SEP = 40; $SEP_COL = 120

function Alto($n) { return 50 + $n * 16 }

$pkg = Get-PaqueteTipo 'Sprint 4 - Navegación' $Rehacer
$claves = if ($Caso.Count) { $Caso } else { @($NAVEGACION_SPRINT4.Keys) }

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
        $tiene["o|$nombreOp"] = $true
    }
    $e.Attributes.Refresh(); $e.Methods.Refresh()
    return @{ id = $e.ElementID; n = [int]$e.Attributes.Count + [int]$e.Methods.Count }
}

$generados = @()   # @{ dia; mios } para ocultar los enlaces ajenos al final

# El del sistema va AL FINAL: los elementos se comparten y cada subsistema
# les suma atributos; si el sistema se dibujara antes, EA agrandaria sus
# cajas despues, hacia abajo, y se pisarian.
$claves = @($claves | Where-Object { $_ -ne 'Sistema' }) + @($claves | Where-Object { $_ -eq 'Sistema' })

foreach ($clave in $claves) {
    $nv = $NAVEGACION_SPRINT4[$clave]
    if (-not $nv) { throw "No hay datos de navegación para '$clave'" }
    $nomDia = "Navegación - $($nv.titulo)"
    if (Get-Diagrama $pkg $nomDia) { Write-Output "  $nomDia ya existe, no se toca"; continue }

    $dia = $pkg.Diagrams.AddNew($nomDia, 'Logical')
    [void]$dia.Update(); $pkg.Diagrams.Refresh()
    $mios = @{}

    function Poner-Caja($id, $l, $t, $w, $h) {
        $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l + $w);t=$t;b=$($t - $h);", '')
        $do.ElementID = $id
        [void]$do.Update()
    }
    function Caja($nombre, $estereotipo, $ruta, $atr, $ops, $l, $t, $w) {
        $el = Elemento $nombre $estereotipo $ruta $atr $ops
        $h = Alto $el.n
        Poner-Caja $el.id $l $t $w $h
        return @{ id = $el.id; h = $h }
    }
    # Un enlace por par y rotulo: si ya existe (lo creo otro diagrama), se
    # reutiliza. Se anota como propio de este diagrama.
    function Enlace($de, $a, $nombre, $estereotipo) {
        $src = $ea.GetElementByID($de)
        $con = $null
        foreach ($x in $src.Connectors) {
            if ($x.SupplierID -eq $a -and $x.ClientID -eq $de -and $x.Type -eq 'Association' -and [string]$x.Name -eq [string]$nombre) { $con = $x; break }
        }
        if (-not $con) {
            $con = $src.Connectors.AddNew($nombre, 'Association')
            $con.SupplierID = $a
            $con.Direction  = 'Source -> Destination'
            if ($estereotipo) { $con.Stereotype = $estereotipo }
            if (-not $con.Update()) { throw "EA no guardó el enlace «$nombre»: $($con.GetLastError())" }
            $src.Connectors.Refresh()
        }
        $mios[[int]$con.ConnectorID] = $true
    }

    # ---- las franjas ---------------------------------------------------------
    # Cada pantalla es una fila: la pantalla en su columna, sus formularios a
    # la derecha apilados desde su altura, y los controladores en la ultima
    # columna, cada uno donde lo pide la primera pantalla que lo usa (y nunca
    # encima del anterior). Asi ninguna flecha atraviesa una caja.
    # Con disposicion = 'columnas' (el del sistema) cada franja es una
    # COLUMNA con su titulo arriba: en filas salia un diagrama de 11000 px de
    # alto. Ese nivel no lleva formularios ni controladores.
    $enColumnas = ($nv.disposicion -eq 'columnas')
    $t = $Y0; $tCtrl = $Y0; $fondoCols = $Y0; $iCol = 0
    $ctrl = @{}; $vistaId = @{}; $filas = @()
    foreach ($banda in $nv.bandas) {
        $xVista = $X_VISTA; $xTitulo = $X_TITULO
        if ($enColumnas) {
            $xVista = $X_VISTA + $iCol * ($CAJA_W + $SEP_COL); $xTitulo = $xVista; $t = $Y0; $iCol++
        }
        $tBanda = $t; $fondoBanda = $t
        if ($banda.titulo) {
            $tit = $pkg.Elements.AddNew('', 'Note'); $tit.Notes = $banda.titulo; [void]$tit.Update()
            Poner-Caja $tit.ElementID $xTitulo $tBanda $(if ($enColumnas) { $CAJA_W } else { $TITULO_W }) 60
            $fondoBanda = $tBanda - 60
            if ($enColumnas) { $t = $tBanda - 60 - $SEP }
        }
        foreach ($p in $banda.pantallas) {
            $v = Caja $p.n 'navigationClass' $p.ruta $p.atr @() $xVista $t $CAJA_W
            if ($vistaId.ContainsKey($p.n)) { throw "$clave : la pantalla '$($p.n)' está dos veces" }
            $vistaId[$p.n] = $v.id
            $fondo = $t - $v.h; $tf = $t
            $cajasForm = @()
            foreach ($f in @($p.forms)) {
                if (-not $f) { continue }
                $tipo = if ($f.tipo) { $f.tipo } else { 'formClass' }
                $cf = Caja $f.n $tipo $f.ruta $f.atr @() $X_FORM $tf $CAJA_W
                $cajasForm += @{ caja = $cf; ctrl = $f.ctrl }
                # Desde un formulario tambien se navega (el dialogo de pago
                # lleva al Checkout de Stripe).
                if (-not $vistaId.ContainsKey($f.n)) { $vistaId[$f.n] = $cf.id }
                $fondo = [math]::Min($fondo, $tf - $cf.h)
                $tf -= $cf.h + $SEP
            }
            $usados = @(@($p.ctrl) + @(@($p.forms) | ForEach-Object { if ($_) { $_.ctrl } }) | Where-Object { $_ } | Select-Object -Unique)
            foreach ($k in $usados) {
                if ($ctrl.ContainsKey($k)) { continue }
                $def = $nv.controladores[$k]
                if (-not $def) { throw "$clave : falta el controlador '$k'" }
                $tc = [math]::Min($t, $tCtrl)
                $ctrl[$k] = Caja $def.n 'controller' $null @() $def.ops $X_CTRL $tc $CTRL_W
                $tCtrl = $tc - $ctrl[$k].h - $SEP
            }
            $filas += @{ p = $p; v = $v; forms = $cajasForm }
            $t = $fondo - $SEP
        }
        $t = [math]::Min($t, $fondoBanda) - $SEP_BANDA
        $fondoCols = [math]::Min($fondoCols, $t)
    }
    $fondoTotal = [math]::Min([math]::Min($t, $tCtrl), $fondoCols)
    $anchoTotal = if ($enColumnas) { $X_VISTA + $iCol * ($CAJA_W + $SEP_COL) - $SEP_COL - $X_MENU } else { $X_CTRL + $CTRL_W - $X_MENU }

    # ---- actores y menus, centrados en el alto del diagrama -----------------
    $centro = [int](($Y0 + $fondoTotal) / 2)
    $actorId = @{}
    $nAct = @($nv.actores).Count
    $ta = $centro + [int]($nAct * 140 / 2)
    foreach ($a in $nv.actores) {
        $actorId[$a] = Get-Actor $a
        Poner-Caja $actorId[$a] $X_ACTOR $ta 60 90
        $ta -= 140
    }
    $menuId = @{}
    $altoMenus = 0; foreach ($m in $nv.menus) { $altoMenus += 110 }
    $tm = $centro + [int]($altoMenus / 2)
    foreach ($m in $nv.menus) {
        $caja = Caja $m.n 'menu' $m.ruta @() @() $X_MENU $tm $MENU_W
        $menuId[$m.k] = $caja.id
        $tm -= $caja.h + 60
    }

    # ---- los enlaces -----------------------------------------------------------
    foreach ($m in $nv.menus) {
        foreach ($a in @($m.actores)) {
            if (-not $a) { continue }
            Enlace $actorId[$a] $menuId[$m.k] $m.guarda 'navigationLink'
        }
        if ($m.desde) { Enlace $menuId[$m.desde] $menuId[$m.k] ("build $($m.guardaDesde)".Trim()) $null }
    }
    foreach ($fila in $filas) {
        $p = $fila.p
        if ($p.actor) {
            Enlace $actorId[$p.actor] $fila.v.id '[sin sesión]' $null
        } elseif ($p.desde) {
            # desde puede ser una lista: se llega a la misma pantalla desde
            # varias (el Checkout de Stripe, desde la web y desde el movil).
            foreach ($dd in @($p.desde)) {
                $origen = if ($vistaId.ContainsKey($dd)) { $vistaId[$dd] } else { $menuId[$dd] }
                if (-not $origen) { throw "$clave : desde '$dd' no es una pantalla ni un menú de este diagrama" }
                Enlace $origen $fila.v.id ("build $($p.guarda)".Trim()) $null
            }
        } else {
            if (-not $menuId.ContainsKey($p.menu)) { throw "$clave : la pantalla '$($p.n)' no dice de qué menú cuelga" }
            Enlace $menuId[$p.menu] $fila.v.id ("build $($p.guarda)".Trim()) $null
        }
        # ctrl puede ser una lista: una pantalla con botones que llaman a
        # distintos archivos del backend (MisFichas.tsx paga, cancela y
        # confirma la asistencia).
        foreach ($k in @($p.ctrl)) { if ($k) { Enlace $fila.v.id $ctrl[$k].id 'submit' $null } }
        foreach ($f in $fila.forms) {
            Enlace $fila.v.id $f.caja.id 'build' $null
            if ($f.ctrl) { Enlace $f.caja.id $ctrl[$f.ctrl].id 'submit' $null }
        }
    }

    $nota = $pkg.Elements.AddNew('', 'Note')
    $nota.Notes = $nv.nota
    [void]$nota.Update()
    Poner-Caja $nota.ElementID $X_MENU ($fondoTotal - 20) $anchoTotal 110

    $dia.DiagramObjects.Refresh()
    $generados += @{ dia = $dia; mios = $mios }
    Write-Output ("  {0} : {1} elementos, {2} enlaces propios" -f $nomDia, $dia.DiagramObjects.Count, $mios.Count)
}

# ---- cada diagrama oculta los enlaces que no son suyos ----------------------
foreach ($g in $generados) {
    $d = $g.dia
    $ids = @{}; $d.DiagramObjects.Refresh()
    foreach ($o in $d.DiagramObjects) { $ids[[int]$o.ElementID] = $true }
    $lista = ($ids.Keys | ForEach-Object { $_ }) -join ','
    $xml = $ea.SQLQuery("SELECT Connector_ID AS id FROM t_connector WHERE Start_Object_ID IN ($lista) AND End_Object_ID IN ($lista)")
    $doc = New-Object System.Xml.XmlDocument; $doc.LoadXml($xml)
    $filasLink = @{}; $d.DiagramLinks.Refresh()
    foreach ($lnk in $d.DiagramLinks) { $filasLink[[int]$lnk.ConnectorID] = $lnk }
    $ocultos = 0
    foreach ($r in $doc.SelectNodes('//Row')) {
        $cid = [int]$r.id
        if ($g.mios.ContainsKey($cid)) { continue }
        $lnk = $filasLink[$cid]
        if (-not $lnk) { $lnk = $d.DiagramLinks.AddNew('', ''); $lnk.ConnectorID = $cid }
        $lnk.IsHidden = $true
        [void]$lnk.Update()
        $ocultos++
    }
    Write-Output ("  {0} : {1} enlaces ajenos ocultos" -f $d.Name, $ocultos)
}

Cerrar-Modelo
Write-Output 'OK'
