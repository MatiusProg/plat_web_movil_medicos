param(
    [switch]$Rehacer
)

# =========================================================================
# CAPITULO 3 - punto 3.10 Paquetes y casos de uso
#   (a) DIAGRAMA DE PAQUETES
#
# ---- POR QUE ESTE NO SIGUE LA GUIA ----
#   La receta de la guia (su punto 2.4) dibuja las clases DENTRO de cada
#   paquete para mostrar cohesion, y usa conectores Usage <<use>> para el
#   acoplamiento. Las dos cosas se apartan de la notacion UML y por eso se
#   corrigieron:
#
#   1. NO HAY NOTACION DISTINTA PARA COHESION Y ACOPLAMIENTO. La referencia
#      de UML lista exactamente tres relaciones entre paquetes -import,
#      access y merge- y las TRES son la misma linea: flecha punteada con
#      punta abierta, distinguidas solo por la palabra clave. La cohesion no
#      es una flecha: es una propiedad que se evalua mirando que quedo dentro
#      de cada paquete, y se discute en el texto, no en el dibujo.
#      Fuente: https://www.uml-diagrams.org/package-diagrams-reference.html
#
#   2. LOS PAQUETES VAN VACIOS. Este diagrama responde "que paquetes hay y
#      cual depende de cual". Meterle las clases adentro lo convierte en otro
#      diagrama -uno de clases agrupado- y tapa lo unico que aca importa, que
#      son las flechas.
#
#   3. SE MODELAN LOS DIEZ, no solo los del sprint en curso: el diagrama
#      describe la arquitectura del sistema completo, y son los mismos diez
#      que rotulan las figuras 3.2 a 3.11 del documento.
#
#   Se usa Dependency sin estereotipo: es la relacion generica, se dibuja
#   punteada con punta abierta, y es lo que corresponde cuando lo que se
#   quiere decir es "este paquete depende de aquel" sin afirmar nada sobre
#   espacios de nombres (que es lo que significan <<import>> y <<access>>).
#
# ---- DE DONDE SALEN LAS FLECHAS ----
#   Las de los cuatro paquetes ya construidos NO se inventaron: se midieron
#   sobre el codigo, contando los imports entre las aplicaciones Django que
#   componen cada paquete. Las de los paquetes que todavia no existen salen
#   del alcance declarado en el Capitulo 3.
#
#   OJO, DOS CICLOS REALES:
#     P1 <-> P2  tenancy/services.py crea el primer administrador y clona las
#                plantillas de rol al dar de alta una organizacion, y accounts
#                depende de tenancy para el contexto de inquilino.
#     P2 <-> P3  accounts/serializers/registration.py crea la ficha de
#                paciente junto con la cuenta, y patients depende de accounts
#                y de la bitacora.
#   Se dibujan las dos direcciones porque es lo que hay. Si el equipo prefiere
#   un diagrama en capas estrictas, hay que romper los ciclos en el codigo
#   primero; maquillarlos en el dibujo seria documentar algo que no existe.
#
# NO exporta imagenes.
# ADITIVO: abre el modelo y solo agrega lo que falta.
# =========================================================================

$ErrorActionPreference = 'Stop'

$modelo = 'D:\UNI\Si2\PROYECTO_MEDICOS\docs\diagramas\PlataformaMedica.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

$NOMBRE_DIA = '3.10a Diagrama de Paquetes'
$NOMBRE_PKG = '3.10 Paquetes y casos de uso'

# ---- Constantes de dibujo -------------------------------------------------
$P_W = 280; $P_H = 80; $PASO_X = 320; $PASO_Y = 150

# ---- Los datos ------------------------------------------------------------
# Cada fila del dibujo. Arriba los que no dependen de nadie; abajo los que
# dependen. Asi las flechas apuntan siempre hacia arriba.
$FILAS = @(
    @(@{ k='p1';  n='Gestión Multi-Tenant' }),
    @(@{ k='p2';  n='Usuarios y Seguridad' }),
    @(@{ k='p3';  n='Gestión de Pacientes' },
      @{ k='p4';  n='Catálogo Médico y Agendas' }),
    @(@{ k='p5';  n='Agendamiento y Compra de Fichas' }),
    @(@{ k='p6';  n='Historia Clínica Digital' },
      @{ k='p7';  n='Notificaciones y Reportes' }),
    @(@{ k='p8';  n='IA 1 · Chatbot de Orientación (RAG)' },
      @{ k='p9';  n='IA 2 · Predicción de Inasistencia' },
      @{ k='p10'; n='IA 3 · Generación de Resúmenes' })
)

