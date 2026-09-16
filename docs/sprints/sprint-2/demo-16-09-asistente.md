# Corte del 16/09 — El asistente, de punta a punta

Guion de lo que se muestra de US-31 en el corte de avance del **miércoles
16/09/26, 19:00**. Lo que se enseña no es una historia terminada: es el camino
vertical funcionando sobre datos reales, que es lo que pidió la docente.

El reparto completo está en [reparto.md](reparto.md), sección 2.

---

## 0. Antes de salir de casa

| Comprobación | Cómo |
|---|---|
| Supabase no está pausada | Abrir <https://web-production-872fa.up.railway.app/api/health/>. Tiene que devolver `{"status":"ok",...}`. Esa vista abre un cursor contra PostgreSQL, así que un 200 significa que la base contestó |
| La extensión existe | En el SQL Editor de Supabase: `SELECT * FROM pg_extension WHERE extname = 'vector';` tiene que devolver una fila |
| El índice tiene fragmentos | `SELECT count(*) FROM assistant_catalog_fragments;` |

> **Si algo de esto falla, se arregla el 15, no el 16.** El plan gratuito de
> Supabase se pausa a los 7 días sin actividad y el despliegue queda caído sin
> aviso.

---

## 1. Preparar la base — una sola vez

La extensión la crea `postgres` desde el **SQL Editor** del panel de Supabase,
porque `app_user` es `NOSUPERUSER` a propósito:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Después, desde la máquina, con `DATABASE_URL` apuntando a Supabase:

```bash
cd backend
python manage.py migrate
python manage.py seed_catalog --organization <slug> --with-schedules
python manage.py embed_catalog --organization <slug>
```

El último comando imprime con qué modelo vectorizó y cuántos fragmentos
guardó. Si dice `local-hash-768`, está usando el proveedor determinista; para
Gemini hay que poner las variables del `.env` (ver
[.env.example](../../../.env.example), sección 4).

**Para revisar el corpus sin gastar cuota ni escribir nada:**

```bash
python manage.py embed_catalog --organization <slug> --dry-run
```

---

## 2. Qué se muestra, en este orden

### a. Que el índice existe y es de verdad

```sql
SELECT source_type, count(*), min(embedding_model)
  FROM assistant_catalog_fragments GROUP BY 1;
```

Cinco especialidades, ~25 fragmentos, un solo modelo. **Mezclar dos modelos en
el mismo índice no da error, da distancias que no significan nada**: por eso
la columna `embedding_model` está y por eso se mira.

### b. La consulta, con su respaldo

```
POST /api/assistant/suggest/
{ "question": "me duele el pecho cuando subo escaleras" }
```

Lo que hay que señalar de la respuesta **no es la especialidad sugerida**: es
el arreglo `fragments`. Cada fragmento viene con su texto y su similitud. Esa
lista es la única evidencia de que el asistente no alucinó — recuperó y
después respondió, en ese orden.

También mirar `generated_by`: dice `gemini` si redactó el modelo, `plantilla`
si el proveedor no respondió y la frase se armó con lo recuperado, y `regla`
si cortó la barrera de emergencia.

### c. Que no inventa

```
{ "question": "cuanto sale alquilar un departamento" }
```

Devuelve `specialty: null` y `fragments: []`. Con cinco especialidades siempre
hay una *menos lejana*; el umbral de similitud es lo que evita que ésa se
convierta en una recomendación médica.

### d. Que corta una urgencia

```
{ "question": "me duele el pecho y no puedo respirar" }
```

`emergency: true`, ninguna especialidad y ninguna invitación a reservar. Es la
semilla de **US-34**, que vence el 26/09. Decir en voz alta qué falta: las
reglas también en el prompt, el asiento en la bitácora, el catálogo de señales
revisado por alguien de clínica y la pantalla del móvil.

### e. El aislamiento — lo de Daniel

La misma pregunta autenticado como paciente de una organización y de la otra,
devolviendo catálogos distintos. Es el apartado 1.1.6 del documento aplicado a
la IA y es el diferencial del proyecto. La prueba automatizada equivalente es
`tests/test_us31.py::test_la_misma_pregunta_en_dos_organizaciones_devuelve_catalogos_distintos`.

---

## 3. Lo que NO se promete

Ninguna historia cerrada. Ni pago, ni reserva, ni conversación con memoria.
US-31 cierra el **26/09** junto con US-34 — el asistente no se publica sin la
derivación a emergencia.

Decirlo de entrada evita que el avance se lea como un incumplimiento.

---

## 4. Si algo se cae en vivo

| Qué pasa | Qué hacer |
|---|---|
| Gemini no responde (cuota, red) | No hay que tocar nada: el endpoint degrada solo. Los fragmentos se siguen recuperando y la frase se arma con lo recuperado, marcada como `plantilla`. Se puede señalar como decisión de diseño, porque lo es |
| El proveedor falla al vectorizar la pregunta | Devuelve **503** y "No puedo responderte ahora". Sin vector no hay búsqueda, y sin búsqueda no hay nada honesto que contestar |
| Se acabó la cuota antes de empezar | En el `.env`, `ASSISTANT_EMBEDDING_PROVIDER=local` y `ASSISTANT_CHAT_PROVIDER=local`, y **reindexar**: `python manage.py embed_catalog --organization <slug>`. Los vectores de dos modelos distintos no se comparan entre sí |
| La red del aula no anda | Lo mismo que arriba. El proveedor local no sale a internet |

> El plan de contingencia **exige reindexar**, y reindexar tarda. Tenerlo
> hecho antes vale más que tenerlo previsto.
