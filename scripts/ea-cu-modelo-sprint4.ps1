param(
    # Borra el paquete «Sprint 4 - Casos de Uso» y lo vuelve a generar.
    [switch]$Rehacer,
    [string]$Modelo = ''
)

# =========================================================================
# CAPITULO 4 - Sprint 4 - punto 1.3 Contexto del Sistema
#   "Modelo de casos de uso estructurado"
#
# ---- QUE DIBUJA ----
#   El 1.3 del Sprint 3 TAL COMO LUIS LO ACOMODO A MANO, mas los casos de uso
#   del Sprint 4. No se regenera desde datos (como ea-cu-modelo-sprint3.ps1):
#   se COPIA el diagrama del Sprint 3.
#     - El diagrama nuevo referencia los MISMOS elementos del paquete
#       «Sprint 3 - Casos de Uso» (no se duplica ningun actor ni caso de uso),
#       con las mismas posiciones, tamanos y estilos (t_diagramobjects) y las
#       mismas filas de t_diagramlinks (rutas, rotulos y ocultos).
#     - Los conectores entre esos elementos ya existen: EA los dibuja solos.
#     - ShowForeign en falso: los elementos son de otro paquete y sin esto EA
#       escribiria «(from Sprint 3 - Casos de Uso)» debajo de cada uno.
#   El diagrama del Sprint 3 no se toca.
#
# ---- LOS CASOS DE USO DEL SPRINT 4 ----
#   CU36 a CU43 ya existen en «3.10 Paquetes y casos de uso» (la lista
#   CU1..CU46 del documento): se reutilizan. CU47 a CU54 son nuevos del
#   Sprint 4 (reparto.md y ampliacion-17-11.md) y se crean en el paquete del
#   Sprint 4. Van en una zona libre, a la derecha de todo, en tres columnas
#   (IA 2, IA 3 y el resto del Sprint 4), con su asociacion a los actores del
#   Sprint 3: Luis solo tiene que moverlos.
#   Actores segun el codigo (los permisos y quien dispara cada flujo):
#     CU36 Administracion (consulta) y Sistema (score_noshow --loop)
#     CU37 Sistema (send_appointment_reminders) -> Paciente recibe el aviso
#     CU38 Administracion. CU39 Sistema (retrain_noshow).
#     CU40/CU41 Medico (al firmar) y Paciente (lee el texto aprobado)
#     CU42/CU43 Medico. CU47 Paciente. CU48 Paciente y Medico.
#     CU49 Paciente (califica) y Administracion (satisfaccion en KPIs)
#     CU50 Paciente. CU51 Administracion. CU52 Paciente.
#     CU53 Paciente y Sistema (process_waitlist). CU54 Medico y Paciente.
#   No se agregan include/extend: ninguno se verifica en el codigo con la
#   claridad de los del Sprint 3 (CU3->CU1, CU17->CU16, CU35->CU32/CU33).
#
# Dos pasadas: COM (paquete, diagrama, objetos, casos nuevos, asociaciones)
# y OLEDB con EA cerrado (estilos y orden de los objetos, filas de
# t_diagramlinks, ShowForeign).
# =========================================================================

$ErrorActionPreference = 'Stop'
$PSScriptRoot_ = $PSScriptRoot
if (-not $Modelo) { $Modelo = Join-Path $PSScriptRoot_ '..\docs\diagramas\PlataformaMedica.eapx' }
$Modelo = [System.IO.Path]::GetFullPath($Modelo)

$DIA_S3 = '1.3 Modelo de Casos de Uso Estructurado - Sprint 3'
$DIA_S4 = '1.3 Modelo de Casos de Uso Estructurado - Sprint 4'
$PKG_S3 = 'Sprint 3 - Casos de Uso'
$PKG_S4 = 'Sprint 4 - Casos de Uso'

