param(
    # Borra el paquete «Sprint 3 - Arquitectura» (solo tiene lo de este
    # script: el 2.1.1.1 y el 2.1.1.2) y lo rehace.
    [switch]$Rehacer,
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx')
)

# =========================================================================
# CAPITULO 4 - Sprint 3 - 2.1.1 Diseno de la arquitectura
#   2.1.1.1 Diagrama de capas
#   2.1.1.2 Diagrama de despliegue
#
# Reemplaza a ea-capas-sprint3.ps1 y ea-despliegue-sprint3.ps1 (01/11/26).
# Sigue la guia de VioletBoutique (GUIA-DIAGRAMAS-EA.md, 7.6, 7.7 y el anexo
# F, scripts/ea-p2-arquitectura.ps1), que trae las correcciones de la ing:
#
#   - Capas: la capa 3 es la «Capa intermedia» (el software sobre el que se
#     ejecuta cada aplicacion: Gunicorn, el ORM, serve, Flutter, el pooler,
#     PostgreSQL) y la capa 4 la «Capa de software» (el sistema sobre el que
#     corre: los contenedores Linux de Railway, Android, el sistema y el
#     navegador del cliente). Antes eran «servidores de desarrollo» y
#     «servidores en la nube», que es lo que muestra el despliegue.
#   - «Se tiene que poder rastrear lo de cada nodo»: cada elemento de las
#     capas 3 y 4 lleva como estereotipo el nodo del despliegue donde corre,
#     el MISMO color que ese nodo, y una relacion «trace» hacia el en el
#     modelo (EA la muestra en la ventana de trazabilidad; no se dibuja
#     porque el nodo no esta en ese diagrama).
#   - Despliegue: Railway construye cada servicio con Nixpacks (railway.json
#     y frontend/railway.json, builder NIXPACKS) y lo corre en un contenedor:
#     cada contenedor es un ExecutionEnvironment DENTRO del nodo, con lo que
#     corre adentro anidado. Los dos procesos en ciclo que lanza
#     scripts/start.sh corren en el contenedor, AL LADO de gunicorn, no
#     dentro. En desarrollo, docker-compose levanta pgvector/pgvector:pg16.
#   - Los servicios externos son Node «servicio externo», no «device»: no
#     son hardware nuestro.
#   - «manifest»: cada artefacto implementa su componente.
#
# Capas: «realiza» va de la capa 1 a la 2 A PROPOSITO (pedido de la catedra,
# guia 7.6); no corregirlo. Va una sola vez, entre los rotulos de las capas:
# los ocho paquetes implementados los realizan las tres aplicaciones, y
# dibujarlo paquete por paquete serian 24 lineas para decir lo mismo. Entre
# las capas 2, 3 y 4 las relaciones van elemento por elemento, que es lo
# que permite rastrear cada nodo.
#
# PowerShell de 64 bits (la segunda pasada usa ACE.OLEDB.16.0), EA cerrado.
# NO exporta imagenes. Probar primero con -Modelo apuntando a una copia.
# =========================================================================

$ErrorActionPreference = 'Stop'
$Modelo = [System.IO.Path]::GetFullPath($Modelo)
if (-not (Test-Path $Modelo)) { throw "No existe $Modelo" }
$PKG = 'Sprint 3 - Arquitectura'
$CAPAS_DIA = '2.1.1.1 Diagrama de Capas - Sprint 3'
$DESP_DIA  = '2.1.1.2 Diagrama de Despliegue - Sprint 3'

# Un color por nodo (BGR), el mismo en los dos diagramas: asi se rastrea.
$COLOR = @{
    CEL = 0xD8F0D8   # telefono Android (verde)
    CLI = 0xF7E4D2   # computadora con navegador (celeste)
    API = 0xCCE5FF   # Railway, contenedor del backend (naranja)
    WEB = 0xCCF5FF   # Railway, contenedor del frontend (amarillo)
    SB  = 0xF2DCEC   # Supabase (lila)
    DEV = 0xE6E6E6   # PC de desarrollo y GitHub (gris)
    EXT = 0xFFFFFF   # servicios externos
}

