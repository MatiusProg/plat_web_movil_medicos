param(
    [string[]]$Caso = @(),
    # Rehace el paquete «Sprint 4 - Secuencia» entero.
    [switch]$Rehacer,
    [string]$Modelo = '',
    # Usa el EA que ya esta abierto (sin proyecto) en vez de levantar uno.
    [switch]$UsarEAAbierto
)

# =========================================================================
# CAPITULO 4 - Sprint 4 - Diagrama de secuencia
#
# El generador del Sprint 3 (ea-secuencia-sprint3.ps1) sobre el guion unico
# de ea-sprint4-casos.ps1. Lo que cambia:
#   - No hay guion aparte: la secuencia dibuja el mismo guion del que salen
#     la comunicacion y el diseno de clase, con la misma numeracion
#     (Mensajes-Del-Guion). El rastreo no se puede desarmar.
#   - Los fragmentos del guion ya son solo los caracteristicos: se dibujan
#     todos, sin simplificar.
#   - La nota «FLUJO n <nombre>» la pone el script en el primer mensaje de
#     cada grupo, a la izquierda y bien lejos de las cajas (trampa del
#     Sprint 3: una nota que toca una caja queda atada a ella).
#   - El rotulo es corto (Acortar-Rotulo, Acortar-Guarda) y el texto entero
#     con su anclaje archivo:linea va a las notas del mensaje.
#   - Las lineas de vida se clasifican con las clases de «Sprint 4 - Diseño
#     de clase» (alias = codigo del caso): va DESPUES de
#     ea-diseno-clases-sprint4.ps1.
#
# Dos pasadas, como en el Sprint 3: COM (lineas de vida, notas, fragmentos y
# mensajes) y OLEDB con EA cerrado (geometria, tipo de mensaje, operandos de
# los fragmentos y orden Z).
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint4-comun.ps1')
trap { Salir-ConError $_ }

$Y_PRIMERO = -135; $PASO = 35; $AUTO = 15
$X0 = 340; $GAP = 70; $TOP_LV = -50
$NOTA_L = 5; $NOTA_R = 175; $NOTA_ALTO = 50
$MAX_ROTULO = 250
$MAX_CORTO = 46     # largo del rotulo dibujado, sin contar el numero

