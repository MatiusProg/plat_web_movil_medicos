param(
    [switch]$Rehacer
)

# =========================================================================
# CAPITULO 4 - Sprint 1 - punto 2.1.1 Disenar la arquitectura
#   (a) DIAGRAMA DE CAPAS
#
# ---- QUE DIBUJA ----
#   Las cuatro capas del sistema, de arriba hacia abajo:
#     1. Vista de analisis   - los paquetes de negocio del documento
#     2. Aplicaciones        - backend, web y movil, con sus archivos mas
#                              caracteristicos adentro
#     3. Servidores locales  - el entorno de desarrollo del equipo
#     4. Servidores en la nube - donde vive el sistema publicado
#
# ---- DE DONDE SALEN LOS DATOS ----
#   Los diez paquetes de la capa 1 NO se inventan: son los del "3.10 Paquetes
#   y casos de uso" del documento, los mismos que rotulan las figuras 3.2 a
#   3.11. Reusarlos es lo que hace que el Capitulo 4 no contradiga al 3.
#   Las capas 2, 3 y 4 salen del repositorio y de docs/entorno/despliegue.md.
#
# ---- DECISIONES DE MODELADO, Y POR QUE ----
#   1. Cada capa tiene su propio elemento rotulo, a la izquierda, y las tres
#      relaciones van entre esos cuatro rotulos. La alternativa -unir cada
#      paquete de la capa 1 con cada aplicacion de la capa 2- serian treinta
#      lineas para decir lo mismo.
#   2. La direccion de <<realiza>> va de la capa 1 a la capa 2. En UML puro la
#      realizacion apunta del que implementa hacia lo realizado, o sea al
#      reves; se dibuja asi porque es como lo pide la catedra y porque de ese
#      modo las tres relaciones se leen todas hacia abajo. QUEDA ANOTADO PARA
#      QUE NADIE LO "CORRIJA" POR ERROR.
#   3. Las capas 3 y 4 son Package -la carpeta- porque asi lo pide la catedra
#      PARA ESTE DIAGRAMA. En el de despliegue esos mismos servidores son Node
#      con <<device>> y <<executionEnvironment>>; ahi la carpeta no vale.
#
# NO exporta imagenes: el acomodado final y la exportacion se hacen a mano.
# ADITIVO: abre el modelo y solo agrega lo que falta.
# =========================================================================

$ErrorActionPreference = 'Stop'

$modelo = 'D:\UNI\Si2\PROYECTO_MEDICOS\docs\diagramas\PlataformaMedica.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

$NOMBRE_DIA = '2.1.1a Diagrama de Capas - Sprint 1'
$NOMBRE_PKG = 'Sprint 1 - Arquitectura'

# ---- Constantes de dibujo -------------------------------------------------
$ROT_X = 40;  $ROT_W = 210; $ROT_H = 80
$CONT_X = 300

# ---- Los datos ------------------------------------------------------------

$CAPAS = @(
    @{ k='c1'; n='Capa 1 · Vista de análisis';       y=-90   },
    @{ k='c2'; n='Capa 2 · Aplicaciones';            y=-400  },
    @{ k='c3'; n='Capa 3 · Servidores de desarrollo'; y=-700 },
    @{ k='c4'; n='Capa 4 · Servidores en la nube';   y=-880  }
)

# Capa 1: los paquetes del punto 3.10 del documento.
$PAQUETES = @(
    'Gestión Multi-Tenant',
    'Usuarios y Seguridad',
    'Gestión de Pacientes',
    'Catálogo Médico y Agendas',
    'Agendamiento y Compra de Fichas',
    'Historia Clínica Digital',
    'Notificaciones y Reportes',
    'IA 1 · Chatbot de Orientación (RAG)',
    'IA 2 · Predicción de Inasistencia',
    'IA 3 · Generación de Resúmenes'
)

# Capa 2: una caja por aplicacion, con sus archivos mas caracteristicos.
$APLICACIONES = @(
    @{ k='backend'; n='Backend · API REST (Django + DRF)'; x=300;  archivos=@(
        'config/settings.py', 'tenancy/middleware.py',
        'accounts/authentication.py', 'audit/services.py') },
    @{ k='web';     n='Frontend Web (React + Vite)';       x=740;  archivos=@(
        'src/App.tsx', 'src/api/cliente.ts',
        'src/sesion/ContextoSesion.tsx') },
    @{ k='movil';   n='Aplicación Móvil (Flutter)';        x=1180; archivos=@(
        'lib/main.dart', 'lib/core/api/client.dart',
        'lib/core/session/session.dart') }
)

# Capa 3 y 4.
$LOCALES = @(
    @{ k='estacion'; n='Estación de desarrollo (Windows 11)'; x=300; ancho=520;
       nota='Python 3.13 con entorno virtual · Node 22 · Flutter SDK · Docker Desktop con PostgreSQL 16 (pgvector)' }
)
$NUBE = @(
    @{ k='railway';  n='Railway (PaaS)';   x=300; ancho=380;
       nota='Servicio del backend (gunicorn) y servicio del frontend estático.' },
    @{ k='supabase'; n='Supabase (DBaaS)'; x=740; ancho=380;
       nota='PostgreSQL 16 con Row Level Security, accedido por el session pooler.' }
)