# =========================================================================
# 2.1.1.2 DESPLIEGUE. Cada nodo: k, nombre, tipo, estereotipo, padre, caja
# (l, t, ancho, alto), color, nota. El padre va antes que el hijo.
# =========================================================================
$NODOS = @(
    # ---- Clientes ----
    @{ k='dCEL'; n='Teléfono Android'; tipo='Device'; st='device'; c='CEL'; mult=$true
       box=@(380, -40, 520, 300); nota='El paciente con la aplicación móvil. Multiplicidad [*]: son muchos.' },
    @{ k='eAND'; n='Android · Flutter'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='dCEL'; c='CEL'
       box=@(410, -90, 460, 220); nota='La aplicación Flutter compilada para Android (minSdk = flutter.minSdkVersion).' },
    @{ k='aAPK'; n='app-release.apk'; tipo='Artifact'; st='artifact'; p='eAND'
       box=@(440, -150, 400, 50); nota='flutter build apk --release. La URL de la API queda dentro del binario; se publica como release de GitHub.' },
    @{ k='aSEC'; n='flutter_secure_storage · tokens JWT'; tipo='Artifact'; st='artifact'; p='eAND'
       box=@(440, -235, 400, 50); nota='El access y el refresh token, en el almacén cifrado de Android.' },

    @{ k='dPC'; n='Computadora del personal o del paciente'; tipo='Device'; st='device'; c='CLI'; mult=$true
       box=@(960, -40, 520, 300); nota='Recepción, médicos y administradores; también el paciente que reserva desde la web. Multiplicidad [*].' },
    @{ k='eNAV'; n='Navegador web (Chrome / Edge)'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='dPC'; c='CLI'
       box=@(990, -90, 460, 220); nota='Ejecuta la SPA de React que sirve Railway.' },

    # ---- Railway ----
    @{ k='dRW'; n='Servidor Railway · PaaS'; tipo='Device'; st='device'; c='API'
       box=@(380, -420, 1100, 440); nota='Dos servicios del proyecto, construidos por Nixpacks desde GitHub. Inyecta PORT.' },
    @{ k='eCAPI'; n='Contenedor backend · Nixpacks (Python 3.13)'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='dRW'; c='API'
       box=@(410, -470, 600, 370); nota='railway.json: builder NIXPACKS, startCommand bash scripts/start.sh (migra, collectstatic, lanza los dos procesos en ciclo y deja a gunicorn).' },
    @{ k='eGUN'; n='Gunicorn 23 · WSGI · 2 workers'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='eCAPI'; c='API'
       box=@(440, -520, 540, 130); nota='exec gunicorn config.wsgi:application, WEB_CONCURRENCY workers (2 por omisión). WhiteNoise sirve los estáticos de Django.' },
    @{ k='aWSGI'; n='config.wsgi:application · Django 5.2'; tipo='Artifact'; st='artifact'; p='eGUN'
       box=@(470, -570, 480, 50); nota='El backend: Django + DRF, las apps de backend/ y sus migraciones.' },
    @{ k='aREC'; n='send_appointment_reminders --loop'; tipo='Artifact'; st='artifact'; p='eCAPI'
       box=@(440, -680, 540, 50); nota='US-28. Una vuelta cada 15 minutos; cada ficha se marca al avisarla. Se apaga con APPOINTMENT_REMINDERS=off.' },
    @{ k='aBAK'; n='run_automatic_backups --loop'; tipo='Artifact'; st='artifact'; p='eCAPI'
       box=@(440, -750, 540, 50); nota='Copias automáticas (CG-6), una vuelta por hora, con candado por organización.' },
    @{ k='eCWEB'; n='Contenedor frontend · Nixpacks (Node 22)'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='dRW'; c='WEB'
       box=@(1040, -470, 410, 370); nota='frontend/railway.json: builder NIXPACKS; Node lo fija frontend/.nvmrc (22).' },
    @{ k='eSRV'; n='serve -s dist · servidor de estáticos'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='eCWEB'; c='WEB'
       box=@(1070, -520, 350, 130); nota='startCommand npx serve -s dist: sirve el bundle y reenvía las rutas al index.html.' },

    # ---- Servicios externos ----
    @{ k='xFCM'; n='Firebase Cloud Messaging'; tipo='Node'; st='servicio externo'; c='EXT'
       box=@(40, -420, 280, 90); nota='Nuevo en el Sprint 3 (US-28). La API le envía los avisos con la API HTTP v1 y la credencial de FIREBASE_CREDENTIALS; FCM los entrega al teléfono.' },
    @{ k='xSTR'; n='Stripe'; tipo='Node'; st='servicio externo'; c='EXT'
       box=@(1540, -420, 300, 90); nota='Pago en línea (US-18), modo prueba. Llama al webhook de la API.' },
    @{ k='xGEM'; n='Google Gemini'; tipo='Node'; st='servicio externo'; c='EXT'
       box=@(1540, -540, 300, 90); nota='El modelo del asistente (US-31 a US-34), por google-genai.' },
    @{ k='xBRE'; n='Brevo · correo transaccional'; tipo='Node'; st='servicio externo'; c='EXT'
       box=@(1540, -660, 300, 90); nota='Por django-anymail: recuperación de acceso, comprobantes, avisos de la ficha (US-28) y reportes.' },

    # ---- Supabase ----
    @{ k='dSB'; n='Servidor Supabase · AWS us-east-1'; tipo='Device'; st='device'; c='SB'
       box=@(380, -940, 600, 300); nota='La base de producción.' },
    @{ k='ePOOL'; n='Supavisor · session pooler :5432'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='dSB'; c='SB'
       box=@(410, -990, 540, 70); nota='La API se conecta por aws-0-<region>.pooler.supabase.com:5432 con el rol app_user (docs/entorno/supabase.md).' },
    @{ k='ePG'; n='PostgreSQL · pgvector'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='dSB'; c='SB'
       box=@(410, -1080, 540, 140); nota='Row Level Security forzado: el aislamiento entre organizaciones se hace cumplir acá.' },
    @{ k='aESQ'; n='esquema multi-inquilino · RLS'; tipo='Artifact'; st='artifact'; p='ePG'
       box=@(440, -1130, 480, 50); nota='Tablas, políticas tenant_isolation y funciones app_current_tenant / app_is_platform_admin. Lo crean las migraciones de Django.' },

    # ---- Desarrollo ----
    @{ k='dDEV'; n='PC de desarrollo · Windows 11'; tipo='Device'; st='device'; c='DEV'
       box=@(1040, -940, 620, 300); nota='La máquina de cada integrante.' },
    @{ k='eDCK'; n='Docker Desktop · docker-compose'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='dDEV'; c='DEV'
       box=@(1070, -990, 560, 160); nota='docker-compose.yml: solo el servicio db. El backend y la web corren fuera de Docker.' },
    @{ k='eCPG'; n='contenedor pgvector/pgvector:pg16 · :5432'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='eDCK'; c='DEV'
       box=@(1100, -1040, 500, 100); nota='plataforma_db, con healthcheck pg_isready y los scripts de backend/init-db.' },
    @{ k='aPGD'; n='volumen pgdata'; tipo='Artifact'; st='artifact'; p='eCPG'
       box=@(1130, -1080, 440, 45); nota='Los datos de la base local, que sobreviven al contenedor.' },
    @{ k='eRUN'; n='manage.py runserver · Vite dev server'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='dDEV'; c='DEV'
       box=@(1070, -1170, 560, 55); nota='En desarrollo: Python 3.13 con su entorno virtual y Node 22. gunicorn no corre en Windows.' },

    @{ k='dGH'; n='GitHub · plat_web_movil_medicos'; tipo='Device'; st='device'; c='DEV'
       box=@(1720, -940, 380, 160); nota='El origen desde el que Railway construye: no es un destino de despliegue.' },
    @{ k='aCFG'; n='railway.json + scripts/start.sh'; tipo='Artifact'; st='artifact'; p='dGH'
       box=@(1750, -1000, 320, 50); nota='Uno en la raíz (backend) y otro en frontend/.' }
)

