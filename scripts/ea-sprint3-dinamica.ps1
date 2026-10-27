# =========================================================================
# Datos de los diagramas DINAMICOS del Sprint 3: secuencia, estado y tiempo.
#
# Lo consumen, con dot-sourcing (despues de ea-sprint3-comun.ps1):
#   ea-secuencia-sprint3.ps1   clave 'secuencia'
#   ea-estado-sprint3.ps1      clave 'estado'
#   ea-tiempo-sprint3.ps1      clave 'tiempo'
#
# Los participantes, los grupos y los mensajes NO estan aca: son los de
# Mateo en ea-sprint3-casos.ps1, los mismos de la comunicacion y del diseno
# de clase. Este archivo solo agrega lo que esos diagramas no tienen.
#
# ---- secuencia ----
#   El guion, de arriba hacia abajo, con el formato de ea-sprint2-casos.ps1:
#     @{ t='nota'; txt='FLUJO n ...' }                  separador de flujo
#     @{ t='msg'; o='<k>'; d='<k>'; n='g.i: texto' }     mensaje (ret=$true: retorno)
#     @{ t='alt' } / @{ t='op'; g='guarda' } / @{ t='fin' }
#     @{ t='loop'; g='guarda' } ... @{ t='fin' }
#   plataforma: el flujo que dibuja la secuencia. Web y móvil siguen el
#   mismo flujo, así que va el móvil donde lo hay (CU28, CU29, CU34) y la
#   web en los que sólo son web.
#   El guion lleva un alt por cada if; ea-secuencia-sprint3.ps1 dibuja solo
#   los caracteristicos (clave=$true fuerza uno, omitir=$true lo quita).
#   Cada mensaje de Mateo va UNA vez, con su numero "<grupo>.<orden>" y su
#   texto; despues de dos espacios puede ir, entre llaves, el anclaje al
#   codigo. No hay llamadas nuevas; los retornos agregados se numeran como
#   subnivel (1.3 -> 1.3.1). ea-secuencia-sprint3.ps1 lo comprueba.
#
# ---- estado ----
#   estados = @( @{ k; n; col; f } | @{ k; tipo='inicial'|'final'; col; f } )
#   transiciones = @( @{ de; a; r='evento [guarda] / accion {archivo:linea}' } )
#   ortogonal=$true en la unica flecha de vuelta del sumidero de errores.
#
# ---- tiempo ----
#   escenario, nota (dice que la regla es relativa y de donde sale cada
#   restriccion) y lineas = @( @{ n; estados; marcas = @( @{ t; e; ev; r } ) } )
#   t de 0 a 84; r sin llaves.
#
# CU30 (indicadores) solo lee y no es de IA, pago ni historia clinica: lleva
# secuencia, pero no estado ni tiempo.
# =========================================================================

$DINAMICA_SPRINT3 = @{}

# =========================================================================
# CU24 (US-23, PR #80) y CU30 (US-29, PR #82): secuencia, estado y tiempo.
# Para pegar en scripts/ea-sprint3-dinamica.ps1, despues de
# $DINAMICA_SPRINT3 = @{}. Participantes y mensajes: los de Mateo en
# ea-sprint3-casos.ps1. Verificado contra el codigo al 26/10.
# =========================================================================

# -------------------------------------------------------------------------
# CU24 Agendamiento y Cobro Asistido: cobro en efectivo en ventanilla.
# Toda la peticion corre en la transaccion de TenantMiddleware
# (tenancy/middleware.py:39, COMMIT en :71); el atomic() de
# register_cash_payment y el de confirm_payment son savepoints. Los asientos
# de la bitacora se encolan y los escribe AuditTrailMiddleware despues del
# COMMIT (config/settings.py:133 va antes que :137, asi que su
# process_response corre despues).
# -------------------------------------------------------------------------
$DINAMICA_SPRINT3['CU24'] = @{
  plataforma = 'web'
  secuencia = @(
    @{ t='nota'; txt='FLUJO 1 Cobrar en ventanilla' },
    @{ t='msg'; o='recep';     d='api';       n='1.1: cobrarEnEfectivo(ficha)  {sin pantalla al 26/10: se llama al endpoint sin cuerpo; el importe lo decide el backend}' },
    @{ t='msg'; o='api';       d='vista';     n='1.2: post(request, pk)  {POST /api/payments/appointments/{id}/cash/, payments/urls.py:17-21; IsAuthenticated y CanRegisterCashPayments, payments/views.py:123, :125}' },
    @{ t='alt' },
    @{ t='op'; g='sin token o sin payments.payment.register_cash' },
    @{ t='msg'; o='vista';     d='api';       n='1.2.1: 401 | 403(detail)  {DRF corta antes de post(); payments/permissions.py:11-14}'; ret=$true },
    @{ t='op'; g='token válido y payments.payment.register_cash' },
    @{ t='msg'; o='vista';     d='ficha';     n='1.3: filter(pk, organization)  {SELECT a.*, p.*, pr.*, b.* FROM appointments a JOIN patients p, practitioners pr, branches b WHERE a.id = :pk AND a.organization_id = :org LIMIT 1; payments/views.py:128-133}' },
    @{ t='msg'; o='ficha';     d='vista';     n='1.3.1: Ficha(status, expires_at) o None()'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='appointment is None' },
    @{ t='msg'; o='vista';     d='api';       n='1.3.2: 404(detail)  {La ficha no existe., payments/views.py:134-136}'; ret=$true },
    @{ t='op'; g='la ficha existe en la organización' },
    @{ t='msg'; o='vista';     d='gestor';    n='1.4: register_cash_payment(appointment, user, request)  {payments/views.py:138-139; payments/services.py:135}' },
    @{ t='msg'; o='gestor';    d='gestor';    n='1.5: _assert_payable(appointment)  {payments/services.py:153, :33-43}' },
    @{ t='alt' },
    @{ t='op'; g='status != pending_payment o expires_at <= now' },
    @{ t='nota'; txt='FLUJO 2 La ficha no se puede cobrar' },
    @{ t='msg'; o='gestor';    d='vista';     n='2.1: ValidationError(code)  {ficha_no_pendiente, payments/services.py:35-38; ficha_vencida, :39-43}'; ret=$true },
    @{ t='msg'; o='vista';     d='api';       n='2.2: 400(code, detail)  {except ValidationError, payments/views.py:140-142}'; ret=$true },
    @{ t='op'; g='pending_payment y expires_at > now' },
    @{ t='msg'; o='gestor';    d='gestor';    n='1.6: quote(appointment)  {payments/services.py:154; payments/pricing.py:39-74: la consulta más barata de la especialidad, la que la nombra o la genérica; si no hay, APPOINTMENT_DEFAULT_FEE = 100.00 BOB, config/settings.py:309-310}' },
    @{ t='msg'; o='gestor';    d='pago';      n='1.7: create(appointment, amount, provider)  {INSERT INTO payments (organization_id, appointment_id, created_by_id, amount, currency, provider = ''cash'', status = ''pending''); dentro de transaction.atomic(), payments/services.py:155-163}' },
    @{ t='msg'; o='gestor';    d='bitgestor'; n='1.8: record(request, action, entity, entity_id, detail)  {_asentar(request, payment, cobro_en_ventanilla), action = payment.movement; se encola en la petición, no se escribe: payments/services.py:164, :241-250; audit/services.py:112-118}' },
    @{ t='msg'; o='gestor';    d='gestor';    n='1.10: confirm_payment(payment, request)  {payments/services.py:165, :79; SELECT * FROM payments WHERE id = :id FOR UPDATE (:89), SELECT * FROM appointments WHERE id = :ficha FOR UPDATE OF appointments (:96-100) y SELECT EXISTS pago succeeded de la ficha (:105-107); el pago recién creado está pending, así que el return idempotente de :90 no se da}' },
    @{ t='alt'; clave=$true },
    @{ t='op'; g='ya hay un pago succeeded o la ficha ya no está pending_payment' },
    @{ t='msg'; o='gestor';    d='gestor';    n='1.10.1: Pago(status = refunded, refund_reason = pago_duplicado | ficha_no_disponible)  {refund_payment: CashProvider.refund no mueve dinero, UPDATE payments SET status = ''refunded'', refunded_at, refund_reason y _asentar(devuelto); payments/services.py:108-111, :168-178; payments/providers.py:196-199}'; ret=$true },
    @{ t='op'; g='ficha pending_payment y sin otro pago succeeded' },
    @{ t='msg'; o='gestor';    d='pago';      n='1.11: save(status, paid_at)  {UPDATE payments SET status = ''succeeded'', provider_payment_id, paid_at = now() WHERE id = :id; payments/services.py:103, :113-116}' },
    @{ t='msg'; o='gestor';    d='ficha';     n='1.12: save(status)  {UPDATE appointments SET status = ''confirmed'', expires_at = NULL WHERE id = :ficha; payments/services.py:118-120}' },
    @{ t='msg'; o='gestor';    d='gestor';    n='1.10.2: Pago(status = succeeded)  {on_commit(notify(CONFIRMED)) y _asentar(pagado), que también se encola; payments/services.py:128-131}'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='gestor';    d='vista';     n='1.4.1: Pago(status)  {register_cash_payment devuelve lo de confirm_payment, payments/services.py:165}'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='payment.status != succeeded' },
    @{ t='msg'; o='vista';     d='api';       n='1.4.2: 409(ficha_ya_pagada, detail)  {hay que devolver el efectivo; payments/views.py:144-149}'; ret=$true },
    @{ t='op'; g='payment.status = succeeded' },
    @{ t='msg'; o='vista';     d='api';       n='1.13: 201(payment_id, amount, appointment)  {también provider, currency y status; refresh_from_db() y AppointmentSerializer, payments/views.py:151-159}'; ret=$true },
    @{ t='fin' },
    @{ t='loop'; g='por cada asiento encolado, después del COMMIT' },
    @{ t='msg'; o='bitgestor'; d='bitacora';  n='1.9: insert(asiento)  {INSERT INTO audit_log (organization_id, user_id, action = ''payment.movement'', entity = ''payment'', entity_id, detail); AuditTrailMiddleware tras el COMMIT de TenantMiddleware: audit/middleware.py:22-23, audit/services.py:145-146, :169; tenancy/middleware.py:71}' },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='fin' }
  )

  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Recepcionista';     col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='val';    n='Validar ficha';                col=1; f=1 },
      @{ k='reg';    n='Registrar cobro en efectivo';  col=2; f=1 },
      @{ k='error';  n='Informar error';               col=2; f=5 },
      @{ k='conf';   n='Confirmar ficha';              col=3; f=0.5 },
      @{ k='dev';    n='Devolver pago duplicado';      col=3; f=3 },
      @{ k='ok';     n='Transacción completada';       col=4; f=2 },
      @{ k='fin';    tipo='final';   col=4; f=4 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='val';    r='[token y payments.payment.register_cash] {CanRegisterCashPayments, payments/views.py:123}' },
      @{ de='aut';   a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='val';   a='reg';    r='[de la organización, pending_payment y expires_at > now] / quote(), INSERT payments (provider = cash) {views.py:128, services.py:35, :39, :154, :156}' },
      @{ de='val';   a='error';  r='[inexistente, no pendiente o vencida] {404 views.py:134, 400 ficha_no_pendiente services.py:35, 400 ficha_vencida :39}' },
      @{ de='reg';   a='conf';   r='[ficha pending_payment y sin otro pago succeeded] / select_for_update() {services.py:89, :96, :108}' },
      @{ de='reg';   a='dev';    r='[ya pagada o la ficha ya no espera pago] / refund_payment(pago_duplicado | ficha_no_disponible) {services.py:108-111}' },
      @{ de='conf';  a='ok';     r='/ pago succeeded, ficha confirmed, expires_at = NULL, on_commit(notify) {services.py:113-120, :128; 201 views.py:152}' },
      @{ de='dev';   a='ok';     r='/ status = refunded {services.py:173; 409 ficha_ya_pagada views.py:144}' },
      @{ de='error'; a='val';    r='reintentar()'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  # Escenario: la ficha se reservo (CU18) y recepcion la cobra en el
  # mostrador antes de que venza su plazo de 15 minutos.
  tiempo = @{
    escenario = 'cobrar en ventanilla una ficha pending_payment antes de que venza su plazo de 15 minutos'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. 15 min = APPOINTMENT_HOLD_MINUTES (config/settings.py:262), que fija expires_at al reservar (appointments/booking.py:109, :140). El cobro sólo pasa si la ficha sigue pending_payment y expires_at > now (_assert_payable, payments/services.py:35, :39); si el plazo venció, 400 ficha_vencida y no se escribe nada. Autenticando es el JWT y CanRegisterCashPayments (payments/views.py:123); Validando, la búsqueda de la ficha en la organización, _assert_payable y quote (views.py:128, services.py:153-154); Escribiendo, el INSERT del pago con provider = cash y confirm_payment, que bloquea pago y ficha, deja el pago succeeded y la ficha confirmed con expires_at = NULL (services.py:155-165, :89-120); Confirmada, el COMMIT que cierra TenantMiddleware (tenancy/middleware.py:71). Los asientos se encolan con record() y los escribe AuditTrailMiddleware después de ese COMMIT (audit/services.py:117, :145-146; audit/middleware.py:22-23); el aviso al paciente sale en on_commit (services.py:128). No hay sesión de pago ni webhook: el dinero ya está en la caja.'
    lineas = @(
      @{ n='Plazo de reserva'
         estados=@('Corriendo', 'Cerrado')
         marcas=@( @{ t=0;  e='Corriendo'; ev='expires_at' },
                   @{ t=58; e='Cerrado';   ev='expires_at = NULL'; r='< 15 min' } ) },
      @{ n='Transacción del cobro'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=36; e='Autenticando'; ev='POST cash/' },
                   @{ t=42; e='Validando';    ev='_assert_payable()' },
                   @{ t=50; e='Escribiendo';  ev='INSERT payments' },
                   @{ t=62; e='Confirmada';   ev='COMMIT' },
                   @{ t=72; e='Inactiva';     ev='201' } ) },
      @{ n='Ficha'
         estados=@('pending_payment', 'confirmed')
         marcas=@( @{ t=0;  e='pending_payment'; ev='reserva (CU18)' },
                   @{ t=58; e='confirmed';       ev='confirm_payment()' } ) },
      @{ n='Pago'
         estados=@('Sin pago', 'pending', 'succeeded')
         marcas=@( @{ t=0;  e='Sin pago' },
                   @{ t=50; e='pending';   ev='create(cash)' },
                   @{ t=56; e='succeeded'; ev='confirm_payment()' } ) },
      @{ n='Bitácora'
         estados=@('Vacía', 'Encolada', 'Escrita')
         marcas=@( @{ t=0;  e='Vacía' },
                   @{ t=52; e='Encolada'; ev='record()' },
                   @{ t=66; e='Escrita';  ev='flush()' } ) }
    )
  }
}

