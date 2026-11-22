param(
    [string[]]$Caso = @(),
    # Rehace el paquete «Sprint 4 - 2.1.3 Comunicación» entero.
    [switch]$Rehacer,
    [string]$Modelo = '',
    # Usa el EA que ya esta abierto (sin proyecto) en vez de levantar uno.
    [switch]$UsarEAAbierto
)

# =========================================================================
# CAPITULO 4 - Sprint 4 - 2.1.3 Logica de negocio: diagramas de COMUNICACION
#
# El generador del Sprint 3 (ea-comunicacion-sprint3.ps1) sobre los datos de
# ea-sprint4-casos.ps1:
#   - Tipo 'Communication'. Participantes: clases de analisis con estereotipo
#     de robustez (boundary, control, entity), que EA dibuja como circulo. El
#     actor es el del modelo de casos de uso.
#   - UNA linea (Association) por par de participantes.
#   - Cada mensaje es un conector 'Collaboration' sobre esa linea, con su
#     numero <grupo>.<orden> en PDATA4 (EA reinicia la numeracion y cambia de
#     color al cambiar de grupo). El sentido va en el rotulo (-> <- ^ v): un
#     mensaje creado por script sale sin punta de flecha.
#   - Los mensajes salen de Mensajes-Del-Guion: los mismos, con el mismo
#     numero, que la secuencia.
#   - Una nota al pie dice que es cada grupo, lejos de los participantes.
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint4-comun.ps1')
trap { Salir-ConError $_ }

$COL_X = @(40, 420, 900, 1420, 1940)
$Y0 = -140; $FILA = 270
$RENGLON = 16
$CAJA = 110

# -Rehacer solo: el paquete entero. -Rehacer -Caso: solo esos casos.
$pkg = Get-PaqueteTipo $PAQ_COMUNICACION ($Rehacer -and -not $Caso.Count)
$filas = @()   # [diagrama, conector, desplazamiento] para la segunda pasada