# El bundle de React es uno solo desplegado en dos nodos: va afuera, con «deploy».
$AFUERA = @(
    @{ k='aBND'; n='dist/ · bundle de React 19 (Vite 8)'; box=@(1540, -40, 600, 60)
       nota='npm run build en frontend/. serve lo sirve y cada navegador lo ejecuta: por eso se dibuja una vez, con dos «deploy».' }
)
# Cada componente al lado de su artefacto, para que el «manifest» no cruce
# el diagrama.
$COMPONENTES = @(
    @{ k='cBE'; n='Backend · Django + DRF'; box=@(40, -580, 280, 60) },
    @{ k='cFE'; n='Frontend · React + Vite'; box=@(1850, -150, 290, 60) },
    @{ k='cMO'; n='Móvil · Flutter'; box=@(40, -150, 280, 60) }
)
$DEPLOY   = @(@('aBND','eNAV'), @('aBND','eSRV'))
$MANIFEST = @(@('aWSGI','cBE'), @('aBND','cFE'), @('aAPK','cMO'))
$CAMINOS  = @(
    @('dCEL','dRW','HTTPS 443 · REST + JWT'),
    @('dPC','dRW','HTTPS 443 · SPA y REST + JWT'),
    @('dRW','dSB','TCP 5432 · TLS · session pooler'),
    @('dRW','xFCM','HTTPS 443 · FCM HTTP v1'),
    @('xFCM','dCEL','push (FCM)'),
    @('dRW','xSTR','HTTPS 443 · Checkout + webhook'),
    @('dRW','xGEM','HTTPS 443'),
    @('dRW','xBRE','HTTPS 443 · API transaccional'),
    @('dGH','dRW','git push → build Nixpacks'),
    @('dDEV','dGH','git push')
)

