"""US-50 — Finanzas por voz y área de contabilidad.

Lo que la historia tiene que cumplir:

- Ingresos, devoluciones, comisión de la pasarela, honorarios por profesional y
  gastos dan una utilidad que se puede sumar a mano.
- Un pago devuelto no se cuenta dos veces: suma en el mes en que se cobró y
  resta en el mes en que se devolvió.
- Agrupar (sede, médico, especialidad, día, semana, mes, trimestre) es solo
  presentación: la suma de los grupos es siempre el total.
- Todo va por moneda y por organización; otra organización no se ve.
- Solo la Administración con plan que incluya `accounting` entra.
- La voz traduce la frase a una consulta cerrada; las cifras las calcula
  Python y la frase dictada no queda en la bitácora.

Gemini nunca se llama de verdad: `voice.ask_model` se simula.
"""

import datetime as dt
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from accounts.models import AuditLog
from audit.actions import LABELS, Action
from catalog.models import (
    Practitioner, PractitionerBranch, PractitionerSpecialty, Specialty,
)
from payments.models import Payment
from reporting import finance, finance_voice, voice
from reporting.models import Expense
from tenancy.context import tenant_context

from .conftest import dar_rol
from .fichas_comunes import (  # noqa: F401 — fixtures
    agenda_a,
    api_client,
    autenticar,
    crear_ficha,
    paciente_a,
    perfil_paciente,
)

LA_PAZ = ZoneInfo("America/La_Paz")
PERMISOS_ADMIN = ["finance.accounting.read", "finance.expense.manage"]


def calcular(org, *args, **kwargs):
    with tenant_context(org.id):
        return finance.calcular(org, *args, **kwargs)


def con_comparacion(org, *args, **kwargs):
    with tenant_context(org.id):
        return finance.con_comparacion(org, *args, **kwargs)


def serie_de_meses(org, *args, **kwargs):
    with tenant_context(org.id):
        return finance.serie_de_meses(org, *args, **kwargs)


def interpretar(frase, usuario, **kwargs):
    with tenant_context(usuario.organization_id):
        return finance_voice.interpretar(frase, usuario, **kwargs)


def D(valor):
    return Decimal(str(valor))


def ahora_en(anio, mes, dia, hora=12, minuto=0):
    return dt.datetime(anio, mes, dia, hora, minuto, tzinfo=LA_PAZ)


# ==========================================================================
#  Datos
# ==========================================================================
@pytest.fixture
def admin_a(user_a, org_a):
    dar_rol(user_a, org_a, "admin-fin", "Administración", PERMISOS_ADMIN)
    return user_a


@pytest.fixture
def medico_b(org_a, branches_a, specialty_a):
    """Un segundo profesional, de otra especialidad y sin honorario."""
    with tenant_context(org_a.id):
        pediatria = Specialty.objects.create(organization=org_a, name="Pediatría")
        medico = Practitioner.objects.create(
            organization=org_a, first_name="Mario", last_name="Soto",
            license_number="MP-2000",
        )
        PractitionerBranch.objects.create(
            organization=org_a, practitioner=medico, branch=branches_a["norte"],
        )
        PractitionerSpecialty.objects.create(
            organization=org_a, practitioner=medico, specialty=pediatria,
        )
    return medico


class Caja:
    """Arma pagos con su ficha, un día distinto cada uno."""

    def __init__(self, org, paciente, agenda):
        self.org, self.paciente, self.agenda = org, paciente, agenda
        self.contador = 0

    def pago(self, medico, sede, monto, cuando, *, estado="succeeded",
             proveedor="stripe", moneda="BOB", devuelto_en=None):
        self.contador += 1
        inicio = cuando + dt.timedelta(days=60, hours=self.contador)
        ficha = crear_ficha(
            self.org, self.paciente, medico, sede, self.agenda, starts_at=inicio,
        )
        with tenant_context(self.org.id):
            return Payment.objects.create(
                organization=self.org, appointment=ficha,
                created_by=self.paciente, amount=D(monto), currency=moneda,
                provider=proveedor, status=estado, paid_at=cuando,
                refunded_at=devuelto_en,
            )


@pytest.fixture
def caja(org_a, paciente_a, agenda_a):
    return Caja(org_a, paciente_a, agenda_a)


