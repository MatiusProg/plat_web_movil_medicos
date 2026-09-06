param(
    [switch]$Rehacer
)

# =========================================================================
# CAPITULO 3 - punto 3.10 Paquetes y casos de uso
#   (b) DIAGRAMAS DE CASOS DE USO POR PAQUETE  -  figuras 3.2 a 3.11
#
# ---- QUE DIBUJA ----
#   DIEZ diagramas, uno por paquete. En cada uno el paquete es un contenedor
#   grande, sus casos de uso van DENTRO de sus limites, y los actores que los
#   inician quedan afuera a la izquierda.
#
# ---- POR QUE DIEZ Y NO UNO ----
#   En EA un elemento solo puede aparecer UNA vez por diagrama, y casi todos
#   los actores participan en varios paquetes. En un unico lienzo, "Paciente"
#   tendria que estar dentro de siete paquetes a la vez. Ademas el documento
#   pide diez figuras, la 3.2 a la 3.11, una por modulo.
#
# ---- DE DONDE SALE EL REPARTO DE CASOS DE USO ----
#   Del punto "5.1 Modulos del sistema" y "5.2 Subsistema de IA" del propio
#   documento: los siete modulos mas los tres de IA son exactamente los diez
#   paquetes, y cada modulo enumera lo que le toca. Los actores salen de la
#   columna "Actor Principal" de la lista "3.9 Lista de casos de uso".
#   Los 46 casos de uso quedan repartidos sin que sobre ni falte ninguno.
#
# ---- DOS DECISIONES QUE CONVIENE CONOCER ----
#   1. Los casos de uso y los actores se crean NUEVOS en este paquete, no se
#      reusan los del diagrama 1.3 del Sprint 1. Si se reusaran, EA rotularia
#      cada uno con "(from Sprint 1 - Casos de Uso)" debajo del nombre en las
#      diez figuras. Los elementos de paquete de arriba SI se reusan, que son
#      los mismos del 3.10a.
#   2. NO se toca el ParentID. Los casos de uso quedan dibujados dentro del
#      paquete y ordenados por Z para que el contenedor no los tape, pero sin
#      volverse hijos suyos en el arbol: si lo fueran, los paquetes del 3.10a
#      dejarian de estar vacios, que es justo lo que ese diagrama corrigio.
#
# ---- LO QUE HAY QUE ORDENAR SI O SI ----
#   El orden Z. Sin el, el rectangulo del paquete se dibuja encima y tapa a
#   todos sus casos de uso. Es el error clasico de este diagrama.
#
# NO exporta imagenes.
# ADITIVO: abre el modelo y solo agrega lo que falta.
# =========================================================================

$ErrorActionPreference = 'Stop'

$modelo = 'D:\UNI\Si2\PROYECTO_MEDICOS\docs\diagramas\PlataformaMedica.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

$NOMBRE_PKG = '3.10 Paquetes y casos de uso'

# ---- Constantes de dibujo -------------------------------------------------
$ACT_X = 40;  $ACT_W = 150; $ACT_H = 80;  $ACT_PASO = 150
$PAQ_X = 300; $PAQ_W = 560
$CU_X  = 340; $CU_W  = 480; $CU_H = 70; $CU_PASO = 110

# ---- Actores --------------------------------------------------------------
$ACTORES = @(
    @{ k='usuario';    n='Usuario';                          abstracto=$true  },
    @{ k='paciente';   n='Paciente';                         abstracto=$false },
    @{ k='titular';    n='Titular';                          abstracto=$false },
    @{ k='recep';      n='Recepcionista';                    abstracto=$false },
    @{ k='medico';     n='Médico';                           abstracto=$false },
    @{ k='adminorg';   n='Administrador de Organización';    abstracto=$false },
    @{ k='superadmin'; n='Superadministrador de Plataforma'; abstracto=$false },
    @{ k='sistema';    n='Sistema';                          abstracto=$false },
    @{ k='equipo';     n='Equipo de Desarrollo';             abstracto=$false }
)

$GENERALIZACIONES = @(
    @{ hijo='paciente';   padre='usuario' },
    @{ hijo='recep';      padre='usuario' },
    @{ hijo='medico';     padre='usuario' },
    @{ hijo='adminorg';   padre='usuario' },
    @{ hijo='superadmin'; padre='usuario' },
    @{ hijo='titular';    padre='paciente' }
)

