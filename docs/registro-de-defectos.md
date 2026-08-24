# Registro de defectos — Sprint 0

Todo lo que se rompió mientras se construía la base del Sprint 0, cómo se
detectó y cómo se corrigió.

No es burocracia: **trece de estos defectos no los encontró nadie leyendo el
código**. Aparecieron al cambiar la forma de probar. Este registro existe para
que el equipo no vuelva a caer en los mismos, y sirve como evidencia del
proceso de calidad para la documentación del proyecto.

**Estado al 2026-08-23:** los 13 corregidos y verificados. 33 pruebas en verde,
`runserver` responde 200, el esquema aplicado en local y en Supabase.

---

## Resumen

| # | Defecto | Historia afectada | Cómo se detectó |
|---|---|---|---|
| D-01 | El middleware no podía registrar alertas de aislamiento | US-45 | probar como `app_user` |
| D-02 | Un login fallido no se podía registrar | US-02, RNF-07 | probar como `app_user` |
| D-03 | El superadministrador no podía auditar sus propias acciones | US-43, US-44 | probar como `app_user` |
| D-04 | La migración semilla no podía sembrar las plantillas de rol | US-04 | probar como `app_user` |
| D-05 | Un menor sin documento no se podía registrar | US-07 | revisión del modelo |
| D-06 | El contexto de superadministrador se filtraba dentro de una transacción | todas | pruebas de Pytest |
| D-07 | Los buzones de sólo escritura no funcionaban con clave autogenerada | US-45, US-02 | pruebas de Pytest |
| D-08 | `ImportError`: el backend no arrancaba | todas | revisión de Karen |
| D-09 | `AuthenticationMiddleware` sin `SessionMiddleware` | todas | revisión de Karen |
| D-10 | El middleware leía un `request.user` siempre anónimo | todas | revisión de Karen |
| D-11 | La autenticación JWT era imposible: el token no llevaba la organización | US-02 | verificar D-10 |
| D-12 | Las alertas escritas durante un rechazo se descartaban | US-45 | escribir la prueba de D-11 |
| D-13 | Los atributos puestos sobre el `Request` de DRF no llegaban al middleware | US-45 | corregir D-12 |

---

## Ronda 1 — Probar como `app_user` en lugar de `postgres`

El modelo se había validado ejecutando el SQL como `postgres`. **`postgres` es
superusuario y omite las políticas RLS aunque las tablas tengan `FORCE`**, así
que ninguna política se ejercitó nunca. Al repetir exactamente las mismas
pruebas como `app_user` —que es como se conecta Django— aparecieron cinco
defectos, cuatro de los cuales bloqueaban una historia del sprint.

### D-01 · El middleware no podía registrar alertas de aislamiento

**Síntoma.** `INSERT` en `isolation_alerts` rechazado por la política RLS.

**Causa.** La política exigía ser superadministrador para escribir. Pero quien
detecta un acceso cruzado es el middleware, que en ese momento está en el
contexto de un inquilino cualquiera, no del superadministrador. La tabla que
registra los incidentes no podía ser escrita por el código que los detecta.

**Corrección.** Política `anyone_reports` (`FOR INSERT WITH CHECK (true)`).
Leer, modificar y resolver siguen siendo exclusivos del superadministrador. Es
el patrón de **buzón de sólo escritura**: cualquiera deposita, uno solo lee.

### D-02 · Un login fallido no se podía registrar

**Síntoma.** Igual que D-01, sobre `login_attempts`.

**Causa.** Un intento fallido se registra **antes** de saber a qué organización
pertenece el correo — de hecho, antes de saber si el correo existe. No hay
contexto que fijar.

**Corrección.** Mismo patrón de buzón. Sin esto, RNF-07 (bloqueo tras 5
intentos) no tenía dónde contar los intentos.

### D-03 · El superadministrador no podía auditar sus propias acciones

**Síntoma.** `INSERT` en `audit_log` con `organization_id NULL` rechazado.

**Causa.** La política sólo aceptaba filas de un inquilino. Pero dar de alta
una organización (US-43) o asignar un plan (US-44) son acciones de nivel
plataforma, sin inquilino al cual atribuirlas. Las dos acciones más sensibles
del sistema eran las únicas que no se podían auditar.

**Corrección.** `audit_log` admite filas con `organization_id NULL`, con el
mismo patrón que `users`: el superadministrador ve las suyas y ninguna de
ningún inquilino.

### D-04 · La migración semilla no podía sembrar las plantillas de rol

**Síntoma.** `INSERT` en `roles` con `organization_id NULL` rechazado.

**Causa.** Las plantillas viven a nivel plataforma, y Django corre las
migraciones como `app_user`, que está sujeto a RLS. Sin las plantillas, US-43
no tiene qué clonar al crear una organización.

**Corrección.** Política `system_templates_write`, y la migración de datos
empieza con `SET LOCAL app.is_platform_admin = 'on'`.

### D-05 · Un menor sin documento no se podía registrar

**Síntoma.** `patients.document_number` era `NOT NULL`.

