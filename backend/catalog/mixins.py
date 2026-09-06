"""Ayudas compartidas por las vistas del catálogo."""


class OrganizationScopedMixin:
    """Acota el queryset a la organización de quien hace la petición.

    RLS ya lo hace en la base, pero filtrar acá también deja el alcance
    explícito y sobrevive a que la vista se llame desde un comando de gestión
    sin `request`.
    """

    def organization(self):
        return self.request.user.organization

    def scoped(self, queryset):
        organization = self.organization()
        if organization is None:
            return queryset.none()
        return queryset.filter(organization=organization)
