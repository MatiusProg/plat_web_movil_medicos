"""US-12 — Operaciones de negocio; las asociaciones se guardan atómicamente."""
from django.db import transaction
from rest_framework.exceptions import ValidationError
from audit.services import record
from scheduling.models import Schedule
from .models import Specialty, Practitioner, PractitionerSpecialty, PractitionerBranch

def _same_org(instance, organization):
    if instance.organization_id != organization.id:
        raise ValidationError({"detail": "El registro no pertenece a esta organización."})

def _audit(request, action, entity, obj, detail=None):
    record(request, action, entity, entity_id=obj.pk, detail=detail or {},
           organization=obj.organization)

def _set_links(model, field, practitioner, values, organization):
    ids = {obj.pk for obj in values}
    model.objects.filter(organization=organization, practitioner=practitioner).exclude(
        **{field + "_id__in": ids}
    ).delete()
    existing = set(model.objects.filter(
        organization=organization, practitioner=practitioner,
    ).values_list(field + "_id", flat=True))
    model.objects.bulk_create([
        model(organization=organization, practitioner=practitioner, **{field: obj})
        for obj in values if obj.pk not in existing
    ])

def _check_schedules(practitioner, branch_values):
    """No quitar una sede que aún tiene reglas de agenda activas."""
    allowed = {obj.pk for obj in branch_values}
    if Schedule.objects.filter(
        organization=practitioner.organization, practitioner=practitioner,
        is_active=True,
    ).exclude(branch_id__in=allowed).exists():
        raise ValidationError({"branches": [
            "No podés quitar una sucursal con agendas activas. Desactivá o reasigná primero esas agendas."
        ]})

@transaction.atomic
def save_specialty(*, organization, data, request=None, instance=None):
    if instance is None:
        obj = Specialty.objects.create(organization=organization, **data)
        action = "catalog.specialty.create"
    else:
        _same_org(instance, organization)
        obj = instance
        for key, value in data.items():
            setattr(obj, key, value)
        obj.save(update_fields=[*data.keys(), "updated_at"])
        action = "catalog.specialty.update"
    _audit(request, action, "specialties", obj, {"name": obj.name})
    return obj

@transaction.atomic
def deactivate_specialty(*, instance, request=None):
    if not instance.is_active:
        return instance
    if PractitionerSpecialty.objects.filter(
        organization=instance.organization, specialty=instance,
        practitioner__is_active=True,
    ).exists():
        raise ValidationError({"detail": "La especialidad tiene profesionales activos asociados. Desasocialos primero."})
    instance.is_active = False
    instance.save(update_fields=["is_active", "updated_at"])
    _audit(request, "catalog.specialty.deactivate", "specialties", instance)
    return instance

@transaction.atomic
def save_practitioner(*, organization, data, request=None, instance=None):
    data = dict(data)
    specialties = data.pop("specialties", None)
    branches = data.pop("branches", None)
    if instance is None:
        obj = Practitioner.objects.create(organization=organization, **data)
        action = "catalog.professional.create"
    else:
        _same_org(instance, organization)
        obj = instance
        if branches is not None:
            _check_schedules(obj, branches)
        for key, value in data.items():
            setattr(obj, key, value)
        # save() recalcula search_name: no usar bulk_update.
        obj.save()
        action = "catalog.professional.update"
    if specialties is not None:
        _set_links(PractitionerSpecialty, "specialty", obj, specialties, organization)
    if branches is not None:
        _set_links(PractitionerBranch, "branch", obj, branches, organization)
    _audit(request, action, "practitioners", obj, {"name": obj.full_name})
    return obj

@transaction.atomic
def deactivate_practitioner(*, instance, request=None):
    if not instance.is_active:
        return instance
    if Schedule.objects.filter(
        organization=instance.organization, practitioner=instance, is_active=True,
    ).exists():
        raise ValidationError({"detail": "El profesional tiene agendas activas. Desactivalas primero."})
    instance.is_active = False
    instance.save(update_fields=["is_active", "updated_at"])
    _audit(request, "catalog.professional.deactivate", "practitioners", instance)
    return instance
