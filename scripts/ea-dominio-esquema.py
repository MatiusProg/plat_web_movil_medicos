"""Vuelca el esquema de las tablas propias del sistema, en JSON, para
ea-dominio-sprint2.ps1 (2.1.2 Modelo de dominio).

Sale de los modelos de Django, no de una base: así el diagrama dice lo mismo
que `main` aunque la base local esté atrasada en migraciones. Que modelos y
migraciones coinciden se comprueba con `manage.py makemigrations --check`.

Uso (desde backend/, con su entorno virtual):
    python ../scripts/ea-dominio-esquema.py salida.json
"""

import json
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402
from django.db import connection, models  # noqa: E402

# Las apps del sistema, en el orden de columnas del diagrama. Quedan fuera las
# de Django y de terceros (auth, contenttypes, token_blacklist).
APPS = [
    "tenancy", "accounts", "audit", "reporting", "backups", "catalog",
    "scheduling", "assistant", "patients", "appointments", "payments",
    "encounters",
]


def tipo(campo):
    """El tipo de PostgreSQL, en mayúsculas y abreviado como en Violet."""
    if isinstance(campo, models.BigAutoField):
        return "BIGSERIAL"
    if isinstance(campo, models.AutoField):
        return "SERIAL"
    t = campo.db_type(connection)
    t = t.replace("timestamp with time zone", "timestamptz").replace(", ", ",")
    return t.upper()


tablas = []
for app in APPS:
    for modelo in apps.get_app_config(app).get_models():
        meta = modelo._meta
        columnas = []
        for campo in meta.concrete_fields:
            fk = campo.is_relation and (campo.many_to_one or campo.one_to_one)
            columnas.append({
                "col": campo.column,
                "tipo": tipo(campo),
                "pk": campo.primary_key,
                "nulo": campo.null,
                "unico": bool(campo.unique and not campo.primary_key),
                "fk": campo.related_model._meta.db_table if fk else None,
            })
        # La clave primaria primero; el resto en el orden del modelo.
        columnas.sort(key=lambda c: not c["pk"])
        tablas.append({"app": app, "tabla": meta.db_table, "columnas": columnas})

with open(sys.argv[1], "w", encoding="utf-8") as salida:
    json.dump(tablas, salida, ensure_ascii=False, indent=1)
print(f"{len(tablas)} tablas")