# ---- EL ROTULO CORTO (01/11/26) ----
#   El guion trae cada mensaje con su anclaje entre llaves (archivo, linea y
#   SQL) y la firma completa. Dibujado asi, cada flecha era un parrafo y no
#   se leia la secuencia. El diagrama muestra solo el numero, el nombre y los
#   argumentos que entran en $MAX_CORTO caracteres, como en la guia
#   (VioletBoutique, 7.8 f). El texto entero va a las NOTAS del mensaje: sigue
#   en el modelo para la defensa, solo que no en la imagen.
#   Revisar-Guion compara el texto entero, asi que el rastreo con la
#   comunicacion y el diseno de clase no cambia.
$ROL_SEQ = @{
    boundary = @{ st = 'interfaz';    color = 0xF5E6D6 }   # celeste
    control  = @{ st = 'controlador'; color = 0xDCF2DC }   # verde
    entity   = @{ st = 'entidad';     color = 0xCCF2FF }   # amarillo
}
function Acortar-Rotulo([string]$texto) {
    $base = ($texto -split '  \{')[0].Trim()
    if ($base -notmatch '^(\S+:)\s*(.*)$') { return $base }
    $num = $Matches[1]; $resto = $Matches[2]
    if ($resto.Length -le $MAX_CORTO) { return "$num $resto" }
    $a = $resto.IndexOf('('); $b = $resto.LastIndexOf(')')
    if ($a -lt 0 -or $b -lt $a) {
        return "$num " + $resto.Substring(0, $MAX_CORTO - 1).TrimEnd() + '…'
    }
    $cabeza = $resto.Substring(0, $a + 1); $cola = $resto.Substring($b)
    $dentro = $resto.Substring($a + 1, $b - $a - 1)
    # Argumentos (o alternativas a | b) enteros mientras entren.
    $sep = if ($dentro.Contains(', ')) { ', ' } elseif ($dentro.Contains(' | ')) { ' | ' } else { $null }
    if ($sep) {
        $partes = $dentro -split [regex]::Escape($sep)
        $toma = @()
        foreach ($p in $partes) {
            $prueba = $cabeza + (($toma + $p) -join $sep) + $sep + '…' + $cola
            if ($prueba.Length -gt $MAX_CORTO -and $toma.Count -gt 0) { break }
            $toma += $p
        }
        if ($toma.Count -lt $partes.Count) { $dentro = ($toma -join $sep) + $sep + '…' } else { $dentro = $toma -join $sep }
        $corto = $cabeza + $dentro + $cola
        if ($corto.Length -le $MAX_CORTO + 6) { return "$num $corto" }
    }
    # Una frase (el texto de un error): palabras enteras mientras entren.
    $lugar = $MAX_CORTO - $cabeza.Length - $cola.Length - 1
    $palabras = $dentro -split ' '; $toma = ''
    foreach ($p in $palabras) {
        $prueba = if ($toma) { "$toma $p" } else { $p }
        if ($prueba.Length -gt $lugar -and $toma) { break }
        $toma = $prueba
    }
    if ($toma.Length -gt $lugar) { $toma = $toma.Substring(0, [math]::Max(4, $lugar)) }
    return "$num $cabeza$toma…$cola"
}
# La guarda de un operando, con la misma idea: sin las referencias al codigo
# «(push.py:125-126, ...)», cortada en el primer «:» o «;» si sigue larga, y
# despues por palabras. La guarda entera queda en el guion de
# ea-sprint4-casos.ps1.
$MAX_GUARDA = 48
function Acortar-Guarda([string]$g) {
    $g = [regex]::Replace($g, '\s*\([^()]*\.(py|dart|ts|tsx)[^()]*\)', '').Trim()
    if ($g.Length -le $MAX_GUARDA) { return $g }
    foreach ($sep in ':', ';', ' (') {
        $i = $g.IndexOf($sep)
        if ($i -ge 12) { $g = $g.Substring(0, $i).Trim() }
        if ($g.Length -le $MAX_GUARDA) { return $g }
    }
    # Clausulas enteras separadas por coma mientras entren.
    $partes = $g -split ', '
    if ($partes.Count -gt 1 -and $partes[0].Length -le $MAX_GUARDA - 3) {
        $toma = @()
        foreach ($p in $partes) { if ((($toma + $p) -join ', ').Length -gt $MAX_GUARDA - 3) { break }; $toma += $p }
        if ($toma.Count -ge 2 -and ($toma -join ', ').Length -ge 30) { return ($toma -join ', ') + ', …' }
    }
    # Por palabras, sin dejar colgando un conector.
    $palabras = New-Object System.Collections.ArrayList
    foreach ($p in ($g -split ' ')) {
        if ((($palabras + $p) -join ' ').Length -gt $MAX_GUARDA - 1) { break }
        [void]$palabras.Add($p)
    }
    $sueltas = 'o','y','u','e','con','de','del','en','que','la','el','los','las','sin','por','a','al'
    while ($palabras.Count -gt 1 -and $sueltas -contains $palabras[$palabras.Count - 1]) { $palabras.RemoveAt($palabras.Count - 1) }
    return ($palabras -join ' ').TrimEnd(',') + '…'
}

# El guion del caso, con el formato que espera el dibujo: cada mensaje con
# su numero y su anclaje entre llaves, y una nota FLUJO en el primer mensaje
# de cada grupo.
function Guion-Secuencia($c) {
    $salida = New-Object System.Collections.ArrayList
    $orden = @{}; $visto = @{}
    foreach ($it in $c.guion) {
        switch ($it.t) {
            'msg' {
                $g = [int]$it.g
                if (-not $orden.ContainsKey($g)) { $orden[$g] = 0 }
                $orden[$g]++
                if (-not $visto.ContainsKey($g)) {
                    $visto[$g] = $true
                    [void]$salida.Add(@{ t = 'nota'; txt = "FLUJO $g " + (($c.grupos.GetEnumerator() | Where-Object { $_.Key -eq $g }).Value) })
                }
                $n = "$g.$($orden[$g]): " + (Rotulo-Mensaje $it)
                if ($it.src) { $n += "  {$($it.src)}" }
                [void]$salida.Add(@{ t = 'msg'; o = $it.o; d = $it.d; n = $n; ret = [bool]$it.ret })
            }
            default { [void]$salida.Add($it) }
        }
    }
    return ,$salida.ToArray()
}

# -Rehacer solo: el paquete entero. -Rehacer -Caso: solo esos casos.
$pkg = Get-PaqueteTipo $PAQ_SECUENCIA ($Rehacer -and -not $Caso.Count)
$pkgClases = Get-PaqueteTipo $PAQ_CLASES $false
$pendientes = @()

