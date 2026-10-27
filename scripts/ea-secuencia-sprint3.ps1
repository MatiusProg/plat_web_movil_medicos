param(
    [string[]]$Caso = @(),
    # Rehace el paquete entero: todos los diagramas de secuencia del Sprint 3.
    [switch]$Rehacer,
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx'),
    # Usa el EA que ya esta abierto (sin proyecto) en vez de levantar uno.
    [switch]$UsarEAAbierto,
    # Dibuja el guion entero, con un alt por cada if (ver «los fragmentos
    # que se dibujan»).
    [switch]$Completo
)

# =========================================================================
# CAPITULO 4 - Sprint 3 - Diagrama de secuencia
#
# El mismo generador del Sprint 2 (ea-secuencia-sprint2.ps1), sobre los datos
# del Sprint 3:
#   - Participantes, grupos y mensajes: los de Mateo en ea-sprint3-casos.ps1,
#     los mismos de la comunicacion y del diseno de clase.
#   - El guion (orden vertical, alt, loop, retornos y notas FLUJO n): en
#     ea-sprint3-dinamica.ps1, clave 'secuencia' de cada caso.
#   - Las lineas de vida se clasifican con las clases de «Diseño de clase»,
#     que ea-diseno-clases-sprint3.ps1 crea con el codigo del caso en el
#     alias. Por eso va DESPUES de ese generador.
#
# ---- EL RASTREO CON EL DISENO DE CLASE (guia, seccion 3.4) ----
#   Cada mensaje de Mateo aparece UNA vez en el guion, con su numero
#   "<grupo>.<orden>" (el mismo que EA pone en la comunicacion desde PDATA4)
#   y su texto. No hay llamadas nuevas: cada mensaje recibido es una
#   operacion del diseno de clase, y una llamada que no estuviera en la
#   lista de Mateo no tendria su operacion. Si se agregan retornos, numerados
#   como subnivel del mensaje que los provoca (1.3 -> 1.3.1). Antes de
#   dibujar se comprueba todo eso, y si algo no cuadra no se dibuja.
#
# ---- LA MAQUETA ----
#   EA NO respeta la altura guardada de los mensajes: los apila por SeqNo de
#   35 en 35 desde -135. Las cajas y las notas, en cambio, quedan donde se
#   guardan, y EA decide que encierra cada una por la altura DIBUJADA. Por eso
#   el script calcula esas alturas y pone las cajas alrededor (ver el bloque
#   «la maqueta que EA impone»).
#
# ---- DOS PASADAS ----
#   1. COM: lineas de vida, notas, fragmentos y mensajes.
#   2. OLEDB, con EA cerrado: la geometria y el tipo de cada mensaje, el
#      operador y los operandos de cada fragmento (al reves: EA los lee de
#      abajo hacia arriba) y el orden Z.
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint3-comun.ps1')
. (Join-Path $PSScriptRoot 'ea-sprint3-dinamica.ps1')
trap { Salir-ConError $_ }

$Y_PRIMERO = -135; $PASO = 35; $AUTO = 15
$X0 = 230; $GAP = 50; $TOP_LV = -50
$NOTA_L = 5; $NOTA_R = 150; $NOTA_ALTO = 50
$MAX_ROTULO = 250