# -------------------------------------------------------------------------
# CU30 Consulta de Indicadores y KPIs. Solo lee: lleva secuencia y nada mas.
# -------------------------------------------------------------------------
$DINAMICA_SPRINT3['CU30'] = @{
  plataforma = 'web'
  secuencia = @(
    @{ t='nota'; txt='FLUJO 1 Ver el panel de los últimos 30 días' },
    @{ t='msg'; o='admin';    d='pantalla'; n='1.1: abrirKpis()  {ruta /kpis, frontend/src/App.tsx:226; Kpis.tsx:71}' },
    @{ t='msg'; o='pantalla'; d='pantalla'; n='1.2: rangoPorDefecto()  {hoy y 29 días antes, Kpis.tsx:22-27, :74}' },
    @{ t='alt' },
    @{ t='op'; g='la sesión no tiene reporting.kpi.read' },
    @{ t='msg'; o='pantalla'; d='admin';    n='1.1.1: mostrarError(No tienes permiso para ver los indicadores de la organización.)  {no pide nada al servidor, Kpis.tsx:84, :108-112}'; ret=$true },
    @{ t='op'; g='puede(reporting.kpi.read)' },
    @{ t='msg'; o='pantalla'; d='vista';    n='1.3: get(request)  {verKpis(filtros, contexto): GET /api/reporting/kpis/?from=&to=, frontend/src/api/kpis.ts:49-52, Kpis.tsx:99-106; KpiView, reporting/kpi_views.py:42-45}' },
    @{ t='alt' },
    @{ t='op'; g='sin token o sin reporting.kpi.read' },
    @{ t='msg'; o='vista';    d='pantalla'; n='1.3.1: 401 | 403(detail)  {IsAuthenticated y CanReadKpis, reporting/kpi_views.py:43; reporting/permissions.py:53-57}'; ret=$true },
    @{ t='op'; g='usuario sin organización (plataforma)' },
    @{ t='msg'; o='vista';    d='pantalla'; n='1.3.2: 200(plataforma = true)  {reporting/kpi_views.py:46-48; la pantalla no dibuja el panel, Kpis.tsx:114}'; ret=$true },
    @{ t='op'; g='usuario de una organización' },
    @{ t='msg'; o='vista';    d='vista';    n='1.4: _fecha(valor)  {date.fromisoformat de to y de from; sin ellos, hasta = hoy en la zona de la organización y desde = hasta - 29 días (DIAS_POR_DEFECTO = 30); reporting/kpi_views.py:35-39, :50-58}' },
    @{ t='alt' },
    @{ t='op'; g='desde o hasta is None: la fecha no es AAAA-MM-DD' },
    @{ t='nota'; txt='FLUJO 3 Rango o sucursal inválidos' },
    @{ t='msg'; o='vista';    d='pantalla'; n='3.1: 400(code, detail)  {_error(invalid_date), reporting/kpi_views.py:31-32, :59-60}'; ret=$true },
    @{ t='msg'; o='pantalla'; d='admin';    n='3.1.1: mostrarError(detail)  {mensajeError(e), Kpis.tsx:104, :142}'; ret=$true },
    @{ t='op'; g='hasta < desde' },
    @{ t='msg'; o='vista';    d='pantalla'; n='1.3.3: 400(invalid_range, detail)  {reporting/kpi_views.py:61-62; la web no lo pide: rangoInvertido, Kpis.tsx:85, :100}'; ret=$true },
    @{ t='op'; g='(hasta - desde).days >= MAX_DIAS (366)' },
    @{ t='msg'; o='vista';    d='pantalla'; n='1.3.4: 400(range_too_long, detail)  {reporting/kpi_views.py:63-64; appointments/kpis.py:35}'; ret=$true },
    @{ t='op'; g='rango válido' },
    @{ t='msg'; o='vista';    d='calc';     n='1.5: calcular(organizacion, desde, hasta, branch_id, ahora)  {reporting/kpi_views.py:75 no pasa ahora: ahora = timezone.now(), appointments/kpis.py:106-108}' },
    @{ t='msg'; o='calc';     d='calc';     n='1.6: rango_utc(organizacion, desde, hasta)  {[desde 00:00, hasta + 1 00:00) en la zona de la organización, appointments/kpis.py:56-61, :109}' },
    @{ t='msg'; o='calc';     d='calc';     n='1.8: _espacios_ofrecidos(organizacion, desde, hasta, branch_id)  {appointments/kpis.py:68, :125}' },
    @{ t='msg'; o='calc';     d='agenda';   n='1.9: filter(is_active, valid_from, valid_until)  {SELECT s.*, b.* FROM schedules s JOIN branches b ON b.id = s.branch_id WHERE s.organization_id = :org AND s.is_active AND s.valid_from <= :hasta AND (s.valid_until IS NULL OR s.valid_until >= :desde) [AND s.branch_id = :branch]; appointments/kpis.py:70-76}' },
    @{ t='msg'; o='agenda';   d='calc';     n='1.9.1: list(Agenda)'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='not agendas' },
    @{ t='msg'; o='calc';     d='calc';     n='1.8.1: ofrecidos(0)  {appointments/kpis.py:77-78}'; ret=$true },
    @{ t='op'; g='hay agendas activas en el rango' },
    @{ t='msg'; o='calc';     d='bloqueo';  n='1.10: filter(starts_at, ends_at)  {SELECT * FROM schedule_blocks WHERE organization_id = :org AND is_active AND starts_at < :ventana_fin AND ends_at > :ventana_ini; ventana con un día de margen, appointments/kpis.py:81-87}' },
    @{ t='loop'; g='por cada bloqueo activo en la ventana' },
    @{ t='msg'; o='bloqueo';  d='calc';     n='1.10.1: BloqueoAgenda(practitioner_id, branch_id, starts_at, ends_at)  {por_profesional[practitioner_id], appointments/kpis.py:84-88}'; ret=$true },
    @{ t='fin' },
    @{ t='loop'; g='por cada agenda activa en el rango' },
    @{ t='msg'; o='calc';     d='calc';     n='1.9.2: espacios(dia, inicio, fin)  {generate_slots(agenda, desde, hasta, tz de la sucursal) contra los bloqueos del profesional o de toda la sucursal, appointments/kpis.py:91-99; cuenta cada espacio que no choca con ningún bloqueo, :100-102}'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='calc';     d='calc';     n='1.8.2: ofrecidos(total)  {appointments/kpis.py:103}'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='calc';     d='ficha';    n='1.7: aggregate(estado, sucursal, especialidad)  {SELECT COUNT(id) FILTER (WHERE debian_atenderse_q(ahora)) AS esperadas, COUNT(id) FILTER (WHERE inasistencia_q(ahora)) AS ausentes FROM appointments WHERE organization_id = :org AND starts_at >= :inicio AND starts_at < :fin [AND branch_id = :branch]; appointments/kpis.py:111-120, :128-131. El COUNT de las ocupadas, status IN (pending_payment, confirmed, attended, no_show), corre antes de 1.8: :123-124}' },
    @{ t='msg'; o='ficha';    d='calc';     n='1.7.1: conteo(esperadas, ausentes)'; ret=$true },
    @{ t='loop'; g='por cada fila de fichas ocupadas agrupadas por sucursal' },
    @{ t='msg'; o='ficha';    d='calc';     n='1.7.2: fila(branch_id, branch__name, total)  {GROUP BY branch_id, branches.name ORDER BY total DESC, appointments/kpis.py:134-138}'; ret=$true },
    @{ t='fin' },
    @{ t='loop'; g='por cada fila agrupada por especialidad del profesional' },
    @{ t='msg'; o='ficha';    d='calc';     n='1.7.3: fila(specialty_id, total)  {GROUP BY practitioner_specialties.specialty_id; el nombre sale de practitioner_specialties y, sin especialidad, Sin especialidad; appointments/kpis.py:141-156}'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='calc';     d='pago';     n='1.11: aggregate(Sum(amount))  {SELECT currency, SUM(amount), COUNT(id) FROM payments p JOIN appointments a ON a.id = p.appointment_id WHERE p.organization_id = :org AND p.status = ''succeeded'' AND a.starts_at >= :inicio AND a.starts_at < :fin [AND a.branch_id = :branch] GROUP BY currency, y otra igual GROUP BY a.branch_id, branches.name, currency; appointments/kpis.py:114-120, :162-176}' },
    @{ t='loop'; g='por cada moneda' },
    @{ t='msg'; o='pago';     d='calc';     n='1.11.1: fila(currency, total, pagos)  {appointments/kpis.py:162-166}'; ret=$true },
    @{ t='fin' },
    @{ t='loop'; g='por cada sucursal y moneda' },
    @{ t='msg'; o='pago';     d='calc';     n='1.11.2: fila(branch_id, branch_name, currency, total)  {appointments/kpis.py:167-176}'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='calc';     d='vista';    n='1.5.1: dict(range, branch, occupancy, no_show, demand, revenue)  {_tasa(parte, total) = None si total = 0, appointments/kpis.py:64-65, :178-195}'; ret=$true },
    @{ t='msg'; o='vista';    d='pantalla'; n='1.12: 200(ocupacion, inasistencia, ingresos, demanda)  {reporting/kpi_views.py:75}'; ret=$true },
    @{ t='msg'; o='pantalla'; d='admin';    n='1.1.2: panel(Anillo, Barras, ingresos)  {Anillo de ocupación e inasistencia, Barras por sucursal y especialidad; con demand.total = 0 y offered = 0 avisa que no hay agendas ni fichas; Kpis.tsx:114-201}'; ret=$true },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='fin' },

    @{ t='nota'; txt='FLUJO 2 Filtrar por sucursal' },
    @{ t='msg'; o='admin';    d='pantalla'; n='2.1: filtrarPorSucursal(branch)  {select con las sucursales de listarSucursales, Kpis.tsx:94, :133-138; cambia la clave y vuelve a pedir, :86, :99-106}' },
    @{ t='msg'; o='pantalla'; d='vista';    n='2.2: get(request)  {GET /api/reporting/kpis/?from=&to=&branch=, frontend/src/api/kpis.ts:51; la misma autenticación y las mismas fechas del flujo 1}' },
    @{ t='alt' },
    @{ t='op'; g='branch no es un UUID' },
    @{ t='msg'; o='vista';    d='pantalla'; n='2.2.1: 400(invalid_branch, detail)  {La sucursal no es válida., reporting/kpi_views.py:66-71}'; ret=$true },
    @{ t='op'; g='branch es un UUID' },
    @{ t='msg'; o='calc';     d='sucursal'; n='2.3: filter(pk, organization)  {SELECT EXISTS (SELECT 1 FROM branches WHERE organization_id = :org AND id = :branch); lo hace KpiView, no calcular: reporting/kpi_views.py:72}' },
    @{ t='msg'; o='sucursal'; d='calc';     n='2.3.1: bool(existe)'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='la sucursal no es de la organización' },
    @{ t='msg'; o='vista';    d='pantalla'; n='2.2.2: 400(invalid_branch, detail)  {La sucursal no existe en esta organización., reporting/kpi_views.py:72-73}'; ret=$true },
    @{ t='op'; g='la sucursal es de la organización' },
    @{ t='msg'; o='vista';    d='pantalla'; n='2.2.3: 200(ocupacion, inasistencia, ingresos, demanda)  {calcular(..., branch_id): los pasos 1.5 a 1.11 con AND branch_id = :branch, appointments/kpis.py:74-75, :118-120}'; ret=$true },
    @{ t='fin' },
    @{ t='fin' }
  )
}