$CU_W = 320; $CU_H = 70; $PASO = 110; $Y0 = -220
$COLS = @(
  @{ x = 2500; titulo = 'Sprint 4 · IA 2 · Predicción de Inasistencia'; cus = @(
      @{ n = 'CU36 Predicción de Riesgo de Inasistencia';             act = @('Administrador de Organización', 'Sistema') },
      @{ n = 'CU37 Envío de Recordatorios por Riesgo de Inasistencia'; act = @('Sistema', 'Paciente') },
      @{ n = 'CU38 Proyección de Demanda de Fichas';                   act = @('Administrador de Organización') },
      @{ n = 'CU39 Reentrenamiento del Modelo de No-Show';             act = @('Sistema') } ) },
  @{ x = 2900; titulo = 'Sprint 4 · IA 3 · Generación de Resúmenes'; cus = @(
      @{ n = 'CU40 Generación de Resumen de Consulta mediante IA'; act = @('Médico', 'Paciente') },
      @{ n = 'CU41 Generación de Indicaciones de Preparación';     act = @('Médico', 'Paciente') },
      @{ n = 'CU42 Generación de Resumen de Historia Clínica';     act = @('Médico') },
      @{ n = 'CU43 Validación de Contenido Generado por IA';       act = @('Médico') } ) },
  @{ x = 3300; titulo = 'Sprint 4 · Historias nuevas (US-46 a US-53)'; cus = @(
      @{ n = 'CU47 Consulta de Transacciones por Voz';            act = @('Paciente') },
      @{ n = 'CU48 Chat con el Médico Tratante';                  act = @('Paciente', 'Médico') },
      @{ n = 'CU49 Calificación de la Atención';                  act = @('Paciente', 'Administrador de Organización') },
      @{ n = 'CU50 Recordatorio de Toma de Medicamentos';         act = @('Paciente') },
      @{ n = 'CU51 Finanzas por Voz y Contabilidad';              act = @('Administrador de Organización') },
      @{ n = 'CU52 Experiencia Plus en la Compra de la Ficha';    act = @('Paciente') },
      @{ n = 'CU53 Lista de Espera con Aviso de Cupo Liberado';   act = @('Paciente', 'Sistema') },
      @{ n = 'CU54 Registro de Signos Vitales';                   act = @('Médico', 'Paciente') } ) }
)


# La semilla de los autonumericos (ver ea-sprint4-comun.ps1, Ajustar-Semillas):
# si quedo atras, el primer conector que EA crea no se guarda.
$cn0 = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;OLE DB Services=-4;Data Source=$Modelo;")
$cn0.Open()
foreach ($t in @(@('t_object', 'Object_ID'), @('t_connector', 'Connector_ID'), @('t_diagram', 'Diagram_ID'), @('t_diagramobjects', 'Instance_ID'), @('t_diagramlinks', 'Instance_ID'))) {
    $q = $cn0.CreateCommand(); $q.CommandText = "SELECT MAX([$($t[1])]) FROM [$($t[0])]"; $max = $q.ExecuteScalar()
    if ($max -is [DBNull]) { continue }
    $q = $cn0.CreateCommand(); $q.CommandText = "ALTER TABLE [$($t[0])] ALTER COLUMN [$($t[1])] COUNTER($([int]$max + 1),1)"; [void]$q.ExecuteNonQuery()
}
$cn0.Close(); $cn0.Dispose(); [System.Data.OleDb.OleDbConnection]::ReleaseObjectPool(); [GC]::Collect()

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($Modelo)) { throw "No se pudo abrir $Modelo" }
trap {
    Write-Host "ERROR: $($_.Exception.Message)  [línea $($_.InvocationInfo.ScriptLineNumber)]"
    try { $ea.CloseFile(); $ea.Exit() } catch { }
    exit 1
}
function Consulta($sql) {
    $doc = New-Object System.Xml.XmlDocument; $doc.LoadXml($ea.SQLQuery($sql))
    $filas = New-Object System.Collections.ArrayList
    foreach ($n in $doc.SelectNodes('//Row')) { [void]$filas.Add($n) }
    return ,$filas
}

