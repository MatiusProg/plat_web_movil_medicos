param(
    # Borra el paquete de casos de uso y lo vuelve a generar.
    [switch]$Rehacer,
    # Crea el modelo desde la plantilla vacia. BORRA el .eapx existente.
    [switch]$Recrear
)

# =========================================================================
# CAPITULO 4 - Sprint 1 - punto 1.3 Contexto del Sistema
#   "Modelo de casos de uso estructurado"
#
# ---- QUE DIBUJA ----
#   Un unico diagrama con TODOS los casos de uso abordados hasta el Sprint 1
#   -los del Sprint 0 y los del Sprint 1- y todos sus actores. Incluye los
#   casos de uso que NO se llegaron a desarrollar (CU6, CU10 y CU11), porque
#   el modelo describe el alcance comprometido, no lo entregado: dejarlos
#   fuera haria que el diagrama contradijera al Sprint Backlog.
#
# ---- DE DONDE SALEN LOS DATOS ----
#   De la "3.9 Lista de casos de uso" del documento del proyecto, que es la
#   numeracion valida (CU1..CU46). OJO: docs/sprints/sprint-1/historias-de-
#   usuario.md numera "CU2 - Gestion de Roles y Permisos", y en el documento
#   ese caso es el CU5; CU2 es "Registro de Usuarios / Pacientes". Acá manda
#   el documento.
#
# ---- DECISIONES DE MODELADO, Y POR QUE ----
#   1. Actor abstracto "Usuario". CU1, CU3, CU4 y CU6 los ejecutan todos los
#      actores humanos. Sin el abstracto habria que dibujar cinco asociaciones
#      por cada uno de esos cuatro casos -veinte lineas- y el diagrama se
#      vuelve ilegible sin decir nada nuevo.
#   2. "Titular" generaliza a "Paciente": un titular es un paciente que ademas
#      administra familiares a cargo. Por eso solo se le asocia CU8; lo demas
#      lo hereda.
#   3. Se dibujan dos relaciones y solo dos, las dos verificables en el codigo
#      que ya existe:
#        - CU3 <<extend>> CU1  : recuperar la contrasenia extiende el inicio de
#          sesion en el punto "credenciales no validas".
#        - CU17 <<include>> CU16 : la busqueda de profesionales muestra el
#          proximo espacio disponible, que lo resuelve la disponibilidad
#          (US-16 punto c). Esta en catalog/search.py.
#      No se inventan mas: un include que nadie puede senalar en el codigo es
#      ruido en la defensa.
#   4. "Medico" se asocia a CU9 aunque el documento liste "Paciente" como actor
#      principal. Es lo que se construyo: el punto (g) de US-08 le da lectura
#      al profesional, y esa lectura queda en la bitacora.
#
# ADITIVO: abre el modelo y solo agrega lo que falta.
# =========================================================================

$ErrorActionPreference = 'Stop'

$modelo   = 'D:\UNI\Si2\PROYECTO_MEDICOS\docs\diagramas\PlataformaMedica.eapx'
$plantilla = 'C:\Program Files (x86)\Sparx Systems\EA Trial\EABase.eapx'

$NOMBRE_DIA = '1.3 Modelo de Casos de Uso Estructurado - Sprint 1'
$NOMBRE_PKG = 'Sprint 1 - Casos de Uso'

# ---- Constantes de dibujo -------------------------------------------------
#
# El trazado no es decorativo. En la primera version los ocho actores iban en
# una sola columna a la izquierda, y el Administrador de Organizacion -que
# inicia ocho casos de uso, todos de la columna derecha- cruzaba el diagrama
# entero ocho veces por encima de los demas. Ilegible.
#
# Ahora hay tres columnas: los actores de la cara del paciente a la izquierda,
# los casos de uso en el medio y los actores de administracion a la derecha,
# cada grupo pegado a los casos que inicia. "Usuario" va arriba y centrado
# porque de el bajan las cinco generalizaciones.
$ACT_W = 140; $ACT_H = 80
$CU_W  = 320; $CU_H  = 70;  $CU_PASO = 120
$CU_X1 = 360; $CU_X2 = 780
$Y0    = -220

# ---- Los datos ------------------------------------------------------------

