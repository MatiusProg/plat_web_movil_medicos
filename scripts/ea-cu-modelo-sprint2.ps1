param(
    # Borra el paquete de casos de uso del Sprint 2 y lo vuelve a generar.
    [switch]$Rehacer,
    # El modelo sobre el que se trabaja. Por omision, el del repositorio.
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx')
)

# =========================================================================
# CAPITULO 4 - Sprint 2 - punto 1.3 Contexto del Sistema
#   "Modelo de casos de uso estructurado"
#
# ---- QUE DIBUJA ----
#   Un unico diagrama ACUMULADO: todos los casos de uso abordados hasta el
#   Sprint 2 -los de los Sprints 0, 1 y 2- y todos sus actores. Es el mismo
#   criterio del 1.3 del Sprint 1 (ea-cu-modelo-estructurado.ps1), que reune
#   los Sprints 0 y 1. Incluye los que todavia no tienen codigo, porque el
#   modelo describe el alcance comprometido, no lo entregado.
#
# ---- DE DONDE SALEN LOS DATOS ----
#   La numeracion es la de la "3.9 Lista de casos de uso" del documento
#   (CU1..CU46), que ya esta en el modelo, en el paquete 3.10. Los casos de
#   los Sprints 0 y 1, sus actores y sus relaciones son los del 1.3 del
#   Sprint 1. Los del Sprint 2 salen de docs/sprints/sprint-2/reparto.md.
#
#   Los actores del Sprint 2 salen de los permisos sembrados, no de la prosa:
#     - appointments.appointment.create/cancel/reschedule -> solo patient
#       (accounts/migrations/0006_seed_permissions_sprint_2_appointments.py)
#     - encounters.encounter.create -> solo practitioner
#       (encounters/migrations/0003_seed_permissions.py)
#     - historial longitudinal -> practitioner y patient
#       (encounters/migrations/0004_permiso_historial.py)
#     - assistant.suggest.use -> patient, receptionist y org_admin
#       (assistant/migrations/0003_seed_permission.py)
#   Cuando un caso lo puede iniciar mas de un actor, se dibuja el principal y
#   los demas quedan en la nota del caso de uso: cada linea de mas cruza el
#   diagrama entero sin decir nada que la nota no diga.
#
# ---- DECISIONES DE MODELADO, Y POR QUE ----
#   1. Actor abstracto "Usuario": CU1, CU3, CU4 y CU6 los ejecutan todos los
#      actores humanos (igual que en el Sprint 1).
#   2. "Titular" generaliza a "Paciente": un titular es un paciente que ademas
#      administra familiares a cargo. Por eso solo se le asocia CU8.
#   3. Solo se dibujan las relaciones verificables en el codigo:
#        - CU3  <<extend>>  CU1  : recuperar la contrasena (Sprint 1).
#        - CU17 <<include>> CU16 : la busqueda muestra el proximo espacio
#          disponible, catalog/search.py (Sprint 1).
#        - CU35 <<extend>>  CU32 : la barrera de triage.py corta la
#          orientacion antes de recuperar nada (assistant/views.py).
#        - CU35 <<extend>>  CU33 : la consulta administrativa tambien deriva
#          si el modelo marca una urgencia (SuggestView._administrativa).
#      CU19 (pago) y CU20 (comprobante) se relacionan con CU18 en el reparto,
#      pero todavia no tienen codigo: no se inventa el include.
#   4. "Medico" se asocia a CU9, como en el Sprint 1: el punto (g) de US-08
#      le da lectura de los antecedentes al profesional.
#
# ---- EL TRAZADO ----
#   Dos columnas de casos de uso: la del paciente y la clinica a la
#   izquierda, la del personal y la administracion a la derecha. Los actores
#   van LEJOS de su columna, con un corredor ancho: con el actor pegado a la
#   columna, la linea hacia un caso de uso de mas abajo entraba en diagonal
#   empinada y pasaba por encima de las elipses de arriba. "Usuario" va
#   arriba, sobre la columna de los actores del paciente.
#
#   Cada actor y cada caso de uso declaran su fila, y se admiten medias filas:
#   es lo que permite correr un elemento sin reescribir coordenadas.
#
# ADITIVO: abre el modelo y solo agrega lo que falta.
# =========================================================================

