"""US-48 — Calificar la atención con estrellas, y los promedios.

Tres lectores, con tres alcances distintos:

- **El paciente** (o el titular de su dependiente) califica y ve **su**
  calificación. Es el mismo alcance que el historial: `history_scope == OWN`.
- **El médico** ve su promedio y la distribución, **nunca quién lo calificó**:
  ni nombre, ni atención, ni comentario. Un comentario puede delatar al
  paciente («la del martes a las 10»), así que tampoco se le muestra.
- **El administrador** ve los promedios por médico, especialidad y sede, y los
  últimos comentarios **sin el nombre del paciente**.

Las reglas que no dependen de la vista (firmada, 1 a 5, 7 días, no se borra)
las hace cumplir la base: ver la migración 0008.
"""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models import Avg, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from catalog.models import PractitionerSpecialty

from .models import Encounter, EncounterRating

ULTIMOS_COMENTARIOS = 10
SIN_ESPECIALIDAD = "Sin especialidad"


class RatingConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "rating_conflict"

    def __init__(self, code, detail):
        super().__init__(detail={"code": code, "detail": detail})


def editable(rating, ahora=None) -> bool:
    return (ahora or timezone.now()) <= rating.editable_until


def as_dict(rating, ahora=None):
    """Lo que ve el paciente de su propia calificación."""
    if rating is None:
        return None
    return {
        "stars": rating.stars,
        "comment": rating.comment,
        "created_at": rating.created_at,
        "updated_at": rating.updated_at,
        "editable_until": rating.editable_until,
        "editable": editable(rating, ahora),
    }


def rate(user, encounter: Encounter, stars: int, comment: str) -> EncounterRating:
    """Primera calificación de una atención firmada."""
    if not encounter.is_signed:
        raise RatingConflict("not_signed", "La atención todavía no está firmada.")
    try:
        with transaction.atomic():
            return EncounterRating.objects.create(
                organization=encounter.organization,
                encounter=encounter,
                patient_id=encounter.patient_id,
                practitioner_id=encounter.practitioner_id,
                branch_id=encounter.branch_id,
                rated_by=user,
                stars=stars,
                comment=comment,
            )
    except IntegrityError:
        # Dos pestañas a la vez: la segunda choca con el `OneToOne`.
        raise RatingConflict("already_rated",
                             "Esta atención ya está calificada. Puedes cambiarla.")


def correct(encounter: Encounter, stars: int, comment: str) -> EncounterRating:
    """Cambiar la calificación mientras queden días."""
    with transaction.atomic():
        rating = (EncounterRating.objects.select_for_update()
                  .filter(encounter=encounter).first())
        if rating is None:
            raise RatingConflict("not_rated", "Esta atención todavía no está calificada.")
        if not editable(rating):
            raise RatingConflict(
                "rating_locked",
                f"Pasaron los {EncounterRating.EDITABLE_DAYS} días: "
                "la calificación ya no se puede cambiar.",
            )
        rating.stars = stars
        rating.comment = comment
        rating.save(update_fields=["stars", "comment", "updated_at"])
        return rating


# --------------------------------------------------------------------------
#  Promedios
# --------------------------------------------------------------------------

def _promedio(valor):
    return round(float(valor), 2) if valor is not None else None


def _distribucion(qs):
    conteo = dict(qs.values_list("stars").annotate(n=Count("id")).order_by())
    return [{"stars": s, "total": conteo.get(s, 0)} for s in range(1, 6)]


def _resumen(qs):
    agregado = qs.aggregate(promedio=Avg("stars"), total=Count("id"))
    return {
        "average": _promedio(agregado["promedio"]),
        "count": agregado["total"],
        "distribution": _distribucion(qs),
    }


def _agrupado(qs, campo_id, campo_nombre):
    filas = (qs.values(campo_id, campo_nombre)
             .annotate(promedio=Avg("stars"), total=Count("id"))
             .order_by())
    salida = [{
        "id": str(f[campo_id]),
        "name": f[campo_nombre],
        "average": _promedio(f["promedio"]),
        "count": f["total"],
    } for f in filas]
    salida.sort(key=lambda f: (-f["average"], -f["count"], f["name"]))
    return salida


def for_practitioner(practitioner) -> dict:
    """Lo que ve el médico: su promedio y la distribución, sin nadie detrás."""
    return _resumen(EncounterRating.objects.filter(
        organization_id=practitioner.organization_id, practitioner=practitioner,
    ))


def for_organization(organizacion, inicio, fin, branch_id=None) -> dict:
    """El tablero del administrador, por la fecha de la atención."""
    qs = EncounterRating.objects.filter(
        organization=organizacion,
        encounter__appointment__starts_at__gte=inicio,
        encounter__appointment__starts_at__lt=fin,
    )
    if branch_id:
        qs = qs.filter(branch_id=branch_id)

    por_medico = (qs.values("practitioner_id", "practitioner__first_name",
                            "practitioner__last_name")
                  .annotate(promedio=Avg("stars"), total=Count("id")).order_by())
    medicos = [{
        "id": str(f["practitioner_id"]),
        "name": f"{f['practitioner__first_name']} {f['practitioner__last_name']}".strip(),
        "average": _promedio(f["promedio"]),
        "count": f["total"],
    } for f in por_medico]
    medicos.sort(key=lambda f: (-f["average"], -f["count"], f["name"]))

    # Un médico con dos especialidades cuenta en las dos, como en la demanda.
    nombres = dict(
        PractitionerSpecialty.objects.filter(organization=organizacion)
        .values_list("specialty_id", "specialty__name")
    )
    especialidades = []
    for f in (qs.values("practitioner__specialty_links__specialty_id")
              .annotate(promedio=Avg("stars"), total=Count("id")).order_by()):
        especialidad_id = f["practitioner__specialty_links__specialty_id"]
        especialidades.append({
            "id": str(especialidad_id) if especialidad_id else None,
            "name": nombres.get(especialidad_id, SIN_ESPECIALIDAD),
            "average": _promedio(f["promedio"]),
            "count": f["total"],
        })
    especialidades.sort(key=lambda f: (-f["average"], -f["count"], f["name"]))

    comentarios = [{
        "stars": r.stars,
        "comment": r.comment,
        "practitioner_name": r.practitioner.full_name,
        "branch_name": r.branch.name,
        "created_at": r.created_at,
    } for r in (qs.exclude(comment="")
                .select_related("practitioner", "branch")
                .order_by("-created_at")[:ULTIMOS_COMENTARIOS])]

    return {
        **_resumen(qs),
        "by_practitioner": medicos,
        "by_specialty": especialidades,
        "by_branch": _agrupado(qs, "branch_id", "branch__name"),
        "latest_comments": comentarios,
    }
