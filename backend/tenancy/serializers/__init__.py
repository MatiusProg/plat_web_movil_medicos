"""Serializers de `tenancy`, uno por historia.

Está partido en paquete a propósito: US-43, US-44 y US-45 viven en la misma
app, y con un solo `serializers.py` cada pull request traía conflicto en el
mismo archivo. Es la regla del archivo compartido de
`docs/convenciones-de-codigo.md` §1.

No se reexporta nada acá —nada de `from .plans import *`—: cada quien importa
del módulo concreto, y así dos historias no vuelven a tocar la misma línea.
"""