# ---- el paquete y el diagrama --------------------------------------------
$pRaiz = $null
foreach ($p in $ea.Models.GetAt(0).Packages) { if ($p.Name -eq 'Plataforma Médica Multi-Inquilino') { $pRaiz = $p } }
$cap = $null; foreach ($p in $pRaiz.Packages) { if ($p.Name -eq 'CAP. 4 - Proceso de desarrollo') { $cap = $p } }
if ($Rehacer) {
    for ($i = $cap.Packages.Count - 1; $i -ge 0; $i--) { if ($cap.Packages.GetAt($i).Name -eq $PKG_S4) { $cap.Packages.DeleteAt($i, $false) } }
    $cap.Packages.Refresh()
}
$pkg = $null; foreach ($p in $cap.Packages) { if ($p.Name -eq $PKG_S4) { $pkg = $p } }
if (-not $pkg) { $pkg = $cap.Packages.AddNew($PKG_S4, 'Package'); [void]$pkg.Update(); $cap.Packages.Refresh() }
foreach ($d in $pkg.Diagrams) { if ($d.Name -eq $DIA_S4) { Write-Output "  $DIA_S4 ya existe; usá -Rehacer"; $ea.CloseFile(); $ea.Exit(); exit 0 } }

$fila = Consulta "SELECT d.Diagram_ID FROM t_diagram d INNER JOIN t_package p ON p.Package_ID = d.Package_ID WHERE p.Name = '$PKG_S3' AND d.Name = '$DIA_S3'"
if ($fila.Count -ne 1) { throw "No encuentro el diagrama '$DIA_S3'" }
$idS3 = [int]$fila[0].Diagram_ID

$dia = $pkg.Diagrams.AddNew($DIA_S4, 'UseCase'); [void]$dia.Update(); $pkg.Diagrams.Refresh()

# ---- 1. la copia: los mismos objetos en las mismas cajas ------------------
$objs = Consulta "SELECT Object_ID, RectLeft, RectTop, RectRight, RectBottom FROM t_diagramobjects WHERE Diagram_ID = $idS3"
foreach ($o in $objs) {
    $do = $dia.DiagramObjects.AddNew("l=$($o.RectLeft);r=$($o.RectRight);t=$($o.RectTop);b=$($o.RectBottom);", '')
    $do.ElementID = [int]$o.Object_ID
    [void]$do.Update()
}

# ---- 2. los casos de uso del Sprint 4 en la zona libre -------------------
$actor = @{}
foreach ($r in (Consulta "SELECT o.Object_ID, o.Name FROM t_object o INNER JOIN t_package p ON p.Package_ID = o.Package_ID WHERE o.Object_Type = 'Actor' AND p.Name = '$PKG_S3'")) { $actor[[string]$r.Name] = [int]$r.Object_ID }
$nuevos = 0; $asoc = 0
foreach ($col in $COLS) {
    $tit = $pkg.Elements.AddNew('', 'Note'); $tit.Notes = $col.titulo; [void]$tit.Update()
    $do = $dia.DiagramObjects.AddNew("l=$($col.x);r=$($col.x + $CU_W);t=$($Y0 + 90);b=$($Y0 + 40);", ''); $do.ElementID = $tit.ElementID; [void]$do.Update()
    $t = $Y0
    foreach ($cu in $col.cus) {
        $codigo = ($cu.n -split ' ')[0]
        $hay = Consulta "SELECT o.Object_ID FROM t_object o INNER JOIN t_package p ON p.Package_ID = o.Package_ID WHERE o.Object_Type = 'UseCase' AND p.Name = '3.10 Paquetes y casos de uso' AND LEFT(o.Name, $($codigo.Length + 1)) = '$codigo '"
        if ($hay.Count) { $eid = [int]$hay[0].Object_ID }
        else {
            $e = $pkg.Elements.AddNew($cu.n, 'UseCase'); [void]$e.Update(); $pkg.Elements.Refresh()
            $eid = $e.ElementID; $nuevos++
        }
        $do = $dia.DiagramObjects.AddNew("l=$($col.x);r=$($col.x + $CU_W);t=$t;b=$($t - $CU_H);", ''); $do.ElementID = $eid; [void]$do.Update()
        foreach ($a in $cu.act) {
            if (-not $actor.ContainsKey($a)) { throw "No está el actor '$a' en $PKG_S3" }
            $src = $ea.GetElementByID($actor[$a])
            $ya = $false
            foreach ($x in $src.Connectors) { if ($x.Type -eq 'Association' -and $x.SupplierID -eq $eid) { $ya = $true } }
            if ($ya) { continue }
            $c = $src.Connectors.AddNew('', 'Association'); $c.SupplierID = $eid
            if (-not $c.Update()) { throw "EA no guardó $a -> $codigo : $($c.GetLastError())" }
            $asoc++
        }
        $t -= $PASO
    }
}
$idS4 = $dia.DiagramID
$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers(); Start-Sleep -Milliseconds 1500