# El guion contra la lista de Mateo. Devuelve los errores encontrados.
function Revisar-Guion($c, $guion) {
    $errores = @()
    $claves = @{}; foreach ($p in $c.participantes) { $claves[$p.k] = $true }
    $textos = @($guion | Where-Object { $_.t -eq 'msg' } | ForEach-Object { $_.n })
    foreach ($m in @($guion | Where-Object { $_.t -eq 'msg' })) {
        foreach ($kk in @($m.o, $m.d)) { if (-not $claves.ContainsKey($kk)) { $errores += "participante desconocido '$kk' en «$($m.n)»" } }
    }
    $orden = @{}; $esperados = @{}
    foreach ($m in $c.mensajes) {
        $g = [int]$m.g
        if (-not $orden.ContainsKey($g)) { $orden[$g] = 0 }
        $orden[$g]++
        $rotulo = "$g.$($orden[$g]): $($m.m)"
        $esperados[$rotulo] = $true
        $veces = @($textos | Where-Object { $_ -eq $rotulo -or $_.StartsWith("$rotulo  ") }).Count
        if ($veces -ne 1) { $errores += "«$rotulo» aparece $veces veces (tiene que estar una)" }
    }
    # Toda llamada del guion tiene que ser de Mateo; lo agregado solo puede
    # ser retorno.
    foreach ($m in @($guion | Where-Object { $_.t -eq 'msg' -and -not $_.ret })) {
        $base = ($m.n -split '  \{')[0]
        if (-not $esperados.ContainsKey($base)) { $errores += "llamada que no está en la comunicación: «$($m.n)»" }
    }
    # Fragmentos balanceados.
    $hondo = 0
    foreach ($it in $guion) {
        if ($it.t -in 'alt', 'loop') { $hondo++ }
        if ($it.t -eq 'fin') { $hondo-- }
        if ($hondo -lt 0) { $errores += 'un fin sin su alt o loop' }
    }
    if ($hondo -ne 0) { $errores += "quedan $hondo fragmentos sin cerrar" }
    return $errores
}

# ---- LOS FRAGMENTOS QUE SE DIBUJAN ----
#   El guion de ea-sprint3-dinamica.ps1 tiene un alt por cada if del codigo,
#   y eso no deja ver la secuencia (CU29 y CU34 pasaban de 15 cajas). Se
#   dibujan solo los fragmentos caracteristicos:
#   - un alt queda si dos o mas operandos llevan mensajes de Mateo (o una
#     nota FLUJO n); si los lleva uno solo, se dibuja ese operando suelto,
#     sin la caja, y los demas (retornos de error agregados) se omiten;
#   - un loop queda si adentro hay algun mensaje de Mateo;
#   - clave=$true en el alt o el loop lo deja siempre, con todos sus
#     operandos; omitir=$true lo quita siempre y deja su contenido suelto.
#   Ningun mensaje de Mateo se pierde, y Revisar-Guion lo comprueba despues.
#   -Completo dibuja el guion entero.
function Leer-Bloque($guion, [ref]$i) {
    $items = New-Object System.Collections.ArrayList
    while ($i.Value -lt $guion.Count) {
        $it = $guion[$i.Value]
        if ($it.t -in 'op', 'fin') { return ,$items }
        $i.Value++
        if ($it.t -in 'alt', 'loop') {
            $fr = @{ t = $it.t; clave = [bool]$it.clave; omitir = [bool]$it.omitir; ops = New-Object System.Collections.ArrayList }
            if ($it.t -eq 'loop') { [void]$fr.ops.Add(@{ g = $it.g; items = (Leer-Bloque $guion $i) }) }
            while ($guion[$i.Value].t -eq 'op') {
                $g = $guion[$i.Value].g; $i.Value++
                [void]$fr.ops.Add(@{ g = $g; items = (Leer-Bloque $guion $i) })
            }
            $i.Value++   # el fin
            [void]$items.Add($fr)
        } else { [void]$items.Add($it) }
    }
    return ,$items
}
function Tiene-Mateo($items) {
    foreach ($it in $items) {
        if ($it.t -eq 'nota') { return $true }
        if ($it.t -eq 'msg' -and $it.n -match '^\d+\.\d+:') { return $true }
        if ($it.ops) { foreach ($o in $it.ops) { if (Tiene-Mateo $o.items) { return $true } } }
    }
    return $false
}
function Escribir-Bloque($items, $salida) {
    foreach ($it in $items) {
        if (-not $it.ops) { [void]$salida.Add($it); continue }
        if ($it.omitir) { foreach ($o in $it.ops) { Escribir-Bloque $o.items $salida }; continue }
        if ($it.t -eq 'loop') {
            if (-not $it.clave -and -not (Tiene-Mateo $it.ops[0].items)) { continue }
            [void]$salida.Add(@{ t = 'loop'; g = $it.ops[0].g })
            Escribir-Bloque $it.ops[0].items $salida
            [void]$salida.Add(@{ t = 'fin' }); continue
        }
        $quedan = @(if ($it.clave) { $it.ops } else { $it.ops | Where-Object { Tiene-Mateo $_.items } })
        if ($quedan.Count -eq 1) { Escribir-Bloque $quedan[0].items $salida; continue }
        if ($quedan.Count -eq 0) { continue }
        [void]$salida.Add(@{ t = 'alt' })
        foreach ($o in $quedan) {
            [void]$salida.Add(@{ t = 'op'; g = $o.g })
            Escribir-Bloque $o.items $salida
        }
        [void]$salida.Add(@{ t = 'fin' })
    }
}
function Simplificar-Guion($guion) {
    $i = 0
    $arbol = Leer-Bloque $guion ([ref]$i)
    if ($i -ne $guion.Count) { throw "El guion tiene un op o un fin suelto (ítem $i)." }
    $salida = New-Object System.Collections.ArrayList
    Escribir-Bloque $arbol $salida
    return ,$salida.ToArray()
}

