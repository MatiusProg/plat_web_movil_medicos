"""La paginación de las listas (config/pagination.py).

Lo que se rompió el 03/10/26: con ~80 usuarios por organización, la pantalla
de usuarios mostraba 25 sin avisar, el filtro de actor de la bitácora ofrecía
25, y el móvil no podía quitarle el rol a la mayoría porque traía 25
asignaciones de ≥80.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User, UserRole
from accounts.tokens import tokens_for_user
from tenancy.context import tenant_context

from .conftest import dar_rol

pytestmark = pytest.mark.django_db


@pytest.fixture
def ochenta_usuarios(org_a, user_a):
    rol = dar_rol(user_a, org_a, "lector", "Lector", ["users.user.read", "users.role.read", "users.role.assign"])
    with tenant_context(org_a.id):
        for i in range(80):
            u = User.objects.create_user(
                email=f"persona{i:02d}@kolping.test", password="clave-de-prueba-1",
                organization=org_a, first_name="Persona", last_name=f"Número {i:02d}",
                document_number=f"8{i:03d}",
            )
            UserRole.objects.create(user=u, role=rol, organization=org_a)
    return user_a


def cliente(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}")
    return client


def test_por_defecto_son_25_por_pagina(ochenta_usuarios):
    datos = cliente(ochenta_usuarios).get(reverse("accounts:user-list")).json()
    assert datos["count"] == 81
    assert len(datos["results"]) == 25
    assert datos["next"] is not None


def test_el_cliente_puede_pedir_paginas_de_hasta_cien(ochenta_usuarios):
    datos = cliente(ochenta_usuarios).get(reverse("accounts:user-list"), {"page_size": 100}).json()
    assert len(datos["results"]) == 81
    assert datos["next"] is None


def test_page_size_no_pasa_de_cien(ochenta_usuarios):
    """Sin tope, ?page_size=1000000 sería una consulta sin límite."""
    datos = cliente(ochenta_usuarios).get(
        reverse("accounts:user-list"), {"page_size": 1_000_000, "page": 1},
    ).json()
    assert len(datos["results"]) == 81   # 81 < 100: entra todo, pero el tope existe
    from config.pagination import Paginacion
    assert Paginacion.max_page_size == 100


def test_recorrer_las_paginas_trae_a_todos_sin_repetir(ochenta_usuarios):
    api, vistos, pagina = cliente(ochenta_usuarios), [], 1
    while True:
        datos = api.get(reverse("accounts:user-list"), {"page": pagina}).json()
        vistos += [u["id"] for u in datos["results"]]
        if not datos["next"]:
            break
        pagina += 1
    assert len(vistos) == 81 == len(set(vistos))


def test_las_asignaciones_tienen_orden_estable(ochenta_usuarios):
    """Sin orden, una asignación podía caer en dos páginas o en ninguna."""
    api, vistas, pagina = cliente(ochenta_usuarios), [], 1
    while True:
        datos = api.get(reverse("accounts:user_role-list"), {"page": pagina}).json()
        vistas += [a["id"] for a in datos["results"]]
        if not datos["next"]:
            break
        pagina += 1
    assert len(vistas) == len(set(vistas))
    assert UserRole._meta.ordering == ["assigned_at", "id"]


@pytest.mark.parametrize("buscado", ["Número 42", "8042", "persona42@"])
def test_el_buscador_de_usuarios_busca_por_nombre_documento_o_correo(ochenta_usuarios, buscado):
    datos = cliente(ochenta_usuarios).get(reverse("accounts:user-list"), {"search": buscado}).json()
    assert [u["email"] for u in datos["results"]] == ["persona42@kolping.test"]