# clave -> nombre. El orden es el de dibujo, de arriba hacia abajo.
$ACTORES = @(
    @{ k='usuario';    n='Usuario';                          abstracto=$true;  x=560;  y=-40   },
    @{ k='paciente';   n='Paciente';                         abstracto=$false; x=40;   y=-700  },
    @{ k='medico';     n='Médico';                           abstracto=$false; x=40;   y=-900  },
    @{ k='titular';    n='Titular';                          abstracto=$false; x=40;   y=-1120 },
    @{ k='recep';      n='Recepcionista';                    abstracto=$false; x=40;   y=-1330 },
    @{ k='adminorg';   n='Administrador de Organización';    abstracto=$false; x=1220; y=-460  },
    @{ k='superadmin'; n='Superadministrador de Plataforma'; abstracto=$false; x=1220; y=-1080 },
    @{ k='sistema';    n='Sistema';                          abstracto=$false; x=1220; y=-1330 }
)

# Columna izquierda: identidad y cara del paciente.
$CU_COL_A = @(
    @{ k='cu1';  n='CU1 Autenticación de Usuario' },
    @{ k='cu3';  n='CU3 Recuperación de Credenciales' },
    @{ k='cu4';  n='CU4 Terminación de Sesión' },
    @{ k='cu6';  n='CU6 Gestión de Perfil de Usuario' },
    @{ k='cu2';  n='CU2 Registro de Usuarios / Pacientes' },
    @{ k='cu16'; n='CU16 Consulta de Disponibilidad Médica' },
    @{ k='cu17'; n='CU17 Búsqueda de Profesionales' },
    @{ k='cu9';  n='CU9 Gestión de Antecedentes del Paciente' },
    @{ k='cu8';  n='CU8 Gestión de Pacientes Dependientes' },
    @{ k='cu10'; n='CU10 Búsqueda y Consulta de Pacientes' }
)

# Columna derecha: administracion del centro medico y de la plataforma.
$CU_COL_B = @(
    @{ k='cu5';  n='CU5 Gestión de Roles y Permisos' },
    @{ k='cu7';  n='CU7 Consulta de Bitácora de Auditoría' },
    @{ k='cu11'; n='CU11 Administración de Pacientes' },
    @{ k='cu12'; n='CU12 Gestión de Sucursales' },
    @{ k='cu13'; n='CU13 Gestión de Especialidades y Profesionales' },
    @{ k='cu14'; n='CU14 Gestión de Agendas Médicas' },
    @{ k='cu15'; n='CU15 Bloqueo de Agenda Médica' },
    @{ k='cu44'; n='CU44 Gestión de Organizaciones (Tenants)' },
    @{ k='cu45'; n='CU45 Gestión de Planes de Suscripción' },
    @{ k='cu46'; n='CU46 Supervisión y Aislamiento de Organizaciones' }
)

# Nota de cada caso de uso: sprint y estado. No se ve en el PNG (regla 8),
# pero queda en el modelo para quien lo abra en EA.
$NOTAS = @{
    cu1  = 'Sprint 0. Entregado.'
    cu2  = 'Sprint 0. Entregado (web); la pantalla móvil se completó en el Sprint 1.'
    cu4  = 'Sprint 0. Entregado.'
    cu44 = 'Sprint 0. Entregado.'
    cu45 = 'Sprint 0. Entregado.'
    cu46 = 'Sprint 0. Entregado.'
    cu5  = 'Arrastre del Sprint 0. Entregado en el Sprint 1.'
    cu3  = 'Sprint 1. Entregado.'
    cu6  = 'Sprint 1. NO desarrollado: US-05 quedó sin responsable y pasa al Sprint 2.'
    cu7  = 'Sprint 1. Entregado.'
    cu8  = 'Sprint 1. Entregado (sólo móvil).'
    cu9  = 'Sprint 1. Entregado: móvil, más el endpoint de lectura para el módulo de atención.'
    cu10 = 'Sprint 1. NO desarrollado: US-09 quedó sin responsable y pasa al Sprint 2.'
    cu11 = 'Sprint 1. NO desarrollado: US-10 quedó sin responsable y pasa al Sprint 2.'
    cu12 = 'Sprint 1. Backend entregado; el ABM web queda pendiente.'
    cu13 = 'Sprint 1. Backend entregado; el ABM web queda pendiente.'
    cu14 = 'Sprint 1. Entregado.'
    cu15 = 'Sprint 1. Entregado.'
    cu16 = 'Sprint 1. Entregado.'
    cu17 = 'Sprint 1. Entregado.'
}