$ErrorActionPreference = 'Stop'

$NOMBRE_DIA = '1.3 Modelo de Casos de Uso Estructurado - Sprint 2'
$NOMBRE_PKG = 'Sprint 2 - Casos de Uso'

# ---- Constantes de dibujo -------------------------------------------------
$ACT_W = 140; $ACT_H = 80
$CU_W  = 320; $CU_H  = 70;  $CU_PASO = 110
$Y0    = -220
$COL   = @{ A = 760; B = 1180 }

# Linea ortogonal cuadrada (Orthogonal Square) en el diagrama.
$ESTILO_GENERALIZACION = 'Mode=3;EOID=;SOID=;Color=-1;LWidth=0;TREE=OS;'

function FilaY($fila) { return [int]($Y0 - $fila * $CU_PASO) }

# ---- Los datos ------------------------------------------------------------

# Cada actor declara su x y su fila (puede ser media fila). Los de la
# derecha van escalonados hacia afuera: su generalizacion sube en vertical,
# y con todos en la misma x la de abajo pasaba por encima de los de arriba.
$ACTORES = @(
    @{ k='usuario';    n='Usuario';                          abstracto=$true;  x=40;   f=-1.5 },
    @{ k='paciente';   n='Paciente';                         abstracto=$false; x=40;   f=10   },
    @{ k='titular';    n='Titular';                          abstracto=$false; x=40;   f=16.5 },
    @{ k='medico';     n='Médico';                           abstracto=$false; x=400;  f=20   },
    @{ k='recep';      n='Recepcionista';                    abstracto=$false; x=1880; f=2    },
    @{ k='adminorg';   n='Administrador de Organización';    abstracto=$false; x=1980; f=8    },
    @{ k='superadmin'; n='Superadministrador de Plataforma'; abstracto=$false; x=2080; f=13.5 },
    @{ k='sistema';    n='Sistema';                          abstracto=$false; x=2080; f=16.5 }
)

# Cada caso de uso declara su columna y su fila.
$CASOS = @(
    # --- identidad (Usuario) ---
    @{ k='cu1';  c='A'; f=0;    n='CU1 Autenticación de Usuario' },
    @{ k='cu3';  c='A'; f=1;    n='CU3 Recuperación de Credenciales' },
    @{ k='cu4';  c='A'; f=2;    n='CU4 Terminación de Sesión' },
    @{ k='cu6';  c='A'; f=3;    n='CU6 Gestión de Perfil de Usuario' },
    # --- cara del paciente ---
    @{ k='cu2';  c='A'; f=5;    n='CU2 Registro de Usuarios / Pacientes' },
    @{ k='cu16'; c='A'; f=6;    n='CU16 Consulta de Disponibilidad Médica' },
    @{ k='cu17'; c='A'; f=7;    n='CU17 Búsqueda de Profesionales' },
    @{ k='cu18'; c='A'; f=8;    n='CU18 Reserva de Ficha Médica' },
    @{ k='cu19'; c='A'; f=9;    n='CU19 Pago de Ficha en Línea' },
    @{ k='cu20'; c='A'; f=10;   n='CU20 Generación de Comprobante Digital' },
    @{ k='cu21'; c='A'; f=11;   n='CU21 Cancelación / Reprogramación de Ficha' },
    @{ k='cu22'; c='A'; f=12;   n='CU22 Confirmación de Asistencia' },
    @{ k='cu32'; c='A'; f=13;   n='CU32 Orientación Médica mediante Chatbot' },
    @{ k='cu35'; c='A'; f=14;   n='CU35 Derivación a Atención de Emergencia' },
    @{ k='cu33'; c='A'; f=15;   n='CU33 Consulta de Información mediante Chatbot' },
    @{ k='cu8';  c='A'; f=16.5; n='CU8 Gestión de Pacientes Dependientes' },
    # --- clinica ---
    @{ k='cu9';  c='A'; f=18;   n='CU9 Gestión de Antecedentes del Paciente' },
    @{ k='cu25'; c='A'; f=19;   n='CU25 Registro de Atención Médica' },
    @{ k='cu26'; c='A'; f=20;   n='CU26 Consulta de Historia Clínica' },
    # --- mostrador ---
    @{ k='cu10'; c='B'; f=1.5;  n='CU10 Búsqueda y Consulta de Pacientes' },
    @{ k='cu23'; c='B'; f=2.5;  n='CU23 Check-in del Paciente' },
    # --- administracion de la organizacion ---
    @{ k='cu5';  c='B'; f=5;    n='CU5 Gestión de Roles y Permisos' },
    @{ k='cu7';  c='B'; f=6;    n='CU7 Consulta de Bitácora de Auditoría' },
    @{ k='cu11'; c='B'; f=7;    n='CU11 Administración de Pacientes' },
    @{ k='cu12'; c='B'; f=8;    n='CU12 Gestión de Sucursales' },
    @{ k='cu13'; c='B'; f=9;    n='CU13 Gestión de Especialidades y Profesionales' },
    @{ k='cu14'; c='B'; f=10;   n='CU14 Gestión de Agendas Médicas' },
    @{ k='cu15'; c='B'; f=11;   n='CU15 Bloqueo de Agenda Médica' },
    # --- plataforma ---
    @{ k='cu44'; c='B'; f=13;   n='CU44 Gestión de Organizaciones (Tenants)' },
    @{ k='cu45'; c='B'; f=14;   n='CU45 Gestión de Planes de Suscripción' },
    @{ k='cu46'; c='B'; f=15.5; n='CU46 Supervisión y Aislamiento de Organizaciones' }
)

