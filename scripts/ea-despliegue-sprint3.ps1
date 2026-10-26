param(
    [switch]$Rehacer
)

# =========================================================================
# CAPITULO 4 - Sprint 3 - punto 2.1.1.2 Diagrama de despliegue
#   El del Sprint 1 (ea-despliegue-2-1-1.ps1) con lo que cambio en el
#   Sprint 3: dentro del mismo gunicorn de Railway corren, lanzados por
#   scripts/start.sh, los procesos en ciclo de recordatorios (US-28) y de
#   copias automaticas; y aparecen los nodos externos: Firebase Cloud
#   Messaging (nuevo), Stripe, Google Gemini y Brevo.
#
# ---- QUE DIBUJA ----
#   Donde corre cada pieza del sistema desplegado y por que protocolo se
#   hablan. Sale de docs/entorno/despliegue.md y de lo verificado en vivo
#   contra Railway y Supabase.
#
# ---- LOS CINCO ERRORES QUE ESTE DIAGRAMA EVITA A PROPOSITO ----
#   Un diagrama de despliegue casi siempre termina siendo uno de componentes
#   con iconos de computadora. Acá:
#
#   1. Los servidores son Node de verdad, y se distingue <<device>> -el
#      hardware o el servicio contratado- de <<executionEnvironment>> -el
#      runtime que corre dentro-. No son Package ni Component.
#   2. Dentro de un nodo NO van componentes: eso es UML 1.x. Lo que se
#      despliega es un ARTEFACTO -el archivo: la APK, el bundle compilado, la
#      aplicacion WSGI, el esquema de la base-.
#   3. Los nodos se unen con CommunicationPath -linea solida, sin punta-, y el
#      protocolo va como NOMBRE del conector. No con Dependency.
#   4. Los clientes llevan multiplicidad [*]: hay muchos telefonos y muchas
#      estaciones, no uno de cada uno.
#   5. El bundle del frontend es UN artefacto desplegado en DOS nodos -lo
#      sirve Railway y lo ejecuta el navegador-, asi que se dibuja una sola vez
#      y se le sacan dos flechas <<deploy>>. Lo demas, que vive en un solo
#      lugar, va dibujado DENTRO de su nodo. Las dos notaciones son validas y
#      mezclarlas con criterio es lo correcto.
#
#   Lleva ademas una nota de leyenda: es el diagrama que mas gente lee mal.
#
# NO exporta imagenes: el acomodado final y la exportacion se hacen a mano.
# ADITIVO: abre el modelo y solo agrega lo que falta.
# =========================================================================

$ErrorActionPreference = 'Stop'

$modelo = 'D:\UNI\Si2\PROYECTO_MEDICOS\docs\diagramas\PlataformaMedica.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

