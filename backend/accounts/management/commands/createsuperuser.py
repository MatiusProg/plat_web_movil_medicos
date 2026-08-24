"""``manage.py createsuperuser`` con el contexto de plataforma puesto.

**El problema que resuelve.** El comando de Django inserta en ``users`` sin
fijar ningún contexto de inquilino, y ``users`` tiene RLS con ``FORCE``. La
política deja pasar la fila sólo si ``organization_id`` coincide con el
inquilino actual, o si es NULL y quien escribe es el superadministrador. Sin
contexto no se cumple ninguna de las dos, así que el comando original falla
con:

    new row violates row-level security policy for table "users"

Y no es un caso raro: **es el primer comando que corre cualquiera al montar su
entorno**. Sin superadministrador no se puede iniciar sesión en la plataforma,
y sin eso no se puede registrar la primera organización (US-43), que es lo que
habilita todo lo demás.

Se resuelve envolviendo el comando de Django en ``platform_admin_context()``,
que fija ``app.is_platform_admin`` mientras dura y lo restaura al salir. Se
sobrescribe el comando estándar en vez de agregar uno nuevo a propósito: así
la instrucción que todo el mundo ya conoce —y la que está en los tutoriales de
Django— funciona sin que nadie tenga que aprenderse un nombre distinto.

El gestor abre una transacción, de modo que las preguntas interactivas
transcurren dentro de ella. Para un comando que se corre una vez por máquina
es aceptable; si se cancela con Ctrl+C, no queda nada a medias.
"""

from django.contrib.auth.management.commands import createsuperuser

from tenancy.context import platform_admin_context


class Command(createsuperuser.Command):
    help = (
        "Crea un Superadministrador de Plataforma. Igual que el comando de "
        "Django, pero con el contexto de plataforma puesto, sin el cual RLS "
        "rechaza la fila."
    )

    def handle(self, *args, **options):
        with platform_admin_context():
            return super().handle(*args, **options)