# =========================================================================
# 2.1.1.1 CAPAS
# =========================================================================
# Capa 1: los paquetes del 3.10 del documento (figuras 3.2 a 3.11).
$CAPA1 = @(
    @{ n='Gestión Multi-Tenant' },
    @{ n='Usuarios y Seguridad' },
    @{ n='Gestión de Pacientes' },
    @{ n='Catálogo Médico y Agendas' },
    @{ n='Agendamiento y Compra de Fichas' },
    @{ n='Historia Clínica Digital' },
    @{ n='Notificaciones y Reportes' },
    @{ n='IA 1 · Chatbot de Orientación (RAG)' },
    @{ n='IA 2 · Predicción de Inasistencia'; pendiente=$true },
    @{ n='IA 3 · Generación de Resúmenes'; pendiente=$true }
)
# Las capas 2, 3 y 4 van en las mismas columnas (web, backend y base, movil,
# desarrollo): asi cada «se ejecuta en» y cada «corre sobre» baja derecho y
# ninguna linea cruza a otra.
$CAPA2 = @(
    @{ k='BE'; n='Backend · API REST (Django + DRF)'; x=900; w=720; cols=2
       nota='backend/. Python 3.13, Django 5.2, DRF, psycopg 3.'
       arts=@('config/settings.py', 'tenancy/middleware.py', 'appointments/counter.py', 'payments/services.py',
              'encounters/prescription_pdf.py', 'notifications/push.py', 'appointments/reminders.py',
              'appointments/kpis.py', 'reporting/datasets.py', 'assistant/booking_views.py') },
    @{ k='FE'; n='Frontend Web (React + Vite)'; x=380; w=480; cols=1
       nota='frontend/. React 19, Vite 8, TypeScript.'
       arts=@('src/App.tsx', 'src/api/cliente.ts', 'src/paginas/Mostrador.tsx', 'src/paginas/RecetaAtencion.tsx',
              'src/paginas/Kpis.tsx', 'src/paginas/Reportes.tsx') },
    @{ k='MO'; n='Aplicación Móvil (Flutter)'; x=1660; w=520; cols=1
       nota='mobile/. Flutter, http, firebase_messaging.'
       arts=@('lib/main.dart', 'lib/core/api/client.dart', 'lib/core/notifications/push.dart',
              'lib/features/assistant/assistant_screen.dart', 'lib/features/clinical_record/clinical_record_screen.dart', 'pubspec.yaml') }
)
# nodo: el del despliegue donde corre (estereotipo, color y «trace»).
$CAPA3 = @(
    @{ k='BRW';  n='Motor del navegador (ejecuta la SPA)';   nodo='eNAV';  c='CLI'; st='nodo: navegador';             de=@('FE') },
    @{ k='SRV';  n='serve · servidor de estáticos';          nodo='eSRV';  c='WEB'; st='nodo: Railway · frontend';    de=@('FE') },
    @{ k='GUN';  n='Gunicorn 23 + WhiteNoise';               nodo='eGUN';  c='API'; st='nodo: Railway · backend';     de=@('BE') },
    @{ k='ORM';  n='Django ORM + psycopg 3 + pgvector';      nodo='eCAPI'; c='API'; st='nodo: Railway · backend';     de=@('BE') },
    @{ k='POOL'; n='Supavisor · session pooler';             nodo='ePOOL'; c='SB';  st='nodo: Supabase';              de=@() },
    @{ k='PG';   n='PostgreSQL + pgvector + RLS';            nodo='ePG';   c='SB';  st='nodo: Supabase';              de=@() },
    @{ k='FLU';  n='Flutter + firebase_messaging';           nodo='eAND';  c='CEL'; st='nodo: teléfono';              de=@('MO') },
    @{ k='PGL';  n='PostgreSQL 16 + pgvector (pg16)';        nodo='eCPG';  c='DEV'; st='nodo: PC de desarrollo';      de=@() },
    @{ k='RUN';  n='runserver + Vite dev server';            nodo='eRUN';  c='DEV'; st='nodo: PC de desarrollo';      de=@() }
)
# Dentro de la capa intermedia: quien usa a quien (vecinos, sin cruzar nada).
$INTERMEDIA = @(@('ORM','POOL','se conecta a'), @('POOL','PG','reparte conexiones a'))
$CAPA4 = @(
    @{ k='OSC'; n='Windows / macOS + navegador';                nodo='dPC';  c='CLI'; st='nodo: computadora';       sobre=@('BRW') },
    @{ k='LNX'; n='Linux · contenedores de Railway (Nixpacks)'; nodo='dRW';  c='API'; st='nodo: Servidor Railway';  sobre=@('SRV','GUN','ORM') },
    @{ k='AWS'; n='Supabase · Linux en AWS us-east-1';          nodo='dSB';  c='SB';  st='nodo: Servidor Supabase'; sobre=@('POOL','PG') },
    @{ k='AND'; n='Android';                                    nodo='dCEL'; c='CEL'; st='nodo: Teléfono Android';  sobre=@('FLU') },
    @{ k='WIN'; n='Windows 11 + Docker Desktop';                nodo='dDEV'; c='DEV'; st='nodo: PC de desarrollo';  sobre=@('PGL','RUN') }
)

