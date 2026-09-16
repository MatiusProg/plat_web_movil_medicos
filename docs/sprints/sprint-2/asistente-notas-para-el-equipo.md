# Asistente de orientación — lo que hay que saber antes de seguir

Notas del 16/09/2026, después de dejar US-31 corriendo en desarrollo y en el
despliegue de Railway. Van dirigidas sobre todo a **Daniel** (dueño del texto
del catálogo) y al **SM** (dueño del despliegue, de Supabase y de US-32), pero
los puntos 3 y 4 son para las cinco máquinas del equipo.

Cómo está hecho el asistente y qué tipo de IA es:
[docs/arquitectura/asistente-como-esta-hecho.md](../../arquitectura/asistente-como-esta-hecho.md).

---

## 1. Daniel: las descripciones del catálogo cambiaron, y también en Supabase

**Qué pasó.** Las descripciones de las cinco especialidades del catálogo de
demostración están reescritas. El cambio entró a `main` con el PR #41 y **ya se
aplicó a la base de Supabase** el 16/09, corriendo `seed_catalog` sobre las dos
organizaciones (`morita2` y `kolping3k`).

**Por qué.** Esas descripciones son el corpus del asistente: es el texto contra
el que se compara la pregunta del paciente. Las que había —"Cardiología:
corazón y sistema circulatorio"— están escritas para un listado, y para
recuperación no sirven: nadie consulta escribiendo "sistema circulatorio". Lo
que acerca la pregunta al fragmento son los **motivos de consulta**.

**Qué cambió en concreto.** Cada especialidad enumera ahora sus motivos en
oraciones separadas, a propósito: el indexador parte por oración, así que cada
grupo termina siendo su propio fragmento y se recupera solo. Pasaron de 9
fragmentos por organización a **24**.

> Cardiología. Motivos de consulta frecuentes: dolor u opresión en el pecho,
> palpitaciones, presión alta…

**Lo que te toca decidir.** El reparto dice que el corpus se acuerda con vos
antes de cargarlo, y esto se cargó primero para que la demostración del 16
funcionara. **El texto es tuyo: revisalo, corregilo o descartalo.** Si lo
cambiás, hay que reindexar (punto 5). Y si preferís otra redacción, el criterio
único es: tiene que parecerse a cómo escribe un paciente, no a cómo se cataloga
una especialidad.

**Ojo con `seed_catalog`:** usa `update_or_create`, así que **sobrescribe** la
descripción de las especialidades que ya existen. Dice "0 creados, 5 ya
estaban" y aun así actualizó el texto. Si alguien había editado una descripción
a mano en Supabase, ese cambio se perdió.

---

## 2. SM: qué quedó tocado en el despliegue

**Variables nuevas en el servicio Backend de Railway** (ambiente `production`):

| Variable | Valor |
|---|---|
| `ASSISTANT_EMBEDDING_PROVIDER` | `gemini` |
| `ASSISTANT_CHAT_PROVIDER` | `gemini` |
| `GEMINI_API_KEY` | la clave, cargada en Railway |

La clave **no está en el repositorio** y no tiene que estarlo: es la regla 11
del sprint. El resto de los parámetros sale de `settings.py`.

**El índice de Supabase se construyó**: `embed_catalog` sobre las dos
organizaciones, 24 fragmentos cada una, con `gemini-embedding-001`. Antes
estaba vacío — la tabla existía y no tenía una sola fila, así que el asistente
desplegado habría contestado "no puedo orientarte" a todo.

**Verificado contra la base de producción**, con el umbral en 0,62:

```
== morita2
   me salieron manchas en la piel        -> Dermatología 0.73     fragmentos: 5
   tengo la presion alta y palpitaciones -> Cardiología 0.725     fragmentos: 5
   mi hijo tiene fiebre hace dos dias    -> Pediatría 0.696       fragmentos: 5
   cuanto sale alquilar un departamento  -> NADA (no inventa)     fragmentos: 0
== kolping3k   (idéntico)
```