def poner_gasto(org, sede, categoria, monto, dia, *, moneda="BOB", mes=10):
    with tenant_context(org.id):
        return Expense.objects.create(
            organization=org, branch=sede, category=categoria,
            amount=D(monto), currency=moneda, spent_on=dt.date(2026, mes, dia),
        )


def fijar(org, medico, *, honorario="0", pasarela="0"):
    with tenant_context(org.id):
        medico.fee_percent = D(honorario)
        medico.save(update_fields=["fee_percent"])
        ajustes = finance.ajustes_de(org)
        ajustes.stripe_percent = D(pasarela)
        ajustes.save()


@pytest.fixture
def octubre(org_a, caja, practitioner_a, medico_b, branches_a):
    """Octubre de 2026 con cifras que se suman a mano.

    Pasarela 4 %; la doctora Gómez cobra 10 % de honorario y Soto 0 %.

    - Gómez, Centro, 100 (Stripe)            comisión 4,00  honorario 10,00
    - Soto,  Norte,  50  (efectivo)          sin comisión   sin honorario
    - Gómez, Centro, 200 (Stripe, devuelto en octubre)  sin comisión ni honorario
    - gastos: 30 en Centro (insumos) y 20 generales (alquiler)

    ingresos 350 · devoluciones 200 · comisión 4 · honorarios 10 · gastos 50
    utilidad = 350 − 200 − 4 − 10 − 50 = 86
    """
    with tenant_context(org_a.id):
        practitioner_a.refresh_from_db()
    fijar(org_a, practitioner_a, honorario="10", pasarela="4")
    centro, norte = branches_a["centro"], branches_a["norte"]
    caja.pago(practitioner_a, centro, "100.00", ahora_en(2026, 10, 5))
    caja.pago(medico_b, norte, "50.00", ahora_en(2026, 10, 12), proveedor="cash")
    caja.pago(practitioner_a, centro, "200.00", ahora_en(2026, 10, 20),
              estado="refunded", devuelto_en=ahora_en(2026, 10, 22))
    poner_gasto(org_a, centro, "insumos", "30.00", 8)
    poner_gasto(org_a, None, "alquiler", "20.00", 1)
    return {"desde": dt.date(2026, 10, 1), "hasta": dt.date(2026, 10, 31)}


def totales(datos, moneda="BOB"):
    return next(m for m in datos["currencies"] if m["currency"] == moneda)["totals"]


# ==========================================================================
#  El cálculo
# ==========================================================================
def test_la_utilidad_se_suma_a_mano(org_a, octubre):
    datos = calcular(org_a, octubre["desde"], octubre["hasta"])

    t = totales(datos)
    assert t["ingresos"] == "350.00"
    assert t["devoluciones"] == "200.00"
    assert t["neto"] == "150.00"
    assert t["comision"] == "4.00"
    assert t["honorarios"] == "10.00"
    assert t["gastos"] == "50.00"
    assert t["utilidad"] == "86.00"
    assert t["pagos"] == 3
    assert t["ticket_promedio"] == "116.67"


def test_el_efectivo_no_paga_comision_y_lo_devuelto_tampoco(org_a, octubre):
    # Solo el primer pago (Stripe, 100, no devuelto) lleva comisión: 4 %.
    t = totales(calcular(org_a, octubre["desde"], octubre["hasta"]))
    assert t["comision"] == "4.00"


def test_sin_pasarela_ni_honorario_no_hay_descuentos(
    org_a, caja, practitioner_a, branches_a,
):
    caja.pago(practitioner_a, branches_a["centro"], "80.00", ahora_en(2026, 10, 3))
    t = totales(calcular(org_a, dt.date(2026, 10, 1), dt.date(2026, 10, 31)))
    assert (t["comision"], t["honorarios"], t["utilidad"]) == ("0.00", "0.00", "80.00")


def test_un_pago_devuelto_otro_mes_suma_en_uno_y_resta_en_el_otro(
    org_a, caja, practitioner_a, branches_a,
):
    caja.pago(practitioner_a, branches_a["centro"], "100.00",
              ahora_en(2026, 10, 15), estado="refunded",
              devuelto_en=ahora_en(2026, 11, 3))

    octubre_ = totales(calcular(org_a, dt.date(2026, 10, 1), dt.date(2026, 10, 31)))
    noviembre = totales(calcular(org_a, dt.date(2026, 11, 1), dt.date(2026, 11, 30)))

    assert (octubre_["ingresos"], octubre_["devoluciones"]) == ("100.00", "0.00")
    assert (noviembre["ingresos"], noviembre["devoluciones"]) == ("0.00", "100.00")
    # Entre los dos meses el pago no deja nada: 100 − 100.
    assert D(octubre_["utilidad"]) + D(noviembre["utilidad"]) == 0


