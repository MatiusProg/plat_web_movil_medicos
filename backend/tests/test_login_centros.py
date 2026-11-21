"""El desplegable de centros médicos del login (21/11/26).

Lo público es sólo el nombre y el slug de las organizaciones **activas**: una
suspendida o inactiva no aparece (y tampoco puede entrar, por
`app_resolve_tenant`). Ningún otro dato de la organización sale por acá.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from tenancy.context import platform_admin_context
from tenancy.models import Organization

URL = reverse("accounts:centers")


@pytest.fixture
def anonimo():
    return APIClient()


def _crear(slug, nombre, estado=Organization.Status.ACTIVE, nit="9"):
    with platform_admin_context():
        return Organization.objects.create(
            slug=slug, name=nombre, legal_name=f"{nombre} SRL", tax_id=nit,
            contact_email=f"c@{slug}.test", status=estado,
        )


def test_sin_sesion_lista_las_activas_por_nombre(anonimo, org_a, org_b):
    _crear("andina", "Andina", nit="3")
    r = anonimo.get(URL)
    assert r.status_code == 200
    assert r.json() == [
        {"slug": "andina", "name": "Andina"},
        {"slug": "kolping", "name": "Kolping"},
        {"slug": "sanluis", "name": "San Luis"},
    ]


def test_suspendidas_e_inactivas_no_aparecen(anonimo, org_a):
    _crear("pausada", "Pausada", Organization.Status.SUSPENDED, nit="4")
    _crear("cerrada", "Cerrada", Organization.Status.INACTIVE, nit="5")
    assert [c["slug"] for c in anonimo.get(URL).json()] == ["kolping"]


def test_al_suspender_desaparece_sola(anonimo, org_a, org_b):
    with platform_admin_context():
        Organization.objects.filter(id=org_b.id).update(
            status=Organization.Status.SUSPENDED)
    assert [c["slug"] for c in anonimo.get(URL).json()] == ["kolping"]


def test_no_expone_nada_mas_que_nombre_y_slug(anonimo, org_a):
    fila = anonimo.get(URL).json()[0]
    assert set(fila) == {"slug", "name"}
    # Ni el NIT, ni el correo, ni el id interno.
    texto = str(anonimo.get(URL).content)
    assert "1001" not in texto and "contacto@" not in texto
    assert str(org_a.id) not in texto


def test_sin_organizaciones_devuelve_lista_vacia(anonimo, db):
    assert anonimo.get(URL).json() == []


def test_es_solo_lectura(anonimo, org_a):
    assert anonimo.post(URL, {"slug": "x", "name": "X"}).status_code == 405