$pkg = Get-PaqueteTipo 'Sprint 3 - Secuencia' $Rehacer
$pkgClases = Get-PaqueteTipo 'Sprint 3 - Diseño de clase' $false
$pendientes = @()

foreach ($clave in (Claves-Casos $Caso)) {
    $c = $CASOS_SPRINT3[$clave]
    $dn = $DINAMICA_SPRINT3[$clave]
    if (-not $dn -or -not $dn.secuencia) { Write-Output "  $($c.cu): sin guion de secuencia"; continue }
    $guion = if ($Completo) { $dn.secuencia } else { Simplificar-Guion $dn.secuencia }
    $nomDia = "Secuencia - $($c.cu) $($c.nombre) ($($dn.plataforma))"
    if (Get-Diagrama $pkg $nomDia) { Write-Output "  $nomDia ya existe, no se toca"; continue }

    $errores = @(Revisar-Guion $c $guion)
    if ($errores.Count) {
        $errores | ForEach-Object { Write-Output "  $($c.cu): $_" }
        throw "El guion de $($c.cu) no cuadra con la comunicación de Mateo."
    }

    # Las clases de este caso de uso: ea-diseno-clases-sprint3.ps1 les pone
    # el codigo del caso en el alias.
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
            $eid = Get-Actor $p.n ($p.rol -eq 'externo')
        } else {
            if (-not $clase.ContainsKey($p.n)) { throw "Falta la clase '$($p.n)' de $($c.cu). Corre antes ea-diseno-clases-sprint3.ps1." }
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
                $msgs += @{ o = $item.o; d = $item.d; n = $item.n; ret = [bool]$item.ret; y = $yy; auto = $auto }
                if ($notaPend) { $notas += @{ txt = $notaPend; y = $yy }; $notaPend = $null }
                foreach ($f in $pila) {
                    $f.lv[$item.o] = $true; $f.lv[$item.d] = $true
                    if ($auto) { $f.txt = [math]::Max($f.txt, $item.n.Length) }
                }
                $k++
            }
            { $_ -in 'alt', 'loop' } {
                $tipo = if ($item.t -eq 'alt') { 0 } else { 4 }
                $ops = New-Object System.Collections.ArrayList
                if ($tipo -eq 4) { [void]$ops.Add($item.g) }
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
                [void]$f.ops.Add($item.g)
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
        # t_connector.Name admite 255 caracteres. Con mas, Update() devuelve
        # False SIN error, el mensaje no se guarda y todos los de abajo suben
        # un renglon: las cajas quedan encerrando lo que no es (26/10/2026).
        # Se recorta solo el anclaje entre llaves; el entero va a las notas.
        $rotulo = $m.n; $notaMsg = ''
        if ($rotulo.Length -gt $MAX_ROTULO) {
            $notaMsg = $rotulo
            $corte = $rotulo.IndexOf('  {')
            if ($corte -lt 0 -or $corte -gt $MAX_ROTULO - 10) { throw "Rótulo de más de $MAX_ROTULO caracteres sin anclaje que recortar: $rotulo" }
            $rotulo = $rotulo.Substring(0, $MAX_ROTULO - 2) + '…}'
        }
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
