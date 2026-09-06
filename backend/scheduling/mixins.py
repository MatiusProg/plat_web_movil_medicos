"""Ayudas compartidas por las vistas de `scheduling`."""

UUID_REGEX = (
    "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)


class OrganizationScopedMixin:
    """Acota el queryset a la organización de quien pide.

    RLS ya lo hace en la base; filtrar acá también deja el alcance explícito.
    """

    def organization(self):
        return self.request.user.organization

    def scoped(self, queryset):
        organization = self.organization()
        if organization is None:
            return queryset.none()
        return queryset.filter(organization=organization)