def test_un_periodo_sin_datos_da_cero_y_no_error(org_a):
    datos = calcular(org_a, dt.date(2020, 1, 1), dt.date(2020, 1, 31))
    assert datos["currencies"] == []


def test_cada_moneda_va_por_separado(org_a, caja, practitioner_a, branches_a):
    centro = branches_a["centro"]
    caja.pago(practitioner_a, centro, "100.00", ahora_en(2026, 10, 3))
    caja.pago(practitioner_a, centro, "30.00", ahora_en(2026, 10, 4), moneda="USD")
    datos = calcular(org_a, dt.date(2026, 10, 1), dt.date(2026, 10, 31))
    assert [m["currency"] for m in datos["currencies"]] == ["BOB", "USD"]
    assert totales(datos, "BOB")["ingresos"] == "100.00"
    assert totales(datos, "USD")["ingresos"] == "30.00"


def test_el_honorario_va_con_el_profesional_y_se_redondea_al_centavo(
    org_a, caja, practitioner_a, branches_a,
):
    fijar(org_a, practitioner_a, honorario="33.33")
    caja.pago(practitioner_a, branches_a["centro"], "10.00", ahora_en(2026, 10, 3))
    t = totales(calcular(org_a, dt.date(2026, 10, 1), dt.date(2026, 10, 31)))
    assert t["honorarios"] == "3.33"


def test_el_filtro_por_medico_deja_afuera_los_gastos(org_a, octubre, practitioner_a):
    datos = calcular(
        org_a, octubre["desde"], octubre["hasta"], practitioner_id=practitioner_a.id,
    )
    t = totales(datos)
    assert t["ingresos"] == "300.00" and t["gastos"] == "0.00"


def test_el_filtro_por_sede_incluye_sus_gastos_pero_no_los_generales(
    org_a, octubre, branches_a,
):
    t = totales(calcular(
        org_a, octubre["desde"], octubre["hasta"], branch_id=branches_a["centro"].id,
    ))
    assert t["ingresos"] == "300.00" and t["gastos"] == "30.00"


# ==========================================================================
#  Agrupar
# ==========================================================================
@pytest.mark.parametrize("agrupar", finance.AGRUPACIONES)
def test_la_suma_de_los_grupos_es_el_total(org_a, octubre, agrupar):
    datos = calcular(
        org_a, octubre["desde"], octubre["hasta"], agrupar=agrupar,
    )
    moneda = datos["currencies"][0]
    assert moneda["groups"], agrupar
    for campo in ("ingresos", "devoluciones", "comision", "honorarios",
                  "gastos", "utilidad"):
        assert sum(D(g[campo]) for g in moneda["groups"]) == D(moneda["totals"][campo]), (
            agrupar, campo,
        )
    assert sum(g["pagos"] for g in moneda["groups"]) == moneda["totals"]["pagos"]


def test_por_sede_los_gastos_generales_tienen_su_grupo(org_a, octubre):
    datos = calcular(org_a, octubre["desde"], octubre["hasta"], agrupar="sede")
    por_nombre = {g["label"]: g for g in datos["currencies"][0]["groups"]}
    assert set(por_nombre) == {"Sede Centro", "Sede Norte", finance.GASTOS_GENERALES}
    assert por_nombre["Sede Centro"]["gastos"] == "30.00"
    assert por_nombre[finance.GASTOS_GENERALES]["gastos"] == "20.00"
    assert por_nombre["Sede Norte"]["ingresos"] == "50.00"


def test_por_medico_y_por_especialidad(org_a, octubre):
    por_medico = calcular(
        org_a, octubre["desde"], octubre["hasta"], agrupar="medico",
    )["currencies"][0]["groups"]
    assert {g["label"]: g["ingresos"] for g in por_medico}["Laura Gómez"] == "300.00"

    por_especialidad = calcular(
        org_a, octubre["desde"], octubre["hasta"], agrupar="especialidad",
    )["currencies"][0]["groups"]
    nombres = {g["label"] for g in por_especialidad}
    assert {"Cardiología", "Pediatría"} <= nombres