# =========================================================================
# EA por COM
# =========================================================================
$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($Modelo)) { throw "No se pudo abrir $Modelo" }
trap {
    try { $ea.CloseFile(); $ea.Exit() } catch { }
    throw $_
}
function Get-Paquete($padre, $nombre) {
    $padre.Packages.Refresh()
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    return $null
}
function Get-OCrear($padre, $nombre) {
    $p = Get-Paquete $padre $nombre
    if ($p) { return $p }
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update(); $padre.Packages.Refresh(); return $p
}
function Poner($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l + $ancho);t=$t;b=$($t - $alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}
function New-Rel($src, $dst, $tipo, $estereotipo, $nombre) {
    $c = $src.Connectors.AddNew($nombre, $tipo)
    $c.SupplierID = $dst.ElementID
    $c.Direction = 'Source -> Destination'
    if ($estereotipo) { $c.Stereotype = $estereotipo; $c.StereotypeEx = $estereotipo }
    [void]$c.Update()
    $src.Connectors.Refresh()
}

$root = $ea.Models.GetAt(0)
$pCap4 = Get-OCrear (Get-OCrear $root 'Plataforma Médica Multi-Inquilino') 'CAP. 4 - Proceso de desarrollo'
if ($Rehacer) {
    for ($i = $pCap4.Packages.Count - 1; $i -ge 0; $i--) {
        if ($pCap4.Packages.GetAt($i).Name -eq $PKG) { Write-Output "  se borra [$PKG]"; $pCap4.Packages.DeleteAt($i, $false) }
    }
    $pCap4.Packages.Refresh()
}
if (Get-Paquete $pCap4 $PKG) {
    Write-Output "  [$PKG] ya existe, no se toca (usar -Rehacer)"
    $ea.CloseFile(); $ea.Exit(); exit 0
}
$pkg = $pCap4.Packages.AddNew($PKG, 'Package'); [void]$pkg.Update(); $pCap4.Packages.Refresh()
function New-El($nombre, $tipo, $st, $nota) {
    $e = $pkg.Elements.AddNew($nombre, $tipo)
    if ($st) { $e.Stereotype = $st; $e.StereotypeEx = $st }
    if ($nota) { $e.Notes = $nota }
    [void]$e.Update(); return $e
}