# Nota de cada caso de uso: historia, sprint y estado al 03/10/26. No se ve
# en el PNG, pero queda en el modelo para quien lo abra en EA.
$NOTAS = @{
    cu1  = 'Sprint 0. Entregado.'
    cu2  = 'Sprint 0. Entregado (web); la pantalla móvil se completó en el Sprint 1.'
    cu4  = 'Sprint 0. Entregado.'
    cu44 = 'Sprint 0. Entregado.'
    cu45 = 'Sprint 0. Entregado.'
    cu46 = 'Sprint 0. Entregado.'
    cu5  = 'Arrastre del Sprint 0. Entregado en el Sprint 1.'
    cu3  = 'Sprint 1. Entregado.'
    cu7  = 'Sprint 1. Entregado.'
    cu8  = 'Sprint 1. Entregado (sólo móvil).'
    cu9  = 'Sprint 1. Entregado: móvil, más el endpoint de lectura para el módulo de atención.'
    cu12 = 'Sprint 1. Entregado.'
    cu13 = 'Sprint 1. Entregado.'
    cu14 = 'Sprint 1. Entregado.'
    cu15 = 'Sprint 1. Entregado.'
    cu16 = 'Sprint 1. Entregado.'
    cu17 = 'Sprint 1. Entregado.'
    cu6  = 'US-05, deuda del Sprint 1. Entregado en el Sprint 2: web y móvil (PR #49).'
    cu10 = 'US-09, deuda del Sprint 1. Sin código en main al 03/10/26.'
    cu11 = 'US-10, deuda del Sprint 1. Sin código en main al 03/10/26.'
    cu18 = 'Sprint 2, US-17. Backend y web entregados (PR #45); falta la pantalla móvil.'
    cu19 = 'Sprint 2, US-18. Sin código en main al 03/10/26.'
    cu20 = 'Sprint 2, US-19. Sin código en main al 03/10/26.'
    cu21 = 'Sprint 2, US-20. Backend y web entregados (PR #45); falta la pantalla móvil.'
    cu22 = 'Sprint 2, US-21. Sin código en main al 03/10/26.'
    cu23 = 'Sprint 2, US-22. Sin código en main al 03/10/26.'
    cu25 = 'Sprint 2, US-24. Entregado (PR #48).'
    cu26 = 'Sprint 2, US-25. Entregado (PR #50). Actor principal: el Médico. El permiso también lo tiene el Paciente, para ver su propio historial (encounters/migrations/0004_permiso_historial.py).'
    cu32 = 'Sprint 2, US-31. Entregado: móvil (PR #41/#42) y web (PR #49). También tienen el permiso la Recepción y el Administrador de Organización.'
    cu33 = 'Sprint 2, US-32. Entregado (PR #47), sobre el mismo endpoint que CU32.'
    cu35 = 'Sprint 2, US-34. Entregado (PR #46): reglas de triage.py y marca de urgencia del modelo.'
}