def test_los_cortes_de_dia_semana_mes_y_trimestre_son_de_la_zona_del_centro(
    org_a, caja, practitioner_a, branches_a,
):
    # 31/10 a las 23:30 en La Paz es 01/11 03:30 UTC: sigue siendo octubre.
    caja.pago(practitioner_a, branches_a["centro"], "10.00",
              ahora_en(2026, 10, 31, 23, 30))
    desde, hasta = dt.date(2026, 10, 1), dt.date(2026, 11, 30)

    def claves(agrupar):
        datos = calcular(org_a, desde, hasta, agrupar=agrupar)
        return [g["key"] for g in datos["currencies"][0]["groups"]]

    assert claves("dia") == ["2026-10-31"]
    assert claves("semana") == ["2026-10-26"]
    assert claves("mes") == ["2026-10"]
    assert claves("trimestre") == ["2026-T4"]


def test_una_agrupacion_desconocida_se_rechaza(org_a):
    with pytest.raises(ValueError):
        calcular(org_a, dt.date(2026, 10, 1), dt.date(2026, 10, 31),
                         agrupar="color")


# ==========================================================================
#  Comparar y la serie
# ==========================================================================
def test_el_periodo_anterior_tiene_la_misma_duracion():
    assert finance.periodo_anterior(dt.date(2026, 11, 1), dt.date(2026, 11, 30)) == (
        dt.date(2026, 10, 2), dt.date(2026, 10, 31),
    )


def test_comparar_da_la_variacion_y_no_divide_por_cero(
    org_a, caja, practitioner_a, branches_a,
):
    centro = branches_a["centro"]
    caja.pago(practitioner_a, centro, "100.00", ahora_en(2026, 10, 10))
    caja.pago(practitioner_a, centro, "150.00", ahora_en(2026, 11, 10))
    datos = con_comparacion(
        org_a, dt.date(2026, 11, 1), dt.date(2026, 11, 30),
    )
    cambio = datos["currencies"][0]["compare"]["change_percent"]
    # El período anterior es 02/10–31/10: 100 → 150 es +50 %.
    assert cambio["ingresos"] == "50.00"
    # No había devoluciones antes: sin base, sin porcentaje.
    assert cambio["devoluciones"] is None


def test_la_serie_trae_seis_meses_con_ceros_en_los_vacios(
    org_a, caja, practitioner_a, branches_a,
):
    caja.pago(practitioner_a, branches_a["centro"], "40.00", ahora_en(2026, 9, 10))
    serie = serie_de_meses(org_a, dt.date(2026, 11, 20))
    assert serie["months"] == [
        "2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11",
    ]
    meses = serie["currencies"][0]["months"]
    assert [m["ingresos"] for m in meses] == [
        "0.00", "0.00", "0.00", "40.00", "0.00", "0.00",
    ]


# ==========================================================================
#  La API: permisos, plan y aislamiento
# ==========================================================================
def resumen(cliente, **params):
    return cliente.get(reverse("reporting:finance-summary"), params)


def test_la_administracion_ve_el_resumen(api_client, admin_a, octubre):
    respuesta = resumen(autenticar(api_client, admin_a),
                        **{"from": "2026-10-01", "to": "2026-10-31", "group": "sede",
                           "compare": "1"})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["currencies"][0]["totals"]["utilidad"] == "86.00"
    assert "compare" in cuerpo["currencies"][0]
    assert cuerpo["group_by"] == "sede"


def test_quien_no_tiene_el_permiso_recibe_403(api_client, user_a, org_a, octubre):
    dar_rol(user_a, org_a, "recepcion", "Recepción", ["reporting.kpi.read"])
    respuesta = resumen(autenticar(api_client, user_a),
                        **{"from": "2026-10-01", "to": "2026-10-31"})
    assert respuesta.status_code == 403


def test_el_plan_basico_no_incluye_la_contabilidad(api_client, user_b, org_b):
    dar_rol(user_b, org_b, "admin-fin", "Administración", PERMISOS_ADMIN)
    respuesta = resumen(autenticar(api_client, user_b))
    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "plan_limit"


def test_los_planes_pro_y_premium_la_incluyen_y_el_basico_no(plans):
    assert plans["basic"].features["accounting"] is False
    assert plans["pro"].features["accounting"] is True
    assert plans["premium"].features["accounting"] is True


