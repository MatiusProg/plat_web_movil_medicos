param(
    [string[]]$Caso = @(),
    # Rehace el paquete entero: todos los diagramas de comunicacion.
    [switch]$Rehacer,
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx')
)

# =========================================================================
# CAPITULO 4 - Sprint 2 - 2.1.3 Logica de negocio: diagramas de COMUNICACION
#
# Armado como los 2.2 de VioletBoutique.eapx:
#   - Tipo 'Communication'. Los participantes son las clases de analisis,
#     con estereotipo de robustez (boundary, control, entity), que EA dibuja
#     como circulo. El actor es el del modelo de casos de uso.
#   - UNA sola linea (Association) por par de participantes, aunque se
#     manden diez mensajes.
#   - Cada mensaje es un conector 'Collaboration' sobre esa linea. Su numero
#     lo pone EA desde PDATA4 ("<grupo>.<orden>"): al cambiar de grupo
#     reinicia la numeracion y lo dibuja en otro color.
#   - Un mensaje creado por script sale sin punta de flecha (GUIA-DIAGRAMAS-EA
#     7.3), asi que el sentido va en el rotulo: -> <- ^ v, segun hacia donde
#     esta el destino en el dibujo.
#   - Una nota al pie dice que es cada grupo.
#
# Las clases de cada caso de uso son suyas: EA dibuja TODA relacion entre los
# elementos del lienzo, y compartirlas obligaria a ocultar las de los demas.
# Los datos estan en ea-sprint2-casos.ps1.
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint2-comun.ps1')
trap { Salir-ConError $_ }

$COL_X = @(40, 400, 800, 1220, 1640)
$Y0 = -140; $FILA = 190
$RENGLON = 16        # alto de un rotulo de mensaje
$CAJA = 110          # cuadrada: el icono de robustez es un circulo inscrito

$pkg = Get-PaqueteTipo 'Sprint 2 - 2.1.3 Comunicación' $Rehacer

