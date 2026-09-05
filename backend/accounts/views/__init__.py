"""Vistas de `accounts`, uno por historia.

Está partido en paquete a propósito, y es la propia convención la que nombra
los archivos (`docs/convenciones-de-codigo.md` §1): en `accounts` trabajan
tres personas el mismo sprint, y con un solo `views.py` cada pull request
traería conflicto en el mismo archivo.

    auth.py            US-02, Karen
    registration.py    US-01, Alexander
    roles.py           US-04, Karen

No se reexporta nada acá —nada de `from .auth import *`—: cada quien importa
del módulo concreto, y así dos historias no vuelven a tocar la misma línea.
"""