def test_los_permisos_nuevos_son_solo_de_la_administracion(db):
    from accounts.models import Role, RolePermission
    from tenancy.context import platform_admin_context

    with platform_admin_context():
        concedidos = {
            (rol.code, rp.permission.code)
            for rol in Role.objects.filter(organization__isnull=True, is_system=True)
            for rp in RolePermission.objects.filter(role=rol).select_related("permission")
            if rp.permission.code.startswith("finance.")
        }
    assert {c for r, c in concedidos if r == "org_admin"} == set(PERMISOS_ADMIN)
    assert not [r for r, _ in concedidos if r != "org_admin"]


@pytest.mark.parametrize("params", [
    {"from": "2026-13-01"},
    {"from": "2026-10-31", "to": "2026-10-01"},
    {"from": "2024-01-01", "to": "2026-10-01"},
    {"group": "color"},
    {"branch": "no-es-uuid"},
    {"practitioner": "no-es-uuid"},
])
def test_los_parametros_invalidos_dan_400(api_client, admin_a, params):
    assert resumen(autenticar(api_client, admin_a), **params).status_code == 400


def test_otra_organizacion_no_se_ve(
    api_client, admin_a, org_a, org_b, branch_b, octubre,
):
    with tenant_context(org_b.id):
        Expense.objects.create(
            organization=org_b, branch=branch_b, category="insumos",
            amount=D("999.00"), currency="BOB", spent_on=dt.date(2026, 10, 10),
        )
    cliente = autenticar(api_client, admin_a)
    resp = resumen(cliente, **{"from": "2026-10-01", "to": "2026-10-31"})
    assert resp.json()["currencies"][0]["totals"]["gastos"] == "50.00"

    lista = cliente.get(reverse("reporting:finance-expenses"),
                        {"from": "2026-10-01", "to": "2026-10-31"})
    assert len(lista.json()) == 2

    # Ni pidiendo la sucursal de la otra organización.
    ajena = resumen(cliente, branch=str(branch_b.id),
                    **{"from": "2026-10-01", "to": "2026-10-31"})
    assert ajena.status_code == 400


# ==========================================================================
#  Gastos y ajustes
# ==========================================================================
def nuevo_gasto(cliente, **extra):
    cuerpo = {"category": "insumos", "amount": "45.50", "currency": "bob",
              "spent_on": "2026-10-15", **extra}
    return cliente.post(reverse("reporting:finance-expenses"), cuerpo, format="json")


def test_cargar_editar_y_borrar_un_gasto_deja_asiento(
    api_client, admin_a, org_a, branches_a,
):
    cliente = autenticar(api_client, admin_a)
    creado = nuevo_gasto(cliente, branch=str(branches_a["centro"].id), note="Guantes")
    assert creado.status_code == 201, creado.content
    assert creado.json()["currency"] == "BOB"
    gasto_id = creado.json()["id"]

    editado = cliente.patch(reverse("reporting:finance-expense", args=[gasto_id]),
                            {"amount": "60.00"}, format="json")
    assert editado.status_code == 200 and editado.json()["amount"] == "60.00"

    borrado = cliente.delete(reverse("reporting:finance-expense", args=[gasto_id]))
    assert borrado.status_code == 204

    with tenant_context(org_a.id):
        acciones = set(AuditLog.objects.filter(
            action__startswith="finance.expense").values_list("action", flat=True))
    assert acciones == {Action.FINANCE_EXPENSE_CREATE, Action.FINANCE_EXPENSE_UPDATE,
                        Action.FINANCE_EXPENSE_DELETE}


@pytest.mark.parametrize("extra", [
    {"amount": "-5"},
    {"amount": "0"},
    {"currency": "BOLIV"},
    {"currency": "1"},
    {"category": "yates"},
    {"spent_on": "1999-01-01"},
    {"spent_on": "2099-01-01"},
])
def test_un_gasto_con_datos_malos_se_rechaza(api_client, admin_a, extra):
    assert nuevo_gasto(autenticar(api_client, admin_a), **extra).status_code == 400


def test_un_gasto_no_se_cuelga_de_la_sucursal_de_otra_organizacion(
    api_client, admin_a, branch_b,
):
    respuesta = nuevo_gasto(autenticar(api_client, admin_a), branch=str(branch_b.id))
    assert respuesta.status_code == 400


