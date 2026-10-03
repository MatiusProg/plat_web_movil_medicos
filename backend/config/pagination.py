"""La paginación de todas las listas de la API.

25 por página, como hasta ahora, pero el cliente puede pedir más con
``?page_size=`` (hasta 100). Lo necesitan los desplegables —elegir un
profesional, el actor de la bitácora, un plan—: un desplegable no se puede
paginar, así que el cliente recorre las páginas, y con páginas de 100 son una
o dos peticiones en vez de cuatro.

El tope de 100 no es decorativo: sin él, ``?page_size=1000000`` convierte
cualquier lista en una consulta sin límite contra la base.

**Una lista que el usuario recorre se muestra paginada en la interfaz**
(anterior/siguiente o "cargar más"), no se trunca a la primera página. Es lo
que se rompió el 03/10/26: la pantalla de usuarios mostraba 25 de ~80 sin
avisar.
"""

from rest_framework.pagination import PageNumberPagination


class Paginacion(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
