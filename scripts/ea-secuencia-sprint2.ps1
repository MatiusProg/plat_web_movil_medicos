param(
    [string[]]$Caso = @(),
    # Rehace el paquete entero: todos los diagramas de secuencia.
    [switch]$Rehacer,
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx')
)

# =========================================================================
# CAPITULO 4 - Sprint 2 - 2.1.4.2 Diagrama de secuencia
#
# Armado como los 3.2 del Ciclo 3 de VioletBoutique.eapx:
#   - Lineas de vida: actor, pantallas, gestores, entidades y, al final, el
#     sistema externo como actor (Servicio de IA). Son elementos 'Sequence'
#     sin nombre, clasificados por la clase de 2.1.4.1 (ClassifierID): EA
#     las rotula ": Clase". Sin color ni estereotipo propios.
#   - Notas "FLUJO n" en una columna a la izquierda, fuera de toda caja.
#   - Pantalla -> gestor es el endpoint ("GET /api/...()"); gestor -> entidad
#     es el SQL; las respuestas van punteadas (Return).
#   - 'alt' solo donde hay una rama real, con las ramas numeradas con letra
#     (1.7a / 1.7b), y 'loop' para cada repeticion. Se pueden anidar.
#   - Lineas de vida, fragmentos y notas viven en el MISMO paquete que el
#     diagrama.
#
# ---- POR QUE HAY UNA SIMULACION ----
#   EA NO respeta la altura guardada de los mensajes: los apila por SeqNo de
#   35 en 35 desde -135, y solo los baja cuando caerian sobre la cabecera de
#   una caja (~27) o sobre la guarda de un operando (~22). Las cajas y las
#   notas, en cambio, quedan donde se guardan. Este script simula esa regla
#   (la de ea-fragmentos-3-2.ps1 de Violet, medida el 29/09/2026) y pone las
#   cajas y las notas alrededor de lo que EA va a dibujar.
#
# ---- DOS PASADAS ----
#   1. COM: lineas de vida, notas, fragmentos y mensajes.
#   2. OLEDB, con EA cerrado: la geometria y el tipo de cada mensaje, el
#      operador y los operandos de cada fragmento (al reves: EA los lee de
#      abajo hacia arriba) y el ORDEN Z, que viene sin definir (999999) y
#      con el que EA no dibuja los fragmentos en su interfaz.
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint2-comun.ps1')
trap { Salir-ConError $_ }

$Y_PRIMERO = -135; $PASO = 35; $CABECERA = 27; $ETIQUETA = 22; $AUTO = 15
$X0 = 230; $GAP = 50; $TOP_LV = -50
$NOTA_L = 5; $NOTA_R = 150; $NOTA_ALTO = 50

$pkg = Get-PaqueteTipo 'Sprint 2 - 2.1.4.2 Secuencia' $Rehacer
$pkgClases = Get-PaqueteTipo 'Sprint 2 - 2.1.4.1 Clases de análisis' $false
$pendientes = @()