def test_ver_no_es_cargar(api_client, user_a, org_a):
    dar_rol(user_a, org_a, "solo-ver", "Contador", ["finance.accounting.read"])
    cliente = autenticar(api_client, user_a)
    assert nuevo_gasto(cliente).status_code == 403
    lectura = cliente.get(reverse("reporting:finance-expenses"))
    assert lectura.status_code == 200


def test_la_comision_se_guarda_y_se_aplica(
    api_client, admin_a, org_a, caja, practitioner_a, branches_a,
):
    cliente = autenticar(api_client, admin_a)
    assert cliente.get(reverse("reporting:finance-settings")).json() == {"stripe_percent": "0.00"}
    guardado = cliente.put(reverse("reporting:finance-settings"), {"stripe_percent": "3.60"},
                           format="json")
    assert guardado.status_code == 200 and guardado.json()["stripe_percent"] == "3.60"

    caja.pago(practitioner_a, branches_a["centro"], "100.00", ahora_en(2026, 10, 3))
    t = totales(calcular(org_a, dt.date(2026, 10, 1), dt.date(2026, 10, 31)))
    assert t["comision"] == "3.60"


@pytest.mark.parametrize("valor", ["-1", "100.01", "abc"])
def test_la_comision_fuera_de_rango_se_rechaza(api_client, admin_a, valor):
    respuesta = autenticar(api_client, admin_a).put(
        reverse("reporting:finance-settings"), {"stripe_percent": valor}, format="json",
    )
    assert respuesta.status_code == 400


@pytest.mark.parametrize("valor", [-1, 101])
def test_el_honorario_tiene_que_estar_entre_0_y_100(practitioner_a, org_a, valor):
    with tenant_context(org_a.id):
        practitioner_a.fee_percent = valor
        with pytest.raises(ValidationError):
            practitioner_a.full_clean()


def test_el_honorario_solo_lo_cambia_quien_maneja_la_contabilidad(
    api_client, user_a, org_a, practitioner_a,
):
    dar_rol(user_a, org_a, "catalogo", "Catálogo", [
        "catalog.professional.read", "catalog.professional.update",
        "finance.accounting.read",
    ])
    respuesta = autenticar(api_client, user_a).patch(
        reverse("catalog:professional-detail", args=[practitioner_a.id]),
        {"fee_percent": "15"}, format="json",
    )
    assert respuesta.status_code == 400


def test_exportar_en_csv_xlsx_y_pdf(api_client, admin_a, octubre):
    cliente = autenticar(api_client, admin_a)
    base = {"from": "2026-10-01", "to": "2026-10-31", "group": "sede"}
    for formato, firma in (("csv", b"Grupo"), ("xlsx", b"PK"), ("pdf", b"%PDF")):
        respuesta = cliente.get(reverse("reporting:finance-export"), {**base, "file": formato})
        assert respuesta.status_code == 200, formato
        assert firma in respuesta.content[:200] or firma in respuesta.content, formato
    assert cliente.get(reverse("reporting:finance-export"),
                       {**base, "file": "doc"}).status_code == 400


def test_exportar_deja_asiento(api_client, admin_a, org_a, octubre):
    autenticar(api_client, admin_a).get(
        reverse("reporting:finance-export"),
        {"from": "2026-10-01", "to": "2026-10-31", "file": "csv"},
    )
    with tenant_context(org_a.id):
        assert AuditLog.objects.filter(action=Action.FINANCE_EXPORT).count() == 1


def test_las_acciones_nuevas_tienen_etiqueta(db):
    for accion in (Action.FINANCE_QUERY, Action.FINANCE_EXPORT,
                   Action.FINANCE_EXPENSE_CREATE, Action.FINANCE_EXPENSE_UPDATE,
                   Action.FINANCE_EXPENSE_DELETE, Action.FINANCE_SETTINGS_UPDATE):
        assert accion in LABELS


# ==========================================================================
#  La voz
# ==========================================================================
HOY = dt.date(2026, 11, 20)
SEDES = [("s1", "Sede Centro"), ("s2", "Sede Norte")]
MEDICOS = [("m1", "Laura", "Gómez"), ("m2", "Mario", "Soto")]


def leer(frase):
    return finance_voice.analizar(frase, HOY, SEDES, MEDICOS)


def test_cuanto_ganamos_este_mes_es_la_utilidad_del_mes():
    consulta, motivos = leer("cuánto ganamos este mes")
    assert motivos == []
    assert consulta["metrica"] == "utilidad"
    assert (consulta["desde"], consulta["hasta"]) == ("2026-11-01", "2026-11-30")