# ---------------------------------------------------------- despliegue --
# Se crea primero: las capas 3 y 4 apuntan con «trace» a sus nodos.
$dDes = $pkg.Diagrams.AddNew($DESP_DIA, 'Deployment'); [void]$dDes.Update(); $pkg.Diagrams.Refresh()
$el = @{}; $padres = @(); $multip = @(); $nivel = @{}
foreach ($n in $NODOS) {
    $e = New-El $n.n $n.tipo $n.st $n.nota
    if ($n.c) { $e.SetAppearance(1, 0, $COLOR[$n.c]); [void]$e.Update() }
    $el[$n.k] = $e
    $nivel[$n.k] = if ($n.p) { $nivel[$n.p] + 1 } else { 0 }
    if ($n.p) { $padres += @{ h = $e.ElementID; p = $el[$n.p].ElementID } }
    if ($n.mult) { $multip += $e.ElementID }
    Poner $dDes $e $n.box[0] $n.box[1] $n.box[2] $n.box[3]
}
foreach ($a in $AFUERA) {
    $e = New-El $a.n 'Artifact' 'artifact' $a.nota
    $el[$a.k] = $e; $nivel[$a.k] = 9
    Poner $dDes $e $a.box[0] $a.box[1] $a.box[2] $a.box[3]
}
foreach ($c in $COMPONENTES) {
    $e = New-El $c.n 'Component' $null 'El componente que implementa el artefacto unido con «manifest».'
    $el[$c.k] = $e; $nivel[$c.k] = 9
    Poner $dDes $e $c.box[0] $c.box[1] $c.box[2] $c.box[3]
}
foreach ($r in $DEPLOY)   { New-Rel $el[$r[0]] $el[$r[1]] 'Deployment' 'deploy' '' }
foreach ($r in $MANIFEST) { New-Rel $el[$r[0]] $el[$r[1]] 'Manifest' 'manifest' '' }
foreach ($r in $CAMINOS)  { New-Rel $el[$r[0]] $el[$r[1]] 'CommunicationPath' $null $r[2] }
$ley = New-El '' 'Note' $null ("CÓMO SE LEE`r`n" +
    "«device» el hardware o el servicio contratado · «executionEnvironment» lo que corre adentro (el contenedor, Gunicorn, el navegador) · «artifact» el archivo que se despliega · «servicio externo» un servicio de terceros.`r`n" +
    "Línea sólida: camino de comunicación, rotulado con el protocolo. «deploy»: el artefacto corre en ese nodo. «manifest»: el artefacto implementa ese componente. [*]: hay muchos.`r`n" +
    "Cada color es un nodo: el diagrama de capas (2.1.1.1) usa los mismos colores.")