# =========================================================================
# Dinámica (secuencia, estado y tiempo) de CU27 y CU28, Sprint 3 (PR #83).
# Participantes y mensajes: los de scripts/ea-sprint3-casos.ps1, con su
# número y su texto exactos. Sólo se agregan retornos (ret = $true),
# numerados como subnivel del mensaje que los provoca.
# =========================================================================

# -------------------------------------------------------------------------
#  CU27 · Emisión de Recetas y Órdenes Médicas (US-26)
# -------------------------------------------------------------------------
$DINAMICA_SPRINT3['CU27'] = @{
  plataforma = 'web'

  secuencia = @(
    @{ t='nota'; txt='FLUJO 1 Armar la receta y las órdenes (borrador)' },
    @{ t='alt' },
    @{ t='op'; g='agregar un medicamento: medicamento, dosis, frecuencia y duración llenos' },
    @{ t='msg'; o='medico';   d='pantalla'; n='1.1: enviarMedicamento(datos)  {formulario «Agregar un medicamento», RecetaAtencion.tsx:97-102; agregarMedicamento, atencion.ts:178}' },
    @{ t='op'; g='agregar una orden: estudio lleno' },
    @{ t='msg'; o='medico';   d='pantalla'; n='1.7: enviarOrden(datos)  {formulario «Agregar una orden», RecetaAtencion.tsx:103-107; agregarOrden, atencion.ts:184}' },
    @{ t='fin' },
    @{ t='msg'; o='pantalla'; d='vista';    n='1.2: post(request, pk, kind)  {POST /api/encounters/{id}/prescription/ u orders/; EncounterChildrenView, views.py:208; kind lo fija urls.py:27, :31}' },
    @{ t='msg'; o='vista';    d='vista';    n='1.3: _own_encounter(request, pk)  {SELECT * FROM encounters WHERE organization_id = :org AND id = :pk, más is_own(user, encuentro) contra practitioners.user_id; views.py:62-74}' },
    @{ t='alt' },
    @{ t='op'; g='encuentro is None o no es del profesional que pide' },
    @{ t='msg'; o='vista';    d='pantalla'; n='1.3.1: 404(detail)  {Http404, views.py:72-73: ajeno no es 403}'; ret=$true },
    @{ t='op'; g='datos inválidos para el serializer' },
    @{ t='msg'; o='vista';    d='pantalla'; n='1.2.1: 400(campo)  {is_valid(raise_exception), views.py:210-211}'; ret=$true },
    @{ t='op'; g='encuentro propio y datos válidos' },
    @{ t='msg'; o='vista';    d='gestor';   n='1.4: add_child(encounter, kind, data)  {services.py:187}' },
    @{ t='msg'; o='gestor';   d='gestor';   n='1.5: _require_draft(encounter)  {services.py:179}' },
    @{ t='alt' },
    @{ t='op'; g='encounter.is_signed' },
    @{ t='msg'; o='gestor';   d='vista';    n='4.1: Conflict(encounter_signed)  {services.py:180-184; el trigger trg_prescription_items_solo_en_borrador también lo rechaza, migrations/0006:92}'; ret=$true },
    @{ t='msg'; o='vista';    d='pantalla'; n='4.2: 409(detail)  {La receta y las órdenes no se editan. Agrega una enmienda.}'; ret=$true },
    @{ t='op'; g='status = draft' },
    @{ t='alt' },
    @{ t='op'; g='kind = prescription' },
    @{ t='msg'; o='gestor';   d='renglon';  n='1.6: create(medication, dose, frequency, duration)  {INSERT INTO encounter_prescription_items (organization_id, encounter_id, medication, dose, frequency, duration, instructions); services.py:189}' },
    @{ t='msg'; o='renglon';  d='gestor';   n='1.6.1: RenglonReceta(id)'; ret=$true },
    @{ t='op'; g='kind = orders' },
    @{ t='msg'; o='gestor';   d='orden';    n='1.8: create(kind, description, notes)  {INSERT INTO encounter_orders (organization_id, encounter_id, kind, description, notes); services.py:189}' },
    @{ t='msg'; o='orden';    d='gestor';   n='1.8.1: OrdenMedica(id)'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='vista';    d='pantalla'; n='1.2.2: 201(encuentro)  {EncounterSerializer(_own_encounter(request, pk)): la atención entera, views.py:213-214}'; ret=$true },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='msg'; o='medico';   d='pantalla'; n='1.9: quitar(renglon)  {botón Quitar, sólo en borrador, RecetaAtencion.tsx:61, :129-133; quitarMedicamento, atencion.ts:181}' },
    @{ t='msg'; o='pantalla'; d='vista';    n='1.10: delete(request, pk, child_pk)  {DELETE /api/encounters/{id}/prescription/{renglon}/; EncounterChildDetailView, views.py:238}' },
    @{ t='alt' },
    @{ t='op'; g='encuentro ajeno o el renglón no es de ese encuentro' },
    @{ t='msg'; o='vista';    d='pantalla'; n='1.10.1: 404(detail)  {_own_encounter, views.py:239; _child, :225-227}'; ret=$true },
    @{ t='op'; g='encuentro propio y renglón suyo' },
    @{ t='msg'; o='vista';    d='gestor';   n='1.11: delete_child(encounter, child)  {services.py:202; llama a _require_draft, :203}' },
    @{ t='alt' },
    @{ t='op'; g='encounter.is_signed' },
    @{ t='msg'; o='gestor';   d='vista';    n='1.11.1: Conflict(encounter_signed)  {services.py:180}'; ret=$true },
    @{ t='msg'; o='vista';    d='pantalla'; n='1.10.2: 409(detail)'; ret=$true },
    @{ t='op'; g='status = draft' },
    @{ t='msg'; o='gestor';   d='renglon';  n='1.12: delete()  {DELETE FROM encounter_prescription_items WHERE id = :child_pk; con kind = orders, DELETE FROM encounter_orders; services.py:204}' },
    @{ t='msg'; o='vista';    d='pantalla'; n='1.13: 200(encuentro)  {views.py:241}'; ret=$true },
    @{ t='fin' },
    @{ t='fin' },

    @{ t='nota'; txt='FLUJO 2 Firmar la atención' },
    @{ t='msg'; o='medico';   d='pantalla'; n='2.1: firmar()  {diálogo «Firmar la atención», Atencion.tsx:84, :164; si hay cambios sin guardar, antes los guarda, :87; firmarEncuentro, atencion.ts:145}' },
    @{ t='msg'; o='pantalla'; d='vista';    n='2.2: sign(request, pk)  {POST /api/encounters/{id}/sign/; EncounterSignView, views.py:169}' },
    @{ t='alt' },
    @{ t='op'; g='encuentro ajeno o inexistente' },
    @{ t='msg'; o='vista';    d='pantalla'; n='2.2.1: 404(detail)  {_own_encounter, views.py:170}'; ret=$true },
    @{ t='op'; g='encuentro propio' },
    @{ t='msg'; o='vista';    d='gestor';   n='2.3: sign(encounter, user)  {@transaction.atomic, services.py:126-127}' },
    @{ t='alt'; clave=$true },
    @{ t='op'; g='encounter.is_signed' },
    @{ t='msg'; o='gestor';   d='vista';    n='2.3.1: Conflict(El encuentro ya estaba firmado.)  {services.py:128-129}'; ret=$true },
    @{ t='msg'; o='vista';    d='pantalla'; n='2.2.2: 409(detail)'; ret=$true },
    @{ t='op'; g='falta motivo o diagnóstico (REQUIRED_TO_SIGN)' },
    @{ t='msg'; o='gestor';   d='vista';    n='2.3.2: ValidationError(reason, diagnosis)  {services.py:131-137}'; ret=$true },
    @{ t='msg'; o='vista';    d='pantalla'; n='2.2.3: 400(campo)'; ret=$true },
    @{ t='op'; g='borrador con motivo y diagnóstico' },
    @{ t='msg'; o='gestor';   d='encuentro'; n='2.4: save(status, signed_at, signed_by)  {UPDATE encounters SET status = ''signed'', signed_at = now(), signed_by_id = :user, updated_at WHERE id = :id; services.py:139-142; después la ficha pasa a attended con select_for_update, :146-149}' },
    @{ t='msg'; o='encuentro'; d='gestor';  n='2.4.1: Encuentro(status = signed, signed_at)'; ret=$true },
    @{ t='msg'; o='vista';    d='vista';    n='2.5: _audit(request, action, encuentro)  {action = encounter.sign, sin contenido clínico; views.py:172, :77-81}' },
    @{ t='msg'; o='vista';    d='pantalla'; n='2.2.4: 200(encuentro firmado)  {views.py:173}'; ret=$true },
    @{ t='fin' },
    @{ t='fin' },

    @{ t='nota'; txt='FLUJO 3 Descargar la receta en PDF' },
    @{ t='msg'; o='medico';   d='pantalla'; n='3.1: descargarReceta(id)  {BotonDescargar, sólo firmada y con receta, RecetaAtencion.tsx:124, :33-38; atencion.ts:202}' },
    @{ t='msg'; o='pantalla'; d='vista';    n='3.2: get(request, pk)  {GET /api/encounters/{id}/prescription.pdf; PrescriptionPdfView, views.py:264; SELECT * FROM encounters JOIN organizations, patients, practitioners, branches, appointments WHERE organization_id = :org AND id = :pk, con prefetch, :266-273}' },
    @{ t='alt' },
    @{ t='op'; g='encuentro is None' },
    @{ t='msg'; o='vista';    d='pantalla'; n='3.2.1: 404(detail)  {views.py:274-275}'; ret=$true },
    @{ t='op'; g='no es el médico que atendió con encounters.encounter.read, y sin alcance de historial o borrador' },
    @{ t='msg'; o='vista';    d='pantalla'; n='3.2.2: 404(detail)  {is_own y has_permission, views.py:277-279; history_scope, :282-287}'; ret=$true },
    @{ t='op'; g='not encuentro.is_signed' },
    @{ t='msg'; o='vista';    d='pantalla'; n='3.2.3: 409(Firma la atención antes de descargar la receta)  {views.py:289-293}'; ret=$true },
    @{ t='op'; g='sin renglones ni órdenes' },
    @{ t='msg'; o='vista';    d='pantalla'; n='3.2.4: 409(La atención no tiene receta ni órdenes.)  {views.py:294-295}'; ret=$true },
    @{ t='op'; g='firmada y con receta u órdenes' },
    @{ t='msg'; o='vista';    d='pdf';      n='3.3: render(encounter)  {reportlab, prescription_pdf.py:52; no lleva el diagnóstico}' },
    @{ t='msg'; o='pdf';      d='encuentro'; n='3.4: select_related(patient, practitioner, branch)  {organización, paciente, médico y sucursal, prescription_pdf.py:61-66; el JOIN corre en views.py:266-270}' },
    @{ t='msg'; o='encuentro'; d='pdf';     n='3.4.1: Encuentro(patient, practitioner, branch, indications, signed_at)'; ret=$true },
    @{ t='msg'; o='pdf';      d='renglon';  n='3.5: prescription_items()  {SELECT * FROM encounter_prescription_items WHERE encounter_id = :id ORDER BY created_at; prefetch de views.py:271, leído en prescription_pdf.py:142}' },
    @{ t='msg'; o='renglon';  d='pdf';      n='3.5.1: RenglonReceta[](medication, dose, frequency, duration, instructions)'; ret=$true },
    @{ t='msg'; o='pdf';      d='orden';    n='3.6: orders()  {SELECT * FROM encounter_orders WHERE encounter_id = :id ORDER BY created_at; prescription_pdf.py:152}' },
    @{ t='msg'; o='orden';    d='pdf';      n='3.6.1: OrdenMedica[](kind, description, notes)'; ret=$true },
    @{ t='msg'; o='pdf';      d='vista';    n='3.3.1: bytes(application/pdf)  {documento.build, prescription_pdf.py:194-195}'; ret=$true },
    @{ t='msg'; o='vista';    d='pantalla'; n='3.7: 200(application/pdf)  {_audit(RECORD_READ, origen = receta_pdf, alcance = attending), views.py:298; Content-Disposition con filename(encounter), :301-304}'; ret=$true },
    @{ t='fin' }
  )

  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Médico';              col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='menu';   n='Seleccionar operación';          col=1; f=2 },
      @{ k='capm';   n='Capturar medicamento u orden';   col=2; f=0 },
      @{ k='quit';   n='Quitar renglón u orden';         col=2; f=1.6 },
      @{ k='capf';   n='Confirmar firma';                col=2; f=3.2 },
      @{ k='pedp';   n='Pedir receta en PDF';            col=2; f=4.8 },
      @{ k='valb';   n='Validar borrador';               col=3; f=0 },
      @{ k='valg';   n='Validar firma';                  col=3; f=3.2 },
      @{ k='valp';   n='Verificar firma y receta';       col=3; f=4.8 },
      @{ k='error';  n='Informar error';                 col=4; f=5.5 },
      @{ k='ok';     n='Transacción completada';         col=4; f=1.5 },
      @{ k='fin';    tipo='final';   col=4; f=3 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='menu';   r='[token y encounters.encounter.create] {CanCreateEncounters, views.py:205, :220, :167}' },
      @{ de='aut';   a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='menu';  a='capm';   r='[agregar] {POST /encounters/<id>/prescription/ | orders/}' },
      @{ de='menu';  a='quit';   r='[quitar] {DELETE /encounters/<id>/prescription/<renglón>/}' },
      @{ de='menu';  a='capf';   r='[firmar] {POST /encounters/<id>/sign/}' },
      @{ de='menu';  a='pedp';   r='[descargar receta] {GET /encounters/<id>/prescription.pdf}' },
      @{ de='capm';  a='valb';   r='enviarMedicamento() | enviarOrden() {RecetaAtencion.tsx:98, :103}' },
      @{ de='valb';  a='ok';     r='[propio, datos válidos y borrador] / add_child() {services.py:187}' },
      @{ de='valb';  a='error';  r='[ajeno, datos inválidos o firmado] {404 views.py:72, 400 :211, 409 services.py:180}' },
      @{ de='quit';  a='ok';     r='[propio y borrador] / delete_child() {services.py:202}' },
      @{ de='quit';  a='error';  r='[renglón ajeno o firmado] {404 views.py:226, 409 services.py:180}' },
      @{ de='capf';  a='valg';   r='firmar() {Atencion.tsx:84}' },
      @{ de='valg';  a='ok';     r='[motivo y diagnóstico] / sign(), ficha attended {services.py:139, :148}' },
      @{ de='valg';  a='error';  r='[ya firmado o falta motivo o diagnóstico] {409 services.py:128, 400 :137}' },
      @{ de='pedp';  a='valp';   r='descargarReceta() {RecetaAtencion.tsx:33}' },
      @{ de='valp';  a='ok';     r='[firmado y con receta u órdenes] / render(), _audit(RECORD_READ) {views.py:297-298}' },
      @{ de='valp';  a='error';  r='[borrador o sin receta ni órdenes] {409 views.py:289, :294}' },
      @{ de='error'; a='menu';   r='reintentar()'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  tiempo = @{
    escenario = 'armar la receta en el borrador y firmar en una consulta que dura más que el token de acceso'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. La receta y las órdenes no tienen plazo propio: se editan mientras la atención es draft (_require_draft, encounters/services.py:179-184) y quedan fijas en el instante de la firma, que pone signed_at = now() (services.py:140); desde ahí las rechaza también el trigger trg_prescription_items_solo_en_borrador (encounters/migrations/0006_us26_rls_e_inmutabilidad.py:92) y recién existe el PDF (views.py:289). El reloj que manda es la sesión del médico en la web: 30 min = ACCESS_TOKEN_LIFETIME (config/settings.py:365); 25 min = MINUTOS_HASTA_RENOVAR (frontend/src/sesion/ContextoSesion.tsx:38), el setTimeout de ContextoSesion.tsx:81 renueva el par antes de que venza, y el refresco viejo va a la lista negra (ROTATE_REFRESH_TOKENS y BLACKLIST_AFTER_ROTATION, config/settings.py:367-368). Por eso la firma sale con el acceso nuevo; sin la renovación, el POST /sign/ respondería 401. La firma también pasa la ficha a attended bajo select_for_update (services.py:146-149).'
    lineas = @(
      @{ n='Transacción'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=6;  e='Autenticando'; ev='POST /prescription/' },
                   @{ t=11; e='Validando';    ev='_require_draft()' },
                   @{ t=16; e='Escribiendo';  ev='INSERT' },
                   @{ t=21; e='Confirmada';   ev='COMMIT' },
                   @{ t=25; e='Inactiva';     ev='201 (encuentro)' },
                   @{ t=60; e='Autenticando'; ev='POST /sign/' },
                   @{ t=65; e='Validando';    ev='sign()' },
                   @{ t=70; e='Escribiendo';  ev='UPDATE' },
                   @{ t=75; e='Confirmada';   ev='COMMIT' },
                   @{ t=80; e='Inactiva';     ev='200' } ) },
      @{ n='Renovación de la sesión'
         estados=@('Esperando', 'Renovando')
         marcas=@( @{ t=0;  e='Esperando' },
                   @{ t=44; e='Renovando'; ev='renovar()'; r='25 min' },
                   @{ t=48; e='Esperando'; ev='par nuevo' } ) },
      @{ n='Acceso viejo'
         estados=@('Vigente', 'Vencido')
         marcas=@( @{ t=0;  e='Vigente' },
                   @{ t=53; e='Vencido'; ev='expira'; r='30 min' } ) },
      @{ n='Atención'
         estados=@('draft', 'signed')
         marcas=@( @{ t=0;  e='draft' },
                   @{ t=75; e='signed'; ev='signed_at = now()' } ) },
      @{ n='Receta'
         estados=@('Vacía', 'Editable', 'Fija')
         marcas=@( @{ t=0;  e='Vacía' },
                   @{ t=21; e='Editable'; ev='INSERT renglón' },
                   @{ t=75; e='Fija';     ev='firma' } ) }
    )
  }
}