def test_utilidad_por_sede_del_mes_pasado():
    consulta, _ = leer("utilidad por sede del mes pasado")
    assert consulta["agrupar"] == "sede"
    assert (consulta["desde"], consulta["hasta"]) == ("2026-10-01", "2026-10-31")


def test_cuanto_facturo_la_doctora_en_octubre():
    consulta, motivos = leer("cuánto facturó la doctora Gómez en octubre")
    assert motivos == []
    assert consulta["metrica"] == "ingresos"
    assert consulta["profesional"] == "m1"
    assert consulta["profesional_nombre"] == "Laura Gómez"
    assert (consulta["desde"], consulta["hasta"]) == ("2026-10-01", "2026-10-31")


def test_compara_este_mes_con_el_anterior():
    consulta, motivos = leer("compará este mes con el anterior")
    assert motivos == []
    assert consulta["comparar"] is True and consulta["metrica"] == "utilidad"
    assert consulta["desde"] == "2026-11-01"


def test_gastos_de_una_sede_los_ultimos_tres_meses_por_semana():
    consulta, motivos = leer(
        "gastos de insumos de la sede Norte de los últimos 3 meses por semana"
    )
    assert motivos == []
    assert consulta["metrica"] == "gastos"
    assert consulta["sede"] == "s2" and consulta["agrupar"] == "semana"
    assert (consulta["desde"], consulta["hasta"]) == ("2026-08-20", "2026-11-20")


@pytest.mark.parametrize("frase,desde,hasta", [
    ("ingresos de hoy", "2026-11-20", "2026-11-20"),
    ("ingresos de ayer", "2026-11-19", "2026-11-19"),
    ("ingresos de esta semana", "2026-11-16", "2026-11-20"),
    ("ingresos de la semana pasada", "2026-11-09", "2026-11-15"),
    ("ingresos de los últimos 15 días", "2026-11-06", "2026-11-20"),
    ("ingresos de las últimas 4 semanas", "2026-10-24", "2026-11-20"),
])
def test_los_periodos_cortos(frase, desde, hasta):
    consulta, motivos = leer(frase)
    assert motivos == []
    assert (consulta["desde"], consulta["hasta"]) == (desde, hasta)


@pytest.mark.parametrize("frase,agrupar", [
    ("ingresos por día", "dia"), ("ingresos por semana", "semana"),
    ("ingresos por mes", "mes"), ("ingresos por trimestre", "trimestre"),
    ("ingresos por médico", "medico"), ("ingresos por especialidad", "especialidad"),
    ("ingresos por sucursal", "sede"), ("ingresos agrupados por sede", "sede"),
])
def test_las_agrupaciones(frase, agrupar):
    consulta, motivos = leer(frase)
    assert motivos == [] and consulta["agrupar"] == agrupar


@pytest.mark.parametrize("frase", [
    "",
    "hola",
    "ingresos y gastos de este mes",
    "ingresos por sede y por médico",
    "ingresos de la doctora Pérez",
    "ingresos de enero y marzo",
    "agrupá los ingresos",
])
def test_lo_que_no_se_entiende_se_dice_y_no_se_ejecuta(frase):
    consulta, motivos = leer(frase)
    assert consulta is None and motivos


def test_sin_proveedor_interpretar_calcula_y_resume(admin_a, org_a, octubre):
    respuesta = interpretar(
        "utilidad de octubre por sede", admin_a, hoy=dt.date(2026, 11, 20),
    )
    assert respuesta["understood"] is True
    assert respuesta["generated_by"] == "plantilla"
    assert respuesta["result"]["currencies"][0]["totals"]["utilidad"] == "86.00"
    frase = respuesta["spoken_summary"]
    assert frase.startswith("La utilidad del 01/10/2026 al 31/10/2026: BOB 86,00")
    assert "Por grupo:" in frase


def test_la_frase_de_respuesta_dice_cuando_no_hay_movimientos(admin_a, org_a):
    respuesta = interpretar(
        "ingresos de enero", admin_a, hoy=dt.date(2026, 11, 20),
    )
    assert respuesta["understood"] is True
    assert respuesta["spoken_summary"].startswith("No hay movimientos")