foreach ($clave in (Claves-Casos $Caso)) {
    $c = $CASOS_SPRINT4[$clave]
    $errores = @(Revisar-Caso $c)
    if ($errores.Count) { $errores | ForEach-Object { Write-Output "  $($c.cu): $_" }; throw "Los datos de $($c.cu) no cuadran." }
    $nomDia = "2.1.3 Comunicación - $($c.cu) $($c.nombre)"
    if (-not (Preparar-Diagrama $pkg $nomDia)) { continue }

    $dia = $pkg.Diagrams.AddNew($nomDia, 'Communication')
    [void]$dia.Update(); $pkg.Diagrams.Refresh()
    $msgs = Mensajes-Del-Guion $c

    # En zigzag dentro de cada columna (una caja si, otra corrida 170 px):
    # EA traza las lineas de centro a centro, y la que une la primera con
    # la tercera de una columna atravesaba la del medio.
    $corrida = @{}
    foreach ($col in @($c.participantes | ForEach-Object { [int]$_.col } | Sort-Object -Unique)) {
        $i = 0
        foreach ($p in @($c.participantes | Where-Object { [int]$_.col -eq $col } | Sort-Object { [double]$_.f })) {
            $corrida[$p.k] = $(if ($i % 2) { 170 } else { 0 }); $i++
        }
    }
    $id = @{}; $centro = @{}
    foreach ($p in $c.participantes) {
        $x = $COL_X[[int]$p.col] + $corrida[$p.k]; $t = [int]($Y0 - $p.f * $FILA)
        if ($p.rol -eq 'actor' -or $p.rol -eq 'externo') {
            $eid = Get-ActorDe $pkg $p $c.cu; $w = 60; $h = 90
        } else {
            $e = $pkg.Elements.AddNew($p.n, 'Class')
            $e.Stereotype = $p.rol; $e.StereotypeEx = $p.rol
            if ($p.nota) { $e.Notes = $p.nota }
            [void]$e.Update()
            $eid = $e.ElementID; $w = $CAJA; $h = $CAJA
        }
        [void](Poner $dia $eid $x $t $w $h)
        $id[$p.k] = $eid
        $centro[$p.k] = @{ x = $x + $w / 2; y = $t - $h / 2 }
    }

    # ---- una linea por par ------------------------------------------------
    $pares = @{}
    foreach ($m in $msgs) {
        if ($m.o -eq $m.d) { continue }
        $k = (@($m.o, $m.d) | Sort-Object) -join '|'
        if ($pares.ContainsKey($k)) { continue }
        $pares[$k] = $true
        $con = $ea.GetElementByID($id[$m.o]).Connectors.AddNew('', 'Association')
        $con.SupplierID = $id[$m.d]
        if (-not $con.Update()) { throw "EA no guardó la línea $($m.o) - $($m.d) de $($c.cu): $($con.GetLastError())" }
    }

    # ---- los mensajes, sobre su linea -------------------------------------
    $enLinea = @{}; $base = @{}; $bloques = @()
    foreach ($m in $msgs) {
        $flecha = ''
        if ($m.o -ne $m.d) {
            $dx = $centro[$m.d].x - $centro[$m.o].x; $dy = $centro[$m.d].y - $centro[$m.o].y
            $flecha = if ([math]::Abs($dx) -ge [math]::Abs($dy)) { if ($dx -gt 0) { ' →' } else { ' ←' } }
                      else { if ($dy -gt 0) { ' ↑' } else { ' ↓' } }
        }
        $con = $ea.GetElementByID($id[$m.o]).Connectors.AddNew("$($m.m)$flecha", 'Collaboration')
        $con.SupplierID = $id[$m.d]
        $con.Direction  = 'Source -> Destination'
        if ($m.src) { $con.Notes = "$($m.num): $($m.m)  {$($m.src)}" }
        if (-not $con.Update()) { throw "EA no guardó el mensaje «$($m.m)»: $($con.GetLastError())" }
        # PDATA4 (el numero) es de solo lectura por la API; PDATA5 baja el
        # rotulo un renglon por cada mensaje anterior en la misma linea.
        $k = (@($m.o, $m.d) | Sort-Object) -join '|'
        if (-not $enLinea.ContainsKey($k)) {
            $enLinea[$k] = 0
            # Dos lineas que se cruzan tienen el medio en el mismo lugar y sus
            # rotulos quedan encimados: la segunda los corre hasta que no
            # choquen con el bloque de rotulos de otra linea.
            $base[$k] = 0
            if ($m.o -ne $m.d) {
                $mx = ($centro[$m.o].x + $centro[$m.d].x) / 2; $my = ($centro[$m.o].y + $centro[$m.d].y) / 2
                $n = @($msgs | Where-Object { ((@($_.o, $_.d) | Sort-Object) -join '|') -eq $k }).Count
                $alto = ($n + 1) * $RENGLON
                $intentos = 0
                while ($intentos -lt 12) {
                    $choca = $false
                    foreach ($b in $bloques) {
                        if ([math]::Abs($b.x - $mx) -lt 260 -and [math]::Abs(($b.y + $b.dy) - ($my + $base[$k])) -lt ($b.alto + $alto) / 2) { $choca = $true }
                    }
                    if (-not $choca) { break }
                    $base[$k] += $(if ($intentos % 2) { -1 } else { 1 }) * ($intentos + 1) * 2 * $RENGLON
                    $intentos++
                }
                $bloques += @{ x = $mx; y = $my; dy = $base[$k]; alto = $alto }
            }
        }
        $j = $enLinea[$k]; $enLinea[$k]++
        # 0, +1, -1, +2, -2 ... renglones alrededor del medio de la linea
        $sy = [int]($base[$k] + [math]::Ceiling($j / 2) * $RENGLON * $(if ($j % 2) { 1 } else { -1 }))
        $ea.Execute("UPDATE t_connector SET PDATA4 = '$($m.num)' WHERE Connector_ID = $($con.ConnectorID)")
        $filas += , @($dia.DiagramID, $con.ConnectorID, $sy)
    }

    # ---- nota con los grupos, debajo de todo --------------------------------
    $leyenda = ($c.grupos.GetEnumerator() | ForEach-Object { "Grupo $($_.Key): $($_.Value)." }) -join '   '
    $nota = $pkg.Elements.AddNew('', 'Note')
    $nota.Notes = "$($c.cu) · $($c.us). $leyenda`r`n$($c.nota)"
    [void]$nota.Update()
    $maxF = ($c.participantes | ForEach-Object { [double]$_.f } | Measure-Object -Maximum).Maximum
    [void](Poner $dia $nota.ElementID $COL_X[1] ([int]($Y0 - ($maxF + 1) * $FILA - 40)) 1000 90)

    $dia.DiagramObjects.Refresh()
    Write-Output ("  {0} : {1} participantes, {2} líneas, {3} mensajes en {4} grupos" -f $nomDia, ($c.participantes.Count), $pares.Count, $msgs.Count, $c.grupos.Count)
}

Cerrar-Modelo

# =========================================================================
# SEGUNDA PASADA - OLEDB, con EA cerrado: la fila de cada mensaje en
# t_diagramlinks. DiagramLinks.AddNew por la API no la guarda, y sin ella EA
# dibuja todos los rotulos de una misma linea en el medio, uno encima del
# otro. SX/SY corren el rotulo (es lo que EA guarda cuando uno lo arrastra).
# =========================================================================
if ($filas.Count) {
    $cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$Modelo;")
    $cn.Open()
    foreach ($f in $filas) {
        $geo = "SX=0;SY=$($f[2]);EX=0;EY=$($f[2]);EDGE=2;`$LLB=;LLT=;LMT=;LMB=;LRT=;LRB=;IRHS=;ILHS=;"
        $cmd = $cn.CreateCommand()
        $cmd.CommandText = "INSERT INTO t_diagramlinks (DiagramID, ConnectorID, Geometry, Style, Hidden, Path) VALUES ($($f[0]), $($f[1]), '$geo', 'Mode=3;Color=-1;LWidth=0;', False, '')"
        [void]$cmd.ExecuteNonQuery()
    }
    $cn.Close()
    Write-Output "  $($filas.Count) rótulos de mensaje acomodados"
}
Write-Output 'OK'