**Causa.** Un paciente a cargo recién nacido no tiene cédula. US-07 pide
registrar familiares a cargo, y el caso más común —un hijo pequeño— era
imposible.

**Corrección.** Columna nulable, índice único **parcial** (para que varios
menores sin documento no choquen entre sí) y un `CHECK` que exige documento
**o** titular.

---

## Ronda 2 — Implementar los modelos en Django

El SQL suelto no ejercita todo. Dos problemas aparecieron sólo al correr las
pruebas con el ORM encima.

### D-06 · El contexto de superadministrador se filtraba

**Síntoma.** Una prueba con contexto de inquilino veía también al
superadministrador.

**Causa.** `SET LOCAL` vive hasta el fin de la **transacción**, no del bloque.
Salir de un `atomic()` anidado libera el savepoint pero **no** devuelve el
parámetro a su valor anterior. Los gestores de contexto ponían el valor y nunca
lo restauraban.

**Gravedad.** Alta. En producción, cualquier petición que cambiara de contexto
habría arrastrado permisos de superadministrador durante el resto de la
transacción.

**Corrección.** Cada gestor guarda los dos parámetros al entrar y los restaura
al salir, y fija **ambos**: entrar al contexto de un inquilino apaga el de
plataforma, y al revés. Además, el middleware limpia el contexto de forma
explícita al cerrar la petición.

### D-07 · Los buzones de sólo escritura no funcionaban

**Síntoma.** El `INSERT` que D-01 y D-02 habían habilitado seguía fallando,
pero sólo desde Django.

**Causa.** Django usa `INSERT ... RETURNING id` para recuperar una clave
`bigserial`. **`RETURNING` lee la fila, así que exige pasar también la política
de `SELECT`** — que en un buzón deniega. El patrón "cualquiera escribe, uno
solo lee" es incompatible con las claves autogeneradas por la base.

**Corrección.** `login_attempts` e `isolation_alerts` pasaron a clave **UUID
generada en Python**. Con la clave ya puesta, Django hace un `INSERT` a secas.

---

## Ronda 3 — Revisión de Karen sobre el backend

Karen revisó el backend y reportó tres problemas. Los tres eran reales. Al
verificarlos aparecieron tres más, y uno de ellos cambió el diseño.

> **El punto de fondo de su revisión.** Las 21 pruebas pasaban con un backend
> que no arrancaba, porque ninguna entraba por el ciclo HTTP: probaban las
> políticas de la base directamente. Ese hueco de cobertura escondía D-08.

### D-08 · El backend no arrancaba

**Síntoma.** `ImportError: cannot import name '_set_local' from 'tenancy.context'`
al correr `runserver`.

**Causa.** Al corregir D-06 se reescribió `context.py` y `_set_local` pasó a
llamarse `_set`, con otra firma. El middleware siguió importando el nombre
viejo.

**Corrección.** El middleware usa la API pública, `set_context()`.

### D-09 · `AuthenticationMiddleware` sin `SessionMiddleware`

**Síntoma.** Django lanza `ImproperlyConfigured` en cada petición.

**Corrección.** Se **quitó** `AuthenticationMiddleware` en lugar de agregar
sesiones. Esto es una API pura con JWT: no hay sesiones de navegador. Agregar
`django.contrib.sessions` habría traído tablas que nadie usa y, peor, habría
mantenido vivo el `request.user` siempre anónimo de D-10.

### D-10 · El middleware leía un `request.user` siempre anónimo

**Síntoma.** La rama que resolvía el inquilino desde el usuario nunca se
ejecutaba; todo terminaba resolviéndose por el encabezado `X-Organization`.

**Causa.** Un middleware de Django corre **antes** de la vista; la
autenticación de DRF ocurre **dentro** de la vista.

**Riesgo señalado por Karen.** Que alguien mandara el token de una organización
y el slug de otra.

### D-11 · La autenticación JWT era imposible

Éste no estaba en el reporte y es el que decidió el diseño.

**Síntoma.** Comprobado experimentalmente:

```
Resolver el usuario SIN contexto:  AuthenticationFailed: "User not found"
Resolver el usuario CON contexto:  P Robe <probe@probe.test>
```

**Causa.** SimpleJWT resuelve el usuario con `User.objects.get(id=...)`, y
`users` está protegida por RLS. Sin contexto la consulta devuelve cero filas.
Y el token no llevaba `organization_id`.

**Consecuencia.** El contexto debe fijarse **antes** de resolver el usuario, y
por lo tanto no puede salir de la base: **tiene que venir en el token**. Las
dos salidas que Karen planteaba como equivalentes se reducían a una.

**Corrección.** Todo token lleva `organization_id` e `is_platform_admin`, y el
contexto se fija en `accounts/authentication.py`:

```
1. validar la firma        (sin tocar la base)
2. leer organization_id del claim
3. SET LOCAL app.tenant_id
4. resolver el usuario     (ya visible bajo RLS)
5. comprobar el nivel de acceso
```

Sobre el riesgo de D-10: **manda el token, no el encabezado**, y hay una prueba
que lo fija.

### D-12 · Las alertas escritas durante un rechazo se descartaban