**La cuota de Gemini es compartida** entre las máquinas de desarrollo y el
despliegue. Si en una demostración aparece `generated_by: "plantilla"` en vez
de `"gemini"`, es cuota o es el 503 del modelo: el asistente sigue contestando
con los fragmentos recuperados, que es el comportamiento diseñado, no una
falla.

---

## 3. pgvector es obligatorio para todos, y en Windows no viene incluido

La columna `embedding` es de tipo `vector`, o sea que la extensión es parte del
esquema: **sin ella no se crea ni la base de pruebas y no corre ninguna prueba
del proyecto**, tampoco las del Sprint 1.

- **En Supabase** la crea `postgres` desde el SQL Editor del panel, una sola
  vez: `CREATE EXTENSION IF NOT EXISTS vector;` — `app_user` es `NOSUPERUSER` a
  propósito y no puede.
- **En Windows**, el instalador de EDB no trae pgvector y el repositorio oficial
  no publica binarios. Lo que funcionó el 16/09 está documentado en
  `docs/entorno/sin-docker.md`: el binario de `pgvector 0.8.6` para PostgreSQL
  18, más un detalle que no es obvio — **la extensión se precrea en
  `template1`**, para que la base de pruebas que crea pytest la herede sin que
  `app_user` necesite ser superusuario.

`pip install pgvector` instala el **cliente**, no la extensión del servidor.
Tener el paquete no cambia nada.

---

## 4. Si tocás el corpus o el modelo, hay que medir de nuevo

Dos cosas que se aprendieron midiendo, y que van a volver a aplicar:

**Reindexar es obligatorio al cambiar de proveedor.** Los vectores de dos
modelos distintos no se comparan entre sí. Mezclarlos **no da error**: da
distancias que no significan nada. Por eso cada fila guarda `embedding_model`,
y por eso conviene mirar esa columna antes de confiar en un índice:

```sql
SELECT embedding_model, count(*) FROM assistant_catalog_fragments GROUP BY 1;
```

**El umbral se mide.** El que hay —0,62 para Gemini— sale de comparar 10
preguntas del catálogo (0,637–0,762) contra 7 ajenas (0,518–0,608). El hueco es
de **0,029**: estrecho. Con el 0,35 que había antes, escrito sin medir,
"cuánto sale alquilar un departamento" recuperaba Medicina general con 0,55 y el
asistente contestaba con una especialidad — justo lo que el umbral existe para
impedir.

---

## 5. Cómo reindexar, cuando haga falta

Desde una máquina con `DATABASE_URL` apuntando a donde corresponda, o desde la
consola del servicio en Railway (ahí el intérprete es `/opt/venv/bin/python`,
porque el `python` del contenedor no tiene Django):

```bash
python backend/manage.py seed_catalog  --organization <slug>   # si cambió el texto
python backend/manage.py embed_catalog --organization <slug>
python backend/manage.py embed_catalog --organization <slug> --dry-run  # sólo mirar
```

`embed_catalog` imprime con qué modelo vectorizó y cuántos fragmentos guardó.
Reindexar **reemplaza** los fragmentos de cada fuente, no los duplica.

---

## 6. Un detalle para cuando se muestre el aislamiento

El punto del aislamiento —la misma pregunta en dos organizaciones— **no se ve a
simple vista con los datos actuales**: las dos tienen sembrado el mismo catálogo
de demostración, así que las dos contestan "Dermatología 0,73". Lo que
efectivamente está aislado son las **filas** del índice: cada organización
recupera sus propios 24 fragmentos, con `source_id` distintos, y ninguna puede
leer los de la otra.

Se demuestra mirando los `source_id` de la respuesta, o con la consulta SQL
agrupada por `organization_id`. Si se quiere que se note a simple vista, hay que
darle a una de las dos una especialidad que la otra no tenga.

La prueba automatizada equivalente es
`tests/test_us31.py::test_los_fragmentos_de_una_organizacion_no_se_ven_desde_la_otra`.
