#!/usr/bin/env python
"""Genera docs/modelo-datos/esquema-generado.sql a partir de las migraciones.

El archivo resultante es el SQL **real** que Django ejecuta contra PostgreSQL,
obtenido con ``manage.py sqlmigrate``. Sirve para la documentación del proyecto
y para revisar el modelo desde el SQL Editor de Supabase.

No hace falta conexión a la base: ``sqlmigrate`` genera el SQL a partir de las
migraciones, no lo lee del servidor.

Uso, desde la raíz del repositorio:

    backend/.venv/Scripts/python scripts/generar_esquema.py     # Windows
    backend/.venv/bin/python scripts/generar_esquema.py         # macOS / Linux

Hay que regenerarlo cada vez que se agregue una migración, para que la
documentación no se separe de lo que realmente hay en la base.
"""

import io
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "backend"
SALIDA = RAIZ / "docs" / "modelo-datos" / "esquema-generado.sql"

# En orden de aplicación. Agregar acá las migraciones de cada sprint.
MIGRACIONES = [
    ("accounts", "0001_initial"),
    ("tenancy", "0001_initial"),
    ("catalog", "0001_initial"),
    ("accounts", "0002_initial"),
    ("patients", "0001_initial"),
    ("tenancy", "0002_rls_policies"),
    ("tenancy", "0003_seed_catalog"),
]

CABECERA = """\
-- =========================================================================
--  ESQUEMA REAL DEL SPRINT 0, GENERADO POR DJANGO
--
--  Este archivo NO se escribio a mano y NO se ejecuta. Es la salida de
--
--      python manage.py sqlmigrate <app> <migracion>
--
--  es decir, exactamente el SQL que Django envio a PostgreSQL al correr
--  "manage.py migrate". Sirve para dos cosas:
--
--    1. la documentacion del proyecto (el DDL real, no una aproximacion),
--    2. leer o revisar el modelo desde el SQL Editor de Supabase.
--
--  El esquema se aplica SIEMPRE con "manage.py migrate", nunca pegando
--  este archivo en una consola. Si se ejecutara, Django despues querria
--  crear tablas que ya existen.
--
--  Para regenerarlo, ver el pie del archivo.
-- =========================================================================
"""

PIE = """

-- =========================================================================
--  Como regenerar este archivo
--
--    backend/.venv/Scripts/python scripts/generar_esquema.py    (Windows)
--    backend/.venv/bin/python scripts/generar_esquema.py        (macOS/Linux)
--
--  Hay que regenerarlo cada vez que se agregue una migracion, para que la
--  documentacion no se separe de lo que realmente hay en la base.
-- =========================================================================
"""


def main() -> int:
    interprete = sys.executable
    partes = [CABECERA]

    for app, migracion in MIGRACIONES:
        resultado = subprocess.run(
            [interprete, "manage.py", "sqlmigrate", app, migracion],
            cwd=BACKEND, capture_output=True, text=True, encoding="utf-8",
        )
        if resultado.returncode != 0:
            print(f"FALLO {app}/{migracion}:", file=sys.stderr)
            print(resultado.stderr, file=sys.stderr)
            return 1

        sql = (resultado.stdout or "").strip()
        partes.append(
            "\n\n-- ====================================================================="
            f"====\n--  {app} / {migracion}\n"
            "-- ========================================================================="
            "\n\n"
        )
        if sql:
            partes.append(sql)
            print(f"  {app}/{migracion:<20} {len(sql.splitlines())} lineas")
        else:
            partes.append(
                "-- Migracion de datos escrita en Python (RunPython): no produce SQL\n"
                "-- estatico. Siembra 3 planes de suscripcion, 5 plantillas de rol y\n"
                "-- 25 permisos. El detalle esta en\n"
                "-- backend/tenancy/migrations/0003_seed_catalog.py"
            )
            print(f"  {app}/{migracion:<20} (migracion de datos)")

    partes.append(PIE)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    io.open(SALIDA, "w", encoding="utf-8", newline="\n").write("".join(partes))
    print(f"\nEscrito: {SALIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