$NOTAS = @{
    p1  = 'Organizaciones, planes, suscripciones y el contexto de inquilino. Aplicación Django: tenancy.'
    p2  = 'Usuarios, roles, permisos, autenticación y bitácora de auditoría. Aplicaciones: accounts y audit.'
    p3  = 'Pacientes, familiares a cargo y antecedentes declarados. Aplicación: patients.'
    p4  = 'Sucursales, especialidades, profesionales, agendas y disponibilidad. Aplicaciones: catalog y scheduling.'
    p5  = 'Reserva, pago y comprobante de la ficha médica. Sprint 2.'
    p6  = 'Registro de la atención, recetas e historia clínica. Sprint 3.'
    p7  = 'Recordatorios, avisos e indicadores de gestión. Sprint 3.'
    p8  = 'Chatbot de orientación con recuperación aumentada sobre el catálogo de especialidades. Sprint 4.'
    p9  = 'Predicción de riesgo de inasistencia sobre el historial de fichas. Sprint 4.'
    p10 = 'Generación de resúmenes de consulta y de historia clínica. Sprint 4.'
}

# cliente -> proveedores. El cliente es el que depende.
$DEPENDE_DE = @{
    p1  = @('p2')                    # medido: tenancy/services.py
    p2  = @('p1','p3')               # medido: accounts -> tenancy, -> patients
    p3  = @('p2','p4')               # medido: patients -> audit/accounts, -> catalog
    p4  = @('p1','p2')               # medido: catalog -> tenancy; FK a accounts.User
    p5  = @('p2','p3','p4')          # alcance del Sprint 2
    p6  = @('p2','p3','p5')          # alcance del Sprint 3
    p7  = @('p3','p5')               # alcance del Sprint 3
    p8  = @('p4','p5')               # alcance del Sprint 4
    p9  = @('p3','p5')               # alcance del Sprint 4
    p10 = @('p6')                    # alcance del Sprint 4
}

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
$pCap  = Get-OCrearPaquete $pRaiz 'CAP. 3 - Requerimientos'

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

$dia = $pkg.Diagrams.AddNew($NOMBRE_DIA, 'Package')
[void]$dia.Update(); $pkg.Diagrams.Refresh()

# ---- Los diez paquetes, vacios --------------------------------------------
# El ancho de la fila mas ancha, para centrar las demas contra ella.
$maxCols = 0
foreach ($fila in $FILAS) { if ($fila.Count -gt $maxCols) { $maxCols = $fila.Count } }
$anchoTotal = ($maxCols * $PASO_X) - ($PASO_X - $P_W)

$PAQ = @{}
$y = -60
foreach ($fila in $FILAS) {
    $anchoFila = ($fila.Count * $PASO_X) - ($PASO_X - $P_W)
    $x = 40 + [int](($anchoTotal - $anchoFila) / 2)
    foreach ($def in $fila) {
        $e = $pkg.Elements.AddNew($def.n, 'Package')
        $e.Notes = $NOTAS[$def.k]
        [void]$e.Update()
        $PAQ[$def.k] = $e
        [void](Poner $dia $e $x $y $P_W $P_H)
        $x += $PASO_X
    }
    $y -= $PASO_Y
}
$pkg.Elements.Refresh()

# ---- Las dependencias: flecha punteada, punta abierta, sin estereotipo ----
$n = 0
foreach ($cliente in $DEPENDE_DE.Keys) {
    foreach ($proveedor in $DEPENDE_DE[$cliente]) {
        $c = $PAQ[$cliente].Connectors.AddNew('', 'Dependency')
        $c.SupplierID = $PAQ[$proveedor].ElementID
        [void]$c.Update()
        $n++
    }
    $PAQ[$cliente].Connectors.Refresh()
}

$dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()
Write-Output "  $NOMBRE_DIA : $($dia.DiagramObjects.Count) paquetes, $n dependencias"

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()

Write-Output 'OK'