# actor -> casos de uso que inicia.
$ASOCIACIONES = @{
    usuario    = @('cu1','cu3','cu4','cu6')
    paciente   = @('cu2','cu16','cu17','cu18','cu19','cu20','cu21','cu22','cu32','cu33','cu9')
    titular    = @('cu8')
    medico     = @('cu9','cu25','cu26')
    recep      = @('cu10','cu23')
    adminorg   = @('cu5','cu7','cu11','cu12','cu13','cu14','cu15','cu46')
    superadmin = @('cu44','cu45','cu46')
    sistema    = @('cu46')
}

$GENERALIZACIONES = @(
    @{ hijo='paciente';   padre='usuario' },
    @{ hijo='recep';      padre='usuario' },
    @{ hijo='medico';     padre='usuario' },
    @{ hijo='adminorg';   padre='usuario' },
    @{ hijo='superadmin'; padre='usuario' },
    @{ hijo='titular';    padre='paciente' }
)

# Dependencias entre casos de uso. extend: DE la extension AL caso base;
# include: DEL que incluye AL incluido.
$DEPENDENCIAS = @(
    @{ de='cu3';  a='cu1';  tipo='extend'  },
    @{ de='cu17'; a='cu16'; tipo='include' },
    @{ de='cu35'; a='cu32'; tipo='extend'  },
    @{ de='cu35'; a='cu33'; tipo='extend'  }
)

# =========================================================================
# PARTE 1 - Enterprise Architect por COM
# =========================================================================

$Modelo = [System.IO.Path]::GetFullPath($Modelo)
if (-not (Test-Path $Modelo)) { throw "No existe $Modelo" }

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($Modelo)) { throw "No se pudo abrir $Modelo" }
# ---- cierre garantizado ----
# Si algo falla a mitad de camino, EA queda abierto en segundo plano, sin
# ventana, reteniendo el archivo. El trap lo cierra antes de propagar el error.
trap {
    Write-Host "ERROR: $($_.Exception.Message)  [$($_.InvocationInfo.ScriptName):$($_.InvocationInfo.ScriptLineNumber)]"
    try { $ea.CloseFile(); $ea.Exit() } catch { }
    try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null } catch { }
    break
}

function Get-OCrearPaquete($padre, $nombre) {
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update()
    $padre.Packages.Refresh(); return $p
}
function BuscarDiagrama($p, $n) {
    foreach ($d in $p.Diagrams) { if ($d.Name -eq $n) { return $d } }
    foreach ($s in $p.Packages) { $r = BuscarDiagrama $s $n; if ($r) { return $r } }
    return $null
}
function Poner($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l + $ancho);t=$t;b=$($t - $alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
    return $do
}
function Cerrar {
    $ea.CloseFile(); $ea.Exit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
    Start-Sleep -Milliseconds 1500
}

$root  = $ea.Models.GetAt(0)
$pRaiz = Get-OCrearPaquete $root 'Plataforma Médica Multi-Inquilino'
$pCap  = Get-OCrearPaquete $pRaiz 'CAP. 4 - Proceso de desarrollo'

if ($Rehacer) {
    for ($i = $pCap.Packages.Count - 1; $i -ge 0; $i--) {
        if ($pCap.Packages.GetAt($i).Name -eq $NOMBRE_PKG) {
            $pCap.Packages.DeleteAt($i, $false)
            Write-Output '  paquete anterior eliminado (-Rehacer)'
        }
    }
    $pCap.Packages.Refresh()
}

$pkg = Get-OCrearPaquete $pCap $NOMBRE_PKG

if (BuscarDiagrama $pkg $NOMBRE_DIA) {
    Write-Output "  $NOMBRE_DIA ya existe, no se toca"
    Cerrar; exit 0
}

