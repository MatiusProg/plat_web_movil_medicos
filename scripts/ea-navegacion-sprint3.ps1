param(
    # Diagramas a generar (claves de $NAVEGACION_SPRINT3). Sin esto, todos.
    [string[]]$Caso = @(),
    # Rehace el paquete entero. Conviene generar SIEMPRE todos juntos: los
    # elementos se comparten y cada diagrama oculta los enlaces ajenos que
    # existen al momento de generarse.
    [switch]$Rehacer,
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx'),
    # Usa el EA que ya esta abierto (sin proyecto) en vez de levantar uno.
    [switch]$UsarEAAbierto
)

# =========================================================================
# CAPITULO 4 - Sprint 3 - Diagrama de navegacion
#
# ---- QUE DIBUJA ----
#   Desde el Sprint 3 la navegacion ya NO va por caso de uso (decision de
#   Karen, 26/10/2026). Hay dos niveles, con la web y el movil JUNTOS:
#     - SISTEMA: el mapa de todas las pantallas que tienen codigo, en franjas
#       por subsistema (P1 a P8), desde cada actor por su menu. Solo
#       pantallas y rutas: a ese tamano los formularios y los controladores
#       no entran, y estan en el nivel de abajo.
#     - SUBSISTEMA (P5, P6, P7 y P8, los del Sprint 3): las pantallas con sus
#       formularios y los controladores del backend con sus funciones. Se ve
#       que la web y el movil llegan al MISMO controlador.
#   No es UML: es la extension UWE, un diagrama de clases con estereotipos de
#   navegacion. Por eso el tipo es 'Logical' y las cajas 'Class'.
#
# ---- REGLAS (las del Sprint 2, GUIA-DE-DIAGRAMAS.md seccion 7) ----
#   - Estereotipos navigationClass, formClass, controller y menu. 'view' y
#     'form' son reservados de EA: cambian la forma y DEJAN DE DIBUJAR los
#     atributos.
#   - La ruta va como ATRIBUTO ("ruta : /mis-fichas"), no en el nombre.
#   - La guarda va en el NOMBRE del enlace, entre corchetes. El estereotipo
#     navigationLink se reserva para el enlace del actor al menu.
#   - Cadena, sin flechas de vuelta.
#   - Las pantallas publicas cuelgan del actor abstracto Usuario, no de un
#     menu: no pasan por la guarda de sesion.
#   - Un archivo es UN elemento, compartido por todos los diagramas; se le
#     suman los atributos y operaciones que falten.
#
# ---- POR QUE SE OCULTAN ENLACES ----
#   EA dibuja TODA relacion que exista entre dos elementos del lienzo
#   (GUIA-DIAGRAMAS-EA.md, regla 3). Como los elementos se comparten, el
#   build que un subsistema dibuja entre dos pantallas apareceria tambien en
#   el del sistema con otra guarda. Al final, cada diagrama oculta los
#   enlaces que no son suyos; a los que EA todavia no materializo se les crea
#   la fila oculta.
#
# Los datos estan en ea-sprint3-navegacion-datos.ps1.
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint3-comun.ps1')
. (Join-Path $PSScriptRoot 'ea-sprint3-navegacion-datos.ps1')
trap { Salir-ConError $_ }

$X_ACTOR = 40; $X_MENU = 300; $X_TITULO = 600; $X_VISTA = 860; $X_FORM = 1300; $X_CTRL = 1760
$CAJA_W = 340; $CTRL_W = 440; $MENU_W = 240; $TITULO_W = 200
$Y0 = -80; $SEP_BANDA = 70; $SEP = 40; $SEP_COL = 120

function Alto($n) { return 50 + $n * 16 }

$pkg = Get-PaqueteTipo 'Sprint 3 - Navegación' $Rehacer
$claves = if ($Caso.Count) { $Caso } else { @($NAVEGACION_SPRINT3.Keys) }

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
    $nv = $NAVEGACION_SPRINT3[$clave]
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
        $actorId[$a] = Get-Actor $a $false
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
