# Convenciones de código — backend

Una página. Se acordaron al cerrar la base del Sprint 0, antes de que los seis
abrieran sus ramas.

**El objetivo es concreto:** que tres personas puedan trabajar en la misma app
sin pisarse, y que cualquiera pueda abrir un archivo de otro y entender dónde
está parado.

---

## 1. Dónde va cada cosa

Cada app corresponde a un módulo del documento del proyecto:

| App | Qué contiene | Historias |
|---|---|---|
| `tenancy` | organizaciones, planes, suscripciones, métricas, alertas, contexto de inquilino | US-43, US-44, US-45 |
| `accounts` | usuarios, roles, permisos, autenticación, bitácora | US-01 a US-06 |
| `catalog` | sucursales, especialidades, profesionales, agendas | US-11 a US-16 |
| `patients` | pacientes y pacientes a cargo | US-07 a US-10 |

Los sprints siguientes agregan `appointments` (US-17 a US-23), `records`
(historia clínica, US-24 a US-27) y `ai` (US-31 a US-42).

### Archivos dentro de una app

```
accounts/
    models.py           los modelos, nada más
    serializers.py      un serializer por recurso
    views.py            las vistas
    permissions.py      clases de permiso de DRF
    services.py         lógica de negocio que no entra en una vista
    urls.py             las rutas de ESTA app
    migrations/
```

**Regla del archivo compartido:** si dos personas van a tocar el mismo archivo
en el mismo sprint, se parte en un paquete antes de empezar, no después del
primer conflicto.

```
accounts/views/
    __init__.py         from .auth import *  ->  no; importar explícito
    auth.py             US-02, Karen
    registration.py     US-01, Alexander
    roles.py            US-04, Michael
```

En el Sprint 0 esto aplica a `accounts`, donde trabajan tres personas.

---

## 2. Las rutas — la regla que evita más conflictos

**`config/urls.py` está cerrado. No se le agregan rutas.**

Cada app tiene su `urls.py` y ya está incluida. Los prefijos están fijados:

| App | Prefijo |
|---|---|
| `tenancy` | `/api/platform/` |
| `accounts` | `/api/accounts/` |
| `catalog` | `/api/catalog/` |
| `patients` | `/api/patients/` |

Tu historia agrega su router en el `urls.py` de su app:

```python
# accounts/urls.py
router.register("users", UserViewSet, basename="user")
```

Si los seis editaran `config/urls.py`, cada pull request traería un conflicto en
la misma línea. Así, cada uno toca un archivo distinto.

---

## 3. Idioma

Esto se decidió tarde y hubo que renombrar código. Ahora está cerrado:

| Qué | Idioma | Ejemplo |
|---|---|---|
| Clases, funciones, variables, constantes | **inglés** | `TenantJWTAuthentication`, `tokens_for_user` |
| Tablas y columnas | **inglés** | `subscription_plans`, `organization_id` |
| Comentarios y docstrings | **español** | `# Sin esto las consultas devuelven cero filas` |
| Nombres de las pruebas | **español** | `def test_un_menor_sin_documento_se_registra_con_titular()` |
| Documentación | **español** | este archivo |

**Por qué el código en inglés:** es la convención de Django y de DRF, y el
documento del proyecto (apartado 1.1.B) dice que el modelo sigue la
nomenclatura HL7 FHIR, cuyos recursos —`Patient`, `Practitioner`,
`Appointment`, `Encounter`— son en inglés. Mezclar los dos idiomas es lo único
que no se puede.

**Por qué las pruebas en español:** el nombre de una prueba es una frase que
describe un comportamiento, y la lee una persona.

---

## 4. Nombres

| Cosa | Forma | Ejemplo |
|---|---|---|
| Modelo | singular, `PascalCase` | `SubscriptionPlan` |
| Tabla (`db_table`) | plural, `snake_case` | `subscription_plans` |
| Serializer | `<Modelo>Serializer` | `OrganizationSerializer` |
| ViewSet | `<Modelo>ViewSet` | `OrganizationViewSet` |
| Clase de permiso | `Can<Acción><Recurso>` | `CanAssignRoles` |
| Ruta (`basename`) | singular, `snake_case` | `subscription_plan` |
| Código de permiso | `modulo.recurso.accion` | `users.role.assign` |
| Rama de git | `feat/KOL-12-descripcion` | ver `CONTRIBUTING.md` |

**Siempre `db_table` explícito** en el `Meta` del modelo. Sin él, Django arma el
nombre concatenando la app (`accounts_user`), que no es el que documentamos.

---

## 5. Reglas propias de este proyecto

No son estilo: **romperlas apaga el aislamiento entre organizaciones sin dar
ningún error**.

### Toda tabla nueva con `organization_id`

1. `ENABLE` **y** `FORCE ROW LEVEL SECURITY`, en una migración `RunSQL`.
2. Política `tenant_isolation` con `USING` y `WITH CHECK`.
3. Clave foránea **compuesta** `(x_id, organization_id)` si referencia a otra
   tabla del inquilino.
4. Su caso en `tests/test_isolation.py`.

Hay una prueba que falla sola si alguien crea una tabla con `organization_id` y
se olvida del RLS.

### Autorización

Va por `user.has_permission("users.role.assign")`, que consulta
`UserRole → RolePermission`.

**Nunca `user.has_perm()` ni `@permission_required`.** Ésas son de
`django.contrib.auth`, cuyas tablas **no** están aisladas por inquilino.

### Tokens

Siempre con `accounts.tokens.tokens_for_user(user)`.

**Nunca `AccessToken.for_user()` ni `RefreshToken.for_user()`.** Un token sin
los claims `organization_id` e `is_platform_admin` no puede autenticar: la
búsqueda del usuario devuelve cero filas por RLS.

### Consultas fuera del ciclo HTTP

Scripts, tareas programadas y pruebas envuelven la consulta:

```python
from tenancy.context import tenant_context

with tenant_context(organization.id):
    Patient.objects.all()
```

Sin contexto, toda consulta devuelve **cero filas**. Es deliberado: si el
middleware falla, el sistema no devuelve nada en lugar de devolverlo todo. **Si
ves cero filas al depurar, es esto** — no se borraron los datos.

---

## 6. Pruebas

| Archivo | Qué cubre |
|---|---|
| `tests/test_isolation.py` | las políticas de la base, con el ORM |
| `tests/test_peticiones.py` | el ciclo HTTP completo, con el cliente de DRF |
| `tests/test_<historia>.py` | lo tuyo |

**Toda historia suma al menos una prueba que entra por HTTP.** Las 21 pruebas de
base pasaban con un backend que no arrancaba, porque ninguna llegaba al
middleware. Está contado en [registro-de-defectos.md](registro-de-defectos.md).

Las pruebas se conectan como `app_user`, nunca como `postgres`. Ya está
configurado; sólo hay que no cambiarlo.

---

## 7. Antes de abrir el pull request

```bash
cd backend
python manage.py check          # sin errores
pytest                          # todas en verde
python manage.py makemigrations --check --dry-run
```

El último comando **no debe generar nada**. Si genera una migración, es que
cambiaste un modelo y te olvidaste de crearla — y quien haga `pull` va a tener
una base distinta de la tuya.

Si agregaste una migración, regenerá también el esquema documentado:

```bash
python ../scripts/generar_esquema.py
```

---

## 8. Cómo se cambia una convención

En una retrospectiva, no por mensaje suelto — igual que las reglas de
`CONTRIBUTING.md`. Y si se cambia, se aplica al código existente en el mismo
pull request: una convención que la mitad del código no cumple no es una
convención.
