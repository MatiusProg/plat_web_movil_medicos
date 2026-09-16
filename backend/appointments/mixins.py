"""Ayudas compartidas por las vistas de `appointments`."""

UUID_REGEX = (
    "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)


class OrganizationScopedMixin:
    """Acota el queryset a la organización de quien hace la petición.

    RLS ya lo hace en la base; filtrar acá también deja el alcance explícito.
    """

    def organization(self):
        return self.request.user.organization

    def scoped(self, queryset):
        organization = self.organization()
        if organization is None:
            return queryset.none()
        return queryset.filter(organization=organization)


def owns_appointment(user, appointment) -> bool:
    """El usuario es el titular de la ficha, o el titular de a quién es.

    Cubre el caso de US-07: el titular reserva y gestiona las fichas de sus
    dependientes, que no tienen cuenta propia.
    """
    paciente = getattr(user, "patient_profile", None)
    if paciente is None:
        return False
    return appointment.patient_id == paciente.id or (
        appointment.patient.guardian_id == paciente.id
    )