# ---- Los diez paquetes, con sus casos de uso y los actores de cada uno ----
# El nombre del paquete tiene que coincidir con el del diagrama 3.10a: los
# elementos se reusan buscandolos por nombre.
$PAQUETES = @(
    @{ fig='3.2'; paquete='Gestión Multi-Tenant'; cus=@(
        @{ n='CU44 Gestión de Organizaciones (Tenants)';        act=@('superadmin') },
        @{ n='CU45 Gestión de Planes de Suscripción';           act=@('superadmin') },
        @{ n='CU46 Supervisión y Aislamiento de Organizaciones'; act=@('adminorg','superadmin','sistema') }
    )},
    @{ fig='3.3'; paquete='Usuarios y Seguridad'; cus=@(
        @{ n='CU1 Autenticación de Usuario';        act=@('usuario') },
        @{ n='CU2 Registro de Usuarios / Pacientes'; act=@('paciente') },
        @{ n='CU3 Recuperación de Credenciales';    act=@('usuario') },
        @{ n='CU4 Terminación de Sesión';           act=@('usuario') },
        @{ n='CU5 Gestión de Roles y Permisos';     act=@('adminorg') },
        @{ n='CU6 Gestión de Perfil de Usuario';    act=@('usuario') },
        @{ n='CU7 Consulta de Bitácora de Auditoría'; act=@('adminorg') }
    )},
    @{ fig='3.4'; paquete='Gestión de Pacientes'; cus=@(
        @{ n='CU8 Gestión de Pacientes Dependientes';    act=@('titular') },
        @{ n='CU9 Gestión de Antecedentes del Paciente'; act=@('paciente','medico') },
        @{ n='CU10 Búsqueda y Consulta de Pacientes';    act=@('recep') },
        @{ n='CU11 Administración de Pacientes';         act=@('adminorg') }
    )},
    @{ fig='3.5'; paquete='Catálogo Médico y Agendas'; cus=@(
        @{ n='CU12 Gestión de Sucursales';                  act=@('adminorg') },
        @{ n='CU13 Gestión de Especialidades y Profesionales'; act=@('adminorg') },
        @{ n='CU14 Gestión de Agendas Médicas';             act=@('adminorg') },
        @{ n='CU15 Bloqueo de Agenda Médica';               act=@('adminorg') },
        @{ n='CU16 Consulta de Disponibilidad Médica';      act=@('paciente') },
        @{ n='CU17 Búsqueda de Profesionales';              act=@('paciente') }
    )},
    @{ fig='3.6'; paquete='Agendamiento y Compra de Fichas'; cus=@(
        @{ n='CU18 Reserva de Ficha Médica';               act=@('paciente') },
        @{ n='CU19 Pago de Ficha en Línea';                act=@('paciente') },
        @{ n='CU20 Generación de Comprobante Digital';     act=@('paciente') },
        @{ n='CU21 Cancelación / Reprogramación de Ficha'; act=@('paciente') },
        @{ n='CU22 Confirmación de Asistencia';            act=@('paciente') },
        @{ n='CU23 Check-in del Paciente';                 act=@('recep') },
        @{ n='CU24 Agendamiento y Cobro Asistido';         act=@('recep') }
    )},
    @{ fig='3.7'; paquete='Historia Clínica Digital'; cus=@(
        @{ n='CU25 Registro de Atención Médica';            act=@('medico') },
        @{ n='CU26 Consulta de Historia Clínica';           act=@('medico','paciente') },
        @{ n='CU27 Emisión de Recetas y Órdenes Médicas';   act=@('medico') },
        @{ n='CU28 Consulta de Recetas e Indicaciones';     act=@('paciente') }
    )},
    @{ fig='3.8'; paquete='Notificaciones y Reportes'; cus=@(
        @{ n='CU29 Gestión de Notificaciones';        act=@('paciente','sistema') },
        @{ n='CU30 Consulta de Indicadores y KPIs';   act=@('adminorg') },
        @{ n='CU31 Generación de Reportes';           act=@('adminorg') }
    )},
    @{ fig='3.9'; paquete='IA 1 · Chatbot de Orientación (RAG)'; cus=@(
        @{ n='CU32 Orientación Médica mediante Chatbot';     act=@('paciente') },
        @{ n='CU33 Consulta de Información mediante Chatbot'; act=@('paciente') },
        @{ n='CU34 Agendamiento mediante Chatbot';           act=@('paciente') },
        @{ n='CU35 Derivación a Atención de Emergencia';     act=@('paciente','sistema') }
    )},
    @{ fig='3.10'; paquete='IA 2 · Predicción de Inasistencia'; cus=@(
        @{ n='CU36 Predicción de Riesgo de Inasistencia';            act=@('adminorg','sistema') },
        @{ n='CU37 Envío de Recordatorios por Riesgo de Inasistencia'; act=@('sistema','paciente') },
        @{ n='CU38 Proyección de Demanda de Fichas';                 act=@('adminorg') },
        @{ n='CU39 Reentrenamiento del Modelo de No-Show';           act=@('equipo') }
    )},
    @{ fig='3.11'; paquete='IA 3 · Generación de Resúmenes'; cus=@(
        @{ n='CU40 Generación de Resumen de Consulta mediante IA'; act=@('sistema','paciente') },
        @{ n='CU41 Generación de Indicaciones de Preparación';     act=@('sistema','paciente') },
        @{ n='CU42 Generación de Resumen de Historia Clínica';     act=@('medico') },
        @{ n='CU43 Validación de Contenido Generado por IA';       act=@('medico') }
    )}
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
    return $null
}
# Regla 6 de la guia: Package.Elements NO devuelve los elementos de tipo
# Package -la API los esconde-, asi que un buscar-o-crear que recorra
# Elements nunca encuentra un paquete ya creado y lo duplica. La lectura que
# no miente es SQL. SQLQuery devuelve XML, no filas.
function IndicePorNombre($repo, $paquete) {
    $mapa = @{}
    $xml = $repo.SQLQuery("SELECT o.Object_ID AS id, o.Name AS nombre, o.Object_Type AS tipo FROM t_object o WHERE o.Package_ID=$($paquete.PackageID)")
    if ($xml) {
        $doc = New-Object System.Xml.XmlDocument
        $doc.LoadXml($xml)
        foreach ($fila in $doc.SelectNodes('//Row')) {
            $mapa["$($fila.tipo)|$($fila.nombre)"] = [int]$fila.id
        }
    }
    return $mapa
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
$pkg   = Get-OCrearPaquete $pCap $NOMBRE_PKG

if ($Rehacer) {
    for ($i = $pkg.Diagrams.Count - 1; $i -ge 0; $i--) {
        if ($pkg.Diagrams.GetAt($i).Name -like 'Fig 3.*') { $pkg.Diagrams.DeleteAt($i, $false) }
    }
    $pkg.Diagrams.Refresh()
    # Se borran solo los actores y casos de uso; los elementos de paquete son
    # del 3.10a y no se tocan.
    for ($i = $pkg.Elements.Count - 1; $i -ge 0; $i--) {
        $t = $pkg.Elements.GetAt($i).Type
        if ($t -eq 'UseCase' -or $t -eq 'Actor') { $pkg.Elements.DeleteAt($i, $false) }
    }
    $pkg.Elements.Refresh()
    Write-Output '  figuras y elementos anteriores eliminados (-Rehacer)'
}

$INDICE = IndicePorNombre $ea $pkg
function BuscarPorNombre($tipo, $nombre) {
    $clave = "$tipo|$nombre"
    if ($INDICE.ContainsKey($clave)) { return $ea.GetElementByID($INDICE[$clave]) }
    return $null
}

# ---- Actores, una sola vez para las diez figuras --------------------------
$ACT = @{}
foreach ($defActor in $ACTORES) {
    $e = BuscarPorNombre 'Actor' $defActor.n
    if (-not $e) {
        $e = $pkg.Elements.AddNew($defActor.n, 'Actor')
        if ($defActor.abstracto) {
            $e.Abstract = '1'
            $e.Notes = 'Actor abstracto: generaliza a los actores humanos. Los casos de uso de identidad los ejecutan todos por igual.'
        }
        [void]$e.Update()
        $INDICE["Actor|$($defActor.n)"] = $e.ElementID
    }
    $ACT[$defActor.k] = $e
}
$pkg.Elements.Refresh()

foreach ($g in $GENERALIZACIONES) {
    $ya = $false
    foreach ($cx in $ACT[$g.hijo].Connectors) {
        if ($cx.Type -eq 'Generalization' -and $cx.SupplierID -eq $ACT[$g.padre].ElementID) { $ya = $true }
    }
    if (-not $ya) {
        $cn = $ACT[$g.hijo].Connectors.AddNew('', 'Generalization')
        $cn.SupplierID = $ACT[$g.padre].ElementID
        [void]$cn.Update()
        $ACT[$g.hijo].Connectors.Refresh()
    }
}

# ---- Una figura por paquete ----------------------------------------------
$zPorDiagrama = @{}
$totalCU = 0

foreach ($defPaq in $PAQUETES) {
    $nombreDia = "Fig $($defPaq.fig) · Casos de uso: $($defPaq.paquete)"

    if (BuscarDiagrama $pkg $nombreDia) {
        Write-Output "  $nombreDia ya existe, no se toca"
        continue
    }

    $elPaquete = BuscarPorNombre 'Package' $defPaq.paquete
    if (-not $elPaquete) { throw "No encuentro el paquete '$($defPaq.paquete)'. Corré antes ea-paquetes-3-10.ps1" }

    $dia = $pkg.Diagrams.AddNew($nombreDia, 'UseCase')
    [void]$dia.Update(); $pkg.Diagrams.Refresh()

    # Actores que intervienen en este paquete, en el orden de $ACTORES.
    $suyos = @()
    foreach ($defActor in $ACTORES) {
        foreach ($cu in $defPaq.cus) {
            if ($cu.act -contains $defActor.k -and $suyos -notcontains $defActor.k) { $suyos += $defActor.k }
        }
    }

    # El contenedor tiene que dar para los casos de uso y para los actores.
    $altoPaq = [Math]::Max($defPaq.cus.Count * $CU_PASO + 90, $suyos.Count * $ACT_PASO + 90)
    [void](Poner $dia $elPaquete $PAQ_X -40 $PAQ_W $altoPaq)

    $idsCU = @()
    $y = -100
    foreach ($cu in $defPaq.cus) {
        $e = BuscarPorNombre 'UseCase' $cu.n
        if (-not $e) {
            $e = $pkg.Elements.AddNew($cu.n, 'UseCase'); [void]$e.Update()
            $INDICE["UseCase|$($cu.n)"] = $e.ElementID
        }
        [void](Poner $dia $e $CU_X $y $CU_W $CU_H)
        $idsCU += $e.ElementID
        $y -= $CU_PASO
        $totalCU++

        foreach ($claveActor in $cu.act) {
            $ya = $false
            foreach ($cx in $ACT[$claveActor].Connectors) {
                if ($cx.Type -eq 'Association' -and $cx.SupplierID -eq $e.ElementID) { $ya = $true }
            }
            if (-not $ya) {
                $cn = $ACT[$claveActor].Connectors.AddNew('', 'Association')
                $cn.SupplierID = $e.ElementID
                [void]$cn.Update()
                $ACT[$claveActor].Connectors.Refresh()
            }
        }
    }

    $yAct = -60
    foreach ($claveActor in $suyos) {
        [void](Poner $dia $ACT[$claveActor] $ACT_X $yAct $ACT_W $ACT_H)
        $yAct -= $ACT_PASO
    }

    $pkg.Elements.Refresh()
    $dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()

    $zPorDiagrama[$dia.DiagramID] = @{ paquete=$elPaquete.ElementID; cus=$idsCU }
    Write-Output "  $nombreDia : $($defPaq.cus.Count) casos de uso, $($suyos.Count) actores"
}

Write-Output "  total: $totalCU casos de uso repartidos en $($PAQUETES.Count) figuras"

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Start-Sleep -Milliseconds 1500

# =========================================================================
# PARTE 2 - Orden Z: sin esto el paquete tapa a sus casos de uso
# =========================================================================

if ($zPorDiagrama.Count -gt 0) {
    $cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$modelo;")
    $cn.Open()
    function Exec($sql) { $cmd = $cn.CreateCommand(); $cmd.CommandText = $sql; return $cmd.ExecuteNonQuery() }

    foreach ($did in $zPorDiagrama.Keys) {
        $z = 2
        foreach ($idCU in $zPorDiagrama[$did].cus) {
            [void](Exec "UPDATE t_diagramobjects SET Sequence = $z WHERE Diagram_ID = $did AND Object_ID = $idCU"); $z++
        }
        [void](Exec "UPDATE t_diagramobjects SET Sequence = 100 WHERE Diagram_ID = $did AND Object_ID = $($zPorDiagrama[$did].paquete)")
    }

    $cn.Close()
    Write-Output '  orden Z aplicado en las figuras nuevas'
}

Write-Output 'OK'