# actor -> casos de uso que inicia.
$ASOCIACIONES = @{
    usuario    = @('cu1','cu3','cu4','cu6')
    paciente   = @('cu2','cu9','cu16','cu17')
    titular    = @('cu8')
    recep      = @('cu10')
    medico     = @('cu9')
    adminorg   = @('cu5','cu7','cu11','cu12','cu13','cu14','cu15','cu46')
    superadmin = @('cu44','cu45','cu46')
    sistema    = @('cu46')
}

# Herencia entre actores: del concreto al abstracto.
$GENERALIZACIONES = @(
    @{ hijo='paciente';   padre='usuario' },
    @{ hijo='recep';      padre='usuario' },
    @{ hijo='medico';     padre='usuario' },
    @{ hijo='adminorg';   padre='usuario' },
    @{ hijo='superadmin'; padre='usuario' },
    @{ hijo='titular';    padre='paciente' }
)

# =========================================================================
# PARTE 1 - Enterprise Architect por COM
# =========================================================================

if ($Recrear) {
    if (-not (Test-Path $plantilla)) { throw "No existe la plantilla $plantilla" }
    if (Test-Path $modelo) { Remove-Item $modelo -Force }
    Copy-Item $plantilla $modelo
    Write-Output "  modelo creado desde la plantilla"
}
if (-not (Test-Path $modelo)) {
    throw "No existe $modelo. Corré el script una primera vez con -Recrear."
}

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

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
    $ea.CloseFile(); $ea.Exit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
    exit 0
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
    $ACT[$a.k] = $e
    [void](Poner $dia $e $a.x $a.y $ACT_W $ACT_H)
}
$pkg.Elements.Refresh()

# ---- Casos de uso ---------------------------------------------------------
$U = @{}
foreach ($par in @(@{ col=$CU_COL_A; x=$CU_X1 }, @{ col=$CU_COL_B; x=$CU_X2 })) {
    $y = $Y0
    foreach ($def in $par.col) {
        $e = $pkg.Elements.AddNew($def.n, 'UseCase')
        if ($NOTAS.ContainsKey($def.k)) { $e.Notes = $NOTAS[$def.k] }
        # Sin ExtensionPoints a proposito: EA dibuja ese texto justo debajo de
        # la elipse de CU1, que es donde cae la etiqueta <<extend>> del conector,
        # y se pisan. El estereotipo ya dice lo que hay que decir.
        [void]$e.Update()
        $U[$def.k] = $e
        [void](Poner $dia $e $par.x $y $CU_W $CU_H)
        $y -= $CU_PASO
    }
}
$pkg.Elements.Refresh()

# ---- Asociaciones actor - caso de uso -------------------------------------
$nAsoc = 0
foreach ($k in $ASOCIACIONES.Keys) {
    foreach ($cu in $ASOCIACIONES[$k]) {
        $c = $ACT[$k].Connectors.AddNew('', 'Association')
        $c.SupplierID = $U[$cu].ElementID
        [void]$c.Update()
        $nAsoc++
    }
    $ACT[$k].Connectors.Refresh()
}

# ---- Herencia entre actores -----------------------------------------------
foreach ($g in $GENERALIZACIONES) {
    $c = $ACT[$g.hijo].Connectors.AddNew('', 'Generalization')
    $c.SupplierID = $ACT[$g.padre].ElementID
    [void]$c.Update()
    $ACT[$g.hijo].Connectors.Refresh()
}

# ---- include / extend -----------------------------------------------------
# extend: va DE la extension AL caso base.
$c = $U['cu3'].Connectors.AddNew('', 'Dependency')
$c.SupplierID   = $U['cu1'].ElementID
$c.Stereotype   = 'extend'
$c.StereotypeEx = 'extend'
[void]$c.Update(); $U['cu3'].Connectors.Refresh()

# include: va DEL que incluye AL incluido.
$c = $U['cu17'].Connectors.AddNew('', 'Dependency')
$c.SupplierID   = $U['cu16'].ElementID
$c.Stereotype   = 'include'
$c.StereotypeEx = 'include'
[void]$c.Update(); $U['cu17'].Connectors.Refresh()

$pkg.Elements.Refresh()
$dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()
Write-Output "  $NOMBRE_DIA : $($dia.DiagramObjects.Count) elementos, $($dia.DiagramLinks.Count) relaciones"
Write-Output "  ($($ACTORES.Count) actores, $($CU_COL_A.Count + $CU_COL_B.Count) casos de uso, $nAsoc asociaciones)"

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Start-Sleep -Milliseconds 1500

Write-Output 'OK'