Poner $dDes $ley 380 -1280 1100 90
Write-Output "  $DESP_DIA : $($NODOS.Count + $AFUERA.Count + $COMPONENTES.Count) elementos, $($CAMINOS.Count) caminos"

# --------------------------------------------------------------- capas --
$dCap = $pkg.Diagrams.AddNew($CAPAS_DIA, 'Component'); [void]$dCap.Update(); $pkg.Diagrams.Refresh()
$Y = @{ 1 = -60; 2 = -330; 3 = -830; 4 = -1080 }
$rot = @{}
$titulos = @('Capa 1 · Vista de análisis', 'Capa 2 · Aplicaciones', 'Capa 3 · Capa intermedia', 'Capa 4 · Capa de software')
$notasRot = @('Los paquetes del 3.10: lo que el sistema hace, sin tecnología.',
              'Las tres aplicaciones, con sus archivos más característicos del Sprint 3.',
              'El software sobre el que se ejecuta cada aplicación.',
              'El sistema sobre el que corre ese software.')
for ($i = 1; $i -le 4; $i++) {
    $r = New-El $titulos[$i - 1] 'Package' 'capa' $notasRot[$i - 1]
    Poner $dCap $r 20 $Y[$i] 300 80; $rot[$i] = $r
}
$fila = 0; $col = 0
foreach ($m in $CAPA1) {
    $nota = if ($m.pendiente) { 'Sprint 4: todavía sin implementar, por eso ninguna aplicación lo realiza aún.' } else { 'Paquete del 3.10 del documento.' }
    $e = New-El $m.n 'Package' $null $nota
    if ($m.pendiente) { $e.SetAppearance(1, 0, 0xEEEEEE); [void]$e.Update() }
    Poner $dCap $e (380 + $col * 360) ($Y[1] - $fila * 100) 340 76
    $col++; if ($col -eq 5) { $col = 0; $fila++ }
}
$npend = New-El '' 'Note' $null 'En gris: IA 2 e IA 3 son del Sprint 4 y todavía no las realiza ninguna aplicación.'
Poner $dCap $npend 2200 -160 260 70
$c2 = @{}; $hijos = @{}
foreach ($b in $CAPA2) {
    $caja = New-El $b.n 'Package' $null $b.nota
    $filas = [math]::Ceiling($b.arts.Count / $b.cols)
    Poner $dCap $caja $b.x $Y[2] $b.w (70 + $filas * 55)
    $c2[$b.k] = $caja; $hijos[$caja.ElementID] = @()
    $anchoArt = if ($b.cols -eq 1) { $b.w - 40 } else { [int](($b.w - 60) / 2) }
    for ($i = 0; $i -lt $b.arts.Count; $i++) {
        $cc = $i % $b.cols; $ff = [math]::Floor($i / $b.cols)
        $a = New-El $b.arts[$i] 'Artifact' $null "Archivo de $($b.n)."
        Poner $dCap $a ($b.x + 20 + $cc * ($anchoArt + 20)) ($Y[2] - 50 - $ff * 55) $anchoArt 45
        $hijos[$caja.ElementID] += $a.ElementID
    }
}
$c3 = @{}; $x = 380
foreach ($s in $CAPA3) {
    $e = New-El $s.n 'Package' $s.st "Corre en el nodo '$($el[$s.nodo].Name)' del diagrama de despliegue (2.1.1.2)."
    $e.SetAppearance(1, 0, $COLOR[$s.c]); [void]$e.Update()
    Poner $dCap $e $x $Y[3] 230 90; $c3[$s.k] = $e; $x += 250
}
$c4 = @{}; $x = 380
foreach ($s in $CAPA4) {
    $e = New-El $s.n 'Package' $s.st "Es el nodo '$($el[$s.nodo].Name)' del diagrama de despliegue (2.1.1.2)."
    $e.SetAppearance(1, 0, $COLOR[$s.c]); [void]$e.Update()
    Poner $dCap $e $x $Y[4] 400 90; $c4[$s.k] = $e; $x += 450
}
$cuenta = @{ e = 0; s = 0; t = 0 }
New-Rel $rot[1] $rot[2] 'Realisation' 'realiza' ''
New-Rel $rot[2] $rot[3] 'Dependency' 'se ejecuta en' ''
New-Rel $rot[3] $rot[4] 'Dependency' 'corre sobre' ''
foreach ($s in $CAPA3) { foreach ($k in $s.de) { New-Rel $c2[$k] $c3[$s.k] 'Dependency' 'se ejecuta en' ''; $cuenta.e++ } }
foreach ($r in $INTERMEDIA) { New-Rel $c3[$r[0]] $c3[$r[1]] 'Dependency' $r[2] ''; $cuenta.e++ }
foreach ($s in $CAPA4) { foreach ($k in $s.sobre) { New-Rel $c3[$k] $c4[$s.k] 'Dependency' 'corre sobre' ''; $cuenta.s++ } }
# «trace» a su nodo del despliegue: queda en el modelo y no se dibuja.
foreach ($s in $CAPA3) { New-Rel $c3[$s.k] $el[$s.nodo] 'Abstraction' 'trace' ''; $cuenta.t++ }
foreach ($s in $CAPA4) { New-Rel $c4[$s.k] $el[$s.nodo] 'Abstraction' 'trace' ''; $cuenta.t++ }
$ley2 = New-El '' 'Note' $null ("Cada elemento de las capas 3 y 4 dice en su estereotipo en qué nodo del diagrama de despliegue (2.1.1.2) corre, tiene el mismo color que ese nodo y está unido a él con una relación «trace» en el modelo.`r`n" +
    "«realiza» va de la capa 1 a la 2 a propósito: así lo pide la cátedra y así se leen las tres relaciones hacia abajo.")