def test_la_comparacion_entra_en_la_frase(admin_a, org_a, caja, practitioner_a,
                                          branches_a):
    centro = branches_a["centro"]
    caja.pago(practitioner_a, centro, "100.00", ahora_en(2026, 10, 10))
    caja.pago(practitioner_a, centro, "150.00", ahora_en(2026, 11, 10))
    respuesta = interpretar(
        "ingresos de este mes comparado con el período anterior", admin_a,
        hoy=dt.date(2026, 11, 20),
    )
    assert respuesta["understood"] is True
    assert "50,00 % más que el período anterior" in respuesta["spoken_summary"]


def test_el_modelo_no_decide_la_agrupacion_ni_ve_los_nombres(
    admin_a, org_a, octubre, monkeypatch,
):
    recibido = {}

    def falso(system_prompt, prompt):
        recibido["prompt"] = prompt
        # Intenta colar una agrupación y una sede que la frase no pidió.
        return ({"metrica": "ingresos", "desde": "2026-10-01",
                 "hasta": "2026-10-31", "comparar": False,
                 "agrupar": "medico", "sede": "otra"}, "gemini")

    monkeypatch.setattr(voice, "ask_model", falso)
    respuesta = interpretar(
        "cuánto facturó la doctora Gómez por sede en octubre", admin_a,
        hoy=dt.date(2026, 11, 20),
    )

    assert respuesta["generated_by"] == "gemini"
    consulta = respuesta["query"]
    assert consulta["agrupar"] == "sede"          # lo decidió Python
    assert consulta["profesional_nombre"] == "Laura Gómez"
    assert consulta["sede"] is None
    for secreto in ("Gómez", "gómez", "gomez", "por sede"):
        assert secreto not in recibido["prompt"]
    assert respuesta["result"]["currencies"][0]["totals"]["ingresos"] == "300.00"


@pytest.mark.parametrize("crudo", [
    None, "texto", [], {}, {"metrica": "plata"}, {"metrica": "ingresos", "desde": "x",
                                                  "hasta": "2026-10-01"},
    {"metrica": "ingresos", "desde": "2026-10-31", "hasta": "2026-10-01"},
])
def test_una_respuesta_rara_del_modelo_no_ejecuta_nada(crudo):
    consulta, motivos = finance_voice.sanear(crudo, HOY, None, None, None, False)
    assert consulta is None and motivos


def test_si_el_modelo_falla_se_usa_el_analizador_local(admin_a, org_a, octubre,
                                                       monkeypatch):
    monkeypatch.setattr(voice, "ask_model", lambda *_: (None, "plantilla"))
    respuesta = interpretar(
        "ingresos de octubre", admin_a, hoy=dt.date(2026, 11, 20),
    )
    assert respuesta["generated_by"] == "plantilla" and respuesta["understood"]


def test_la_frase_no_queda_en_la_bitacora(api_client, admin_a, org_a, octubre):
    cliente = autenticar(api_client, admin_a)
    respuesta = cliente.post(
        reverse("reporting:finance-interpret"),
        {"text": "cuánto facturó la doctora Gómez en octubre"}, format="json",
    )
    assert respuesta.status_code == 200 and respuesta.json()["understood"] is True

    with tenant_context(org_a.id):
        asiento = AuditLog.objects.filter(action=Action.FINANCE_QUERY).get()
    assert asiento.detail["metrica"] == "ingresos" and asiento.detail["voz"] is True
    for pedazo in ("Gómez", "gomez", "doctora", "octubre", "facturó"):
        assert pedazo not in str(asiento.detail)


def test_interpretar_exige_permiso_y_plan(api_client, user_a, org_a, user_b, org_b):
    dar_rol(user_a, org_a, "recepcion", "Recepción", ["reporting.kpi.read"])
    sin_permiso = autenticar(api_client, user_a).post(
        reverse("reporting:finance-interpret"), {"text": "ingresos"}, format="json",
    )
    assert sin_permiso.status_code == 403

    dar_rol(user_b, org_b, "admin-fin", "Administración", PERMISOS_ADMIN)
    sin_plan = autenticar(api_client, user_b).post(
        reverse("reporting:finance-interpret"), {"text": "ingresos"}, format="json",
    )
    assert sin_plan.status_code == 403 and sin_plan.json()["code"] == "plan_limit"


def test_una_frase_muy_larga_se_rechaza(api_client, admin_a):
    respuesta = autenticar(api_client, admin_a).post(
        reverse("reporting:finance-interpret"), {"text": "x" * 301}, format="json",
    )
    assert respuesta.status_code == 400