# ---- 3. OLEDB: estilos, orden, filas de enlaces y ShowForeign -------------
$cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;OLE DB Services=-4;Data Source=$Modelo;")
$cn.Open()
try {
    $cmd = $cn.CreateCommand()
    $cmd.CommandText = "SELECT Object_ID, ObjectStyle, [Sequence] FROM t_diagramobjects WHERE Diagram_ID = $idS3"
    $rd = $cmd.ExecuteReader(); $est = @()
    while ($rd.Read()) { $est += , @([int]$rd[0], [string]$rd[1], $(if ($rd[2] -is [DBNull]) { 0 } else { [int]$rd[2] })) }
    $rd.Close()
    foreach ($x in $est) {
        $u = $cn.CreateCommand()
        $u.CommandText = "UPDATE t_diagramobjects SET ObjectStyle = ?, [Sequence] = ? WHERE Diagram_ID = $idS4 AND Object_ID = $($x[0])"
        [void]$u.Parameters.AddWithValue('a', $x[1]); [void]$u.Parameters.AddWithValue('b', $x[2])
        [void]$u.ExecuteNonQuery()
    }
    $cmd.CommandText = "SELECT ConnectorID, Geometry, Style, Hidden, Path FROM t_diagramlinks WHERE DiagramID = $idS3"
    $rd = $cmd.ExecuteReader(); $lk = @()
    while ($rd.Read()) { $lk += , @([int]$rd[0], [string]$rd[1], [string]$rd[2], $(if ($rd[3] -is [DBNull]) { $false } else { [bool]$rd[3] }), [string]$rd[4]) }
    $rd.Close()
    foreach ($x in $lk) {
        $u = $cn.CreateCommand()
        $u.CommandText = "INSERT INTO t_diagramlinks (DiagramID, ConnectorID, Geometry, Style, Hidden, Path) VALUES ($idS4, $($x[0]), ?, ?, ?, ?)"
        [void]$u.Parameters.AddWithValue('g', $x[1]); [void]$u.Parameters.AddWithValue('s', $x[2])
        [void]$u.Parameters.AddWithValue('h', $x[3]); [void]$u.Parameters.AddWithValue('p', $x[4])
        [void]$u.ExecuteNonQuery()
    }
    $u = $cn.CreateCommand(); $u.CommandText = "UPDATE t_diagram SET ShowForeign = False WHERE Diagram_ID = $idS4"; [void]$u.ExecuteNonQuery()
} finally { $cn.Close(); $cn.Dispose(); [System.Data.OleDb.OleDbConnection]::ReleaseObjectPool() }

Write-Output ("  {0} : {1} objetos copiados del Sprint 3, {2} filas de enlaces, {3} casos nuevos, {4} asociaciones" -f $DIA_S4, $objs.Count, $lk.Count, $nuevos, $asoc)
Write-Output 'OK'