foreach ($clave in (Claves-Casos $Caso)) {
    $c = $CASOS_SPRINT2[$clave]
    if (-not $c.secuencia) { Write-Output "  $($c.cu): sin guion de secuencia"; continue }
    $nomDia = "2.1.4.2 Secuencia - $($c.cu) $($c.nombre)"
    if (Get-Diagrama $pkg $nomDia) { Write-Output "  $nomDia ya existe, no se toca"; continue }

    # Las clases de este caso de uso: ea-clases-sprint2.ps1 les pone el
    # codigo del caso en el alias.
    $clase = @{}
    foreach ($e in $pkgClases.Elements) {
        if ($e.Type -eq 'Class' -and $e.Alias -eq $c.cu) { $clase[$e.Name] = $e.ElementID }
    }

    # ---- lineas de vida: en el orden de rol y, dentro, de aparicion -------
    $ordenRol = @{ actor = 0; boundary = 1; control = 2; entity = 3; externo = 4 }
    $primera = @{}; $i = 0
    foreach ($p in $c.secuencia) {
        if ($p.t -ne 'msg') { continue }
        foreach ($kk in @($p.o, $p.d)) { if (-not $primera.ContainsKey($kk)) { $primera[$kk] = $i } }
        $i++
    }
    $lineas = @($c.participantes | Where-Object { $primera.ContainsKey($_.k) } |
                Sort-Object { $ordenRol[$_.rol] }, { $primera[$_.k] })
    $lv = @{}; $cx = @{}; $x = $X0
    foreach ($p in $lineas) {
        $w = [int][math]::Max(120, ($p.n.Length + 3) * 8)
        if ($p.rol -eq 'actor' -or $p.rol -eq 'externo') {
            $eid = Get-Actor $p.n ($p.rol -eq 'externo')
        } else {
            if (-not $clase.ContainsKey($p.n)) { throw "Falta la clase '$($p.n)' de $($c.cu). Corré antes ea-clases-sprint2.ps1." }
            $el = $pkg.Elements.AddNew('', 'Sequence')
            $el.Name = ''
            $el.ClassifierID = $clase[$p.n]
            [void]$el.Update()
            $eid = $el.ElementID
        }
        $lv[$p.k] = @{ id = $eid; l = $x; w = $w }
        $cx[$p.k] = [int]($x + $w / 2)
        $x += $w + $GAP
    }
    $derecha = $x - $GAP

    # ---- simulacion de la maqueta de EA -------------------------------------
    $msgs = @(); $notas = @(); $frames = @()
    $piso = $Y_PRIMERO + $PASO; $fondo = $piso; $limite = 0
    $pila = New-Object System.Collections.ArrayList
    $topAbierto = $null; $notaPend = $null; $ultimoBot = $null; $ultimoBotK = -1; $k = 0
    foreach ($item in $c.secuencia) {   # NO "$paso": PowerShell no distingue mayusculas
        switch ($item.t) {
            'nota' { $notaPend = $item.txt }
            'msg' {
                $yy = $piso - $PASO
                if ($limite -lt 0 -and $yy -gt $limite) { $yy = $limite }
                $auto = ($item.o -eq $item.d)
                $msgs += @{ o = $item.o; d = $item.d; n = $item.n; ret = [bool]$item.ret; y = $yy; auto = $auto }
                $piso = $yy; $fondo = $yy - $(if ($auto) { $AUTO } else { 0 })
                if ($notaPend) { $notas += @{ txt = $notaPend; y = $yy }; $notaPend = $null }
                foreach ($f in $pila) {
                    $f.lv[$item.o] = $true; $f.lv[$item.d] = $true
                    if ($auto) { $f.txt = [math]::Max($f.txt, $item.n.Length) }
                }
                $limite = 0; $topAbierto = $null; $k++
            }
            { $_ -in 'alt', 'loop' } {
                if ($null -ne $topAbierto) { $top = $topAbierto - 6 }
                elseif ($limite -lt 0) { $top = $limite - 4 }
                else { $top = $fondo - 8 }
                $topAbierto = $top
                # NO se baja un renglon mas para que la guarda no quede tachada
                # por el primer mensaje: EA no respeta ese hueco y todas las
                # cajas de abajo quedan corridas un mensaje (03/10/2026).
                $limite = $top - $CABECERA
                $tipo = if ($item.t -eq 'alt') { 0 } else { 4 }
                $ops = New-Object System.Collections.ArrayList
                if ($tipo -eq 4) { [void]$ops.Add($item.g) }
                [void]$pila.Add(@{ tipo = $tipo; top = $top; hondo = $pila.Count; cortes = @(); ops = $ops; lv = @{}; desde = $k; txt = 0 })
            }
            'op' {
                $f = $pila[$pila.Count - 1]
                if ($f.ops.Count -gt 0) {
                    $corte = $fondo - 10
                    $f.cortes += $corte
                    $limite = $corte - $ETIQUETA
                }
                [void]$f.ops.Add($item.g)
            }
            'fin' {
                $f = $pila[$pila.Count - 1]; $pila.RemoveAt($pila.Count - 1)
                $bot = $fondo - 12
                if ($null -ne $ultimoBot -and $ultimoBotK -eq $k) { $bot = [math]::Min($bot, $ultimoBot - 6) }
                $ultimoBot = $bot; $ultimoBotK = $k
                $f.bot = $bot
                $fondo = $bot; $piso = [math]::Min($piso, $bot + 20)
                $frames += $f
            }
        }
    }
    foreach ($f in $frames) {
        if ($f.tipo -eq 0) {
            $f.l = $X0 - 60 + 8 * $f.hondo; $f.r = $derecha + 40 - 8 * $f.hondo
        } else {
            $izq = [int]::MaxValue; $der = 0
            foreach ($key in $f.lv.Keys) { $izq = [math]::Min($izq, $lv[$key].l); $der = [math]::Max($der, $lv[$key].l + $lv[$key].w) }
            $f.l = $izq - 15; $f.r = $der + 15
            # Un loop que encierra un mensaje a si mismo mide lo que la linea
            # de vida, y su guarda y el rotulo del lazo se salian de la caja:
            # se ensancha hasta cubrirlos (unos 6 px por caracter).
            $minimo = [math]::Max($f.ops[0].Length * 6 + 60, $f.txt * 6 + 80)
            if ($f.r - $f.l -lt $minimo) { $f.r = $f.l + $minimo }
        }
        $limites = @($f.top) + $f.cortes + @($f.bot)
        $partes = ''
        for ($j = $f.ops.Count - 1; $j -ge 0; $j--) {   # AL REVES: EA lee de abajo hacia arriba
            $gid = '{' + [guid]::NewGuid().ToString().ToUpper() + '}'
            $partes += "@PAR;Name=$($f.ops[$j]);Size=$($limites[$j] - $limites[$j + 1]);GUID=$gid;@ENDPAR;"
        }
        $f.partes = $partes
    }
    $minMsg = (($msgs | ForEach-Object { $_.y }) | Measure-Object -Minimum).Minimum
    $minFr  = if ($frames.Count) { (($frames | ForEach-Object { $_.bot }) | Measure-Object -Minimum).Minimum } else { 0 }
    $bajo = [math]::Min($minMsg - 60, $minFr - 30)

    # ---- el diagrama ----------------------------------------------------------
    $dia = $pkg.Diagrams.AddNew($nomDia, 'Sequence')
    [void]$dia.Update(); $pkg.Diagrams.Refresh()
    $orden = @()   # [id, z] para la segunda pasada
    $z = 1
    foreach ($n in $notas) {
        $nota = $pkg.Elements.AddNew('', 'Note'); $nota.Notes = $n.txt; [void]$nota.Update()
        Poner $dia $nota.ElementID $NOTA_L ($n.y + 12) ($NOTA_R - $NOTA_L) $NOTA_ALTO
        $orden += , @($nota.ElementID, $z); $z++
    }
    foreach ($p in $lineas) {
        $v = $lv[$p.k]
        Poner $dia $v.id $v.l $TOP_LV $v.w ($TOP_LV - $bajo)
        $orden += , @($v.id, $z); $z++
    }
    $frags = @()
    foreach ($f in $frames) {
        $fr = $pkg.Elements.AddNew('', 'InteractionFragment'); [void]$fr.Update()
        Poner $dia $fr.ElementID $f.l $f.top ($f.r - $f.l) ($f.top - $f.bot)
        $frags += @{ g = $fr.ElementGUID; tipo = $f.tipo; partes = $f.partes }
        $orden += , @($fr.ElementID, $z); $z++
    }

    $geo = @(); $seq = 1
    foreach ($m in $msgs) {
        $con = $ea.GetElementByID($lv[$m.o].id).Connectors.AddNew($m.n, 'Sequence')
        $con.SupplierID = $lv[$m.d].id
        $con.Direction  = 'Source -> Destination'
        $con.DiagramID  = $dia.DiagramID
        $con.SequenceNo = $seq
        [void]$con.Update()
        $sx = $cx[$m.o]; $ex = $cx[$m.d]; $ye = $m.y
        if ($m.auto) { $ex = $sx + 5; $ye = $m.y - $AUTO }   # el lazo: si PtEnd = PtStart no se dibuja
        $geo += @{ g = $con.ConnectorGUID; seq = $seq; sx = $sx; ex = $ex; y = $m.y; ye = $ye; ret = $m.ret }
        $seq++
    }

    $pendientes += @{ dia = $nomDia; diaId = $dia.DiagramID; geo = $geo; frags = $frags; orden = $orden }
    Write-Output ("  {0} : {1} líneas de vida, {2} mensajes, {3} fragmentos, {4} notas" -f $nomDia, $lineas.Count, $msgs.Count, $frames.Count, $notas.Count)
}