**Síntoma.** Un token con otra organización devolvía 401 correctamente, pero no
quedaba ninguna alerta.

**Causa.** **DRF llama a `set_rollback()` cuando maneja una excepción.** Todo lo
escrito durante el rechazo se descarta. Los intentos de acceso cruzado pasaban
en silencio, que es exactamente lo que US-45 tiene que ver.

**Corrección.** Las alertas quedan pendientes en la petición y el middleware
las persiste **después** de cerrar la transacción.

### D-13 · Los atributos sobre el `Request` de DRF no llegan al middleware

**Síntoma.** La corrección de D-12 no funcionaba: la lista de alertas
pendientes llegaba vacía.

**Causa.** DRF envuelve el `HttpRequest` de Django en su propio objeto
`Request`. Un atributo asignado sobre el envoltorio no lo ve el middleware, que
trabaja con el de abajo.

**Corrección.** Desenvolver con `request._request`.

---

## Lo que dejó cada ronda, como regla

**1. Las pruebas de aislamiento se corren como `app_user`, nunca como
`postgres`.** Ya está configurado así; sólo hay que no cambiarlo. `postgres`
omite RLS aunque haya `FORCE`, así que las pruebas pasarían sin verificar nada.
Costó cinco defectos.

**2. Toda historia suma pruebas que entran por el ciclo HTTP**, en
`tests/test_peticiones.py`, no sólo pruebas de base en `test_isolation.py`. Un
backend que no arranca puede tener todas las pruebas de base en verde.

**3. `SET LOCAL` vive hasta el fin de la transacción, no del bloque.** Salir de
un `atomic()` anidado no lo deshace.

**4. `INSERT ... RETURNING` exige pasar también la política de `SELECT`.** Si
una tabla deniega la lectura, su clave no puede ser `bigserial`.

**5. Si escribís auditoría en un camino de error, no va a sobrevivir.** DRF hace
rollback al manejar excepciones.

**6. Nunca emitir tokens con `AccessToken.for_user()`.** Usar
`accounts.tokens.tokens_para()`.

---

## Comportamientos conocidos y aceptados

No son defectos: son consecuencias buscadas del diseño. Se anotan para que
nadie los reporte como fallas.

### C-01 · No se puede borrar un usuario en duro

RNF-18 exige que la bitácora sea inalterable, así que `app_user` no tiene
`UPDATE` ni `DELETE` sobre `audit_log` (verificado: `SELECT` e `INSERT` sí,
`UPDATE` y `DELETE` no). Como `audit_log.user` usa `ON DELETE SET NULL`,
PostgreSQL necesita esos permisos para borrar un usuario referenciado, y falla
con `permission denied for table audit_log`.

**Es el comportamiento buscado:** los usuarios se **desactivan**
(`is_active = false`), no se borran. Un sistema con historia clínica no borra a
quien firmó una atención. Lo mismo aplica a organizaciones.

### C-02 · El superadministrador no ve datos de ningún inquilino

Por diseño (decisión D-3 del modelo). Consecuencia operativa: la tarea de
métricas de US-45 tiene que recorrer organización por organización. El
pseudocódigo está en `modelo-datos/sprint-0.md` §7.3.

### C-03 · Sin Docker no hay pgvector

Quien instale PostgreSQL directamente no tendrá la extensión. **No afecta al
Sprint 0** —no hay ninguna columna de tipo vector— pero hace falta en el
Sprint 3. Los tres caminos están en `entorno/sin-docker.md`. Conviene
resolverlo antes de que ese sprint empiece.

---

## Defectos de documentación

También se corrigieron, porque una guía equivocada cuesta lo mismo que un bug.

| # | Qué decía | Qué pasaba |
|---|---|---|
| DOC-01 | "Un `#` dentro de un valor del `.env` lo corta ahí" | **Falso.** `abc#def` llega entero. Lo que sí rompe es un comentario en la **misma línea** (se vuelve parte del valor) o espacios alrededor del `=` (la línea se descarta sin aviso). Verificado contra `django-environ` |
| DOC-02 | `CORS_ALLOWED_ORIGINS` no figuraba en `.env.example` | `settings.py` la leía y nadie la veía |
| DOC-03 | La guía mandaba ejecutar `sprint-0.sql` a mano | Quedó viejo al existir las migraciones. Ejecutarlo dejaría a Django queriendo crear tablas que ya existen |
| DOC-04 | El tutorial no mencionaba instalar Git ni Docker | Asumía que ya estaban. Docker en Windows además necesita virtualización, que es donde más se traba |

---

## Cómo se verificó cada corrección

Todos los defectos tienen una prueba que **fallaba antes** de la corrección:

- **D-01 a D-07** → `backend/tests/test_isolation.py` (21 pruebas)
- **D-08 a D-13** → `backend/tests/test_peticiones.py` (12 pruebas)

```bash
cd backend && pytest        # 33 passed
```

Además, comprobado a mano: `runserver` responde `200` en `/api/health/`, y el
esquema está aplicado tanto en el contenedor local como en Supabase, con el
aislamiento verificado en vivo en ambos.
