from datetime import date

import pytest
from rest_framework.test import APIClient

from accounts.models import AuditLog
from accounts.tokens import tokens_for_user
from tenancy.context import platform_admin_context
from tenancy.models import Subscription


pytestmark = pytest.mark.django_db


def authenticated_client(user):
    tokens = tokens_for_user(user)

    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens['access']}"
    )

    return client


@pytest.fixture
def platform_client(platform_admin):
    return authenticated_client(platform_admin)


def test_superadmin_puede_listar_planes(
    platform_client,
    plans,
):
    response = platform_client.get(
        "/api/platform/plans/"
    )

    assert response.status_code == 200

    codes = {
        item["code"]
        for item in response.data["results"]
    }

    assert codes == {
        "basic",
        "pro",
        "premium",
    }


def test_usuario_normal_no_puede_listar_planes(
    user_a,
):
    client = authenticated_client(user_a)

    response = client.get(
        "/api/platform/plans/"
    )

    assert response.status_code == 403


def test_superadmin_puede_editar_plan(
    platform_client,
    plans,
):
    plan = plans["pro"]

    response = platform_client.patch(
        f"/api/platform/plans/{plan.id}/",
        {
            "description": "Plan Pro actualizado",
        },
        format="json",
    )

    assert response.status_code == 200

    with platform_admin_context():
        plan.refresh_from_db()

        assert (
            plan.description
            == "Plan Pro actualizado"
        )


def test_no_se_puede_asignar_plan_inactivo(
    platform_client,
    org_a,
    plans,
):
    plan = plans["basic"]

    with platform_admin_context():
        plan.is_active = False
        plan.save(
            update_fields=[
                "is_active",
            ]
        )

    response = platform_client.post(
        "/api/platform/subscriptions/assign/",
        {
            "organization_id": str(org_a.id),
            "plan_id": str(plan.id),
            "starts_at": "2026-09-01",
            "change_reason": "Prueba plan inactivo",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "plan_id" in response.data


def test_superadmin_puede_cambiar_plan(
    platform_client,
    platform_admin,
    org_b,
    plans,
):
    response = platform_client.post(
        "/api/platform/subscriptions/assign/",
        {
            "organization_id": str(org_b.id),
            "plan_id": str(plans["pro"].id),
            "starts_at": "2026-09-01",
            "change_reason": "Cambio de Básico a Pro",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["plan_code"] == "pro"

    assert (
        str(response.data["organization"])
        == str(org_b.id)
    )

    with platform_admin_context():
        current = Subscription.objects.get(
            organization=org_b,
            ends_at__isnull=True,
        )

        assert current.plan.code == "pro"

        assert (
            current.assigned_by_id
            == platform_admin.id
        )


def test_cambio_de_plan_cierra_suscripcion_anterior(
    platform_client,
    org_b,
    plans,
):
    with platform_admin_context():
        previous = Subscription.objects.get(
            organization=org_b,
            ends_at__isnull=True,
        )

        previous_id = previous.id

    response = platform_client.post(
        "/api/platform/subscriptions/assign/",
        {
            "organization_id": str(org_b.id),
            "plan_id": str(plans["pro"].id),
            "starts_at": "2026-09-01",
            "change_reason": "Cambio de plan",
        },
        format="json",
    )

    assert response.status_code == 201

    with platform_admin_context():
        previous = Subscription.objects.get(
            id=previous_id
        )

        assert (
            previous.status
            == Subscription.Status.CANCELLED
        )

        assert previous.ends_at == date(
            2026,
            9,
            1,
        )


def test_solo_queda_una_suscripcion_vigente(
    platform_client,
    org_b,
    plans,
):
    response = platform_client.post(
        "/api/platform/subscriptions/assign/",
        {
            "organization_id": str(org_b.id),
            "plan_id": str(plans["pro"].id),
            "starts_at": "2026-09-01",
        },
        format="json",
    )

    assert response.status_code == 201

    with platform_admin_context():
        assert (
            Subscription.objects.filter(
                organization=org_b,
                ends_at__isnull=True,
            ).count()
            == 1
        )


def test_asignacion_de_plan_genera_auditoria(
    platform_client,
    platform_admin,
    org_b,
    plans,
):
    response = platform_client.post(
        "/api/platform/subscriptions/assign/",
        {
            "organization_id": str(org_b.id),
            "plan_id": str(plans["pro"].id),
            "starts_at": "2026-09-01",
            "change_reason": "Mejora de plan",
        },
        format="json",
    )

    assert response.status_code == 201

    with platform_admin_context():
        audit = AuditLog.objects.get(
            action="plan.assign"
        )

        assert audit.organization is None

        assert (
            audit.user_id
            == platform_admin.id
        )

        assert (
            audit.detail["new_plan"]
            == "pro"
        )

        assert (
            audit.detail["previous_plan"]
            == "basic"
        )


def test_se_puede_consultar_historial_de_organizacion(
    platform_client,
    org_b,
    plans,
):
    response = platform_client.post(
        "/api/platform/subscriptions/assign/",
        {
            "organization_id": str(org_b.id),
            "plan_id": str(plans["pro"].id),
            "starts_at": "2026-09-01",
        },
        format="json",
    )

    assert response.status_code == 201

    response = platform_client.get(
        (
            "/api/platform/organizations/"
            f"{org_b.id}/subscriptions/"
        )
    )

    assert response.status_code == 200
    assert response.data["count"] == 2

    plan_codes = {
        item["plan_code"]
        for item in response.data["results"]
    }

    assert plan_codes == {
        "basic",
        "pro",
    }


def test_no_se_puede_asignar_el_mismo_plan_vigente(
    platform_client,
    org_b,
    plans,
):
    response = platform_client.post(
        "/api/platform/subscriptions/assign/",
        {
            "organization_id": str(org_b.id),
            "plan_id": str(plans["basic"].id),
            "starts_at": "2026-09-01",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "plan_id" in response.data