Poner $dCap $ley2 20 -1220 1100 70
Write-Output ("  {0} : «se ejecuta en» {1}, «corre sobre» {2}, «trace» {3}" -f $CAPAS_DIA, $cuenta.e, $cuenta.s, $cuenta.t)

$didDes = $dDes.DiagramID; $didCap = $dCap.DiagramID
# Los ID, antes de cerrar EA: despues los objetos COM ya no responden.
$idEl = @{}; foreach ($k in $el.Keys) { $idEl[$k] = $el[$k].ElementID }
$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Start-Sleep -Milliseconds 1500

# =========================================================================
# Segunda pasada por OLEDB (EA cerrado): lo que la API COM no deja hacer.
#   a) ParentID: la contencion real, no solo dibujada.
#   b) Multiplicity '*' de los clientes.
#   c) Orden Z: Sequence mas bajo = se dibuja encima. Cuanto mas adentro, mas arriba.
# =========================================================================
$cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$Modelo;")
$cn.Open()
function Exec($sql) { $c = $cn.CreateCommand(); $c.CommandText = $sql; return $c.ExecuteNonQuery() }
foreach ($r in $padres) { [void](Exec "UPDATE t_object SET ParentID = $($r.p) WHERE Object_ID = $($r.h)") }
if ($multip.Count) { [void](Exec "UPDATE t_object SET Multiplicity = '*' WHERE Object_ID IN ($($multip -join ','))") }
foreach ($k in $el.Keys) {
    $seq = 200 - 40 * [math]::Min($nivel[$k], 4)
    [void](Exec "UPDATE t_diagramobjects SET Sequence = $seq WHERE Diagram_ID = $didDes AND Object_ID = $($idEl[$k])")
}
foreach ($caja in $hijos.Keys) {
    [void](Exec "UPDATE t_diagramobjects SET Sequence = 100 WHERE Diagram_ID = $didCap AND Object_ID = $caja")
    foreach ($h in $hijos[$caja]) {
        [void](Exec "UPDATE t_object SET ParentID = $caja WHERE Object_ID = $h")
        [void](Exec "UPDATE t_diagramobjects SET Sequence = 2 WHERE Diagram_ID = $didCap AND Object_ID = $h")
    }
}
$cn.Close()
Write-Output "  $($padres.Count) contenciones, $($multip.Count) multiplicidades y el orden Z escritos"
Write-Output 'OK'