# =========================================================================
# PARTE 1 - Enterprise Architect por COM
# =========================================================================

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

$dia = $pkg.Diagrams.AddNew($NOMBRE_DIA, 'Component')
[void]$dia.Update(); $pkg.Diagrams.Refresh()

# ---- Rotulos de capa ------------------------------------------------------
$ROT = @{}
foreach ($capa in $CAPAS) {
    $e = $pkg.Elements.AddNew($capa.n, 'Package')
    $e.Stereotype   = 'capa'
    $e.StereotypeEx = 'capa'
    [void]$e.Update()
    $ROT[$capa.k] = $e
    [void](Poner $dia $e $ROT_X $capa.y $ROT_W $ROT_H)
}

# ---- Capa 1: paquetes de analisis (dos filas de cinco) --------------------
$idsCapa1 = @()
$col = 0; $fila = 0
foreach ($nombre in $PAQUETES) {
    $e = $pkg.Elements.AddNew($nombre, 'Package')
    [void]$e.Update()
    $x = $CONT_X + ($col * 300)
    $y = -40 - ($fila * 110)
    [void](Poner $dia $e $x $y 280 80)
    $idsCapa1 += $e.ElementID
    $col++
    if ($col -ge 5) { $col = 0; $fila++ }
}

# ---- Capa 2: aplicaciones con sus archivos dentro -------------------------
$APP = @{}
$hijosPorCaja = @{}
foreach ($app in $APLICACIONES) {
    $caja = $pkg.Elements.AddNew($app.n, 'Package')
    [void]$caja.Update()
    $APP[$app.k] = $caja
    $altoCaja = 90 + ($app.archivos.Count * 45)
    [void](Poner $dia $caja $app.x -360 400 $altoCaja)

    $hijos = @()
    $yArch = -415
    foreach ($archivo in $app.archivos) {
        $a = $pkg.Elements.AddNew($archivo, 'Artifact')
        [void]$a.Update()
        [void](Poner $dia $a ($app.x + 30) $yArch 340 35)
        $hijos += $a.ElementID
        $yArch -= 45
    }
    $hijosPorCaja[$caja.ElementID] = $hijos
}

# ---- Capa 3 y capa 4 ------------------------------------------------------
foreach ($srv in ($LOCALES + $NUBE)) {
    $e = $pkg.Elements.AddNew($srv.n, 'Package')
    $e.Notes = $srv.nota
    [void]$e.Update()
    $y = if ($LOCALES.k -contains $srv.k) { -680 } else { -860 }
    [void](Poner $dia $e $srv.x $y $srv.ancho 100)
}

$pkg.Elements.Refresh()

# ---- Las tres relaciones, una por salto -----------------------------------
$c = $ROT['c1'].Connectors.AddNew('', 'Realisation')
$c.SupplierID   = $ROT['c2'].ElementID
$c.Stereotype   = 'realiza'
$c.StereotypeEx = 'realiza'
[void]$c.Update(); $ROT['c1'].Connectors.Refresh()

$c = $ROT['c2'].Connectors.AddNew('', 'Dependency')
$c.SupplierID   = $ROT['c3'].ElementID
$c.Stereotype   = 'ejecuta en'
$c.StereotypeEx = 'ejecuta en'
[void]$c.Update(); $ROT['c2'].Connectors.Refresh()

$c = $ROT['c3'].Connectors.AddNew('', 'Dependency')
$c.SupplierID   = $ROT['c4'].ElementID
$c.Stereotype   = 'despliega en'
$c.StereotypeEx = 'despliega en'
[void]$c.Update(); $ROT['c3'].Connectors.Refresh()

$dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()
Write-Output "  $NOMBRE_DIA : $($dia.DiagramObjects.Count) elementos, $($dia.DiagramLinks.Count) relaciones"

$didCom = $dia.DiagramID

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Start-Sleep -Milliseconds 1500

# =========================================================================
# PARTE 2 - Lo que la API COM no deja hacer
#   ParentID: que los archivos cuelguen de verdad de su caja. Asignarlo por
#   COM lanza NullReferenceException en EA 15.
#   Orden Z: si no, la caja tapa a los archivos que tiene dentro.
# =========================================================================

$cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$modelo;")
$cn.Open()
function Exec($sql) { $cmd = $cn.CreateCommand(); $cmd.CommandText = $sql; return $cmd.ExecuteNonQuery() }

foreach ($idCaja in $hijosPorCaja.Keys) {
    $hijos = $hijosPorCaja[$idCaja]
    if ($hijos.Count -eq 0) { continue }
    $lista = $hijos -join ','
    [void](Exec "UPDATE t_object SET ParentID = $idCaja WHERE Object_ID IN ($lista)")

    $z = 2
    foreach ($idHijo in $hijos) {
        [void](Exec "UPDATE t_diagramobjects SET Sequence = $z WHERE Diagram_ID = $didCom AND Object_ID = $idHijo")
        $z++
    }
    [void](Exec "UPDATE t_diagramobjects SET Sequence = 100 WHERE Diagram_ID = $didCom AND Object_ID = $idCaja")
}

$cn.Close()
Write-Output '  contención y orden Z aplicados'
Write-Output 'OK'
