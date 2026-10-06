param(
    # Rehace el paquete entero.
    [switch]$Rehacer,
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\PlataformaMedica.eapx'),
    # El esquema en JSON. Sin esto, lo genera ea-dominio-esquema.py con el
    # entorno virtual del backend.
    [string]$Esquema = ''
)

# =========================================================================
# CAPITULO 4 - Sprint 2 - 2.1.2 Modelo de dominio
#
# Uno para todo el sistema (GUIA-DE-DIAGRAMAS.md, seccion 4.2), armado como
# el 3.3.1 Modelo de Dominio de VioletBoutique.eapx:
#   - una clase por TABLA, con su nombre en MAYUSCULAS y sin operaciones;
#   - columnas privadas, la clave primaria primero, el tipo de PostgreSQL en
#     mayusculas y el estereotipo PK / FK / PK,FK;
#   - asociaciones sin direccion, del padre al hijo, con un verbo en
#     MAYUSCULAS que se lee PADRE VERBO HIJO, y la cardinalidad en los dos
#     extremos: el padre 1 (0..1 si la FK admite NULL) y el hijo 0..* (0..1
#     si la FK es unica, un OneToOne).
#
# ---- DE DONDE SALE ----
#   Las tablas, columnas, tipos y claves salen de los modelos de Django con
#   ea-dominio-esquema.py, nunca a mano. Lo que agrega este script es lo que
#   el codigo no dice: el verbo de cada relacion, la disposicion y las notas.
#   Si aparece una FK sin verbo, el script se detiene y la nombra.
#
# ---- organization_id ----
#   Va como columna FK en toda tabla que la tiene: es el argumento
#   multi-inquilino. Pero la LINEA hacia ORGANIZATIONS sólo se dibuja para lo
#   propio del inquilino (suscripcion, metricas, alertas): con las otras 24
#   el diagrama no se lee. La nota del diagrama lo explica.
# =========================================================================

. (Join-Path $PSScriptRoot 'ea-sprint2-comun.ps1')
trap { Salir-ConError $_ }

if (-not $Esquema) {
    $Esquema = Join-Path $env:TEMP 'ea-dominio-esquema.json'
    $backend = Join-Path $PSScriptRoot '..\backend'
    Push-Location $backend
    try { & '.\.venv\Scripts\python.exe' (Join-Path $PSScriptRoot 'ea-dominio-esquema.py') $Esquema }
    finally { Pop-Location }
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo volcar el esquema' }
}
$tablas = [IO.File]::ReadAllText($Esquema, [Text.Encoding]::UTF8) | ConvertFrom-Json

# Columnas del diagrama, de izquierda a derecha: inquilino, usuarios y
# seguridad, lo que cuelga del usuario, catalogo, agenda, pacientes, fichas y
# atencion. Dentro de cada columna, de arriba abajo.
$COLUMNAS = @(
    @('organizations', 'subscription_plans', 'subscriptions', 'usage_metrics', 'isolation_alerts'),
    @('users', 'user_roles', 'roles', 'role_permissions', 'permissions'),
    @('audit_log', 'login_attempts', 'password_reset_tokens', 'saved_reports', 'backup_records', 'backup_files'),
    @('branches', 'branch_hours', 'practitioner_branches', 'practitioners', 'practitioner_specialties', 'specialties', 'services'),
    @('schedules', 'schedule_blocks', 'assistant_catalog_fragments'),
    @('patients', 'patient_history_entries'),
    @('appointments', 'payments'),
    @('encounters', 'encounter_amendments')
)
$X0 = 40; $PASO_X = 340; $ANCHO_CAJA = 290; $Y_ARRIBA = -170; $SEP_Y = 60
$ESTILO = 'BFol=0;LCol=0;BCol=15136253;font=Times New Roman;bold=0;black=0;italic=0;ul=0;charset=0;pitch=18;fontsz=80;'

# Las lineas hacia ORGANIZATIONS que si se dibujan.
$LINEAS_INQUILINO = @('subscriptions.organization_id', 'usage_metrics.organization_id',
                      'isolation_alerts.source_organization_id', 'isolation_alerts.target_organization_id')