foreach ($clave in (Claves-Casos $Caso)) {
    $c = $CASOS_SPRINT4[$clave]
    $errores = @(Revisar-Caso $c)
    if ($errores.Count) { $errores | ForEach-Object { Write-Output "  $($c.cu): $_" }; throw "Los datos de $($c.cu) no cuadran." }
    $guion = Guion-Secuencia $c
    $nomDia = "Secuencia - $($c.cu) $($c.nombre) ($($c.plataforma))"
    if (-not (Preparar-Diagrama $pkg $nomDia)) { continue }

    $clase = @{}
    foreach ($e in $pkgClases.Elements) {
        if ($e.Type -eq 'Class' -and $e.Alias -eq $c.cu) { $clase[$e.Name] = $e.ElementID }
    }

    # ---- lineas de vida: en el orden de rol y, dentro, de aparicion -------
    $ordenRol = @{ actor = 0; boundary = 1; control = 2; entity = 3; externo = 4 }
    $primera = @{}; $i = 0
    foreach ($p in $guion) {
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
            $eid = Get-ActorDe $pkg $p $c.cu
        } else {
            if (-not $clase.ContainsKey($p.n)) { throw "Falta la clase '$($p.n)' de $($c.cu). Corré antes ea-diseno-clases-sprint4.ps1." }
            $el = $pkg.Elements.AddNew('', 'Sequence')
            $el.Name = ''
            $el.ClassifierID = $clase[$p.n]
            # La linea de vida no muestra el estereotipo de su clase: se le da
            # el suyo, en castellano (en ingles EA dibuja los iconos de
            # robustez), y el color de su rol (guia 7.8 d-bis).
            $r = $ROL_SEQ[$p.rol]
            if ($r) { $el.Stereotype = $r.st; $el.StereotypeEx = $r.st }
            [void]$el.Update()
            if ($r) { $el.SetAppearance(1, 0, $r.color); [void]$el.Update() }
            $eid = $el.ElementID
        }
        $lv[$p.k] = @{ id = $eid; l = $x; w = $w }
        $cx[$p.k] = [int]($x + $w / 2)
        $x += $w + $GAP
    }
    $derecha = $x - $GAP

    # ---- la maqueta que EA impone ------------------------------------------
    # Medido el 26/10/2026 abriendo y guardando un diagrama con EA.App: EA
    # guarda TODOS los mensajes de 35 en 35 desde -135, por SeqNo, sin bajar
    # ninguno por la cabecera de una caja ni por la guarda de un operando
    # (la regla de Violet del 29/09 ya no vale aca). Las cajas y las notas
    # quedan donde se guardan. Entonces: el mensaje k va en -135 - 35 k, y lo
    # que hay ENTRE dos mensajes (cabeceras, cortes de operando, cierres) se
    # reparte parejo dentro de ese hueco de 35 px, en el orden del guion.
    $msgs = @(); $notas = @(); $frames = @()
    $hueco = @{}            # k -> fichas que caen antes del mensaje k
    $pila = New-Object System.Collections.ArrayList
    $notaPend = $null; $k = 0
    foreach ($item in $guion) {   # NO "$paso": PowerShell no distingue mayusculas
        if (-not $hueco.ContainsKey($k)) { $hueco[$k] = New-Object System.Collections.ArrayList }
        switch ($item.t) {
            'nota' { $notaPend = $item.txt }
            'msg' {
                $yy = $Y_PRIMERO - $PASO * $k
                $auto = ($item.o -eq $item.d)
                $corto = Acortar-Rotulo $item.n
                $msgs += @{ o = $item.o; d = $item.d; n = $item.n; corto = $corto; ret = [bool]$item.ret; y = $yy; auto = $auto }
                if ($notaPend) { $notas += @{ txt = $notaPend; y = $yy }; $notaPend = $null }
                foreach ($f in $pila) {
                    $f.lv[$item.o] = $true; $f.lv[$item.d] = $true
                    if ($auto) { $f.txt = [math]::Max($f.txt, $corto.Length) }
                }
                $k++
            }
            { $_ -in 'alt', 'loop' } {
                $tipo = if ($item.t -eq 'alt') { 0 } else { 4 }
                $ops = New-Object System.Collections.ArrayList
                if ($tipo -eq 4) { [void]$ops.Add((Acortar-Guarda $item.g)) }
                $f = @{ tipo = $tipo; hondo = $pila.Count; cortes = New-Object System.Collections.ArrayList; ops = $ops; lv = @{}; txt = 0 }
                [void]$pila.Add($f)
                [void]$hueco[$k].Add(@{ f = $f; que = 'top' })
            }
            'op' {
                $f = $pila[$pila.Count - 1]
                if ($f.ops.Count -gt 0) {
                    $ficha = @{ f = $f; que = 'corte'; i = $f.cortes.Count }
                    [void]$f.cortes.Add(0)
                    [void]$hueco[$k].Add($ficha)
                }
                [void]$f.ops.Add((Acortar-Guarda $item.g))
            }
            'fin' {
                $f = $pila[$pila.Count - 1]; $pila.RemoveAt($pila.Count - 1)
                [void]$hueco[$k].Add(@{ f = $f; que = 'bot' })
                $frames += $f
            }
        }
    }
    $ultimoY = $Y_PRIMERO - $PASO * ($k - 1)
    foreach ($kk in $hueco.Keys) {
        $lista = $hueco[$kk]; $n = $lista.Count
        if ($n -eq 0) { continue }
        # Arriba: el mensaje anterior (o el borde superior si es el primero).
        # Abajo: el mensaje kk; despues del ultimo, 12 px por cierre.
        $arriba = if ($kk -eq 0) { $Y_PRIMERO + 30 } else { $Y_PRIMERO - $PASO * ($kk - 1) }
        $paso2  = if ($kk -ge $k) { 12 } else { $PASO / ($n + 1) }
        if ($kk -ge $k) { $arriba = $ultimoY - 4 }
        for ($j = 0; $j -lt $n; $j++) {
            $y = [int]($arriba - $paso2 * ($j + 1))
            $ficha = $lista[$j]
            switch ($ficha.que) {
                'top'   { $ficha.f.top = $y }
                'corte' { $ficha.f.cortes[$ficha.i] = $y }
                'bot'   { $ficha.f.bot = $y }
            }
        }
    }
    foreach ($f in $frames) {
        # El alt de afuera va a todo lo ancho; el que esta dentro de otra caja
        # y los loop, solo sobre sus lineas de vida, y cada nivel 8 px mas
        # adentro para que no cruce el borde de la caja que lo contiene.
        if ($f.tipo -eq 0 -and $f.hondo -eq 0) {
            $f.l = $X0 - 60; $f.r = $derecha + 40
        } else {
            $izq = [int]::MaxValue; $der = 0
            foreach ($key in $f.lv.Keys) { $izq = [math]::Min($izq, $lv[$key].l); $der = [math]::Max($der, $lv[$key].l + $lv[$key].w) }
            $f.l = $izq - 40 + 8 * $f.hondo; $f.r = $der + 40 - 8 * $f.hondo
            $guarda = ($f.ops | ForEach-Object { $_.Length } | Measure-Object -Maximum).Maximum
            $minimo = [math]::Max($guarda * 6 + 60, $f.txt * 6 + 80)
            if ($f.r - $f.l -lt $minimo) { $f.r = $f.l + $minimo }
        }
        $limites = @($f.top) + @($f.cortes) + @($f.bot)
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
    # Dos flujos que empiezan en mensajes seguidos dejaban las notas una
    # encima de la otra: cada nota arranca, como mucho, debajo de la anterior.
    $pisoNota = $null
    foreach ($n in $notas) {
        $nota = $pkg.Elements.AddNew('', 'Note'); $nota.Notes = $n.txt; [void]$nota.Update()
        $tn = $n.y + 12
        if ($null -ne $pisoNota) { $tn = [math]::Min($tn, $pisoNota - 6) }
        Poner $dia $nota.ElementID $NOTA_L $tn ($NOTA_R - $NOTA_L) $NOTA_ALTO
        $pisoNota = $tn - $NOTA_ALTO
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
    $ley = $pkg.Elements.AddNew('', 'Note')
    $ley.Notes = "Celeste: «interfaz» (pantalla)  ·  Verde: «controlador»  ·  Amarillo: «entidad» (tabla).`r`nPunteado: retorno. El archivo, la línea y el SQL de cada mensaje están en sus notas, en el modelo."
    [void]$ley.Update()
    Poner $dia $ley.ElementID $X0 ($bajo - 20) 640 45
    $orden += , @($ley.ElementID, $z); $z++

    $geo = @(); $seq = 1
    foreach ($m in $msgs) {
        # El rotulo corto en el dibujo y el texto entero en las notas. (Ademas
        # t_connector.Name admite 255 caracteres: con mas, Update() devuelve
        # False SIN error y el mensaje no se guarda, 26/10/2026.)
        $rotulo = $m.corto
        $notaMsg = if ($m.n -ne $rotulo) { $m.n } else { '' }
        if ($rotulo.Length -gt $MAX_ROTULO) { throw "Rótulo de más de $MAX_ROTULO caracteres: $rotulo" }
        $con = $ea.GetElementByID($lv[$m.o].id).Connectors.AddNew($rotulo, 'Sequence')
        $con.SupplierID = $lv[$m.d].id
        $con.Direction  = 'Source -> Destination'
        $con.DiagramID  = $dia.DiagramID
        $con.SequenceNo = $seq
        if ($notaMsg) { $con.Notes = $notaMsg }
        if (-not $con.Update()) { throw "EA no guardó el mensaje «$rotulo»: $($con.GetLastError())" }
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
    # El orden Z: notas, lineas de vida y fragmentos. Sin definir (999999),
    # EA no dibuja los fragmentos en su interfaz.
    foreach ($o in $pend.orden) {
        [void](Exec "UPDATE t_diagramobjects SET [Sequence] = $($o[1]) WHERE Diagram_ID = $($pend.diaId) AND Object_ID = $($o[0])")
    }
    Write-Output "  $($pend.dia) : geometría, retornos, fragmentos y orden Z escritos"
}
$cn.Close()
Write-Output 'OK'