# -------------------------------------------------------------------------
#  CU28 · Consulta de Recetas e Indicaciones (US-27)
# -------------------------------------------------------------------------
$DINAMICA_SPRINT3['CU28'] = @{
  plataforma = 'móvil'

  secuencia = @(
    @{ t='nota'; txt='FLUJO 1 Ver la historia con sus recetas' },
    @{ t='msg'; o='paciente'; d='pantalla'; n='1.1: abrirMiHistoria()  {pide las personas (GET /patients/dependents/patient-options/) y elige la primera; PatientSelector, clinical_record_screen.dart:168-171}' },
    @{ t='msg'; o='pantalla'; d='vista';    n='1.2: get(request, patient_id)  {GET /api/encounters/history/{patient_id}/; verHistorial, atencion.ts:167; móvil verHistoriaClinica, clinical_record_api.dart:178; PatientHistoryView, history_views.py:40}' },
    @{ t='msg'; o='vista';    d='vista';    n='1.3: has_permission(request, view)  {IsAuthenticated y CanReadHistory: encounters.history.read, history_views.py:33-38, permissions.py:16-21}' },
    @{ t='alt' },
    @{ t='op'; g='sin el permiso encounters.history.read' },
    @{ t='msg'; o='vista';    d='pantalla'; n='3.1: 403(detail)  {No tienes permiso para realizar esta acción., permissions.py:14; sin token es 401}'; ret=$true },
    @{ t='op'; g='con el permiso' },
    @{ t='msg'; o='vista';    d='gestor';   n='1.4: history_scope(user, patient)  {antes, SELECT * FROM patients WHERE organization_id = :org AND id = :patient_id, history_views.py:41-44; services.py:216}' },
    @{ t='alt' },
    @{ t='op'; g='no es el propio paciente y patient.guardian_id no es nulo' },
    @{ t='msg'; o='gestor';   d='entpaciente'; n='1.5: filter(user, guardian)  {titular_de(user): SELECT * FROM patients WHERE user_id = :user AND is_active LIMIT 1, patients/dependents.py:74; compara con guardian_id, services.py:240-243}' },
    @{ t='msg'; o='entpaciente'; d='gestor'; n='1.5.1: Paciente(id)'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='gestor';   d='vista';    n='1.4.1: alcance(own | professional | None)  {own: user_id o titular, services.py:238-243; professional: médico con ficha, :245-252}'; ret=$true },
    @{ t='alt'; clave=$true },
    @{ t='op'; g='alcance is None' },
    @{ t='msg'; o='vista';    d='pantalla'; n='1.4.2: 404(detail)  {history_views.py:45-46: no 403, para no confirmar que existe}'; ret=$true },
    @{ t='op'; g='alcance own' },
    @{ t='msg'; o='vista';    d='encuentro'; n='1.6: filter(patient)  {SELECT * FROM encounters JOIN patients, practitioners, branches, appointments, users WHERE organization_id = :org AND patient_id = :id AND status = ''signed'' ORDER BY appointments.starts_at DESC; history_views.py:48-56}' },
    @{ t='msg'; o='encuentro'; d='vista';   n='1.6.1: Encuentro[](indications, treatment, signed_at)'; ret=$true },
    @{ t='msg'; o='vista';    d='renglon';  n='1.7: prefetch(prescription_items)  {SELECT * FROM encounter_prescription_items WHERE encounter_id IN (:ids); history_views.py:54}' },
    @{ t='msg'; o='renglon';  d='vista';    n='1.7.1: RenglonReceta[]'; ret=$true },
    @{ t='msg'; o='vista';    d='orden';    n='1.8: prefetch(orders)  {SELECT * FROM encounter_orders WHERE encounter_id IN (:ids)}' },
    @{ t='msg'; o='orden';    d='vista';    n='1.8.1: OrdenMedica[]'; ret=$true },
    @{ t='msg'; o='vista';    d='enmienda'; n='1.9: prefetch(amendments)  {SELECT * FROM encounter_amendments JOIN users WHERE encounter_id IN (:ids) ORDER BY created_at; amendments__author}' },
    @{ t='msg'; o='enmienda'; d='vista';    n='1.9.1: Enmienda[](section, text, author)'; ret=$true },
    @{ t='msg'; o='vista';    d='pantalla'; n='1.10: 200(atenciones)  {patient, scope, branches, encounters; antes record(RECORD_READ, origen = historial), history_views.py:58-71}'; ret=$true },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='msg'; o='paciente'; d='pantalla'; n='1.11: cambiarPersona(opcion)  {vuelve a 1.2 con el patient_id del dependiente; _cambiarPersona, clinical_record_screen.dart:140-149}' },

    @{ t='nota'; txt='FLUJO 2 Descargar una receta' },
    @{ t='msg'; o='paciente'; d='pantalla'; n='2.1: descargarReceta(id)  {sólo si hay receta u órdenes; _descargarReceta, clinical_record_screen.dart:90-96}' },
    @{ t='msg'; o='pantalla'; d='recetavista'; n='2.2: get(request, pk)  {GET /api/encounters/{id}/prescription.pdf; PrescriptionPdfView, views.py:264-273}' },
    @{ t='alt' },
    @{ t='op'; g='encuentro is None' },
    @{ t='msg'; o='recetavista'; d='pantalla'; n='2.2.1: 404(detail)  {views.py:274-275}'; ret=$true },
    @{ t='op'; g='sin encounters.history.read, history_scope is None o borrador' },
    @{ t='msg'; o='recetavista'; d='pantalla'; n='2.2.2: 404(detail)  {views.py:281-287}'; ret=$true },
    @{ t='op'; g='sin renglones ni órdenes' },
    @{ t='msg'; o='recetavista'; d='pantalla'; n='2.2.3: 409(La atención no tiene receta ni órdenes.)  {views.py:294-295}'; ret=$true },
    @{ t='op'; g='firmada, con alcance own y con receta u órdenes' },
    @{ t='msg'; o='recetavista'; d='pdf';   n='2.3: render(encounter)  {prescription_pdf.py:52; sin diagnóstico}' },
    @{ t='msg'; o='pdf';      d='recetavista'; n='2.3.1: bytes(application/pdf)  {prescription_pdf.py:194-195}'; ret=$true },
    @{ t='msg'; o='recetavista'; d='pantalla'; n='2.4: 200(application/pdf)  {_audit(RECORD_READ, origen = receta_pdf, alcance = own), views.py:298; Content-Disposition con filename(encounter), :301-304}'; ret=$true },
    @{ t='msg'; o='pantalla'; d='paciente'; n='2.4.1: Receta guardada en Descargas(nombre)  {clinical_record_screen.dart:97-114}'; ret=$true },
    @{ t='fin' }
  )

  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Paciente';             col=0; f=2 },
      @{ k='fin401'; tipo='final';   col=0; f=4.5 },
      @{ k='sel';    n='Elegir persona';                  col=1; f=2 },
      @{ k='perm';   n='Verificar permiso';               col=2; f=2 },
      @{ k='alc';    n='Resolver alcance';                col=3; f=2 },
      @{ k='leer';   n='Leer atenciones firmadas';        col=3; f=0 },
      @{ k='most';   n='Mostrar o descargar receta';      col=4; f=0 },
      @{ k='ok';     n='Transacción completada';          col=4; f=2 },
      @{ k='fin';    tipo='final';   col=4; f=3.5 },
      @{ k='error';  n='Informar error';                  col=4; f=5.5 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='sel';    r='[token válido] {IsAuthenticated, history_views.py:38}' },
      @{ de='aut';   a='fin401'; r='[sin token o refresco vencido] {401}' },
      @{ de='sel';   a='perm';   r='verHistorial(persona) {GET /history/<patient_id>/}' },
      @{ de='perm';  a='alc';    r='[encounters.history.read] {CanReadHistory, history_views.py:33}' },
      @{ de='perm';  a='error';  r='[sin el permiso] {403 permissions.py:18}' },
      @{ de='alc';   a='leer';   r='[own: propio o dependiente a cargo] {services.py:238, :242}' },
      @{ de='alc';   a='error';  r='[sin alcance] {404 history_views.py:45}' },
      @{ de='leer';  a='most';   r='/ filter(status=signed), prefetch(prescription_items, orders), record(RECORD_READ) {history_views.py:50, :54, :58}' },
      @{ de='most';  a='ok';     r='[ver, o descargar con receta] / render(), _audit(RECORD_READ) {views.py:297-298}' },
      @{ de='ok';    a='fin' },
      @{ de='error'; a='sel';    r='reintentar()'; ortogonal=$true }
    )
  }

  tiempo = @{
    escenario = 'ver la historia en el móvil y bajar la receta después de que venció el acceso'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. La historia y la receta no tienen reloj propio (ni vencimiento ni sondeo ni paginación): manda la sesión. 30 min = ACCESS_TOKEN_LIFETIME (config/settings.py:365). El paciente abre la historia, deja el teléfono y vuelve cuando el acceso ya venció; el móvil no renueva por temporizador sino antes de cada petición: accessToken() renueva si el acceso vence dentro de 1 min (refreshMargin, mobile/lib/core/config.dart:34; mobile/lib/core/session/session.dart:312-319; jwt.dart:48), y si igual llega un 401 renueva a la fuerza y reintenta una sola vez (mobile/lib/core/api/client.dart:198-208). El refresco rota y el viejo va a la lista negra (ROTATE_REFRESH_TOKENS y BLACKLIST_AFTER_ROTATION, config/settings.py:367-368). 20 s = Config.timeout (mobile/lib/core/config.dart:40, client.dart:184): si el PDF no llega en ese tiempo, la descarga falla como sin conexión. En la web la renovación es por setTimeout a los 25 min (frontend/src/sesion/ContextoSesion.tsx:38, :81).'
    lineas = @(
      @{ n='Transacción'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Leyendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=4;  e='Autenticando'; ev='GET /history/' },
                   @{ t=9;  e='Validando';    ev='history_scope()' },
                   @{ t=14; e='Leyendo';      ev='SELECT encounters' },
                   @{ t=19; e='Confirmada';   ev='COMMIT' },
                   @{ t=23; e='Inactiva';     ev='200 (atenciones)' },
                   @{ t=62; e='Autenticando'; ev='GET prescription.pdf' },
                   @{ t=66; e='Validando';    ev='history_scope()' },
                   @{ t=70; e='Leyendo';      ev='render()' },
                   @{ t=75; e='Confirmada';   ev='COMMIT' },
                   @{ t=79; e='Inactiva';     ev='200 (PDF)' } ) },
      @{ n='Acceso viejo'
         estados=@('Vigente', 'Vencido')
         marcas=@( @{ t=0;  e='Vigente' },
                   @{ t=45; e='Vencido'; ev='expira'; r='30 min' } ) },
      @{ n='Renovación (móvil)'
         estados=@('Esperando', 'Renovando')
         marcas=@( @{ t=0;  e='Esperando' },
                   @{ t=55; e='Renovando'; ev='accessToken()'; r='margen 1 min' },
                   @{ t=60; e='Esperando'; ev='par nuevo' } ) },
      @{ n='Refresco viejo'
         estados=@('Vigente', 'Revocado')
         marcas=@( @{ t=0;  e='Vigente' },
                   @{ t=60; e='Revocado'; ev='BLACKLIST_AFTER_ROTATION' } ) },
      @{ n='Descarga'
         estados=@('Sin archivo', 'Bajando', 'Guardada')
         marcas=@( @{ t=0;  e='Sin archivo' },
                   @{ t=55; e='Bajando';  ev='descargarReceta()' },
                   @{ t=82; e='Guardada'; ev='Descargas'; r='< 20 s' } ) }
    )
  }
}