# El verbo de cada FK, como "tabla.columna". Se lee PADRE VERBO HIJO.
$VERBOS = @{
    'subscriptions.organization_id'           = 'CONTRATA'
    'subscriptions.plan_id'                   = 'RIGE'
    'subscriptions.assigned_by_id'            = 'ASIGNA_PLAN'
    'usage_metrics.organization_id'           = 'ACUMULA'
    'isolation_alerts.source_organization_id' = 'ORIGINA'
    'isolation_alerts.target_organization_id' = 'RECIBE'
    'isolation_alerts.user_id'                = 'PROVOCA'
    'isolation_alerts.resolved_by_id'         = 'RESUELVE'
    'users.branch_id'                         = 'ADSCRIBE'
    'user_roles.user_id'                      = 'DESEMPENA'
    'user_roles.role_id'                      = 'SE_ASIGNA_EN'
    'user_roles.assigned_by_id'               = 'ASIGNA'
    'role_permissions.role_id'                = 'OTORGA'
    'role_permissions.permission_id'          = 'SE_OTORGA_EN'
    'audit_log.user_id'                       = 'QUEDA_REGISTRADO_EN'
    'login_attempts.user_id'                  = 'INTENTA'
    'password_reset_tokens.user_id'           = 'SOLICITA'
    'saved_reports.owner_id'                  = 'GUARDA'
    'backup_records.performed_by_id'          = 'EJECUTA'
    'backup_files.record_id'                  = 'SE_GUARDA_EN'
    'branch_hours.branch_id'                  = 'ABRE_SEGUN'
    'practitioners.user_id'                   = 'PUEDE_SER'
    'practitioner_branches.practitioner_id'   = 'ATIENDE_EN'
    'practitioner_branches.branch_id'         = 'CUENTA_CON'
    'practitioner_specialties.practitioner_id' = 'EJERCE'
    'practitioner_specialties.specialty_id'   = 'SE_EJERCE_EN'
    'services.specialty_id'                   = 'OFRECE'
    'schedules.practitioner_id'               = 'ATIENDE_SEGUN'
    'schedules.branch_id'                     = 'PROGRAMA'
    'schedule_blocks.practitioner_id'         = 'SE_BLOQUEA_EN'
    'schedule_blocks.branch_id'               = 'SUSPENDE'
    'patients.user_id'                        = 'ES_TAMBIEN'
    'patients.guardian_id'                    = 'TUTELA'
    'patient_history_entries.patient_id'      = 'TIENE'
    'patient_history_entries.declared_by_id'  = 'DECLARA'
    'appointments.patient_id'                 = 'SE_AGENDA_EN'
    'appointments.booked_by_id'               = 'RESERVA'
    'appointments.practitioner_id'            = 'ATIENDE'
    'appointments.branch_id'                  = 'ACOGE'
    'appointments.schedule_id'                = 'GENERA'
    'appointments.rescheduled_from_id'        = 'SE_REPROGRAMA_EN'
    'payments.appointment_id'                 = 'SE_PAGA_CON'
    'payments.created_by_id'                  = 'INICIA'
    'encounters.appointment_id'               = 'SE_ATIENDE_EN'
    'encounters.patient_id'                   = 'ACUMULA_HISTORIA_EN'
    'encounters.practitioner_id'              = 'REGISTRA'
    'encounters.branch_id'                    = 'ALBERGA'
    'encounters.signed_by_id'                 = 'FIRMA'
    'encounter_amendments.encounter_id'       = 'SE_ENMIENDA_CON'
    'encounter_amendments.author_id'          = 'ESCRIBE'
}

# La nota de las tablas que la necesitan, como en Violet: lo que la tabla no
# dice sola. EA la guarda en el elemento; no se dibuja.
$NOTAS = @{
    organizations = 'El inquilino. Toda tabla con organization_id le pertenece y la aísla Row Level Security de PostgreSQL.'
    users = 'organization_id nulo = administrador de la plataforma. El correo es único dentro de cada organización, no en toda la plataforma.'
    roles = 'organization_id nulo = rol del sistema, común a todas las organizaciones.'
    patients = 'user_id nulo = paciente sin cuenta. guardian_id apunta al titular de un dependiente.'
    appointments = 'La ficha. status: pending_payment, confirmed, attended, cancelled, rescheduled, expired o no_show. rescheduled_from_id apunta a la ficha que se reprogramó.'
    payments = 'El cobro de una ficha. status: pending, succeeded, failed, expired o refunded; provider: stripe o simulated. Una ficha tiene a lo sumo un pago succeeded.'
    encounters = 'La atención registrada sobre una ficha, a lo sumo una por ficha. Firmada, no se modifica: se corrige con una enmienda.'
    encounter_amendments = 'Una corrección a una atención ya firmada, con su autor y su fecha.'
    audit_log = 'La bitácora: se inserta, nunca se modifica. organization_id nulo = acción de nivel plataforma (alta de organización, asignación de plan).'
    assistant_catalog_fragments = 'Los fragmentos del catálogo que consulta el asistente, con su embedding VECTOR(768) de pgvector.'
    backup_files = 'El archivo de una copia automática, comprimido y cifrado.'
}