Cerrar-Modelo
if ($pendientes.Count -eq 0) { Write-Output 'OK'; exit 0 }

# =========================================================================
# PARTE 2 - OLEDB, con EA cerrado
# =========================================================================
$cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$Modelo;")
$cn.Open()
function Exec($sql, $param) {
    $cmd = $cn.CreateCommand(); $cmd.CommandText = $sql
    if ($null -ne $param) { [void]$cmd.Parameters.AddWithValue('p', $param) }
    return $cmd.ExecuteNonQuery()
}
foreach ($pend in $pendientes) {
    foreach ($x in $pend.geo) {
        $tipo  = if ($x.ret) { 'Return' } else { 'Call' }
        $flags = if ($x.seq -eq 1) { 'Activation=0;Initiate=1;ForceActivation=0;ExtendActivationUp=0;' } else { 'Activation=0;' }
        [void](Exec "UPDATE t_connector SET SeqNo = $($x.seq), PtStartX = $($x.sx), PtStartY = $($x.y), PtEndX = $($x.ex), PtEndY = $($x.ye), PDATA1 = 'Synchronous', PDATA2 = 'retval=void;', PDATA3 = '$tipo', StateFlags = '$flags' WHERE ea_guid = '$($x.g)'")
    }
    foreach ($f in $pend.frags) {
        # NType 0 = alt, 4 = loop. PDATA1 = 6, igual que en el archivo de catedra.
        [void](Exec "UPDATE t_object SET NType = $($f.tipo), PDATA1 = '6' WHERE ea_guid = '$($f.g)'")
        $gx = '{' + [guid]::NewGuid().ToString().ToUpper() + '}'
        # Las guardas van por parametro: concatenadas, los acentos llegan rotos.
        [void](Exec "INSERT INTO t_xref (XrefID, Name, Type, Visibility, Client, Description) VALUES ('$gx', 'Partitions', 'element property', 'Public', '$($f.g)', ?)" $f.partes)
    }
    # El orden Z, como en Violet: notas, lineas de vida y fragmentos, en ese
    # orden. Sin definir (999999), EA no dibuja los fragmentos en su interfaz.
    foreach ($o in $pend.orden) {
        [void](Exec "UPDATE t_diagramobjects SET [Sequence] = $($o[1]) WHERE Diagram_ID = $($pend.diaId) AND Object_ID = $($o[0])")
    }
    Write-Output "  $($pend.dia) : geometría, retornos, fragmentos y orden Z escritos"
}
$cn.Close()
Write-Output 'OK'