$dia = $pkg.Diagrams.AddNew($NOMBRE_DIA, 'UseCase')
[void]$dia.Update(); $pkg.Diagrams.Refresh()

# ---- Actores --------------------------------------------------------------
$ACT = @{}
foreach ($a in $ACTORES) {
    $e = $pkg.Elements.AddNew($a.n, 'Actor')
    if ($a.abstracto) {
        $e.Abstract = '1'
        $e.Notes = 'Actor abstracto. Generaliza a los actores humanos: los casos de ' +
                   'uso de identidad los ejecutan todos por igual y asociarlos uno por ' +
                   'uno multiplicaría las líneas sin agregar información.'
    }
    [void]$e.Update()
    $ACT[$a.k] = $e.ElementID
}
$pkg.Elements.Refresh()

# ---- Casos de uso ---------------------------------------------------------
$U = @{}
foreach ($def in $CASOS) {
    $e = $pkg.Elements.AddNew($def.n, 'UseCase')
    if ($NOTAS.ContainsKey($def.k)) { $e.Notes = $NOTAS[$def.k] }
    [void]$e.Update()
    $U[$def.k] = @{ id = $e.ElementID; x = $COL[$def.c]; y = (FilaY $def.f) }
}
$pkg.Elements.Refresh()

# Se ubican despues de crear todo, releyendo cada elemento por su id: una
# referencia COM guardada antes de Elements.Refresh() devuelve ElementID 0 y
# el diagrama sale con las cajas sueltas (GUIA-DIAGRAMAS-EA, seccion 9).
foreach ($a in $ACTORES) {
    [void](Poner $dia $ea.GetElementByID($ACT[$a.k]) $a.x (FilaY $a.f) $ACT_W $ACT_H)
}
foreach ($k in $U.Keys) {
    [void](Poner $dia $ea.GetElementByID($U[$k].id) $U[$k].x $U[$k].y $CU_W $CU_H)
}

# ---- Asociaciones actor - caso de uso -------------------------------------
$nAsoc = 0
foreach ($k in $ASOCIACIONES.Keys) {
    $actor = $ea.GetElementByID($ACT[$k])
    foreach ($cu in $ASOCIACIONES[$k]) {
        $c = $actor.Connectors.AddNew('', 'Association')
        $c.SupplierID = $U[$cu].id
        [void]$c.Update()
        $nAsoc++
    }
}

# ---- Herencia entre actores -----------------------------------------------
foreach ($g in $GENERALIZACIONES) {
    $hijo = $ea.GetElementByID($ACT[$g.hijo])
    $c = $hijo.Connectors.AddNew('', 'Generalization')
    $c.SupplierID = $ACT[$g.padre]
    # Ortogonal: la linea sube por el corredor de su actor y cruza por la
    # franja de arriba, donde no hay casos de uso. En linea recta, las
    # generalizaciones de los actores de la derecha atravesaban el diagrama
    # en diagonal, por encima de las elipses.
    #
    # El estilo de la linea NO es del conector sino de su aparicion en cada
    # diagrama: vive en t_diagramlinks.Style. Connector.RouteStyle por COM no
    # cambia nada. Se crea la fila del enlace con su estilo puesto.
    [void]$c.Update()
    $lnk = $dia.DiagramLinks.AddNew('', '')
    $lnk.ConnectorID = $c.ConnectorID
    $lnk.Style = $ESTILO_GENERALIZACION
    [void]$lnk.Update()
}

# ---- include / extend -----------------------------------------------------
foreach ($x in $DEPENDENCIAS) {
    $de = $ea.GetElementByID($U[$x.de].id)
    $c = $de.Connectors.AddNew('', 'Dependency')
    $c.SupplierID   = $U[$x.a].id
    $c.Stereotype   = $x.tipo
    $c.StereotypeEx = $x.tipo
    [void]$c.Update()
}

$dia.DiagramObjects.Refresh()
Write-Output "  $NOMBRE_DIA : $($dia.DiagramObjects.Count) elementos"
Write-Output "  ($($ACTORES.Count) actores, $($CASOS.Count) casos de uso, $nAsoc asociaciones, $($DEPENDENCIAS.Count) include/extend)"

Cerrar
Write-Output 'OK'
