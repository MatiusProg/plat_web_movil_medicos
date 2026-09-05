"""Lógica de negocio de `accounts`, uno por historia.

Está partido en paquete por la misma razón que `views` y `serializers`, y es
la propia convención la que lo pide (`docs/convenciones-de-codigo.md` §1,
regla del archivo compartido): en `accounts` trabajan tres personas el mismo
sprint, y un solo `services.py` traería conflicto en cada pull request.

    auth.py            US-02, Karen
    roles.py           US-04, Karen

No se reexporta nada acá —nada de `from .auth import *`—: cada quien importa
del módulo concreto, y así dos historias no vuelven a tocar la misma línea.
"""