$NOTA_DIAGRAMA = 'organization_id va como FK en toda tabla que pertenece a una organización. La línea hacia ORGANIZATIONS sólo se dibuja para la suscripción, las métricas de uso y las alertas de aislamiento; en las demás tablas la relación es la misma (organización 1 — 0..* filas) y se omite para que el diagrama se lea.'

# =========================================================================

$porTabla = @{}
foreach ($t in $tablas) { $porTabla[$t.tabla] = $t }
$enColumnas = @($COLUMNAS | ForEach-Object { $_ })
foreach ($t in $tablas) { if ($enColumnas -notcontains $t.tabla) { throw "La tabla $($t.tabla) no tiene lugar en `$COLUMNAS" } }

$pkg = Get-PaqueteTipo 'Sprint 2 - 2.1.2 Modelo de dominio' $Rehacer
$nomDia = '2.1.2 Modelo de Dominio - Sprint 2'
if (Get-Diagrama $pkg $nomDia) { Write-Output "  $nomDia ya existe, no se toca"; Cerrar-Modelo; Write-Output 'OK'; return }
$dia = $pkg.Diagrams.AddNew($nomDia, 'Logical')
$dia.Notes = 'Modelo de dominio de todo el sistema al cierre del Sprint 2: una clase por tabla, sacada de los modelos de Django.'
[void]$dia.Update(); $pkg.Diagrams.Refresh()

# ---- las clases ---------------------------------------------------------
$id = @{}
for ($ci = 0; $ci -lt $COLUMNAS.Count; $ci++) {
    $y = $Y_ARRIBA
    foreach ($nombre in $COLUMNAS[$ci]) {
        $t = $porTabla[$nombre]
        if (-not $t) { throw "No está la tabla $nombre en el esquema" }
        $e = $pkg.Elements.AddNew($nombre.ToUpper(), 'Class')
        if ($NOTAS[$nombre]) { $e.Notes = $NOTAS[$nombre] }
        [void]$e.Update()
        $pos = 0
        foreach ($c in $t.columnas) {
            $a = $e.Attributes.AddNew($c.col, $c.tipo)
            $a.Visibility = 'Private'; $a.Pos = $pos; $pos++
            $est = @(); if ($c.pk) { $est += 'PK' }; if ($c.fk) { $est += 'FK' }
            if ($est.Count) { $a.Stereotype = $est -join ',' }
            [void]$a.Update()
        }
        $e.Attributes.Refresh()
        $alto = 60 + $t.columnas.Count * 18
        $x = $X0 + $ci * $PASO_X
        $do = $dia.DiagramObjects.AddNew("l=$x;r=$($x + $ANCHO_CAJA);t=$y;b=$($y - $alto);", '')
        $do.ElementID = $e.ElementID; $do.Style = $ESTILO
        [void]$do.Update()
        $id[$nombre] = $e.ElementID
        $y = $y - $alto - $SEP_Y
    }
}

# ---- las asociaciones ---------------------------------------------------
$n = 0
foreach ($t in $tablas) {
    foreach ($c in $t.columnas) {
        if (-not $c.fk) { continue }
        $clave = "$($t.tabla).$($c.col)"
        if ($c.fk -eq 'organizations' -and $LINEAS_INQUILINO -notcontains $clave) { continue }
        $verbo = $VERBOS[$clave]
        if (-not $verbo) { throw "La FK $clave no tiene verbo en `$VERBOS" }
        $con = $ea.GetElementByID($id[$c.fk]).Connectors.AddNew($verbo, 'Association')
        $con.SupplierID = $id[$t.tabla]
        $con.Direction = 'Unspecified'
        [void]$con.Update()
        $con.ClientEnd.Cardinality = $(if ($c.nulo) { '0..1' } else { '1' }); [void]$con.ClientEnd.Update()
        $con.SupplierEnd.Cardinality = $(if ($c.unico) { '0..1' } else { '0..*' }); [void]$con.SupplierEnd.Update()
        $n++
    }
}

# ---- la nota del diagrama -----------------------------------------------
$nota = $pkg.Elements.AddNew('', 'Note'); $nota.Notes = $NOTA_DIAGRAMA; [void]$nota.Update()
$yNota = -20
$do = $dia.DiagramObjects.AddNew("l=$X0;r=$($X0 + 2 * $PASO_X + $ANCHO_CAJA);t=$yNota;b=$($yNota - 90);", '')
$do.ElementID = $nota.ElementID; [void]$do.Update()

$dia.DiagramObjects.Refresh()
Write-Output ("  {0} : {1} tablas, {2} asociaciones" -f $nomDia, $tablas.Count, $n)
Cerrar-Modelo
Write-Output 'OK'