# =========================================================================
# CU29 Gestión de Notificaciones (US-28, PR #81): secuencia, estado y tiempo.
# Participantes y mensajes: el bloque 'CU29' de scripts/ea-sprint3-casos.ps1
# (Mateo). Cada mensaje suyo aparece una vez, con su número y su texto; lo
# único agregado son retornos (ret) y anclajes entre llaves.
# Rutas del backend relativas a backend/; las del móvil, a mobile/lib/.
# =========================================================================

$DINAMICA_SPRINT3['CU29'] = @{
  plataforma = 'móvil'

  secuencia = @(
    # ---------------------------------------------------------------------
    @{ t='nota'; txt='FLUJO 1 Registrar el dispositivo al iniciar sesión' },
    @{ t='msg'; o='paciente'; d='app'; n='1.1: iniciarSesion()  {Session.saveSession() tras el login de US-02, core/session/session.dart:261; llama a _registrarTelefono(), :282}' },
    @{ t='alt' },
    @{ t='op'; g='sesión abierta y no es superadministrador (session.dart:206)' },
    @{ t='msg'; o='app'; d='app'; n='1.2: iniciar()  {Push.registrar(api) lo llama primero, push.dart:180-181; inicia una sola vez: Firebase.initializeApp y onMessage.listen(_mostrarConLaAppAbierta), :125, :134, :155}' },
    @{ t='alt' },
    @{ t='op'; g='iniciar() = true (Android con los cuatro --dart-define de Firebase) y permiso de notificaciones no denegado (push.dart:128-131, :181, :183-184)' },
    @{ t='msg'; o='app'; d='fcm'; n='1.3: getToken()  {antes requestPermission(), push.dart:183; getToken :187}' },
    @{ t='msg'; o='fcm'; d='app'; n='1.3.1: token'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='token != null (push.dart:188)' },
    @{ t='msg'; o='app'; d='vista'; n='1.4: post(request)  {POST /api/notifications/devices/ {token, platform = android}, _enviar() push.dart:207-215; IsAuthenticated, notifications/views.py:22, :24}' },
    @{ t='alt' },
    @{ t='op'; g='user.organization_id no es None y DeviceTokenSerializer válido (views.py:26, :34)' },
    @{ t='msg'; o='vista'; d='tokens'; n='1.5: update_or_create(token, user, platform)  {SELECT * FROM device_tokens WHERE organization_id = :org AND token = :token FOR UPDATE; UPDATE device_tokens SET user_id, platform, last_seen_at | INSERT INTO device_tokens (organization_id, token, user_id, platform); views.py:36-39}' },
    @{ t='msg'; o='tokens'; d='vista'; n='1.5.1: DeviceToken(id, platform), creado'; ret=$true },
    @{ t='msg'; o='vista'; d='app'; n='1.4.1a: 201(id, platform)  {200 si el token ya estaba registrado, views.py:40-43}'; ret=$true },
    @{ t='op'; g='superadministrador sin organización o token vacío' },
    @{ t='msg'; o='vista'; d='app'; n='1.4.1b: 400(code, detail)  {sin_organizacion views.py:26-32; token, :34; la app sólo lo anota, push.dart:216-218}'; ret=$true },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='fin' },

    # ---------------------------------------------------------------------
    @{ t='nota'; txt='FLUJO 2 Recordatorio de la ficha' },
    @{ t='msg'; o='sistema'; d='comando'; n='2.1: handle()  {python manage.py send_appointment_reminders --loop, scripts/start.sh:45; appointments/management/commands/send_appointment_reminders.py:41}' },
    @{ t='alt' },
    @{ t='op'; g='APPOINTMENT_REMINDERS en off, 0 o false (send_appointment_reminders.py:42; settings.py:287)' },
    @{ t='msg'; o='comando'; d='sistema'; n='2.1.1a: Recordatorios apagados (APPOINTMENT_REMINDERS=off)  {send_appointment_reminders.py:43-44}'; ret=$true },
    @{ t='op'; g='encendido' },
    @{ t='loop'; omitir=$true; g='sin --loop, una vuelta; con --loop, while True con una pausa de --every minutos, 15 por omisión (send_appointment_reminders.py:46-48, :50, :54, :66)' },
    @{ t='msg'; o='comando'; d='recordatorios'; n='2.2: run_due(now)  {_vuelta() la llama sin now, send_appointment_reminders.py:68-69; platform_admin_context: SELECT * FROM organizations WHERE status = ''active'', appointments/reminders.py:87-90}' },
    @{ t='loop'; g='por cada organización activa (reminders.py:93); si run_for lanza, se anota y sigue con la siguiente (:94-98)' },
    @{ t='msg'; o='recordatorios'; d='recordatorios'; n='2.3: run_for(organization, now)  {tenant_context(org); due(now).values_list(pk): SELECT id FROM appointments WHERE status = ''confirmed'' AND reminder_sent_at IS NULL AND starts_at > :now AND starts_at <= :now + 24 h AND created_at <= starts_at - 24 h; reminders.py:45-51, :59-60, :95}' },
    @{ t='loop'; g='por cada ficha pendiente, una transacción por ficha (reminders.py:63, :66)' },
    @{ t='msg'; o='recordatorios'; d='ficha'; n='2.4: select_for_update(skip_locked)  {SELECT * FROM appointments WHERE id = :pk AND (condiciones de due) LIMIT 1 FOR UPDATE SKIP LOCKED; reminders.py:67-70}' },
    @{ t='msg'; o='ficha'; d='recordatorios'; n='2.4.1: Ficha | None'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='ficha no es None; si es None, la tomó otro proceso o ya no corresponde y se sigue con la siguiente (reminders.py:71-73)' },
    @{ t='msg'; o='recordatorios'; d='notif'; n='2.5: notify(event, appointment_id, organization_id)  {notify(REMINDER, ficha.id, organization.id), reminders.py:74; notifications/services.py:40; recordatorio no pasa por send_confirmation_email, :46}' },
    @{ t='msg'; o='notif'; d='ficha'; n='2.6: _load(appointment_id)  {tenant_context propio; SELECT * FROM appointments JOIN organizations, patients, users, practitioners, branches WHERE id = :id; services.py:52-53, :81-89}' },
    @{ t='msg'; o='ficha'; d='notif'; n='2.6.1: Ficha(patient, practitioner, branch, organization)'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='_recipient(ficha) devuelve un usuario: el paciente o su titular, con correo (services.py:54-56; appointments/attendance.py:107-110)' },
    @{ t='msg'; o='notif'; d='push'; n='2.7: send_to_user(user, message)  {_push_text(recordatorio): Recordatorio de tu ficha, data {appointment_id, event}; services.py:57-61, :112-114}' },
    @{ t='msg'; o='push'; d='tokens'; n='2.8: filter(user)  {SELECT * FROM device_tokens WHERE user_id = :user; notifications/push.py:124}' },
    @{ t='msg'; o='tokens'; d='push'; n='2.8.1: list(DeviceToken)'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='hay dispositivos y FIREBASE_CREDENTIALS cargada (push.py:125-126, :128-135; settings.py:284)' },
    @{ t='loop'; g='por cada dispositivo del usuario (push.py:139)' },
    @{ t='msg'; o='push'; d='fcm'; n='2.9: send(payload)  {session.post(SEND_URL, json = _payload(token, message), timeout = 10 s), API HTTP v1; push.py:35-36, :84-99, :141-142}' },
    @{ t='alt'; clave=$true },
    @{ t='op'; g='status_code = 200 (push.py:147)' },
    @{ t='msg'; o='fcm'; d='push'; n='2.9.1a: 200(name)  {enviados += 1, push.py:148}'; ret=$true },
    @{ t='op'; g='_is_dead(response): 404, o 400 UNREGISTERED o registration token inválido (push.py:102-116, :149)' },
    @{ t='msg'; o='fcm'; d='push'; n='2.9.1b: 404 | 400(UNREGISTERED)'; ret=$true },
    @{ t='msg'; o='push'; d='tokens'; n='2.10: delete()  {DELETE FROM device_tokens WHERE id = :id; push.py:150-152}' },
    @{ t='op'; g='otro error, o la red falló: se anota y sigue con el siguiente (push.py:143-146, :153-155)' },
    @{ t='msg'; o='fcm'; d='push'; n='2.9.1c: error(status_code, detalle)'; ret=$true },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='msg'; o='push'; d='notif'; n='2.7.1: enviados  {push.py:156}'; ret=$true },
    @{ t='msg'; o='notif'; d='correo'; n='2.11: send_mail(asunto, cuerpo)  {fuera del tenant_context de notify; Recordatorio: tu ficha del dd/mm, con el enlace de asistencia si no la confirmó; Brevo por django-anymail si hay BREVO_API_KEY; services.py:62-63, :71-73, :136-147; settings.py:400-407}' },
    @{ t='fin' },
    @{ t='msg'; o='notif'; d='recordatorios'; n='2.5.1: None  {nunca propaga un error: push y correo caídos se anotan, services.py:64-66, :74-76}'; ret=$true },
    @{ t='msg'; o='recordatorios'; d='ficha'; n='2.12: save(reminder_sent_at)  {UPDATE appointments SET reminder_sent_at = now(), updated_at = now() WHERE id = :id; se marca aunque el envío falle; COMMIT al salir del tenant_context de la ficha; reminders.py:66, :75-77}' },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='msg'; o='recordatorios'; d='recordatorios'; n='2.3.1: avisadas  {reminders.py:78}'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='recordatorios'; d='comando'; n='2.2.1: total  {reminders.py:99}'; ret=$true },
    @{ t='msg'; o='comando'; d='sistema'; n='2.1.1b: Recordatorios de fichas: N enviado(s)  {send_appointment_reminders.py:70-72; con --loop, close_old_connections() y time.sleep(every * 60), :65-66}'; ret=$true },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='alt' },
    @{ t='op'; g='app abierta en primer plano: FirebaseMessaging.onMessage (push.dart:155); cerrada o en segundo plano, Android lo muestra solo en la barra' },
    @{ t='msg'; o='fcm'; d='app'; n='2.13: _mostrarConLaAppAbierta(mensaje)  {asíncrono: FCM lo entrega cuando puede, incluso antes del COMMIT de 2.12; flutter_local_notifications en el canal fichas, push.dart:252-270; push.py:39}' },
    @{ t='fin' },
    @{ t='msg'; o='paciente'; d='app'; n='2.14: tocarAviso(appointmentId)  {el toque real llega por onDidReceiveNotificationResponse, onMessageOpenedApp o getInitialMessage a _abrir(), push.dart:147-148, :156-157, :161-166, :273-276}' },
    @{ t='alt' },
    @{ t='op'; g='appointmentId no vacío y la app ya fijó alAbrirFicha (push.dart:277-278, :283; app.dart:39)' },
    @{ t='msg'; o='app'; d='paciente'; n='2.14.1a: abrirFicha(/appointments/<id>)  {_abrirFicha, router.go, app.dart:47-50}'; ret=$true },
    @{ t='op'; g='el router todavía no está listo (push.dart:279-281)' },
    @{ t='msg'; o='app'; d='app'; n='2.14.1b: _pendiente = appointmentId  {se entrega al fijar alAbrirFicha, push.dart:112-118}'; ret=$true },
    @{ t='fin' },

    # ---------------------------------------------------------------------
    @{ t='nota'; txt='FLUJO 3 Olvidar el dispositivo al cerrar sesión' },
    @{ t='msg'; o='paciente'; d='app'; n='3.1: cerrarSesion()  {Session.signOut(), session.dart:368; borra los tokens del teléfono y llama a Push.olvidar(api) antes del logout, :376, :386}' },
    @{ t='alt' },
    @{ t='op'; g='había access y refresh (session.dart:379), push disponible y token conocido (push.dart:230, :232-236)' },
    @{ t='msg'; o='app'; d='vista'; n='3.2: delete(request)  {DELETE /api/notifications/devices/ {token}, con el access que todavía vale; push.dart:237-238; views.py:45}' },
    @{ t='alt' },
    @{ t='op'; g='ForgetDeviceSerializer válido (views.py:46-47)' },
    @{ t='msg'; o='vista'; d='tokens'; n='3.3: filter(token, user).delete()  {DELETE FROM device_tokens WHERE user_id = :user AND token = :token; views.py:48-50}' },
    @{ t='msg'; o='tokens'; d='vista'; n='3.3.1: borrados'; ret=$true },
    @{ t='msg'; o='vista'; d='app'; n='3.2.1a: 204()  {views.py:51; después la app invalida el token en FCM con deleteToken(), push.dart:243-245}'; ret=$true },
    @{ t='op'; g='token vacío' },
    @{ t='msg'; o='vista'; d='app'; n='3.2.1b: 400(token)  {la app sólo lo anota, push.dart:240-241}'; ret=$true },
    @{ t='fin' },
    @{ t='fin' }
  )

  # Flujo de la transacción: una vuelta del recordatorio. El disparador es el
  # comando, sin usuario ni JWT; el contexto lo fija tenant_context.
  estado = @{
    estados = @(
      @{ k='ini';     tipo='inicial'; col=0; f=0 },
      @{ k='vuelta';  n='Iniciar comando';                 col=0; f=2 },
      @{ k='ok';      n='Transacción completada';          col=0; f=4 },
      @{ k='fin';     tipo='final';   col=0; f=6 },
      @{ k='finoff';  tipo='final';   col=1; f=0 },
      @{ k='orgs';    n='Recorrer organizaciones activas'; col=1; f=2 },
      @{ k='esperar'; n='Esperar la vuelta siguiente';     col=1; f=4 },
      @{ k='listar';  n='Listar fichas en la ventana';     col=2; f=0.5 },
      @{ k='error';   n='Informar error';                  col=2; f=6 },
      @{ k='sig';     n='Tomar siguiente ficha';           col=3; f=1.5 },
      @{ k='cerrar';  n='Cerrar transacción de la ficha';  col=3; f=3.5 },
      @{ k='bloq';    n='Bloquear ficha';                  col=4; f=0.5 },
      @{ k='avisar';  n='Avisar por push y correo';        col=4; f=2.25 },
      @{ k='marcar';  n='Marcar recordatorio enviado';     col=4; f=4 }
    )
    transiciones = @(
      @{ de='ini';     a='vuelta' },
      @{ de='vuelta';  a='finoff';  r='[APPOINTMENT_REMINDERS en off, 0 o false] {send_appointment_reminders.py:42-44}' },
      @{ de='vuelta';  a='orgs';    r='handle() [encendido] / _vuelta(), run_due() {send_appointment_reminders.py:41, :47, :56, :69}' },
      @{ de='orgs';    a='listar';  r='[queda una organización activa] / run_for(organization), tenant_context(org) {reminders.py:93-95, :59}' },
      @{ de='listar';  a='sig';     r='/ due(now).values_list(pk): confirmed, sin reminder_sent_at, empieza en las próximas 24 h y reservada antes de la ventana {reminders.py:45-51, :60}' },
      @{ de='sig';     a='orgs';    r='[no quedan fichas] / return avisadas {reminders.py:78}' },
      @{ de='sig';     a='bloq';    r='[queda un pk] / tenant_context(org): una transacción por ficha {reminders.py:63, :66}' },
      @{ de='bloq';    a='avisar';  r='[select_for_update(skip_locked) devuelve la ficha] / notify(recordatorio) {reminders.py:67-71, :74}' },
      @{ de='bloq';    a='cerrar';  r='[None: la tomó otro proceso o se canceló] / continue {reminders.py:71-73}' },
      @{ de='avisar';  a='marcar';  r='[enviado, sin destinatario o fallido: notify nunca propaga] {services.py:55-56, :64-66, :74-76}' },
      @{ de='marcar';  a='cerrar';  r='/ reminder_sent_at = now(), save() {reminders.py:75-77}' },
      @{ de='cerrar';  a='sig';     r='/ COMMIT de la ficha {reminders.py:66; tenancy/context.py:57}' },
      @{ de='marcar';  a='error';   r='[excepción en la base dentro de run_for] {reminders.py:94-96}' },
      @{ de='error';   a='orgs';    r='/ logger.exception: siguiente organización, sus fichas quedan sin marcar {reminders.py:96-98}'; ortogonal=$true },
      @{ de='orgs';    a='ok';      r='[no quedan organizaciones] / return total {reminders.py:99}' },
      @{ de='ok';      a='esperar'; r='[--loop] / time.sleep(every * 60) {send_appointment_reminders.py:50, :66}' },
      @{ de='esperar'; a='orgs';    r='/ close_old_connections(), _vuelta() {send_appointment_reminders.py:54-56, :65}' },
      @{ de='ok';      a='fin';     r='[sin --loop] {send_appointment_reminders.py:46-48}' }
    )
  }

  # Escenario: la ficha confirmada entra en la ventana de 24 h y la vuelta
  # siguiente la recuerda una sola vez; la otra vuelta ya no la encuentra.
  tiempo = @{
    escenario = 'la ficha confirmada entra en la ventana de 24 horas y la vuelta siguiente del comando la recuerda una sola vez'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. 24 h = APPOINTMENT_REMINDER_HOURS (config/settings.py:289): due() toma las fichas confirmed sin reminder_sent_at que empiezan dentro de las próximas 24 h y que se reservaron antes de que empezara la ventana (appointments/reminders.py:45-51); una reservada con menos de 24 h ya recibió la confirmación. 15 min = --every por omisión (send_appointment_reminders.py:36-39, :50), la pausa entre vueltas del proceso que lanza scripts/start.sh:45; por eso el recordatorio sale a lo sumo unos 15 min después de que la ficha entra en la ventana. 10 s = TIMEOUT_SECONDS de cada POST a FCM (notifications/push.py:36). Transacción de la ficha: no hay JWT; Fijando inquilino es tenant_context(org) (reminders.py:66; tenancy/context.py:57), Validando es el SELECT ... FOR UPDATE SKIP LOCKED con las condiciones de due() (reminders.py:67-71), Escribiendo es notify() más el UPDATE de reminder_sent_at (:74-76) y Confirmada es el COMMIT al salir del bloque. Push y correo salen dentro de esa transacción y nunca la deshacen (notifications/services.py:64-66, :74-76): la ficha se marca aunque el envío falle. FCM entrega el aviso de forma asíncrona, así que el teléfono puede mostrarlo antes o después del COMMIT. En la segunda vuelta (t = 84) la ficha ya tiene reminder_sent_at y due() no la devuelve: el recordatorio no se repite.'
    lineas = @(
      @{ n='Comando de recordatorios'
         estados=@('Durmiendo', 'Dando la vuelta')
         marcas=@( @{ t=0;  e='Durmiendo';       ev='time.sleep()' },
                   @{ t=10; e='Dando la vuelta'; ev='_vuelta()'; r='15 min' },
                   @{ t=64; e='Durmiendo';       ev='total' },
                   @{ t=84; e='Dando la vuelta'; ev='_vuelta()'; r='15 min' } ) },
      @{ n='Transacción de la ficha'
         estados=@('Inactiva', 'Fijando inquilino', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=16; e='Fijando inquilino'; ev='tenant_context()' },
                   @{ t=22; e='Validando';         ev='SKIP LOCKED' },
                   @{ t=28; e='Escribiendo';       ev='notify()' },
                   @{ t=56; e='Confirmada';        ev='COMMIT' },
                   @{ t=60; e='Inactiva' } ) },
      @{ n='Ficha'
         estados=@('Fuera de la ventana', 'En la ventana', 'Recordada')
         marcas=@( @{ t=0;  e='Fuera de la ventana'; ev='confirmed' },
                   @{ t=6;  e='En la ventana';       ev='faltan 24 h'; r='24 h' },
                   @{ t=56; e='Recordada';           ev='reminder_sent_at'; r='< 15 min' } ) },
      @{ n='Aviso push'
         estados=@('Sin aviso', 'En FCM', 'Mostrado')
         marcas=@( @{ t=0;  e='Sin aviso' },
                   @{ t=34; e='En FCM';   ev='send(payload)'; r='10 s' },
                   @{ t=44; e='Mostrado'; ev='onMessage' } ) },
      @{ n='Correo'
         estados=@('Sin enviar', 'Enviado')
         marcas=@( @{ t=0;  e='Sin enviar' },
                   @{ t=48; e='Enviado'; ev='send_mail()' } ) }
    )
  }
}