$NOMBRE_DIA = '2.1.1.2 Diagrama de Despliegue - Sprint 3'
$NOMBRE_PKG = 'Sprint 3 - Arquitectura'

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
function BuscarPaquete($p, $n) {
    foreach ($s in $p.Packages) { if ($s.Name -eq $n) { return $s }; $r = BuscarPaquete $s $n; if ($r) { return $r } }
    return $null
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
function NuevoElemento($paquete, $nombre, $tipo, $estereotipo, $notas) {
    $e = $paquete.Elements.AddNew($nombre, $tipo)
    if ($estereotipo) { $e.Stereotype = $estereotipo; $e.StereotypeEx = $estereotipo }
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update()
    return $e
}

$root  = $ea.Models.GetAt(0)
$pRaiz = Get-OCrearPaquete $root 'Plataforma Médica Multi-Inquilino'
$pCap  = Get-OCrearPaquete $pRaiz 'CAP. 4 - Proceso de desarrollo'
$pkg   = Get-OCrearPaquete $pCap $NOMBRE_PKG

if ($Rehacer) {
    $d = BuscarDiagrama $pkg $NOMBRE_DIA
    if ($d) {
        for ($i = $pkg.Diagrams.Count - 1; $i -ge 0; $i--) {
            if ($pkg.Diagrams.GetAt($i).Name -eq $NOMBRE_DIA) { $pkg.Diagrams.DeleteAt($i, $false) }
        }
        $pkg.Diagrams.Refresh()
        Write-Output '  diagrama anterior eliminado (-Rehacer)'
        # Los elementos del despliegue quedan en el paquete; se borran por
        # nombre para no arrastrar los del diagrama de capas.
        $suyos = @('Teléfono del paciente','Estación del personal','Railway · PaaS',
                   'Supabase · DBaaS','Android 8 o superior','Navegador web',
                   'Gunicorn · Python 3.13','Node 22 · servidor de estáticos',
                   'PostgreSQL 16 · pgvector','app-release.apk',
                   'plataforma-medica · aplicación WSGI','esquema multi-inquilino · RLS',
                   'dist/ · bundle de React','Leyenda','Firebase Cloud Messaging','Stripe','Google Gemini','Brevo',
                   'send_appointment_reminders --loop','run_automatic_backups --loop')
        for ($i = $pkg.Elements.Count - 1; $i -ge 0; $i--) {
            if ($suyos -contains $pkg.Elements.GetAt($i).Name) { $pkg.Elements.DeleteAt($i, $false) }
        }
        $pkg.Elements.Refresh()
    }
}

if (BuscarDiagrama $pkg $NOMBRE_DIA) {
    Write-Output "  $NOMBRE_DIA ya existe, no se toca"
    $ea.CloseFile(); $ea.Exit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
    exit 0
}

$dia = $pkg.Diagrams.AddNew($NOMBRE_DIA, 'Deployment')
[void]$dia.Update(); $pkg.Diagrams.Refresh()

# ---- Nodos: dispositivos y entornos de ejecucion --------------------------

$telefono = NuevoElemento $pkg 'Teléfono del paciente' 'Device' 'device' `
    'Dispositivo del paciente. Multiplicidad [*]: son muchos, no uno.'
[void](Poner $dia $telefono 40 -60 340 260)

$android = NuevoElemento $pkg 'Android 8 o superior' 'ExecutionEnvironment' 'executionEnvironment' $null
[void](Poner $dia $android 70 -110 280 180)

$estacion = NuevoElemento $pkg 'Estación del personal' 'Device' 'device' `
    'Computadora del personal del centro médico. Multiplicidad [*].'
[void](Poner $dia $estacion 440 -60 340 260)

$navegador = NuevoElemento $pkg 'Navegador web' 'ExecutionEnvironment' 'executionEnvironment' $null
[void](Poner $dia $navegador 470 -110 280 180)

$railway = NuevoElemento $pkg 'Railway · PaaS' 'Device' 'device' `
    'Plataforma como servicio. Corre dos servicios del proyecto.'
[void](Poner $dia $railway 900 -60 460 500)

$gunicorn = NuevoElemento $pkg 'Gunicorn · Python 3.13' 'ExecutionEnvironment' 'executionEnvironment' `
    'Servicio del backend. Arranca con scripts/start.sh, que aplica las migraciones en cada arranque.'
[void](Poner $dia $gunicorn 930 -110 400 250)

$nodo = NuevoElemento $pkg 'Node 22 · servidor de estáticos' 'ExecutionEnvironment' 'executionEnvironment' `
    'Servicio del frontend: sirve el bundle ya compilado.'
[void](Poner $dia $nodo 930 -390 400 130)

$supabase = NuevoElemento $pkg 'Supabase · DBaaS' 'Device' 'device' `
    'Base de datos como servicio, región us-east-1.'
[void](Poner $dia $supabase 900 -640 460 200)

$postgres = NuevoElemento $pkg 'PostgreSQL 16 · pgvector' 'ExecutionEnvironment' 'executionEnvironment' `
    'El aislamiento entre organizaciones se hace cumplir acá, con Row Level Security forzado.'
[void](Poner $dia $postgres 930 -690 400 120)

# ---- Artefactos -----------------------------------------------------------
# Dentro de su nodo los que viven en un solo lugar.

$apk = NuevoElemento $pkg 'app-release.apk' 'Artifact' 'artifact' `
    'Aplicación Flutter compilada. La URL de la API queda dentro del binario.'
[void](Poner $dia $apk 100 -170 220 45)

$wsgi = NuevoElemento $pkg 'plataforma-medica · aplicación WSGI' 'Artifact' 'artifact' `
    'El backend Django: config.wsgi:application.'
[void](Poner $dia $wsgi 960 -170 340 45)

$esquema = NuevoElemento $pkg 'esquema multi-inquilino · RLS' 'Artifact' 'artifact' `
    'Tablas, políticas tenant_isolation y funciones app_current_tenant / app_is_platform_admin.'
[void](Poner $dia $esquema 960 -750 340 45)

# Sprint 3: los procesos en ciclo que start.sh lanza junto con gunicorn.
$recordatorios = NuevoElemento $pkg 'send_appointment_reminders --loop' 'Artifact' 'artifact' `
    'US-28. Una vuelta cada 15 minutos; cada ficha se marca al avisarla (reminder_sent_at). Se apaga con APPOINTMENT_REMINDERS=off.'
[void](Poner $dia $recordatorios 960 -225 340 45)
$copias = NuevoElemento $pkg 'run_automatic_backups --loop' 'Artifact' 'artifact' `
    'Copias automáticas (CG-6), una vuelta por hora.'
[void](Poner $dia $copias 960 -280 340 45)

# Sprint 3: los servicios externos. FCM es el nuevo.
$fcm = NuevoElemento $pkg 'Firebase Cloud Messaging' 'Device' 'device' `
    'Nuevo en el Sprint 3 (US-28). La API le envía los avisos con la API HTTP v1 y la credencial de servicio en FIREBASE_CREDENTIALS.'
[void](Poner $dia $fcm 1500 -60 320 90)
$stripe = NuevoElemento $pkg 'Stripe' 'Device' 'device' 'Pago en línea (US-18), modo prueba. Llama al webhook de la API.'
[void](Poner $dia $stripe 1500 -200 320 90)
$gemini = NuevoElemento $pkg 'Google Gemini' 'Device' 'device' 'Modelo del asistente (US-31, US-32, US-33).'
[void](Poner $dia $gemini 1500 -340 320 90)
$brevo = NuevoElemento $pkg 'Brevo' 'Device' 'device' 'Correo transaccional por API: recuperación, comprobantes, avisos de la ficha (US-28) y reportes.'
[void](Poner $dia $brevo 1500 -480 320 90)

# Fuera, con dos flechas <<deploy>>: es UN bundle desplegado en DOS nodos.
$bundle = NuevoElemento $pkg 'dist/ · bundle de React' 'Artifact' 'artifact' `
    'Un único artefacto: Railway lo sirve y el navegador lo ejecuta. Por eso se dibuja una vez y se le sacan dos <<deploy>>.'
[void](Poner $dia $bundle 440 -420 320 50)

$cDeploy1 = $bundle.Connectors.AddNew('', 'Deployment')
$cDeploy1.SupplierID = $nodo.ElementID
$cDeploy1.Stereotype = 'deploy'; $cDeploy1.StereotypeEx = 'deploy'
[void]$cDeploy1.Update()

$cDeploy2 = $bundle.Connectors.AddNew('', 'Deployment')
$cDeploy2.SupplierID = $navegador.ElementID
$cDeploy2.Stereotype = 'deploy'; $cDeploy2.StereotypeEx = 'deploy'
[void]$cDeploy2.Update()
$bundle.Connectors.Refresh()

# ---- Caminos de comunicacion: el protocolo va como NOMBRE -----------------
$rutas = @(
    @{ de=$telefono; a=$railway;  n='HTTPS · REST + JWT' },
    @{ de=$estacion; a=$railway;  n='HTTPS · REST + JWT' },
    @{ de=$railway;  a=$supabase; n='PostgreSQL · session pooler (TLS, 5432)' },
    @{ de=$railway;  a=$fcm;      n='HTTPS · FCM API HTTP v1' },
    @{ de=$fcm;      a=$telefono; n='push (FCM)' },
    @{ de=$railway;  a=$stripe;   n='HTTPS · Checkout + webhook' },
    @{ de=$railway;  a=$gemini;   n='HTTPS · API de Gemini' },
    @{ de=$railway;  a=$brevo;    n='HTTPS · API transaccional' }
)
foreach ($r in $rutas) {
    $c = $r.de.Connectors.AddNew($r.n, 'CommunicationPath')
    $c.SupplierID = $r.a.ElementID
    [void]$c.Update()
    $r.de.Connectors.Refresh()
}

# ---- Leyenda --------------------------------------------------------------
$leyenda = $pkg.Elements.AddNew('Leyenda', 'Note')
$leyenda.Notes = @'
<<device>>                 hardware o servicio contratado donde algo corre.
<<executionEnvironment>>   el runtime que corre DENTRO de un dispositivo.
«artifact»                 el archivo que se despliega: APK, bundle, WSGI, esquema.
<<deploy>>                 flecha punteada: ese artefacto se instala en ese nodo.
línea sólida sin punta     camino de comunicación; el rótulo es el protocolo.
[*]                        hay muchas instancias de ese dispositivo, no una.
'@
[void]$leyenda.Update()
[void](Poner $dia $leyenda 40 -520 700 160)

$pkg.Elements.Refresh()
$dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()
Write-Output "  $NOMBRE_DIA : $($dia.DiagramObjects.Count) elementos, $($dia.DiagramLinks.Count) relaciones"

# IDs que necesita la PARTE 2, guardados ANTES de cerrar.
$did      = $dia.DiagramID
$idsMult  = @($telefono.ElementID, $estacion.ElementID) -join ','
$contiene = @(
    @{ padre=$telefono.ElementID; hijos=@($android.ElementID) },
    @{ padre=$estacion.ElementID; hijos=@($navegador.ElementID) },
    @{ padre=$railway.ElementID;  hijos=@($gunicorn.ElementID, $nodo.ElementID) },
    @{ padre=$supabase.ElementID; hijos=@($postgres.ElementID) },
    @{ padre=$android.ElementID;  hijos=@($apk.ElementID) },
    @{ padre=$gunicorn.ElementID; hijos=@($wsgi.ElementID, $recordatorios.ElementID, $copias.ElementID) },
    @{ padre=$postgres.ElementID; hijos=@($esquema.ElementID) }
)
$idsArtefactos = @($apk.ElementID, $wsgi.ElementID, $recordatorios.ElementID, $copias.ElementID, $esquema.ElementID, $bundle.ElementID)
$idsEntornos   = @($android.ElementID, $navegador.ElementID, $gunicorn.ElementID, $nodo.ElementID, $postgres.ElementID)
$idsDisp       = @($telefono.ElementID, $estacion.ElementID, $railway.ElementID, $supabase.ElementID, $fcm.ElementID, $stripe.ElementID, $gemini.ElementID, $brevo.ElementID)

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Start-Sleep -Milliseconds 1500

# =========================================================================
# PARTE 2 - Contencion real, multiplicidad y orden Z
# =========================================================================

$cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$modelo;")
$cn.Open()
function Exec($sql) { $cmd = $cn.CreateCommand(); $cmd.CommandText = $sql; return $cmd.ExecuteNonQuery() }

# Contencion: estar dibujado encima no es pertenecer. Al mover el nodo, los
# hijos se quedarian atras.
foreach ($rel in $contiene) {
    $lista = $rel.hijos -join ','
    [void](Exec "UPDATE t_object SET ParentID = $($rel.padre) WHERE Object_ID IN ($lista)")
}

# Multiplicidad de los clientes.
[void](Exec "UPDATE t_object SET Multiplicity = '*' WHERE Object_ID IN ($idsMult)")

# Orden Z en tres niveles: mas bajo = mas al frente.
$z = 2
foreach ($id in $idsArtefactos) {
    [void](Exec "UPDATE t_diagramobjects SET Sequence = $z WHERE Diagram_ID = $did AND Object_ID = $id"); $z++
}
foreach ($id in $idsEntornos) {
    [void](Exec "UPDATE t_diagramobjects SET Sequence = 100 WHERE Diagram_ID = $did AND Object_ID = $id")
}
foreach ($id in $idsDisp) {
    [void](Exec "UPDATE t_diagramobjects SET Sequence = 200 WHERE Diagram_ID = $did AND Object_ID = $id")
}

$cn.Close()
Write-Output '  contención, multiplicidad [*] y orden Z aplicados'
Write-Output 'OK'