foreach ($clave in (Claves-Casos $Caso)) {
    $c = $CASOS_SPRINT2[$clave]
    $nomDia = "2.1.3 Comunicación - $($c.cu) $($c.nombre)"
    if (Get-Diagrama $pkg $nomDia) { Write-Output "  $nomDia ya existe, no se toca"; continue }

    $dia = $pkg.Diagrams.AddNew($nomDia, 'Communication')
    [void]$dia.Update(); $pkg.Diagrams.Refresh()

    $id = @{}; $centro = @{}
    foreach ($p in $c.participantes) {
        $x = $COL_X[$p.col]; $t = [int]($Y0 - $p.f * $FILA)
        if ($p.rol -eq 'actor' -or $p.rol -eq 'externo') {
            $eid = Get-Actor $p.n ($p.rol -eq 'externo'); $w = 60; $h = 90
        } else {
            $e = $pkg.Elements.AddNew($p.n, 'Class')
            $e.Stereotype = $p.rol; $e.StereotypeEx = $p.rol
            if ($p.nota) { $e.Notes = $p.nota }
            [void]$e.Update()
            $eid = $e.ElementID; $w = $CAJA; $h = $CAJA
        }
        Poner $dia $eid $x $t $w $h
        $id[$p.k] = $eid
        $centro[$p.k] = @{ x = $x + $w / 2; y = $t - $h / 2 }
    }

    # ---- una linea por par ------------------------------------------------
    $pares = @{}
    foreach ($m in $c.mensajes) {
        if ($m.d -eq $m.a) { continue }
        $k = (@($m.d, $m.a) | Sort-Object) -join '|'
        if ($pares.ContainsKey($k)) { continue }
        $pares[$k] = $true
        $con = $ea.GetElementByID($id[$m.d]).Connectors.AddNew('', 'Association')
        $con.SupplierID = $id[$m.a]
        [void]$con.Update()
    }

    # ---- los mensajes, sobre su linea -------------------------------------
    $orden = @{}; $enLinea = @{}
    foreach ($m in $c.mensajes) {
        $g = [int]$m.g
        if (-not $orden.ContainsKey($g)) { $orden[$g] = 0 }
        $orden[$g]++
        $flecha = ''
        if ($m.d -ne $m.a) {
            $dx = $centro[$m.a].x - $centro[$m.d].x; $dy = $centro[$m.a].y - $centro[$m.d].y
            $flecha = if ([math]::Abs($dx) -ge [math]::Abs($dy)) { if ($dx -gt 0) { ' →' } else { ' ←' } }
                      else { if ($dy -gt 0) { ' ↑' } else { ' ↓' } }
        }
        $con = $ea.GetElementByID($id[$m.d]).Connectors.AddNew("$($m.m)$flecha", 'Collaboration')
        $con.SupplierID = $id[$m.a]
        $con.Direction  = 'Source -> Destination'
        [void]$con.Update()
        # PDATA4 es de solo lectura por la API: se escribe por SQL.
        # PDATA5 corre el rotulo (es lo que EA guarda cuando uno lo
        # arrastra): con tres o mas mensajes en la misma linea EA los dibuja
        # encimados, asi que cada uno baja un renglon respecto del anterior.
        $k = (@($m.d, $m.a) | Sort-Object) -join '|'
        if (-not $enLinea.ContainsKey($k)) { $enLinea[$k] = 0 }
        $sy = $enLinea[$k] * $RENGLON; $enLinea[$k]++
        $ea.Execute("UPDATE t_connector SET PDATA4 = '$g.$($orden[$g])', PDATA5 = 'SX=0;SY=$sy;EX=0;EY=$sy;' WHERE Connector_ID = $($con.ConnectorID)")
    }

    # ---- la fila de cada conector en el diagrama ----------------------------
    # Violet tiene una fila en t_diagramlinks por linea y por mensaje; un
    # diagrama recien creado por script no tiene ninguna, y sin ellas EA dibuja
    # los rotulos de una misma linea uno encima del otro.
    $dia.DiagramLinks.Refresh()
    $yaEsta = @{}; foreach ($l in $dia.DiagramLinks) { $yaEsta[[int]$l.ConnectorID] = $true }
    $xml = $ea.SQLQuery("SELECT c.Connector_ID FROM t_connector c WHERE c.Start_Object_ID IN (SELECT o.Object_ID FROM t_diagramobjects o WHERE o.Diagram_ID = $($dia.DiagramID)) AND c.End_Object_ID IN (SELECT o2.Object_ID FROM t_diagramobjects o2 WHERE o2.Diagram_ID = $($dia.DiagramID))")
    $doc = New-Object System.Xml.XmlDocument; $doc.LoadXml($xml)
    foreach ($f in $doc.SelectNodes('//Row')) {
        $cid = [int]$f.Connector_ID
        if ($yaEsta.ContainsKey($cid)) { continue }
        $lnk = $dia.DiagramLinks.AddNew('', ''); $lnk.ConnectorID = $cid; [void]$lnk.Update()
    }

    # ---- nota con los grupos ------------------------------------------------
    $leyenda = ($c.grupos.GetEnumerator() | ForEach-Object { "Grupo $($_.Key): $($_.Value)." }) -join '   '
    $nota = $pkg.Elements.AddNew('', 'Note')
    $nota.Notes = "$($c.cu) · $($c.us). $leyenda`r`n$($c.nota)"
    [void]$nota.Update()
    $maxF = ($c.participantes | ForEach-Object { $_.f } | Measure-Object -Maximum).Maximum
    Poner $dia $nota.ElementID $COL_X[1] ([int]($Y0 - ($maxF + 1) * $FILA)) 1000 80

    $dia.DiagramObjects.Refresh()
    Write-Output ("  {0} : {1} participantes, {2} líneas, {3} mensajes en {4} grupos" -f $nomDia, ($c.participantes.Count), $pares.Count, $c.mensajes.Count, $c.grupos.Count)
}

Cerrar-Modelo
Write-Output 'OK'