# -----------------------------------------------------------------------
# CU34 Agendamiento mediante Chatbot (US-33). Backend PR #77, web PR #78,
# movil PR #84. Participantes, grupos y mensajes: los de Mateo en
# ea-sprint3-casos.ps1 (bloque 'CU34'). Aca solo va el guion de la
# secuencia, el flujo de la transaccion (estado) y el escenario de tiempo.
#
# Reglas que el guion deja ver: el modelo propone y no reserva (la reserva
# es book_appointment, la misma de CU18); nada se reserva sin Confirmar;
# los horarios salen de consolidated_availability, nunca del texto del
# modelo; la barrera de urgencias (triage.py) corre antes de buscar turnos;
# la preferencia se suelta de a poco (relaxed); la conversacion no se
# guarda en el servidor.
# -----------------------------------------------------------------------
$DINAMICA_SPRINT3['CU34'] = @{
  plataforma = 'móvil'

  secuencia = @(
    # ===================================================================
    @{ t='nota'; txt='FLUJO 1 Pedir un turno en lenguaje natural' },
    @{ t='msg'; o='paciente';  d='pantalla';     n='1.1: escribir(mensaje)  {_enviar(), assistant_screen.dart:133}' },
    @{ t='msg'; o='pantalla';  d='asistente';    n='1.2: post(request)  {POST /api/assistant/suggest/ (question); consultarAsistente, asistente.ts:105, assistant_api.dart:290; SuggestView.post, views.py:56}' },
    @{ t='alt' },
    @{ t='op'; g='sin token o sin permiso assistant.suggest.use' },
    @{ t='msg'; o='asistente'; d='pantalla';     n='1.2.1: 403(detail)  {401 sin token | 403 sin permiso; CanUseAssistant, views.py:54}'; ret=$true },
    @{ t='op'; g='question inválida' },
    @{ t='msg'; o='asistente'; d='pantalla';     n='1.2.2: 400(question)  {views.py:57-58}'; ret=$true },
    @{ t='op'; g='organization is None, plan sin ai_chatbot o sin cupo de consultas' },
    @{ t='msg'; o='asistente'; d='pantalla';     n='1.2.3: 403(detail)  {views.py:61-69, :75-78}'; ret=$true },
    @{ t='op'; g='triage.check(question).is_emergency' },
    @{ t='msg'; o='asistente'; d='pantalla';     n='1.2.4: _emergency_response(regla)  {primera capa de US-34, antes de recuperar nada; views.py:81-84, CU35}'; ret=$true },
    @{ t='op'; g='EmbeddingError en retrieve()' },
    @{ t='msg'; o='asistente'; d='pantalla';     n='1.2.5: 503(answer)  {views.py:87-104}'; ret=$true },
    @{ t='op'; g='sin urgencia y con fragmentos recuperados' },
    @{ t='alt' },
    @{ t='op'; g='fragments[0] es administrativo (US-32)' },
    @{ t='msg'; o='asistente'; d='pref';         n='1.3: has_booking_intent(text)  {reglas, sin modelo; views.py:112, preferences.py:161}' },
    @{ t='msg'; o='pref';      d='asistente';    n='1.3.1: bool()'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='pide reservar' },
    @{ t='loop'; g='por cada fragmento, hasta un servicio con especialidad activa' },
    @{ t='msg'; o='asistente'; d='especialidad'; n='1.5: filter(organization, name)  {_specialty_for_booking: SELECT sp.id, sp.name FROM services s JOIN specialties sp ON sp.id = s.specialty_id WHERE s.id = :source_id AND s.organization_id = :org AND sp.is_active; views.py:198-207}' },
    @{ t='msg'; o='especialidad'; d='asistente'; n='1.5.1: Especialidad(id, name)  {si ningún servicio la tiene, rank_specialties(fragments), views.py:211}'; ret=$true },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='msg'; o='asistente'; d='asistente';    n='1.4: _booking_hint(request, question, especialidad)  {available: especialidad, ficha de paciente, appointments.appointment.create y scheduling.slot.read; booking_intent: has_booking_intent otra vez; views.py:215-232, llamado en :116 y :163}' },
    @{ t='alt' },
    @{ t='op'; g='el modelo marcó urgencia (segunda capa de US-34)' },
    @{ t='msg'; o='asistente'; d='pantalla';     n='1.2.6: _emergency_response(gemini)  {orientación views.py:133-135, antes de _booking_hint; administrativa :176-178}'; ret=$true },
    @{ t='op'; g='sin urgencia' },
    @{ t='msg'; o='asistente'; d='pantalla';     n='1.6: 200(answer, booking)  {kind orientacion o administrativa; booking = (available, booking_intent, specialty); views.py:138-167, :181-191}'; ret=$true },
    @{ t='fin' },
    @{ t='fin' },

    # ===================================================================
    @{ t='nota'; txt='FLUJO 2 Ofrecer horarios reales' },
    @{ t='msg'; o='pantalla';  d='pantalla';     n='2.1: _buscarTurnos(pedido)  {solo si booking.available y booking_intent (assistant_screen.dart:174-180); si no, al tocar Ver horarios (assistant_screen.dart:349); assistant_screen.dart:185}' },
    @{ t='msg'; o='pantalla';  d='reserva';      n='2.2: slots(request)  {POST /api/assistant/slots/ (specialty, preference = el mismo mensaje); pedirTurnos, asistente.ts:119, assistant_api.dart:363; SlotsView.post, booking_views.py:65}' },
    @{ t='alt' },
    @{ t='op'; g='sin token o sin permiso assistant.suggest.use o scheduling.slot.read' },
    @{ t='msg'; o='reserva';   d='pantalla';     n='2.2.1: 403(detail)  {401 | 403; booking_views.py:63}'; ret=$true },
    @{ t='op'; g='specialty no es un UUID o preference de más de 200 caracteres' },
    @{ t='msg'; o='reserva';   d='pantalla';     n='2.2.2: 400(campo)  {booking_views.py:66-67, serializers.py:50-55}'; ret=$true },
    @{ t='op'; g='organization is None o plan sin ai_chatbot' },
    @{ t='msg'; o='reserva';   d='pantalla';     n='2.2.3: 403(detail)  {booking_views.py:71-73}'; ret=$true },
    @{ t='op'; g='autorizado, válido y con plan' },
    @{ t='msg'; o='reserva';   d='triage';       n='2.3: check(preference)  {antes que todo: la preferencia es texto del paciente; booking_views.py:76; recorre EMERGENCY_SIGNALS y COMBINED_SIGNALS, triage.py:231-238}' },
    @{ t='msg'; o='triage';    d='reserva';      n='2.3.1: TriageResult(is_emergency, matched, message)'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='is_emergency' },
    @{ t='msg'; o='reserva';   d='pantalla';     n='4.1: _emergency_response(regla)  {_audit(emergency_layer = regla) y no busca turnos; booking_views.py:76-78}'; ret=$true },
    @{ t='op'; g='especialidad inexistente, inactiva o de otra organización' },
    @{ t='msg'; o='reserva';   d='pantalla';     n='2.2.4: 404(especialidad_invalida)  {Specialty.objects.filter(pk, organization, is_active), booking_views.py:80-88}'; ret=$true },
    @{ t='op'; g='sin urgencia y especialidad activa de la organización' },
    @{ t='msg'; o='reserva';   d='pref';         n='2.4: parse(text, today)  {reglas, sin modelo; sin día, hoy + 14 días; booking_views.py:90-91, preferences.py:105}' },
    @{ t='msg'; o='pref';      d='reserva';      n='2.4.1: Preferencia(date_from, date_to, days, part_of_day)'; ret=$true },
    @{ t='msg'; o='reserva';   d='oferta';       n='2.5: offer_slots(organization, specialty, preference, branch_id)  {hasta 6, máx. 3 por profesional; booking_views.py:92-94, offers.py:29-35}' },
    @{ t='msg'; o='oferta';    d='profesional';  n='2.6: filter(is_active, specialties)  {SELECT DISTINCT p.* FROM practitioners p JOIN practitioner_specialties ps ON ps.practitioner_id = p.id WHERE p.organization_id = :org AND p.is_active AND ps.specialty_id = :especialidad ORDER BY p.last_name, p.first_name; offers.py:42-48}' },
    @{ t='msg'; o='profesional'; d='oferta';     n='2.6.1: list(Practitioner)'; ret=$true },
    @{ t='loop'; g='por cada profesional activo de la especialidad' },
    @{ t='msg'; o='oferta';    d='agenda';       n='2.7: consolidated_availability(practitioner, desde, hasta)  {SELECT * FROM schedules WHERE practitioner_id = :p AND is_active AND valid_from <= :hasta AND (valid_until IS NULL OR valid_until >= :desde) [AND branch_id = :branch]; offers.py:51-59, availability.py:102, :128-140}' },
    @{ t='alt' },
    @{ t='op'; g='rango fuera del horizonte (ValidationError)' },
    @{ t='msg'; o='agenda';    d='oferta';       n='2.7.1: ValidationError()  {continue: los demás profesionales pueden tener; offers.py:60-63}'; ret=$true },
    @{ t='op'; g='disponibilidad del rango' },
    @{ t='msg'; o='agenda';    d='oferta';       n='2.7.2: dict(days, slots)  {sin los pasados, bloqueados ni ocupados; se queda con los reservable que preference.accepts(), offers.py:64-81}'; ret=$true },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='msg'; o='oferta';    d='reserva';      n='2.5.1: list(oferta)  {del más cercano al más lejano; offers.py:83-102}'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='not ofertas and not preferencia.is_empty' },
    @{ t='msg'; o='reserva';   d='pref';         n='2.8: relaxations(preference, today)  {mismo_dia, misma_franja, proximos; booking_views.py:100-101, preferences.py:166-185}' },
    @{ t='loop'; g='por cada (cual, relajada), hasta que offer_slots devuelva ofertas' },
    @{ t='msg'; o='pref';      d='reserva';      n='2.8.1: (cual, Preferencia relajada)  {con ella vuelve a offer_slots (2.5); si hay ofertas, alternativa = cual y break; booking_views.py:101-107}'; ret=$true },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='msg'; o='reserva';   d='reserva';      n='2.9: _redactar(especialidad, ofertas, alternativa)  {frase fija del backend, no del modelo; booking_views.py:113, :125-151}' },
    @{ t='msg'; o='reserva';   d='pantalla';     n='2.10: 200(offers, answer)  {emergency false, kind reserva, preference, matched_preference, relaxed; nada se guarda en el servidor; booking_views.py:110-122}'; ret=$true },
    @{ t='fin' },
    @{ t='fin' },

    # ===================================================================
    @{ t='nota'; txt='FLUJO 3 Confirmar y reservar' },
    @{ t='msg'; o='paciente';  d='pantalla';     n='3.1: elegir(oferta)  {tocar una tarjeta sólo abre la confirmación: _elegir, ConfirmarReservaSheet, assistant_screen.dart:220-234}' },
    @{ t='alt' },
    @{ t='op'; g='el paciente toca Reservar' },
    @{ t='msg'; o='paciente';  d='pantalla';     n='3.2: confirmar()  {confirmar_reserva_sheet.dart:74-77}' },
    @{ t='msg'; o='pantalla';  d='reserva';      n='3.3: book(request)  {POST /api/assistant/book/ (patient, practitioner, branch, schedule, starts_at); reservarDesdeAsistente, asistente.ts:139, assistant_api.dart:389; BookView.post, booking_views.py:159}' },
    @{ t='alt' },
    @{ t='op'; g='sin token o sin permiso assistant.suggest.use o appointments.appointment.create' },
    @{ t='msg'; o='reserva';   d='pantalla';     n='3.3.1: 403(detail)  {401 | 403; booking_views.py:157}'; ret=$true },
    @{ t='op'; g='cuerpo inválido' },
    @{ t='msg'; o='reserva';   d='pantalla';     n='3.3.2: 400(campo)  {booking_views.py:160-161}'; ret=$true },
    @{ t='op'; g='organization is None, plan sin ai_chatbot o sin ficha de paciente' },
    @{ t='msg'; o='reserva';   d='pantalla';     n='3.3.3: 403(detail)  {sin_ficha_de_paciente; booking_views.py:165-175}'; ret=$true },
    @{ t='op'; g='titular con ficha de paciente' },
    @{ t='msg'; o='reserva';   d='entpaciente';  n='3.4: filter(titular o a cargo)  {SELECT EXISTS (SELECT 1 FROM patients WHERE id = :paciente AND organization_id = :org AND is_active AND (id = :titular OR guardian_id = :titular)); booking_views.py:179-183}' },
    @{ t='msg'; o='entpaciente'; d='reserva';    n='3.4.1: bool()'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='not propio' },
    @{ t='msg'; o='reserva';   d='pantalla';     n='3.3.4: 404(paciente_invalido)  {un ajeno responde igual que uno que no existe; booking_views.py:184-188}'; ret=$true },
    @{ t='op'; g='tope max_appointments_month alcanzado' },
    @{ t='msg'; o='reserva';   d='pantalla';     n='3.3.5: 403(plan_limit)  {check_limit, booking_views.py:190-192}'; ret=$true },
    @{ t='op'; g='propio y dentro del tope' },
    @{ t='msg'; o='reserva';   d='booking';      n='3.5: book_appointment(patient, practitioner, starts_at)  {la misma reserva de CU18: SELECT * FROM schedules WHERE id = :schedule ... FOR UPDATE y _validate_slot_is_real; booking_views.py:194-203, booking.py:72, :111-127}' },
    @{ t='alt' },
    @{ t='op'; g='paciente, profesional, sucursal o agenda inválidos, turno pasado o que la agenda no tiene' },
    @{ t='msg'; o='booking';   d='reserva';      n='3.5.1: ValidationError(code)  {booking.py:83-107, :121-127, :53-69}'; ret=$true },
    @{ t='msg'; o='reserva';   d='pantalla';     n='3.3.6: 400(code, detail)  {booking_views.py:204-209}'; ret=$true },
    @{ t='op'; g='turno real y vigente' },
    @{ t='msg'; o='booking';   d='ficha';        n='3.6: create(status, expires_at)  {INSERT INTO appointments (organization_id, patient_id, booked_by_id, practitioner_id, branch_id, schedule_id, starts_at, ends_at, status = ''pending_payment'', expires_at = now + APPOINTMENT_HOLD_MINUTES); booking.py:130-141}' },
    @{ t='alt' },
    @{ t='op'; g='IntegrityError en uq_appointment_active_slot: otro lo tomó' },
    @{ t='msg'; o='booking';   d='reserva';      n='4.2: SlotAlreadyTaken()  {ofrecer no es apartar; booking.py:142-146}'; ret=$true },
    @{ t='msg'; o='reserva';   d='pantalla';     n='4.3: 409(detail)  {turno_ocupado, booking_views.py:210-215; la app avisa y vuelve a pedir turnos: assistant_screen.dart:256-262}'; ret=$true },
    @{ t='op'; g='INSERT sin choque' },
    @{ t='msg'; o='ficha';     d='booking';      n='3.6.1: Ficha(id, status = pending_payment, expires_at)'; ret=$true },
    @{ t='msg'; o='booking';   d='reserva';      n='3.5.2: Ficha()'; ret=$true },
    @{ t='msg'; o='reserva';   d='pantalla';     n='3.7: 201(ficha)  {AppointmentSerializer; bitácora assistant.booking sin texto del paciente; booking_views.py:217-222}'; ret=$true },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='op'; g='el paciente cancela' },
    @{ t='msg'; o='pantalla';  d='paciente';     n='3.1.1: cerrar()  {no se reserva nada; paraQuien == null, assistant_screen.dart:235}'; ret=$true },
    @{ t='fin' }
  )

  # Flujo de la transaccion (no el ciclo de vida de la ficha), desde que el
  # pedido llega a slots/ hasta que la ficha nace pending_payment.
  estado = @{
    estados = @(
      @{ k='ini';     tipo='inicial'; col=0; f=0 },
      @{ k='aut';     n='Autenticar Paciente';           col=0; f=2 },
      @{ k='fin403';  tipo='final';   col=0; f=4 },
      @{ k='finurg';  tipo='final';   col=1; f=0 },
      @{ k='tri';     n='Revisar urgencia';              col=1; f=2 },
      @{ k='pref';    n='Interpretar preferencia';       col=2; f=0.5 },
      @{ k='of';      n='Ofrecer horarios reales';       col=2; f=2 },
      @{ k='conf';    n='Elegir y confirmar';            col=3; f=1 },
      @{ k='rel';     n='Soltar la preferencia';         col=3; f=2.5 },
      @{ k='error';   n='Informar error';                col=3; f=4.5 },
      @{ k='res';     n='Reservar ficha';                col=4; f=1 },
      @{ k='ok';      n='Transacción completada';        col=4; f=3 },
      @{ k='fin';     tipo='final';   col=4; f=4.5 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='tri';    r='pedirTurnos(especialidad, preferencia) [token, assistant.suggest.use, scheduling.slot.read y plan con ai_chatbot] {booking_views.py:63, :73}' },
      @{ de='aut';   a='fin403'; r='[sin token, sin permiso, sin organización o plan sin ai_chatbot] {401 | 403}' },
      @{ de='tri';   a='finurg'; r='[triage.check(preference).is_emergency] / _emergency_response(regla): deriva a emergencias {booking_views.py:76-78}' },
      @{ de='tri';   a='pref';   r='[sin urgencia y especialidad activa] / parse(text, today) {booking_views.py:80-91}' },
      @{ de='tri';   a='error';  r='[especialidad inexistente, inactiva o ajena] {404 booking_views.py:83-88}' },
      @{ de='pref';  a='of';     r='/ offer_slots() sobre consolidated_availability {booking_views.py:92, offers.py:51-59}' },
      @{ de='of';    a='conf';   r='[hay ofertas o la preferencia está vacía] / 200(offers, answer) {booking_views.py:100, :110}' },
      @{ de='of';    a='rel';    r='[sin ofertas y preferencia no vacía] / relaxations() {booking_views.py:100-101}' },
      @{ de='rel';   a='conf';   r='/ relaxed = mismo_dia | misma_franja | proximos, o lista vacía {booking_views.py:101-108, preferences.py:176-185}' },
      @{ de='conf';  a='res';    r='confirmar() [eligió turno y para quién] / POST /api/assistant/book/ {Asistente.tsx:206, assistant_screen.dart:235-241}' },
      @{ de='conf';  a='ok';     r='[sin ofertas o cancela] / no se reserva nada {assistant_screen.dart:235}' },
      @{ de='res';   a='ok';     r='[propio, dentro del tope y sin choque] / INSERT status = pending_payment {booking.py:130-141, booking_views.py:217-222}' },
      @{ de='res';   a='error';  r='[sin ficha de paciente, ajeno, tope, ValidationError o SlotAlreadyTaken] {403, 404, 400, 409 booking_views.py:169-215}' },
      @{ de='error'; a='of';     r='reintentar() / _buscarTurnos(pedido) {Asistente.tsx:219-229, assistant_screen.dart:256-262}'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  # Escenario: el pedido ya trae la intencion de reservar, se ofrecen turnos,
  # el paciente confirma y la ficha nace pending_payment con su plazo.
  tiempo = @{
    escenario = 'pedir turno en lenguaje natural, ofrecer horarios, confirmar y que la ficha nazca pending_payment con su plazo de 15 minutos'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. El mensaje ya pide reservar («quiero una ficha de cardiología el jueves por la tarde»): suggest/ devuelve booking_intent (views.py:230) y la pantalla pide slots/ sola, con el mismo mensaje como preferencia (Asistente.tsx:148, assistant_screen.dart:174-180). slots/ sólo lee: pasa por Autenticando y Validando (triage.check y parse, booking_views.py:76, :91) y vuelve a Inactiva sin escribir. 14 días = DEFAULT_HORIZON_DAYS (preferences.py:26), la ventana de turnos cuando no se pide día. Ofrecer no es apartar (offers.py:9-11 del docstring): el turno sigue libre hasta el INSERT de book/, y si otro lo toma antes, SlotAlreadyTaken y 409 (booking.py:142-146). En book/, Validando es el paciente propio y el tope del plan (booking_views.py:179-192) y las comprobaciones de book_appointment antes de la transacción (booking.py:83-107); Escribiendo es el SELECT ... FOR UPDATE de la agenda, _validate_slot_is_real y el INSERT (booking.py:111-141). 15 min = APPOINTMENT_HOLD_MINUTES (config/settings.py:262), que fija expires_at al reservar (booking.py:140). Sólo el pago de CU19 la pasa a confirmed.'
    lineas = @(
      @{ n='Pantalla del asistente'
         estados=@('Escribiendo', 'Esperando', 'Mostrando ofertas', 'Confirmando', 'Reservada')
         marcas=@( @{ t=0;  e='Escribiendo' },
                   @{ t=4;  e='Esperando';         ev='suggest/' },
                   @{ t=26; e='Mostrando ofertas'; ev='200 offers' },
                   @{ t=36; e='Confirmando';       ev='elegir()' },
                   @{ t=46; e='Esperando';         ev='book/' },
                   @{ t=72; e='Reservada';         ev='201' } ) },
      @{ n='Transacción'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=10; e='Autenticando'; ev='slots/' },
                   @{ t=16; e='Validando';    ev='check()' },
                   @{ t=24; e='Inactiva';     ev='200' },
                   @{ t=48; e='Autenticando'; ev='book/' },
                   @{ t=54; e='Validando';    ev='filter()' },
                   @{ t=60; e='Escribiendo';  ev='FOR UPDATE' },
                   @{ t=66; e='Confirmada';   ev='COMMIT' },
                   @{ t=72; e='Inactiva';     ev='201' } ) },
      @{ n='Turno ofrecido'
         estados=@('Libre', 'Ofrecido', 'Ocupado')
         marcas=@( @{ t=0;  e='Libre' },
                   @{ t=20; e='Ofrecido'; ev='offer_slots()'; r='14 días' },
                   @{ t=66; e='Ocupado';  ev='INSERT' } ) },
      @{ n='Ficha'
         estados=@('Sin ficha', 'pending_payment')
         marcas=@( @{ t=0;  e='Sin ficha' },
                   @{ t=66; e='pending_payment'; ev='create()' } ) },
      @{ n='Plazo de reserva'
         estados=@('Sin plazo', 'Corriendo', 'Vencido')
         marcas=@( @{ t=0;  e='Sin plazo' },
                   @{ t=66; e='Corriendo'; ev='expires_at' },
                   @{ t=84; e='Vencido';   ev='sin pago'; r='15 min' } ) }
    )
  }
}
