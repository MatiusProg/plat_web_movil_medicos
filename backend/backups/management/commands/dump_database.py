"""Copia de seguridad de **toda la instalación**. Característica general 6.

    python manage.py dump_database
    python manage.py dump_database --output C:\\respaldos
    python manage.py dump_database --format plain     # SQL legible

**Por qué es un comando de consola y no un endpoint.** La consigna pide
respaldar «todo el sistema», y eso incluye las tablas que no pertenecen a
ninguna organización —el catálogo de permisos, los planes de suscripción, las
propias organizaciones— y el esquema con sus políticas RLS. Un endpoint que
devolviera eso tendría que ejecutarlo alguien autenticado *dentro* del sistema,
y el caso de uso de un respaldo completo es justamente el de un sistema al que
no se puede entrar. Esto lo corre quien administra la instalación, con las
credenciales de la base, sin pasar por la aplicación.

La copia **por organización** —la que sí es de la aplicación, la que un cliente
del SaaS puede pedir— está en ``backup_organization`` y en
``POST /api/backups/create/``.

**Requiere ``pg_dump`` en el PATH**, de una versión igual o mayor que la del
servidor. Es la trampa clásica: con un cliente de PostgreSQL 15 contra un
servidor 16, ``pg_dump`` se niega con «server version mismatch» y no hay
respaldo. Por eso el comando lo comprueba antes y lo dice con todas las letras
en vez de dejar un archivo de cero bytes.

En Supabase y en Railway, ``DATABASE_URL`` apunta al servidor gestionado y esto
funciona igual desde cualquier máquina que lo alcance.
"""

import datetime as dt
import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# `custom` es el formato comprimido de PostgreSQL, el que admite restauración
# selectiva con `pg_restore -t`. `plain` es SQL de texto, que se puede leer y
# versionar pero pesa varias veces más.
FORMATS = {"custom": ("-Fc", "dump"), "plain": ("-Fp", "sql")}


class Command(BaseCommand):
    help = "Genera una copia de seguridad de toda la base con pg_dump."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output", default=".",
            help="Carpeta donde dejar el archivo. Por omisión, la actual.",
        )
        parser.add_argument(
            "--format", choices=sorted(FORMATS), default="custom",
            help="custom (comprimido, restauración selectiva) o plain (SQL).",
        )

    def handle(self, *args, **options):
        ejecutable = shutil.which("pg_dump")
        if ejecutable is None:
            raise CommandError(
                "No se encontró «pg_dump» en el PATH. Instalá las "
                "herramientas de cliente de PostgreSQL 16 —vienen con el "
                "instalador oficial— o corré este comando desde el contenedor:\n"
                "    docker compose exec db pg_dump ...",
            )

        base = settings.DATABASES["default"]
        destino = Path(options["output"]).expanduser().resolve()
        destino.mkdir(parents=True, exist_ok=True)

        bandera, extension = FORMATS[options["format"]]
        nombre = (
            f"{base.get('NAME') or 'plataforma'}"
            f"-{dt.datetime.now():%Y%m%d-%H%M%S}.{extension}"
        )
        archivo = destino / nombre

        orden = [
            ejecutable,
            "--host", str(base.get("HOST") or "localhost"),
            "--port", str(base.get("PORT") or 5432),
            "--username", str(base.get("USER") or ""),
            "--dbname", str(base.get("NAME") or ""),
            "--no-owner",          # se restaura con el usuario que restaure
            "--no-privileges",     # los GRANT los repone init-db
            bandera,
            "--file", str(archivo),
        ]

        # La contraseña va por el entorno y no por la línea de comandos: en la
        # línea la ve cualquiera que liste los procesos de la máquina.
        entorno = {"PGPASSWORD": str(base.get("PASSWORD") or "")}

        self.stdout.write(f"Respaldando {base.get('NAME')} en {archivo} …")
        resultado = subprocess.run(
            orden, env={**_os_environ(), **entorno},
            capture_output=True, text=True,
        )

        if resultado.returncode != 0:
            # Si falló, el archivo puede haber quedado vacío o a medias. Se
            # borra: un respaldo incompleto con nombre de respaldo bueno es
            # peor que ninguno, porque se descubre el día que hace falta.
            archivo.unlink(missing_ok=True)
            raise CommandError(
                f"pg_dump falló (código {resultado.returncode}):\n"
                f"{resultado.stderr.strip()}",
            )

        tamanio = archivo.stat().st_size
        self.stdout.write(self.style.SUCCESS(
            f"Listo: {archivo} ({tamanio / 1024 / 1024:.1f} MB)",
        ))
        self.stdout.write(
            "\nPara restaurarlo sobre una base vacía:\n"
            + (f"    pg_restore --clean --if-exists --no-owner "
               f"-d <base> {archivo}\n"
               if options["format"] == "custom"
               else f"    psql -d <base> -f {archivo}\n")
            + "\nOjo: la base de destino necesita el rol «app_user» y la "
              "extensión «vector» creados antes. Los deja "
              "backend/init-db/, que NO viene dentro de este volcado porque "
              "pg_dump no incluye roles del servidor.",
        )


def _os_environ():
    import os
    return dict(os.environ)
